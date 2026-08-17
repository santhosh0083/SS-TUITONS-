"""Strip personal information before anything leaves for an AI provider.

SS Tuitions students are children, and the free tiers of most providers may
use submitted data to improve their models. This module is the boundary: no
name, email, phone number, or student identifier crosses it.

The approach is deliberately allow-list shaped. Rather than trying to detect
and remove personal data from arbitrary text (which fails quietly the first
time someone writes their name in an unexpected format), callers pass only the
fields they intend to send, and this module scrubs what slips through anyway.
"""

import re
from dataclasses import dataclass

# Indian mobile numbers, with or without +91 and common separators.
_PHONE = re.compile(r"(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# Long digit runs: admission numbers, Aadhaar, account numbers.
_LONG_DIGITS = re.compile(r"\b\d{8,}\b")
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)

REDACTED = "[removed]"


@dataclass(frozen=True)
class ScrubResult:
    text: str
    removed_count: int

    @property
    def was_modified(self) -> bool:
        return self.removed_count > 0


def scrub(text: str, extra_terms: list[str] | None = None) -> ScrubResult:
    """Remove identifiers from text destined for an AI provider.

    `extra_terms` should carry the known names for this request — the student's
    own name, their parents' names — so a student writing "Hi, I'm Ananya and I
    don't understand this" has that removed too.
    """
    removed = 0
    cleaned = text

    for pattern in (_EMAIL, _PHONE, _UUID, _LONG_DIGITS):
        cleaned, n = pattern.subn(REDACTED, cleaned)
        removed += n

    for term in extra_terms or []:
        term = term.strip()
        # Two characters or fewer would match half the alphabet inside words.
        if len(term) < 3:
            continue
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        cleaned, n = pattern.subn(REDACTED, cleaned)
        removed += n

    return ScrubResult(text=cleaned, removed_count=removed)


def scrub_for_student(text: str, *, full_name: str, email: str) -> ScrubResult:
    """Scrub a student's message, including the parts of their own name.

    Name parts are passed individually so "Ananya" is caught even when the
    student never writes their surname.
    """
    terms = [*full_name.split(), full_name, email, email.split("@")[0]]
    return scrub(text, extra_terms=terms)
