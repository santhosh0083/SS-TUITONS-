"""AI tutor endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import tutor
from app.ai.provider import is_configured
from app.ai.tutor import DailyLimitReached, TutorError, TutorUnavailable
from app.auth.dependencies import CurrentUser
from app.db.session import get_db

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


class TutorStatus(BaseModel):
    available: bool
    reason: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    subject: str | None = Field(default=None, max_length=60)


class AskResponse(BaseModel):
    answer: str
    questions_used_today: int
    daily_limit: int


class HistoryMessage(BaseModel):
    role: str
    content: str
    at: datetime


@router.get("/status", response_model=TutorStatus)
async def status_check(_user: CurrentUser) -> TutorStatus:
    """Whether the AI tutor can be used.

    The UI calls this first so it can hide the feature entirely rather than
    letting a student type a question into something that cannot answer.
    """
    if is_configured():
        return TutorStatus(available=True)
    return TutorStatus(
        available=False,
        reason="The AI tutor is not switched on yet.",
    )


@router.get("/history", response_model=list[HistoryMessage])
async def get_history(session: Db, user: CurrentUser) -> list[HistoryMessage]:
    """This student's own conversation. Scoped to them by construction."""
    try:
        ai_session = await tutor.start_or_resume_session(session, user=user)
        rows = await tutor.history(session, ai_session=ai_session)
    except TutorError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    await session.commit()
    return [HistoryMessage(**r) for r in rows]


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, session: Db, user: CurrentUser) -> AskResponse:
    """Ask the AI tutor a question.

    Identifiers are stripped from the question before it reaches the AI
    provider. The tutor guides rather than supplying finished answers.
    """
    try:
        result = await tutor.ask(
            session,
            user=user,
            question=payload.question,
            subject=payload.subject,
        )
    except TutorUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except DailyLimitReached as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except TutorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return AskResponse(**result)
