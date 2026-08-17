"""AI tutor sessions, RAG chunks, and ML model tracking.

Two honesty mechanisms live here:

1. `DocumentChunk` carries denormalized entitlement columns so RAG retrieval
   filters on what a student is allowed to see BEFORE the vector search runs.
   A Grade 11 NEET student cannot retrieve Grade 12 JEE Advanced material, and
   no student can retrieve another student's data (spec section 37).

2. `MLPrediction.is_heuristic` marks predictions produced by transparent rules
   rather than a trained model. It stays true until enough real data exists to
   train on, and the UI labels those predictions accordingly. `MLModel.metrics`
   stores real validation numbers only — never fabricated accuracy
   (spec sections 16 and 42).
"""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AISessionMode,
    Grade,
    MLTask,
    RecommendationKind,
    RecommendationSource,
)
from app.models.types import pg_enum

EMBEDDING_DIM = 1024  # voyage-3


class AISession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_sessions"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[AISessionMode] = mapped_column(
        pg_enum(AISessionMode, "ai_session_mode"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    messages: Mapped[list["AIMessage"]] = relationship(back_populates="session")


class AIMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(80))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    # Set when a safety filter or the model flags the exchange for review.
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    session: Mapped[AISession] = relationship(back_populates="messages")


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A chunk of study material with its embedding, for RAG retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("content_item_id", "chunk_index"),)

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    # ---- Entitlement columns: filtered BEFORE vector search ----
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL"), index=True
    )
    grade: Mapped[Grade | None] = mapped_column(pg_enum(Grade, "grade"), index=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), index=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL")
    )


class AIRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_recommendations"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[RecommendationKind] = mapped_column(
        pg_enum(RecommendationKind, "recommendation_kind"), nullable=False
    )
    # Interpreted against `kind` (a topic id, content item id, or test id).
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    source: Mapped[RecommendationSource] = mapped_column(
        pg_enum(RecommendationSource, "recommendation_source"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    acted_on_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MLModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A trained model version. `metrics` holds REAL validation results only."""

    __tablename__ = "ml_models"
    __table_args__ = (UniqueConstraint("name", "version"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    task: Mapped[MLTask] = mapped_column(pg_enum(MLTask, "ml_task"), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)

    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    training_rows: Mapped[int | None] = mapped_column(Integer)
    # e.g. {"roc_auc": 0.81, "f1": 0.74, "cv_folds": 5}
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    feature_list: Mapped[list | None] = mapped_column(JSONB)
    artifact_path: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MLFeatureSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Dated feature store.

    Makes training reproducible and lets a prediction be explained months later.
    """

    __tablename__ = "ml_feature_snapshots"
    __table_args__ = (UniqueConstraint("student_id", "snapshot_date"),)

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)


class MLPrediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ml_predictions"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_models.id", ondelete="SET NULL")
    )
    task: Mapped[MLTask] = mapped_column(pg_enum(MLTask, "ml_task"), nullable=False)

    predicted_value: Mapped[float | None] = mapped_column(Float)
    probability: Mapped[float | None] = mapped_column(Float)
    # SHAP values or the rule trace behind a heuristic.
    explanation: Mapped[dict | None] = mapped_column(JSONB)

    # TRUE while predictions come from transparent rules rather than a trained
    # model. The UI must label these as heuristics, never as ML output.
    is_heuristic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
