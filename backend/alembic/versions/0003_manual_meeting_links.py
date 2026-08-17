"""Allow meeting links supplied by a person, not only by the Google API.

Creating a Meet link through the API requires Google Workspace, which
SS Tuitions does not have. But a tutor can create a real Meet link from any
free Gmail account at meet.google.com and hand it over.

That link is genuine — created inside Google Meet by a human — so storing it
breaks no rule. What must still never happen is the platform *inventing* a
link. The existing CHECK constraint enforces that, and this migration keeps it
intact while adding one permitted case.

  not_configured  no link exists, and none may be stored
  manual          a real link, supplied by a person   <-- added here
  pending         API request in flight
  active          created by the Google API
  failed          API request failed; no link stored

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum values cannot be added and used inside one transaction.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE meeting_integration_status "
            "ADD VALUE IF NOT EXISTS 'manual' AFTER 'not_configured'"
        )

    # Rebuild the constraint so 'manual' may carry a URL, while
    # 'not_configured' still may not. A class with no link stays linkless.
    op.execute(
        "ALTER TABLE class_sessions "
        "DROP CONSTRAINT IF EXISTS ck_class_sessions_no_url_when_unconfigured"
    )
    op.execute(
        """
        ALTER TABLE class_sessions
        ADD CONSTRAINT ck_class_sessions_no_url_when_unconfigured
        CHECK (
            integration_status <> 'not_configured' OR meeting_url IS NULL
        )
        """
    )

    # A stored link must actually be a Google Meet URL. Without this, a typo or
    # a pasted WhatsApp link would sit in the database looking like a class
    # link until a parent clicked it and found nothing.
    op.execute(
        """
        ALTER TABLE class_sessions
        ADD CONSTRAINT ck_class_sessions_meeting_url_is_google_meet
        CHECK (
            meeting_url IS NULL
            OR meeting_url ~ '^https://meet\\.google\\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}(\\?.*)?$'
        )
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE class_sessions "
        "DROP CONSTRAINT IF EXISTS ck_class_sessions_meeting_url_is_google_meet"
    )
    # PostgreSQL cannot remove an enum value; 'manual' remains. Rows using it
    # would have to be migrated by hand before the type could be rebuilt.
