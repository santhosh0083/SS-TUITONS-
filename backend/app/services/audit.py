"""Audit logging.

Writes to `audit_logs`, which a database trigger makes append-only — rows
cannot be edited or deleted, including by this application.

Audit writes must never break the operation they are recording. A failure to
log is reported but does not roll back the user's action.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import AuditLog

logger = logging.getLogger(__name__)

# Actions worth recording. Named constants so a typo becomes an import error
# rather than an unsearchable audit trail.
LOGIN_SUCCEEDED = "auth.login.succeeded"
LOGIN_FAILED = "auth.login.failed"
LOGIN_BLOCKED_LOCKED = "auth.login.blocked_locked"
LOGOUT = "auth.logout"
TOKEN_REFRESHED = "auth.token.refreshed"  # noqa: S105 - action name, not a secret
TOKEN_REUSE_DETECTED = "auth.token.reuse_detected"  # noqa: S105 - action name
PASSWORD_CHANGED = "auth.password.changed"  # noqa: S105 - action name


async def record(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Append an audit entry.

    Never raises. A logging failure must not cost the user their action.
    """
    try:
        session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before,
                after_state=after,
                ip_address=ip_address,
                user_agent=(user_agent or "")[:400] or None,
                created_at=datetime.now(UTC),
            )
        )
        await session.flush()
    except Exception:
        logger.exception("Failed to write audit log for action %s", action)
