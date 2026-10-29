"""Legacy credential migration with isolated real SQLite transactions."""

import sys
import unittest
from pathlib import Path

from sqlalchemy import Boolean, Column, Integer, LargeBinary, MetaData, String, Table, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.credentials import read_credentials, seal_credentials
from scripts.encrypt_cnc_account_passwords import migrate_passwords


class PasswordMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", hide_parameters=True)
        self.accounts = Table(
            "cnc_account",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("username", String),
            Column("password", String),
            Column("credential_ciphertext", LargeBinary),
            Column("enabled", Boolean, default=True),
            Column("is_deleted", Boolean, default=False),
        )
        self.accounts.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def insert(self, **values):
        with self.engine.begin() as connection:
            connection.execute(self.accounts.insert().values(username="synthetic", **values))

    def rows(self):
        with self.engine.connect() as connection:
            return connection.execute(select(self.accounts).order_by(self.accounts.c.id)).all()

    def migrate(self, apply=False):
        with self.engine.connect() as connection:
            return migrate_passwords(connection, apply=apply)

    def test_dry_run_does_not_write(self):
        self.insert(id=1, password="legacy-synthetic")
        self.assertEqual(self.migrate(), 1)
        row = self.rows()[0]
        self.assertEqual(row.password, "legacy-synthetic")
        self.assertIsNone(row.credential_ciphertext)

    def test_apply_covers_disabled_deleted_and_long_unicode_passwords_and_is_idempotent(self):
        password = "密碼🔐'\"\\\n" * 30
        self.insert(id=1, password=password, enabled=False, is_deleted=True)
        self.assertEqual(self.migrate(apply=True), 1)
        row = self.rows()[0]
        self.assertEqual(row.password, "")
        self.assertEqual(read_credentials(row), ("synthetic", password))
        self.assertNotIn(password.encode(), row.credential_ciphertext)
        self.assertFalse(row.enabled)
        self.assertTrue(row.is_deleted)
        self.assertEqual(self.migrate(apply=True), 0)
        self.assertEqual(self.rows()[0].credential_ciphertext, row.credential_ciphertext)

    def test_existing_ciphertext_is_preserved_and_stale_plaintext_cleared(self):
        ciphertext = seal_credentials("synthetic", "current-password")
        self.insert(id=1, password="stale-plaintext", credential_ciphertext=ciphertext)
        self.assertEqual(self.migrate(apply=True), 1)
        row = self.rows()[0]
        self.assertEqual(row.password, "")
        self.assertEqual(row.credential_ciphertext, ciphertext)
        self.assertEqual(read_credentials(row)[1], "current-password")

    def test_bad_ciphertext_rolls_back_all_rows_and_never_uses_plaintext_fallback(self):
        self.insert(id=1, password="legacy-synthetic")
        self.insert(id=2, password="stale-plaintext", credential_ciphertext=b"invalid-ciphertext")
        with self.assertRaisesRegex(LoginError, "CREDENTIALS_UNAVAILABLE"):
            self.migrate(apply=True)
        rows = self.rows()
        self.assertEqual(rows[0].password, "legacy-synthetic")
        self.assertIsNone(rows[0].credential_ciphertext)
        self.assertEqual(rows[1].password, "stale-plaintext")
        self.assertEqual(rows[1].credential_ciphertext, b"invalid-ciphertext")

    def test_dry_run_validates_existing_ciphertext(self):
        self.insert(id=1, password="stale-plaintext", credential_ciphertext=seal_credentials("another-user", "password"))
        with self.assertRaisesRegex(LoginError, "CREDENTIALS_UNAVAILABLE"):
            self.migrate()
        self.assertEqual(self.rows()[0].password, "stale-plaintext")

    def test_empty_password_rows_are_unchanged(self):
        ciphertext = seal_credentials("synthetic", "current-password")
        self.insert(id=1, password="", credential_ciphertext=ciphertext)
        self.insert(id=2, password="")
        self.assertEqual(self.migrate(apply=True), 0)
        self.assertEqual(self.rows()[0].credential_ciphertext, ciphertext)
        self.assertIsNone(self.rows()[1].credential_ciphertext)


if __name__ == "__main__":
    unittest.main()
