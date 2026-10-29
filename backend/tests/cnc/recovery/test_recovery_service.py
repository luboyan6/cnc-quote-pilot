import unittest
from datetime import UTC, datetime
from uuid import uuid4

from app.modules.cnc.batch.repository import BatchRepository
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel, CncQuoteCapacityModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
from app.modules.cnc.recovery.contracts import (
    RecoveryAction,
    RecoveryError,
    SideEffectState,
)
from app.modules.cnc.recovery.service import RecoveryService
from tests.cnc.quote._quote_support import Base, QuoteDatabase, copy_table


class Batch(Base):
    __table__ = copy_table(CncQuoteBatchModel.__table__)


class Capacity(Base):
    __table__ = copy_table(CncQuoteCapacityModel.__table__)


class Item(Base):
    __table__ = copy_table(CncQuoteBatchItemModel.__table__)


class RecoveryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = QuoteDatabase()
        await self.db.asyncSetUp()
        self.sessions = self.db.sessions
        self.batch_repo = BatchRepository(self.sessions)
        self.recovery_service = RecoveryService(self.sessions, self.batch_repo)

    async def asyncTearDown(self):
        await self.db.asyncTearDown()

    async def _create_batch_and_item(self, actor_id=1, exec_status="PENDING", attempt_count=0, max_attempts=3, run_id=None):
        batch_id = str(uuid4())
        item_id = str(uuid4())
        now = datetime.now(UTC)
        async with self.sessions() as db, db.begin():
            batch = Batch(
                id=batch_id,
                actor_id=actor_id,
                request_id=str(uuid4()),
                request_fingerprint="fp-" + batch_id[:8],
                status="PENDING",
                created_at=now,
                updated_at=now,
            )
            item = Item(
                id=item_id,
                batch_id=batch_id,
                config_id=1,
                account_id=1,
                input_snapshot={"qty": 5},
                input_fingerprint="ifp-" + item_id[:8],
                exec_status=exec_status,
                attempt_count=attempt_count,
                max_attempts=max_attempts,
                run_id=run_id,
                created_at=now,
                updated_at=now,
            )
            db.add_all([batch, item])
        return batch_id, item_id

    async def test_record_failure_network_timeout_transitions_to_retry_wait(self):
        batch_id, item_id = await self._create_batch_and_item(exec_status="PENDING", attempt_count=0)
        decision = await self.recovery_service.record_failure(
            item_id=item_id,
            error="NETWORK_TIMEOUT",
            stage="UPLOADING",
            effect_state=SideEffectState.NONE,
        )
        self.assertEqual(decision.action, RecoveryAction.RETRY_WAIT)
        async with self.sessions() as db:
            row = await db.get(Item, item_id)
            self.assertEqual(row.exec_status, "RETRY_WAIT")
            self.assertEqual(row.attempt_count, 1)
            self.assertIsNotNone(row.next_attempt_at)
            self.assertIsNone(row.claim_owner)

    async def test_record_failure_uncertain_mutation_transitions_to_reconciling(self):
        batch_id, item_id = await self._create_batch_and_item(exec_status="RUNNING", attempt_count=1, run_id="run-1")
        decision = await self.recovery_service.record_failure(
            item_id=item_id,
            error="MUTATION_UNCERTAIN",
            stage="SUBMITTING",
            effect_state=SideEffectState.UNCERTAIN,
        )
        self.assertEqual(decision.action, RecoveryAction.RECONCILING)
        async with self.sessions() as db:
            row = await db.get(Item, item_id)
            self.assertEqual(row.exec_status, "RECONCILING")
            self.assertEqual(row.error_code, "RECONCILIATION_REQUIRED")

    async def test_retry_item_success(self):
        batch_id, item_id = await self._create_batch_and_item(actor_id=1, exec_status="FAILED", attempt_count=1)
        res = await self.recovery_service.retry_item(actor_id=1, item_id=item_id)
        self.assertEqual(res["exec_status"], "PENDING")

        async with self.sessions() as db:
            row = await db.get(Item, item_id)
            self.assertEqual(row.exec_status, "PENDING")
            self.assertIsNone(row.error_code)
            self.assertIsNone(row.claim_owner)

    async def test_retry_cannot_displace_waiting_human_owner_or_cancelled_request(self):
        _, item_id = await self._create_batch_and_item(actor_id=1, exec_status="WAITING_HUMAN", attempt_count=1, run_id="live-run")
        async with self.sessions() as db, db.begin():
            row = await db.get(Item, item_id)
            row.claim_owner = "live-owner"
        with self.assertRaises(RecoveryError):
            await self.recovery_service.retry_item(actor_id=1, item_id=item_id)
        async with self.sessions() as db:
            row = await db.get(Item, item_id)
            self.assertEqual(row.claim_owner, "live-owner")
            self.assertEqual(row.exec_status, "WAITING_HUMAN")

    async def test_retry_item_forbids_completed_or_cancelled(self):
        _, completed_id = await self._create_batch_and_item(actor_id=1, exec_status="COMPLETED")
        with self.assertRaises(RecoveryError) as ctx:
            await self.recovery_service.retry_item(actor_id=1, item_id=completed_id)
        self.assertEqual(ctx.exception.reason, "CANNOT_RETRY_COMPLETED_ITEM")

        _, cancelled_id = await self._create_batch_and_item(actor_id=1, exec_status="CANCELLED")
        with self.assertRaises(RecoveryError) as ctx:
            await self.recovery_service.retry_item(actor_id=1, item_id=cancelled_id)
        self.assertEqual(ctx.exception.reason, "CANNOT_RETRY_CANCELLED_ITEM")

    async def test_retry_item_forbids_uncertain_reconciling_mutation(self):
        _, reconciling_id = await self._create_batch_and_item(actor_id=1, exec_status="RECONCILING")
        with self.assertRaises(RecoveryError) as ctx:
            await self.recovery_service.retry_item(actor_id=1, item_id=reconciling_id)
        self.assertEqual(ctx.exception.reason, "BATCH_UNCERTAIN_MUTATION_RETRY_FORBIDDEN")

    async def test_retry_item_forbids_max_attempts_exceeded_for_non_superuser(self):
        _, exhausted_id = await self._create_batch_and_item(actor_id=1, exec_status="FAILED", attempt_count=3, max_attempts=3)
        with self.assertRaises(RecoveryError) as ctx:
            await self.recovery_service.retry_item(actor_id=1, item_id=exhausted_id, is_superuser=False)
        self.assertEqual(ctx.exception.reason, "MAX_ATTEMPTS_EXCEEDED")

        # Superuser can retry even if budget was exhausted
        res = await self.recovery_service.retry_item(actor_id=1, item_id=exhausted_id, is_superuser=True)
        self.assertEqual(res["exec_status"], "PENDING")

    async def test_retry_item_forbids_unauthorized_actor(self):
        _, item_id = await self._create_batch_and_item(actor_id=1, exec_status="FAILED")
        with self.assertRaises(RecoveryError) as ctx:
            await self.recovery_service.retry_item(actor_id=999, item_id=item_id, is_superuser=False)
        self.assertEqual(ctx.exception.reason, "ITEM_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
