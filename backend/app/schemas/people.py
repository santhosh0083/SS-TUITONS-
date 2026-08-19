"""Contracts for creating and listing students, parents and tutors."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Grade, UserStatus


class PersonCreated(BaseModel):
    """Returned once, immediately after creating an account.

    `temporary_password` is generated server-side and shown to the admin a
    single time. Only its Argon2id hash is stored, so it cannot be retrieved
    later — the admin must pass it on now or reset it.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: EmailStr
    temporary_password: str


# ---------------------------------------------------------------------------
# Tutors
# ---------------------------------------------------------------------------


class TutorCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    qualification: str | None = Field(default=None, max_length=200)
    experience_years: int | None = Field(default=None, ge=0, le=60)
    bio: str | None = None
    # Defaults false: a tutor's contact details are never exposed to students
    # or parents unless the owner deliberately opts them in.
    is_contact_public: bool = False


class TutorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # The profile row id (tutors/parents/students) and the sign-in account
    # id are different. Account actions -- removal, password reset -- key on
    # user_id, so it has to be on the wire or the UI cannot call them.
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    qualification: str | None
    experience_years: int | None
    is_contact_public: bool
    status: UserStatus
    batches_assigned: int
    students_reached: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    grade: Grade
    admission_no: str | None = Field(
        default=None,
        max_length=30,
        description="Generated automatically when omitted",
    )
    target_exam_id: uuid.UUID | None = None
    school_name: str | None = Field(default=None, max_length=200)
    date_of_birth: date | None = None
    joined_on: date | None = None

    # Optionally create and link a parent in the same step. Most enrolments
    # add both at once, and a student without a linked parent means the parent
    # cannot see their child's progress.
    parent_full_name: str | None = Field(default=None, max_length=200)
    parent_email: EmailStr | None = None
    parent_phone: str | None = Field(default=None, max_length=20)
    parent_relationship: str = Field(default="guardian", max_length=20)


class StudentCreated(PersonCreated):
    admission_no: str
    parent: PersonCreated | None = None


class StudentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # The profile row id (tutors/parents/students) and the sign-in account
    # id are different. Account actions -- removal, password reset -- key on
    # user_id, so it has to be on the wire or the UI cannot call them.
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    admission_no: str
    grade: Grade
    school_name: str | None
    target_exam: str | None
    status: UserStatus
    joined_on: date
    batches: list[str]
    parents: list[str]


# ---------------------------------------------------------------------------
# Parents
# ---------------------------------------------------------------------------


class ParentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    occupation: str | None = Field(default=None, max_length=120)


class ParentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # The profile row id (tutors/parents/students) and the sign-in account
    # id are different. Account actions -- removal, password reset -- key on
    # user_id, so it has to be on the wire or the UI cannot call them.
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    status: UserStatus
    children: list[str]


class LinkParentRequest(BaseModel):
    parent_id: uuid.UUID
    relationship_type: str = Field(default="guardian", max_length=20)
    is_primary: bool = False
