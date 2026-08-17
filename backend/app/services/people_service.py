"""Creating and listing students, parents and tutors.

Account creation is deliberately centralised here rather than done per-route,
because every account has to get four things right at once: the user record,
the role, the profile row, and an audit entry. Doing that in three places
guarantees they drift apart.

Passwords are generated, hashed with Argon2id, and returned to the admin once.
The plaintext is never stored and cannot be recovered.
"""

import secrets
import string
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.academics import Batch, BatchStudent, TutorAssignment
from app.models.enums import EnrolmentStatus, RoleCode, UserStatus
from app.models.identity import (
    Parent,
    Role,
    Student,
    StudentParent,
    Tutor,
    User,
    UserRole,
)
from app.schemas.people import (
    ParentCreate,
    ParentSummary,
    PersonCreated,
    StudentCreate,
    StudentCreated,
    StudentSummary,
    TutorCreate,
    TutorSummary,
)
from app.services import audit


class PeopleError(Exception):
    """Message is safe to show an admin."""


# Ambiguous characters removed: these get read aloud and typed by hand.
_ALPHABET = (
    "".join(c for c in string.ascii_letters if c not in "lIO")
    + "".join(c for c in string.digits if c not in "01")
)


def _temp_password(length: int = 12) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


async def _role_id(session: AsyncSession, code: RoleCode) -> uuid.UUID:
    role = (
        await session.execute(select(Role).where(Role.code == code))
    ).scalar_one_or_none()
    if role is None:
        raise PeopleError(
            f"Role {code.value} is missing. Run: python -m scripts.seed"
        )
    return role.id


async def _create_user(
    session: AsyncSession,
    *,
    full_name: str,
    email: str,
    phone: str | None,
    role: RoleCode,
) -> tuple[User, str]:
    existing = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise PeopleError(f"An account already exists for {email}")

    password = _temp_password()
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        phone=phone,
        status=UserStatus.ACTIVE,
        is_superadmin=False,
        failed_login_count=0,
    )
    session.add(user)
    await session.flush()

    session.add(UserRole(user_id=user.id, role_id=await _role_id(session, role)))
    await session.flush()
    return user, password


async def _next_admission_no(session: AsyncSession) -> str:
    """Sequential per year, e.g. SS-2026-0007."""
    year = datetime.now(UTC).year
    prefix = f"SS-{year}-"
    count = (
        await session.execute(
            select(func.count())
            .select_from(Student)
            .where(Student.admission_no.like(f"{prefix}%"))
        )
    ).scalar_one()
    return f"{prefix}{count + 1:04d}"


# ---------------------------------------------------------------------------
# Tutors
# ---------------------------------------------------------------------------


async def create_tutor(
    session: AsyncSession, *, payload: TutorCreate, actor_id: uuid.UUID
) -> PersonCreated:
    user, password = await _create_user(
        session,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role=RoleCode.TUTOR,
    )

    tutor = Tutor(
        user_id=user.id,
        qualification=payload.qualification,
        experience_years=payload.experience_years,
        bio=payload.bio,
        is_contact_public=payload.is_contact_public,
    )
    session.add(tutor)

    try:
        await session.flush()
    except IntegrityError as exc:
        # The database enforces that a superadmin cannot hold a tutor profile,
        # and that nobody is both parent and tutor.
        await session.rollback()
        raise PeopleError(
            "This person cannot be made a tutor. A parent account cannot also "
            "be a tutor, and the owner account cannot teach."
        ) from exc

    await audit.record(
        session,
        action="tutor.created",
        entity_type="tutor",
        entity_id=tutor.id,
        actor_user_id=actor_id,
        after={"email": payload.email, "full_name": payload.full_name},
    )

    return PersonCreated(
        id=tutor.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        temporary_password=password,
    )


async def list_tutors(session: AsyncSession) -> list[TutorSummary]:
    rows = (
        await session.execute(
            select(Tutor, User).join(User, User.id == Tutor.user_id).order_by(User.full_name)
        )
    ).all()

    summaries: list[TutorSummary] = []
    for tutor, user in rows:
        batch_ids = (
            await session.execute(
                select(TutorAssignment.batch_id).where(
                    TutorAssignment.tutor_id == tutor.id,
                    TutorAssignment.revoked_on.is_(None),
                )
            )
        ).scalars().all()

        students = 0
        if batch_ids:
            students = (
                await session.execute(
                    select(func.count(func.distinct(BatchStudent.student_id))).where(
                        BatchStudent.batch_id.in_(batch_ids),
                        BatchStudent.status == EnrolmentStatus.ACTIVE,
                    )
                )
            ).scalar_one()

        summaries.append(
            TutorSummary(
                id=tutor.id,
                full_name=user.full_name,
                email=user.email,
                phone=user.phone,
                qualification=tutor.qualification,
                experience_years=tutor.experience_years,
                is_contact_public=tutor.is_contact_public,
                status=user.status,
                batches_assigned=len(set(batch_ids)),
                students_reached=students,
                created_at=tutor.created_at,
            )
        )
    return summaries


