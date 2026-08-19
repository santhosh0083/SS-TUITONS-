"""Verify a running deployment without writing anything to it.

The full harness in verify_requirements.py creates students, classes, messages
and payments to prove the rules hold, then deletes them. That is the right
trade against a throwaway database and the wrong one against a database with
real students in it.

Everything here is a GET, plus the login itself. It cannot create, modify or
delete a record. What it gives up is the ability to prove a rule by violating
it; what it checks instead is that the deployment refuses what it should
refuse, and exposes only what it should expose.

Credentials come from .env (SS_VERIFY_EMAIL / SS_VERIFY_PASSWORD) and are
never printed.

Usage:

    cd backend
    ./.venv/Scripts/python -m scripts.verify_readonly
    SS_VERIFY_BASE_URL=https://example.onrender.com/api/v1 \
        ./.venv/Scripts/python -m scripts.verify_readonly
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

BASE = os.environ.get(
    "SS_VERIFY_BASE_URL", "https://ss-tuitons-1.onrender.com/api/v1"
).rstrip("/")
SITE = os.environ.get("SS_VERIFY_ORIGIN", "https://ss-tuitons.vercel.app")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: object, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def main() -> int:
    emailaddr = os.environ.get("SS_VERIFY_EMAIL", "")
    password = os.environ.get("SS_VERIFY_PASSWORD", "")
    if not emailaddr or not password:
        print("Set SS_VERIFY_EMAIL and SS_VERIFY_PASSWORD in .env first.")
        return 2

    print(f"target: {BASE}")
    print(f"origin: {SITE}\n")

    client = httpx.Client(timeout=90, headers={"Origin": SITE})

    # ---- Anonymous callers must be refused before we authenticate ----------
    for path in ("/admin/students", "/admin/tutors", "/admin/parents",
                 "/messages", "/payments/invoices", "/ai/history"):
        r = client.get(f"{BASE}{path}")
        check(f"anonymous refused {path}", r.status_code in (401, 403, 404),
              f"HTTP {r.status_code}")

    # ---- Login -------------------------------------------------------------
    r = client.post(f"{BASE}/auth/login",
                    json={"email": emailaddr, "password": password})
    if r.status_code != 200:
        print(f"Login failed: HTTP {r.status_code} {r.text[:200]}")
        print("\nNothing else can be checked without a session.")
        print("Careful: five failures locks the account for 15 minutes.")
        return 1

    check("owner can sign in", True, "HTTP 200")
    token = r.json().get("access_token", "")
    check("access token issued", bool(token))

    # The cross-site cookie is the failure that looks like success.
    cookie = next(
        (c for c in r.headers.get_list("set-cookie") if "refresh" in c.lower()), ""
    )
    flat = cookie.lower().replace(" ", "")
    check("refresh cookie set", bool(cookie))
    check("refresh cookie HttpOnly", "httponly" in flat)
    check("refresh cookie Secure", "secure" in flat)
    check("refresh cookie SameSite=None", "samesite=none" in flat)

    auth = {"Authorization": f"Bearer {token}", "Origin": SITE}

    # ---- Identity ----------------------------------------------------------
    r = client.get(f"{BASE}/auth/me", headers=auth)
    me = r.json() if r.status_code == 200 else {}
    check("/auth/me responds", r.status_code == 200, f"HTTP {r.status_code}")
    check("signed in as the right account",
          str(me.get("email", "")).lower() == emailaddr.lower(),
          str(me.get("email", "")))
    check("account is not stuck on password change",
          me.get("must_change_password") in (False, None),
          str(me.get("must_change_password")))

    # ---- A tampered token must not be accepted ----------------------------
    r = client.get(f"{BASE}/auth/me",
                   headers={"Authorization": f"Bearer {token[:-8]}AAAAAAAA",
                            "Origin": SITE})
    check("tampered token refused", r.status_code in (401, 403),
          f"HTTP {r.status_code}")

    # ---- Owner reads ------------------------------------------------------
    seen: dict[str, object] = {}
    for path, label in [("/admin/overview", "overview"),
                        ("/admin/students", "students"),
                        ("/admin/tutors", "tutors"),
                        ("/admin/parents", "parents"),
                        ("/admin/subjects", "subjects"),
                        ("/messages", "conversations"),
                        ("/messages/unread-count", "unread count"),
                        ("/attendance/discrepancies", "attendance disputes"),
                        ("/payments/invoices", "invoices"),
                        ("/payments/claims", "payment claims"),
                        ("/classes/mine", "own classes")]:
        r = client.get(f"{BASE}{path}", headers=auth)
        ok = r.status_code == 200
        size = ""
        if ok:
            try:
                data = r.json()
                seen[label] = data
                size = f"{len(data)} rows" if isinstance(data, list) else "object"
            except ValueError:
                # A 200 that is not JSON is worth knowing about, but it does
                # not make the read itself a failure.
                size = "non-JSON body"
        check(f"owner can read {label}", ok, f"HTTP {r.status_code} {size}".strip())

    # ---- Grades 1-12 ------------------------------------------------------
    subjects = seen.get("subjects")
    grades = set()
    if isinstance(subjects, list):
        for s in subjects:
            g = s.get("grade") if isinstance(s, dict) else None
            if isinstance(g, int):
                grades.add(g)
    if grades:
        check("grades cover 1 to 12", min(grades) <= 1 <= 12 <= max(grades),
              f"{min(grades)}-{max(grades)}")

    # ---- Payment details must be real -------------------------------------
    r = client.get(f"{BASE}/payments/details", headers=auth)
    if r.status_code == 200:
        d = r.json()
        blob = str(d).upper()
        check("payment details configured", d.get("configured") is True)
        check("no placeholder in payment details",
              "CONFIGURE_ME" not in blob and "CHANGE_ME" not in blob)
    else:
        check("payment details readable", False, f"HTTP {r.status_code}")

    # ---- Tutor identities must not leak ------------------------------------
    students = seen.get("students")
    if isinstance(students, list) and students:
        blob = str(students).lower()
        check("student list carries no tutor email",
              "@" not in blob or "tutor_email" not in blob)

    # ---- The AI tutor is for students -------------------------------------
    r = client.get(f"{BASE}/ai/status", headers=auth)
    check("AI status readable", r.status_code == 200, f"HTTP {r.status_code}")
    r = client.get(f"{BASE}/ai/history", headers=auth)
    check("owner is not treated as a student", r.status_code in (403, 404),
          f"HTTP {r.status_code}")

    # ---- Nothing internal leaks in errors ---------------------------------
    r = client.get(f"{BASE}/not-a-real-route", headers=auth)
    lowered = r.text.lower()
    check("error body leaks nothing",
          not any(w in lowered for w in
                  ("traceback", "sqlalchemy", "asyncpg", "postgres", "/app/")))

    # ---- Report -----------------------------------------------------------
    print(f"{'RESULT':8} CHECK")
    print("-" * 70)
    failed = 0
    for name, ok, detail in results:
        if not ok:
            failed += 1
        print(f"{'PASS' if ok else 'FAIL':8} {name}" + (f"   [{detail}]" if detail else ""))
    print("-" * 70)
    print(f"{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
