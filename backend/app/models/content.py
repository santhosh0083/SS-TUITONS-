"""Content hierarchy and access-controlled study material.

Worksheets, notes, and PYQs share every column and differ only by kind, so they
are one `content_items` table with a `content_type` discriminator rather than
three near-identical tables.

File bytes live in object storage; only metadata lives here (spec section 32).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AccessScopeType,
    ContentType,
    Difficulty,
    Grade,
    VirusScanStatus,
)
from app.models.types import pg_enum


class Chapter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("subject_id", "exam_id", "grade", "name"),)

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    grade: Mapped[Grade] = mapped_column(pg_enum(Grade, "grade"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    topics: Mapped[list["Topic"]] = relationship(back_populates="chapter")


class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("chapter_id", "name"),)

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficulty_hint: Mapped[Difficulty | None] = mapped_column(
        pg_enum(Difficulty, "difficulty")
    )

    chapter: Mapped[Chapter] = relationship(back_populates="topics")


class StoredFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadata for an object in storage. Never holds file bytes."""

    __tablename__ = "files"

    bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    object_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    virus_scan_status: Mapped[VirusScanStatus] = mapped_column(
        pg_enum(VirusScanStatus, "virus_scan_status"),
        nullable=False,
        default=VirusScanStatus.PENDING,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (UniqueConstraint("bucket", "object_path"),)


class ContentItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Worksheet, notes, PYQ, assignment, or reference material."""

    __tablename__ = "content_items"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        pg_enum(ContentType, "content_type"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)

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
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), index=True
    )

    file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    access_rules: Mapped[list["ContentAccessRule"]] = relationship(
        back_populates="content_item", cascade="all, delete-orphan"
    )


class ContentAccessRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Who may download a content item.

    Downloads are served via short-lived signed URLs issued only after this
    check passes. Buckets are never public.
    """

    __tablename__ = "content_access_rules"

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[AccessScopeType] = mapped_column(
        pg_enum(AccessScopeType, "access_scope_type"), nullable=False
    )
    # Interpreted against scope_type; NULL for EXAM_GRADE which uses the
    # content item's own exam/grade columns.
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    content_item: Mapped[ContentItem] = relationship(back_populates="access_rules")
