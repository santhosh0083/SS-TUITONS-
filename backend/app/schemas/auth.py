"""Request and response contracts for authentication."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """The refresh token is NOT included here.

    It is set as an httpOnly cookie so browser JavaScript cannot read it, which
    limits what an XSS bug can steal.
    """

    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth scheme name, not a secret
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None
    roles: list[str]
    is_superadmin: bool
    must_change_password: bool
    last_login_at: datetime | None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class MessageResponse(BaseModel):
    detail: str
