import unittest

from src.errors import ValidationError
from src.validation import (
    validate_age,
    validate_date,
    validate_diagnoses,
    validate_id,
    validate_name,
    validate_text,
)


class TestValidateName(unittest.TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(validate_name("  Anna   Grigoryan "), "Anna Grigoryan")

    def test_rejects_empty(self):
        for value in ("", "   ", "\t"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_name(value)

    def test_rejects_name_without_letters(self):
        with self.assertRaises(ValidationError):
            validate_name("12345")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            validate_name("a" * 101)

    def test_rejects_non_string(self):
        with self.assertRaises(ValidationError):
            validate_name(42)


class TestValidateAge(unittest.TestCase):
    def test_accepts_int_and_numeric_string(self):
        self.assertEqual(validate_age(30), 30)
        self.assertEqual(validate_age(" 30 "), 30)

    def test_accepts_boundaries(self):
        self.assertEqual(validate_age(0), 0)
        self.assertEqual(validate_age(130), 130)

    def test_rejects_out_of_range(self):
        for value in (-1, 131):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_age(value)

    def test_rejects_non_numeric(self):
        for value in ("abc", "", None, True):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_age(value)


class TestValidateDiagnoses(unittest.TestCase):
    def test_splits_comma_separated_string(self):
        self.assertEqual(validate_diagnoses("Asthma, Allergy"), ["Asthma", "Allergy"])

    def test_drops_empty_items_and_duplicates(self):
        self.assertEqual(validate_diagnoses("Asthma, , asthma, Flu"), ["Asthma", "Flu"])

    def test_accepts_none_and_list(self):
        self.assertEqual(validate_diagnoses(None), [])
        self.assertEqual(validate_diagnoses(["Flu"]), ["Flu"])

    def test_rejects_non_string_items(self):
        with self.assertRaises(ValidationError):
            validate_diagnoses([1, 2])


class TestValidateDate(unittest.TestCase):
    def test_accepts_iso_string(self):
        self.assertEqual(validate_date("2026-05-12"), "2026-05-12")

    def test_rejects_wrong_format(self):
        for value in ("12/05/2026", "2026-13-01", "not a date", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_date(value)

    def test_rejects_year_before_1900(self):
        with self.assertRaises(ValidationError):
            validate_date("1899-12-31")


class TestValidateTextAndId(unittest.TestCase):
    def test_optional_text_may_be_blank(self):
        self.assertEqual(validate_text("", "Notes", required=False), "")

    def test_required_text_may_not_be_blank(self):
        with self.assertRaises(ValidationError):
            validate_text("  ", "Reason")

    def test_id_must_be_positive(self):
        self.assertEqual(validate_id("7"), 7)
        for value in (0, -3, "abc", None):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_id(value)


if __name__ == "__main__":
    unittest.main()
