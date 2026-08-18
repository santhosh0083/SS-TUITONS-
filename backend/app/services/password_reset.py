"""Forgot-password flow: request a reset link by email, then set a new password.

Two properties matter here:

1. **No account enumeration.** Requesting a reset for an unknown email returns
   the same response as for a known one. Otherwise the endpoint becomes a way
   to discover which emails have accounts.

2. **Single-use, short-lived, hashed tokens.** Only a SHA-256 hash of the token
   is stored, so a leaked table cannot reset anyone's password. A token expires
   after an hour and is consumed on use.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.identity import PasswordResetToken, RefreshToken, User
from app.services import audit, email

TOKEN_TTL = timedelta(hours=1)


class ResetError(Exception):
    """Message is safe to show the user."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def request_reset(session: AsyncSession, *, user_email: str) -> None:
    """Create a reset token and email it. Silent about whether the email exists.

    Always returns without error, so the caller can give the same message
    regardless of whether an account was found.
    """
    user = (
        await session.execute(select(User).where(User.email == user_email))
    ).scalar_one_or_none()

    if user is None:
        # No account: do nothing, but do not reveal that.
        await audit.record(
            session,
            action="auth.password_reset.requested_unknown",
            entity_type="user",
            after={"email_attempted": user_email},
        )
        return

    # Raw token goes in the email; only its hash is stored.
    raw_token = secrets.token_urlsafe(32)
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash(raw_token),
            expires_at=datetime.now(UTC) + TOKEN_TTL,
        )
    )
    await session.flush()

    settings = get_settings()
    link = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
    email.send(
        to=user.email,
        subject="Reset your SS Tuitions password",
        body_text=(
            f"Dear {user.full_name},\n\n"
            "We received a request to reset your SS Tuitions password.\n\n"
            f"Open this link to set a new one (valid for one hour):\n{link}\n\n"
            "If you did not request this, you can ignore this email — your "
            "password stays unchanged.\n\nSS Tuitions"
        ),
    )
    await audit.record(
        session,
        action="auth.password_reset.requested",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
    )


async def complete_reset(
    session: AsyncSession, *, token: str, new_password: str
) -> None:
    """Consume a token and set the new password. Revokes existing sessions."""
    if len(new_password) < 10:
        raise ResetError("Password must be at least 10 characters")

    row = (
        await session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == _hash(token)
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise ResetError(
            "This reset link is invalid or has expired. Please request a new one."
        )

    user = (
        await session.execute(select(User).where(User.id == row.user_id))
    ).scalar_one_or_none()
    if user is None:
        raise ResetError("That account no longer exists")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.failed_login_count = 0
    user.locked_until = None
    row.used_at = now

    # Anyone who had a live session is signed out — the reset may be happening
    # because the old password was compromised.
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    await audit.record(
        session,
        action="auth.password_reset.completed",
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        after={"sessions_revoked": True},
    )
