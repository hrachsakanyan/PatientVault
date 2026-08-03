"""Menu-driven command line interface.

The CLI owns *no* domain logic: it collects text, builds Patient / Visit
objects, hands them to the repository and prints what comes back. Any
PatientVaultError is caught here and shown as a friendly message, so a typo
never crashes the program.
"""

from datetime import date

from . import __version__
from .config import IN_MEMORY
from .errors import PatientVaultError, ValidationError
from .exporters import export_json, export_patients_csv, export_visits_csv
from .models import Patient, Visit
from .validation import (
    validate_age,
    validate_date,
    validate_diagnoses,
    validate_id,
    validate_name,
    validate_text,
)

LINE = "=" * 62
THIN = "-" * 62


class ExitRequested(Exception):
    """Raised internally when the user chooses to quit (or presses Ctrl+D)."""


class PatientVaultCLI:
    """Interactive front end for a PatientRepository."""

    def __init__(self, repository, db_source="default location"):
        self.repository = repository
        self.db_source = db_source
        self.menu = [
            ("1", "Add patient", self.add_patient),
            ("2", "List all patients", self.list_patients),
            ("3", "Find patient by id", self.find_patient),
            ("4", "Search patients by name", self.search_patients),
            ("5", "Update patient", self.update_patient),
            ("6", "Delete patient", self.delete_patient),
            ("7", "Add visit to a patient", self.add_visit),
            ("8", "List visits of a patient", self.list_visits),
            ("9", "Delete visit", self.delete_visit),
            ("10", "Statistics", self.show_stats),
            ("11", "Export data (CSV / JSON)", self.export_data),
            ("0", "Exit", self.quit),
        ]

    # --- main loop --------------------------------------------------------

    def run(self):
        self.print_banner()
        while True:
            self.print_menu()
            try:
                choice = self.ask("Choose an option", required=True)
            except ExitRequested:
                print("\nGoodbye!")
                return
            except KeyboardInterrupt:
                print("\nGoodbye!")
                return

            handler = self.find_handler(choice)
            if handler is None:
                print(f"\n  '{choice}' is not on the menu. Try again.")
                continue

            try:
                handler()
            except ExitRequested:
                print("\nGoodbye!")
                return
            except PatientVaultError as exc:
                print(f"\n  Error: {exc}")
            except KeyboardInterrupt:
                print("\n  Cancelled.")

    def find_handler(self, choice):
        for key, _label, handler in self.menu:
            if choice == key:
                return handler
        return None

    def print_banner(self):
        location = self.repository.db_path
        location = "in-memory (nothing is saved)" if location == IN_MEMORY else location
        print(LINE)
        print(f"  PatientVault {__version__} — patient records manager")
        print(f"  Database: {location}")
        print(f"  Source:   {self.db_source}")
        print("  Educational project — do not store real patient data.")
        print(LINE)

    def print_menu(self):
        print(f"\n{THIN}")
        for key, label, _handler in self.menu:
            print(f"  {key:>2}) {label}")
        print(THIN)

    # --- input helpers ----------------------------------------------------

    def ask(self, prompt, default=None, required=False):
        """Read one line. Ctrl+D / Ctrl+Z quits, blank input returns default."""
        suffix = f" [{default}]" if default not in (None, "") else ""
        while True:
            try:
                answer = input(f"{prompt}{suffix}: ").strip()
            except EOFError:
                raise ExitRequested from None
            if not answer and default is not None:
                return default
            if answer or not required:
                return answer
            print("  This field is required.")

    def ask_valid(self, prompt, validator, default=None, allow_blank=False):
        """Keep asking until `validator` accepts the answer."""
        while True:
            answer = self.ask(prompt, default=default)
            if not answer and allow_blank:
                return None
            try:
                return validator(answer)
            except ValidationError as exc:
                print(f"  {exc}")

    def ask_patient_id(self, prompt="Patient id"):
        return self.ask_valid(prompt, lambda value: validate_id(value, "Patient id"))

    def confirm(self, prompt):
        answer = self.ask(f"{prompt} (y/n)", default="n").lower()
        return answer in ("y", "yes")

    # --- output helpers ---------------------------------------------------

    @staticmethod
    def print_patient_table(patients):
        if not patients:
            print("\n  No patients to show.")
            return
        print(f"\n  {'ID':>4}  {'NAME':<24} {'AGE':>4}  {'VISITS':>6}  DIAGNOSES")
        print(f"  {THIN}")
        for patient in patients:
            name = patient.name if len(patient.name) <= 24 else patient.name[:21] + "..."
            diagnoses = patient.diagnoses_text()
            if len(diagnoses) > 30:
                diagnoses = diagnoses[:27] + "..."
            print(
                f"  {patient.id:>4}  {name:<24} {patient.age:>4}  "
                f"{patient.visit_count:>6}  {diagnoses}"
            )
        print(f"\n  {len(patients)} patient(s).")

    @staticmethod
    def print_patient_detail(patient):
        print(f"\n  Patient #{patient.id}")
        print(f"  {THIN}")
        print(f"  Name:       {patient.name}")
        print(f"  Age:        {patient.age}")
        print(f"  Diagnoses:  {patient.diagnoses_text()}")
        print(f"  Registered: {patient.created_at}")
        print(f"  Visits:     {patient.visit_count}")
        for visit in patient.visits:
            print(f"    - {visit}")

    # --- menu actions: patients -------------------------------------------

    def add_patient(self):
        print("\n  New patient")
        name = self.ask_valid("  Name", validate_name)
        age = self.ask_valid("  Age", validate_age)
        diagnoses = self.ask("  Diagnoses (comma separated, optional)")

        patient = Patient(name=name, age=age, diagnoses=diagnoses)
        self.repository.add_patient(patient)
        print(f"\n  Saved: {patient}")

    def list_patients(self):
        order = self.ask("\n  Sort by (name / age / id)", default="name").lower()
        if order not in ("name", "age", "id"):
            print("  Unknown sort key, using 'name'.")
            order = "name"
        self.print_patient_table(self.repository.list_patients(order_by=order, with_visits=True))

    def find_patient(self):
        patient_id = self.ask_patient_id("\n  Patient id")
        self.print_patient_detail(self.repository.get_patient(patient_id))

    def search_patients(self):
        term = self.ask("\n  Name contains", required=True)
        results = self.repository.search_patients(term, with_visits=True)
        if not results:
            print(f"\n  No patient matches {term!r}.")
            return
        self.print_patient_table(results)

    def update_patient(self):
        patient_id = self.ask_patient_id("\n  Id of the patient to update")
        patient = self.repository.get_patient(patient_id)
        self.print_patient_detail(patient)
        print("\n  Press Enter to keep the current value.")

        patient.name = self.ask_valid("  Name", validate_name, default=patient.name)
        patient.age = self.ask_valid("  Age", validate_age, default=str(patient.age))
        current = patient.diagnoses_text() if patient.diagnoses else ""
        patient.diagnoses = self.ask_valid(
            "  Diagnoses (comma separated)", validate_diagnoses, default=current
        )

        self.repository.update_patient(patient)
        print(f"\n  Updated: {patient}")

    def delete_patient(self):
        patient_id = self.ask_patient_id("\n  Id of the patient to delete")
        patient = self.repository.get_patient(patient_id)
        self.print_patient_detail(patient)
        if not self.confirm(f"\n  Delete {patient.name} and all {patient.visit_count} visit(s)?"):
            print("  Cancelled.")
            return
        self.repository.delete_patient(patient_id)
        print(f"\n  Patient #{patient_id} deleted.")

    # --- menu actions: visits ----------------------------------------------

    def add_visit(self):
        patient_id = self.ask_patient_id("\n  Patient id")
        patient = self.repository.get_patient(patient_id, with_visits=False)
        print(f"  Adding a visit for {patient.name}.")

        today = date.today().isoformat()
        visit_date = self.ask_valid("  Date (YYYY-MM-DD)", validate_date, default=today)
        reason = self.ask_valid("  Reason", _validate_reason)
        notes = self.ask("  Notes (optional)")

        visit = Visit(patient_id=patient_id, visit_date=visit_date, reason=reason, notes=notes)
        self.repository.add_visit(visit)
        print(f"\n  Saved visit {visit}")

    def list_visits(self):
        patient_id = self.ask_patient_id("\n  Patient id")
        patient = self.repository.get_patient(patient_id)
        if not patient.visit_count:
            print(f"\n  {patient.name} has no visits yet.")
            return
        print(f"\n  Visits of {patient.name} (#{patient.id}):")
        print(f"  {THIN}")
        for visit in patient.visits:
            print(f"  {visit}")
        print(f"\n  {patient.visit_count} visit(s).")

    def delete_visit(self):
        visit_id = self.ask_valid("\n  Visit id", lambda v: validate_id(v, "Visit id"))
        visit = self.repository.get_visit(visit_id)
        print(f"  {visit}")
        if not self.confirm("  Delete this visit?"):
            print("  Cancelled.")
            return
        self.repository.delete_visit(visit_id)
        print(f"\n  Visit #{visit_id} deleted.")

    # --- menu actions: extras ----------------------------------------------

    def show_stats(self):
        stats = self.repository.stats()
        print("\n  Statistics")
        print(f"  {THIN}")
        print(f"  Patients:               {stats['total_patients']}")
        print(f"  Visits:                 {stats['total_visits']}")
        print(f"  Average age:            {_or_dash(stats['average_age'])}")
        print(f"  Age range:              {_range(stats['youngest_age'], stats['oldest_age'])}")
        print(f"  Avg visits / patient:   {stats['average_visits_per_patient']}")
        print(f"  Patients with 0 visits: {stats['patients_without_visits']}")

        busiest = stats["busiest_patient"]
        if busiest:
            print(
                f"  Most visits:            {busiest['name']} (#{busiest['id']}) "
                f"— {busiest['visits']}"
            )
        if stats["top_diagnoses"]:
            print("  Top diagnoses:")
            for entry in stats["top_diagnoses"]:
                print(f"    - {entry['diagnosis']}: {entry['count']}")

    def export_data(self):
        print("\n  Export")
        print("    1) patients.csv")
        print("    2) visits.csv")
        print("    3) vault.json (patients + visits + stats)")
        choice = self.ask("  Choose a format", default="3")

        actions = {
            "1": ("exports/patients.csv", export_patients_csv),
            "2": ("exports/visits.csv", export_visits_csv),
            "3": ("exports/vault.json", export_json),
        }
        if choice not in actions:
            print("  Unknown format.")
            return

        default_path, exporter = actions[choice]
        path = self.ask("  Save to", default=default_path)
        written = exporter(self.repository, path)
        print(f"\n  Exported to {written.resolve()}")

    def quit(self):
        raise ExitRequested


# --- small helpers ----------------------------------------------------------


def _validate_reason(value):
    return validate_text(value, "Reason", max_length=200)


def _or_dash(value):
    return "-" if value is None else value


def _range(low, high):
    if low is None or high is None:
        return "-"
    return f"{low} – {high}"
