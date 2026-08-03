"""Exception hierarchy for PatientVault.

Every error raised on purpose by this project inherits from PatientVaultError,
so the CLI can catch one type and still show a useful message.
"""


class PatientVaultError(Exception):
    """Base class for all PatientVault errors."""


class ValidationError(PatientVaultError):
    """Raised when user input does not satisfy a domain rule."""


class NotFoundError(PatientVaultError):
    """Base class for lookups that returned nothing."""


class PatientNotFoundError(NotFoundError):
    """Raised when no patient exists with the requested id."""

    def __init__(self, patient_id):
        super().__init__(f"No patient found with id {patient_id}.")
        self.patient_id = patient_id


class VisitNotFoundError(NotFoundError):
    """Raised when no visit exists with the requested id."""

    def __init__(self, visit_id):
        super().__init__(f"No visit found with id {visit_id}.")
        self.visit_id = visit_id


class RepositoryError(PatientVaultError):
    """Raised when the storage layer itself fails (SQL, file access, ...)."""
