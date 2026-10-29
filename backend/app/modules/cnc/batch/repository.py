"""Short independent transactions. No browser work holds a database lock."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, update

from app.modules.cnc.cnc_quote.model import CncQuoteRunModel
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel as Batch
from app.modules.cnc.cnc_quote_batch.model import CncQuoteCapacityModel as Capacity
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel as Item
from app.modules.cnc.quote.contracts import QuoteRunView

from .contracts import TERMINAL_ITEMS, BatchError, aggregate


def utcnow():
    return datetime.now(UTC)


def item_view(row):
    return {
        k: getattr(row, k)
        for k in (
            "id",
            "batch_id",
            "config_id",
            "account_id",
            "exec_status",
            "quote_kind",
            "run_id",
            "attempt_count",
            "max_attempts",
            "error_code",
            "next_attempt_at",
            "cancel_requested_at",
            "created_at",
            "started_at",
            "finished_at",
            "row_version",
        )
    } | {
        "requested": row.input_snapshot["requested"],
        "file_name": row.input_snapshot["file_name"],
    }


class BatchRepository:
    def __init__(self, sessions, capacity=1000):
        self.sessions, self.capacity = sessions, capacity

    @staticmethod
    async def visible(db, actor_id, batch_id, *, lock=False):
        stmt = select(Batch).where(Batch.id == batch_id, Batch.actor_id == actor_id)
        row = await db.scalar(stmt.with_for_update() if lock else stmt)
        if row is None:
            raise BatchError("BATCH_UNAVAILABLE", 404)
        return row

    async def find_request(self, actor_id, request_id, fingerprint):
        async with self.sessions() as db:
            row = await db.scalar(select(Batch).where(Batch.actor_id == actor_id, Batch.request_id == request_id))
            if row is None:
                return None
            if row.request_fingerprint != fingerprint:
                raise BatchError("BATCH_REQUEST_CONFLICT", 409)
            return row.id

    async def create(self, actor_id, request_id, fingerprint, snapshots):
        async with self.sessions() as db, db.begin():
            # An UPDATE takes an exclusive row lock on PG and a writer lock on
            # SQLite. All admissions serialize capacity and request arbitration.
            result = await db.execute(update(Capacity).where(Capacity.id == 1).values(version=Capacity.version + 1))
            if result.rowcount != 1:
                raise BatchError("BATCH_MIGRATION_REQUIRED", 503)
            prior = await db.scalar(select(Batch).where(Batch.actor_id == actor_id, Batch.request_id == request_id))
            if prior:
                if prior.request_fingerprint != fingerprint:
                    raise BatchError("BATCH_REQUEST_CONFLICT", 409)
                return prior.id
            count = await db.scalar(select(func.count()).select_from(Item).where(Item.exec_status.not_in(TERMINAL_ITEMS)))
            if count + len(snapshots) > self.capacity:
                raise BatchError("BATCH_QUEUE_FULL", 409)
            now, batch_id = utcnow(), str(uuid4())
            db.add(Batch(id=batch_id, actor_id=actor_id, source="manual", request_id=request_id, request_fingerprint=fingerprint, status="PENDING", created_at=now, updated_at=now))
            await db.flush()
            for frozen, fingerprint in snapshots:
                db.add(
                    Item(
                        id=str(uuid4()),
                        batch_id=batch_id,
                        config_id=frozen["config_id"],
                        account_id=frozen["account_id"],
                        input_snapshot=frozen,
                        input_fingerprint=fingerprint,
                        exec_status="PENDING",
                        attempt_count=0,
                        max_attempts=3,
                        claim_token=0,
                        row_version=0,
                        created_at=now,
                        updated_at=now,
                    )
                )
            return batch_id

    async def detail(self, actor_id, batch_id):
        async with self.sessions() as db:
            row = await self.visible(db, actor_id, batch_id)
            states = (await db.scalars(select(Item.exec_status).where(Item.batch_id == batch_id))).all()
            status, counts = aggregate(list(states))
            return {
                "id": row.id,
                "request_id": row.request_id,
                "source": row.source,
                "status": status,
                "counts": counts,
                "item_count": len(states),
                "cancel_requested_at": row.cancel_requested_at,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }

    async def list(self, actor_id, offset=0, limit=50):
        async with self.sessions() as db:
            ids = (await db.scalars(select(Batch.id).where(Batch.actor_id == actor_id).order_by(Batch.created_at.desc(), Batch.id).offset(offset).limit(limit))).all()
            total = await db.scalar(select(func.count()).select_from(Batch).where(Batch.actor_id == actor_id))
        return {"items": [await self.detail(actor_id, id) for id in ids], "total": total}

    async def items(self, actor_id, batch_id, offset=0, limit=100):
        async with self.sessions() as db:
            await self.visible(db, actor_id, batch_id)
            rows = (await db.scalars(select(Item).where(Item.batch_id == batch_id).order_by(Item.created_at, Item.id).offset(offset).limit(limit))).all()
            return [item_view(row) for row in rows]

    async def attempts(self, actor_id, item_id):
        async with self.sessions() as db:
            item = await db.get(Item, item_id)
            if item is None:
                raise BatchError("BATCH_ITEM_UNAVAILABLE", 404)
            await self.visible(db, actor_id, item.batch_id)
            runs = (await db.scalars(select(CncQuoteRunModel).where(CncQuoteRunModel.item_id == item_id).order_by(CncQuoteRunModel.attempt_no))).all()
            return [{"attempt_no": run.attempt_no, "run": QuoteRunView.model_validate(run.public_view).model_dump(mode="json")} for run in runs]

    async def cancel(self, actor_id, batch_id):
        async with self.sessions() as db, db.begin():
            # Completion takes Item then Batch; cancellation follows that order.
            batch = await self.visible(db, actor_id, batch_id)
            now = utcnow()
            rows = (await db.scalars(select(Item).where(Item.batch_id == batch_id).with_for_update())).all()
            if all(row.exec_status in TERMINAL_ITEMS for row in rows):
                return
            batch.cancel_requested_at = batch.cancel_requested_at or now
            for row in rows:
                if row.exec_status in TERMINAL_ITEMS:
                    continue
                row.cancel_requested_at = row.cancel_requested_at or now
                if row.run_id is None:
                    row.exec_status, row.finished_at = "CANCELLED", now
                    row.claim_owner, row.claim_until = None, None
                else:
                    row.exec_status = "CANCELLING"
                row.row_version += 1
                row.updated_at = now
            batch.status, batch.updated_at = aggregate([row.exec_status for row in rows])[0], now
            await self.aggregate(db, batch_id)

    async def claim(self, owner):
        async with self.sessions() as db, db.begin():
            now = utcnow()
            row = await db.scalar(
                select(Item)
                .where(
                    Item.exec_status.in_(["PENDING", "RETRY_WAIT"]), Item.cancel_requested_at.is_(None), Item.claim_owner.is_(None), (Item.next_attempt_at.is_(None) | (Item.next_attempt_at <= now))
                )
                .order_by(Item.created_at, Item.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if row is None:
                return None
            # Conditional update is also required on SQLite, which has no row lock.
            token, version = row.claim_token + 1, row.row_version + 1
            claimed = await db.execute(
                update(Item)
                .where(Item.id == row.id, Item.row_version == row.row_version, Item.claim_owner.is_(None), Item.cancel_requested_at.is_(None))
                .values(claim_owner=owner, claim_token=token, claim_until=now + timedelta(seconds=60), row_version=version)
            )
            if claimed.rowcount != 1:
                return None
            batch = await db.get(Batch, row.batch_id)
            return {
                "id": row.id,
                "batch_id": row.batch_id,
                "actor_id": batch.actor_id,
                "source": batch.source,
                "config_id": row.config_id,
                "account_id": row.account_id,
                "input_snapshot": row.input_snapshot,
                "owner": owner,
                "token": token,
                "attempt_no": row.attempt_count + 1,
            }

    async def release_wait(self, claim):
        async with self.sessions() as db, db.begin():
            # A lease can expire while PostgreSQL waits for this row's lock.
            # Read the current deadline under the lock before measuring time.
            deadline = await db.scalar(
                select(Item.claim_until)
                .where(Item.id == claim["id"], Item.claim_owner == claim["owner"], Item.claim_token == claim["token"], Item.run_id.is_(None), Item.cancel_requested_at.is_(None))
                .with_for_update()
            )
            if deadline is None or deadline.replace(tzinfo=UTC) <= utcnow():
                return
            await db.execute(
                update(Item)
                .where(
                    Item.id == claim["id"],
                    Item.claim_owner == claim["owner"],
                    Item.claim_token == claim["token"],
                    Item.claim_until > utcnow(),
                    Item.run_id.is_(None),
                    Item.cancel_requested_at.is_(None),
                )
                .values(claim_owner=None, claim_until=None, next_attempt_at=utcnow() + timedelta(seconds=2), row_version=Item.row_version + 1)
            )

    async def fail_claim(self, claim, reason):
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(Item).where(Item.id == claim["id"], Item.claim_owner == claim["owner"], Item.claim_token == claim["token"]).with_for_update())
            if row is None or row.exec_status in TERMINAL_ITEMS or row.claim_until is None or row.claim_until.replace(tzinfo=UTC) <= utcnow():
                return
            if row.run_id is not None:
                # A committed Run may already own a remote side effect. Never
                # settle the item independently of its Run/result transaction.
                row.exec_status = "RECONCILING"
                row.error_code = "BATCH_SHUTDOWN_UNSETTLED" if reason == "BATCH_SHUTDOWN_UNSETTLED" else "BATCH_RUN_REQUIRES_RECONCILIATION"
                row.claim_until = None
                row.row_version += 1
                await self.aggregate(db, row.batch_id)
                return
            if row.cancel_requested_at:
                row.exec_status = "CANCELLED"
                row.error_code, row.finished_at, row.updated_at = reason, utcnow(), utcnow()
                row.claim_owner, row.claim_until = None, None
            else:
                from app.modules.cnc.recovery.contracts import RecoveryAction, SideEffectState
                from app.modules.cnc.recovery.policy import classify_error

                now = utcnow()
                attempt = row.attempt_count + 1
                decision = classify_error(
                    error=reason,
                    stage="STARTING",
                    effect_state=SideEffectState.NONE,
                    attempt_count=attempt,
                    max_attempts=row.max_attempts,
                    reauth_count=int(row.error_code == "SESSION_EXPIRED_REAUTHENTICATING"),
                    clock=lambda: now,
                )
                row.attempt_count = attempt
                row.updated_at = now
                if decision.action in {RecoveryAction.RETRY_WAIT, RecoveryAction.REAUTHENTICATE}:
                    row.exec_status = "RETRY_WAIT"
                    row.error_code = decision.error_code
                    row.next_attempt_at = decision.next_attempt_at
                    row.claim_owner, row.claim_until = None, None
                elif decision.action == RecoveryAction.WAITING_HUMAN:
                    row.exec_status = "WAITING_HUMAN"
                    row.error_code = decision.error_code
                    row.claim_owner, row.claim_until = None, None
                elif decision.action == RecoveryAction.RECONCILING:
                    row.exec_status = "RECONCILING"
                    row.error_code = decision.error_code
                    row.claim_until = None
                else:
                    row.exec_status = "FAILED"
                    row.error_code = reason
                    row.finished_at = now
                    row.claim_owner, row.claim_until = None, None
            row.row_version += 1
            await self.aggregate(db, row.batch_id)

    async def owns_cancellation(self, claim):
        """Authorize only this dispatcher's persisted, still-live cancel claim."""
        async with self.sessions() as db, db.begin():
            deadline = await db.scalar(
                select(Item.claim_until)
                .join(Batch, Batch.id == Item.batch_id)
                .join(CncQuoteRunModel, CncQuoteRunModel.run_id == Item.run_id)
                .where(
                    Item.id == claim["id"],
                    Item.run_id == claim["run_id"],
                    Item.config_id == claim["config_id"],
                    Item.claim_owner == claim["owner"],
                    Item.claim_token == claim["token"],
                    Item.exec_status == "CANCELLING",
                    Item.cancel_requested_at.is_not(None),
                    Batch.actor_id == claim["actor_id"],
                    CncQuoteRunModel.item_id == Item.id,
                    CncQuoteRunModel.config_id == Item.config_id,
                    CncQuoteRunModel.actor_id == Batch.actor_id,
                    CncQuoteRunModel.item_claim_owner == Item.claim_owner,
                    CncQuoteRunModel.item_claim_token == Item.claim_token,
                )
                .with_for_update(of=Item)
            )
            return deadline is not None and deadline.replace(tzinfo=UTC) > utcnow()

    @staticmethod
    async def aggregate(db, batch_id):
        await db.flush()
        states = (await db.scalars(select(Item.exec_status).where(Item.batch_id == batch_id))).all()
        status, _ = aggregate(list(states))
        now = utcnow()
        await db.execute(update(Batch).where(Batch.id == batch_id).values(status=status, updated_at=now))
        if status in {"COMPLETED", "PARTIAL_FAILED", "FAILED", "CANCELLED"}:
            source = await db.scalar(select(Batch.source).where(Batch.id == batch_id))
            if source == "schedule":
                from app.modules.cnc.cnc_quote_schedule_round.model import CncQuoteScheduleRoundModel

                await db.execute(
                    update(CncQuoteScheduleRoundModel).where(CncQuoteScheduleRoundModel.batch_id == batch_id, CncQuoteScheduleRoundModel.status == "RUNNING").values(status=status, finished_at=now)
                )

    async def active(self, owner):
        async with self.sessions() as db, db.begin():
            now = utcnow()
            rows = (await db.scalars(select(Item).where(Item.claim_owner == owner, Item.claim_until > now, Item.exec_status.not_in(TERMINAL_ITEMS)).with_for_update())).all()
            active = []
            for row in rows:
                # A row can expire while its lock is being acquired. Check the
                # fence again in the actual UPDATE instead of reviving it.
                now = utcnow()
                renewed = await db.execute(
                    update(Item)
                    .where(Item.id == row.id, Item.claim_owner == owner, Item.claim_token == row.claim_token, Item.claim_until > now, Item.exec_status.not_in(TERMINAL_ITEMS))
                    .values(claim_until=now + timedelta(seconds=60))
                    .returning(Item.id)
                    .execution_options(synchronize_session=False)
                )
                if renewed.scalar_one_or_none() is not None:
                    active.append(
                        {
                            "id": row.id,
                            "run_id": row.run_id,
                            "config_id": row.config_id,
                            "actor_id": (await db.get(Batch, row.batch_id)).actor_id,
                            "cancel": row.cancel_requested_at is not None,
                            "owner": owner,
                            "token": row.claim_token,
                        }
                    )
            return active

    async def settle_expired_claims(self):
        """Never replay a lost browser's side effects. T2 owns reconciliation."""
        async with self.sessions() as db, db.begin():
            now = utcnow()
            rows = (await db.scalars(select(Item).where(Item.claim_until < now, Item.exec_status.not_in(TERMINAL_ITEMS)).with_for_update(skip_locked=True))).all()
            for row in rows:
                if row.run_id is None:
                    row.claim_owner, row.claim_until = None, None
                else:
                    row.exec_status, row.error_code = "RECONCILING", "BATCH_OWNER_LOST_NO_RETRY"
                    row.claim_until = None
                row.row_version += 1
                await self.aggregate(db, row.batch_id)

    async def retry_item(self, actor_id, item_id):
        from app.modules.cnc.recovery.service import RecoveryService

        service = RecoveryService(self.sessions, self)
        return await service.retry_item(actor_id, item_id)

    async def reconcile_item(self, actor_id, item_id, quotes=None):
        from app.modules.cnc.recovery.service import RecoveryService

        service = RecoveryService(self.sessions, self)
        return await service.reconcile_item(actor_id, item_id, quotes=quotes)
