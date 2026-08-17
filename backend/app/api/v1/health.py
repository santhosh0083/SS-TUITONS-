"""Health and readiness endpoints.

`/health` answers "is the process alive". `/ready` answers "can it actually
serve traffic", which means checking the database. Keeping them separate
matters for deployment: a restart loop caused by a database blip is worse than
serving a clear "not ready".
"""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.models import Base

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — does not touch the database."""
    return {"status": "ok", "service": settings.app_name}


@router.get("/ready")
async def ready() -> dict[str, object]:
    """Readiness — verifies the database is reachable and migrated."""
    expected_tables = len(Base.metadata.tables)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            actual = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = 'public' "
                        "AND table_type = 'BASE TABLE' "
                        "AND table_name <> 'alembic_version'"
                    )
                )
            ).scalar_one()
            revision = (
                await conn.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        return {
            "ready": False,
            "database": "unreachable",
            "reason": type(exc).__name__,
            "hint": "Check DATABASE_URL in .env, then run: alembic upgrade head",
        }

    migrated = actual == expected_tables
    return {
        "ready": migrated,
        "database": "connected",
        "tables_expected": expected_tables,
        "tables_found": actual,
        "migration_revision": revision,
        "hint": None if migrated else "Run: alembic upgrade head",
    }
