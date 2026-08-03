import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.exporters import export_json, export_patients_csv, export_visits_csv
from src.models import Patient, Visit
from src.repository import PatientRepository
from src.seed import seed_demo_data


class TestExporters(unittest.TestCase):
    def setUp(self):
        self.repo = PatientRepository(":memory:")
        self.addCleanup(self.repo.close)

        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.out = Path(self.folder.name)

        anna = self.repo.add_patient(Patient(name="Anna", age=34, diagnoses="Asthma, Allergy"))
        self.repo.add_patient(Patient(name="Lonely", age=50))
        self.repo.add_visit(
            Visit(patient_id=anna.id, visit_date="2026-05-12", reason="Check-up", notes="Fine")
        )

    def test_export_patients_csv(self):
        path = export_patients_csv(self.repo, self.out / "patients.csv")
        with open(path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Anna")
        self.assertEqual(rows[0]["diagnoses"], "Asthma; Allergy")
        self.assertEqual(rows[0]["visit_count"], "1")
        self.assertEqual(rows[0]["last_visit"], "2026-05-12")
        self.assertEqual(rows[1]["last_visit"], "")

    def test_export_visits_csv_includes_patient_name(self):
        path = export_visits_csv(self.repo, self.out / "visits.csv")
        with open(path, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["patient_name"], "Anna")
        self.assertEqual(rows[0]["reason"], "Check-up")

    def test_export_json_structure(self):
        path = export_json(self.repo, self.out / "nested" / "vault.json")
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("exported_at", payload)
        self.assertEqual(payload["stats"]["total_patients"], 2)
        self.assertEqual(len(payload["patients"]), 2)
        self.assertEqual(payload["patients"][0]["diagnoses"], ["Asthma", "Allergy"])
        self.assertEqual(len(payload["patients"][0]["visits"]), 1)

    def test_export_creates_missing_folders(self):
        path = export_patients_csv(self.repo, self.out / "a" / "b" / "patients.csv")
        self.assertTrue(path.exists())


class TestSeed(unittest.TestCase):
    def setUp(self):
        self.repo = PatientRepository(":memory:")
        self.addCleanup(self.repo.close)

    def test_seed_fills_an_empty_vault(self):
        added = seed_demo_data(self.repo)
        self.assertEqual(added, 4)
        self.assertEqual(self.repo.count_patients(), 4)
        self.assertEqual(self.repo.count_visits(), 6)

    def test_seed_skips_a_non_empty_vault(self):
        seed_demo_data(self.repo)
        self.assertEqual(seed_demo_data(self.repo), 0)
        self.assertEqual(self.repo.count_patients(), 4)


if __name__ == "__main__":
    unittest.main()
