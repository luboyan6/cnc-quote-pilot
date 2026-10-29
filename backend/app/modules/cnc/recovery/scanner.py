import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logger import logger
from app.modules.cnc.batch.repository import BatchRepository
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class RecoveryScanner:
    def __init__(self, sessions, quotes=None, *, interval: int = 5, human_timeout_seconds: int = 900):
        self.sessions = sessions
        self.quotes = quotes
        self.interval = interval
        self.human_timeout_seconds = human_timeout_seconds
        self.task: asyncio.Task | None = None
        self.stopping = False

    async def scan_expired_human_waits(self) -> int:
        async with self.sessions() as db, db.begin():
            now = utcnow()
            cutoff = now - timedelta(seconds=self.human_timeout_seconds)
            rows = (
                await db.scalars(
                    select(CncQuoteBatchItemModel)
                    .where(
                        CncQuoteBatchItemModel.exec_status == "WAITING_HUMAN",
                        CncQuoteBatchItemModel.updated_at < cutoff,
                    )
                    .with_for_update(skip_locked=True)
                )
            ).all()

            affected = 0
            affected_batches = set()
            for row in rows:
                row.error_code = "MANUAL_TIMEOUT"
                if row.run_id and row.claim_owner and row.claim_until and row.claim_until.replace(tzinfo=UTC) > now:
                    # Ask the live dispatcher to stop its owner before releasing it.
                    row.exec_status = "CANCELLING"
                    row.cancel_requested_at = row.cancel_requested_at or now
                elif row.run_id:
                    # A lost owner may have performed an unconfirmed mutation.
                    row.exec_status = "RECONCILING"
                    row.claim_until = None
                else:
                    row.exec_status = "FAILED"
                    row.finished_at = now
                    row.claim_owner = None
                    row.claim_until = None
                row.updated_at = now
                row.row_version += 1
                affected_batches.add(row.batch_id)
                affected += 1

            for batch_id in affected_batches:
                await BatchRepository.aggregate(db, batch_id)

            return affected

    async def scan_stale_reconciliations(self) -> int:
        if not self.quotes:
            return 0

        async with self.sessions() as db:
            rows = (
                await db.execute(
                    select(CncQuoteBatchItemModel.id, CncQuoteBatchItemModel.run_id).where(CncQuoteBatchItemModel.exec_status == "RECONCILING", CncQuoteBatchItemModel.run_id.is_not(None))
                )
            ).all()
        recovered = 0
        for item_id, run_id in rows:
            # The quote repository owns the item lock and atomic Run/result/item
            # settlement. Do not hold that lock across a second DB session.
            try:
                candidate = await self.quotes.persist_pending_result(run_id)
            except Exception:
                logger.warning("CNC reconciliation could not persist a staged result")
                continue
            if candidate:
                async with self.sessions() as db, db.begin():
                    row = await db.scalar(select(CncQuoteBatchItemModel).where(CncQuoteBatchItemModel.id == item_id).with_for_update())
                    if row and row.exec_status == "RECONCILING" and row.run_id == run_id:
                        row.exec_status = "COMPLETED"
                        row.claim_owner, row.claim_until = None, None
                        row.finished_at = row.updated_at = utcnow()
                        row.row_version += 1
                        await BatchRepository.aggregate(db, row.batch_id)
                recovered += 1
        return recovered

    async def tick(self):
        try:
            await self.scan_expired_human_waits()
            await self.scan_stale_reconciliations()
        except Exception:
            logger.warning("RecoveryScanner tick encountered an error", exc_info=True)

    async def start(self):
        if self.task is None:
            self.stopping = False
            self.task = asyncio.create_task(self._run(), name="cnc-recovery-scanner")

    async def stop(self):
        self.stopping = True
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None

    async def _run(self):
        while not self.stopping:
            await self.tick()
            await asyncio.sleep(self.interval)
