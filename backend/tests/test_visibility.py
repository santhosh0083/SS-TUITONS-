"""Tests for the visibility policy layer.

These compile the generated SQL and inspect it. That is deliberate: the whole
point of this layer is which rows a query can reach, and the SQL is the
artifact that decides it. A wrong scope here leaks a minor's records, so the
conditions are asserted individually rather than trusting the query "looks
right".
"""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models.enums import RoleCode
from app.models.identity import Role, Student, User, UserRole
from app.models.scheduling import Attendance
from app.services.visibility import (
    StudentScope,
    apply_student_scope,
    resolve_student_scope,
    scope_permits_student,
)


def _compile(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()


def _user(role: RoleCode | None, *, superadmin: bool = False) -> User:
    """An unsaved User wired up with one role, enough for scope resolution."""
    user = User(
        id=uuid.uuid4(),
        email="x@example.com",
        password_hash="x",
        full_name="Test",
        is_superadmin=superadmin,
    )
    if role is not None:
        user.roles = [UserRole(user_id=user.id, role=Role(code=role, name=role.value))]
    else:
        user.roles = []
    return user


class TestAdminScope:
    def test_superadmin_is_unrestricted(self) -> None:
        assert resolve_student_scope(_user(None, superadmin=True)).unrestricted

    def test_admin_role_is_unrestricted(self) -> None:
        assert resolve_student_scope(_user(RoleCode.ADMIN)).unrestricted

    def test_admin_query_is_left_untouched(self) -> None:
        scope = StudentScope.all_students()
        stmt = select(Attendance)
        assert _compile(apply_student_scope(stmt, Attendance.student_id, scope)) == (
            _compile(stmt)
        )


class TestTutorScope:
    def test_tutor_scope_is_restricted(self) -> None:
        assert not resolve_student_scope(_user(RoleCode.TUTOR)).unrestricted

    def test_tutor_scope_excludes_revoked_assignments(self) -> None:
        """A revoked assignment must stop granting access immediately."""
        scope = resolve_student_scope(_user(RoleCode.TUTOR))
        assert scope.student_ids is not None
        sql = _compile(scope.student_ids)
        assert "revoked_on is null" in sql

    def test_tutor_scope_excludes_withdrawn_students(self) -> None:
        scope = resolve_student_scope(_user(RoleCode.TUTOR))
        assert scope.student_ids is not None
        sql = _compile(scope.student_ids)
        assert "batch_students.status" in sql
        assert "active" in sql

    def test_tutor_scope_goes_through_tutor_assignments(self) -> None:
        scope = resolve_student_scope(_user(RoleCode.TUTOR))
        assert scope.student_ids is not None
        assert "tutor_assignments" in _compile(scope.student_ids)


class TestParentScope:
    def test_parent_scope_uses_student_parents_link(self) -> None:
        scope = resolve_student_scope(_user(RoleCode.PARENT))
        assert scope.student_ids is not None
        assert "student_parents" in _compile(scope.student_ids)

    def test_parent_scope_is_restricted(self) -> None:
        assert not resolve_student_scope(_user(RoleCode.PARENT)).unrestricted


class TestStudentScope:
    def test_student_sees_only_themselves(self) -> None:
        user = _user(RoleCode.STUDENT)
        scope = resolve_student_scope(user)
        assert scope.student_ids is not None
        sql = _compile(scope.student_ids)
        assert "students.user_id" in sql
        assert str(user.id) in sql
        # Must not reach through batches or parent links.
        assert "tutor_assignments" not in sql
        assert "student_parents" not in sql


class TestNoRoleIsDeniedByDefault:
    """A user with no recognised role must see nothing, not everything."""

    def test_roleless_user_is_denied(self) -> None:
        scope = resolve_student_scope(_user(None))
        assert scope.is_denied
        assert not scope.unrestricted

    def test_denied_scope_filters_everything_out(self) -> None:
        scope = StudentScope.none()
        sql = _compile(apply_student_scope(select(Attendance), Attendance.student_id, scope))
        assert "where false" in sql


class TestApplyScope:
    def test_restricted_scope_adds_in_clause(self) -> None:
        scope = resolve_student_scope(_user(RoleCode.PARENT))
        sql = _compile(apply_student_scope(select(Attendance), Attendance.student_id, scope))
        assert "attendance.student_id in" in sql

    def test_scope_applies_to_any_student_column(self) -> None:
        """The helper must work for any table carrying a student_id."""
        scope = resolve_student_scope(_user(RoleCode.TUTOR))
        sql = _compile(apply_student_scope(select(Student), Student.id, scope))
        assert "students.id in" in sql


class TestSingleRecordChecks:
    def test_admin_needs_no_check(self) -> None:
        assert scope_permits_student(StudentScope.all_students(), uuid.uuid4()) is None

    def test_denied_scope_matches_nothing(self) -> None:
        stmt = scope_permits_student(StudentScope.none(), uuid.uuid4())
        assert stmt is not None
        assert "where false" in _compile(stmt)

    def test_restricted_scope_checks_membership(self) -> None:
        scope = resolve_student_scope(_user(RoleCode.PARENT))
        target = uuid.uuid4()
        stmt = scope_permits_student(scope, target)
        assert stmt is not None
        sql = _compile(stmt)
        assert str(target) in sql
        assert "in (select" in sql
