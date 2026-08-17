# SS TUITIONS — Database Schema v1 (for review)

**Status: PROPOSED — nothing has been applied to the database.**

Target: PostgreSQL 17 (Supabase, `ap-south-1`) + `pgvector`.
**49 tables** across 9 domains, 30 enum types, 48 indexes, 7 integrity triggers.
All tables carry `created_at` / `updated_at` unless noted.

> The per-domain counts below were written before implementation and undercount
> join tables; the built total is 49, not 44.

Conventions: UUID primary keys (`gen_random_uuid()`), `citext` for emails, soft-delete only where history matters, every foreign key indexed.

---

## Reflecting your decisions

| Your decision | How the schema enforces it |
|---|---|
| Owner has every permission | `users.is_superadmin`; admin bypasses all scope filters |
| Owner never teaches | No admin account in `tutor_assignments`; classes require a `tutor_id` |
| Parent ≠ tutor | DB trigger on `user_roles` rejects holding both roles |
| Tutor: join, log, attend, message | Tutor scope derives entirely from `tutor_assignments` |
| Student **and** tutor mark attendance | Two separate mark columns + discrepancy flag |
| Tutor logs subject/topics/timings | Dedicated `class_reports` table |
| You review, then share with parents | `reviewed_by_admin_at`, `shared_with_parents_at` |

---

## 1. Identity & access (7 tables)

| Table | Purpose | Key columns |
|---|---|---|
| `users` | One row per human. Auth lives here only. | `email` (citext, unique), `password_hash` (argon2id), `status`, `failed_login_count`, `locked_until` |
| `roles` | ADMIN / TUTOR / PARENT / STUDENT | `code`, `name` |
| `user_roles` | Role assignment | `(user_id, role_id)` PK |
| `students` | Student profile | `user_id` (unique), `admission_no` (unique), `grade`, `target_exam_id`, `joined_on` |
| `parents` | Parent profile | `user_id` (unique), `preferred_contact` |
| `tutors` | Tutor profile | `user_id` (unique), `qualification`, `experience_years`, `bio`, `is_contact_public` (default **false**) |
| `student_parents` | Links children to parents | `(student_id, parent_id)`, `relationship`, `is_primary` |
| `refresh_tokens` | Session revocation | `token_hash`, `expires_at`, `revoked_at` |

**The parent/tutor exclusivity constraint.** A plain `CHECK` can't see other rows, so this is a trigger on `user_roles`:

```
BEFORE INSERT OR UPDATE ON user_roles
  → if the resulting role set contains both PARENT and TUTOR, RAISE EXCEPTION
```

This holds even if application code has a bug. `is_contact_public` defaults to false so tutor phone/email is never exposed by accident (spec §25).

---

## 2. Academics (7 tables)

| Table | Purpose | Notes |
|---|---|---|
| `exams` | JEE_MAIN, JEE_ADV, EAMCET, IPE, NEET, SAT | Seeded |
| `subjects` | Physics, Chemistry, Maths, Biology | Seeded |
| `courses` | A sellable programme | `duration_months`, `classes_per_week`, `max_batch_size`, `mode` |
| `course_subjects` | Which subjects a course covers | join table |
| `batches` | `JEE-12-A` etc. | `code` unique, `capacity`, `start_date`, `end_date` |
| `batch_students` | Enrolment | `enrolled_on`, `left_on` — history preserved |
| `tutor_assignments` | **Tutor authorization backbone** | `(tutor_id, batch_id, subject_id)` |

**`tutor_assignments` is the single source of truth for tutor permissions.** Every tutor-scoped query — "my students", "my classes", "which parents may I message" — resolves through this one table. Revoking a row instantly revokes all access.

**Decision needing sign-off:** one-to-one tutoring is modelled as a **batch with `capacity = 1`**, not a separate mechanism. One scheduling path, one attendance path, one billing path instead of two parallel systems. The UI still presents it as "One-to-One".

---

## 3. Scheduling & attendance (3 tables)

### `class_sessions`
`batch_id`, `tutor_id`, `subject_id`, `scheduled_date`, `scheduled_start`, `scheduled_end`, `status`, `meeting_url` (**nullable**), `google_event_id` (nullable), `integration_status`, `created_by`, `cancellation_reason`

