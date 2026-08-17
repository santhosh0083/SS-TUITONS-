"""The visibility policy layer.

Every read of student-scoped data resolves through this module. Routes must not
query student data any other way.

The reasoning: this platform has roughly 150 endpoints touching student data,
and most of its users are minors. Re-checking permissions inside each endpoint
means ~150 chances to forget one, and a single omission leaks a child's records.
Here there is one function to get right and one place to audit.

    Admin   -> every student
    Tutor   -> only students in batches they hold a LIVE tutor_assignment for
    Parent  -> only children linked via student_parents
    Student -> only themselves
    Anyone else -> nothing

Scopes are computed from live database state, never from JWT claims. Revoking a
tutor's assignment takes effect on their next request, not when their token
expires.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, false, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.academics import BatchStudent, TutorAssignment
from app.models.enums import EnrolmentStatus, RoleCode
from app.models.identity import Parent, Student, StudentParent, Tutor, User


class AccessDenied(Exception):
    """Raised when a caller requests a specific student they cannot see."""


@dataclass(frozen=True)
class StudentScope:
    """The set of students a caller may access.

    Either unrestricted (admin), or defined by a subquery of student ids.
    `deny_all` is represented by an unrestricted=False scope with a subquery
    that matches nothing, so callers never have to special-case it.
    """

    unrestricted: bool
    student_ids: Select | None

    @property
    def is_denied(self) -> bool:
        return not self.unrestricted and self.student_ids is None

    @classmethod
    def all_students(cls) -> StudentScope:
        return cls(unrestricted=True, student_ids=None)

    @classmethod
    def none(cls) -> StudentScope:
        return cls(unrestricted=False, student_ids=None)

    @classmethod
    def limited_to(cls, subquery: Select) -> StudentScope:
        return cls(unrestricted=False, student_ids=subquery)


# ---------------------------------------------------------------------------
# Per-role subqueries
# ---------------------------------------------------------------------------


def _tutor_visible_students(user_id: uuid.UUID) -> Select:
    """Students in batches this tutor currently teaches.

    Two conditions matter and both are easy to forget:
      - the assignment must not be revoked (`revoked_on IS NULL`)
      - the enrolment must be active, so a withdrawn student disappears
    """
    return (
        select(BatchStudent.student_id)
        .join(TutorAssignment, TutorAssignment.batch_id == BatchStudent.batch_id)
        .join(Tutor, Tutor.id == TutorAssignment.tutor_id)
        .where(
            Tutor.user_id == user_id,
            TutorAssignment.revoked_on.is_(None),
            BatchStudent.status == EnrolmentStatus.ACTIVE,
        )
    )


def _parent_visible_students(user_id: uuid.UUID) -> Select:
    """Children linked to this parent."""
    return (
        select(StudentParent.student_id)
        .join(Parent, Parent.id == StudentParent.parent_id)
        .where(Parent.user_id == user_id)
    )


def _student_visible_students(user_id: uuid.UUID) -> Select:
    """A student sees only themselves."""
    return select(Student.id).where(Student.user_id == user_id)


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def resolve_student_scope(user: User) -> StudentScope:
    """Resolve which students `user` may access.

    Role precedence is deliberate: admin wins, then tutor, then parent, then
    student. Parent and tutor are mutually exclusive at the database level, so
    that pair can never actually collide.
    """
    if user.is_superadmin:
        return StudentScope.all_students()

    roles = user.role_codes

    if RoleCode.ADMIN in roles:
        return StudentScope.all_students()
    if RoleCode.TUTOR in roles:
        return StudentScope.limited_to(_tutor_visible_students(user.id))
    if RoleCode.PARENT in roles:
        return StudentScope.limited_to(_parent_visible_students(user.id))
    if RoleCode.STUDENT in roles:
        return StudentScope.limited_to(_student_visible_students(user.id))

    return StudentScope.none()


def apply_student_scope(
    stmt: Select,
    student_id_column: ColumnElement[uuid.UUID],
    scope: StudentScope,
) -> Select:
    """Constrain a query to the students the caller may see.

    Usage:

        scope = resolve_student_scope(current_user)
        stmt = apply_student_scope(
            select(Attendance), Attendance.student_id, scope
        )

    An admin's query is returned unchanged. A denied caller gets a query that
    returns nothing — deliberately an empty result rather than an exception, so
    list endpoints degrade to "no rows" instead of leaking existence through an
    error.
    """
    if scope.unrestricted:
        return stmt
    if scope.student_ids is None:
        return stmt.where(false())
    return stmt.where(student_id_column.in_(scope.student_ids))


def scope_permits_student(scope: StudentScope, student_id: uuid.UUID) -> Select | None:
    """Build a query that returns the student id only if the scope allows it.

    For single-record endpoints, where "not found" and "not permitted" must be
    indistinguishable to the caller. Returns None when the scope is unrestricted
    and no check is needed.
    """
    if scope.unrestricted:
        return None
    if scope.student_ids is None:
        return select(Student.id).where(false())
    return select(Student.id).where(
        Student.id == student_id, Student.id.in_(scope.student_ids)
    )
