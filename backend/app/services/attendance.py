"""Attendance marking and tutor class reports.

DUAL MARKING
------------
Both the student and the tutor mark attendance, into separate columns. A
database trigger reconciles them:

  both agree      -> final_status set, has_discrepancy false
  they disagree   -> tutor mark holds provisionally, has_discrepancy true
  only one marked -> final_status stays NULL

Neither party can overwrite the other, and the application does not decide the
outcome. The trigger does, so a bug here cannot silently rewrite a record the
owner may later rely on in a fee dispute.

CLASS REPORTS
-------------
Separate from attendance: what the tutor actually taught, with real start and
end times. The gap between scheduled and actual is the punctuality record.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academics import BatchStudent, TutorAssignment
from app.models.enums import (
    AttendanceMark,
    ClassReportStatus,
    ClassSessionStatus,
    EnrolmentStatus,
    RoleCode,
)
from app.models.identity import Student, Tutor, User
from app.models.scheduling import Attendance, ClassReport, ClassSession
from app.services import audit


class AttendanceError(Exception):
    """Message is safe to show the user."""


class NotPermitted(AttendanceError):
    pass


async def _tutor_owns_session(
    session: AsyncSession, *, user: User, class_session: ClassSession
) -> bool:
    tutor = (
        await session.execute(select(Tutor).where(Tutor.user_id == user.id))
    ).scalar_one_or_none()
    if tutor is None or tutor.id != class_session.tutor_id:
        return False
    # The assignment must still be live: a tutor removed from the batch cannot
    # mark attendance for it.
    live = (
        await session.execute(
            select(TutorAssignment.id).where(
                TutorAssignment.tutor_id == tutor.id,
                TutorAssignment.batch_id == class_session.batch_id,
                TutorAssignment.revoked_on.is_(None),
            )
        )
    ).scalar_one_or_none()
    return live is not None


async def _load_session(
    session: AsyncSession, class_session_id: uuid.UUID
) -> ClassSession:
    row = (
        await session.execute(
            select(ClassSession).where(ClassSession.id == class_session_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotPermitted("That class no longer exists")
    return row


async def roster(
    session: AsyncSession, *, user: User, class_session_id: uuid.UUID
) -> list[dict]:
    """Students in this class, with whatever marks exist so far."""
    class_session = await _load_session(session, class_session_id)

    is_admin = user.is_superadmin or RoleCode.ADMIN in user.role_codes
    if not is_admin and not await _tutor_owns_session(
        session, user=user, class_session=class_session
    ):
        raise NotPermitted("You do not teach this class")

    rows = (
        await session.execute(
            select(Student.id, User.full_name)
            .join(User, User.id == Student.user_id)
            .join(BatchStudent, BatchStudent.student_id == Student.id)
            .where(
                BatchStudent.batch_id == class_session.batch_id,
                BatchStudent.status == EnrolmentStatus.ACTIVE,
            )
            .order_by(User.full_name)
        )
    ).all()

    existing = {
        a.student_id: a
        for a in (
            await session.execute(
                select(Attendance).where(
                    Attendance.class_session_id == class_session_id
                )
            )
        )
        .scalars()
        .all()
    }

    out: list[dict] = []
    for student_id, name in rows:
        a = existing.get(student_id)
        out.append(
            {
                "student_id": student_id,
                "student_name": name,
                "student_marked": a.student_marked_status if a else None,
                "tutor_marked": a.tutor_marked_status if a else None,
                "final_status": a.final_status if a else None,
                "has_discrepancy": bool(a and a.has_discrepancy),
            }
        )
    return out


async def mark_by_tutor(
    session: AsyncSession,
    *,
    user: User,
    class_session_id: uuid.UUID,
    marks: dict[uuid.UUID, AttendanceMark],
) -> int:
    """Tutor marks the whole batch in one submission."""
    class_session = await _load_session(session, class_session_id)
    if not await _tutor_owns_session(session, user=user, class_session=class_session):
        raise NotPermitted("You do not teach this class")

    enrolled = set(
        (
            await session.execute(
                select(BatchStudent.student_id).where(
                    BatchStudent.batch_id == class_session.batch_id,
                    BatchStudent.status == EnrolmentStatus.ACTIVE,
                )
            )
        )
        .scalars()
        .all()
    )
    if set(marks) - enrolled:
        raise NotPermitted("That student is not in this class")

    now = datetime.now(UTC)
    for student_id, mark in marks.items():
        row = (
            await session.execute(
                select(Attendance).where(
                    Attendance.class_session_id == class_session_id,
                    Attendance.student_id == student_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = Attendance(
                class_session_id=class_session_id,
                student_id=student_id,
                has_discrepancy=False,
            )
            session.add(row)
        row.tutor_marked_status = mark
        row.tutor_marked_at = now

    await session.flush()
    await audit.record(
        session,
        action="attendance.marked_by_tutor",
        entity_type="class_session",
        entity_id=class_session_id,
        actor_user_id=user.id,
        after={"students_marked": len(marks)},
    )
    return len(marks)


async def mark_by_student(
    session: AsyncSession,
    *,
    user: User,
    class_session_id: uuid.UUID,
    mark: AttendanceMark,
) -> None:
    """A student marks their own attendance, and only their own."""
    student = (
        await session.execute(select(Student).where(Student.user_id == user.id))
    ).scalar_one_or_none()
    if student is None:
        raise NotPermitted("Only students can mark their own attendance")

    class_session = await _load_session(session, class_session_id)

    enrolled = (
        await session.execute(
            select(BatchStudent.student_id).where(
                BatchStudent.batch_id == class_session.batch_id,
                BatchStudent.student_id == student.id,
                BatchStudent.status == EnrolmentStatus.ACTIVE,
            )
        )
    ).scalar_one_or_none()
    if enrolled is None:
        raise NotPermitted("You are not in this class")

    row = (
        await session.execute(
            select(Attendance).where(
                Attendance.class_session_id == class_session_id,
                Attendance.student_id == student.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = Attendance(
            class_session_id=class_session_id,
            student_id=student.id,
            has_discrepancy=False,
        )
        session.add(row)

    row.student_marked_status = mark
    row.student_marked_at = datetime.now(UTC)
    await session.flush()


async def discrepancies(session: AsyncSession) -> list[dict]:
    """Unresolved disagreements, for the owner to arbitrate."""
    rows = (
        await session.execute(
            select(Attendance)
            .where(
                Attendance.has_discrepancy.is_(True),
                Attendance.resolved_at.is_(None),
            )
            .order_by(Attendance.created_at.desc())
        )
    ).scalars().all()

    out: list[dict] = []
    for a in rows:
        student_name = (
            await session.execute(
                select(User.full_name)
                .join(Student, Student.user_id == User.id)
                .where(Student.id == a.student_id)
            )
        ).scalar_one_or_none() or "-"
        cs = (
            await session.execute(
                select(ClassSession).where(ClassSession.id == a.class_session_id)
            )
        ).scalar_one()
        out.append(
            {
                "attendance_id": a.id,
                "student_name": student_name,
                "scheduled_date": cs.scheduled_date,
                "student_marked": a.student_marked_status,
                "tutor_marked": a.tutor_marked_status,
            }
        )
    return out


async def resolve_discrepancy(
    session: AsyncSession,
    *,
    attendance_id: uuid.UUID,
    final: AttendanceMark,
    actor_id: uuid.UUID,
) -> None:
    """The owner decides. Setting resolved_by clears the flag via the trigger."""
    row = (
        await session.execute(select(Attendance).where(Attendance.id == attendance_id))
    ).scalar_one_or_none()
    if row is None:
        raise AttendanceError("That attendance record no longer exists")

    before = {
        "student": row.student_marked_status.value
        if row.student_marked_status
        else None,
        "tutor": row.tutor_marked_status.value if row.tutor_marked_status else None,
    }
    row.final_status = final
    row.resolved_by = actor_id
    row.resolved_at = datetime.now(UTC)
    await session.flush()

    await audit.record(
        session,
        action="attendance.discrepancy_resolved",
        entity_type="attendance",
        entity_id=attendance_id,
        actor_user_id=actor_id,
        before=before,
        after={"final": final.value},
    )


# ---------------------------------------------------------------------------
# Class reports
# ---------------------------------------------------------------------------


async def submit_class_report(
    session: AsyncSession,
    *,
    user: User,
    class_session_id: uuid.UUID,
    topics_covered: str,
    actual_start_at: datetime,
    actual_end_at: datetime,
    homework_assigned: str | None,
    notes: str | None,
) -> ClassReport:
    """The tutor records what they actually taught."""
    class_session = await _load_session(session, class_session_id)
    if not await _tutor_owns_session(session, user=user, class_session=class_session):
        raise NotPermitted("You do not teach this class")

    if not topics_covered.strip():
        raise AttendanceError("Please say what you covered")
    if actual_end_at <= actual_start_at:
        raise AttendanceError("The class must end after it starts")

    report = (
        await session.execute(
            select(ClassReport).where(ClassReport.class_session_id == class_session_id)
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if report is None:
        report = ClassReport(
            class_session_id=class_session_id,
            tutor_id=class_session.tutor_id,
            subject_id=class_session.subject_id,
            status=ClassReportStatus.SUBMITTED,
        )
        session.add(report)
    elif report.status == ClassReportStatus.REVIEWED:
        raise AttendanceError(
            "This report has already been reviewed and cannot be changed"
        )

    report.topics_covered = topics_covered.strip()
    report.actual_start_at = actual_start_at
    report.actual_end_at = actual_end_at
    report.homework_assigned = homework_assigned
    report.notes = notes
    report.submitted_at = now
    report.status = ClassReportStatus.SUBMITTED

    # Submitting the report is what marks the class taught.
    class_session.status = ClassSessionStatus.COMPLETED

    await session.flush()
    await audit.record(
        session,
        action="class_report.submitted",
        entity_type="class_report",
        entity_id=report.id,
        actor_user_id=user.id,
    )
    return report
