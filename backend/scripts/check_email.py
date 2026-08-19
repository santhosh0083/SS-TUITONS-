"""Check that email can actually be delivered, before trusting it in production.

"Configured" and "working" are different things. The service reported email
enabled for days while every send failed, because the host blocked the port.
This asks the provider directly.

Usage:

    cd backend
    ./.venv/Scripts/python -m scripts.check_email
    ./.venv/Scripts/python -m scripts.check_email --send someone@example.com
"""

import sys

import httpx

from app.core.config import get_settings
from app.services import email as email_service


def check_brevo(api_key: str, sender: str) -> bool:
    """Validate the key and confirm the sender address is verified."""
    headers = {"api-key": api_key, "accept": "application/json"}

    r = httpx.get("https://api.brevo.com/v3/account", headers=headers, timeout=20)
    if r.status_code == 401:
        print("  FAIL  Brevo rejected the key (401).")
        if api_key.startswith("xsmtpsib"):
            print()
            print("        This is an SMTP key. Brevo issues two different kinds:")
            print("          xsmtpsib-...  SMTP key   -> for smtplib, port 587")
            print("          xkeysib-...   API key    -> for the HTTPS API")
            print()
            print("        The HTTPS API is the one that works on Render, because")
            print("        the SMTP ports are blocked there. Create an API key at")
            print("        Brevo -> SMTP & API -> API Keys -> Generate a new API key.")
        return False
    if r.status_code != 200:
        print(f"  FAIL  Brevo returned HTTP {r.status_code}: {r.text[:200]}")
        return False

    account = r.json()
    print(f"  PASS  key valid, account {account.get('email', '?')}")
    plan = account.get("plan")
    if isinstance(plan, list) and plan:
        credits = plan[0].get("credits")
        print(f"        plan {plan[0].get('type', '?')}, credits {credits}")

    # A verified sender is required; this is the usual cause of a 400 on send.
    r = httpx.get("https://api.brevo.com/v3/senders", headers=headers, timeout=20)
    if r.status_code != 200:
        print(f"  WARN  could not list senders (HTTP {r.status_code})")
        return True

    senders = r.json().get("senders", [])
    match = next((s for s in senders if s.get("email", "").lower() == sender.lower()), None)
    if match is None:
        print(f"  FAIL  {sender} is not a sender on this account.")
        if senders:
            # Usually one already exists -- Brevo creates it from the signup
            # address -- and pointing EMAIL_FROM_ADDRESS at it is quicker than
            # verifying another.
            print("        Senders that do exist on this account:")
            for item in senders:
                state = "verified" if item.get("active") else "NOT verified"
                print(f"          {item.get('email', '?'):36} {state}")
        else:
            print("        This account has no senders at all.")
        print("        Either set EMAIL_FROM_ADDRESS to a verified one above, or")
        print("        add this address under Senders, Domains & Dedicated IPs")
        print("        and click the confirmation link Brevo emails to it.")
        return False
    if not match.get("active", False):
        print(f"  FAIL  {sender} exists but is not verified yet.")
        print("        Click the confirmation link Brevo sent to that address.")
        return False
    print(f"  PASS  sender {sender} is verified")
    return True


def recent_events(api_key: str, limit: int = 15) -> None:
    """Show what the provider did with recent messages.

    A successful API call means Brevo accepted the message, not that it
    reached anyone. Delivery, bounce and spam outcomes only appear here.
    """
    r = httpx.get(
        "https://api.brevo.com/v3/smtp/statistics/events",
        headers={"api-key": api_key, "accept": "application/json"},
        params={"limit": limit},
        timeout=20,
    )
    if r.status_code != 200:
        print(f"  could not read events (HTTP {r.status_code}): {r.text[:200]}")
        return

    events = r.json().get("events", [])
    if not events:
        print("  no events yet -- Brevo can take a minute to report them")
        return

    print(f"  {'WHEN':22} {'EVENT':12} {'TO'}")
    for e in events:
        when = str(e.get("date", ""))[:19].replace("T", " ")
        print(f"  {when:22} {str(e.get('event', '')):12} {e.get('email', '')}")


def main() -> int:
    s = get_settings()
    print(f"provider   : {s.email_provider}")
    print(f"enabled    : {s.email_enabled}")
    print(f"from       : {s.email_from_address}")
    print(f"configured : {email_service.is_configured()}")
    print(f"status     : {email_service.configuration_hint()}")
    print()

    if s.email_provider != "brevo":
        print("EMAIL_PROVIDER is not 'brevo', so nothing to check against the API.")
        print("Note that SMTP will not work on a host that blocks ports 25/465/587.")
        return 0

    if not s.brevo_api_key:
        print("  FAIL  BREVO_API_KEY is empty.")
        return 1

    ok = check_brevo(s.brevo_api_key, s.email_from_address)

    if "--recent" in sys.argv:
        print("\nrecent delivery events:")
        recent_events(s.brevo_api_key)

    if ok and len(sys.argv) == 3 and sys.argv[1] == "--send":
        target = sys.argv[2]
        print(f"\nsending a test message to {target} ...")
        sent = email_service.send(
            to=target,
            subject="SS Tuitions — email delivery test",
            body_text=(
                "This is a test message from the SS Tuitions platform.\n\n"
                "If you are reading it, password resets, fee reminders and "
                "payment receipts will now reach their recipients.\n"
            ),
        )
        print("  sent" if sent else "  FAILED — see the error above")
        ok = ok and sent

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
