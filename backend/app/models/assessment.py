"""Tests, questions, attempts, and per-topic performance rollups.

AI-generated questions enter with review_status = PENDING_REVIEW and cannot be
served to a student until an admin approves them (spec section 13).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AttemptStatus,
    Difficulty,
    Grade,
    QuestionSource,
    QuestionType,
    ReviewStatus,
    TestType,
)
from app.models.types import pg_enum


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "questions"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL")
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )

    question_type: Mapped[QuestionType] = mapped_column(
        pg_enum(QuestionType, "question_type"), nullable=False
    )
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        pg_enum(Difficulty, "difficulty"), nullable=False
    )
    marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=4)
    negative_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    solution_text: Mapped[str | None] = mapped_column(Text)

    # ---- Provenance and review gate ----
    source: Mapped[QuestionSource] = mapped_column(
        pg_enum(QuestionSource, "question_source"),
        nullable=False,
        default=QuestionSource.MANUAL,
    )
    ai_model: Mapped[str | None] = mapped_column(String(80))
    review_status: Mapped[ReviewStatus] = mapped_column(
        pg_enum(ReviewStatus, "review_status"),
        nullable=False,
        default=ReviewStatus.APPROVED,
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
    numeric_answer: Mapped["QuestionNumericAnswer | None"] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )


class QuestionOption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_options"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(5), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    question: Mapped[Question] = relationship(back_populates="options")


class QuestionNumericAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_numeric_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    correct_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    tolerance: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(30))

    question: Mapped[Question] = relationship(back_populates="numeric_answer")


class Test(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tests"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    test_type: Mapped[TestType] = mapped_column(
        pg_enum(TestType, "test_type"), nullable=False
    )
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL")
    )
    grade: Mapped[Grade | None] = mapped_column(pg_enum(Grade, "grade"))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL")
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL")
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL")
    )

    difficulty: Mapped[Difficulty | None] = mapped_column(
        pg_enum(Difficulty, "difficulty")
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_marks: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    negative_marking_ratio: Mapped[float] = mapped_column(
        Numeric(4, 3), nullable=False, default=0
    )
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="duration_positive"),
        CheckConstraint(
            "available_until IS NULL OR available_from IS NULL "
            "OR available_until > available_from",
            name="availability_window_valid",
        ),
    )

    questions: Mapped[list["TestQuestion"]] = relationship(back_populates="test")


class TestQuestion(TimestampMixin, Base):
    __tablename__ = "test_questions"

    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tests.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    marks_override: Mapped[float | None] = mapped_column(Numeric(6, 2))

    test: Mapped[Test] = relationship(back_populates="questions")
    question: Mapped[Question] = relationship(lazy="joined")


class TestAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "test_attempts"

    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttemptStatus] = mapped_column(
        pg_enum(AttemptStatus, "attempt_status"),
        nullable=False,
        default=AttemptStatus.IN_PROGRESS,
    )

    score: Mapped[float | None] = mapped_column(Numeric(8, 2))
    max_score: Mapped[float | None] = mapped_column(Numeric(8, 2))
    accuracy_pct: Mapped[float | None] = mapped_column(Float)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer)
    is_auto_submitted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    answers: Mapped[list["TestAnswer"]] = relationship(back_populates="attempt")


class TestAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "test_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False
    )

    selected_option_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True))
    )
    numeric_answer: Mapped[float | None] = mapped_column(Numeric(18, 6))
    text_answer: Mapped[str | None] = mapped_column(Text)

    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    marks_awarded: Mapped[float | None] = mapped_column(Numeric(6, 2))
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer)

    attempt: Mapped[TestAttempt] = relationship(back_populates="answers")


class StudentTopicPerformance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Rolled-up per-topic accuracy. Feeds the ML features and recommendations."""

    __tablename__ = "student_topic_performance"
    __table_args__ = (UniqueConstraint("student_id", "topic_id"),)

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )

    questions_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_pct: Mapped[float | None] = mapped_column(Float)
    avg_time_seconds: Mapped[float | None] = mapped_column(Float)
    mastery_level: Mapped[str | None] = mapped_column(String(20))
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
