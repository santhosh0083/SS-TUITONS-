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
from app.services import email

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


@router.get("/diagnostics")
async def diagnostics() -> dict[str, object]:
    """Report configuration state without revealing any secret value.

    Exists because a misconfigured deployment otherwise fails opaquely: a
    missing JWT secret, a wrong cookie mode or an unset database URL all
    surface as a generic error. This says which one, using booleans and
    lengths only — never the values themselves.
    """
    s = get_settings()

    def present(value: str) -> bool:
        return bool(value) and not value.upper().startswith(("CONFIGURE_ME", "CHANGE_ME"))

    problems: list[str] = []
    try:
        s.assert_production_safe()
    except RuntimeError as exc:
        problems.append(str(exc))

    return {
        "app_env": s.app_env,
        "serverless": s.serverless,
        "cookie": {"secure": s.cookie_secure, "samesite": s.cookie_samesite},
        "cross_site": s.is_cross_site,
        "frontend_base_url": s.frontend_base_url,
        "cors_allowed_origins": s.cors_origins,
        "configured": {
            "database_url": present(s.database_url),
            "jwt_secret": len(s.jwt_secret) >= 32,
            "message_encryption_key": len(s.message_encryption_key) >= 32,
            "ai_provider": s.ai_provider or None,
            "gemini_api_key": present(s.gemini_api_key),
            "email_enabled": s.email_enabled,
            # Which transport, and whether it can work here. "enabled" alone
            # reported healthy for days while every send failed: SMTP is
            # blocked outbound on Render's free plan.
            "email_provider": s.email_provider,
            "email_ready": email.is_configured(),
            "email_status": email.configuration_hint(),
            "payment_upi": present(s.payment_upi_id),
        },
        "config_problems": problems or None,
    }
