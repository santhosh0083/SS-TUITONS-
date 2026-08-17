# SS TUITIONS

AI-assisted tutoring platform for Grade 11–12 students preparing for JEE, EAMCET, IPE, NEET, and SAT.

**Status:** Phase 1 in progress — schema and migrations complete, auth next.

---

## Prerequisites

Already installed on this machine:

| Tool | Version |
|---|---|
| Python | 3.12.10 |
| Node.js | 24.19.0 LTS |
| Git | 2.55 |

Docker is **not** required. Postgres and file storage are provided by Supabase; Redis will come from Upstash.

> **One-time Windows fix:** the Microsoft Store `python.exe` alias shadows the real install.
> Settings → Apps → Advanced app settings → App execution aliases → turn **off** both Python entries.

---

## First-time setup

### 1. Configure environment

```bash
cp .env.example .env
```

Then fill in `.env`. The two values needed right now:

**`DATABASE_DIRECT_URL`** and **`DATABASE_URL`** — already filled in except the password. Both use the **Session Pooler**:

```
postgresql+psycopg://postgres.iycurjblbydkjtuavhfr:YOUR-PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

> **Use the pooler, not the direct connection.** Supabase's direct host
> (`db.<ref>.supabase.co`) is **IPv6-only** — it publishes no A record at all.
> On any network without IPv6 it fails with
> `socket.gaierror: [Errno 11001] getaddrinfo failed`, which looks like a
> credentials problem but is not. The pooler resolves over IPv4.
>
> Port **5432** is session mode, which supports DDL and migrations. Port 6543 is
> transaction mode and needs extra driver settings — avoid it for now.

**`JWT_SECRET`** — generate a fresh one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 2. Install backend dependencies

```bash
cd backend && python -m venv .venv && ./.venv/Scripts/pip install -r requirements.txt
```

### 3. Apply the database schema

```bash
cd backend && ./.venv/Scripts/alembic upgrade head
```

This creates 49 tables, 30 enum types, 48 indexes, and 7 integrity triggers.

### 4. Verify it worked

```bash
cd backend && ./.venv/Scripts/python -m scripts.verify_schema
```

---

## Project layout

```
backend/
  app/
    core/          settings, security primitives
    db/            declarative base, session management
    models/        SQLAlchemy ORM — 49 tables across 9 domains
    schemas/       Pydantic request/response contracts
    api/v1/        FastAPI routers
    services/      business logic, including the visibility policy layer
    repositories/  data access
    auth/          authentication and RBAC
  alembic/
    versions/
      0001_initial_schema.py
      sql/
        0001_initial.sql       frozen DDL snapshot
        0001_constraints.sql   triggers and checks
docs/
  INTAKE.md        business information questionnaire (unfilled)
  SCHEMA.md        schema design and rationale
```

---

## Design rules this codebase enforces

These are not conventions — they are enforced by database triggers and constraints, so they hold even if application code has a bug.

| Rule | Enforcement |
|---|---|
| A user cannot be both parent and tutor | Trigger on `user_roles` |
| The owner administers and never teaches | Trigger blocking a tutor profile for a superadmin |
| An unreviewed AI question cannot reach a student | Two triggers on `test_questions` and `tests` |
| Attendance disagreements are flagged, never silently resolved | Trigger on `attendance` |
| No meeting URL exists while Google Meet is unconfigured | `CHECK` constraint on `class_sessions` |
| A batch cannot exceed its capacity | Trigger on `batch_students` |
| Audit logs cannot be edited or deleted | Trigger on `audit_logs` |

Additionally, by construction:

- **Money is stored as integer paise**, never floating point.
- **A payment screenshot cannot mark a fee paid.** Only an admin action inserts into `payments`.
- **No column exists for a PIN, OTP, CVV, or banking password.**
- **ML predictions carry `is_heuristic`** until real models are trained on real data.
- **Messaging is TLS-protected, not end-to-end encrypted** — and nothing claims otherwise.

---

## Quality checks

```bash
cd backend && ./.venv/Scripts/python -m ruff check app alembic
```

```bash
cd backend && ./.venv/Scripts/python -m mypy app --ignore-missing-imports
```

---

## Outstanding

- `docs/INTAKE.md` is unfilled — business details, fees, tutors, and branding are still placeholders.
- Google Meet integration is inert pending a Google Workspace account.
- ML models cannot be trained until real student activity data exists.
