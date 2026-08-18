"""Force password change on first login, and support email password reset.

Two owner requirements:

  1. The owner hands out a username and temporary password. The person must
     change that password before using the platform. `must_change_password`
     drives that: it is true on every admin-created account and cleared on the
     first successful change.

  2. A person who forgets their password can reset it themselves via an email
     link, rather than asking the owner. `password_reset_tokens` holds a hash
     of a single-use token with a short expiry.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Default true at the column level so existing accounts are also required
    # to change on next login. The owner's own account is exempted below.
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    # The owner set their own password knowingly; do not force them to change it.
    op.execute("UPDATE users SET must_change_password = false WHERE is_superadmin")

    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False
        ),
        # Only a hash of the token is stored, so a leaked table cannot be used
        # to reset anyone's password.
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE",
            name="fk_password_reset_tokens_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
        sa.UniqueConstraint(
            "token_hash", name="uq_password_reset_tokens_token_hash"
        ),
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_tokens_user_id", table_name="password_reset_tokens"
    )
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "must_change_password")
