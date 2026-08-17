"""Expand coverage to grades 1-12 and add the remaining school subjects.

The platform originally targeted Grade 11-12 exam preparation only. The owner
extended the business to home and online tuition for grades 1 through 12 across
all subjects, so the `grade` enum and the subject list both have to grow.

Note on ALTER TYPE ... ADD VALUE: PostgreSQL cannot add an enum value and use it
in the same transaction, so these run in an autocommit block. That also means
this migration is not transactional — a failure partway through leaves the
already-added values in place. They are additive and harmless, and re-running is
safe because each uses IF NOT EXISTS.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Added in ascending order, each before '11', so the enum sorts 1..12 naturally.
NEW_GRADES = [str(n) for n in range(1, 11)]

NEW_SUBJECTS: list[tuple[str, str]] = [
    ("ENG", "English"),
    ("SCI", "General Science"),
    ("SOC", "Social Studies"),
    ("EVS", "Environmental Science"),
    ("CS", "Computer Science"),
    ("HIN", "Hindi"),
    ("TEL", "Telugu"),
]


def upgrade() -> None:
    # Enum values cannot be added inside a transaction that also uses them.
    with op.get_context().autocommit_block():
        for grade in NEW_GRADES:
            op.execute(f"ALTER TYPE grade ADD VALUE IF NOT EXISTS '{grade}' BEFORE '11'")

    # Bound parameters rather than f-strings. These particular values are
    # hardcoded constants, so nothing is exploitable today, but a migration is
    # exactly the kind of file someone later edits to read from a CSV.
    bind = op.get_bind()
    insert_subject = sa.text(
        "INSERT INTO subjects (code, name, is_active) "
        "VALUES (:code, :name, true) ON CONFLICT (code) DO NOTHING"
    )
    for code, name in NEW_SUBJECTS:
        bind.execute(insert_subject, {"code": code, "name": name})


def downgrade() -> None:
    # PostgreSQL cannot remove a value from an enum type. Reversing this would
    # mean recreating `grade` and rewriting every column that uses it, which
    # risks data loss for any row already using grades 1-10. Deliberately not
    # automated: if this must be reversed, do it by hand with a backup in place.
    raise NotImplementedError(
        "Downgrade is not supported: PostgreSQL cannot drop enum values, and "
        "rebuilding the 'grade' type would risk data loss."
    )