`integration_status` is one of `not_configured | pending | active | failed`. Until you have Google Workspace it stays `not_configured`, `meeting_url` stays **NULL**, and the UI says "Meeting link not yet configured". **No placeholder or randomly generated Meet link is ever written** (spec §42).

### `class_reports` — your addition
`class_session_id` (unique), `tutor_id`, `subject_id`, `topics_covered`, `actual_start_at`, `actual_end_at`, `homework_assigned`, `notes`, `submitted_at`, `reviewed_by_admin_at`, `shared_with_parents_at`, `status`

Note `actual_*` is stored separately from `scheduled_*` — so a class scheduled 7:00–8:00 but taught 7:12–8:05 records the truth. That difference is also your tutor-punctuality report later.

### `attendance`
`class_session_id`, `student_id`, `student_marked_status`, `student_marked_at`, `tutor_marked_status`, `tutor_marked_at`, `final_status`, `has_discrepancy`, `resolved_by`, `resolved_at` — unique on `(class_session_id, student_id)`

Resolution rule: marks agree → that becomes `final_status`. Marks disagree → `has_discrepancy = true`, the tutor's mark holds provisionally, and it surfaces in your admin queue. **Neither party silently overwrites the other.**

---

## 4. Content (5 tables)

| Table | Purpose |
|---|---|
| `chapters` | Under subject + exam + grade, ordered |
| `topics` | Under chapter, ordered |
| `files` | Object-storage metadata: `bucket`, `object_path`, `mime_type`, `size_bytes`, `checksum`, `virus_scan_status` |
| `content_items` | Worksheets, notes, PYQs, assignments |
| `content_access_rules` | Who may download what |

**Decision needing sign-off:** your spec listed `worksheets` and `pyqs` as separate tables. They share every single column and differ only in kind, so I've merged them into `content_items` with a `content_type` enum. Three near-identical tables would mean three near-identical APIs and three places to fix every bug.

Bytes live in Supabase Storage; only metadata lives in Postgres (spec §32). Downloads issue short-lived signed URLs after an authorization check — never a public bucket path.

---

## 5. Assessment (8 tables)

| Table | Notes |
|---|---|
| `tests` | `difficulty`, `duration_minutes`, `total_marks`, `negative_marking_ratio`, `available_from/until` |
| `questions` | `question_type`, `stem`, `marks`, `negative_marks`, `solution_text`, `source`, **`review_status`** |
| `question_options` | For MCQ single/multi; `is_correct` |
| `question_numeric_answers` | `correct_value`, `tolerance` |
| `test_questions` | Ordering + per-test mark override |
| `test_attempts` | `score`, `accuracy_pct`, `time_taken_seconds`, `is_auto_submitted` |
| `test_answers` | Per-question response, `is_correct`, `time_spent_seconds` |
| `student_topic_performance` | Rollup: `accuracy_pct`, `mastery_level` — feeds ML and recommendations |

**AI-generated questions are gated.** `questions.source` records `manual | ai_generated | pyq`, and anything AI-generated is inserted with `review_status = 'pending_review'`. A partial unique index prevents an unapproved question from entering a published test. Per spec §13, no AI answer reaches a student unreviewed.

---

## 6. Finance (4 tables)

`fee_plans` → `invoices` → `payment_submissions` → `payments`

| Table | Role |
|---|---|
| `fee_plans` | `amount`, `billing_cycle`, `registration_fee`, `due_day_of_month`, `grace_days`, `late_fee` |
| `invoices` | What a student owes for a period. `status` derived from payments. |
| `payment_submissions` | **An unverified claim.** `reference_id`, `amount_claimed`, `proof_file_id`, `status = pending` |
| `payments` | **The verified ledger.** Row exists only via admin action; `recorded_by` is never null. |

A parent uploading a screenshot creates a `payment_submission`, nothing more. The invoice cannot reach `paid` until you insert a `payments` row. Uploading a proof can never mark a fee paid (spec §10, §42).

**No PIN, OTP, CVV, or banking password is stored anywhere.** There is no column for one.

---

## 7. Messaging & notifications (5 tables)

