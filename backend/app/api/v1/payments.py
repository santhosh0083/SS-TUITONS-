"""Fee and payment endpoints."""

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import InvoiceStatus, PaymentMethod, RoleCode, SubmissionStatus
from app.models.finance import Invoice, PaymentSubmission
from app.models.identity import Parent, Student, StudentParent, User
from app.services import email, payments
from app.services.payments import PaymentError

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


class PaymentDetails(BaseModel):
    """How to pay. Empty fields mean the owner has not supplied them yet, and
    the UI says so rather than showing a wrong UPI id."""

    configured: bool
    upi_id: str | None
    payee_name: str | None
    bank_name: str | None
    qr_image_url: str | None
    instructions: str | None


class InvoiceOut(BaseModel):
    id: uuid.UUID
    student_name: str
    period_start: date
    period_end: date
    amount_payable_paise: int
    paid_paise: int
    outstanding_paise: int
    due_date: date
    status: InvoiceStatus
    has_pending_claim: bool


class CreateInvoiceRequest(BaseModel):
    student_id: uuid.UUID
    amount_rupees: float = Field(gt=0, description="Rupees; stored as paise")
    period_start: date
    period_end: date
    due_date: date
    discount_rupees: float = Field(default=0, ge=0)
    note: str | None = None


class SubmitClaimRequest(BaseModel):
    invoice_id: uuid.UUID
    amount_rupees: float = Field(gt=0)
    method: PaymentMethod = PaymentMethod.UPI
    reference_id: str | None = Field(
        default=None, max_length=120, description="UPI transaction id"
    )
    note: str | None = None


class ClaimOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    student_name: str
    submitted_by_name: str
    amount_claimed_paise: int
    method: PaymentMethod
    reference_id: str | None
    submitted_at: datetime
    status: SubmissionStatus


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


# The .env template ships placeholders. They are truthy strings, so a naive
# `if value` check treats them as configured and shows a parent "CONFIGURE_ME"
# as the UPI id to pay into. Showing nothing is far better than showing that.
_PLACEHOLDERS = {"configure_me", "change_me", "todo", "tbd", ""}


def _real(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return None if cleaned.lower() in _PLACEHOLDERS else cleaned


@router.get("/details", response_model=PaymentDetails)
async def payment_details(_user: CurrentUser) -> PaymentDetails:
    """Where to send the money. Shown to parents.

    `configured` is false unless a genuine UPI id and payee name exist. The UI
    then says payment details are not set up yet, rather than displaying a
    placeholder a parent might actually try to pay.
    """
    s = get_settings()
    upi = _real(s.payment_upi_id)
    payee = _real(s.payment_payee_name)
    return PaymentDetails(
        configured=bool(upi and payee),
        upi_id=upi,
        payee_name=payee,
        bank_name=_real(s.payment_bank_name),
        qr_image_url=_real(s.payment_qr_image_url),
        instructions=_real(s.payment_instructions),
    )


async def _visible_invoices(session: AsyncSession, user: User):
    """Admin sees all; a parent sees only their children's."""
    stmt = select(Invoice).order_by(Invoice.due_date.desc())
    if user.is_superadmin or RoleCode.ADMIN in user.role_codes:
        return stmt
    if RoleCode.PARENT in user.role_codes:
        children = (
            select(StudentParent.student_id)
            .join(Parent, Parent.id == StudentParent.parent_id)
            .where(Parent.user_id == user.id)
        )
        return stmt.where(Invoice.student_id.in_(children))
    if RoleCode.STUDENT in user.role_codes:
        own = select(Student.id).where(Student.user_id == user.id)
        return stmt.where(Invoice.student_id.in_(own))
    return stmt.where(Invoice.id.is_(None))  # matches nothing


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(session: Db, user: CurrentUser) -> list[InvoiceOut]:
    rows = (await session.execute(await _visible_invoices(session, user))).scalars().all()

    out: list[InvoiceOut] = []
    for inv in rows:
        student_name = (
            await session.execute(
                select(User.full_name)
                .join(Student, Student.user_id == User.id)
                .where(Student.id == inv.student_id)
            )
        ).scalar_one_or_none() or "—"

        paid = await payments._paid_total(session, inv.id)
        pending = (
            await session.execute(
                select(PaymentSubmission.id).where(
                    PaymentSubmission.invoice_id == inv.id,
                    PaymentSubmission.status == SubmissionStatus.PENDING,
                )
            )
        ).first()

        out.append(
            InvoiceOut(
                id=inv.id,
                student_name=student_name,
                period_start=inv.period_start,
                period_end=inv.period_end,
                amount_payable_paise=inv.amount_payable,
                paid_paise=paid,
                outstanding_paise=max(inv.amount_payable - paid, 0),
                due_date=inv.due_date,
                status=inv.status,
                has_pending_claim=pending is not None,
            )
        )
    return out


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: CreateInvoiceRequest, session: Db, admin: AdminUser
) -> dict:
    try:
        invoice = await payments.create_invoice(
            session,
            student_id=payload.student_id,
            amount_paise=round(payload.amount_rupees * 100),
            discount_paise=round(payload.discount_rupees * 100),
            period_start=payload.period_start,
            period_end=payload.period_end,
            due_date=payload.due_date,
            note=payload.note,
            actor_id=admin.id,
        )
    except PaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return {"id": str(invoice.id), "amount_payable_paise": invoice.amount_payable}


