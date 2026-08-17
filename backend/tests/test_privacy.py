"""Tests for the AI privacy boundary.

These matter more than most: a gap here means a child's name or phone number
reaches a third-party model that may train on it.
"""

from app.ai.privacy import scrub, scrub_for_student


class TestContactDetails:
    def test_email_removed(self) -> None:
        r = scrub("Contact me at ananya.reddy@gmail.com please")
        assert "ananya.reddy@gmail.com" not in r.text
        assert r.was_modified

    def test_indian_mobile_removed(self) -> None:
        for number in ["9876543210", "+91 9876543210", "98765-43210", "+919876543210"]:
            r = scrub(f"my number is {number}")
            assert "9876543210" not in r.text.replace(" ", "").replace("-", ""), number

    def test_uuid_removed(self) -> None:
        r = scrub("student 6ccd5e71-98c9-4091-ac00-fbae88bcafbd failed")
        assert "6ccd5e71" not in r.text

    def test_long_digit_run_removed(self) -> None:
        """Admission numbers, Aadhaar, account numbers."""
        r = scrub("admission number 202400187")
        assert "202400187" not in r.text


class TestStudentNames:
    def test_full_name_removed(self) -> None:
        r = scrub_for_student(
            "Hi, I am Ananya Reddy and I need help",
            full_name="Ananya Reddy",
            email="ananya@example.com",
        )
        assert "Ananya" not in r.text
        assert "Reddy" not in r.text

    def test_first_name_alone_removed(self) -> None:
        """A student rarely writes their surname."""
        r = scrub_for_student(
            "Ananya here, stuck on question 3",
            full_name="Ananya Reddy",
            email="ananya@example.com",
        )
        assert "Ananya" not in r.text

    def test_name_matched_case_insensitively(self) -> None:
        r = scrub_for_student(
            "ANANYA cannot solve this",
            full_name="Ananya Reddy",
            email="a@b.com",
        )
        assert "ANANYA" not in r.text


class TestPhysicsIsNotDamaged:
    """The scrubber must not mangle the actual question.

    Over-redaction is a real failure: a physics problem with its numbers
    removed is useless to the tutor.
    """

    def test_normal_numbers_survive(self) -> None:
        q = "A body of mass 5 kg accelerates at 2.5 m/s^2 for 10 seconds"
        assert scrub(q).text == q

    def test_equations_survive(self) -> None:
        q = "Solve x^2 - 5x + 6 = 0 and find the value of 1/2 mv^2"
        assert scrub(q).text == q

    def test_chemistry_notation_survives(self) -> None:
        q = "Balance: 2H2 + O2 -> 2H2O at 273 K and 101325 Pa"
        # 101325 is six digits, below the 8-digit redaction threshold.
        assert "101325" in scrub(q).text

    def test_short_name_fragments_do_not_over_match(self) -> None:
        """A two-letter name must not blank out ordinary words."""
        r = scrub("A body is at rest", extra_terms=["Al"])
        assert r.text == "A body is at rest"


class TestNothingToRemove:
    def test_clean_text_unchanged(self) -> None:
        q = "Explain Newton's second law with an example"
        r = scrub(q)
        assert r.text == q
        assert not r.was_modified
        assert r.removed_count == 0
