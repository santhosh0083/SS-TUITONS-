"""Shared column type helpers."""

import enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=enum.Enum)

# Enum instances are cached by type name. Several enums (Grade, Difficulty,
# AttendanceMark, MLTask, PaymentMethod) are used on more than one column, and
# a distinct SAEnum object per column would make SQLAlchemy emit CREATE TYPE
# once per usage — which fails on the second statement with "type already
# exists". Reusing one instance per name emits it exactly once.
_ENUM_CACHE: dict[str, SAEnum] = {}


def pg_enum(python_enum: type[E], type_name: str) -> SAEnum:
    """Native PostgreSQL enum backed by a Python enum.

    Persists the enum *value* (e.g. "mcq_single") rather than the member *name*
    (e.g. "MCQ_SINGLE"), which keeps stored data readable in raw SQL.
    """
    cached = _ENUM_CACHE.get(type_name)
    if cached is not None:
        return cached

    created = SAEnum(
        python_enum,
        name=type_name,
        native_enum=True,
        values_callable=lambda e: [member.value for member in e],
        validate_strings=True,
    )
    _ENUM_CACHE[type_name] = created
    return created
