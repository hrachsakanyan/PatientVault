import tempfile
import unittest
from pathlib import Path

from src.errors import (
    PatientNotFoundError,
    RepositoryError,
    ValidationError,
    VisitNotFoundError,
)
from src.models import Patient, Visit
from src.repository import PatientRepository


class RepositoryTestCase(unittest.TestCase):
    """Base class: every test gets a fresh in-memory database."""

    def setUp(self):
        self.repo = PatientRepository(":memory:")
        self.addCleanup(self.repo.close)

    def add_patient(self, name="Anna Grigoryan", age=34, diagnoses="Asthma"):
        return self.repo.add_patient(Patient(name=name, age=age, diagnoses=diagnoses))

    def add_visit(self, patient_id, visit_date="2026-05-12", reason="Check-up", notes=""):
        return self.repo.add_visit(
            Visit(patient_id=patient_id, visit_date=visit_date, reason=reason, notes=notes)
        )


class TestPatientCrud(RepositoryTestCase):
    def test_add_patient_assigns_id(self):
        patient = self.add_patient()
        self.assertIsNotNone(patient.id)
        self.assertEqual(self.repo.count_patients(), 1)

    def test_add_patient_rejects_already_saved(self):
        patient = self.add_patient()
        with self.assertRaises(ValidationError):
            self.repo.add_patient(patient)

    def test_add_patient_rejects_wrong_type(self):
        with self.assertRaises(ValidationError):
            self.repo.add_patient("Anna")

    def test_get_patient_round_trip(self):
        saved = self.add_patient(diagnoses="Asthma, Allergy")
        loaded = self.repo.get_patient(saved.id)
        self.assertEqual(loaded.name, saved.name)
        self.assertEqual(loaded.age, saved.age)
        self.assertEqual(loaded.diagnoses, ("Asthma", "Allergy"))

    def test_get_missing_patient_raises(self):
        with self.assertRaises(PatientNotFoundError):
            self.repo.get_patient(999)

    def test_get_patient_rejects_bad_id(self):
        with self.assertRaises(ValidationError):
            self.repo.get_patient("abc")

    def test_update_patient(self):
        patient = self.add_patient()
        patient.name = "Anna G."
        patient.age = 35
        patient.add_diagnosis("Migraine")
        self.repo.update_patient(patient)

        reloaded = self.repo.get_patient(patient.id)
        self.assertEqual(reloaded.name, "Anna G.")
        self.assertEqual(reloaded.age, 35)
        self.assertIn("Migraine", reloaded.diagnoses)

    def test_update_unsaved_patient_raises(self):
        with self.assertRaises(ValidationError):
            self.repo.update_patient(Patient(name="Ghost", age=20))

    def test_update_deleted_patient_raises(self):
        patient = self.add_patient()
        self.repo.delete_patient(patient.id)
        with self.assertRaises(PatientNotFoundError):
            self.repo.update_patient(patient)

    def test_delete_patient(self):
        patient = self.add_patient()
        self.assertTrue(self.repo.delete_patient(patient.id))
        self.assertEqual(self.repo.count_patients(), 0)

    def test_delete_missing_patient_raises(self):
        with self.assertRaises(PatientNotFoundError):
            self.repo.delete_patient(42)

    def test_patient_exists(self):
        patient = self.add_patient()
        self.assertTrue(self.repo.patient_exists(patient.id))
        self.assertFalse(self.repo.patient_exists(patient.id + 1))


