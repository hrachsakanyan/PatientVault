# PatientVault — Patient Records Manager

A patient records manager built with **object-oriented Python** on top of **SQLite**.
It models a small clinical domain (patients, diagnoses, visits), stores it in a real
relational database, and exposes everything through a menu-driven CLI.

No third-party dependencies — only the Python standard library.

> **Disclaimer:** this is an educational project. It has no authentication,
> no encryption and no audit log. **Do not store real patient data in it.**
> All names in the demo data are fictional.

---

## Architecture

The project is a small three-layer application. Each layer only talks to the one below it:

```
        cli.py            collects input, prints tables — no domain rules
          ↓
      models.py           Patient, Visit — the domain and its rules
          ↓
   repository.py          the only module that knows SQL exists
          ↓
        SQLite
```

`validation.py` sits beside the models and is called from their property setters, so an
invalid `Patient` or `Visit` object cannot be created in the first place — bad data is
rejected long before it reaches the database.

### Classes

| Class | Responsibility |
| --- | --- |
| `Patient` | Name, age, diagnoses and the visits that belong to them. Validates on every assignment via properties. |
| `Visit` | One appointment: date, reason, notes. Always belongs to exactly one patient. |
| `PatientRepository` | All CRUD, search and statistics. Takes and returns objects, never rows. Usable as a context manager. |

**Encapsulation** — state lives in private attributes (`_name`, `_age`, `_visits`) behind
properties, so `patient.age = 200` raises `ValidationError` instead of corrupting the record.
`patient.diagnoses` and `patient.visits` return tuples, so callers cannot mutate internals
by accident.

**Composition** — a `Patient` *has* `Visit` objects. Visits have no independent life:
deleting a patient deletes their visits, enforced by the database itself with
`ON DELETE CASCADE`.

### Database schema

```sql
CREATE TABLE patients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    age        INTEGER NOT NULL CHECK (age >= 0 AND age <= 130),
    diagnoses  TEXT    NOT NULL DEFAULT '[]',   -- JSON list
    created_at TEXT    NOT NULL
);

CREATE TABLE visits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_date TEXT    NOT NULL,                -- ISO 8601, YYYY-MM-DD
    reason     TEXT    NOT NULL,
    notes      TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE INDEX idx_patients_name    ON patients(name);
CREATE INDEX idx_visits_patient_id ON visits(patient_id);
```

Two design notes:

- **Diagnoses are stored as a JSON list in a `TEXT` column.** A separate `diagnoses` table
  would be the fully normalised choice; a JSON column keeps the project readable and is
  enough for the queries here. The trade-off is that diagnosis counting happens in Python
  (`_top_diagnoses`) instead of in SQL.
- **`PRAGMA foreign_keys = ON` is set on every connection.** SQLite does *not* enforce
  foreign keys by default, so without it the cascade delete would silently do nothing.

### Error handling

Every deliberate error inherits from `PatientVaultError`:

```
PatientVaultError
├── ValidationError        bad input
├── NotFoundError
│   ├── PatientNotFoundError
│   └── VisitNotFoundError
└── RepositoryError        SQL / file system failure
```

`sqlite3.Error` never escapes the repository — it is translated into `RepositoryError`.
The CLI catches `PatientVaultError` in one place, prints a readable message and returns to
the menu, so a typo never produces a traceback.

---

## Features

**Core**

- Add, find, update and delete patients (full CRUD)
- Add and delete visits per patient
- List all patients, sorted by name, age or id
- Case-insensitive partial search by name
- SQLite persistence with cascade deletes
- Menu-driven CLI with per-field re-prompting on invalid input

**Extras**

- Validation layer shared by the models and the CLI
- Export to CSV (patients, visits) and JSON (whole vault + stats)
- Statistics: average age, age range, visits per patient, busiest patient, top diagnoses
- 78 unit tests (`unittest`, no external runner needed)
- Config-driven database path: `--db` flag, environment variable, or default
- `--seed` flag with demo data for a first look

---

## Setup

Requires **Python 3.8+**. Nothing else to install.

```bash
git clone https://github.com/<your-username>/patientvault.git
cd patientvault
```

Optionally create a virtual environment:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

---

## Usage

Run from the project root:

```bash
python -m src.main
```

On Windows, if `python` is not on your PATH, use the launcher: `py -m src.main`.

