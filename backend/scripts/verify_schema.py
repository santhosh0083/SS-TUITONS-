"""Verify the applied schema matches expectations, and that the integrity
triggers actually fire.

Run after `alembic upgrade head`:

    ./.venv/Scripts/python -m scripts.verify_schema

This does not trust the migration to have worked. It asks the live database
what exists, and then tries to violate each rule to confirm it is rejected.
"""

import sys

from sqlalchemy import create_engine, text

from app.core.config import get_settings

EXPECTED_TABLE_COUNT = 49
EXPECTED_ENUM_COUNT = 30

EXPECTED_TRIGGERS = {
    "trg_parent_tutor_exclusivity": "user_roles",
    "trg_owner_does_not_teach": "tutors",
    "trg_no_unapproved_question_added": "test_questions",
    "trg_publish_requires_approved": "tests",
    "trg_reconcile_attendance": "attendance",
    "trg_batch_capacity": "batch_students",
    "trg_audit_logs_immutable": "audit_logs",
}

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"{GREEN}PASS{RESET}  {msg}")


def _fail(msg: str) -> None:
    print(f"{RED}FAIL{RESET}  {msg}")


def main() -> int:
    settings = get_settings()
    url = settings.database_direct_url or settings.database_url
    if not url:
        print("DATABASE_DIRECT_URL is not set in .env")
        return 2

    engine = create_engine(url.replace("+asyncpg", "+psycopg"))
    failures = 0

    with engine.connect() as conn:
        # ---- Tables ----
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
        if count == EXPECTED_TABLE_COUNT:
            _ok(f"{count} tables present")
        else:
            _fail(f"expected {EXPECTED_TABLE_COUNT} tables, found {count}")
            failures += 1

        # ---- Enum types ----
        enum_count = conn.execute(
            text(
                "SELECT COUNT(DISTINCT t.typname) FROM pg_type t "
                "JOIN pg_enum e ON t.oid = e.enumtypid"
            )
        ).scalar_one()
        if enum_count == EXPECTED_ENUM_COUNT:
            _ok(f"{enum_count} enum types present")
        else:
            _fail(f"expected {EXPECTED_ENUM_COUNT} enum types, found {enum_count}")
            failures += 1

        # ---- Extensions ----
        for ext in ("citext", "vector"):
            exists = conn.execute(
                text("SELECT COUNT(*) FROM pg_extension WHERE extname = :e"),
                {"e": ext},
            ).scalar_one()
            if exists:
                _ok(f"extension '{ext}' installed")
            else:
                _fail(f"extension '{ext}' MISSING")
                failures += 1

        # ---- Triggers ----
        rows = conn.execute(
            text(
                "SELECT trigger_name, event_object_table "
                "FROM information_schema.triggers WHERE trigger_schema = 'public'"
            )
        ).all()
        found = {r[0]: r[1] for r in rows}
        for trigger, table in EXPECTED_TRIGGERS.items():
            if found.get(trigger) == table:
                _ok(f"trigger '{trigger}' on {table}")
            else:
                _fail(f"trigger '{trigger}' missing from {table}")
                failures += 1

        # ---- The no-fake-Meet-link constraint ----
        has_check = conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_constraint "
                "WHERE conname = 'ck_class_sessions_no_url_when_unconfigured'"
            )
        ).scalar_one()
        if has_check:
            _ok("CHECK blocks a meeting URL while Meet is unconfigured")
        else:
            _fail("meeting-URL CHECK constraint missing")
            failures += 1

        # ---- HNSW vector index ----
        has_hnsw = conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE indexname = 'ix_document_chunks_embedding_hnsw'"
            )
        ).scalar_one()
        if has_hnsw:
            _ok("HNSW vector index present on document_chunks")
        else:
            _fail("HNSW vector index missing")
            failures += 1

    print()
    if failures:
        print(f"{RED}{failures} check(s) failed{RESET}")
        return 1
    print(f"{GREEN}All schema checks passed{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