| Table | Notes |
|---|---|
| `conversations` | `student_id` gives context — the conversation is *about* a child |
| `conversation_members` | `last_read_at` drives unread counts |
| `messages` | `body`, `sent_at`, `edited_at`, `deleted_at` |
| `message_attachments` | Links to `files`, same validation as content |
| `notifications` | `type`, `title`, `body`, `link_url`, `is_read`, `channel` |

A conversation is valid only if it contains **exactly one parent and one tutor**, the parent is linked to `student_id` via `student_parents`, and the tutor has a live row in `tutor_assignments` for that student's batch. Enforced in the service layer plus a DB check on membership composition.

`notifications.channel` exists from day one so email/SMS/WhatsApp can be added later without a migration (spec §20).

**On encryption:** messages are protected by TLS in transit and Supabase's at-rest encryption. That is **not** end-to-end encryption, and nothing in the UI will claim it is (spec §9).

---

## 8. AI & ML (7 tables)

| Table | Notes |
|---|---|
| `ai_sessions` | `mode` = tutor / homework_scan; token usage for cost control |
| `ai_messages` | Full transcript, `model`, `tokens_in/out` |
| `ai_recommendations` | `kind`, `target_id`, `reason`, `confidence`, `source` |
| `document_chunks` | `chunk_text`, `embedding vector(1024)`, **+ `exam_id`, `grade`, `subject_id`, `topic_id`** |
| `ml_models` | `algorithm`, `version`, `trained_at`, `training_rows`, `metrics` (jsonb), `is_active` |
| `ml_feature_snapshots` | `(student_id, snapshot_date)` unique, `features` jsonb |
| `ml_predictions` | `predicted_value`, `probability`, `explanation` (SHAP, jsonb), **`is_heuristic`** |

**RAG entitlement.** `document_chunks` carries denormalized exam/grade/subject columns so retrieval filters on entitlement *before* the vector search runs. A Grade 11 NEET student's query cannot retrieve Grade 12 JEE Advanced material, and no student can ever retrieve another student's data (spec §37).

**`ml_predictions.is_heuristic` is the honesty flag.** Until there is enough real data to train on, predictions come from transparent rules and this is `true`; the UI labels them as heuristics. When real models are trained, `ml_models.metrics` stores the **actual** validation numbers, whatever they turn out to be. Nothing displays a fabricated accuracy (spec §16, §42).

**`ml_feature_snapshots` is a dated feature store** — it makes training reproducible and lets you answer "why was this student flagged in March?" months later.

---

## 9. Operations (2 tables)

| Table | Notes |
|---|---|
| `audit_logs` | `actor_user_id`, `action`, `entity_type`, `entity_id`, `before`/`after` jsonb, `ip`, `user_agent` |
| `consent_records` | `student_id`, `parent_id`, `consent_type`, `granted_at`, `revoked_at` |

`consent_records` exists because most of your students are minors. India's DPDP Act 2023 requires verifiable parental consent for processing a child's data, and this table is what makes that provable rather than assumed (spec §37).

---

## The visibility policy layer

Every read of student-scoped data passes through one resolver rather than being re-checked in ~150 endpoints:

| Caller | Sees |
|---|---|
| **Admin (you)** | Everything |
| **Tutor** | Only students in batches they hold a live `tutor_assignments` row for |
| **Parent** | Only children linked via `student_parents` |
| **Student** | Only themselves |

Routes cannot query student data any other way. This is what makes spec §30 and §37 enforceable instead of aspirational.

---

## Seven decisions needing your sign-off

1. **One-to-one = batch of capacity 1** — one code path instead of two parallel systems
2. **`content_items` merges worksheets + PYQs + notes** — they differ only by an enum value
3. **AI questions default to `pending_review`** — you approve before students ever see them
4. **Payment verification is two-stage** — a screenshot upload can never mark a fee paid
5. **`is_heuristic` labels predictions honestly** — no fake ML accuracy before real data exists
6. **Parent/tutor exclusivity is a DB trigger** — survives application bugs
7. **Attendance discrepancies are flagged, not silently resolved** — you arbitrate

---

## Not yet in this schema

Deliberately deferred until the relevant intake group is answered:

- **Tutor payroll** — needs your rate structure (Group G)
- **Discount/scholarship rules** — needs Group E
- **Payment gateway tables** — manual verification only for now (Group F)
- **Class recordings** — needs your retention policy (Group J)
