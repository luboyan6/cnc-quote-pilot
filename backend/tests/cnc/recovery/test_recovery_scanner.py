import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from app.modules.cnc.batch.repository import BatchRepository
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel, CncQuoteCapacityModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
from app.modules.cnc.recovery.scanner import RecoveryScanner
from tests.cnc.quote._quote_support import Base, QuoteDatabase, copy_table


class Batch(Base):
    __table__ = copy_table(CncQuoteBatchModel.__table__)


class Capacity(Base):
    __table__ = copy_table(CncQuoteCapacityModel.__table__)


class Item(Base):
    __table__ = copy_table(CncQuoteBatchItemModel.__table__)


class RecoveryScannerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = QuoteDatabase()
        await self.db.asyncSetUp()
        self.sessions = self.db.sessions
        self.batch_repo = BatchRepository(self.sessions)
        self.quotes_mock = AsyncMock()
        self.scanner = RecoveryScanner(
            self.sessions,
            quotes=self.quotes_mock,
            interval=1,
            human_timeout_seconds=60,
        )

    async def asyncTearDown(self):
        await self.scanner.stop()
        await self.db.asyncTearDown()

    async def _create_batch_and_item(self, exec_status="WAITING_HUMAN", updated_delta_seconds=0, run_id=None):
        batch_id = str(uuid4())
        item_id = str(uuid4())
        now = datetime.now(UTC)
        updated_at = now - timedelta(seconds=updated_delta_seconds)
        async with self.sessions() as db, db.begin():
            batch = Batch(
                id=batch_id,
                actor_id=1,
                request_id=str(uuid4()),
                request_fingerprint="fp-" + batch_id[:8],
                status=exec_status,
                created_at=now,
                updated_at=now,
            )
            item = Item(
                id=item_id,
                batch_id=batch_id,
                config_id=1,
                account_id=1,
                input_snapshot={"qty": 1},
                input_fingerprint="ifp-" + item_id[:8],
                exec_status=exec_status,
                attempt_count=1,
                max_attempts=3,
                run_id=run_id,
                created_at=now,
                updated_at=updated_at,
            )
            db.add_all([batch, item])
        return batch_id, item_id

    async def test_scan_expired_human_waits(self):
        # Item 1: expired (120s > 60s timeout)
        _, expired_id = await self._create_batch_and_item(exec_status="WAITING_HUMAN", updated_delta_seconds=120)
        # Item 2: fresh (10s < 60s timeout)
        _, fresh_id = await self._create_batch_and_item(exec_status="WAITING_HUMAN", updated_delta_seconds=10)

        affected = await self.scanner.scan_expired_human_waits()
        self.assertEqual(affected, 1)

        async with self.sessions() as db:
            row_exp = await db.get(Item, expired_id)
            self.assertEqual(row_exp.exec_status, "FAILED")
            self.assertEqual(row_exp.error_code, "MANUAL_TIMEOUT")

            row_fresh = await db.get(Item, fresh_id)
            self.assertEqual(row_fresh.exec_status, "WAITING_HUMAN")

    async def test_timed_out_live_owner_is_cancelled_before_releasing_its_claim(self):
        _, item_id = await self._create_batch_and_item(exec_status="WAITING_HUMAN", updated_delta_seconds=120, run_id="live-run")
        async with self.sessions() as db, db.begin():
            row = await db.get(Item, item_id)
            row.claim_owner = "owner"
            row.claim_until = datetime.now(UTC) + timedelta(minutes=5)
        self.assertEqual(await self.scanner.scan_expired_human_waits(), 1)
        async with self.sessions() as db:
            row = await db.get(Item, item_id)
            self.assertEqual(row.exec_status, "CANCELLING")
            self.assertEqual(row.claim_owner, "owner")
            self.assertIsNotNone(row.cancel_requested_at)

    async def test_scan_stale_reconciliations_success(self):
        _, item_id = await self._create_batch_and_item(exec_status="RECONCILING", run_id="run-100")
        self.quotes_mock.persist_pending_result.return_value = {"quoted": True}

        recovered = await self.scanner.scan_stale_reconciliations()
        self.assertEqual(recovered, 1)

        async with self.sessions() as db:
            row = await db.get(Item, item_id)
            self.assertEqual(row.exec_status, "COMPLETED")

    async def test_scan_stale_reconciliations_when_candidate_not_found(self):
        _, item_id = await self._create_batch_and_item(exec_status="RECONCILING", run_id="run-200")
        self.quotes_mock.persist_pending_result.return_value = None

        recovered = await self.scanner.scan_stale_reconciliations()
        self.assertEqual(recovered, 0)

        async with self.sessions() as db:
            row = await db.get(Item, item_id)
            self.assertEqual(row.exec_status, "RECONCILING")

    async def test_scanner_lifecycle_start_and_stop(self):
        await self.scanner.start()
        self.assertIsNotNone(self.scanner.task)
        self.assertFalse(self.scanner.task.done())
        await self.scanner.stop()
        self.assertIsNone(self.scanner.task)


if __name__ == "__main__":
    unittest.main()
