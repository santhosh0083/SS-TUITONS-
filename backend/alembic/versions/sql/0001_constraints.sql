-- ---------------------------------------------------------------------------
-- Integrity rules enforced by the DATABASE, not by application code.
--
-- Each of these encodes a decision the owner made. They live here rather than
-- in a service layer so they survive application bugs, direct SQL edits, and
-- any future second client talking to this database.
-- ---------------------------------------------------------------------------


-- ---------------------------------------------------------------------------
-- RULE 1: A user may not hold both PARENT and TUTOR roles.
-- Owner's instruction, 2026-08-17: "parent and tutor cant be same".
--
-- AFTER trigger, so the row being inserted is already visible to the check.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_parent_tutor_exclusivity()
RETURNS TRIGGER AS $$
DECLARE
    conflicting_count integer;
BEGIN
    SELECT COUNT(DISTINCT r.code)
      INTO conflicting_count
      FROM user_roles ur
      JOIN roles r ON r.id = ur.role_id
     WHERE ur.user_id = NEW.user_id
       AND r.code IN ('PARENT', 'TUTOR');

    IF conflicting_count > 1 THEN
        RAISE EXCEPTION
            'User % cannot hold both PARENT and TUTOR roles', NEW.user_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_parent_tutor_exclusivity ON user_roles;
CREATE TRIGGER trg_parent_tutor_exclusivity
    AFTER INSERT OR UPDATE ON user_roles
    FOR EACH ROW
    EXECUTE FUNCTION enforce_parent_tutor_exclusivity();


-- ---------------------------------------------------------------------------
-- RULE 2: The owner administers and does not teach.
-- Owner's instruction, 2026-08-17: "No, I only administer - hired tutors teach".
--
-- Blocks creating a tutor profile for a superadmin account, which in turn makes
-- it impossible to assign the owner to a batch or a class.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_owner_does_not_teach()
RETURNS TRIGGER AS $$
DECLARE
    target_is_superadmin boolean;
BEGIN
    SELECT is_superadmin INTO target_is_superadmin
      FROM users WHERE id = NEW.user_id;

    IF target_is_superadmin THEN
        RAISE EXCEPTION
            'User % is a superadmin and cannot be given a tutor profile', NEW.user_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_owner_does_not_teach ON tutors;
CREATE TRIGGER trg_owner_does_not_teach
    AFTER INSERT OR UPDATE ON tutors
    FOR EACH ROW
    EXECUTE FUNCTION enforce_owner_does_not_teach();


-- ---------------------------------------------------------------------------
-- RULE 3: An unapproved question can never reach a student.
-- Spec section 13: AI-generated content must be reviewed before use.
--
-- Two directions have to be blocked:
--   3a. adding an unapproved question to an already-published test
--   3b. publishing a test that contains an unapproved question
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_no_unapproved_question_in_published_test()
RETURNS TRIGGER AS $$
DECLARE
    test_is_published boolean;
    question_review review_status;
BEGIN
    SELECT is_published INTO test_is_published FROM tests WHERE id = NEW.test_id;
    SELECT review_status INTO question_review FROM questions WHERE id = NEW.question_id;

    IF test_is_published AND question_review <> 'approved' THEN
        RAISE EXCEPTION
            'Question % is %, and cannot be added to published test %',
            NEW.question_id, question_review, NEW.test_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_no_unapproved_question_added ON test_questions;
CREATE TRIGGER trg_no_unapproved_question_added
    AFTER INSERT OR UPDATE ON test_questions
    FOR EACH ROW
    EXECUTE FUNCTION enforce_no_unapproved_question_in_published_test();


CREATE OR REPLACE FUNCTION enforce_publish_requires_approved_questions()
RETURNS TRIGGER AS $$
DECLARE
    unapproved_count integer;
