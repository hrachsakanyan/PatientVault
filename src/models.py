"""Domain models: Visit and Patient.

Both classes keep their state in private attributes and expose it through
properties, so validation runs on every assignment — not just in __init__.
A Patient *composes* Visit objects: visits belong to a patient and are deleted
together with them.
"""

import json
from datetime import datetime

from .errors import ValidationError
from .validation import (
    validate_age,
    validate_date,
    validate_diagnoses,
    validate_id,
    validate_name,
    validate_text,
)


def _now():
    """Current local timestamp as a stable, sortable string."""
    return datetime.now().isoformat(timespec="seconds")


class Visit:
    """A single appointment belonging to one patient."""

    def __init__(self, patient_id, visit_date, reason, notes="", visit_id=None, created_at=None):
        self._id = None if visit_id is None else validate_id(visit_id, "Visit id")
        self.patient_id = patient_id
        self.visit_date = visit_date
        self.reason = reason
        self.notes = notes
        self._created_at = created_at or _now()

    # --- properties -----------------------------------------------------

    @property
    def id(self):
        """Database id, or None while the visit has not been saved yet."""
        return self._id

    @property
    def created_at(self):
        return self._created_at

    @property
    def patient_id(self):
        return self._patient_id

    @patient_id.setter
    def patient_id(self, value):
        self._patient_id = validate_id(value, "Patient id")

    @property
    def visit_date(self):
        return self._visit_date

    @visit_date.setter
    def visit_date(self, value):
        self._visit_date = validate_date(value)

    @property
    def reason(self):
        return self._reason

    @reason.setter
    def reason(self, value):
        self._reason = validate_text(value, "Reason", max_length=200)

    @property
    def notes(self):
        return self._notes

    @notes.setter
    def notes(self, value):
        self._notes = validate_text(value, "Notes", max_length=1000, required=False)

    # --- persistence helpers --------------------------------------------

    def to_dict(self):
        return {
            "id": self._id,
            "patient_id": self._patient_id,
            "visit_date": self._visit_date,
            "reason": self._reason,
            "notes": self._notes,
            "created_at": self._created_at,
        }

    @classmethod
    def from_row(cls, row):
        """Build a Visit from a sqlite3.Row (or any mapping with the columns)."""
        return cls(
            visit_id=row["id"],
            patient_id=row["patient_id"],
            visit_date=row["visit_date"],
            reason=row["reason"],
            notes=row["notes"],
            created_at=row["created_at"],
        )

    def _assign_id(self, new_id):
        """Called by the repository once SQLite has issued a primary key."""
        self._id = validate_id(new_id, "Visit id")

    # --- dunders ---------------------------------------------------------

    def __str__(self):
        label = f"#{self._id}" if self._id else "#new"
        notes = f" — {self._notes}" if self._notes else ""
        return f"{label} {self._visit_date} · {self._reason}{notes}"

    def __repr__(self):
        return (
            f"Visit(visit_id={self._id!r}, patient_id={self._patient_id!r}, "
            f"visit_date={self._visit_date!r}, reason={self._reason!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, Visit):
            return NotImplemented
        return self.to_dict() == other.to_dict()


class Patient:
    """A patient record together with the visits that belong to it."""

    def __init__(self, name, age, diagnoses=None, patient_id=None, created_at=None, visits=None):
        self._id = None if patient_id is None else validate_id(patient_id, "Patient id")
        self.name = name
        self.age = age
        self.diagnoses = diagnoses
        self._created_at = created_at or _now()
        self._visits = []
        for visit in visits or []:
            self.add_visit(visit)

    # --- properties -----------------------------------------------------

    @property
    def id(self):
        """Database id, or None while the patient has not been saved yet."""
        return self._id

    @property
    def created_at(self):
        return self._created_at

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = validate_name(value)

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        self._age = validate_age(value)

    @property
    def diagnoses(self):
        """Diagnoses as a tuple, so callers cannot mutate internal state."""
        return tuple(self._diagnoses)

    @diagnoses.setter
    def diagnoses(self, value):
        self._diagnoses = validate_diagnoses(value)

    @property
    def visits(self):
        """Visits as a tuple, newest first."""
        return tuple(sorted(self._visits, key=lambda v: (v.visit_date, v.id or 0), reverse=True))

    @property
    def visit_count(self):
        return len(self._visits)

    @property
    def last_visit_date(self):
        """ISO date of the most recent visit, or None if there are no visits."""
        if not self._visits:
            return None
        return max(visit.visit_date for visit in self._visits)

    # --- behaviour -------------------------------------------------------

    def add_diagnosis(self, diagnosis):
        """Add one diagnosis, ignoring duplicates (case-insensitive)."""
        self.diagnoses = list(self._diagnoses) + [diagnosis]

    def remove_diagnosis(self, diagnosis):
        """Remove a diagnosis by name. Returns True if something was removed."""
        target = " ".join(str(diagnosis).split()).lower()
        remaining = [d for d in self._diagnoses if d.lower() != target]
        removed = len(remaining) != len(self._diagnoses)
        self._diagnoses = remaining
        return removed

    def add_visit(self, visit):
        """Attach a Visit to this patient (composition)."""
        if not isinstance(visit, Visit):
            raise ValidationError("Only Visit objects can be added to a patient.")
        if self._id is not None and visit.patient_id != self._id:
            raise ValidationError(
                f"Visit belongs to patient {visit.patient_id}, not to patient {self._id}."
            )
        self._visits.append(visit)
        return visit

    def clear_visits(self):
        """Drop the in-memory visit list (used when reloading from storage)."""
        self._visits = []

    # --- persistence helpers --------------------------------------------

    def to_dict(self, include_visits=True):
        data = {
            "id": self._id,
            "name": self._name,
            "age": self._age,
            "diagnoses": list(self._diagnoses),
            "created_at": self._created_at,
        }
        if include_visits:
            data["visits"] = [visit.to_dict() for visit in self.visits]
        return data

    @classmethod
    def from_row(cls, row, visits=None):
        """Build a Patient from a sqlite3.Row; diagnoses are stored as JSON."""
        try:
            diagnoses = json.loads(row["diagnoses"] or "[]")
        except (TypeError, ValueError):
            diagnoses = []
        return cls(
            patient_id=row["id"],
            name=row["name"],
            age=row["age"],
            diagnoses=diagnoses,
            created_at=row["created_at"],
            visits=visits,
        )

    def diagnoses_json(self):
        """Diagnoses serialised for the TEXT column in SQLite."""
        return json.dumps(list(self._diagnoses), ensure_ascii=False)

    def diagnoses_text(self):
        """Human-readable diagnoses for the CLI."""
        return ", ".join(self._diagnoses) if self._diagnoses else "-"

    def _assign_id(self, new_id):
        """Called by the repository once SQLite has issued a primary key."""
        self._id = validate_id(new_id, "Patient id")

    # --- dunders ---------------------------------------------------------

    def __str__(self):
        label = f"#{self._id}" if self._id else "#new"
        return (
            f"{label} {self._name}, age {self._age} · "
            f"diagnoses: {self.diagnoses_text()} · visits: {self.visit_count}"
        )

    def __repr__(self):
        return (
            f"Patient(patient_id={self._id!r}, name={self._name!r}, "
            f"age={self._age!r}, diagnoses={list(self._diagnoses)!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, Patient):
            return NotImplemented
        return self.to_dict() == other.to_dict()