class TestListingAndSearch(RepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.add_patient(name="Zara Mkrtchyan", age=20)
        self.add_patient(name="Anna Grigoryan", age=64)
        self.add_patient(name="anna petrosyan", age=8)

    def test_list_sorted_by_name_ignores_case(self):
        names = [p.name for p in self.repo.list_patients(order_by="name")]
        self.assertEqual(names, ["Anna Grigoryan", "anna petrosyan", "Zara Mkrtchyan"])

    def test_list_sorted_by_age(self):
        ages = [p.age for p in self.repo.list_patients(order_by="age")]
        self.assertEqual(ages, [8, 20, 64])

    def test_list_rejects_unknown_sort_key(self):
        with self.assertRaises(ValidationError):
            self.repo.list_patients(order_by="diagnoses; DROP TABLE patients")

    def test_search_is_case_insensitive_and_partial(self):
        results = self.repo.search_patients("ANN")
        self.assertEqual(len(results), 2)

    def test_search_without_match_returns_empty_list(self):
        self.assertEqual(self.repo.search_patients("Nobody"), [])

    def test_search_rejects_empty_term(self):
        with self.assertRaises(ValidationError):
            self.repo.search_patients("   ")

    def test_search_treats_wildcards_as_literals(self):
        # A LIKE pattern typed by the user must not match everything.
        self.assertEqual(self.repo.search_patients("%"), [])


class TestVisits(RepositoryTestCase):
    def test_add_visit_assigns_id(self):
        patient = self.add_patient()
        visit = self.add_visit(patient.id)
        self.assertIsNotNone(visit.id)
        self.assertEqual(self.repo.count_visits(), 1)

    def test_add_visit_for_unknown_patient_raises(self):
        with self.assertRaises(PatientNotFoundError):
            self.add_visit(999)

    def test_get_patient_loads_visits(self):
        patient = self.add_patient()
        self.add_visit(patient.id, visit_date="2026-01-01")
        self.add_visit(patient.id, visit_date="2026-03-01")

        loaded = self.repo.get_patient(patient.id)
        self.assertEqual(loaded.visit_count, 2)
        self.assertEqual(loaded.last_visit_date, "2026-03-01")

    def test_get_patient_can_skip_visits(self):
        patient = self.add_patient()
        self.add_visit(patient.id)
        self.assertEqual(self.repo.get_patient(patient.id, with_visits=False).visit_count, 0)

    def test_list_visits_newest_first(self):
        patient = self.add_patient()
        for day in ("2026-01-01", "2026-03-01", "2026-02-01"):
            self.add_visit(patient.id, visit_date=day)
        dates = [v.visit_date for v in self.repo.list_visits(patient.id)]
        self.assertEqual(dates, ["2026-03-01", "2026-02-01", "2026-01-01"])

    def test_update_visit(self):
        patient = self.add_patient()
        visit = self.add_visit(patient.id)
        visit.reason = "Follow-up"
        visit.notes = "Feeling better"
        self.repo.update_visit(visit)

        reloaded = self.repo.get_visit(visit.id)
        self.assertEqual(reloaded.reason, "Follow-up")
        self.assertEqual(reloaded.notes, "Feeling better")

    def test_delete_visit(self):
        patient = self.add_patient()
        visit = self.add_visit(patient.id)
        self.assertTrue(self.repo.delete_visit(visit.id))
        self.assertEqual(self.repo.count_visits(), 0)

    def test_get_missing_visit_raises(self):
        with self.assertRaises(VisitNotFoundError):
            self.repo.get_visit(123)

    def test_delete_missing_visit_raises(self):
        with self.assertRaises(VisitNotFoundError):
            self.repo.delete_visit(123)

    def test_deleting_patient_cascades_to_visits(self):
        patient = self.add_patient()
        self.add_visit(patient.id)
        self.add_visit(patient.id, visit_date="2026-06-01")

        self.repo.delete_patient(patient.id)
        self.assertEqual(self.repo.count_visits(), 0)

    def test_visits_of_other_patients_survive(self):
        keep = self.add_patient(name="Keep Me")
        remove = self.add_patient(name="Remove Me")
        self.add_visit(keep.id)
        self.add_visit(remove.id)

        self.repo.delete_patient(remove.id)
        self.assertEqual(self.repo.count_visits(), 1)
        self.assertEqual(len(self.repo.list_visits(keep.id)), 1)


class TestStats(RepositoryTestCase):
    def test_stats_on_empty_vault(self):
        stats = self.repo.stats()
        self.assertEqual(stats["total_patients"], 0)
        self.assertEqual(stats["total_visits"], 0)
        self.assertIsNone(stats["average_age"])
        self.assertIsNone(stats["busiest_patient"])
        self.assertEqual(stats["average_visits_per_patient"], 0)
        self.assertEqual(stats["top_diagnoses"], [])

    def test_stats_with_data(self):
        anna = self.add_patient(name="Anna", age=30, diagnoses="Asthma")
        david = self.add_patient(name="David", age=40, diagnoses="asthma, Diabetes")
        self.add_patient(name="Lonely", age=50, diagnoses="")

        self.add_visit(anna.id)
        self.add_visit(david.id)
        self.add_visit(david.id, visit_date="2026-06-01")

        stats = self.repo.stats()
        self.assertEqual(stats["total_patients"], 3)
        self.assertEqual(stats["total_visits"], 3)
        self.assertEqual(stats["average_age"], 40.0)
        self.assertEqual(stats["youngest_age"], 30)
        self.assertEqual(stats["oldest_age"], 50)
        self.assertEqual(stats["average_visits_per_patient"], 1.0)
        self.assertEqual(stats["patients_without_visits"], 1)
        self.assertEqual(stats["busiest_patient"]["name"], "David")
        self.assertEqual(stats["busiest_patient"]["visits"], 2)
        self.assertEqual(stats["top_diagnoses"][0], {"diagnosis": "asthma", "count": 2})


class TestConnectionHandling(unittest.TestCase):
    def test_data_survives_reconnect(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = Path(folder) / "nested" / "patients.db"

            with PatientRepository(db_path) as repo:
                patient = repo.add_patient(Patient(name="Anna", age=34))
                repo.add_visit(
                    Visit(patient_id=patient.id, visit_date="2026-05-12", reason="Check-up")
                )

            self.assertTrue(db_path.exists())

            with PatientRepository(db_path) as repo:
                reloaded = repo.get_patient(1)
                self.assertEqual(reloaded.name, "Anna")
                self.assertEqual(reloaded.visit_count, 1)

    def test_using_a_closed_repository_raises(self):
        repo = PatientRepository(":memory:")
        repo.close()
        with self.assertRaises(RepositoryError):
            repo.count_patients()

    def test_connect_is_idempotent(self):
        repo = PatientRepository(":memory:")
        self.addCleanup(repo.close)
        self.assertIs(repo.connect(), repo.connect())


if __name__ == "__main__":
    unittest.main()
