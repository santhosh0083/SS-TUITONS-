"""Transactional email.

Two transports, chosen by EMAIL_PROVIDER.

  brevo  An HTTPS request to Brevo's API. 300 messages/day free, authorised by
         a verified sender address, so no domain purchase is needed.
  smtp   A direct SMTP connection. Works locally with a Gmail App Password.

The transport matters more than it looks. Render's free web services block
outbound traffic on ports 25, 465 and 587, so an SMTP send there dies with
"[Errno 101] Network is unreachable" however correct the credentials are.
Every password reset, fee reminder and payment receipt failed that way, and
because sends are deliberately non-fatal, nothing surfaced to the user. An
HTTP API leaves over 443 and is unaffected.

SETUP for brevo (free):
  1. Create an account at brevo.com
  2. Verify the sending address under Senders, Domains & Dedicated IPs
  3. Create an API key under SMTP & API -> API Keys
  4. Set EMAIL_PROVIDER=brevo and BREVO_API_KEY

SETUP for smtp (local development):
  1. Turn on 2-Step Verification for the sending Google account
  2. Create an App Password at myaccount.google.com/apppasswords
  3. Set EMAIL_SMTP_PASSWORD

Nothing here raises into a request path. If email is unconfigured or the send
fails, that is logged and returned as a boolean — a parent's payment must
still be recorded even if the receipt cannot go out.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def is_configured() -> bool:
    s = get_settings()
    if not (s.email_enabled and s.email_from_address):
        return False
    if s.email_provider == "brevo":
        return bool(s.brevo_api_key)
    return bool(s.email_smtp_host and s.email_smtp_user and s.email_smtp_password)


def configuration_hint() -> str:
    s = get_settings()
    if not s.email_enabled:
        return "Email is switched off. Set EMAIL_ENABLED=true."
    if not s.email_from_address:
        return "EMAIL_FROM_ADDRESS is missing."
    if s.email_provider == "brevo":
        if not s.brevo_api_key:
            return (
                "BREVO_API_KEY is missing. Create one at brevo.com under "
                "SMTP & API, and verify the sending address under Senders."
            )
        return "Email is configured (Brevo, over HTTPS)."
    if not s.email_smtp_password:
        return (
            "EMAIL_SMTP_PASSWORD is missing. Create a Google App Password at "
            "myaccount.google.com/apppasswords — an ordinary Gmail password "
            "will not work for SMTP."
        )
    return "Email is configured (SMTP)."


def _send_via_brevo(
    *, to: str, subject: str, body_text: str, body_html: str | None
) -> bool:
    s = get_settings()
    payload: dict[str, object] = {
        "sender": {"name": s.email_from_name, "email": s.email_from_address},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body_text,
    }
    if body_html:
        payload["htmlContent"] = body_html

    response = httpx.post(
        BREVO_ENDPOINT,
        json=payload,
        headers={"api-key": s.brevo_api_key, "accept": "application/json"},
        timeout=20,
    )
    if response.status_code in (200, 201, 202):
        logger.info("Sent '%s' to %s via Brevo", subject, to)
        return True

    # The response body names the reason precisely -- an unverified sender is
    # the usual one -- and carries no secret, so it is worth logging.
    logger.error(
        "Brevo refused the message to %s: HTTP %s %s",
        to,
        response.status_code,
        response.text[:300],
    )
    return False


def _send_via_smtp(
    *, to: str, subject: str, body_text: str, body_html: str | None
) -> bool:
    s = get_settings()
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
        logger.info("Sent '%s' to %s via SMTP", subject, to)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. If using Gmail, EMAIL_SMTP_PASSWORD "
            "must be an App Password, not the account password."
        )
        return False
    except OSError as exc:
        # Errno 101 here means the host blocks outbound SMTP, as Render's free
        # plan does. Name that, rather than leaving a bare network error that
        # reads like a transient blip and invites retrying forever.
        logger.error(
            "Could not reach %s:%s (%s). Hosts commonly block outbound SMTP "
            "ports; set EMAIL_PROVIDER=brevo to send over HTTPS instead.",
            s.email_smtp_host,
            s.email_smtp_port,
            exc,
        )
        return False


def send(*, to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """Send one email. Returns True on success.

    Never raises: callers are recording payments and enrolling students, and
    those must not fail because a mail server was briefly unreachable.
    """
    s = get_settings()

    if not is_configured():
        logger.warning(
            "Email not configured; message to %s was not sent. %s",
            to,
            configuration_hint(),
        )
        return False

    try:
        if s.email_provider == "brevo":
            return _send_via_brevo(
                to=to, subject=subject, body_text=body_text, body_html=body_html
            )
        return _send_via_smtp(
            to=to, subject=subject, body_text=body_text, body_html=body_html
        )
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
