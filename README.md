# 🏥 PatientVault 

### Patient Records Manager built with Python + SQLite

A clean, object-oriented patient records management system built with **Python** and **SQLite**.

PatientVault models a small clinical domain — **patients, diagnoses, and visits** — stores everything in a real relational database, and provides a simple **menu-driven CLI** for managing records.

> ⚠️ **Educational project only.**
> PatientVault has no authentication, encryption, or audit logging.
> **Do not store real patient data in this application.**
> All demo names and data are fictional.

---

<p align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python\&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite\&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-78%20passing-success)
![Dependencies](https://img.shields.io/badge/Dependencies-None-brightgreen)
![License](https://img.shields.io/badge/License-Educational-lightgrey)

</p>

---

## ✨ Features

### 👤 Patient Management

* Add patients
* Find patients by ID
* Update patient information
* Delete patients
* List all patients
* Sort by name, age, or ID
* Case-insensitive partial name search

### 🩺 Clinical Records

* Add visits to patients
* List patient visits
* Delete visits
* Store diagnoses
* Automatic visit count tracking
* Last visit information

### 🗄️ Database

* SQLite persistence
* Foreign key relationships
* `ON DELETE CASCADE`
* Parameterized SQL queries
* Database indexes
* Automatic database directory creation

### 📊 Statistics

* Average patient age
* Minimum and maximum age
* Total number of patients
* Total number of visits
* Average visits per patient
* Patients with zero visits
* Busiest patient
* Most common diagnoses

### 📤 Data Export

* Export patients to CSV
* Export visits to CSV
* Export complete vault to JSON
* Export statistics to JSON

### 🧪 Testing

* **78 unit tests**
* Python built-in `unittest`
* In-memory SQLite databases
* Temporary folders for file-based tests
* No external test runner required

---

# 🏗️ Architecture

PatientVault follows a simple **three-layer architecture**.

Each layer communicates only with the layer directly below it.

```text
                    ┌─────────────────────┐
                    │       cli.py        │
                    │  User interaction   │
                    │  Menu & input       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      models.py      │
                    │  Patient & Visit    │
                    │  Domain rules       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   repository.py    │
                    │   CRUD & SQL        │
                    │   SQLite access     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       SQLite        │
                    │      Database       │
                    └─────────────────────┘
```

### Validation Layer

`validation.py` sits beside the domain models.

It is called from model property setters, meaning invalid objects are rejected **before they ever reach the database**.

```text
User Input
    │
    ▼
   CLI
    │
    ▼
Validation
    │
    ├──── Invalid ────► ValidationError
    │
    ▼
 Patient / Visit
    │
    ▼
Repository
    │
    ▼
 SQLite
```

---

# 🧩 Core Classes

| Class               | Responsibility                                             |
| ------------------- | ---------------------------------------------------------- |
| `Patient`           | Represents a patient with name, age, diagnoses, and visits |
| `Visit`             | Represents an appointment belonging to exactly one patient |
| `PatientRepository` | Handles CRUD, search, statistics, and database access      |

---

## 🔒 Encapsulation

Domain state is stored in private attributes and exposed through properties.

```python
patient.age = 200
```

Instead of allowing invalid data, the model raises:

```text
ValidationError
```

This prevents invalid domain objects from being created.

Additionally:

```python
patient.diagnoses
patient.visits
```

return immutable tuples, preventing callers from accidentally modifying internal state.

---

## 🧱 Composition

A `Patient` **has** `Visit` objects.

A visit belongs to exactly one patient.

```text
Patient
   │
   ├── Visit
   ├── Visit
   └── Visit
```

Visits do not have an independent lifecycle.

When a patient is deleted, their visits are automatically deleted by SQLite using:

```sql
ON DELETE CASCADE
```

---

# 🗃️ Database Schema

```sql
CREATE TABLE patients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    age        INTEGER NOT NULL CHECK (age >= 0 AND age <= 130),
    diagnoses  TEXT    NOT NULL DEFAULT '[]',
    created_at TEXT    NOT NULL
);

CREATE TABLE visits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    visit_date TEXT    NOT NULL,
    reason     TEXT    NOT NULL,
    notes      TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL,

    FOREIGN KEY (patient_id)
        REFERENCES patients(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_patients_name
    ON patients(name);

CREATE INDEX idx_visits_patient_id
    ON visits(patient_id);
```

### 💡 Design Decisions

#### Diagnoses 

Diagnoses are stored as a JSON list inside a `TEXT` column.

```json
["Asthma", "Seasonal allergy"]
```

A fully normalized design would use a separate `diagnoses` table.

For this educational project, JSON keeps the implementation simple and readable.

**Trade-off:** diagnosis statistics are calculated in Python rather than directly in SQL.

#### Foreign Keys

SQLite does not enforce foreign keys by default.

PatientVault explicitly enables them on every connection:

```sql
PRAGMA foreign_keys = ON;
```

This ensures that cascade deletes work correctly.

---

# 🚨 Error Handling

All deliberate application errors inherit from:

```text
PatientVaultError
```

The hierarchy is:

```text
PatientVaultError
├── ValidationError
│   └── Invalid user input
│
├── NotFoundError
│   ├── PatientNotFoundError
│   └── VisitNotFoundError
│
└── RepositoryError
    └── SQL / file system failure
```

Database-level `sqlite3.Error` exceptions never escape the repository layer.

Instead, they are translated into:

```python
RepositoryError
```

The CLI catches the base exception:

```python
PatientVaultError
```

This allows all expected application errors to be handled consistently without exposing Python tracebacks to the user.

---

# 🚀 Setup

### Requirements

* Python **3.8+**
* No third-party dependencies
* SQLite included with Python

Clone the repository:

```bash
git clone https://github.com/<your-username>/patientvault.git
cd patientvault
```

Optionally create a virtual environment:

```bash
python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

No additional packages are required.

---

# ▶️ Usage

Run the application from the project root:

```bash
python -m src.main
```

On Windows, if `python` is not available:

```powershell
py -m src.main
```

### Available Commands

Start with demo data:

```bash
python -m src.main --seed
```

Use a custom database:

```bash
python -m src.main --db data/demo.db
```

Use a temporary in-memory database:

```bash
python -m src.main --db :memory:
```

Show version:

```bash
python -m src.main --version
```

Show help:

```bash
python -m src.main --help
```

---

# 🗂️ Database Location 

PatientVault resolves the database path in the following order:

```text
1. --db PATH
       ↓
2. PATIENTVAULT_DB environment variable
       ↓
3. data/patients.db
```

The first available option is used.

### Windows PowerShell

```powershell
$env:PATIENTVAULT_DB = "C:\vaults\clinic.db"
```

### macOS / Linux

```bash
export PATIENTVAULT_DB=~/vaults/clinic.db
```

---

# 💻 Example Session

```text
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

Diagnoses (comma separated, optional):
Asthma, Seasonal allergy

Saved:

#1 Anna Grigoryan
Age: 34
Diagnoses: Asthma, Seasonal allergy
Visits: 0
```

---

# 📋 Patient List

```text
    ID  NAME                      AGE  VISITS  DIAGNOSES
  --------------------------------------------------------------
     3  Mariam Sargsyan             8       1  Otitis media
     1  Anna Grigoryan             34       2  Asthma, Seasonal allergy
     4  Karen Hovhannisyan         45       0  -
     2  David Petrosyan            67       3  Hypertension, Type 2 diabetes

  4 patient(s).
```

---

# 📊 Statistics

```text
  Statistics
  --------------------------------------------------------------

  Patients:               4
  Visits:                 6
  Average age:            38.5
  Age range:              8 – 67
  Avg visits / patient:   1.5
  Patients with 0 visits: 1

  Most visits:
    David Petrosyan (#2) — 3

  Top diagnoses:
    - asthma: 1
    - hypertension: 1
    - otitis media: 1
    - seasonal allergy: 1
    - type 2 diabetes: 1
```

---

# 🐍 Using the Repository Programmatically

The repository is independent from the CLI and can be used directly from Python code.

```python
from src.models import Patient, Visit
from src.repository import PatientRepository


with PatientRepository("data/patients.db") as repo:

    anna = repo.add_patient(
        Patient(
            name="Anna Grigoryan",
            age=34,
            diagnoses="Asthma"
        )
    )

    repo.add_visit(
        Visit(
            patient_id=anna.id,
            visit_date="2026-05-12",
            reason="Check-up"
        )
    )

    loaded = repo.get_patient(anna.id)

    print(loaded.visit_count)
    print(loaded.last_visit_date)
```

Output:

```text
1
2026-05-12
```

---

# 🧪 Tests

Run the complete test suite:

```bash
python -m unittest discover -s tests -t . -v
```

The project contains **78 unit tests** covering:

* Validation rules
* `Patient` model
* `Visit` model
* Repository methods
* CRUD operations
* Cascade deletes
* Exporters
* Seed data

Tests use:

* In-memory SQLite databases
* Temporary directories
* Python's built-in `unittest`

Your real database is never touched by the test suite.

---

# 📁 Project Structure

```text
patientvault/
│
├── src/
│   ├── __init__.py
│   ├── main.py           # Application entry point
│   ├── cli.py            # Menu, prompts and output
│   ├── models.py         # Patient and Visit models
│   ├── repository.py     # SQLite access and SQL queries
│   ├── validation.py     # Shared validation rules
│   ├── exporters.py      # CSV and JSON exports
│   ├── config.py         # Database path resolution
│   └── seed.py           # Demo data
│
├── tests/
│   ├── __init__.py
│   ├── test_validation.py
│   ├── test_models.py
│   ├── test_repository.py
│   └── test_exporters.py
│
├── data/
│   └── patients.db       # Git-ignored database
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

# 🎯 What I Practised

Building PatientVault helped me practise:

* 🐍 Object-Oriented Programming with Python
* 🧩 Classes, properties, and encapsulation
* 🔗 Composition between domain objects
* 🗄️ SQLite and relational databases
* 📝 SQL CRUD operations
* 🔐 Foreign keys and cascade deletes
* ⚡ Database indexes
* 🛡️ Parameterized SQL queries
* 🏗️ Repository Pattern
* 🚨 Custom exception hierarchies
* ✅ Input validation
* 🧪 Unit testing with `unittest`
* 📦 In-memory database testing
* 📤 CSV and JSON data export
* ⚙️ CLI argument parsing
* 🔧 Environment-based configuration

---

# Key Architecture Concepts

```text
                USER
                  │
                  ▼
             CLI Layer
                  │
                  ▼
            Domain Models
                  │
                  ▼
         Repository Pattern
                  │
                  ▼
              SQLite
```

The main design goal was to keep responsibilities separated:

> **CLI handles interaction.**
> **Models handle domain rules.**
> **Repository handles persistence.**
> **SQLite handles storage.**

This makes the application easier to test, maintain, and extend.

---

# ⚠️ Disclaimer

PatientVault is an **educational software project** and is **not intended for real clinical use**.

It does not provide:

* Authentication
* Authorization
* Encryption
* Audit logging
* HIPAA/GDPR compliance
* Production-grade security

**Never store real patient or medical data in this application.**

All patient names and demo data are fictional.

---

# 📌 Project Status

**Status:** Completed ✅

**Version:** `1.0.0`

**Tests:** `78 passing`

**Dependencies:** None

**Database:** SQLite

**Language:** Python 3.8+

---

<p align="center">

Built with 🐍 Python and 🗄️ SQLite

</p>
