"""Real independent SQLite transactions for fencing and legacy migration.

Uses an isolated minimal mapping, not the site's PostgreSQL tables or fixtures.
This proves conditional updates and transaction behavior, not PostgreSQL rollout.
"""

import asyncio
import logging
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String, event, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.modules.cnc.login import repository
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.credentials import read_credentials


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "isolated_login_account"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)
    platform_id: Mapped[int] = mapped_column(Integer, default=2)
    created_id: Mapped[int] = mapped_column(Integer, default=7)
    login_method: Mapped[str] = mapped_column(String, default="PASSWORD")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    credential_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    session_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    session_status: Mapped[str | None] = mapped_column(String, nullable=True)
    session_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_verified_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String, nullable=True)
    lease_until: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    lease_token: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def platform(self):
        return SimpleNamespace(name="Synthetic", is_deleted=False, login_url="https://www.xometry.com/account/login/", quote_entry_url="https://www.xometry.com/quoting/home/")


class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_sqlite_log_level = logging.getLogger("aiosqlite").level
        logging.getLogger("aiosqlite").setLevel(logging.WARNING)
        self.directory = tempfile.TemporaryDirectory(prefix="cnc-login-repository-")
        self.engine = create_async_engine("sqlite+aiosqlite:///" + str(Path(self.directory.name) / "isolated.db"))
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db, db.begin():
            db.add(Account(id=31, username="synthetic", password="legacy-synthetic"))
        self.patch = patch.object(repository, "CncAccountModel", Account)
        self.patch.start()
        self.repo = repository.LoginRepository(self.sessions)
        self.auth = AuthSchema(user=CoreUserSchema(id=7, is_superuser=False))
        self.snapshot = await self.repo.load(self.auth, 31)

    async def asyncTearDown(self):
        self.patch.stop()
        await self.engine.dispose()
        self.directory.cleanup()
        logging.getLogger("aiosqlite").setLevel(self.previous_sqlite_log_level)

    async def row(self):
        async with self.sessions() as db:
            return await db.scalar(select(Account).where(Account.id == 31))

    async def test_load_migrates_legacy_secret_in_committed_independent_transaction(self):
        row = await self.row()
        self.assertEqual(row.password, "")
        self.assertTrue(row.credential_ciphertext)
        self.assertEqual(read_credentials(row), ("synthetic", "legacy-synthetic"))
        self.assertEqual(self.snapshot.password, "legacy-synthetic")

    async def test_concurrent_claims_have_one_winner(self):
        results = await asyncio.gather(self.repo.claim(self.snapshot, "worker-one"), self.repo.claim(self.snapshot, "worker-two"), return_exceptions=True)
        self.assertEqual(sum(isinstance(value, int) for value in results), 1)
        failures = [value for value in results if isinstance(value, LoginError)]
        self.assertEqual([value.reason for value in failures], ["ACCOUNT_BUSY"])
        self.assertEqual((await self.row()).lease_token, 1)

    async def test_expired_lease_takeover_fences_old_renewal_and_release(self):
        old_token = await self.repo.claim(self.snapshot, "old-worker")
        async with self.sessions() as db, db.begin():
            await db.execute(update(Account).where(Account.id == 31).values(lease_until=repository.utcnow() - timedelta(seconds=1)))
        new_token = await self.repo.claim(self.snapshot, "new-worker")
        self.assertGreater(new_token, old_token)
        with self.assertRaisesRegex(LoginError, "LEASE_LOST"):
            await self.repo.renew(self.snapshot, "old-worker", old_token, state="must-not-save")
        await self.repo.release(self.snapshot, "old-worker", old_token)
        row = await self.row()
        self.assertEqual(row.lease_owner, "new-worker")
        self.assertIsNone(row.session_ciphertext)
        await self.repo.renew(self.snapshot, "new-worker", new_token, state="synthetic-encrypted-state")
        row = await self.row()
        self.assertEqual(row.session_ciphertext, b"synthetic-encrypted-state")
        self.assertEqual(row.session_status, "VALID")
        self.assertEqual(row.session_version, 1)

    async def test_changed_account_or_revoked_owner_is_rechecked(self):
        token = await self.repo.claim(self.snapshot, "worker")
        async with self.sessions() as db, db.begin():
            await db.execute(update(Account).where(Account.id == 31).values(created_id=99))
        with self.assertRaisesRegex(LoginError, "ACCOUNT_UNAVAILABLE"):
            await self.repo.load(self.auth, 31)
        with self.assertRaisesRegex(LoginError, "ACCOUNT_CHANGED_OR_LEASE_LOST"):
            await self.repo.renew(self.snapshot, "worker", token)

    async def test_expiry_between_read_and_write_cannot_report_successful_renewal(self):
        token = await self.repo.claim(self.snapshot, "worker")
        initial = repository.utcnow()
        clock = SimpleNamespace(now=initial)

        def expire_after_read(connection, cursor, statement, parameters, context, many):
            if statement.lstrip().startswith("SELECT"):
                clock.now = initial + timedelta(seconds=61)

        event.listen(self.engine.sync_engine, "after_cursor_execute", expire_after_read)
        try:
            with patch.object(repository, "utcnow", side_effect=lambda: clock.now):
                with self.assertRaisesRegex(LoginError, "LEASE_LOST"):
                    await self.repo.renew(self.snapshot, "worker", token, state="must-not-be-saved")
        finally:
            event.remove(self.engine.sync_engine, "after_cursor_execute", expire_after_read)
        self.assertIsNone((await self.row()).session_ciphertext)


if __name__ == "__main__":
    unittest.main()
