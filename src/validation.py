"""Input validation layer.

The models call these helpers from their property setters, so an invalid
Patient or Visit object can never exist — bad data is rejected before it ever
reaches SQLite.
"""

from datetime import date, datetime

from .errors import ValidationError

MIN_AGE = 0
MAX_AGE = 130
MAX_NAME_LENGTH = 100
MIN_YEAR = 1900
DATE_FORMAT = "%Y-%m-%d"


def validate_name(value):
    """Return a cleaned patient name or raise ValidationError."""
    if not isinstance(value, str):
        raise ValidationError("Name must be text.")

    name = " ".join(value.split())
    if not name:
        raise ValidationError("Name cannot be empty.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"Name cannot be longer than {MAX_NAME_LENGTH} characters.")
    if not any(char.isalpha() for char in name):
        raise ValidationError("Name must contain at least one letter.")
    return name


def validate_age(value):
    """Return an age as int or raise ValidationError."""
    if isinstance(value, bool):
        raise ValidationError("Age must be a whole number.")
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValidationError("Age cannot be empty.")
    try:
        age = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Age must be a whole number, got {value!r}.") from None

    if age < MIN_AGE or age > MAX_AGE:
        raise ValidationError(f"Age must be between {MIN_AGE} and {MAX_AGE}, got {age}.")
    return age


def validate_diagnoses(value):
    """Normalise diagnoses into a de-duplicated list of clean strings.

    Accepts either a comma-separated string (what the CLI collects) or any
    iterable of strings (what the repository reads back from JSON).
    """
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        try:
            raw_items = list(value)
        except TypeError:
            raise ValidationError("Diagnoses must be text or a list of texts.") from None

    diagnoses = []
    for item in raw_items:
        if not isinstance(item, str):
            raise ValidationError(f"Each diagnosis must be text, got {item!r}.")
        cleaned = " ".join(item.split())
        if cleaned and cleaned.lower() not in [d.lower() for d in diagnoses]:
            diagnoses.append(cleaned)
    return diagnoses


def validate_date(value):
    """Return an ISO date string (YYYY-MM-DD) or raise ValidationError."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValidationError("Date cannot be empty.")
        try:
            parsed = datetime.strptime(text, DATE_FORMAT).date()
        except ValueError:
            raise ValidationError(f"Date must look like YYYY-MM-DD, got {value!r}.") from None
    else:
        raise ValidationError(f"Date must be text or a date object, got {value!r}.")

    if parsed.year < MIN_YEAR:
        raise ValidationError(f"Date must be in year {MIN_YEAR} or later, got {parsed.isoformat()}.")
    return parsed.isoformat()


def validate_text(value, field_name, max_length=500, required=True):
    """Return cleaned free text for fields such as a visit reason or notes."""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be text.")

    text = value.strip()
    if required and not text:
        raise ValidationError(f"{field_name} cannot be empty.")
    if len(text) > max_length:
        raise ValidationError(f"{field_name} cannot be longer than {max_length} characters.")
    return text


def validate_id(value, field_name="Id"):
    """Return a positive int id or raise ValidationError."""
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a positive whole number.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a positive whole number, got {value!r}.") from None
    if number <= 0:
        raise ValidationError(f"{field_name} must be greater than 0, got {number}.")
    return number
