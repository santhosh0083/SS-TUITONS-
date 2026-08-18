# SS Tuitions — Where things stand

Last updated: 2026-08-18

---

## Start working again

Two terminals, one command each.

**Terminal 1 — API:**

```bash
cd C:\dev\ss-tuitions\backend && ./.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

**Terminal 2 — website:**

```bash
cd C:\dev\ss-tuitions\frontend && npm run dev
```

Then open **http://localhost:3000**

Sign in with the owner account. The credentials are **not stored in this
repository** — they were shown once when the account was created. If they are
lost, issue a new password:

```bash
cd C:/dev/ss-tuitions/backend && ./.venv/Scripts/python -m scripts.seed --email YOUR-EMAIL
```

Check everything is healthy: <http://localhost:8000/api/v1/ready> should report
`"ready": true` and `"tables_found": 49`.

---

## What works today

| Area | State |
|---|---|
| Database — 49 tables, Supabase Mumbai | Live, migration `0004` |
| Sign-in, roles, permissions | Working |
| Public homepage, 20 reviews, contact | Live |
| Admin: tutors, students, parents | Working |
| Assign tutor → schedule class → Join button | Working |
| Parent / tutor / student dashboards | Working |
| Messaging, encrypted, admin can read | Working |
| **AI tutor (Gemini)** | **Live and answering** |
| **Fees: invoices, UPI, verification** | **Working** |
| Curriculum — 336 chapters | Seeded |
| Tests: 65 backend | All passing |

### Rules the database enforces, not just the code

- A user cannot be both parent and tutor
- The owner cannot be assigned as a tutor
- An unreviewed AI question cannot reach a student
- Attendance disagreements are flagged, never silently resolved
- A meeting URL cannot exist while Meet is unconfigured, and must match the
  Google Meet format
- Audit logs cannot be edited or deleted (only anonymised on user erasure)
- A batch cannot exceed capacity

---

## Waiting on you

**1. Save the payment QR image**

Right-click the PhonePe QR → Save as →
`C:\dev\ss-tuitions\frontend\public\payment-qr.png`

Until then the QR is hidden on the parent fees page. UPI details still show, so
parents can still pay.

**2. Gmail App Password** — so fee receipts actually send

- Turn on 2-Step Verification for `sstuitions42@gmail.com`
- <https://myaccount.google.com/apppasswords> → create one
- In `.env`: `EMAIL_ENABLED=true` and `EMAIL_SMTP_PASSWORD=<16 chars>`

A normal Gmail password will not work; Google blocks it for SMTP.

**3. Rotate the Gemini API key** — the current one was pasted into a chat, so
treat it as exposed. <https://aistudio.google.com/apikey> → revoke, create new,
paste into `.env` as `GEMINI_API_KEY`.

**4. Deploy** — see `docs/DEPLOYMENT.md`. Website on Vercel, API on Render,
both free. Nothing is reachable by parents until this is done.

---

## Not built yet

- Attendance marking screens (backend model exists, dual-mark logic in the DB)
- Tests, worksheets, mock papers (curriculum is seeded; question bank is empty)
- ML analytics and at-risk detection (needs real student data first)
- Google Meet auto-creation (needs Google Workspace; manual links work now)

---

## Two risks worth acting on before real students

**No backups.** The Supabase free tier has none. Once the database holds real
marks, attendance and fee records, losing it loses your business records.
Either Supabase Pro (~₹2,100/month, daily backups + 7-day recovery) or a
scheduled `pg_dump` script.

**Render free tier sleeps** after 15 minutes idle — the first request then
takes ~50 seconds. Unacceptable when a parent taps *Join class* two minutes
before a lesson. ~₹600/month removes it.

---

## Useful commands

```bash
cd C:\dev\ss-tuitions\backend && ./.venv/Scripts/python -m pytest -q
```

```bash
cd C:\dev\ss-tuitions\backend && ./.venv/Scripts/python -m alembic current
```

```bash
cd C:\dev\ss-tuitions && git log --oneline -15
```
