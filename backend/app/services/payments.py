"""Fee management with two-stage verification.

THE RULE THIS ENFORCES
----------------------
A parent uploading a screenshot creates a CLAIM, not a payment. The invoice
does not move. Only an admin verifying it inserts a row in `payments`, and only
then does the invoice become paid and the receipt email go out.

This matters commercially: anyone can screenshot a UPI app. Treating an upload
as proof would let a fee be marked paid by anyone who can operate a phone.

MONEY
-----
All amounts are integer paise. 45000 paise is exactly Rs 450.00, always.
Floating-point money accumulates rounding errors that eventually show up as a
parent disputing a balance.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InvoiceStatus, PaymentMethod, SubmissionStatus
from app.models.finance import Invoice, Payment, PaymentSubmission
from app.models.identity import Parent, Student, StudentParent, User
from app.services import audit, email


class PaymentError(Exception):
    """Message is safe to show the user."""


async def create_invoice(
    session: AsyncSession,
    *,
    student_id: uuid.UUID,
    amount_paise: int,
    period_start: date,
    period_end: date,
    due_date: date,
    discount_paise: int = 0,
    note: str | None = None,
    actor_id: uuid.UUID,
) -> Invoice:
    if amount_paise <= 0:
        raise PaymentError("The amount must be greater than zero")
    if discount_paise < 0 or discount_paise > amount_paise:
        raise PaymentError("The discount cannot exceed the amount")
    if period_end < period_start:
        raise PaymentError("The period end cannot be before the start")

    invoice = Invoice(
        student_id=student_id,
        period_start=period_start,
        period_end=period_end,
        amount_due=amount_paise,
        discount=discount_paise,
        amount_payable=amount_paise - discount_paise,
        due_date=due_date,
        status=InvoiceStatus.PENDING,
        issued_at=datetime.now(UTC),
        note=note,
    )
    session.add(invoice)
    await session.flush()

    await audit.record(
        session,
        action="invoice.created",
        entity_type="invoice",
        entity_id=invoice.id,
        actor_user_id=actor_id,
        after={"amount_payable": invoice.amount_payable},
    )
    return invoice


async def submit_payment_claim(
    session: AsyncSession,
    *,
    invoice_id: uuid.UUID,
    submitted_by: uuid.UUID,
    method: PaymentMethod,
    amount_paise: int,
    reference_id: str | None,
    proof_file_id: uuid.UUID | None,
    note: str | None = None,
) -> PaymentSubmission:
    """Record that a parent says they have paid.

    Deliberately does NOT change the invoice. The invoice moves only when an
    admin verifies this claim.
    """
    invoice = (
        await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        raise PaymentError("That invoice no longer exists")
    if invoice.status == InvoiceStatus.PAID:
        raise PaymentError("This fee has already been paid in full")
    if amount_paise <= 0:
        raise PaymentError("The amount must be greater than zero")

    submission = PaymentSubmission(
        invoice_id=invoice_id,
        submitted_by=submitted_by,
        method=method,
        reference_id=reference_id,
        amount_claimed=amount_paise,
        proof_file_id=proof_file_id,
        note=note,
        status=SubmissionStatus.PENDING,
        submitted_at=datetime.now(UTC),
    )
    session.add(submission)
    await session.flush()

    await audit.record(
        session,
        action="payment.claim_submitted",
        entity_type="payment_submission",
        entity_id=submission.id,
        actor_user_id=submitted_by,
        after={"amount_claimed": amount_paise, "reference": reference_id},
    )
    return submission


async def verify_payment(
    session: AsyncSession,
    *,
    submission_id: uuid.UUID,
    actor_id: uuid.UUID,
    amount_override_paise: int | None = None,
) -> dict:
    """Confirm a claim. This is the ONLY path that records money as received.

    Creates the ledger row, recalculates the invoice, and emails the parent.
    """
    submission = (
        await session.execute(
            select(PaymentSubmission).where(PaymentSubmission.id == submission_id)
        )
    ).scalar_one_or_none()
    if submission is None:
        raise PaymentError("That payment claim no longer exists")
    if submission.status != SubmissionStatus.PENDING:
        raise PaymentError(
            f"This claim was already {submission.status.value}"
        )

    invoice = (
        await session.execute(
            select(Invoice).where(Invoice.id == submission.invoice_id)
        )
    ).scalar_one()

    amount = amount_override_paise or submission.amount_claimed
    now = datetime.now(UTC)

    session.add(
        Payment(
            invoice_id=invoice.id,
            submission_id=submission.id,
            amount=amount,
            method=submission.method,
            reference_id=submission.reference_id,
            received_on=submission.submitted_at.date(),
            recorded_by=actor_id,
        )
    )
    submission.status = SubmissionStatus.VERIFIED
    submission.reviewed_by = actor_id
    submission.reviewed_at = now
    await session.flush()

    paid_total = await _paid_total(session, invoice.id)
    invoice.status = (
        InvoiceStatus.PAID
        if paid_total >= invoice.amount_payable
        else InvoiceStatus.PARTIAL
    )

    await audit.record(
        session,
        action="payment.verified",
        entity_type="payment_submission",
        entity_id=submission.id,
        actor_user_id=actor_id,
        after={"amount": amount, "invoice_status": invoice.status.value},
    )

    emailed = await _email_receipt(session, invoice=invoice, amount=amount,
                                   reference=submission.reference_id)

    return {
        "invoice_status": invoice.status.value,
        "paid_total_paise": paid_total,
        "outstanding_paise": max(invoice.amount_payable - paid_total, 0),
        "receipt_emailed": emailed,
    }


async def reject_payment(
    session: AsyncSession,
    *,
    submission_id: uuid.UUID,
    actor_id: uuid.UUID,
    reason: str,
) -> None:
    submission = (
        await session.execute(
            select(PaymentSubmission).where(PaymentSubmission.id == submission_id)
        )
    ).scalar_one_or_none()
    if submission is None:
        raise PaymentError("That payment claim no longer exists")
    if submission.status != SubmissionStatus.PENDING:
        raise PaymentError(f"This claim was already {submission.status.value}")
    if not reason.strip():
        raise PaymentError("Please give a reason, so the parent knows what to fix")

    submission.status = SubmissionStatus.REJECTED
    submission.reviewed_by = actor_id
    submission.reviewed_at = datetime.now(UTC)
    submission.rejection_reason = reason.strip()

    await audit.record(
        session,
        action="payment.rejected",
        entity_type="payment_submission",
        entity_id=submission.id,
        actor_user_id=actor_id,
        after={"reason": reason.strip()},
    )


async def _paid_total(session: AsyncSession, invoice_id: uuid.UUID) -> int:
    rows = (
        await session.execute(
            select(Payment.amount).where(Payment.invoice_id == invoice_id)
        )
    ).scalars().all()
    return sum(rows)


async def _email_receipt(
    session: AsyncSession, *, invoice: Invoice, amount: int, reference: str | None
) -> bool:
    """Email the primary parent. Failure is reported, never raised — the
    payment is recorded regardless of whether the mail server cooperates."""
    row = (
        await session.execute(
            select(User.full_name, User.email)
            .join(Parent, Parent.user_id == User.id)
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == invoice.student_id)
            .order_by(StudentParent.is_primary.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return False

    student_name = (
        await session.execute(
            select(User.full_name)
            .join(Student, Student.user_id == User.id)
            .where(Student.id == invoice.student_id)
        )
    ).scalar_one_or_none() or "your child"

    period = f"{invoice.period_start:%d %b %Y} to {invoice.period_end:%d %b %Y}"
    return email.payment_received(
        to=row.email,
        parent_name=row.full_name,
        student_name=student_name,
        amount_paise=amount,
        period=period,
        reference=reference,
    )


async def mark_overdue(session: AsyncSession, *, grace_days: int = 0) -> int:
    """Move past-due pending invoices to overdue. Run on a schedule."""
    cutoff = date.today() - timedelta(days=grace_days)
    invoices = (
        await session.execute(
            select(Invoice).where(
                Invoice.due_date < cutoff,
                Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]),
            )
        )
    ).scalars().all()
    for invoice in invoices:
        invoice.status = InvoiceStatus.OVERDUE
    return len(invoices)
