"""Tutor assignment and class scheduling.

The owner's mental model is "assign a tutor to a student for a subject". The
schema underneath needs a course, a batch, an enrolment and an assignment. This
module does that work so the owner performs one action, not four.

One-to-one tuition is a batch with capacity 1 — the same scheduling,
attendance and billing path as a group, with no parallel system to maintain.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academics import (
    Batch,
    BatchStudent,
    Course,
    Exam,
    Subject,
    TutorAssignment,
)
from app.models.enums import (
    ClassMode,
    ClassSessionStatus,
    EnrolmentStatus,
    MeetingIntegrationStatus,
    RoleCode,
)
from app.models.identity import Parent, Student, StudentParent, Tutor, User
from app.models.scheduling import ClassSession
from app.schemas.scheduling import ClassSessionOut
from app.services import audit, messaging

# A class becomes joinable shortly before it starts and stays joinable a while
# after, so a student arriving late is not locked out.
JOIN_OPENS_BEFORE = timedelta(minutes=15)
JOIN_CLOSES_AFTER = timedelta(minutes=30)


class SchedulingError(Exception):
    """Message is safe to show an admin."""


async def assign_tutor(
    session: AsyncSession,
    *,
    student_id: uuid.UUID,
    tutor_id: uuid.UUID,
    subject_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> dict:
    """Assign a tutor to a student for one subject.

    Creates the one-to-one batch and enrolment if they do not exist, then the
    assignment, then the parent-tutor conversation.
    """
    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        raise SchedulingError("That student no longer exists")

    tutor = (
        await session.execute(select(Tutor).where(Tutor.id == tutor_id))
    ).scalar_one_or_none()
    if tutor is None:
        raise SchedulingError("That tutor no longer exists")

    subject = (
        await session.execute(select(Subject).where(Subject.id == subject_id))
    ).scalar_one_or_none()
    if subject is None:
        raise SchedulingError("That subject no longer exists")

    batch_code = f"1-1-{student.admission_no}-{subject.code}"

    batch = (
        await session.execute(select(Batch).where(Batch.code == batch_code))
    ).scalar_one_or_none()

    if batch is None:
        course = await _one_to_one_course(session, student=student, subject=subject)
        batch = Batch(
            code=batch_code,
            course_id=course.id,
            capacity=1,
            start_date=date.today(),
            is_active=True,
        )
        session.add(batch)
        await session.flush()

    enrolled = (
        await session.execute(
            select(BatchStudent).where(
                BatchStudent.batch_id == batch.id,
                BatchStudent.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if enrolled is None:
        session.add(
            BatchStudent(
                batch_id=batch.id,
                student_id=student_id,
                enrolled_on=date.today(),
                status=EnrolmentStatus.ACTIVE,
            )
        )
        await session.flush()

    existing = (
        await session.execute(
            select(TutorAssignment).where(
                TutorAssignment.tutor_id == tutor_id,
                TutorAssignment.batch_id == batch.id,
                TutorAssignment.subject_id == subject_id,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        if existing.revoked_on is None:
            raise SchedulingError(
                "That tutor is already assigned to this student for this subject"
            )
        existing.revoked_on = None  # re-activate rather than duplicate
        assignment = existing
    else:
        assignment = TutorAssignment(
            tutor_id=tutor_id,
            batch_id=batch.id,
            subject_id=subject_id,
            assigned_on=date.today(),
        )
        session.add(assignment)
    await session.flush()

    # A conversation needs at least one parent to talk to.
    has_parent = (
        await session.execute(
            select(StudentParent.parent_id)
            .where(StudentParent.student_id == student_id)
            .limit(1)
        )
    ).scalar_one_or_none()

    conversation_id: uuid.UUID | None = None
    if has_parent:
        conversation = await messaging.get_or_create_conversation(
            session,
            student_id=student_id,
            tutor_id=tutor_id,
            subject_line=subject.name,
        )
        conversation_id = conversation.id
        note = "A private conversation between the parent and tutor is ready."
    else:
        note = (
            "No parent is linked to this student, so no conversation was "
            "created. Link a parent to enable messaging."
        )

    await audit.record(
        session,
        action="tutor.assigned",
        entity_type="tutor_assignment",
        entity_id=assignment.id,
        actor_user_id=actor_id,
        after={
            "student_id": str(student_id),
            "tutor_id": str(tutor_id),
            "subject": subject.code,
        },
    )

    return {
        "batch_id": batch.id,
        "batch_code": batch.code,
        "assignment_id": assignment.id,
        "conversation_id": conversation_id,
        "conversation_note": note,
    }


async def _one_to_one_course(
    session: AsyncSession, *, student: Student, subject: Subject
) -> Course:
    """Find or create the one-to-one course for this grade and subject."""
    name = f"One-to-One · Grade {student.grade.value} · {subject.name}"
    course = (
        await session.execute(select(Course).where(Course.name == name))
    ).scalar_one_or_none()
    if course is not None:
        return course

    exam_id = student.target_exam_id
    if exam_id is None:
        # Courses require an exam. Fall back to the board exam rather than
        # inventing a competitive target the student has not chosen.
        exam_id = (
            await session.execute(select(Exam.id).where(Exam.code == "CBSE"))
        ).scalar_one_or_none()
        if exam_id is None:
            exam_id = (await session.execute(select(Exam.id).limit(1))).scalar_one()

    course = Course(
        name=name,
        exam_id=exam_id,
        grade=student.grade,
        mode=ClassMode.ONE_TO_ONE,
        max_batch_size=1,
        is_active=True,
    )
    session.add(course)
    await session.flush()
    return course


async def schedule_class(
    session: AsyncSession,
    *,
    batch_id: uuid.UUID,
    tutor_id: uuid.UUID,
    subject_id: uuid.UUID,
    scheduled_date: date,
    scheduled_start,
    scheduled_end,
    meeting_url: str | None,
    actor_id: uuid.UUID,
) -> ClassSession:
    """Create a class session, with or without a meeting link.

    A link is stored only when a person supplies a real one. With no link the
    session is MANUAL-less: integration_status stays NOT_CONFIGURED and
    meeting_url stays NULL, which the database also enforces.
    """
    integration_status = (
        MeetingIntegrationStatus.MANUAL
        if meeting_url
        else MeetingIntegrationStatus.NOT_CONFIGURED
    )

    session_row = ClassSession(
        batch_id=batch_id,
        tutor_id=tutor_id,
        subject_id=subject_id,
        scheduled_date=scheduled_date,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status=ClassSessionStatus.SCHEDULED,
        integration_status=integration_status,
        meeting_url=meeting_url,
        created_by=actor_id,
    )
    session.add(session_row)
    await session.flush()

    await audit.record(
        session,
        action="class.scheduled",
        entity_type="class_session",
        entity_id=session_row.id,
        actor_user_id=actor_id,
        after={
            "date": scheduled_date.isoformat(),
            "has_link": meeting_url is not None,
        },
    )
    return session_row


def _join_state(
    row: ClassSession, now: datetime
) -> tuple[bool, str | None]:
    """Whether the JOIN button should work, and if not, why."""
    if row.status == ClassSessionStatus.CANCELLED:
        return False, "This class was cancelled."
    if not row.meeting_url:
        return False, "The class link has not been added yet."

    start = datetime.combine(row.scheduled_date, row.scheduled_start, tzinfo=UTC)
    end = datetime.combine(row.scheduled_date, row.scheduled_end, tzinfo=UTC)

    if now < start - JOIN_OPENS_BEFORE:
        return False, f"Opens at {(start - JOIN_OPENS_BEFORE).strftime('%I:%M %p')}."
    if now > end + JOIN_CLOSES_AFTER:
        return False, "This class has finished."
    return True, None


async def list_classes_for_user(
    session: AsyncSession, *, user: User, days_ahead: int = 14
) -> list[ClassSessionOut]:
    """Upcoming classes this user is entitled to see.

    Scoping mirrors the visibility layer: a tutor sees classes they teach, a
    parent sees their children's, a student sees their own, an admin sees all.
    """
    roles = user.role_codes
    today = date.today()
    horizon = today + timedelta(days=days_ahead)

    stmt = (
        select(ClassSession)
        .where(
            ClassSession.scheduled_date >= today,
            ClassSession.scheduled_date <= horizon,
            ClassSession.status != ClassSessionStatus.CANCELLED,
        )
        .order_by(ClassSession.scheduled_date, ClassSession.scheduled_start)
    )

    if user.is_superadmin or RoleCode.ADMIN in roles:
        pass
    elif RoleCode.TUTOR in roles:
        stmt = stmt.join(Tutor, Tutor.id == ClassSession.tutor_id).where(
            Tutor.user_id == user.id
        )
    elif RoleCode.PARENT in roles:
        child_ids = (
            select(StudentParent.student_id)
            .join(Parent, Parent.id == StudentParent.parent_id)
            .where(Parent.user_id == user.id)
        )
        stmt = stmt.join(
            BatchStudent, BatchStudent.batch_id == ClassSession.batch_id
        ).where(BatchStudent.student_id.in_(child_ids))
    elif RoleCode.STUDENT in roles:
        own = select(Student.id).where(Student.user_id == user.id)
        stmt = stmt.join(
            BatchStudent, BatchStudent.batch_id == ClassSession.batch_id
        ).where(BatchStudent.student_id.in_(own))
    else:
        return []

    rows = (await session.execute(stmt)).scalars().unique().all()
    now = datetime.now(UTC)

    out: list[ClassSessionOut] = []
    for row in rows:
        batch_code = (
            await session.execute(select(Batch.code).where(Batch.id == row.batch_id))
        ).scalar_one()
        subject_name = (
            await session.execute(
                select(Subject.name).where(Subject.id == row.subject_id)
            )
        ).scalar_one()
        tutor_name = (
            await session.execute(
                select(User.full_name)
                .join(Tutor, Tutor.user_id == User.id)
                .where(Tutor.id == row.tutor_id)
            )
        ).scalar_one()
        student_name = (
            await session.execute(
                select(User.full_name)
                .join(Student, Student.user_id == User.id)
                .join(BatchStudent, BatchStudent.student_id == Student.id)
                .where(
                    BatchStudent.batch_id == row.batch_id,
                    BatchStudent.status == EnrolmentStatus.ACTIVE,
                )
                .limit(1)
            )
        ).scalar_one_or_none() or "—"

        can_join, hint = _join_state(row, now)
        out.append(
            ClassSessionOut(
                id=row.id,
                batch_code=batch_code,
                subject=subject_name,
                student_name=student_name,
                tutor_name=tutor_name,
                scheduled_date=row.scheduled_date,
                scheduled_start=row.scheduled_start,
                scheduled_end=row.scheduled_end,
                status=row.status,
                integration_status=row.integration_status,
                # The link is only ever returned to someone already scoped in
                # above, and only when the class is actually joinable.
                meeting_url=row.meeting_url if can_join else None,
                can_join=can_join,
                join_hint=hint,
            )
        )
    return out
