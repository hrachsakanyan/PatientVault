"""Entry point.

Run from the project root:

    python -m src.main
    python -m src.main --db data/demo.db
    python -m src.main --seed --db :memory:
"""

import argparse
import sys

from . import __version__
from .config import ENV_VAR, describe_source, resolve_db_path
from .errors import PatientVaultError
from .cli import PatientVaultCLI
from .repository import PatientRepository
from .seed import seed_demo_data


def build_parser():
    parser = argparse.ArgumentParser(
        prog="patientvault",
        description="PatientVault — an OOP + SQLite patient records manager.",
        epilog=f"The database path can also be set with the {ENV_VAR} environment variable.",
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        help="path to the SQLite file (use ':memory:' for a throwaway database)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="insert a few demo patients before starting (only if the vault is empty)",
    )
    parser.add_argument("--version", action="version", version=f"PatientVault {__version__}")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        with PatientRepository(resolve_db_path(args.db)) as repository:
            if args.seed:
                added = seed_demo_data(repository)
                print(f"Seeded {added} demo patient(s).")
            PatientVaultCLI(repository, db_source=describe_source(args.db)).run()
    except PatientVaultError as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
