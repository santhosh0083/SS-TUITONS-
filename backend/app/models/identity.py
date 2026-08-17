"""Identity, roles, and the four role profiles.

Authorization rule enforced here: a single person may NOT hold both PARENT and
TUTOR. That rule is a database trigger (see the initial migration), not merely
application logic, so it survives application bugs.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Grade, RoleCode, UserStatus
from app.models.types import pg_enum


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[UserStatus] = mapped_column(
        pg_enum(UserStatus, "user_status"), nullable=False, default=UserStatus.PENDING
    )

    # The owner. Bypasses every visibility scope filter.
    is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Brute-force protection
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    parent: Mapped["Parent | None"] = relationship(back_populates="user", uselist=False)
    tutor: Mapped["Tutor | None"] = relationship(back_populates="user", uselist=False)

    @property
    def role_codes(self) -> set[RoleCode]:
        return {ur.role.code for ur in self.roles if ur.role is not None}


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    code: Mapped[RoleCode] = mapped_column(
        pg_enum(RoleCode, "role_code"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class UserRole(TimestampMixin, Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )

    user: Mapped[User] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship(lazy="joined")


class Student(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "students"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    admission_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    grade: Mapped[Grade] = mapped_column(pg_enum(Grade, "grade"), nullable=False)
    target_exam_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL")
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    school_name: Mapped[str | None] = mapped_column(String(200))
    joined_on: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped[User] = relationship(back_populates="student")
    parents: Mapped[list["StudentParent"]] = relationship(back_populates="student")


class Parent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    occupation: Mapped[str | None] = mapped_column(String(120))
    preferred_contact: Mapped[str | None] = mapped_column(String(20))

    user: Mapped[User] = relationship(back_populates="parent")
    children: Mapped[list["StudentParent"]] = relationship(back_populates="parent")


class Tutor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tutors"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    qualification: Mapped[str | None] = mapped_column(String(200))
    experience_years: Mapped[int | None] = mapped_column(Integer)
    bio: Mapped[str | None] = mapped_column(Text)

    # Defaults to False so a tutor's phone/email is never exposed to students or
    # parents unless the owner explicitly opts them in (spec section 25).
    is_contact_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    user: Mapped[User] = relationship(back_populates="tutor")


class StudentParent(TimestampMixin, Base):
    """Links a child to a parent. Drives the parent's entire visibility scope."""

    __tablename__ = "student_parents"
    __table_args__ = (UniqueConstraint("student_id", "parent_id"),)

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        primary_key=True,
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    student: Mapped[Student] = relationship(back_populates="parents")
    parent: Mapped[Parent] = relationship(back_populates="children")


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores only a hash of the token, never the token itself."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    ip_address: Mapped[str | None] = mapped_column(String(45))
