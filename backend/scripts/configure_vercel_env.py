"""Push backend environment variables from .env to a Vercel project.

Vercel does not read a .env file from the repository — committed secrets are a
security hole, which is why ours is gitignored. Variables must live in Vercel's
own store. This script puts them there in one command instead of by hand.

Usage:

    set VERCEL_TOKEN=your_token_from_vercel.com/account/tokens
    ./.venv/Scripts/python -m scripts.configure_vercel_env

Values are read from .env and sent straight to Vercel; they are never printed.
Existing variables of the same name are replaced.
"""

import os
import sys
from pathlib import Path

import httpx

PROJECT = "ss-tuitons12"  # the API project (root directory: backend)
API = "https://api.vercel.com"

# Applies to all three Vercel environments so preview deploys work too.
TARGETS = ["production", "preview", "development"]

SECRET_KEYS = {
    "DATABASE_URL",
    "DATABASE_DIRECT_URL",
    "JWT_SECRET",
    "MESSAGE_ENCRYPTION_KEY",
    "GEMINI_API_KEY",
    "EMAIL_SMTP_PASSWORD",
}

# Values that must differ from local development on a deployed backend.
OVERRIDES = {
    "APP_ENV": "production",
    "SERVERLESS": "true",
    "COOKIE_SECURE": "true",
    "COOKIE_SAMESITE": "none",
    "FORCE_HTTPS": "true",
    "FRONTEND_BASE_URL": "https://ss-tuitons.vercel.app",
    "CORS_ALLOWED_ORIGINS": "https://ss-tuitons.vercel.app",
    "BACKEND_BASE_URL": f"https://{PROJECT}.vercel.app",
}

WANTED = [
    "APP_ENV", "APP_NAME", "APP_TIMEZONE", "SERVERLESS",
    "BACKEND_BASE_URL", "FRONTEND_BASE_URL", "CORS_ALLOWED_ORIGINS",
    "COOKIE_SECURE", "COOKIE_SAMESITE", "FORCE_HTTPS",
    "DATABASE_URL", "DATABASE_DIRECT_URL",
    "JWT_SECRET", "MESSAGE_ENCRYPTION_KEY",
    "AI_PROVIDER", "GEMINI_API_KEY", "GEMINI_MODEL", "AI_STRIP_IDENTIFIERS",
    "EMAIL_ENABLED", "EMAIL_SMTP_HOST", "EMAIL_SMTP_PORT", "EMAIL_SMTP_USER",
    "EMAIL_SMTP_PASSWORD", "EMAIL_FROM_ADDRESS", "EMAIL_FROM_NAME",
    "PAYMENT_UPI_ID", "PAYMENT_PAYEE_NAME", "PAYMENT_PHONE_NUMBER",
    "PAYMENT_BANK_NAME", "PAYMENT_ACCOUNT_NUMBER", "PAYMENT_IFSC",
    "PAYMENT_QR_IMAGE_URL", "PAYMENT_INSTRUCTIONS",
]


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def main() -> int:
    token = os.environ.get("VERCEL_TOKEN", "").strip()
    if not token:
        print("Create a token at https://vercel.com/account/tokens, then:")
        print("  set VERCEL_TOKEN=your_token")
        print("  .\\.venv\\Scripts\\python -m scripts.configure_vercel_env")
        return 1

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        print(f"Could not find {env_path}")
        return 1

    values = load_env(env_path)
    values.update(OVERRIDES)

    headers = {"Authorization": f"Bearer {token}"}
    client = httpx.Client(headers=headers, timeout=45)

    # Remove existing entries first so this is repeatable rather than additive.
    existing = client.get(f"{API}/v9/projects/{PROJECT}/env")
    if existing.status_code == 404:
        print(f"Project '{PROJECT}' not found. Check the name in Vercel.")
        return 1
    if existing.status_code != 200:
        print(f"Could not list variables: HTTP {existing.status_code}")
        return 1

    by_key = {e["key"]: e["id"] for e in existing.json().get("envs", [])}

    created = 0
    skipped: list[str] = []
    for key in WANTED:
        value = values.get(key, "")
        if not value or value.upper().startswith(("CONFIGURE_ME", "CHANGE_ME")):
            skipped.append(key)
            continue

        if key in by_key:
            client.delete(f"{API}/v9/projects/{PROJECT}/env/{by_key[key]}")

        r = client.post(
            f"{API}/v10/projects/{PROJECT}/env",
            json={
                "key": key,
                "value": value,
                "type": "encrypted" if key in SECRET_KEYS else "plain",
                "target": TARGETS,
            },
        )
        if r.status_code in (200, 201):
            created += 1
            shown = "***" if key in SECRET_KEYS else value[:48]
            print(f"  {key:26} = {shown}")
        else:
            print(f"  FAILED {key}: HTTP {r.status_code} {r.text[:120]}")
            return 1

    print(f"\nSet {created} variables on '{PROJECT}'.")
    if skipped:
        print(f"Skipped (empty in .env): {', '.join(skipped)}")
    print("\nRedeploy the project for these to take effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
