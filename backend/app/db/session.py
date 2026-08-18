"""Async database engine and session management.

Serverless vs long-running
--------------------------
On a normal server one process holds a small connection pool for its lifetime.
On serverless (Vercel), each cold start is a fresh process that may serve one
request and vanish, so a per-process pool is wasted and, multiplied across
concurrent invocations, will exhaust the database's connection limit.

`SERVERLESS=true` therefore switches to NullPool: open a connection, use it,
close it. Supabase's pooler does the actual pooling on its side, which is what
it is for.

asyncpg + a transaction pooler also cannot use prepared statements, because a
statement prepared on one pooled backend may be executed on another. Disabling
the statement cache avoids the "prepared statement does not exist" errors that
otherwise appear intermittently under load.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

_settings = get_settings()

_engine_kwargs: dict[str, Any] = {"echo": False}

if _settings.serverless:
    # No per-process pool; the Supabase pooler handles pooling.
    _engine_kwargs["poolclass"] = NullPool
    _engine_kwargs["connect_args"] = {
        # Required when talking to a transaction pooler through asyncpg.
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
else:
    _engine_kwargs.update(
        pool_size=_settings.db_pool_size,
        max_overflow=_settings.db_max_overflow,
        # Supabase drops idle connections; verify one before reusing it.
        pool_pre_ping=True,
    )

engine = create_async_engine(_settings.database_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a session that always closes.

    Commits are explicit in the service layer — this only guarantees rollback
    on error and cleanup on exit.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
