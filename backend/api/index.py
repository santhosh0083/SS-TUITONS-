"""Vercel serverless entry point.

Vercel's Python runtime looks for an ASGI app in this module. FastAPI is one,
so it is re-exported directly — no adapter needed.

Note what does NOT happen here: database migrations. On a long-running host the
container runs `alembic upgrade head` at start-up, but a serverless function
may cold-start hundreds of times a day and must not attempt schema changes.
Migrations are run manually from a developer machine:

    cd backend && ./.venv/Scripts/python -m alembic upgrade head
"""

from app.main import app

# Vercel discovers this symbol.
__all__ = ["app"]
