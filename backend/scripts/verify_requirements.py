"""Verify the platform against what the owner actually asked for.

Creates real accounts, exercises every stated requirement against the running
API, then deletes everything it made. Reports PASS/FAIL per requirement rather
than describing intent.

    ./.venv/Scripts/python -m scripts.verify_requirements
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import create_engine, text

from app.core.config import get_settings

BASE = "http://127.0.0.1:8000/api/v1"
TAG = "qa-verify"
# Owner credentials come from the environment, never the source. Hardcoding
# them here put the password into git history once already.
#
#   set SS_VERIFY_EMAIL=you@example.com
#   set SS_VERIFY_PASSWORD=...
OWNER = (
    os.environ.get("SS_VERIFY_EMAIL", ""),
    os.environ.get("SS_VERIFY_PASSWORD", ""),
)

results: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))


def call(method, path, body=None, token=None):
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - fixed localhost URL
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:  # noqa: BLE001
        return None, type(e).__name__


def login(email, password):
    s, b = call("POST", "/auth/login", body={"email": email, "password": password})
    return json.loads(b)["access_token"] if s == 200 else None


def main() -> int:  # noqa: PLR0915
    if not OWNER[0] or not OWNER[1]:
        print("Set SS_VERIFY_EMAIL and SS_VERIFY_PASSWORD first. In PowerShell:")
        print('  $env:SS_VERIFY_EMAIL = "you@example.com"')
        print('  $env:SS_VERIFY_PASSWORD = "your-password"')
        return 1

    admin = login(*OWNER)
    if not admin:
        print("Could not sign in. Check the credentials, and that the API is up.")
        return 1

    eng = create_engine(get_settings().database_direct_url)

    # ---------------- Build a realistic scenario ----------------
    tutor_a = json.loads(
        call("POST", "/admin/tutors", body={
            "full_name": "Tutor Alpha", "email": f"{TAG}-ta@sstuitions-verify.in",
            "phone": "9111111111", "qualification": "IIT Hyderabad CSE",
        }, token=admin)[1]
    )
    tutor_b = json.loads(
        call("POST", "/admin/tutors", body={
            "full_name": "Tutor Beta", "email": f"{TAG}-tb@sstuitions-verify.in",
            "phone": "9222222222",
        }, token=admin)[1]
    )
    stu = json.loads(
        call("POST", "/admin/students", body={
            "full_name": "Student One", "email": f"{TAG}-s1@sstuitions-verify.in",
            "grade": "11", "parent_full_name": "Parent One",
            "parent_email": f"{TAG}-p1@sstuitions-verify.in",
            "parent_phone": "9333333333",
        }, token=admin)[1]
    )
    other = json.loads(
        call("POST", "/admin/students", body={
            "full_name": "Student Two", "email": f"{TAG}-s2@sstuitions-verify.in",
            "grade": "12", "parent_full_name": "Parent Two",
            "parent_email": f"{TAG}-p2@sstuitions-verify.in",
        }, token=admin)[1]
    )

    with eng.connect() as c:
        sid = c.execute(text(
            "SELECT s.id FROM students s JOIN users u ON u.id=s.user_id WHERE u.email=:e"
        ), {"e": f"{TAG}-s1@sstuitions-verify.in"}).scalar_one()
        sid2 = c.execute(text(
            "SELECT s.id FROM students s JOIN users u ON u.id=s.user_id WHERE u.email=:e"
        ), {"e": f"{TAG}-s2@sstuitions-verify.in"}).scalar_one()
        tid = c.execute(text(
            "SELECT t.id FROM tutors t JOIN users u ON u.id=t.user_id WHERE u.email=:e"
        ), {"e": f"{TAG}-ta@sstuitions-verify.in"}).scalar_one()
        subj = c.execute(text("SELECT id FROM subjects WHERE code='MATH'")).scalar_one()

    asg = json.loads(call("POST", "/assignments", body={
        "student_id": str(sid), "tutor_id": str(tid), "subject_id": str(subj)
    }, token=admin)[1])

    now = datetime.now(UTC)
    cls = json.loads(call("POST", "/classes", body={
        "batch_id": asg["batch_id"], "tutor_id": str(tid), "subject_id": str(subj),
        "scheduled_date": date.today().isoformat(),
        "scheduled_start": (now - timedelta(minutes=5)).strftime("%H:%M"),
        "scheduled_end": (now + timedelta(minutes=55)).strftime("%H:%M"),
        "meeting_url": "https://meet.google.com/abc-defg-hij",
    }, token=admin)[1])

    ta = login(f"{TAG}-ta@sstuitions-verify.in", tutor_a["temporary_password"])
    tb = login(f"{TAG}-tb@sstuitions-verify.in", tutor_b["temporary_password"])
    p1 = login(f"{TAG}-p1@sstuitions-verify.in", stu["parent"]["temporary_password"])
    p2 = login(f"{TAG}-p2@sstuitions-verify.in", other["parent"]["temporary_password"])

    # ================= REQUIREMENT CHECKS =================

    # --- Privacy: no contact details cross between parent and tutor ---
    _, parent_classes = call("GET", "/classes/mine", token=p1)
    check("Parent never sees tutor phone", "9111111111" not in parent_classes)
    check("Parent never sees tutor email", f"{TAG}-ta@" not in parent_classes)

    _, tutor_classes = call("GET", "/classes/mine", token=ta)
    check("Tutor never sees parent phone", "9333333333" not in tutor_classes)
    check("Tutor never sees parent email", f"{TAG}-p1@" not in tutor_classes)

    _, convs = call("GET", "/messages", token=p1)
    check("Messaging exposes no contact details",
          "9111111111" not in convs and f"{TAG}-ta@" not in convs)

    # --- Scoping: each side sees only their own people ---
    parent_sees = json.loads(parent_classes)
    check("Parent sees only their own child",
          all(c["student_name"] == "Student One" for c in parent_sees),
          f"{len(parent_sees)} class(es)")

    _, other_parent_classes = call("GET", "/classes/mine", token=p2)
    check("Unrelated parent sees nothing",
          json.loads(other_parent_classes) == [])

    _, tutor_b_classes = call("GET", "/classes/mine", token=tb)
    check("Unassigned tutor sees no classes",
          json.loads(tutor_b_classes) == [])

    # --- Meet link: one per class, only to authorised people ---
    check("Assigned parent gets the Join link",
          any(c.get("meeting_url") for c in parent_sees))
    check("Meet link is a real meet.google.com URL",
          all(str(c.get("meeting_url", "")).startswith("https://meet.google.com/")
              for c in parent_sees if c.get("meeting_url")))
    s_fake, _ = call("POST", "/classes", body={
        "batch_id": asg["batch_id"], "tutor_id": str(tid), "subject_id": str(subj),
        "scheduled_date": date.today().isoformat(),
        "scheduled_start": "23:00", "scheduled_end": "23:30",
        "meeting_url": "https://zoom.us/j/123",
    }, token=admin)
    check("Non-Meet link is rejected", s_fake == 422, f"HTTP {s_fake}")

    # --- Tutor is restricted to teaching only ---
    s_admin_try, _ = call("GET", "/admin/students", token=ta)
    check("Tutor cannot list all students", s_admin_try == 403, f"HTTP {s_admin_try}")
    s_fee_try, _ = call("POST", "/payments/invoices", body={
        "student_id": str(sid), "amount_rupees": 100,
        "period_start": str(date.today()), "period_end": str(date.today()),
        "due_date": str(date.today()),
    }, token=ta)
    check("Tutor cannot raise fees", s_fee_try == 403, f"HTTP {s_fee_try}")

    # --- Parent/tutor exclusivity, owner does not teach ---
    with eng.connect() as c:
        both = c.execute(text("""
            SELECT COUNT(*) FROM (
              SELECT ur.user_id FROM user_roles ur JOIN roles r ON r.id=ur.role_id
              WHERE r.code IN ('PARENT','TUTOR')
              GROUP BY ur.user_id HAVING COUNT(DISTINCT r.code) > 1) x
        """)).scalar_one()
        owner_teaches = c.execute(text(
            "SELECT COUNT(*) FROM tutors t JOIN users u ON u.id=t.user_id "
            "WHERE u.is_superadmin"
        )).scalar_one()
    check("Nobody is both parent and tutor", both == 0)
    check("Owner is not a tutor", owner_teaches == 0)

    # --- Messaging: only assigned pairs, admin sees everything ---
    conv_list = json.loads(convs)
    check("Conversation auto-created on assignment", len(conv_list) >= 1)
    if conv_list:
        cid = conv_list[0]["id"]
        s_out, _ = call("GET", f"/messages/{cid}", token=tb)
        check("Unrelated tutor cannot open the thread",
              s_out == 404, f"HTTP {s_out}")
        s_send, _ = call("POST", f"/messages/{cid}", body={"body": "Test message"},
                         token=p1)
        check("Parent can message their tutor", s_send == 201, f"HTTP {s_send}")
        s_admin_read, admin_msgs = call("GET", f"/messages/{cid}?reason=verification",
                                        token=admin)
        check("Owner can read any conversation", s_admin_read == 200)
        with eng.connect() as c:
            audited = c.execute(text(
                "SELECT COUNT(*) FROM audit_logs WHERE action='conversation.admin_viewed'"
            )).scalar_one()
        check("Owner's access is audit-logged", audited > 0, f"{audited} entries")
        with eng.connect() as c:
            stored = c.execute(text(
                "SELECT body FROM messages ORDER BY sent_at DESC LIMIT 1"
            )).scalar_one_or_none()
        encrypted = (
            isinstance(stored, str)
            and "Test message" not in stored
            and stored.startswith("v1:")
        )
        check("Messages encrypted at rest", encrypted)

    # --- Attendance: dual marking ---
    call("POST", f"/attendance/{cls['id']}/student-mark", body={"mark": "present"},
         token=login(f"{TAG}-s1@sstuitions-verify.in", stu["temporary_password"]))
    call("POST", f"/attendance/{cls['id']}/tutor-mark",
         body={"marks": {str(sid): "absent"}}, token=ta)
    _, roster = call("GET", f"/attendance/{cls['id']}/roster", token=ta)
    r0 = json.loads(roster)[0]
    check("Student and tutor marks both kept",
          r0["student_marked"] == "present" and r0["tutor_marked"] == "absent")
    check("Disagreement is flagged for the owner", r0["has_discrepancy"] is True)

    # --- Payments: upload is a claim, not a payment ---
    inv = json.loads(call("POST", "/payments/invoices", body={
        "student_id": str(sid), "amount_rupees": 1500,
        "period_start": str(date.today()), "period_end": str(date.today()),
        "due_date": str(date.today() + timedelta(days=5)),
    }, token=admin)[1])
    call("POST", "/payments/claims", body={
        "invoice_id": inv["id"], "amount_rupees": 1500, "reference_id": "TEST123"
    }, token=p1)
    _, invs = call("GET", "/payments/invoices", token=p1)
    inv_after = [i for i in json.loads(invs) if i["id"] == inv["id"]][0]
    check("Parent claim does NOT mark the fee paid",
          inv_after["status"] != "paid", f"status={inv_after['status']}")
    claims = json.loads(call("GET", "/payments/claims", token=admin)[1])
    mine = [c for c in claims if c["invoice_id"] == inv["id"]]
    check("Claim reaches the owner for verification", len(mine) == 1)
    if mine:
        vr = json.loads(call("POST", f"/payments/claims/{mine[0]['id']}/verify",
                             body={}, token=admin)[1])
        check("Owner verification marks it paid", vr["invoice_status"] == "paid")
        check("Receipt email status reported honestly",
              "receipt_emailed" in vr,
              f"emailed={vr['receipt_emailed']}")

    # --- Grades 1-12 and subjects ---
    with eng.connect() as c:
        grades = [r[0] for r in c.execute(text(
            "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid "
            "WHERE t.typname='grade' ORDER BY e.enumsortorder"))]
        subjects = c.execute(text("SELECT COUNT(*) FROM subjects")).scalar_one()
        chapters = c.execute(text("SELECT COUNT(*) FROM chapters")).scalar_one()
    check("Grades 1 to 12 supported",
          grades == [str(n) for n in range(1, 13)], f"{len(grades)} grades")
    check("All subjects present", subjects >= 11, f"{subjects} subjects")
    check("Curriculum seeded", chapters > 300, f"{chapters} chapters")

    # --- AI tutor ---
    s_ai, ai_body = call("GET", "/ai/status", token=admin)
    ai_ok = s_ai == 200 and json.loads(ai_body)["available"]
    check("AI tutor is configured", ai_ok)
    s_ai_admin, _ = call("POST", "/ai/ask", body={"question": "What is 2+2?"},
                         token=admin)
    check("AI tutor is students-only", s_ai_admin == 403, f"HTTP {s_ai_admin}")

    # ---------------- Cleanup ----------------
    with eng.begin() as c:
        c.execute(text("DELETE FROM payments WHERE invoice_id IN "
                       "(SELECT id FROM invoices WHERE student_id IN (:a,:b))"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM payment_submissions WHERE invoice_id IN "
                       "(SELECT id FROM invoices WHERE student_id IN (:a,:b))"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM invoices WHERE student_id IN (:a,:b)"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM attendance WHERE student_id IN (:a,:b)"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM messages WHERE conversation_id IN "
                       "(SELECT id FROM conversations WHERE student_id IN (:a,:b))"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM conversation_members WHERE conversation_id IN "
                       "(SELECT id FROM conversations WHERE student_id IN (:a,:b))"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM notifications WHERE related_entity_id IN "
                       "(SELECT id FROM conversations WHERE student_id IN (:a,:b))"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM conversations WHERE student_id IN (:a,:b)"),
                  {"a": sid, "b": sid2})
        c.execute(text("DELETE FROM class_reports WHERE class_session_id IN "
                       "(SELECT id FROM class_sessions WHERE batch_id=:b)"),
                  {"b": asg["batch_id"]})
        c.execute(text("DELETE FROM class_sessions WHERE batch_id=:b"),
                  {"b": asg["batch_id"]})
        c.execute(text("DELETE FROM tutor_assignments WHERE batch_id=:b"),
                  {"b": asg["batch_id"]})
        c.execute(text("DELETE FROM batch_students WHERE batch_id=:b"),
                  {"b": asg["batch_id"]})
        c.execute(text("DELETE FROM batches WHERE id=:b"), {"b": asg["batch_id"]})
        c.execute(text("DELETE FROM courses WHERE name LIKE 'One-to-One%'"))
        c.execute(text("DELETE FROM users WHERE email LIKE :p"), {"p": f"{TAG}%"})

    # ---------------- Report ----------------
    passed = sum(1 for _, ok, _ in results if ok)
    print()
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        extra = f"   ({detail})" if detail else ""
        print(f"  [{mark}] {name}{extra}")
    print(f"\n  {passed}/{len(results)} requirements verified")

    with eng.connect() as c:
        left = c.execute(text("SELECT COUNT(*) FROM users WHERE email LIKE :p"),
                         {"p": f"{TAG}%"}).scalar_one()
    print(f"  test data left behind: {left} (must be 0)")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
