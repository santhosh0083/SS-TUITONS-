"""Provider-agnostic AI client.

SS Tuitions starts on a free tier and may move to a paid one. Everything above
this module talks to `AIProvider`, so switching is a config change rather than
a rewrite of the tutor and the question generator.

Providers:
  gemini     Google AI Studio free tier — 1,500 requests/day, no card required.
             NOTE: Google may use free-tier data to improve their models, which
             is why app/ai/privacy.py strips identifiers before anything is sent.
  anthropic  Claude. Paid; data is not used for training.

Nothing here ever receives a student's name — callers pass scrubbed text only.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    """The provider failed. Message is safe to log, not to show a student."""


class AINotConfigured(AIError):
    """No API key set. The feature should be presented as unavailable."""


@dataclass(frozen=True)
class AIResponse:
    text: str
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> AIResponse: ...


class GeminiProvider(AIProvider):
    """Google AI Studio. Free tier requires only an API key."""

    name = "gemini"
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise AINotConfigured("GEMINI_API_KEY is not set")
        self._key = api_key
        self._model = model

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> AIResponse:
        body: dict = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        url = f"{self.BASE}/models/{self._model}:generateContent"

        # The free tier returns 503 "high demand" fairly often, and a transient
        # blip should not surface to a student as a failure. Retry briefly
        # before giving up. 429 is NOT retried — that is a real quota limit and
        # hammering it makes things worse.
        r = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    r = await client.post(url, params={"key": self._key}, json=body)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise AIError(
                        f"Could not reach Gemini: {type(exc).__name__}"
                    ) from exc
                await asyncio.sleep(1.5 * (attempt + 1))
                continue

            if r.status_code == 503 and attempt < 2:
                logger.info("Gemini busy (503), retrying in %.1fs", 1.5 * (attempt + 1))
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            break

        if r is None:
            raise AIError("Could not reach Gemini")

        if r.status_code == 429:
            raise AIError(
                "Today's free AI limit has been reached. It resets tomorrow."
            )
        if r.status_code == 503:
            raise AIError(
                "The AI tutor is very busy right now. Please try again in a moment."
            )
        if r.status_code >= 400:
            # Never surface the body: it can echo the prompt back.
            raise AIError(f"Gemini returned HTTP {r.status_code}")

        data = r.json()
        candidates = data.get("candidates") or []
        if not candidates:
            # Usually a safety block.
            raise AIError("Gemini returned no answer for that request")

        parts = candidates[0].get("content", {}).get("parts") or []
        # Gemini 3 models reason internally and may return those thoughts as
        # parts flagged `thought: true`. That is the model's scratch work, not
        # its answer — showing it to a student would leak the reasoning they
        # are supposed to be doing themselves.
        text = "".join(
            p.get("text", "") for p in parts if not p.get("thought")
        ).strip()
        usage = data.get("usageMetadata", {})

        if not text:
            # Everything came back as thinking with no answer, usually because
            # maxOutputTokens was exhausted before the reply began.
            finish = candidates[0].get("finishReason")
            raise AIError(
                f"Gemini returned no usable answer (finishReason={finish}). "
                "Try increasing max_tokens."
            )

        return AIResponse(
            text=text,
            model=self._model,
            tokens_in=usage.get("promptTokenCount"),
            tokens_out=usage.get("candidatesTokenCount"),
        )


class AnthropicProvider(AIProvider):
    """Claude. Paid; submitted data is not used for training."""

    name = "anthropic"
    BASE = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key or api_key.startswith("CHANGE_ME"):
            raise AINotConfigured("ANTHROPIC_API_KEY is not set")
        self._key = api_key
        self._model = model

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> AIResponse:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(
                    self.BASE,
                    headers={
                        "x-api-key": self._key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "system": system,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
        except httpx.HTTPError as exc:
            raise AIError(f"Could not reach Claude: {type(exc).__name__}") from exc

        if r.status_code == 429:
            raise AIError("Rate limit reached. Try again shortly.")
        if r.status_code >= 400:
            raise AIError(f"Claude returned HTTP {r.status_code}")

        data = r.json()
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        ).strip()
        usage = data.get("usage", {})
        return AIResponse(
            text=text,
            model=self._model,
            tokens_in=usage.get("input_tokens"),
            tokens_out=usage.get("output_tokens"),
        )


def get_provider() -> AIProvider:
    """Build the configured provider, or raise AINotConfigured."""
    s = get_settings()
    choice = (s.ai_provider or "").lower()

    if choice == "gemini":
        return GeminiProvider(s.gemini_api_key, s.gemini_model)
    if choice == "anthropic":
        return AnthropicProvider(s.anthropic_api_key, s.ai_model_tutor)
    raise AINotConfigured(
        "AI_PROVIDER is not set. Use 'gemini' (free) or 'anthropic' (paid)."
    )


def is_configured() -> bool:
    """True when AI features can actually run. Used to hide them in the UI
    rather than letting a student click into an error."""
    try:
        get_provider()
    except AINotConfigured:
        return False
    return True


def parse_json_response(text: str) -> object:
    """Parse a model's JSON reply, tolerating markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("AI returned malformed JSON: %s", cleaned[:200])
        raise AIError("The AI returned a malformed response") from exc
