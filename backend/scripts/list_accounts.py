"""List the platform's user accounts, so the owner can see who can sign in.

Exists because "which email do I log in with?" is otherwise unanswerable
without opening a SQL console. It prints identity and sign-in state only.

Password hashes are never selected. They are Argon2id and cannot be reversed,
so there is nothing to recover here -- a forgotten password is fixed with the
reset flow, not by looking it up.

Usage:

    cd backend
    ./.venv/Scripts/python -m scripts.list_accounts
"""

import sys

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    url = settings.database_direct_url or settings.database_url
    if not url:
        print("No database URL configured. Check .env.")
        return 1

    # The sync driver, since this is a one-shot script.
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(url, connect_args={"connect_timeout": 30})
    with engine.connect() as conn:
        revision = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
        tables = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE' "
                "AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
        print(f"database: {tables} tables, migration {revision}\n")

        # Roles live in user_roles -> roles, not as a column on users, and a
        # person can hold more than one, so they are aggregated per account.
        rows = conn.execute(
            text(
                """
                SELECT u.email,
                       u.is_superadmin,
                       COALESCE(
                           string_agg(r.name::text, ',' ORDER BY r.name::text),
                           '-'
                       )                            AS roles,
                       u.status::text               AS status,
                       u.must_change_password,
                       u.failed_login_count,
                       u.locked_until IS NOT NULL   AS locked,
                       u.last_login_at IS NOT NULL  AS signed_in_before
                FROM users u
                LEFT JOIN user_roles ur ON ur.user_id = u.id
                LEFT JOIN roles r       ON r.id = ur.role_id
                GROUP BY u.id, u.email, u.is_superadmin, u.status,
                         u.must_change_password, u.failed_login_count,
                         u.locked_until, u.last_login_at
                ORDER BY u.is_superadmin DESC, u.email
                """
            )
        ).all()

    if not rows:
        print("No user accounts exist yet.")
        return 0

    print(
        f"{'EMAIL':34} {'OWNER':6} {'ROLES':16} {'STATUS':10} "
        f"{'MUST CHG':9} {'FAILS':6} {'LOCKED':7} {'SIGNED IN'}"
    )
    print("-" * 108)
    for r in rows:
        print(
            f"{r.email:34} {'YES' if r.is_superadmin else '-':6} "
            f"{r.roles:16} {r.status:10} "
            f"{str(r.must_change_password):9} {r.failed_login_count:<6} "
            f"{'YES' if r.locked else 'no':7} "
            f"{'yes' if r.signed_in_before else 'never'}"
        )
    print(f"\n{len(rows)} account(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
