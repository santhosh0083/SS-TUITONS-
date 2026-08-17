"""Admin dashboard analytics.

All counts are real aggregates. When the platform is empty, this returns zeros
and `is_empty=True` so the UI can show onboarding steps instead of a wall of
meaningless charts.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academics import Batch, BatchStudent, Course, TutorAssignment
from app.models.assessment import Question
from app.models.content import ContentItem
from app.models.enums import (
    ClassSessionStatus,
    EnrolmentStatus,
    InvoiceStatus,
    ReviewStatus,
    SubmissionStatus,
    UserStatus,
)
from app.models.finance import Invoice, PaymentSubmission
from app.models.identity import Parent, Student, Tutor, User
from app.models.scheduling import Attendance, ClassSession
from app.schemas.admin import AdminOverview, OverviewCounts, SetupTask


async def _scalar(session: AsyncSession, stmt: Select) -> int:
    return (await session.execute(stmt)).scalar_one() or 0


async def build_overview(session: AsyncSession) -> AdminOverview:
    today: date = datetime.now(UTC).date()
    week_ahead = today + timedelta(days=7)

    students_total = await _scalar(
        session,
        select(func.count())
        .select_from(Student)
        .join(User, User.id == Student.user_id)
        .where(User.status == UserStatus.ACTIVE),
    )
    students_suspended = await _scalar(
        session,
        select(func.count())
        .select_from(Student)
        .join(User, User.id == Student.user_id)
        .where(User.status == UserStatus.SUSPENDED),
    )
    parents_total = await _scalar(session, select(func.count()).select_from(Parent))
    tutors_total = await _scalar(session, select(func.count()).select_from(Tutor))

    batches_active = await _scalar(
        session,
        select(func.count()).select_from(Batch).where(Batch.is_active.is_(True)),
    )

    # Batches whose active enrolment has reached capacity. Done as one grouped
    # query rather than counting per batch in a loop.
    full_batches = (
        select(BatchStudent.batch_id)
        .join(Batch, Batch.id == BatchStudent.batch_id)
        .where(
            Batch.is_active.is_(True),
            BatchStudent.status == EnrolmentStatus.ACTIVE,
        )
        .group_by(BatchStudent.batch_id, Batch.capacity)
        .having(func.count(BatchStudent.student_id) >= Batch.capacity)
        .subquery()
    )
    batches_at_capacity = await _scalar(
        session, select(func.count()).select_from(full_batches)
    )

    classes_today = await _scalar(
        session,
        select(func.count())
        .select_from(ClassSession)
        .where(
            ClassSession.scheduled_date == today,
            ClassSession.status != ClassSessionStatus.CANCELLED,
        ),
    )
    classes_upcoming = await _scalar(
        session,
        select(func.count())
        .select_from(ClassSession)
        .where(
            ClassSession.scheduled_date > today,
            ClassSession.scheduled_date <= week_ahead,
            ClassSession.status != ClassSessionStatus.CANCELLED,
        ),
    )

    attendance_discrepancies = await _scalar(
        session,
        select(func.count())
        .select_from(Attendance)
        .where(
            Attendance.has_discrepancy.is_(True),
            Attendance.resolved_at.is_(None),
        ),
    )

    payments_pending = await _scalar(
        session,
        select(func.count())
        .select_from(PaymentSubmission)
        .where(PaymentSubmission.status == SubmissionStatus.PENDING),
    )
    invoices_overdue = await _scalar(
        session,
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.status == InvoiceStatus.OVERDUE),
    )

    questions_pending = await _scalar(
        session,
        select(func.count())
        .select_from(Question)
        .where(Question.review_status == ReviewStatus.PENDING_REVIEW),
    )

    # ---- Setup checklist: what still has to exist before the platform works ----
    courses_exist = await _scalar(session, select(func.count()).select_from(Course)) > 0
    assignments_exist = (
        await _scalar(session, select(func.count()).select_from(TutorAssignment)) > 0
    )
    content_exists = (
        await _scalar(session, select(func.count()).select_from(ContentItem)) > 0
    )

    setup = [
        SetupTask(
            key="tutors",
            label="Add your first tutor",
            done=tutors_total > 0,
            hint="Tutors teach batches and mark attendance.",
        ),
        SetupTask(
            key="courses",
            label="Create a course",
            done=courses_exist,
            hint="A course sets the grade, exam and subjects.",
        ),
        SetupTask(
            key="batches",
            label="Create a batch",
            done=batches_active > 0,
            hint="One-to-one tuition is a batch with capacity 1.",
        ),
        SetupTask(
            key="assignments",
            label="Assign a tutor to a batch",
            done=assignments_exist,
            hint="This is what gives a tutor access to their students.",
        ),
        SetupTask(
            key="students",
            label="Enrol your first student",
            done=students_total > 0,
            hint="Students and their parents get sign-in accounts.",
        ),
        SetupTask(
            key="content",
            label="Upload study material",
            done=content_exists,
            hint="Worksheets, notes and previous year papers.",
        ),
    ]

    return AdminOverview(
        counts=OverviewCounts(
            students_total=students_total,
            students_suspended=students_suspended,
            parents_total=parents_total,
            tutors_total=tutors_total,
            batches_active=batches_active,
            batches_at_capacity=batches_at_capacity,
            classes_today=classes_today,
            classes_upcoming_7d=classes_upcoming,
            attendance_discrepancies=attendance_discrepancies,
            payments_pending_review=payments_pending,
            invoices_overdue=invoices_overdue,
            questions_pending_review=questions_pending,
        ),
        setup=setup,
        is_empty=students_total == 0 and tutors_total == 0,
    )
