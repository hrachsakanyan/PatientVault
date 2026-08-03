import json
import unittest

from src.errors import ValidationError
from src.models import Patient, Visit


class TestVisit(unittest.TestCase):
    def make_visit(self, **overrides):
        data = {"patient_id": 1, "visit_date": "2026-05-12", "reason": "Ear pain"}
        data.update(overrides)
        return Visit(**data)

    def test_new_visit_has_no_id(self):
        self.assertIsNone(self.make_visit().id)

    def test_setters_validate(self):
        visit = self.make_visit()
        with self.assertRaises(ValidationError):
            visit.visit_date = "12/05/2026"
        with self.assertRaises(ValidationError):
            visit.reason = ""
        with self.assertRaises(ValidationError):
            visit.patient_id = 0

    def test_notes_are_optional(self):
        self.assertEqual(self.make_visit().notes, "")

    def test_from_row_round_trip(self):
        visit = self.make_visit(notes="Antibiotics", visit_id=5, created_at="2026-05-12T10:00:00")
        restored = Visit.from_row(visit.to_dict())
        self.assertEqual(visit, restored)

    def test_str_contains_date_and_reason(self):
        text = str(self.make_visit())
        self.assertIn("2026-05-12", text)
        self.assertIn("Ear pain", text)


class TestPatient(unittest.TestCase):
    def make_patient(self, **overrides):
        data = {"name": "Anna Grigoryan", "age": 34, "diagnoses": "Asthma, Allergy"}
        data.update(overrides)
        return Patient(**data)

    def test_construction_normalises_fields(self):
        patient = self.make_patient(name="  anna   grigoryan ")
        self.assertEqual(patient.name, "anna grigoryan")
        self.assertEqual(patient.diagnoses, ("Asthma", "Allergy"))
        self.assertIsNone(patient.id)

    def test_setters_validate(self):
        patient = self.make_patient()
        with self.assertRaises(ValidationError):
            patient.age = 200
        with self.assertRaises(ValidationError):
            patient.name = ""

    def test_diagnoses_are_immutable_from_outside(self):
        patient = self.make_patient()
        self.assertIsInstance(patient.diagnoses, tuple)

    def test_add_and_remove_diagnosis(self):
        patient = self.make_patient(diagnoses="Asthma")
        patient.add_diagnosis("Flu")
        patient.add_diagnosis("flu")  # duplicate, case-insensitive
        self.assertEqual(patient.diagnoses, ("Asthma", "Flu"))
        self.assertTrue(patient.remove_diagnosis("ASTHMA"))
        self.assertFalse(patient.remove_diagnosis("Nothing"))
        self.assertEqual(patient.diagnoses, ("Flu",))

    def test_add_visit_composition(self):
        patient = self.make_patient(patient_id=1)
        patient.add_visit(Visit(patient_id=1, visit_date="2026-01-01", reason="Check-up"))
        self.assertEqual(patient.visit_count, 1)

    def test_add_visit_rejects_foreign_visit(self):
        patient = self.make_patient(patient_id=1)
        with self.assertRaises(ValidationError):
            patient.add_visit(Visit(patient_id=2, visit_date="2026-01-01", reason="Check-up"))

    def test_add_visit_rejects_non_visit(self):
        with self.assertRaises(ValidationError):
            self.make_patient().add_visit("not a visit")

    def test_visits_are_sorted_newest_first(self):
        patient = self.make_patient(patient_id=1)
        for day in ("2026-01-01", "2026-03-01", "2026-02-01"):
            patient.add_visit(Visit(patient_id=1, visit_date=day, reason="Check-up"))
        self.assertEqual(
            [v.visit_date for v in patient.visits],
            ["2026-03-01", "2026-02-01", "2026-01-01"],
        )
        self.assertEqual(patient.last_visit_date, "2026-03-01")

    def test_last_visit_date_is_none_without_visits(self):
        self.assertIsNone(self.make_patient().last_visit_date)

    def test_diagnoses_json_round_trip(self):
        patient = self.make_patient()
        self.assertEqual(json.loads(patient.diagnoses_json()), ["Asthma", "Allergy"])

    def test_from_row_reads_json_diagnoses(self):
        row = {
            "id": 3,
            "name": "Anna",
            "age": 34,
            "diagnoses": '["Asthma"]',
            "created_at": "2026-01-01T09:00:00",
        }
        patient = Patient.from_row(row)
        self.assertEqual(patient.id, 3)
        self.assertEqual(patient.diagnoses, ("Asthma",))

    def test_from_row_survives_broken_json(self):
        row = {"id": 3, "name": "Anna", "age": 34, "diagnoses": "not json", "created_at": ""}
        self.assertEqual(Patient.from_row(row).diagnoses, ())

    def test_to_dict_includes_visits(self):
        patient = self.make_patient(patient_id=1)
        patient.add_visit(Visit(patient_id=1, visit_date="2026-01-01", reason="Check-up"))
        data = patient.to_dict()
        self.assertEqual(len(data["visits"]), 1)
        self.assertNotIn("visits", patient.to_dict(include_visits=False))


if __name__ == "__main__":
    unittest.main()
