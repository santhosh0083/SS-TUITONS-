"""Attendance and class report endpoints."""

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_admin
from app.db.session import get_db
from app.models.enums import AttendanceMark
from app.models.identity import User
from app.services import attendance
from app.services.attendance import AttendanceError, NotPermitted

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


class RosterEntry(BaseModel):
    student_id: uuid.UUID
    student_name: str
    student_marked: AttendanceMark | None
    tutor_marked: AttendanceMark | None
    final_status: AttendanceMark | None
    has_discrepancy: bool


class TutorMarkRequest(BaseModel):
    # student_id -> mark, so the whole batch is submitted in one action
    marks: dict[uuid.UUID, AttendanceMark] = Field(min_length=1)


class StudentMarkRequest(BaseModel):
    mark: AttendanceMark = AttendanceMark.PRESENT


class DiscrepancyOut(BaseModel):
    attendance_id: uuid.UUID
    student_name: str
    scheduled_date: date
    student_marked: AttendanceMark | None
    tutor_marked: AttendanceMark | None


class ResolveRequest(BaseModel):
    final: AttendanceMark


class ClassReportRequest(BaseModel):
    topics_covered: str = Field(min_length=1, max_length=4000)
    actual_start_at: datetime
    actual_end_at: datetime
    homework_assigned: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


def _not_found(exc: NotPermitted) -> HTTPException:
    # 404 rather than 403: someone who does not teach a class should not learn
    # that it exists.
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Class not found"
    )


@router.get("/{class_session_id}/roster", response_model=list[RosterEntry])
async def get_roster(
    class_session_id: uuid.UUID, session: Db, user: CurrentUser
) -> list[RosterEntry]:
    """The students in this class and their current marks."""
    try:
        rows = await attendance.roster(
            session, user=user, class_session_id=class_session_id
        )
    except NotPermitted as exc:
        raise _not_found(exc) from exc
    return [RosterEntry(**r) for r in rows]


@router.post("/{class_session_id}/tutor-mark")
async def tutor_mark(
    class_session_id: uuid.UUID,
    payload: TutorMarkRequest,
    session: Db,
    user: CurrentUser,
) -> dict:
    """Tutor marks the batch. Does not overwrite what students recorded."""
    try:
        count = await attendance.mark_by_tutor(
            session,
            user=user,
            class_session_id=class_session_id,
            marks=payload.marks,
        )
    except NotPermitted as exc:
        raise _not_found(exc) from exc
    except AttendanceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return {"marked": count}


@router.post("/{class_session_id}/student-mark")
async def student_mark(
    class_session_id: uuid.UUID,
    payload: StudentMarkRequest,
    session: Db,
    user: CurrentUser,
) -> dict:
    """A student records their own attendance."""
    try:
        await attendance.mark_by_student(
            session,
            user=user,
            class_session_id=class_session_id,
            mark=payload.mark,
        )
    except NotPermitted as exc:
        raise _not_found(exc) from exc
    await session.commit()
    return {"status": "recorded"}


@router.post("/{class_session_id}/report", status_code=status.HTTP_201_CREATED)
async def submit_report(
    class_session_id: uuid.UUID,
    payload: ClassReportRequest,
    session: Db,
    user: CurrentUser,
) -> dict:
    """Tutor records what was actually taught, and the real timings."""
    try:
        report = await attendance.submit_class_report(
            session,
            user=user,
            class_session_id=class_session_id,
            topics_covered=payload.topics_covered,
            actual_start_at=payload.actual_start_at,
            actual_end_at=payload.actual_end_at,
            homework_assigned=payload.homework_assigned,
            notes=payload.notes,
        )
    except NotPermitted as exc:
        raise _not_found(exc) from exc
    except AttendanceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return {"id": str(report.id), "status": report.status.value}


@router.get("/discrepancies", response_model=list[DiscrepancyOut])
async def list_discrepancies(session: Db, _admin: AdminUser) -> list[DiscrepancyOut]:
    """Attendance the student and tutor disagree on."""
    rows = await attendance.discrepancies(session)
    return [DiscrepancyOut(**r) for r in rows]


@router.post("/discrepancies/{attendance_id}/resolve")
async def resolve(
    attendance_id: uuid.UUID,
    payload: ResolveRequest,
    session: Db,
    admin: AdminUser,
) -> dict:
    """The owner decides which mark stands. Recorded in the audit log."""
    try:
        await attendance.resolve_discrepancy(
            session,
            attendance_id=attendance_id,
            final=payload.final,
            actor_id=admin.id,
        )
    except AttendanceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return {"status": "resolved", "final": payload.final.value}
