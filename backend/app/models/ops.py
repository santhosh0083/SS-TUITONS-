"""Audit logging and consent records.

`ConsentRecord` exists because most students here are minors. India's DPDP Act
2023 requires verifiable parental consent for processing a child's personal
data; this table makes that provable rather than assumed (spec section 37).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConsentType
from app.models.types import pg_enum


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only record of privileged actions.

    Deliberately has no `updated_at`: audit rows are never modified.
    """

    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    before_state: Mapped[dict | None] = mapped_column(JSONB)
    after_state: Mapped[dict | None] = mapped_column(JSONB)

    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class ConsentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "consent_records"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parents.id", ondelete="SET NULL")
    )
    consent_type: Mapped[ConsentType] = mapped_column(
        pg_enum(ConsentType, "consent_type"), nullable=False
    )
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_note: Mapped[str | None] = mapped_column(Text)
