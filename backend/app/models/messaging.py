"""Private parent-tutor messaging and notifications.

A conversation is valid only when it holds exactly one parent and one tutor,
the parent is linked to the conversation's student, and the tutor holds a live
tutor_assignment covering that student's batch.

Security note: messages are protected by TLS in transit and at-rest encryption
in the database. That is NOT end-to-end encryption, and no part of the UI
claims otherwise (spec section 9).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConversationType, NotificationChannel, NotificationType
from app.models.types import pg_enum


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    conversation_type: Mapped[ConversationType] = mapped_column(
        pg_enum(ConversationType, "conversation_type"), nullable=False
    )
    # The child the conversation is about. Drives the authorization check.
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_line: Mapped[str | None] = mapped_column(String(200))
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    members: Mapped[list["ConversationMember"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class ConversationMember(TimestampMixin, Base):
    __tablename__ = "conversation_members"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Drives unread counts without scanning the whole message table.
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[Conversation] = relationship(back_populates="members")


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Soft delete: the record is retained for audit and safeguarding.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    attachments: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "message_attachments"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="RESTRICT"), nullable=False
    )

    message: Mapped[Message] = relationship(back_populates="attachments")


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """In-app notification.

    `channel` exists from day one so email/SMS/WhatsApp can be added later
    without a migration (spec section 20).
    """

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        pg_enum(NotificationType, "notification_type"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel"),
        nullable=False,
        default=NotificationChannel.IN_APP,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    link_url: Mapped[str | None] = mapped_column(String(500))

    related_entity_type: Mapped[str | None] = mapped_column(String(50))
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
