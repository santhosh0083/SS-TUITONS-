"""Tests for the guards on removing someone from the dashboard.

Removal suspends an account rather than deleting it, and every guard here
refuses before touching the database, so they can be tested without one.

The two that matter are locking yourself out and losing the owner. Both are
recoverable only by editing the database by hand, which is exactly the
situation a business owner cannot get themselves out of at 9pm.
"""

import uuid

import pytest

from app.models.enums import UserStatus
from app.services import people_service
from app.services.people_service import PeopleError


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    """The smallest thing remove_person can look a user up in."""

    def __init__(self, user):
        self._user = user

    async def execute(self, _statement):
        return _Result(self._user)


class _User:
    def __init__(self, *, is_superadmin=False, status=UserStatus.ACTIVE, name="Sai"):
        self.id = uuid.uuid4()
        self.full_name = name
        self.is_superadmin = is_superadmin
        self.status = status


@pytest.mark.asyncio
class TestRemovalGuards:
    async def test_owner_cannot_be_removed(self) -> None:
        owner = _User(is_superadmin=True, name="Santhosh")
        with pytest.raises(PeopleError, match="owner"):
            await people_service.remove_person(
                _Session(owner), user_id=owner.id, actor_id=uuid.uuid4()
            )
        assert owner.status is UserStatus.ACTIVE

    async def test_cannot_remove_yourself(self) -> None:
        # Otherwise the only admin can suspend the account they are using and
        # lock themselves out of their own platform.
        admin = _User(name="Admin")
        with pytest.raises(PeopleError, match="your own"):
            await people_service.remove_person(
                _Session(admin), user_id=admin.id, actor_id=admin.id
            )
        assert admin.status is UserStatus.ACTIVE

    async def test_missing_account_is_reported(self) -> None:
        with pytest.raises(PeopleError, match="no longer exists"):
            await people_service.remove_person(
                _Session(None), user_id=uuid.uuid4(), actor_id=uuid.uuid4()
            )

    async def test_removing_twice_is_refused(self) -> None:
        # A second removal would revoke assignments again and write a
        # misleading audit entry claiming they were active beforehand.
        gone = _User(status=UserStatus.SUSPENDED, name="Ravi")
        with pytest.raises(PeopleError, match="already been removed"):
            await people_service.remove_person(
                _Session(gone), user_id=gone.id, actor_id=uuid.uuid4()
            )


@pytest.mark.asyncio
class TestRestoreGuards:
    async def test_restoring_someone_active_is_refused(self) -> None:
        active = _User(name="Meera")
        with pytest.raises(PeopleError, match="not removed"):
            await people_service.restore_person(
                _Session(active), user_id=active.id, actor_id=uuid.uuid4()
            )

    async def test_missing_account_is_reported(self) -> None:
        with pytest.raises(PeopleError, match="no longer exists"):
            await people_service.restore_person(
                _Session(None), user_id=uuid.uuid4(), actor_id=uuid.uuid4()
            )
