"""Initial schema: 49 tables, 30 enum types, and database-level integrity rules.

The DDL lives in frozen .sql files beside this module rather than inline
op.create_table() calls. Two reasons:

  1. A first migration written as `Base.metadata.create_all()` silently changes
     meaning whenever a model changes. Frozen SQL is a true point-in-time
     snapshot — this migration will always produce exactly this schema.
  2. Hand-transcribing 49 tables into op.create_table() invites typos that the
     model layer would not catch.

Subsequent migrations use ordinary op.* directives.

Revision ID: 0001
Revises:
Create Date: 2026-08-18
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SQL_DIR = Path(__file__).parent / "sql"


def _run_sql_file(filename: str) -> None:
    path = SQL_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Migration SQL missing: {path}")
    op.execute(path.read_text(encoding="utf-8"))


def upgrade() -> None:
    # ---- Extensions ----
    # citext  : case-insensitive email column, so Ravi@x.com == ravi@x.com
    # vector  : pgvector, for RAG embeddings on document_chunks
    # gen_random_uuid() is built into PostgreSQL 13+, so pgcrypto is not needed.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # ---- Tables, enum types, indexes ----
    _run_sql_file("0001_initial.sql")

    # ---- Triggers and checks encoding the owner's rules ----
    _run_sql_file("0001_constraints.sql")


def downgrade() -> None:
    # The initial migration owns every object it created. Dropping the public
    # schema is the only reliable way to reverse 49 tables plus 30 enum types
    # plus 7 trigger functions without leaving orphans behind.
    #
    # This DESTROYS ALL DATA. It exists for local development resets only and
    # must never be run against production.
    op.execute("DROP SCHEMA public CASCADE;")
    op.execute("CREATE SCHEMA public;")
    op.execute("GRANT USAGE ON SCHEMA public TO public;")
