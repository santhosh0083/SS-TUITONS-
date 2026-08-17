# SS Tuitions — Privacy Model

**Status: implemented and enforced in code.** This document describes what the
platform actually does today, not what is planned.

---

## 1. Parents and tutors never see each other's contact details

Parents and tutors communicate **only** through SS Tuitions. Neither side ever
receives the other's phone number, WhatsApp number, or personal email.

| Who is looking | What they see about the other party |
|---|---|
| Parent viewing their child's tutor | Tutor's **display name and subject only** |
| Tutor viewing a student's parent | Parent's **display name only** |
| Admin (owner) | Everything |

`tutors.is_contact_public` defaults to `false`. A tutor's details reach a parent
only if the owner deliberately turns that on for that tutor.

### Why this holds

Contact fields are excluded from the response schemas used by parent- and
tutor-facing endpoints. They are not "hidden in the UI" — they never leave the
server. A parent inspecting network traffic sees no phone number, because none
was sent.

---

## 2. Each person sees only their own people

Enforced by the visibility policy layer (`app/services/visibility.py`), which
every read of student data passes through:

| Role | Can see |
|---|---|
| **Parent** | Only children linked via `student_parents`, and only the tutors currently assigned to those children |
| **Tutor** | Only students in batches they hold a live `tutor_assignments` row for |
| **Student** | Only themselves |
| **Admin** | Everything |

Scopes are computed from live database state, never from the login token. When
the owner revokes a tutor's assignment, that tutor loses access on their **next
request** — not whenever their session happens to expire.

---

## 3. Class meetings

- **One meeting per class session.** Never a shared room, never a reused link.
- The link is returned only to the assigned tutor, the enrolled student, and
  that student's linked parents.
- Meetings are created through the **official Google Calendar API** with a Meet
  conference attached.

### No fake links, guaranteed twice

If Google is not configured, no link is created. The application refuses, and
independently the database rejects it:

```sql
CONSTRAINT ck_class_sessions_no_url_when_unconfigured
CHECK (integration_status <> 'not_configured' OR meeting_url IS NULL)
```

Both the application layer and the database would have to be wrong for a
placeholder link to reach a parent.

**Current state:** not connected. Google Meet requires a Google Workspace
account; a free Gmail account cannot create Meet conferences through the API.
Classes can still be scheduled — they simply show "link not yet available"
instead of a fabricated one.

---

## 4. Message encryption — read this carefully

Message bodies are encrypted at rest with **AES-256-GCM** before being written
to the database.

### This is NOT end-to-end encryption

**The SS Tuitions server holds the key and can decrypt any message.** That is a
deliberate decision, not an oversight: the platform serves children, and the
owner must be able to review a conversation if a safeguarding concern arises.
True end-to-end encryption would make that impossible.

Nowhere in this platform is messaging described as "end-to-end encrypted",
because it is not.

### What the encryption does protect against

- A stolen or leaked database backup
- A read-only SQL breach
- Anyone browsing rows in the database console

If the database leaked tomorrow, message contents would be unreadable ciphertext.

### What it does not protect against

- Someone who obtains the encryption key (held in environment config, never in
  the database)
- A compromised application server, which by definition holds the key
- A legitimate admin — see below

Messages are additionally bound to their conversation cryptographically, so a
row cannot be moved into a thread it was never part of.

---

## 5. Admin access to conversations

The owner can read conversations. This is disclosed here rather than hidden.

Every access is:

- **Restricted** to accounts holding the ADMIN role
- **Recorded** in `audit_logs`, which a database trigger makes append-only —
  the record cannot be edited or deleted, including by the owner
- **Attributable** — which admin, which conversation, when

### What parents and tutors should be told

> Messages you send through SS Tuitions are encrypted and private between you
> and the tutor. SS Tuitions administrators can access conversations when
> needed for safety or support reasons. Every such access is permanently
> recorded.

This wording is accurate. Do not replace it with a stronger privacy claim.

---

## 6. Children's data

Most SS Tuitions students are minors. India's DPDP Act 2023 requires verifiable
parental consent for processing a child's personal data.

- `consent_records` stores consent per student, per purpose, with timestamps
- AI features strip identifiers before any text reaches a third-party provider
  (`app/ai/privacy.py`) — no name, email, phone or student ID is ever sent
- Student data is never public; there are no unauthenticated endpoints
  returning student information

---

## 7. What is not yet implemented

Stated plainly so this document is not read as a promise:

- Google Meet is **not connected** (needs Workspace)
- Message notifications are in-app only; email and WhatsApp are not wired
- There is no automated data-export or deletion tool yet — Group J of
  `docs/INTAKE.md` needs answering first
