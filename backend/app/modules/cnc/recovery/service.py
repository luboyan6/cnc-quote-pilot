from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.modules.cnc.batch.repository import BatchRepository
from app.modules.cnc.browser.contracts import IntentState
from app.modules.cnc.cnc_quote.model import CncQuoteIntentModel
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel

from .contracts import (
    RecoveryAction,
    RecoveryDecision,
    RecoveryError,
    SideEffectState,
)
from .policy import classify_error


def utcnow() -> datetime:
    return datetime.now(UTC)


class RecoveryService:
    def __init__(self, sessions, batch_repository: BatchRepository | None = None):
        self.sessions = sessions
        self.batches = batch_repository or BatchRepository(sessions)

    async def record_failure(
        self,
        item_id: str,
        error: Exception | str,
        stage: str = "UNKNOWN",
        effect_state: SideEffectState = SideEffectState.NONE,
        cooldown_seconds: int = 0,
    ) -> RecoveryDecision:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(CncQuoteBatchItemModel).where(CncQuoteBatchItemModel.id == item_id).with_for_update())
            if row is None:
                raise RecoveryError("ITEM_NOT_FOUND", 404)

            now = utcnow()
            attempt = row.attempt_count + 1
            decision = classify_error(
                error=error,
                stage=stage,
                effect_state=effect_state,
                attempt_count=attempt,
                max_attempts=row.max_attempts,
                clock=lambda: now,
                cooldown_seconds=cooldown_seconds,
            )

            row.attempt_count = attempt
            row.error_code = decision.error_code
            row.updated_at = now
            row.row_version += 1

            if decision.action in (RecoveryAction.RETRY_WAIT, RecoveryAction.REAUTHENTICATE):
                row.exec_status = "RETRY_WAIT"
                row.next_attempt_at = decision.next_attempt_at
                row.claim_owner = None
                row.claim_until = None
            elif decision.action == RecoveryAction.WAITING_HUMAN:
                row.exec_status = "WAITING_HUMAN"
                row.claim_until = None
            elif decision.action == RecoveryAction.RECONCILING:
                row.exec_status = "RECONCILING"
                row.claim_until = None
            elif decision.action == RecoveryAction.RETRY_LOCAL_SAVE:
                # A remote observation already exists. Only the local recovery
                # scanner may persist it; never schedule another browser run.
                row.exec_status = "RECONCILING"
                row.next_attempt_at = None
                row.claim_until = None
            else:  # FAIL_TERMINAL
                row.exec_status = "FAILED"
                row.finished_at = now
                row.claim_owner = None
                row.claim_until = None

            await self.batches.aggregate(db, row.batch_id)
            return decision

    async def retry_item(self, actor_id: int, item_id: str, *, is_superuser: bool = False) -> dict[str, Any]:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(
                select(CncQuoteBatchItemModel)
                .join(CncQuoteBatchModel, CncQuoteBatchModel.id == CncQuoteBatchItemModel.batch_id)
                .where(CncQuoteBatchItemModel.id == item_id)
                .with_for_update(of=CncQuoteBatchItemModel)
            )
            if row is None:
                raise RecoveryError("ITEM_NOT_FOUND", 404)

            batch = await db.get(CncQuoteBatchModel, row.batch_id)
            if not is_superuser and batch.actor_id != actor_id:
                raise RecoveryError("ITEM_FORBIDDEN", 403)

            # State checks
            if row.exec_status == "COMPLETED":
                raise RecoveryError("CANNOT_RETRY_COMPLETED_ITEM", 400)
            if row.exec_status == "CANCELLED":
                raise RecoveryError("CANNOT_RETRY_CANCELLED_ITEM", 400)
            if row.exec_status in ("PENDING", "RUNNING", "CANCELLING", "WAITING_HUMAN"):
                raise RecoveryError("ITEM_CURRENTLY_ACTIVE", 400)
            if row.exec_status == "RECONCILING":
                raise RecoveryError("BATCH_UNCERTAIN_MUTATION_RETRY_FORBIDDEN", 400)
            if row.exec_status not in ("FAILED", "RETRY_WAIT") or row.cancel_requested_at or batch.cancel_requested_at or row.claim_owner:
                raise RecoveryError("ITEM_CURRENTLY_ACTIVE", 400)
            if row.run_id:
                uncertain = await db.scalar(
                    select(CncQuoteIntentModel.id).where(CncQuoteIntentModel.run_id == row.run_id, CncQuoteIntentModel.state.in_([IntentState.CLAIMED.value, IntentState.UNCERTAIN.value])).limit(1)
                )
                if uncertain:
                    raise RecoveryError("BATCH_UNCERTAIN_MUTATION_RETRY_FORBIDDEN", 400)

            # Budget check
            if row.attempt_count >= row.max_attempts and not is_superuser:
                raise RecoveryError("MAX_ATTEMPTS_EXCEEDED", 400)

            now = utcnow()
            row.exec_status = "PENDING"
            row.error_code = None
            row.next_attempt_at = now
            row.claim_owner = None
            row.claim_until = None
            row.run_id = None
            row.row_version += 1
            row.updated_at = now

            await self.batches.aggregate(db, row.batch_id)
            return {
                "id": row.id,
                "batch_id": row.batch_id,
                "exec_status": row.exec_status,
                "attempt_count": row.attempt_count,
                "max_attempts": row.max_attempts,
            }

    async def reconcile_item(self, actor_id: int, item_id: str, quotes=None, *, is_superuser: bool = False) -> dict[str, Any]:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(CncQuoteBatchItemModel).where(CncQuoteBatchItemModel.id == item_id).with_for_update())
            if row is None:
                raise RecoveryError("ITEM_NOT_FOUND", 404)

            batch = await db.get(CncQuoteBatchModel, row.batch_id)
            if not is_superuser and batch.actor_id != actor_id:
                raise RecoveryError("ITEM_FORBIDDEN", 403)

            if quotes and row.run_id:
                candidate = await quotes.persist_pending_result(row.run_id)
                if candidate:
                    row.exec_status = "COMPLETED"
                    row.claim_until = None
                    row.row_version += 1
                    row.finished_at = utcnow()
                    await self.batches.aggregate(db, row.batch_id)

            return {
                "id": row.id,
                "batch_id": row.batch_id,
                "exec_status": row.exec_status,
                "error_code": row.error_code,
            }
