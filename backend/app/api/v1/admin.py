"""Admin endpoints. Every route here requires the ADMIN role."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.db.session import get_db
from app.models.identity import User
from app.schemas.admin import AdminOverview
from app.services import admin_analytics

router = APIRouter()


@router.get("/overview", response_model=AdminOverview)
async def overview(
    session: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> AdminOverview:
    """Headline counts and the remaining setup steps.

    All figures are live aggregates. An empty platform reports zeros rather
    than sample data.
    """
    return await admin_analytics.build_overview(session)