# ---------------------------------------------------------------------------
# Parents
# ---------------------------------------------------------------------------


async def create_parent(
    session: AsyncSession, *, payload: ParentCreate, actor_id: uuid.UUID
) -> PersonCreated:
    user, password = await _create_user(
        session,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role=RoleCode.PARENT,
    )
    parent = Parent(user_id=user.id, occupation=payload.occupation, preferred_contact=payload.phone)
    session.add(parent)

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise PeopleError(
            "This person cannot be made a parent. A tutor account cannot also "
            "be a parent."
        ) from exc

    await audit.record(
        session,
        action="parent.created",
        entity_type="parent",
        entity_id=parent.id,
        actor_user_id=actor_id,
        after={"email": payload.email},
    )
    return PersonCreated(
        id=parent.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        temporary_password=password,
    )


async def list_parents(session: AsyncSession) -> list[ParentSummary]:
    rows = (
        await session.execute(
            select(Parent, User).join(User, User.id == Parent.user_id).order_by(User.full_name)
        )
    ).all()

    out: list[ParentSummary] = []
    for parent, user in rows:
        children = (
            await session.execute(
                select(User.full_name)
                .join(Student, Student.user_id == User.id)
                .join(StudentParent, StudentParent.student_id == Student.id)
                .where(StudentParent.parent_id == parent.id)
            )
        ).scalars().all()
        out.append(
            ParentSummary(
                id=parent.id,
                full_name=user.full_name,
                email=user.email,
                phone=user.phone,
                status=user.status,
                children=list(children),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------


async def create_student(
    session: AsyncSession, *, payload: StudentCreate, actor_id: uuid.UUID
) -> StudentCreated:
    user, password = await _create_user(
        session,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role=RoleCode.STUDENT,
    )

    admission_no = payload.admission_no or await _next_admission_no(session)
    student = Student(
        user_id=user.id,
        admission_no=admission_no,
        grade=payload.grade,
        target_exam_id=payload.target_exam_id,
        school_name=payload.school_name,
        date_of_birth=payload.date_of_birth,
        joined_on=payload.joined_on or date.today(),
    )
    session.add(student)

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise PeopleError(
            f"Could not create the student. Admission number {admission_no} "
            "may already be in use."
        ) from exc

    # Optionally create and link the parent in the same operation.
    parent_created: PersonCreated | None = None
    if payload.parent_full_name and payload.parent_email:
        parent_created = await create_parent(
            session,
            payload=ParentCreate(
                full_name=payload.parent_full_name,
                email=payload.parent_email,
                phone=payload.parent_phone,
            ),
            actor_id=actor_id,
        )
        session.add(
            StudentParent(
                student_id=student.id,
                parent_id=parent_created.id,
                relationship_type=payload.parent_relationship,
                is_primary=True,
            )
        )
        await session.flush()

    await audit.record(
        session,
        action="student.created",
        entity_type="student",
        entity_id=student.id,
        actor_user_id=actor_id,
        after={"admission_no": admission_no, "grade": payload.grade.value},
    )

    return StudentCreated(
        id=student.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        temporary_password=password,
        admission_no=admission_no,
        parent=parent_created,
    )


async def list_students(session: AsyncSession) -> list[StudentSummary]:
    from app.models.academics import Exam  # local import avoids a cycle

    rows = (
        await session.execute(
            select(Student, User).join(User, User.id == Student.user_id).order_by(User.full_name)
        )
    ).all()

    out: list[StudentSummary] = []
    for student, user in rows:
        exam_name = None
        if student.target_exam_id:
            exam_name = (
                await session.execute(
                    select(Exam.name).where(Exam.id == student.target_exam_id)
                )
            ).scalar_one_or_none()

        batches = (
            await session.execute(
                select(Batch.code)
                .join(BatchStudent, BatchStudent.batch_id == Batch.id)
                .where(
                    BatchStudent.student_id == student.id,
                    BatchStudent.status == EnrolmentStatus.ACTIVE,
                )
            )
        ).scalars().all()

        parents = (
            await session.execute(
                select(User.full_name)
                .join(Parent, Parent.user_id == User.id)
                .join(StudentParent, StudentParent.parent_id == Parent.id)
                .where(StudentParent.student_id == student.id)
            )
        ).scalars().all()

        out.append(
            StudentSummary(
                id=student.id,
                full_name=user.full_name,
                email=user.email,
                phone=user.phone,
                admission_no=student.admission_no,
                grade=student.grade,
                school_name=student.school_name,
                target_exam=exam_name,
                status=user.status,
                joined_on=student.joined_on,
                batches=list(batches),
                parents=list(parents),
            )
        )
    return out
