"""Vercel serverless entry point.

Vercel's Python runtime looks for an ASGI app in this module. FastAPI is one,
so it can be served directly — but two hosting quirks are handled here.

1. PATH RECOVERY
   vercel.json rewrites every path to this file. Vercel warned during the build
   that "internal rewrites now route requests using the rewritten destination
   path", which would hand FastAPI `/api/index` instead of `/api/v1/health` and
   404 every route. The wrapper below restores the original path from whichever
   header Vercel provides, and leaves the request untouched when the path is
   already correct — so it is harmless if the rewrite behaves as before.

2. NO MIGRATIONS ON COLD START
   A long-running container runs `alembic upgrade head` at start-up. A
   serverless function may cold-start hundreds of times a day and must never
   attempt schema changes. Migrations are run from a developer machine:

       cd backend && ./.venv/Scripts/python -m alembic upgrade head
"""

import logging

from app.main import app as fastapi_app

logger = logging.getLogger(__name__)

# Paths that mean "the rewrite replaced the real path".
_REWRITTEN = ("/api/index", "/api/index.py")

# Headers Vercel has used to carry the original request path, most specific
# first. Checked in order; the first usable one wins.
_ORIGINAL_PATH_HEADERS = (
    b"x-vercel-original-path",
    b"x-vercel-original-pathname",
    b"x-original-uri",
    b"x-forwarded-uri",
)


def _recover_path(scope: dict) -> str | None:
    """Return the caller's real path when the rewrite has masked it."""
    headers = dict(scope.get("headers") or [])
    for name in _ORIGINAL_PATH_HEADERS:
        raw = headers.get(name)
        if not raw:
            continue
        value = raw.decode("latin-1").split("?", 1)[0]
        if value.startswith("/") and not value.startswith(_REWRITTEN):
            return value
    return None


async def app(scope, receive, send):
    """ASGI wrapper that repairs the request path, then delegates to FastAPI."""
    if scope.get("type") == "http":
        path = scope.get("path", "")
        # Diagnostic hatch: always answers, whatever the routing is doing.
        if "__whoami" in path or b"__whoami" in (scope.get("query_string") or b""):
            await _echo(scope, send)
            return
        if path.startswith(_REWRITTEN):
            recovered = _recover_path(scope)
            if recovered:
                scope = {**scope, "path": recovered, "raw_path": recovered.encode()}
            else:
                # No header carried the original path. Rather than 404 with no
                # explanation, log the headers received so the cause is visible
                # in the Vercel function logs.
                logger.error(
                    "Request arrived as %s with no original-path header. "
                    "Headers seen: %s",
                    path,
                    sorted(
                        k.decode("latin-1") for k in dict(scope.get("headers") or {})
                    ),
                )
    await fastapi_app(scope, receive, send)


async def _echo(scope, send) -> None:
    """Report exactly what this function received.

    Temporary. Every route 404s in production, which means FastAPI is being
    handed a path it does not recognise and none of the headers guessed at in
    _ORIGINAL_PATH_HEADERS carried the original. Rather than guess a fourth
    time, this returns the raw scope so the truth is visible in one request.
    """
    import json

    payload = json.dumps(
        {
            "received_path": scope.get("path"),
            "raw_path": (scope.get("raw_path") or b"").decode("latin-1"),
            "root_path": scope.get("root_path"),
            "query_string": (scope.get("query_string") or b"").decode("latin-1"),
            "headers": {
                k.decode("latin-1"): v.decode("latin-1")
                for k, v in (scope.get("headers") or [])
            },
        },
        indent=1,
    ).encode()

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send({"type": "http.response.body", "body": payload})


__all__ = ["app"]
