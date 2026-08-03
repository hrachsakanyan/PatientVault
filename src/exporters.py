"""Export the vault to CSV or JSON.

Exporters read through the repository, so they only ever see domain objects.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from .errors import RepositoryError

PATIENT_COLUMNS = ["id", "name", "age", "diagnoses", "visit_count", "last_visit", "created_at"]
VISIT_COLUMNS = ["id", "patient_id", "patient_name", "visit_date", "reason", "notes", "created_at"]


def _prepare(path):
    """Make sure the parent folder of `path` exists; return it as a Path."""
    target = Path(path).expanduser()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RepositoryError(f"Cannot create export folder {target.parent}: {exc}") from exc
    return target


def _write_csv(path, columns, rows):
    target = _prepare(path)
    try:
        with open(target, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    except OSError as exc:
        raise RepositoryError(f"Cannot write {target}: {exc}") from exc
    return target


def export_patients_csv(repository, path):
    """Write one row per patient, with their visit count."""
    rows = []
    for patient in repository.list_patients(order_by="id", with_visits=True):
        rows.append(
            {
                "id": patient.id,
                "name": patient.name,
                "age": patient.age,
                "diagnoses": "; ".join(patient.diagnoses),
                "visit_count": patient.visit_count,
                "last_visit": patient.last_visit_date or "",
                "created_at": patient.created_at,
            }
        )
    return _write_csv(path, PATIENT_COLUMNS, rows)


def export_visits_csv(repository, path):
    """Write one row per visit, joined with the patient's name."""
    names = {p.id: p.name for p in repository.list_patients(order_by="id")}
    rows = [
        {
            "id": visit.id,
            "patient_id": visit.patient_id,
            "patient_name": names.get(visit.patient_id, ""),
            "visit_date": visit.visit_date,
            "reason": visit.reason,
            "notes": visit.notes,
            "created_at": visit.created_at,
        }
        for visit in repository.list_all_visits()
    ]
    return _write_csv(path, VISIT_COLUMNS, rows)


def export_json(repository, path):
    """Write the whole vault — patients with nested visits — as one JSON file."""
    target = _prepare(path)
    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "stats": repository.stats(),
        "patients": [
            patient.to_dict()
            for patient in repository.list_patients(order_by="id", with_visits=True)
        ],
    }
    try:
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    except OSError as exc:
        raise RepositoryError(f"Cannot write {target}: {exc}") from exc
    return target
