"""Assignment and class scheduling endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_admin
from app.db.session import get_db
from app.models.identity import User
from app.schemas.scheduling import (
    AssignTutorRequest,
    AssignTutorResponse,
    ClassSessionOut,
    ScheduleClassRequest,
)
from app.services import scheduling
from app.services.scheduling import SchedulingError

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.post(
    "/assignments",
    response_model=AssignTutorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_tutor(
    payload: AssignTutorRequest, session: Db, admin: AdminUser
) -> AssignTutorResponse:
    """Assign a tutor to a student for one subject.

    Creates the one-to-one batch, enrolment, assignment and the private
    parent-tutor conversation in a single action.
    """
    try:
        result = await scheduling.assign_tutor(
            session,
            student_id=payload.student_id,
            tutor_id=payload.tutor_id,
            subject_id=payload.subject_id,
            actor_id=admin.id,
        )
    except SchedulingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return AssignTutorResponse(**result)


@router.post(
    "/classes", response_model=ClassSessionOut, status_code=status.HTTP_201_CREATED
)
async def schedule_class(
    payload: ScheduleClassRequest, session: Db, admin: AdminUser
) -> ClassSessionOut:
    """Schedule a class.

    `meeting_url` must be a real Google Meet link or omitted entirely. The
    platform never generates one; the database independently rejects a link
    that is not a genuine Meet URL.
    """
    try:
        await scheduling.schedule_class(
            session,
            batch_id=payload.batch_id,
            tutor_id=payload.tutor_id,
            subject_id=payload.subject_id,
            scheduled_date=payload.scheduled_date,
            scheduled_start=payload.scheduled_start,
            scheduled_end=payload.scheduled_end,
            meeting_url=payload.meeting_url,
            actor_id=admin.id,
        )
    except SchedulingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()

    classes = await scheduling.list_classes_for_user(session, user=admin)
    latest = next(
        (
            c
            for c in classes
            if c.scheduled_date == payload.scheduled_date
            and c.scheduled_start == payload.scheduled_start
        ),
        None,
    )
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The class was created but could not be read back.",
        )
    return latest


@router.get("/classes/mine", response_model=list[ClassSessionOut])
async def my_classes(session: Db, user: CurrentUser) -> list[ClassSessionOut]:
    """Upcoming classes for the signed-in user.

    Tutors see classes they teach; parents see their children's; students see
    their own; admins see all. The meeting link is included only when the class
    is actually joinable.
    """
    return await scheduling.list_classes_for_user(session, user=user)
