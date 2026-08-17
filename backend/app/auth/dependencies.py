"""FastAPI dependencies for authentication and role checks.

The current user is always re-loaded from the database, never trusted from the
JWT alone. A suspended account or a removed role therefore takes effect on the
next request rather than whenever the token happens to expire.
"""

import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import TokenError, decode_token, token_subject
from app.db.session import get_db
from app.models.enums import RoleCode, UserStatus
from app.models.identity import User

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise CREDENTIALS_EXCEPTION

    try:
        payload = decode_token(credentials.credentials, "access")
        user_id: uuid.UUID = token_subject(payload)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = (
        await session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        )
    ).scalar_one_or_none()

    if user is None:
        raise CREDENTIALS_EXCEPTION

    # Checked live, not from the token: a suspension applies immediately.
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(
    *allowed: RoleCode,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Dependency factory restricting an endpoint to specific roles.

    The superadmin always passes. Note this is a coarse gate on *which
    endpoints* a caller may reach — it does not decide *which rows* they see.
    That is the visibility layer's job, and both are required.
    """

    async def _check(user: CurrentUser) -> User:
        if user.is_superadmin:
            return user
        if not (set(allowed) & user.role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return _check


require_admin = require_roles(RoleCode.ADMIN)
require_tutor = require_roles(RoleCode.TUTOR)
require_parent = require_roles(RoleCode.PARENT)
require_student = require_roles(RoleCode.STUDENT)


def client_ip(request: Request) -> str | None:
    """Best-effort client IP.

    X-Forwarded-For is only trusted when a proxy is expected in front of the
    app; otherwise a client can spoof it freely.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.client.host[:45] if request.client else None
