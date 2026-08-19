"""Set a user's password directly, for when email delivery is unavailable.

The normal route is the reset link. This exists for the case where that route
is itself broken -- a blocked SMTP port, an unconfigured provider -- and
someone would otherwise be locked out of their own platform with no way back
in.

The password is typed into this terminal and never appears in an argument, a
log, or the shell history. Only the Argon2id hash is written, so the stored
value remains unreadable, exactly as if it had been set through the app.

Usage:

    cd backend
    ./.venv/Scripts/python -m scripts.set_password someone@example.com
"""

import getpass
import sys

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.security import hash_password

# Matches PasswordChangeRequest.new_password in app/schemas/auth.py, so a
# password set here is one the app would also have accepted.
MIN_LENGTH = 10


def _engine():
    settings = get_settings()
    url = settings.database_direct_url or settings.database_url
    if not url:
        raise SystemExit("No database URL configured. Check .env.")
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, connect_args={"connect_timeout": 30})


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.set_password <email>")
        return 2
    email = sys.argv[1].strip()

    engine = _engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, full_name FROM users WHERE email = :e"), {"e": email}
        ).first()

    if row is None:
        print(f"No account with email {email}.")
        print("Run: python -m scripts.list_accounts   to see the accounts that exist.")
        return 1

    print(f"Setting a new password for {row.full_name} <{email}>.")
    print(f"Minimum {MIN_LENGTH} characters. Nothing is echoed as you type.\n")

    first = getpass.getpass("New password: ")
    if len(first) < MIN_LENGTH:
        print(f"Too short: {MIN_LENGTH} characters minimum. Nothing was changed.")
        return 1
    second = getpass.getpass("Repeat it: ")
    if first != second:
        print("They do not match. Nothing was changed.")
        return 1

    digest = hash_password(first)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE users
                   SET password_hash        = :h,
                       must_change_password = false,
                       failed_login_count   = 0,
                       locked_until         = NULL
                 WHERE id = :id
                """
            ),
            {"h": digest, "id": row.id},
        )
        # Existing sessions were issued against the old password. Dropping the
        # refresh tokens signs other devices out, which is the expected
        # behaviour after a password change.
        removed = conn.execute(
            text("DELETE FROM refresh_tokens WHERE user_id = :id"), {"id": row.id}
        ).rowcount

    print("\nPassword updated.")
    print(f"Signed out {removed} existing session(s); any lockout was cleared.")
    print("Sign in at the website with the new password.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
