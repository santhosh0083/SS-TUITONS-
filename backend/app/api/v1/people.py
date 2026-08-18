"""Admin endpoints for managing students, parents and tutors."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.db.session import get_db
from app.models.identity import User
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
from app.services import people_service
from app.services.people_service import PeopleError

router = APIRouter()

AdminUser = Annotated[User, Depends(require_admin)]
Db = Annotated[AsyncSession, Depends(get_db)]


def _bad_request(exc: PeopleError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ---- Tutors ----


@router.get("/tutors", response_model=list[TutorSummary])
async def list_tutors(session: Db, _admin: AdminUser) -> list[TutorSummary]:
    return await people_service.list_tutors(session)


@router.post(
    "/tutors", response_model=PersonCreated, status_code=status.HTTP_201_CREATED
)
async def create_tutor(
    payload: TutorCreate, session: Db, admin: AdminUser
) -> PersonCreated:
    """Create a tutor account.

    The response contains a temporary password shown once. It is not stored in
    plaintext and cannot be retrieved later.
    """
    try:
        created = await people_service.create_tutor(
            session, payload=payload, actor_id=admin.id
        )
    except PeopleError as exc:
        raise _bad_request(exc) from exc
    await session.commit()
    return created


# ---- Parents ----


@router.get("/parents", response_model=list[ParentSummary])
async def list_parents(session: Db, _admin: AdminUser) -> list[ParentSummary]:
    return await people_service.list_parents(session)


@router.post(
    "/parents", response_model=PersonCreated, status_code=status.HTTP_201_CREATED
)
async def create_parent(
    payload: ParentCreate, session: Db, admin: AdminUser
) -> PersonCreated:
    try:
        created = await people_service.create_parent(
            session, payload=payload, actor_id=admin.id
        )
    except PeopleError as exc:
        raise _bad_request(exc) from exc
    await session.commit()
    return created


# ---- Students ----


@router.get("/students", response_model=list[StudentSummary])
async def list_students(session: Db, _admin: AdminUser) -> list[StudentSummary]:
    return await people_service.list_students(session)


@router.post(
    "/students", response_model=StudentCreated, status_code=status.HTTP_201_CREATED
)
async def create_student(
    payload: StudentCreate, session: Db, admin: AdminUser
) -> StudentCreated:
    """Create a student, optionally creating and linking a parent at the same
    time. Both temporary passwords are returned once."""
    try:
        created = await people_service.create_student(
            session, payload=payload, actor_id=admin.id
        )
    except PeopleError as exc:
        raise _bad_request(exc) from exc
    await session.commit()
    return created


@router.get("/exams", response_model=list[dict])
async def list_exams(session: Db, _admin: AdminUser) -> list[dict]:
    """Exam options for the student form."""
    from sqlalchemy import select

    from app.models.academics import Exam

    rows = (
        await session.execute(
            select(Exam.id, Exam.code, Exam.name)
            .where(Exam.is_active.is_(True))
            .order_by(Exam.name)
        )
    ).all()
    return [{"id": str(r.id), "code": r.code, "name": r.name} for r in rows]


@router.get("/subjects", response_model=list[dict])
async def list_subjects(session: Db, _admin: AdminUser) -> list[dict]:
    """Subject options for the assignment form."""
    from sqlalchemy import select

    from app.models.academics import Subject

    rows = (
        await session.execute(
            select(Subject.id, Subject.code, Subject.name)
            .where(Subject.is_active.is_(True))
            .order_by(Subject.name)
        )
    ).all()
    return [{"id": str(r.id), "code": r.code, "name": r.name} for r in rows]


@router.post("/users/{user_id}/reset-password", response_model=dict)
async def reset_password(user_id: uuid.UUID, session: Db, admin: AdminUser) -> dict:
    """Issue a new temporary password. Shown once; all sessions are revoked."""
    try:
        full_name, email, password = await people_service.reset_password(
            session, user_id=user_id, actor_id=admin.id
        )
    except PeopleError as exc:
        raise _bad_request(exc) from exc
    await session.commit()
    return {"full_name": full_name, "email": email, "temporary_password": password}


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def not_implemented_delete(student_id: uuid.UUID) -> None:
    """Deliberately not implemented.

    Deleting a student would cascade away their attendance, test attempts and
    payment history. Suspending the account is almost always what is wanted,
    and a real deletion path needs a data-retention decision first
    (docs/INTAKE.md Group J).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Students are suspended rather than deleted, so attendance, test "
            "and payment history is preserved."
        ),
    )
