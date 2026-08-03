"""Optional demo data, so a fresh clone has something to look at."""

from .models import Patient, Visit

DEMO_PATIENTS = [
    {
        "name": "Anna Grigoryan",
        "age": 34,
        "diagnoses": "Asthma, Seasonal allergy",
        "visits": [
            ("2025-11-04", "Routine check-up", "Peak flow normal."),
            ("2026-02-17", "Shortness of breath", "Inhaler dose reviewed."),
        ],
    },
    {
        "name": "David Petrosyan",
        "age": 67,
        "diagnoses": "Hypertension, Type 2 diabetes",
        "visits": [
            ("2026-01-09", "Blood pressure follow-up", "150/95, medication adjusted."),
            ("2026-04-21", "Lab results review", "HbA1c improved."),
            ("2026-06-30", "Foot examination", ""),
        ],
    },
    {
        "name": "Mariam Sargsyan",
        "age": 8,
        "diagnoses": "Otitis media",
        "visits": [("2026-05-12", "Ear pain", "Antibiotics prescribed for 7 days.")],
    },
    {
        "name": "Karen Hovhannisyan",
        "age": 45,
        "diagnoses": "",
        "visits": [],
    },
]


def seed_demo_data(repository, force=False):
    """Insert the demo records. Returns how many patients were added.

    Does nothing when the vault already holds data, unless `force` is True.
    """
    if repository.count_patients() and not force:
        return 0

    added = 0
    for entry in DEMO_PATIENTS:
        patient = Patient(name=entry["name"], age=entry["age"], diagnoses=entry["diagnoses"])
        repository.add_patient(patient)
        added += 1
        for visit_date, reason, notes in entry["visits"]:
            repository.add_visit(
                Visit(
                    patient_id=patient.id,
                    visit_date=visit_date,
                    reason=reason,
                    notes=notes,
                )
            )
    return added
