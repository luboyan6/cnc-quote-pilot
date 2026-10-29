"""Opt-in PostgreSQL lock tests in a disposable, per-test schema.

Set CNC_BATCH_PG_TEST_DSN to an isolated PostgreSQL database. The tests never
connect to the application's configured database implicitly.
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Table, event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.modules.cnc.batch import repository as batch_repository
from app.modules.cnc.batch.contracts import BatchError, attempt_request_id
from app.modules.cnc.cnc_quote_schedule.model import CncQuoteScheduleModel
from app.modules.cnc.cnc_quote_schedule_round.model import CncQuoteScheduleRoundModel
from app.modules.cnc.monitor.contracts import ScheduleCreate, ScheduleTarget
from app.modules.cnc.monitor.repository import ScheduleRepository
from app.modules.cnc.quote.contracts import QuoteError, QuoteResult
from tests.cnc.batch import test_batch_migration as migration_cases
from tests.cnc.batch import test_batch_service as batch_cases
from tests.cnc.quote import _quote_support as support

support.copy_table(CncQuoteScheduleModel.__table__)
support.copy_table(CncQuoteScheduleRoundModel.__table__)


@pytest.mark.skipif(not os.environ.get("CNC_BATCH_PG_TEST_DSN"), reason="Explicit isolated PostgreSQL test DSN not supplied")
class PostgresBatchTests(batch_cases.BatchTests):
    """Run portable business cases and real PostgreSQL contention checks."""

    async def asyncSetUp(self):
        dsn = os.environ["CNC_BATCH_PG_TEST_DSN"]
        if not dsn.startswith("postgresql+asyncpg://"):
            raise ValueError("CNC_BATCH_PG_TEST_DSN must use postgresql+asyncpg")

        # Generated identifiers are confined to a fresh schema and contain
        # only a fixed prefix and UUID hex, making the quoted DDL safe.
        self.pg_schema = "cnc_t1_" + uuid4().hex
        self.pg_admin = create_async_engine(dsn, hide_parameters=True)
        try:
            async with self.pg_admin.begin() as connection:
                await connection.execute(text(f'CREATE SCHEMA "{self.pg_schema}"'))
        except BaseException:
            await self.pg_admin.dispose()
            raise
        self.addAsyncCleanup(self._drop_test_schema)

        scoped = create_async_engine(dsn, connect_args={"server_settings": {"search_path": self.pg_schema}}, hide_parameters=True)
        self.addAsyncCleanup(scoped.dispose)
        # Reuse the actual transaction fixtures, but replace their SQLite
        # engine with an independent PG engine before their setup runs.
        with patch.object(support, "create_async_engine", return_value=scoped):
            await super().asyncSetUp()
        # The SQLite fixture does not enforce foreign keys by default. Real PG
        # does, so seed the actual result audit-table references explicitly.
        async with self.sessions() as db, db.begin():
            await db.execute(support.Base.metadata.tables["sys_user"].insert(), [{"id": 7}, {"id": 99}])

    async def _drop_test_schema(self):
        try:
            async with self.pg_admin.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{self.pg_schema}" CASCADE'))
        finally:
            await self.pg_admin.dispose()

    async def test_concurrent_capacity_admission_is_atomic(self):
        self.repository.capacity = 2
        outcomes = await asyncio.wait_for(asyncio.gather(*(self.service.create(self.auth, self.request([1, 2])) for _ in range(3)), return_exceptions=True), timeout=10)
        accepted = [outcome for outcome in outcomes if isinstance(outcome, dict)]
        rejected = [outcome for outcome in outcomes if isinstance(outcome, BatchError)]
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(rejected), 2)
        self.assertTrue(all(error.reason == "BATCH_QUEUE_FULL" for error in rejected))
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(batch_cases.Batch)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(batch_cases.Item)), 2)

    async def test_scheduled_and_manual_admission_share_capacity_lock(self):
        self.repository.capacity = 1
        schedules = ScheduleRepository(self.sessions, capacity_limit=1)
        now = datetime.now(UTC)
        data = ScheduleCreate(name="concurrent", interval_minutes=15, targets=[ScheduleTarget(config_id=5, account_id=31, quantities=[1])])
        schedule_id = await schedules.create(7, data, {"items": [{"config_id": 5, "account_id": 31, "requested": {"quantity": "1"}}]})
        async with self.sessions() as db, db.begin():
            schedule = await db.get(CncQuoteScheduleModel, schedule_id)
            schedule.next_run_at = now
        outcomes = await asyncio.wait_for(asyncio.gather(self.service.create(self.auth, self.request([1])), schedules.scan_due(clock_now=now), return_exceptions=True), timeout=10)
        async with self.sessions() as db:
            count = await db.scalar(select(func.count()).select_from(batch_cases.Item))
        self.assertEqual(count, 1)
        self.assertTrue(any(isinstance(outcome, BatchError) or (isinstance(outcome, list) and outcome[0]["status"] == "CAPACITY_WAIT") for outcome in outcomes))

    async def test_claim_skips_a_row_locked_by_another_transaction(self):
        created = await self.service.create(self.auth, self.request([1, 2]))
        item = batch_cases.Item.__table__
        async with self.sessions() as locking, locking.begin():
            first = await locking.scalar(select(item.c.id).where(item.c.batch_id == created["id"]).order_by(item.c.created_at, item.c.id).limit(1).with_for_update())
            claim = await asyncio.wait_for(self.repository.claim("second-owner"), timeout=5)
            self.assertIsNotNone(claim)
            self.assertNotEqual(claim["id"], first)
        remaining = await asyncio.wait_for(self.repository.claim("first-owner"), timeout=5)
        self.assertEqual(remaining["id"], first)

    async def test_same_configuration_runs_cannot_win_concurrently(self):
        await self.service.create(self.auth, self.request([1, 2]))
        claims = [await self.repository.claim("owner-a"), await self.repository.claim("owner-b")]
        snapshots = [await self.repo.from_frozen(self.auth, claim["input_snapshot"]) for claim in claims]
        outcomes = await asyncio.wait_for(
            asyncio.gather(
                *(self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim) for snapshot, claim in zip(snapshots, claims, strict=True)),
                return_exceptions=True,
            ),
            timeout=10,
        )
        winners = [outcome for outcome in outcomes if isinstance(outcome, tuple)]
        conflicts = [outcome for outcome in outcomes if isinstance(outcome, QuoteError)]
        self.assertEqual(len(winners), 1)
        self.assertTrue(winners[0][1])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].reason, "CONFIGURATION_BUSY")
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(support.CncQuoteRunModel)), 1)

    async def test_release_wait_rechecks_expiry_after_row_lock(self):
        await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        item = cast(Table, batch_cases.Item.__table__)
        now = datetime.now(UTC)
        deadline = now + timedelta(minutes=1)
        clock = [now]
        waiting = asyncio.Event()

        def observe_release(_connection, _cursor, statement, _parameters, _context, _executemany):
            if "cnc_quote_batch_item" in statement and ("FOR UPDATE" in statement.upper() or statement.lstrip().upper().startswith("UPDATE")):
                waiting.set()

        task = None
        listening = False
        try:
            with patch.object(batch_repository, "utcnow", side_effect=lambda: clock[0]):
                async with self.sessions() as locking, locking.begin():
                    await locking.execute(item.update().where(item.c.id == claim["id"]).values(claim_until=deadline))
                    event.listen(self.engine.sync_engine, "before_cursor_execute", observe_release)
                    listening = True
                    task = asyncio.create_task(self.repository.release_wait(claim))
                    await asyncio.wait_for(waiting.wait(), timeout=10)
                    # Advance only the clock after the blocked statement began;
                    # the competing transaction still owns the actual row lock.
                    clock[0] = deadline + timedelta(seconds=1)
                await asyncio.wait_for(task, timeout=10)
        finally:
            if listening:
                event.remove(self.engine.sync_engine, "before_cursor_execute", observe_release)
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        async with self.sessions() as db:
            row = (await db.execute(select(item.c.claim_owner, item.c.claim_token, item.c.claim_until).where(item.c.id == claim["id"]))).one()
            self.assertEqual((row.claim_owner, row.claim_token, row.claim_until), ("owner", claim["token"], deadline))

    async def test_cancel_and_duplicate_completion_preserve_one_result(self):
        created = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        candidate = view.model_copy(
            update={
                "status": "REFERENCE_ESTIMATE",
                "stage": "complete",
                "result": QuoteResult(status="REFERENCE_ESTIMATE", amount="12.34", currency="USD", price_scope="unit", effective=view.requested, observed_at=datetime.now(UTC)),
            }
        )
        both_waiting = asyncio.Event()
        lock_queries = 0

        def observe_item_lock(_connection, _cursor, statement, _parameters, _context, _executemany):
            nonlocal lock_queries
            if "cnc_quote_batch_item" in statement and "FOR UPDATE" in statement.upper():
                lock_queries += 1
                if lock_queries >= 2:
                    both_waiting.set()

        tasks = []
        listening = False
        try:
            async with self.sessions() as locking, locking.begin():
                item = batch_cases.Item.__table__
                await locking.execute(select(item.c.id).where(item.c.id == claim["id"]).with_for_update())
                event.listen(self.engine.sync_engine, "before_cursor_execute", observe_item_lock)
                listening = True
                tasks = [asyncio.create_task(self.repo.save(candidate)), asyncio.create_task(self.repository.cancel(7, created["id"])), asyncio.create_task(self.repo.save(candidate))]
                # Both cancellation and completion must contend for the item
                # row before the third transaction releases it.
                await asyncio.wait_for(both_waiting.wait(), timeout=10)
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)
        finally:
            if listening:
                event.remove(self.engine.sync_engine, "before_cursor_execute", observe_item_lock)
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        self.assertEqual((await self.repository.detail(7, created["id"]))["status"], "COMPLETED")
        async with self.sessions() as db:
            count = await db.scalar(select(func.count()).select_from(support.CncQuoteResultModel).where(support.CncQuoteResultModel.__table__.c.run_id == view.run_id))
            self.assertEqual(count, 1)

    async def test_postgres_migration_preserves_history_and_enforces_unique_result(self):
        migration_schema = self.pg_schema + "_migration"
        async with self.pg_admin.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{migration_schema}"'))
        engine = create_async_engine(os.environ["CNC_BATCH_PG_TEST_DSN"], connect_args={"server_settings": {"search_path": migration_schema}}, hide_parameters=True)

        def exercise_migration(connection):
            root = Path(__file__).resolve().parents[3] / "app/alembic/versions"
            original = migration_cases.migration(root / "2026_10_23_1600_c9e3a6b72f14.py")
            new = migration_cases.migration(root / "2026_10_28_1400_d4b9a2f61028.py")
            operations = Operations(MigrationContext.configure(connection))
            setattr(original, "op", operations)
            setattr(new, "op", operations)
            original.upgrade()
            connection.execute(text("CREATE TABLE cnc_quote_result (id INTEGER PRIMARY KEY, run_id VARCHAR(64), currency VARCHAR(10) NOT NULL)"))
            connection.execute(text("INSERT INTO cnc_quote_result(id, run_id, currency) VALUES (1, 'old-run', 'USD'), (2, 'old-run', 'USD')"))
            with pytest.raises(RuntimeError, match="old-run"):
                new.upgrade()
            assert connection.scalar(text("SELECT COUNT(*) FROM cnc_quote_result")) == 2
            assert "cnc_quote_batch" not in inspect(connection).get_table_names()
            connection.execute(text("DELETE FROM cnc_quote_result WHERE id = 2"))
            new.upgrade()
            assert connection.scalar(text("SELECT version FROM cnc_quote_capacity WHERE id = 1")) == 0
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text("INSERT INTO cnc_quote_result(id, run_id, currency) VALUES (3, 'old-run', NULL)"))
            assert connection.scalar(text("SELECT COUNT(*) FROM cnc_quote_result WHERE run_id = 'old-run'")) == 1
            assert ("run_id",) in {tuple(constraint["column_names"]) for constraint in inspect(connection).get_unique_constraints("cnc_quote_result")}
            new.downgrade()

        try:
            async with engine.begin() as connection:
                await connection.run_sync(exercise_migration)
        finally:
            await engine.dispose()
            async with self.pg_admin.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{migration_schema}" CASCADE'))
