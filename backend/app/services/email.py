"""Transactional email.

Uses plain SMTP, which works with a free Gmail account and needs no paid
service. Gmail allows roughly 500 messages a day — far beyond what a tuition
business sends.

SETUP (free, about 5 minutes):
  1. Turn on 2-Step Verification for the sending Google account
  2. Create an App Password: myaccount.google.com/apppasswords
  3. Put it in .env as EMAIL_SMTP_PASSWORD

An App Password is required because Google blocks ordinary passwords for SMTP.
It is scoped to mail only and can be revoked without changing the account
password.

Nothing here raises into a request path. If email is unconfigured or the send
fails, that is logged and reported to the caller as a boolean — a parent's
payment must still be recorded even if the receipt email cannot go out.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    s = get_settings()
    return bool(
        s.email_enabled
        and s.email_smtp_host
        and s.email_smtp_user
        and s.email_smtp_password
        and s.email_from_address
    )


def configuration_hint() -> str:
    s = get_settings()
    if not s.email_enabled:
        return (
            "Email is switched off. Set EMAIL_ENABLED=true and add a Gmail "
            "App Password to send payment receipts automatically."
        )
    if not s.email_smtp_password:
        return (
            "EMAIL_SMTP_PASSWORD is missing. Create a Google App Password at "
            "myaccount.google.com/apppasswords — an ordinary Gmail password "
            "will not work for SMTP."
        )
    return "Email is configured."


def send(*, to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """Send one email. Returns True on success.

    Never raises: callers are recording payments and enrolling students, and
    those must not fail because a mail server was briefly unreachable.
    """
    s = get_settings()

    if not is_configured():
        logger.info("Email not configured; skipping message to %s", to)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{s.email_from_name} <{s.email_from_address}>"
    message["To"] = to
    message.set_content(body_text)
    if body_html:
        message.add_alternative(body_html, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(s.email_smtp_host, s.email_smtp_port, timeout=20) as server:
            server.starttls(context=context)
            server.login(s.email_smtp_user, s.email_smtp_password)
            server.send_message(message)
        logger.info("Sent '%s' to %s", subject, to)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. If using Gmail, EMAIL_SMTP_PASSWORD "
            "must be an App Password, not the account password."
        )
        return False
    except Exception:
        logger.exception("Could not send email to %s", to)
        return False


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def payment_received(
    *,
    to: str,
    parent_name: str,
    student_name: str,
    amount_paise: int,
    period: str,
    reference: str | None,
) -> bool:
    """Confirmation that a fee payment has been verified.

    Sent only after an admin verifies the payment, never on upload — an
    uploaded screenshot is a claim, not a payment.
    """
    amount = f"Rs {amount_paise / 100:,.2f}"
    ref_line = f"\nReference: {reference}" if reference else ""

    text = f"""Dear {parent_name},

We have received and confirmed your fee payment for {student_name}.

Amount: {amount}
Period: {period}{ref_line}

Thank you.

SS Tuitions
Kokapet, Hyderabad
"""

    html = f"""<div style="font-family:Arial,Helvetica,sans-serif;color:#262b33;max-width:520px">
  <div style="background:#14213d;padding:20px 24px">
    <span style="color:#fff;font-size:18px;font-weight:600">SS <span style="color:#e5a33a">TUITIONS</span></span>
  </div>
  <div style="padding:24px">
    <p>Dear {parent_name},</p>
    <p>We have received and confirmed your fee payment for <strong>{student_name}</strong>.</p>
    <table style="border-collapse:collapse;margin:18px 0;width:100%">
      <tr><td style="padding:8px 0;color:#6f7785">Amount</td>
          <td style="padding:8px 0;font-weight:600;text-align:right">{amount}</td></tr>
      <tr><td style="padding:8px 0;color:#6f7785">Period</td>
          <td style="padding:8px 0;text-align:right">{period}</td></tr>
      {f'<tr><td style="padding:8px 0;color:#6f7785">Reference</td><td style="padding:8px 0;text-align:right">{reference}</td></tr>' if reference else ''}
    </table>
    <p style="color:#515966;font-size:14px">Thank you.</p>
    <p style="color:#6f7785;font-size:13px;margin-top:24px">
      SS Tuitions · Kokapet, Hyderabad
    </p>
  </div>
</div>"""

    return send(
        to=to,
        subject=f"Fee received — {student_name}",
        body_text=text,
        body_html=html,
    )


def welcome_credentials(
    *, to: str, full_name: str, role: str, temporary_password: str
) -> bool:
    """Sign-in details for a newly created account."""
    s = get_settings()
    text = f"""Dear {full_name},

An SS Tuitions account has been created for you.

Sign in at: {s.frontend_base_url}/login
Email: {to}
Temporary password: {temporary_password}

Please change your password after signing in.

SS Tuitions
"""
    return send(to=to, subject="Your SS Tuitions account", body_text=text)
