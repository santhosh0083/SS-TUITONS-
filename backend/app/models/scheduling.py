"""Class sessions, tutor class reports, and dual-marked attendance."""

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AttendanceMark,
    ClassReportStatus,
    ClassSessionStatus,
    MeetingIntegrationStatus,
)
from app.models.types import pg_enum


class ClassSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A scheduled class.

    `meeting_url` stays NULL while `integration_status` is NOT_CONFIGURED. No
    placeholder or randomly generated meeting link is ever written — the UI
    shows "link not yet configured" instead (spec section 42).
    """

    __tablename__ = "class_sessions"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tutor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scheduled_start: Mapped[time] = mapped_column(Time, nullable=False)
    scheduled_end: Mapped[time] = mapped_column(Time, nullable=False)

    status: Mapped[ClassSessionStatus] = mapped_column(
        pg_enum(ClassSessionStatus, "class_session_status"),
        nullable=False,
        default=ClassSessionStatus.SCHEDULED,
    )

    # ---- Google Meet wiring (inert until a Workspace account exists) ----
    integration_status: Mapped[MeetingIntegrationStatus] = mapped_column(
        pg_enum(MeetingIntegrationStatus, "meeting_integration_status"),
        nullable=False,
        default=MeetingIntegrationStatus.NOT_CONFIGURED,
    )
    meeting_url: Mapped[str | None] = mapped_column(String(500))
    google_event_id: Mapped[str | None] = mapped_column(String(200))
    google_conference_id: Mapped[str | None] = mapped_column(String(200))

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    report: Mapped["ClassReport | None"] = relationship(
        back_populates="session", uselist=False
    )
    attendance: Mapped[list["Attendance"]] = relationship(back_populates="session")


class ClassReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The tutor's record of what they actually taught.

    `actual_start_at` / `actual_end_at` are stored separately from the session's
    scheduled times, so a class booked 19:00-20:00 but taught 19:12-20:05
    records the truth. That gap is also the punctuality record.
    """

    __tablename__ = "class_reports"

    class_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    tutor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )

    topics_covered: Mapped[str] = mapped_column(Text, nullable=False)
    actual_start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    actual_end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    homework_assigned: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    status: Mapped[ClassReportStatus] = mapped_column(
        pg_enum(ClassReportStatus, "class_report_status"),
        nullable=False,
        default=ClassReportStatus.DRAFT,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Owner review, then optional release to parents.
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shared_with_parents_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    session: Mapped[ClassSession] = relationship(back_populates="report")


class Attendance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Dual-marked attendance.

    The student's mark and the tutor's mark are stored in separate columns.
    Neither overwrites the other. When they disagree, `has_discrepancy` is set
    and the row surfaces in the owner's review queue.
    """

    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("class_session_id", "student_id"),)

    class_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_marked_status: Mapped[AttendanceMark | None] = mapped_column(
        pg_enum(AttendanceMark, "attendance_mark")
    )
    student_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tutor_marked_status: Mapped[AttendanceMark | None] = mapped_column(
        pg_enum(AttendanceMark, "attendance_mark")
    )
    tutor_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Resolution: marks agree -> that value. Marks differ -> the tutor's mark
    # holds provisionally and has_discrepancy is raised for the owner.
    final_status: Mapped[AttendanceMark | None] = mapped_column(
        pg_enum(AttendanceMark, "attendance_mark")
    )
    has_discrepancy: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[ClassSession] = relationship(back_populates="attendance")