Useful flags:

```bash
python -m src.main --seed              # start with demo patients (only if the vault is empty)
python -m src.main --db data/demo.db   # use a different database file
python -m src.main --db :memory:       # throwaway database, nothing is saved
python -m src.main --version
python -m src.main --help
```

### Where the database lives

The path is resolved in this order — first match wins:

1. `--db PATH` on the command line
2. the `PATIENTVAULT_DB` environment variable
3. `data/patients.db` (default; the folder is created automatically)

```bash
# Windows PowerShell
$env:PATIENTVAULT_DB = "C:\vaults\clinic.db"

# macOS / Linux
export PATIENTVAULT_DB=~/vaults/clinic.db
```

### Example session

```
==============================================================
  PatientVault 1.0.0 — patient records manager
  Database: data/patients.db
  Source:   default location
  Educational project — do not store real patient data.
==============================================================

--------------------------------------------------------------
   1) Add patient
   2) List all patients
   3) Find patient by id
   4) Search patients by name
   5) Update patient
   6) Delete patient
   7) Add visit to a patient
   8) List visits of a patient
   9) Delete visit
  10) Statistics
  11) Export data (CSV / JSON)
   0) Exit
--------------------------------------------------------------
Choose an option: 1

  New patient
  Name: Anna Grigoryan
  Age: abc
  Age must be a whole number, got 'abc'.
  Age: 34
  Diagnoses (comma separated, optional): Asthma, Seasonal allergy

  Saved: #1 Anna Grigoryan, age 34 · diagnoses: Asthma, Seasonal allergy · visits: 0
```

Listing patients:

```
    ID  NAME                      AGE  VISITS  DIAGNOSES
  --------------------------------------------------------------
     3  Mariam Sargsyan             8       1  Otitis media
     1  Anna Grigoryan             34       2  Asthma, Seasonal allergy
     4  Karen Hovhannisyan         45       0  -
     2  David Petrosyan            67       3  Hypertension, Type 2 diabetes

  4 patient(s).
```

Statistics:

```
  Statistics
  --------------------------------------------------------------
  Patients:               4
  Visits:                 6
  Average age:            38.5
  Age range:              8 – 67
  Avg visits / patient:   1.5
  Patients with 0 visits: 1
  Most visits:            David Petrosyan (#2) — 3
  Top diagnoses:
    - asthma: 1
    - hypertension: 1
    - otitis media: 1
    - seasonal allergy: 1
    - type 2 diabetes: 1
```

### Using the repository from your own code

The repository works standalone — the CLI is just one possible front end:

```python
from src.models import Patient, Visit
from src.repository import PatientRepository

with PatientRepository("data/patients.db") as repo:
    anna = repo.add_patient(Patient(name="Anna Grigoryan", age=34, diagnoses="Asthma"))
    repo.add_visit(Visit(patient_id=anna.id, visit_date="2026-05-12", reason="Check-up"))

    loaded = repo.get_patient(anna.id)
    print(loaded.visit_count, loaded.last_visit_date)   # 1 2026-05-12
```

---

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

78 tests covering the validation rules, both models, every repository method, the
cascade delete, the exporters and the seed data. They run against `:memory:` databases and
temporary folders, so they never touch your real vault.

---

## Project structure

```
patientvault/
├── src/
│   ├── __init__.py
│   ├── main.py           entry point, argument parsing
│   ├── cli.py            menu loop, prompts, tables
│   ├── models.py         Patient, Visit
│   ├── repository.py     SQLite layer (the only module with SQL)
│   ├── validation.py     input rules shared by models and CLI
│   ├── exporters.py      CSV / JSON export
│   ├── config.py         database path resolution
│   └── seed.py           optional demo data
├── tests/
│   ├── __init__.py
│   ├── test_validation.py
│   ├── test_models.py
│   ├── test_repository.py
│   └── test_exporters.py
├── data/                 patients.db lives here (git-ignored)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## What I practised

- Modelling a domain with classes, properties and composition
- Keeping validation in one place and enforcing it at the boundary of the objects
- The repository pattern: separating domain objects from storage
- SQL CRUD, foreign keys, cascade deletes, indexes and parameterised queries
- Turning library exceptions into a meaningful, catchable error hierarchy
- Writing unit tests against an in-memory database
