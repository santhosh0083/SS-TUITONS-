"""Let audit rows be anonymised without letting them be edited.

THE PROBLEM
-----------
`audit_logs.actor_user_id` has ON DELETE SET NULL, so deleting a user makes
PostgreSQL issue an UPDATE against audit_logs. The append-only trigger blocked
every UPDATE, so the delete failed with:

    audit_logs is append-only; UPDATE is not permitted

The practical effect: any user who had ever done anything could never be
deleted. That is wrong for two reasons — routine cleanup becomes impossible,
and India's DPDP Act gives people a right to erasure that the platform could
not honour.

THE FIX
-------
The trigger now permits exactly one kind of UPDATE: clearing `actor_user_id`
from a value to NULL, with every other column unchanged. That is precisely what
the foreign key's SET NULL does when a user is erased.

What the audit log is for — what happened, to what, when, and the before/after
state — remains immutable. Only the link to a deleted person is severed, which
is the point of erasure.

Everything else stays blocked: no editing an action, no changing a timestamp,
no rewriting before/after state, and no deletes at all.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'audit_logs is append-only; DELETE is not permitted'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;

            -- Permit only the anonymisation performed by ON DELETE SET NULL:
            -- actor_user_id goes from a value to NULL and nothing else moves.
            IF OLD.actor_user_id IS NOT NULL
               AND NEW.actor_user_id IS NULL
               AND NEW.action              IS NOT DISTINCT FROM OLD.action
               AND NEW.entity_type         IS NOT DISTINCT FROM OLD.entity_type
               AND NEW.entity_id           IS NOT DISTINCT FROM OLD.entity_id
               AND NEW.before_state        IS NOT DISTINCT FROM OLD.before_state
               AND NEW.after_state         IS NOT DISTINCT FROM OLD.after_state
               AND NEW.ip_address          IS NOT DISTINCT FROM OLD.ip_address
               AND NEW.user_agent          IS NOT DISTINCT FROM OLD.user_agent
               AND NEW.created_at          IS NOT DISTINCT FROM OLD.created_at
               AND NEW.id                  IS NOT DISTINCT FROM OLD.id
            THEN
                RETURN NEW;
            END IF;

            RAISE EXCEPTION
                'audit_logs is append-only; only anonymising actor_user_id is permitted'
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # BEFORE UPDATE must return NEW for the row to change, so the trigger is
    # recreated for UPDATE and DELETE explicitly.
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_immutable
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only; % is not permitted', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