@router.post("/claims", status_code=status.HTTP_201_CREATED)
async def submit_claim(
    payload: SubmitClaimRequest, session: Db, user: CurrentUser
) -> dict:
    """Tell SS Tuitions you have paid.

    This does NOT mark the fee as paid. An administrator checks it first.
    """
    try:
        submission = await payments.submit_payment_claim(
            session,
            invoice_id=payload.invoice_id,
            submitted_by=user.id,
            method=payload.method,
            amount_paise=round(payload.amount_rupees * 100),
            reference_id=payload.reference_id,
            proof_file_id=None,
            note=payload.note,
        )
    except PaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return {
        "id": str(submission.id),
        "status": submission.status.value,
        "message": (
            "Thank you. SS Tuitions will confirm your payment shortly, and you "
            "will receive an email once it is verified."
        ),
    }


@router.get("/claims", response_model=list[ClaimOut])
async def list_claims(session: Db, _admin: AdminUser) -> list[ClaimOut]:
    """Claims awaiting verification."""
    rows = (
        await session.execute(
            select(PaymentSubmission)
            .where(PaymentSubmission.status == SubmissionStatus.PENDING)
            .order_by(PaymentSubmission.submitted_at)
        )
    ).scalars().all()

    out: list[ClaimOut] = []
    for s in rows:
        invoice = (
            await session.execute(select(Invoice).where(Invoice.id == s.invoice_id))
        ).scalar_one()
        student_name = (
            await session.execute(
                select(User.full_name)
                .join(Student, Student.user_id == User.id)
                .where(Student.id == invoice.student_id)
            )
        ).scalar_one_or_none() or "—"
        submitter = (
            await session.execute(select(User.full_name).where(User.id == s.submitted_by))
        ).scalar_one_or_none() or "—"
        out.append(
            ClaimOut(
                id=s.id,
                invoice_id=s.invoice_id,
                student_name=student_name,
                submitted_by_name=submitter,
                amount_claimed_paise=s.amount_claimed,
                method=s.method,
                reference_id=s.reference_id,
                submitted_at=s.submitted_at,
                status=s.status,
            )
        )
    return out


@router.post("/claims/{claim_id}/verify")
async def verify(claim_id: uuid.UUID, session: Db, admin: AdminUser) -> dict:
    """Confirm a payment. The only path that records money as received."""
    try:
        result = await payments.verify_payment(
            session, submission_id=claim_id, actor_id=admin.id
        )
    except PaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()

    if not result["receipt_emailed"]:
        result["email_note"] = email.configuration_hint()
    return result


@router.post("/claims/{claim_id}/reject")
async def reject(
    claim_id: uuid.UUID, payload: RejectRequest, session: Db, admin: AdminUser
) -> dict:
    try:
        await payments.reject_payment(
            session, submission_id=claim_id, actor_id=admin.id, reason=payload.reason
        )
    except PaymentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return {"status": "rejected"}
