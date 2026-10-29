"""Storage failures retain useful status without dumping credential parameters."""

import logging
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import text
from sqlalchemy.exc import StatementError

from app.config.setting import settings
from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.database import create_async_engine_and_session, create_sync_engine
from app.core.logger import logger
from app.modules.cnc.cnc_account.crud import CncAccountCRUD


class PlainRow:
    def __init__(self, **values):
        self.__dict__.update(values)


class StoragePrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_crud_failure_omits_traceback_but_base_behavior_is_preserved(self):
        failure = StatementError("synthetic failure", "INSERT accounts", {"credential_ciphertext": "private-synthetic"}, RuntimeError("fixed"))
        db = SimpleNamespace(add=Mock(), flush=AsyncMock(side_effect=failure))
        auth = AuthSchema(user=CoreUserSchema(id=7))
        account_crud = CncAccountCRUD(auth, db)
        with (
            patch.object(account_crud, "model", PlainRow),
            patch("app.modules.cnc.cnc_account.crud.logger.error") as safe_log,
            patch("app.core.base_crud.logger.exception") as trace_log,
        ):
            with self.assertRaises(StatementError):
                await account_crud.create({"credential_ciphertext": b"private-synthetic"})
            safe_log.assert_called_once_with("创建失败")
            trace_log.assert_not_called()
        ordinary_crud = CRUDBase(PlainRow, auth, db)
        with patch("app.core.base_crud.logger.exception") as trace_log:
            with self.assertRaises(StatementError):
                await ordinary_crud.create({"value": "ordinary"})
            trace_log.assert_called_once_with("创建失败")

    async def test_sync_and_async_engine_failures_hide_bound_values(self):
        secret = "synthetic-ciphertext-do-not-log"
        sync_engine = create_sync_engine("sqlite://")
        try:
            self.assertTrue(sync_engine.hide_parameters)
            with sync_engine.connect() as connection:
                with self.assertRaises(StatementError) as failure:
                    connection.execute(text("INSERT INTO missing_private_table VALUES (:secret)"), {"secret": secret})
            self.assertNotIn(secret, str(failure.exception))
        finally:
            sync_engine.dispose()
        with patch.object(settings, "DATABASE_TYPE", "sqlite"):
            engine, _ = create_async_engine_and_session("sqlite+aiosqlite://")
        try:
            self.assertTrue(engine.sync_engine.hide_parameters)
            async with engine.connect() as connection:
                with self.assertRaises(StatementError) as failure:
                    await connection.execute(text("INSERT INTO missing_private_table VALUES (:secret)"), {"secret": secret})
            self.assertNotIn(secret, str(failure.exception))
        finally:
            await engine.dispose()

    async def test_debug_echo_and_driver_logs_never_emit_bound_or_fetched_values(self):
        secret = "synthetic-private-result-and-parameter"
        self.assertGreaterEqual(logging.getLogger("aiosqlite").getEffectiveLevel(), logging.WARNING)
        captured: list[str] = []
        sink = logger.add(lambda message: captured.append(str(message)), level="DEBUG", diagnose=False)
        try:
            with patch.object(settings, "DATABASE_ECHO", "debug"), patch.object(settings, "DATABASE_TYPE", "sqlite"):
                sync_engine = create_sync_engine("sqlite://")
                async_engine, _ = create_async_engine_and_session("sqlite+aiosqlite://")
            try:
                self.assertIs(sync_engine.echo, True)
                self.assertIs(async_engine.echo, True)
                with sync_engine.connect() as connection:
                    self.assertEqual(connection.execute(text("SELECT :secret"), {"secret": secret}).scalar_one(), secret)
                async with async_engine.connect() as connection:
                    self.assertEqual((await connection.execute(text("SELECT :secret"), {"secret": secret})).scalar_one(), secret)
            finally:
                sync_engine.dispose()
                await async_engine.dispose()
            messages = "\n".join(captured)
            self.assertIn("SELECT ?", messages)
            self.assertIn("SQL parameters hidden", messages)
            self.assertNotIn(secret, messages)
        finally:
            logger.remove(sink)


if __name__ == "__main__":
    unittest.main()
