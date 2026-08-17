"""Fee management with two-stage payment verification.

A parent uploading a screenshot creates a PaymentSubmission — an unverified
CLAIM. Only an admin action creates a Payment, the verified ledger row. An
upload can never mark an invoice paid (spec sections 10 and 42).

All money is stored as INTEGER PAISE, never float. Floating-point money
accumulates rounding errors; 45000 paise is exactly Rs 450.00, always.

No column exists anywhere for a PIN, OTP, CVV, or banking password.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InvoiceStatus, PaymentMethod, SubmissionStatus
from app.models.types import pg_enum


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fee_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fee_plans.id", ondelete="SET NULL")
    )

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    amount_due: Mapped[int] = mapped_column(Integer, nullable=False)
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amount_payable: Mapped[int] = mapped_column(Integer, nullable=False)

    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        pg_enum(InvoiceStatus, "invoice_status"),
        nullable=False,
        default=InvoiceStatus.PENDING,
        index=True,
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("amount_due >= 0", name="amount_due_non_negative"),
        CheckConstraint("discount >= 0", name="discount_non_negative"),
        CheckConstraint("amount_payable >= 0", name="amount_payable_non_negative"),
        CheckConstraint("period_end >= period_start", name="period_valid"),
    )

    submissions: Mapped[list["PaymentSubmission"]] = relationship(
        back_populates="invoice"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")


class PaymentSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An unverified claim that a payment was made.

    Creating one changes nothing about the invoice's status.
    """

    __tablename__ = "payment_submissions"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    method: Mapped[PaymentMethod] = mapped_column(
        pg_enum(PaymentMethod, "payment_method"), nullable=False
    )
    reference_id: Mapped[str | None] = mapped_column(String(120))
    amount_claimed: Mapped[int] = mapped_column(Integer, nullable=False)
    proof_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)

    status: Mapped[SubmissionStatus] = mapped_column(
        pg_enum(SubmissionStatus, "submission_status"),
        nullable=False,
        default=SubmissionStatus.PENDING,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("amount_claimed > 0", name="amount_claimed_positive"),
    )

    invoice: Mapped[Invoice] = relationship(back_populates="submissions")


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The verified ledger.

    `recorded_by` is NOT NULL by design: every row must be traceable to the
    admin who confirmed it. There is no code path that inserts here
    automatically.
    """

    __tablename__ = "payments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_submissions.id", ondelete="SET NULL")
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        pg_enum(PaymentMethod, "payment_method"), nullable=False
    )
    reference_id: Mapped[str | None] = mapped_column(String(120))
    received_on: Mapped[date] = mapped_column(Date, nullable=False)

    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
