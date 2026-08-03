"""Configuration: where the SQLite file lives.

Resolution order (first match wins):
    1. an explicit path passed on the command line (--db)
    2. the PATIENTVAULT_DB environment variable
    3. <project root>/data/patients.db
"""

import os
from pathlib import Path

ENV_VAR = "PATIENTVAULT_DB"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "patients.db"

#: sqlite3 accepts this special name for a throwaway in-memory database.
IN_MEMORY = ":memory:"


def resolve_db_path(cli_path=None):
    """Return the database path to use, as a Path (or the ':memory:' string)."""
    raw = cli_path or os.environ.get(ENV_VAR) or DEFAULT_DB_PATH
    if str(raw) == IN_MEMORY:
        return IN_MEMORY
    return Path(raw).expanduser()


def describe_source(cli_path=None):
    """Explain which configuration source won, for the CLI banner."""
    if cli_path:
        return "--db argument"
    if os.environ.get(ENV_VAR):
        return f"{ENV_VAR} environment variable"
    return "default location"