BEGIN
    IF NEW.is_published AND NOT COALESCE(OLD.is_published, false) THEN
        SELECT COUNT(*)
          INTO unapproved_count
          FROM test_questions tq
          JOIN questions q ON q.id = tq.question_id
         WHERE tq.test_id = NEW.id
           AND q.review_status <> 'approved';

        IF unapproved_count > 0 THEN
            RAISE EXCEPTION
                'Test % cannot be published: % question(s) await review',
                NEW.id, unapproved_count
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_publish_requires_approved ON tests;
CREATE TRIGGER trg_publish_requires_approved
    BEFORE UPDATE ON tests
    FOR EACH ROW
    EXECUTE FUNCTION enforce_publish_requires_approved_questions();


-- ---------------------------------------------------------------------------
-- RULE 4: Attendance discrepancies are flagged, never silently resolved.
-- Owner's instruction, 2026-08-17: student and tutor both mark attendance.
--
-- Marks agree      -> final_status is that value.
-- Marks differ     -> has_discrepancy is raised, tutor's mark holds
--                     provisionally, and the owner arbitrates.
-- Only one present -> no final status yet.
--
-- An explicit admin resolution (resolved_by set) is always respected.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION reconcile_attendance_marks()
RETURNS TRIGGER AS $$
BEGIN
    -- An admin has arbitrated; leave their decision untouched.
    IF NEW.resolved_by IS NOT NULL THEN
        NEW.has_discrepancy := false;
        RETURN NEW;
    END IF;

    IF NEW.student_marked_status IS NOT NULL
       AND NEW.tutor_marked_status IS NOT NULL THEN
        IF NEW.student_marked_status = NEW.tutor_marked_status THEN
            NEW.final_status    := NEW.tutor_marked_status;
            NEW.has_discrepancy := false;
        ELSE
            -- Tutor's mark holds provisionally; owner is alerted.
            NEW.final_status    := NEW.tutor_marked_status;
            NEW.has_discrepancy := true;
        END IF;
    ELSE
        NEW.final_status    := NULL;
        NEW.has_discrepancy := false;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reconcile_attendance ON attendance;
CREATE TRIGGER trg_reconcile_attendance
    BEFORE INSERT OR UPDATE ON attendance
    FOR EACH ROW
    EXECUTE FUNCTION reconcile_attendance_marks();


-- ---------------------------------------------------------------------------
-- RULE 5: A class session must not carry a meeting URL while the Google
-- integration is unconfigured. Spec section 42: no fake Meet links, ever.
-- ---------------------------------------------------------------------------
ALTER TABLE class_sessions
    ADD CONSTRAINT ck_class_sessions_no_url_when_unconfigured
    CHECK (
        integration_status <> 'not_configured'
        OR meeting_url IS NULL
    );


-- ---------------------------------------------------------------------------
-- RULE 6: A batch cannot enrol more active students than its capacity.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_batch_capacity()
RETURNS TRIGGER AS $$
DECLARE
    active_count integer;
    batch_capacity integer;
BEGIN
    IF NEW.status <> 'active' THEN
        RETURN NEW;
    END IF;

    SELECT capacity INTO batch_capacity FROM batches WHERE id = NEW.batch_id;

    SELECT COUNT(*) INTO active_count
      FROM batch_students
     WHERE batch_id = NEW.batch_id
       AND status = 'active';

    IF active_count > batch_capacity THEN
        RAISE EXCEPTION
            'Batch % is full (capacity %)', NEW.batch_id, batch_capacity
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_batch_capacity ON batch_students;
CREATE TRIGGER trg_batch_capacity
    AFTER INSERT OR UPDATE ON batch_students
    FOR EACH ROW
    EXECUTE FUNCTION enforce_batch_capacity();


-- ---------------------------------------------------------------------------
-- RULE 7: Audit logs are append-only.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only; % is not permitted', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs;
CREATE TRIGGER trg_audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_mutation();


-- ---------------------------------------------------------------------------
-- Performance: vector similarity index for RAG retrieval.
-- HNSW with cosine distance. Built after the table exists but before any
-- meaningful data volume.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);
