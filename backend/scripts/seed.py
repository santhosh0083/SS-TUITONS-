"""Seed reference data and create the owner account.

Run once after `alembic upgrade head`:

    ./.venv/Scripts/python -m scripts.seed --email you@example.com

Seeds the four roles plus the exam and subject reference tables, then creates a
single superadmin account for the owner.

The password is generated here and printed once. It is never written to a file,
never committed, and cannot be recovered afterwards — copy it immediately and
change it after your first sign-in.

Safe to re-run: existing rows are left untouched.
"""

import argparse
import asyncio
import secrets
import string
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.academics import Exam, Subject
from app.models.enums import RoleCode, UserStatus
from app.models.identity import Role, User, UserRole

ROLES: list[tuple[RoleCode, str, str]] = [
    (RoleCode.ADMIN, "Administrator", "Full access to every part of the platform"),
    (RoleCode.TUTOR, "Tutor", "Teaches assigned batches; cannot administer"),
    (RoleCode.PARENT, "Parent", "Views their own children's progress"),
    (RoleCode.STUDENT, "Student", "Attends classes and takes tests"),
]

EXAMS: list[tuple[str, str]] = [
    ("JEE_MAIN", "JEE Main"),
    ("JEE_ADVANCED", "JEE Advanced"),
    ("EAMCET", "TG EAPCET / EAMCET"),
    ("IPE", "Intermediate Public Examination"),
    ("NEET", "NEET"),
    ("SAT", "SAT"),
]

SUBJECTS: list[tuple[str, str]] = [
    ("PHY", "Physics"),
    ("CHEM", "Chemistry"),
    ("MATH", "Mathematics"),
    ("BIO", "Biology"),
]


def generate_password(length: int = 20) -> str:
    """A strong random password. Ambiguous characters are excluded so it can be
    read off a screen and typed without confusion."""
    alphabet = (
        "".join(c for c in string.ascii_letters if c not in "lIO")
        + "".join(c for c in string.digits if c not in "01")
        + "!@#$%^&*-_=+"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def seed(email: str, full_name: str) -> int:
    created: list[str] = []
    skipped: list[str] = []

    async with SessionLocal() as session:
        # ---- Roles ----
        for code, name, description in ROLES:
            existing = (
                await session.execute(select(Role).where(Role.code == code))
            ).scalar_one_or_none()
            if existing is None:
                session.add(Role(code=code, name=name, description=description))
                created.append(f"role {code.value}")
            else:
                skipped.append(f"role {code.value}")

        # ---- Exams ----
        for exam_code, exam_name in EXAMS:
            existing_exam = (
                await session.execute(select(Exam).where(Exam.code == exam_code))
            ).scalar_one_or_none()
            if existing_exam is None:
                session.add(Exam(code=exam_code, name=exam_name, is_active=True))
                created.append(f"exam {exam_code}")
            else:
                skipped.append(f"exam {exam_code}")

        # ---- Subjects ----
        for subject_code, subject_name in SUBJECTS:
            existing_subject = (
                await session.execute(
                    select(Subject).where(Subject.code == subject_code)
                )
            ).scalar_one_or_none()
            if existing_subject is None:
                session.add(
                    Subject(code=subject_code, name=subject_name, is_active=True)
                )
                created.append(f"subject {subject_code}")
            else:
                skipped.append(f"subject {subject_code}")

        await session.flush()

        # ---- Owner account ----
        existing_user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

        password: str | None = None
        if existing_user is None:
            password = generate_password()
            owner = User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                status=UserStatus.ACTIVE,
                is_superadmin=True,
                failed_login_count=0,
                last_login_at=None,
            )
            session.add(owner)
            await session.flush()

            admin_role = (
                await session.execute(
                    select(Role).where(Role.code == RoleCode.ADMIN)
                )
            ).scalar_one()
            session.add(UserRole(user_id=owner.id, role_id=admin_role.id))
            created.append(f"owner account {email}")
        else:
            skipped.append(f"owner account {email} (already exists)")

        await session.commit()

    print(f"\nSeed completed at {datetime.now(UTC).isoformat(timespec='seconds')}\n")
    if created:
        print("Created:")
        for item in created:
            print(f"  + {item}")
    if skipped:
        print("\nAlready present (unchanged):")
        for item in skipped:
            print(f"  = {item}")

    if password is not None:
        print("\n" + "=" * 62)
        print("  OWNER SIGN-IN DETAILS - SHOWN ONCE, COPY THEM NOW")
        print("=" * 62)
        print(f"  Email    : {email}")
        print(f"  Password : {password}")
        print("=" * 62)
        print("  This password is not stored anywhere and cannot be recovered.")
        print("  Change it after your first sign-in.")
        print("=" * 62 + "\n")
    else:
        print(
            "\nNo new password generated - that account already existed.\n"
            "If you are locked out, create a new admin or reset the hash directly.\n"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed SS Tuitions reference data.")
    parser.add_argument("--email", required=True, help="Owner's sign-in email")
    parser.add_argument("--name", default="SS Tuitions Owner", help="Owner's full name")
    args = parser.parse_args()

    if "@" not in args.email:
        print(f"'{args.email}' does not look like an email address.", file=sys.stderr)
        return 2

    return asyncio.run(seed(args.email, args.name))


if __name__ == "__main__":
    sys.exit(main())
