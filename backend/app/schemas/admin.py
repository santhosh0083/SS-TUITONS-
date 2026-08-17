"""Admin analytics contracts."""

from pydantic import BaseModel, Field


class OverviewCounts(BaseModel):
    """Headline numbers for the admin dashboard.

    Every field is a real count from the database. Nothing here is estimated,
    projected, or filled in with a plausible-looking placeholder — an empty
    platform reports zeros, and the UI is responsible for saying so clearly.
    """

    students_total: int = Field(description="Students with an active account")
    students_suspended: int
    parents_total: int
    tutors_total: int

    batches_active: int
    batches_at_capacity: int = Field(
        description="Active batches with no remaining seats"
    )

    classes_today: int
    classes_upcoming_7d: int

    # Attendance rows where the student and tutor marks disagree and no admin
    # has arbitrated yet.
    attendance_discrepancies: int

    payments_pending_review: int = Field(
        description="Payment claims awaiting your verification"
    )
    invoices_overdue: int

    questions_pending_review: int = Field(
        description="AI-generated questions not yet approved"
    )


class SetupTask(BaseModel):
    """A step the owner still has to complete before the platform is usable."""

    key: str
    label: str
    done: bool
    hint: str | None = None


class AdminOverview(BaseModel):
    counts: OverviewCounts
    setup: list[SetupTask]
    is_empty: bool = Field(
        description="True when no students exist yet, so the UI shows onboarding "
        "rather than empty charts"
    )
