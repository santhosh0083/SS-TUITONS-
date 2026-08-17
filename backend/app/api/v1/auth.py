"""Authentication endpoints.

The refresh token travels as an httpOnly, SameSite cookie rather than in the
response body, so browser JavaScript cannot read it and an XSS bug cannot steal
a long-lived session.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, client_ip
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    TokenResponse,
    UserProfile,
)
from app.services import auth_service

router = APIRouter()
settings = get_settings()

REFRESH_COOKIE = "ss_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


def _profile(user) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        roles=sorted(r.value for r in user.role_codes),
        is_superadmin=user.is_superadmin,
        last_login_at=user.last_login_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Sign in with email and password."""
    try:
        _user, access, refresh = await auth_service.authenticate(
            session,
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=client_ip(request),
        )
    except auth_service.AccountLocked as exc:
        await session.commit()  # persist the audit entry
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except auth_service.AuthError as exc:
        await session.commit()  # persist failure count and audit entry
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    await session.commit()
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    ss_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    """Exchange a refresh token for a new access token.

    The refresh token is rotated on every call.
    """
    if not ss_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No active session"
        )

    try:
        _user, access, new_refresh = await auth_service.refresh_session(
            session,
            refresh_token=ss_refresh,
            user_agent=request.headers.get("user-agent"),
            ip_address=client_ip(request),
        )
    except auth_service.AuthError as exc:
        await session.commit()  # persist any reuse-detection revocations
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    await session.commit()
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(
        access_token=access,
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    all_devices: bool = False,
    ss_refresh: Annotated[str | None, Cookie()] = None,
) -> MessageResponse:
    """End the current session, or every session for this account."""
    await auth_service.logout(
        session,
        refresh_token=ss_refresh,
        user_id=current_user.id,
        all_devices=all_devices,
    )
    await session.commit()
    _clear_refresh_cookie(response)
    return MessageResponse(
        detail="Signed out of all devices" if all_devices else "Signed out"
    )


@router.get("/me", response_model=UserProfile)
async def me(current_user: CurrentUser) -> UserProfile:
    """The signed-in user's own profile."""
    return _profile(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> MessageResponse:
    """Change your password. All existing sessions are signed out."""
    try:
        await auth_service.change_password(
            session,
            user=current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await session.commit()
    _clear_refresh_cookie(response)
    return MessageResponse(
        detail="Password changed. Please sign in again on all devices."
    )
