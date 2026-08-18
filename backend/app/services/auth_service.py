"""Authentication: login, session refresh, logout, password change.

Three security properties are deliberate here and worth stating, because each
would be easy to lose in a later refactor:

1. **No user enumeration.** A wrong email and a wrong password take the same
   path, cost the same time, and return the same message. Otherwise an attacker
   can discover which parents and students have accounts.

2. **Account lockout.** Repeated failures lock the account for a cooldown. This
   is the brute-force defence that works without Redis; per-IP rate limiting is
   added on top later.

3. **Refresh-token rotation with reuse detection.** Each refresh issues a new
   token and revokes the old one. If a already-revoked token is presented, that
   means it was stolen and replayed, so every session for that user is revoked
   immediately.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    token_subject,
    verify_password,
)
from app.models.enums import UserStatus
from app.models.identity import RefreshToken, User
from app.services import audit

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

# Hashing this on a missing-user login keeps the timing indistinguishable from
# a real user with a wrong password.
_DUMMY_HASH = hash_password("timing-equalisation-placeholder")


class AuthError(Exception):
    """Authentication failed. The message is safe to show a client."""


class AccountLocked(AuthError):
    pass


class InactiveAccount(AuthError):
    pass


GENERIC_FAILURE = "Incorrect email or password"


async def _load_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = (
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _load_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


def _is_locked(user: User, now: datetime) -> bool:
    return user.locked_until is not None and user.locked_until > now


async def _register_failure(session: AsyncSession, user: User, now: datetime) -> None:
    user.failed_login_count += 1
    if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
        user.locked_until = now + LOCKOUT_DURATION
        user.failed_login_count = 0
        logger.warning("Account %s locked after repeated failed logins", user.id)


async def _issue_session(
    session: AsyncSession,
    user: User,
    *,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[str, str]:
    """Create an access/refresh pair and persist the refresh token's hash."""
    access = create_access_token(user.id, roles=[r.value for r in user.role_codes])
    refresh = create_refresh_token(user.id)

    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_ttl_days),
            user_agent=(user_agent or "")[:400] or None,
            ip_address=ip_address,
        )
    )
    return access, refresh


async def authenticate(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, str, str]:
    """Verify credentials and open a session.

    Returns (user, access_token, refresh_token).
    """
    now = datetime.now(UTC)
    user = await _load_user_by_email(session, email)

    if user is None:
        # Spend the same time as a real verification so the response time does
        # not reveal whether the account exists.
        verify_password(password, _DUMMY_HASH)
        await audit.record(
            session,
            action=audit.LOGIN_FAILED,
            entity_type="user",
            after={"email_attempted": email, "reason": "no_such_user"},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthError(GENERIC_FAILURE)

    if _is_locked(user, now):
        await audit.record(
            session,
            action=audit.LOGIN_BLOCKED_LOCKED,
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AccountLocked(
            "Account temporarily locked after repeated failed attempts. "
            "Try again in a few minutes."
        )

    if not verify_password(password, user.password_hash):
        await _register_failure(session, user, now)
        await audit.record(
            session,
            action=audit.LOGIN_FAILED,
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            after={"reason": "bad_password"},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthError(GENERIC_FAILURE)

    if user.status != UserStatus.ACTIVE:
        await audit.record(
            session,
            action=audit.LOGIN_FAILED,
            entity_type="user",
            entity_id=user.id,
            actor_user_id=user.id,
            after={"reason": f"status_{user.status.value}"},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise InactiveAccount(
            "This account is not active. Please contact SS Tuitions."
        )

    # Success: clear failure state and transparently upgrade an old hash.
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    access, refresh = await _issue_session(
        session, user, user_agent=user_agent, ip_address=ip_address
    )
    await audit.record(
        session,
        action=audit.LOGIN_SUCCEEDED,
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user, access, refresh


async def refresh_session(
    session: AsyncSession,
    *,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, str, str]:
    """Rotate a refresh token.

    Presenting an already-revoked token means it leaked and is being replayed,
    so every session belonging to that user is revoked.
    """
    try:
        payload = decode_token(refresh_token, "refresh")
        user_id = token_subject(payload)
    except TokenError as exc:
        raise AuthError("Session expired. Please sign in again.") from exc

    now = datetime.now(UTC)
    token_hash = hash_refresh_token(refresh_token)

    stored = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
    ).scalar_one_or_none()

    if stored is None:
        raise AuthError("Session expired. Please sign in again.")

    if stored.revoked_at is not None:
        # Replay of a rotated token. Treat every session as compromised.
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == stored.user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await audit.record(
            session,
            action=audit.TOKEN_REUSE_DETECTED,
            entity_type="user",
            entity_id=stored.user_id,
            actor_user_id=stored.user_id,
            after={"all_sessions_revoked": True},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.warning(
            "Refresh token reuse detected for user %s; all sessions revoked",
            stored.user_id,
        )
        raise AuthError("Session expired. Please sign in again.")

    if stored.expires_at <= now:
        raise AuthError("Session expired. Please sign in again.")

    user = await _load_user_by_id(session, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthError("Session expired. Please sign in again.")

    # Rotate: revoke the presented token, issue a fresh pair.
    stored.revoked_at = now
    access, new_refresh = await _issue_session(
        session, user, user_agent=user_agent, ip_address=ip_address
    )
    await audit.record(
        session,
        action=audit.TOKEN_REFRESHED,
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user, access, new_refresh


async def logout(
    session: AsyncSession,
    *,
    refresh_token: str | None,
    user_id: uuid.UUID | None = None,
    all_devices: bool = False,
) -> None:
    """Revoke the current session, or every session for the user."""
    now = datetime.now(UTC)

    if all_devices and user_id is not None:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
    elif refresh_token:
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == hash_refresh_token(refresh_token),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    await audit.record(
        session,
        action=audit.LOGOUT,
        entity_type="user",
        entity_id=user_id,
        actor_user_id=user_id,
        after={"all_devices": all_devices},
    )


async def change_password(
    session: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Change a password and revoke every existing session.

    Revoking sessions is the point: if the password is being changed because it
    was compromised, leaving old sessions alive defeats the exercise.
    """
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect")

    if verify_password(new_password, user.password_hash):
        raise AuthError("New password must be different from the current one")

    user.password_hash = hash_password(new_password)
    # First-login / forced change is now satisfied.
    user.must_change_password = False

    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await audit.record(
        session,
        action=audit.PASSWORD_CHANGED,
        entity_type="user",
        entity_id=user.id,
        actor_user_id=user.id,
        after={"sessions_revoked": True},
    )
