from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, update

from app.modules.cnc.batch.contracts import TERMINAL_ITEMS, digest
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel, CncQuoteCapacityModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
from app.modules.cnc.cnc_quote_schedule.model import CncQuoteScheduleModel
from app.modules.cnc.cnc_quote_schedule_round.model import CncQuoteScheduleRoundModel

from .contracts import (
    ScheduleCreate,
    ScheduleError,
    ScheduleUpdate,
    compute_next_slot,
    ensure_utc,
    target_fingerprint,
    utcnow,
)


class ScheduleRepository:
    def __init__(self, sessions, capacity_limit: int = 1000):
        self.sessions = sessions
        self.capacity_limit = capacity_limit

    async def create(self, actor_id: int, data: ScheduleCreate, target_snapshot: dict) -> str:
        async with self.sessions() as db, db.begin():
            now = utcnow()
            fp = target_fingerprint(data.targets)
            schedule_id = str(uuid4())
            next_run = compute_next_slot(now, data.interval_minutes, now)

            row = CncQuoteScheduleModel(
                id=schedule_id,
                actor_id=actor_id,
                name=data.name,
                interval_minutes=data.interval_minutes,
                timezone=data.timezone,
                anchor_time=now,
                next_run_at=next_run,
                status="ENABLED",
                target_snapshot=target_snapshot,
                target_fingerprint=fp,
                revision=1,
                last_round_at=None,
                pause_reason=None,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            return schedule_id

    async def update(self, actor_id: int, schedule_id: str, data: ScheduleUpdate, target_snapshot: dict | None = None) -> dict[str, Any]:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(CncQuoteScheduleModel).where(CncQuoteScheduleModel.id == schedule_id).with_for_update())
            if row is None:
                raise ScheduleError("SCHEDULE_NOT_FOUND", 404)
            if row.actor_id != actor_id:
                raise ScheduleError("SCHEDULE_FORBIDDEN", 403)

            now = utcnow()
            if data.targets is not None or data.interval_minutes is not None:
                await self._clear_capacity_wait(db, row.id, now)
            if data.name is not None:
                row.name = data.name
            if data.timezone is not None:
                row.timezone = data.timezone
            if data.interval_minutes is not None:
                row.interval_minutes = data.interval_minutes
                if row.status == "ENABLED":
                    row.next_run_at = compute_next_slot(row.anchor_time, row.interval_minutes, now)
            if target_snapshot is not None and data.targets is not None:
                row.target_snapshot = target_snapshot
                row.target_fingerprint = target_fingerprint(data.targets)
                row.revision += 1
                if row.status == "ENABLED":
                    row.next_run_at = compute_next_slot(row.anchor_time, row.interval_minutes, now)

            row.updated_at = now
            return self._format_schedule(row)

    async def pause(self, actor_id: int, schedule_id: str, reason: str = "USER_PAUSED") -> dict[str, Any]:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(CncQuoteScheduleModel).where(CncQuoteScheduleModel.id == schedule_id).with_for_update())
            if row is None:
                raise ScheduleError("SCHEDULE_NOT_FOUND", 404)
            if row.actor_id != actor_id:
                raise ScheduleError("SCHEDULE_FORBIDDEN", 403)

            row.status = "PAUSED"
            row.pause_reason = reason
            row.updated_at = utcnow()
            await self._clear_capacity_wait(db, row.id, row.updated_at)
            return self._format_schedule(row)

    @staticmethod
    async def _clear_capacity_wait(db, schedule_id: str, now: datetime) -> None:
        await db.execute(
            update(CncQuoteScheduleRoundModel)
            .where(CncQuoteScheduleRoundModel.schedule_id == schedule_id, CncQuoteScheduleRoundModel.status == "CAPACITY_WAIT")
            .values(status="MISSED", skip_reason="SCHEDULE_CHANGED", finished_at=now)
        )

    async def resume(self, actor_id: int, schedule_id: str) -> dict[str, Any]:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(CncQuoteScheduleModel).where(CncQuoteScheduleModel.id == schedule_id).with_for_update())
            if row is None:
                raise ScheduleError("SCHEDULE_NOT_FOUND", 404)
            if row.actor_id != actor_id:
                raise ScheduleError("SCHEDULE_FORBIDDEN", 403)

            now = utcnow()
            row.status = "ENABLED"
            row.pause_reason = None
            row.next_run_at = compute_next_slot(row.anchor_time, row.interval_minutes, now)
            row.updated_at = now
            return self._format_schedule(row)

    async def detail(self, actor_id: int, schedule_id: str) -> dict[str, Any]:
        async with self.sessions() as db:
            row = await db.get(CncQuoteScheduleModel, schedule_id)
            if row is None:
                raise ScheduleError("SCHEDULE_NOT_FOUND", 404)
            if row.actor_id != actor_id:
                raise ScheduleError("SCHEDULE_FORBIDDEN", 403)
            return self._format_schedule(row)

    async def list(self, actor_id: int, offset: int = 0, limit: int = 50) -> dict[str, Any]:
        async with self.sessions() as db:
            query = select(CncQuoteScheduleModel).where(CncQuoteScheduleModel.actor_id == actor_id)
            total = await db.scalar(select(func.count()).select_from(query.subquery()))
            rows = (await db.scalars(query.order_by(CncQuoteScheduleModel.created_at.desc()).offset(offset).limit(limit))).all()
            return {"total": total or 0, "items": [self._format_schedule(r) for r in rows]}

    async def rounds(self, actor_id: int, schedule_id: str, offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        async with self.sessions() as db:
            sched = await db.get(CncQuoteScheduleModel, schedule_id)
            if sched is None:
                raise ScheduleError("SCHEDULE_NOT_FOUND", 404)
            if sched.actor_id != actor_id:
                raise ScheduleError("SCHEDULE_FORBIDDEN", 403)

            query = select(CncQuoteScheduleRoundModel).where(CncQuoteScheduleRoundModel.schedule_id == schedule_id).order_by(CncQuoteScheduleRoundModel.round_no.desc()).offset(offset).limit(limit)
            rows = (await db.scalars(query)).all()
            return [self._format_round(r) for r in rows]

    async def due(self, clock_now: datetime | None = None) -> list[dict[str, Any]]:
        async with self.sessions() as db:
            rows = (await db.scalars(select(CncQuoteScheduleModel).where(CncQuoteScheduleModel.status == "ENABLED", CncQuoteScheduleModel.next_run_at <= ensure_utc(clock_now or utcnow())))).all()
            return [{"id": row.id, "actor_id": row.actor_id, "revision": row.revision, "next_run_at": row.next_run_at, "target_snapshot": row.target_snapshot} for row in rows]

    async def pause_invalid(self, schedule_id: str, revision: int, slot: datetime) -> None:
        async with self.sessions() as db, db.begin():
            row = await db.scalar(select(CncQuoteScheduleModel).where(CncQuoteScheduleModel.id == schedule_id).with_for_update())
            if row and row.status == "ENABLED" and row.revision == revision and ensure_utc(row.next_run_at) == ensure_utc(slot):
                row.status, row.pause_reason, row.updated_at = "PAUSED", "SCHEDULE_INPUT_OR_PERMISSION_CHANGED", utcnow()
                await self._clear_capacity_wait(db, row.id, row.updated_at)

    async def scan_due(self, clock_now: datetime | None = None, grace_period_seconds: int = 60, *, validated: dict | None = None) -> list[dict[str, Any]]:
        now = ensure_utc(clock_now or utcnow())
        results = []
        async with self.sessions() as db, db.begin():
            # Lock due schedules
            schedules = (
                await db.scalars(
                    select(CncQuoteScheduleModel)
                    .where(
                        CncQuoteScheduleModel.status == "ENABLED",
                        CncQuoteScheduleModel.next_run_at <= now,
                    )
                    .order_by(CncQuoteScheduleModel.next_run_at, CncQuoteScheduleModel.id)
                    .with_for_update(skip_locked=True)
                )
            ).all()

            for sched in schedules:
                slot = ensure_utc(sched.next_run_at)
                if validated is not None:
                    checked = validated.get(sched.id)
                    if checked is None or checked[0] != sched.revision or ensure_utc(checked[1]) != slot:
                        continue
                latest_round_no = (await db.scalar(select(func.max(CncQuoteScheduleRoundModel.round_no)).where(CncQuoteScheduleRoundModel.schedule_id == sched.id))) or 0
                next_round_no = latest_round_no + 1

                # 1. Overlap Check: any previous active round?
                active_round = await db.scalar(
                    select(CncQuoteScheduleRoundModel)
                    .where(
                        CncQuoteScheduleRoundModel.schedule_id == sched.id,
                        CncQuoteScheduleRoundModel.status == "RUNNING",
                    )
                    .limit(1)
                )
                if active_round is not None:
                    previous_batch = await db.get(CncQuoteBatchModel, active_round.batch_id) if active_round.batch_id else None
                    if previous_batch and previous_batch.status in {"COMPLETED", "PARTIAL_FAILED", "FAILED", "CANCELLED"}:
                        active_round.status = previous_batch.status
                        active_round.finished_at = previous_batch.updated_at
                        active_round = None
                if active_round is not None:
                    round_id = str(uuid4())
                    r = CncQuoteScheduleRoundModel(
                        id=round_id,
                        schedule_id=sched.id,
                        round_no=next_round_no,
                        scheduled_for=slot,
                        status="SKIPPED_OVERLAP",
                        batch_id=None,
                        schedule_revision=sched.revision,
                        skip_reason="PREVIOUS_ROUND_RUNNING",
                        created_at=now,
                        finished_at=now,
                    )
                    db.add(r)
                    sched.next_run_at = compute_next_slot(sched.anchor_time, sched.interval_minutes, now)
                    results.append({"schedule_id": sched.id, "status": "SKIPPED_OVERLAP", "round_no": next_round_no})
                    continue

                # 2. Missed Slot Check: downtime exceeding grace period
                waiting = await db.scalar(
                    select(CncQuoteScheduleRoundModel)
                    .where(CncQuoteScheduleRoundModel.schedule_id == sched.id, CncQuoteScheduleRoundModel.scheduled_for == slot, CncQuoteScheduleRoundModel.status == "CAPACITY_WAIT")
                    .with_for_update()
                )
                if waiting is not None:
                    next_round_no = waiting.round_no
                if waiting is None and (now - slot).total_seconds() > grace_period_seconds:
                    round_id = str(uuid4())
                    r = CncQuoteScheduleRoundModel(
                        id=round_id,
                        schedule_id=sched.id,
                        round_no=next_round_no,
                        scheduled_for=slot,
                        status="MISSED",
                        batch_id=None,
                        schedule_revision=sched.revision,
                        skip_reason="MISSED_SLOT_DOWNTIME",
                        created_at=now,
                        finished_at=now,
                    )
                    db.add(r)
                    sched.next_run_at = compute_next_slot(sched.anchor_time, sched.interval_minutes, now)
                    results.append({"schedule_id": sched.id, "status": "MISSED", "round_no": next_round_no})
                    continue

                # 3. Capacity Check
                capacity = await db.execute(update(CncQuoteCapacityModel).where(CncQuoteCapacityModel.id == 1).values(version=CncQuoteCapacityModel.version + 1))
                if capacity.rowcount != 1:
                    raise ScheduleError("BATCH_MIGRATION_REQUIRED", 503)
                active_items = await db.scalar(select(func.count(CncQuoteBatchItemModel.id)).where(CncQuoteBatchItemModel.exec_status.not_in(TERMINAL_ITEMS))) or 0
                snapshots = list({digest(item): item for item in sched.target_snapshot.get("items", [])}.values())
                if active_items + len(snapshots) > self.capacity_limit:
                    r = waiting or CncQuoteScheduleRoundModel(
                        id=str(uuid4()),
                        schedule_id=sched.id,
                        round_no=next_round_no,
                        scheduled_for=slot,
                        status="CAPACITY_WAIT",
                        batch_id=None,
                        schedule_revision=sched.revision,
                        skip_reason="BATCH_CAPACITY_EXCEEDED",
                        created_at=now,
                        finished_at=None,
                    )
                    if waiting is None:
                        db.add(r)
                    results.append({"schedule_id": sched.id, "status": "CAPACITY_WAIT", "round_no": next_round_no})
                    continue

                # 4. Valid Admittance: Create Batch + Items + Round in same transaction
                batch_id = str(uuid4())
                batch = CncQuoteBatchModel(
                    id=batch_id,
                    actor_id=sched.actor_id,
                    source="schedule",
                    request_id=f"sched-{sched.id[:8]}-r{next_round_no}",
                    request_fingerprint=sched.target_fingerprint,
                    status="PENDING",
                    created_at=now,
                    updated_at=now,
                )
                db.add(batch)

                for item_data in snapshots:
                    item_id = str(uuid4())
                    item = CncQuoteBatchItemModel(
                        id=item_id,
                        batch_id=batch_id,
                        config_id=item_data["config_id"],
                        account_id=item_data["account_id"],
                        input_snapshot=item_data,
                        input_fingerprint=digest(item_data),
                        exec_status="PENDING",
                        row_version=0,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(item)

                r = waiting or CncQuoteScheduleRoundModel(
                    id=str(uuid4()),
                    schedule_id=sched.id,
                    round_no=next_round_no,
                    scheduled_for=slot,
                    status="RUNNING",
                    batch_id=batch_id,
                    schedule_revision=sched.revision,
                    skip_reason=None,
                    created_at=now,
                    finished_at=None,
                )
                if waiting is None:
                    db.add(r)
                else:
                    r.status, r.batch_id, r.skip_reason = "RUNNING", batch_id, None

                sched.last_round_at = now
                sched.next_run_at = compute_next_slot(sched.anchor_time, sched.interval_minutes, now)
                if sched.next_run_at <= now:
                    sched.next_run_at += timedelta(minutes=sched.interval_minutes)
                results.append({"schedule_id": sched.id, "status": "RUNNING", "round_no": next_round_no, "batch_id": batch_id})

        return results

    @staticmethod
    def _format_schedule(row: CncQuoteScheduleModel) -> dict[str, Any]:
        return {
            "id": row.id,
            "actor_id": row.actor_id,
            "name": row.name,
            "interval_minutes": row.interval_minutes,
            "timezone": row.timezone,
            "anchor_time": row.anchor_time.isoformat() if row.anchor_time else None,
            "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
            "status": row.status,
            "revision": row.revision,
            "last_round_at": row.last_round_at.isoformat() if row.last_round_at else None,
            "pause_reason": row.pause_reason,
            "target_snapshot": row.target_snapshot,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _format_round(row: CncQuoteScheduleRoundModel) -> dict[str, Any]:
        return {
            "id": row.id,
            "schedule_id": row.schedule_id,
            "round_no": row.round_no,
            "scheduled_for": row.scheduled_for.isoformat() if row.scheduled_for else None,
            "status": row.status,
            "batch_id": row.batch_id,
            "schedule_revision": row.schedule_revision,
            "skip_reason": row.skip_reason,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        }
