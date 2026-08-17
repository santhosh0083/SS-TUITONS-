"""Exams, subjects, courses, batches, and tutor assignments.

`TutorAssignment` is the authorization backbone for the entire tutor role: a
tutor's students, classes, and permitted parent conversations all resolve
through it. Deleting a row revokes that access immediately.
"""

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BillingCycle, ClassMode, EnrolmentStatus, Grade
from app.models.types import pg_enum


class Exam(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exams"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subjects"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    grade: Mapped[Grade] = mapped_column(pg_enum(Grade, "grade"), nullable=False)
    mode: Mapped[ClassMode] = mapped_column(
        pg_enum(ClassMode, "class_mode"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)

    # NULL means "not yet supplied by the owner" — see docs/INTAKE.md Group D.
    duration_months: Mapped[int | None] = mapped_column(Integer)
    classes_per_week: Mapped[int | None] = mapped_column(Integer)
    class_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    max_batch_size: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    subjects: Mapped[list["CourseSubject"]] = relationship(back_populates="course")


class CourseSubject(TimestampMixin, Base):
    __tablename__ = "course_subjects"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    course: Mapped[Course] = relationship(back_populates="subjects")
    subject: Mapped[Subject] = relationship(lazy="joined")


class Batch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A teaching group, e.g. JEE-12-A.

    One-to-one tutoring is a batch with capacity = 1. This keeps a single
    scheduling, attendance, and billing path rather than two parallel systems.
    """

    __tablename__ = "batches"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course: Mapped[Course] = relationship(lazy="joined")
    students: Mapped[list["BatchStudent"]] = relationship(back_populates="batch")


class BatchStudent(TimestampMixin, Base):
    """Enrolment. `left_on` preserves history rather than deleting the row."""

    __tablename__ = "batch_students"
    __table_args__ = (UniqueConstraint("batch_id", "student_id"),)

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enrolled_on: Mapped[date] = mapped_column(Date, nullable=False)
    left_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[EnrolmentStatus] = mapped_column(
        pg_enum(EnrolmentStatus, "enrolment_status"),
        nullable=False,
        default=EnrolmentStatus.ACTIVE,
    )

    batch: Mapped[Batch] = relationship(back_populates="students")


class TutorAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Which tutor teaches which subject in which batch.

    THE authorization source for the tutor role. Every tutor-scoped query
    resolves through this table.
    """

    __tablename__ = "tutor_assignments"
    __table_args__ = (UniqueConstraint("tutor_id", "batch_id", "subject_id"),)

    tutor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tutors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_on: Mapped[date] = mapped_column(Date, nullable=False)
    revoked_on: Mapped[date | None] = mapped_column(Date)

    @property
    def is_live(self) -> bool:
        return self.revoked_on is None


class FeePlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fee structure for a course. Amounts stay NULL until the owner supplies
    them (docs/INTAKE.md Group E) — no invented pricing."""

    __tablename__ = "fee_plans"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[int | None] = mapped_column(Integer)  # stored in paise
    registration_fee: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        pg_enum(BillingCycle, "billing_cycle"), nullable=False
    )
    due_day_of_month: Mapped[int | None] = mapped_column(Integer)
    grace_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_fee: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
