"""Encrypt every remaining legacy CNC password with the application's key ring.

Run from backend: .venv/Scripts/python.exe scripts/encrypt_cnc_account_passwords.py
The default validates and counts only; add --apply to commit one atomic migration.
"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import Integer, LargeBinary, String, column, select, table, update
from sqlalchemy.engine import Connection

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.cnc.login.credentials import read_credentials, seal_credentials

_ACCOUNTS = table(
    "cnc_account",
    column("id", Integer),
    column("username", String),
    column("password", String),
    column("credential_ciphertext", LargeBinary),
)


def migrate_passwords(connection: Connection, *, apply: bool = False) -> int:
    """Validate candidates and optionally migrate, including disabled/deleted rows.

    The connection must have no active transaction. Any failed credential or write
    rolls back every change. Existing ciphertext remains authoritative and intact.
    """
    with connection.begin():
        query = select(_ACCOUNTS).where(_ACCOUNTS.c.password != "").order_by(_ACCOUNTS.c.id)
        if apply:
            query = query.with_for_update()
        rows = connection.execute(query).all()
        for row in rows:
            username, password = read_credentials(row)
            if apply:
                ciphertext = row.credential_ciphertext or seal_credentials(username, password)
                connection.execute(update(_ACCOUNTS).where(_ACCOUNTS.c.id == row.id).values(password="", credential_ciphertext=ciphertext))
        return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Encrypt legacy CNC account passwords; output contains counts only.")
    parser.add_argument("--apply", action="store_true", help="Commit the migration (default: validate without writing).")
    args = parser.parse_args()
    # Suppress driver/debug logs and traceback locals for this credential operation.
    logging.disable(logging.CRITICAL)
    from app.core.logger import logger

    logger.remove()
    engine = None
    try:
        from app.core.database import create_sync_engine

        engine = create_sync_engine()
        engine.echo = False
        engine.hide_parameters = True
        with engine.connect() as connection:
            count = migrate_passwords(connection, apply=args.apply)
        print(f"{'Migrated' if args.apply else 'Validated (dry run)'}: {count} account(s).")
        return 0
    except Exception:
        print("Migration failed; transaction rolled back. Check the database schema and encryption keys.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
