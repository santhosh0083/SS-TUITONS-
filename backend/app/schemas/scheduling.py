"""Contracts for tutor assignment and class scheduling."""

import uuid
from datetime import date, time

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ClassSessionStatus, MeetingIntegrationStatus

# A real Google Meet link looks like https://meet.google.com/abc-defg-hij.
# The database enforces this too; validating here gives a better message than
# a constraint violation.
MEET_URL_PATTERN = r"^https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}(\?.*)?$"


class AssignTutorRequest(BaseModel):
    """Assign a tutor to a student for one subject.

    Creates whatever is needed underneath — a one-to-one batch, the enrolment,
    the assignment, and the parent-tutor conversation — so the owner performs
    one action rather than four.
    """

    student_id: uuid.UUID
    tutor_id: uuid.UUID
    subject_id: uuid.UUID


class AssignTutorResponse(BaseModel):
    batch_id: uuid.UUID
    batch_code: str
    assignment_id: uuid.UUID
    conversation_id: uuid.UUID | None
    conversation_note: str


class ScheduleClassRequest(BaseModel):
    batch_id: uuid.UUID
    tutor_id: uuid.UUID
    subject_id: uuid.UUID
    scheduled_date: date
    scheduled_start: time
    scheduled_end: time
    meeting_url: str | None = Field(
        default=None,
        description=(
            "A real Google Meet link created at meet.google.com. Leave empty "
            "if there is no link yet — the platform never invents one."
        ),
    )

    @field_validator("meeting_url")
    @classmethod
    def _validate_meet_url(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        import re

        v = v.strip()
        if not re.match(MEET_URL_PATTERN, v):
            raise ValueError(
                "That is not a Google Meet link. It should look like "
                "https://meet.google.com/abc-defg-hij — open meet.google.com, "
                "start a new meeting, and copy the link."
            )
        return v

    @field_validator("scheduled_end")
    @classmethod
    def _end_after_start(cls, v: time, info) -> time:
        start = info.data.get("scheduled_start")
        if start is not None and v <= start:
            raise ValueError("The class must end after it starts")
        return v


class ClassSessionOut(BaseModel):
    """A scheduled class, as seen by a student, parent, tutor or admin.

    Carries display names only. A parent never receives the tutor's email or
    phone, and a tutor never receives the parent's — those fields are not in
    this schema, so they never leave the server.
    """

    id: uuid.UUID
    batch_code: str
    subject: str
    student_name: str
    tutor_name: str
    scheduled_date: date
    scheduled_start: time
    scheduled_end: time
    status: ClassSessionStatus
    integration_status: MeetingIntegrationStatus
    meeting_url: str | None
    can_join: bool = Field(
        description="True when a link exists and the class is near enough to join"
    )
    join_hint: str | None = Field(
        default=None, description="Why joining is unavailable, in plain words"
    )
