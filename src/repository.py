"""SQLite storage layer.

The repository is the only place in the project that knows SQL exists. It
takes and returns domain objects (Patient, Visit); everything above it — the
CLI, the exporters, the tests — works with objects, never with rows.

Schema
------
patients(id, name, age, diagnoses JSON TEXT, created_at)
visits(id, patient_id -> patients.id ON DELETE CASCADE, visit_date, reason,
       notes, created_at)
"""

import json
import sqlite3
from pathlib import Path

from .config import IN_MEMORY, resolve_db_path
from .errors import PatientNotFoundError, RepositoryError, ValidationError, VisitNotFoundError
from .models import Patient, Visit
from .validation import validate_id, validate_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    age        INTEGER NOT NULL CHECK (age >= 0 AND age <= 130),
    diagnoses  TEXT    NOT NULL DEFAULT '[]',
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS visits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_date TEXT    NOT NULL,
    reason     TEXT    NOT NULL,
    notes      TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name);
CREATE INDEX IF NOT EXISTS idx_visits_patient_id ON visits(patient_id);
"""


def _escape_like(term):
    """Escape LIKE wildcards so a search for '%' looks for a literal '%'."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PatientRepository:
    """CRUD access to patients and their visits, backed by SQLite."""

    def __init__(self, db_path=None, auto_connect=True):
        self.db_path = resolve_db_path(db_path)
        self._connection = None
        if auto_connect:
            self.connect()

    # --- connection management ------------------------------------------

    def connect(self):
        """Open the database, creating the file and schema when missing."""
        if self._connection is not None:
            return self._connection

        if self.db_path != IN_MEMORY:
            parent = Path(self.db_path).parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise RepositoryError(f"Cannot create database folder {parent}: {exc}") from exc

        try:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.executescript(SCHEMA)
            self._connection.commit()
        except sqlite3.Error as exc:
            raise RepositoryError(f"Cannot open database {self.db_path}: {exc}") from exc
        return self._connection

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            raise RepositoryError("Repository is not connected. Call connect() first.")
        return self._connection

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def _execute(self, sql, params=()):
        """Run a statement, translating sqlite3 failures into our own error."""
        try:
            return self.connection.execute(sql, params)
        except sqlite3.Error as exc:
            raise RepositoryError(f"Database error: {exc}") from exc

    # --- patients: create ------------------------------------------------

    def add_patient(self, patient):
        """Insert a patient and return the same object with its new id."""
        if not isinstance(patient, Patient):
            raise ValidationError("add_patient expects a Patient object.")
        if patient.id is not None:
            raise ValidationError(
                f"Patient {patient.id} is already stored; use update_patient instead."
            )

        cursor = self._execute(
            "INSERT INTO patients (name, age, diagnoses, created_at) VALUES (?, ?, ?, ?)",
            (patient.name, patient.age, patient.diagnoses_json(), patient.created_at),
        )
        self.connection.commit()
        patient._assign_id(cursor.lastrowid)
        return patient

    # --- patients: read --------------------------------------------------

    def get_patient(self, patient_id, with_visits=True):
        """Return one Patient or raise PatientNotFoundError."""
        patient_id = validate_id(patient_id, "Patient id")
        row = self._execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if row is None:
            raise PatientNotFoundError(patient_id)

        visits = self.list_visits(patient_id) if with_visits else None
        return Patient.from_row(row, visits=visits)

    def list_patients(self, order_by="name", with_visits=False):
        """Return every patient, sorted by 'name', 'age' or 'id'."""
        columns = {"name": "name COLLATE NOCASE", "age": "age", "id": "id"}
        if order_by not in columns:
            raise ValidationError(
                f"Cannot sort by {order_by!r}; choose one of {', '.join(sorted(columns))}."
            )

        rows = self._execute(f"SELECT * FROM patients ORDER BY {columns[order_by]}").fetchall()
        return [self._build_patient(row, with_visits) for row in rows]

    def search_patients(self, term, with_visits=False):
        """Return patients whose name contains `term` (case-insensitive)."""
        term = validate_text(term, "Search term", max_length=100)
        pattern = f"%{_escape_like(term)}%"
        rows = self._execute(
            "SELECT * FROM patients WHERE name LIKE ? ESCAPE '\\' ORDER BY name COLLATE NOCASE",
            (pattern,),
        ).fetchall()
        return [self._build_patient(row, with_visits) for row in rows]

    def count_patients(self):
        return self._execute("SELECT COUNT(*) AS total FROM patients").fetchone()["total"]

    def patient_exists(self, patient_id):
        patient_id = validate_id(patient_id, "Patient id")
        row = self._execute("SELECT 1 FROM patients WHERE id = ?", (patient_id,)).fetchone()
        return row is not None

    def _build_patient(self, row, with_visits):
        visits = self.list_visits(row["id"]) if with_visits else None
        return Patient.from_row(row, visits=visits)

    # --- patients: update / delete ---------------------------------------

    def update_patient(self, patient):
        """Write a modified Patient back to storage."""
        if not isinstance(patient, Patient):
            raise ValidationError("update_patient expects a Patient object.")
        if patient.id is None:
            raise ValidationError("Cannot update a patient that has not been saved yet.")

        cursor = self._execute(
            "UPDATE patients SET name = ?, age = ?, diagnoses = ? WHERE id = ?",
            (patient.name, patient.age, patient.diagnoses_json(), patient.id),
        )
        if cursor.rowcount == 0:
            raise PatientNotFoundError(patient.id)
        self.connection.commit()
        return patient

    def delete_patient(self, patient_id):
        """Delete a patient; ON DELETE CASCADE removes their visits too."""
        patient_id = validate_id(patient_id, "Patient id")
        cursor = self._execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        if cursor.rowcount == 0:
            raise PatientNotFoundError(patient_id)
        self.connection.commit()
        return True

    # --- visits ----------------------------------------------------------

    def add_visit(self, visit):
        """Insert a visit and return it with its new id."""
        if not isinstance(visit, Visit):
            raise ValidationError("add_visit expects a Visit object.")
        if visit.id is not None:
            raise ValidationError(f"Visit {visit.id} is already stored.")
        if not self.patient_exists(visit.patient_id):
            raise PatientNotFoundError(visit.patient_id)

        cursor = self._execute(
            "INSERT INTO visits (patient_id, visit_date, reason, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (visit.patient_id, visit.visit_date, visit.reason, visit.notes, visit.created_at),
        )
        self.connection.commit()
        visit._assign_id(cursor.lastrowid)
        return visit

    def get_visit(self, visit_id):
        visit_id = validate_id(visit_id, "Visit id")
        row = self._execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
        if row is None:
            raise VisitNotFoundError(visit_id)
        return Visit.from_row(row)

    def list_visits(self, patient_id):
        """Return one patient's visits, newest first."""
        patient_id = validate_id(patient_id, "Patient id")
        rows = self._execute(
            "SELECT * FROM visits WHERE patient_id = ? ORDER BY visit_date DESC, id DESC",
            (patient_id,),
        ).fetchall()
        return [Visit.from_row(row) for row in rows]

    def list_all_visits(self):
        rows = self._execute(
            "SELECT * FROM visits ORDER BY visit_date DESC, id DESC"
        ).fetchall()
        return [Visit.from_row(row) for row in rows]

    def update_visit(self, visit):
        if not isinstance(visit, Visit):
            raise ValidationError("update_visit expects a Visit object.")
        if visit.id is None:
            raise ValidationError("Cannot update a visit that has not been saved yet.")

        cursor = self._execute(
            "UPDATE visits SET visit_date = ?, reason = ?, notes = ? WHERE id = ?",
            (visit.visit_date, visit.reason, visit.notes, visit.id),
        )
        if cursor.rowcount == 0:
            raise VisitNotFoundError(visit.id)
        self.connection.commit()
        return visit

    def delete_visit(self, visit_id):
        visit_id = validate_id(visit_id, "Visit id")
        cursor = self._execute("DELETE FROM visits WHERE id = ?", (visit_id,))
        if cursor.rowcount == 0:
            raise VisitNotFoundError(visit_id)
        self.connection.commit()
        return True

    def count_visits(self):
        return self._execute("SELECT COUNT(*) AS total FROM visits").fetchone()["total"]

    # --- statistics -------------------------------------------------------

    def stats(self):
        """Aggregate numbers for the statistics screen."""
        row = self._execute(
            "SELECT COUNT(*) AS patients, AVG(age) AS avg_age, "
            "MIN(age) AS min_age, MAX(age) AS max_age FROM patients"
        ).fetchone()

        total_patients = row["patients"]
        total_visits = self.count_visits()
        busiest = self._execute(
            "SELECT p.id, p.name, COUNT(v.id) AS visit_count "
            "FROM patients p JOIN visits v ON v.patient_id = p.id "
            "GROUP BY p.id, p.name ORDER BY visit_count DESC, p.name LIMIT 1"
        ).fetchone()

        top_diagnoses = self._top_diagnoses()

        return {
            "total_patients": total_patients,
            "total_visits": total_visits,
            "average_age": round(row["avg_age"], 1) if row["avg_age"] is not None else None,
            "youngest_age": row["min_age"],
            "oldest_age": row["max_age"],
            "average_visits_per_patient": (
                round(total_visits / total_patients, 2) if total_patients else 0
            ),
            "patients_without_visits": self._count_patients_without_visits(),
            "busiest_patient": (
                {"id": busiest["id"], "name": busiest["name"], "visits": busiest["visit_count"]}
                if busiest
                else None
            ),
            "top_diagnoses": top_diagnoses,
        }

    def _count_patients_without_visits(self):
        return self._execute(
            "SELECT COUNT(*) AS total FROM patients p "
            "WHERE NOT EXISTS (SELECT 1 FROM visits v WHERE v.patient_id = p.id)"
        ).fetchone()["total"]

    def _top_diagnoses(self, limit=5):
        """Count diagnoses in Python, since they live in a JSON column."""
        counts = {}
        for row in self._execute("SELECT diagnoses FROM patients").fetchall():
            try:
                diagnoses = json.loads(row["diagnoses"] or "[]")
            except ValueError:
                continue
            for diagnosis in diagnoses:
                key = str(diagnosis).lower()
                counts[key] = counts.get(key, 0) + 1

        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [{"diagnosis": name, "count": count} for name, count in ordered[:limit]]
