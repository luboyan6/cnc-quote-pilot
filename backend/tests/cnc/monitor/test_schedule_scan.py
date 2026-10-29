import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel, CncQuoteCapacityModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
from app.modules.cnc.cnc_quote_schedule.model import CncQuoteScheduleModel
from app.modules.cnc.cnc_quote_schedule_round.model import CncQuoteScheduleRoundModel
from app.modules.cnc.monitor.contracts import ScheduleCreate, ScheduleTarget, ensure_utc
from app.modules.cnc.monitor.repository import ScheduleRepository
from tests.cnc.quote._quote_support import Base, QuoteDatabase, copy_table


class Batch(Base):
    __table__ = copy_table(CncQuoteBatchModel.__table__)


class Capacity(Base):
    __table__ = copy_table(CncQuoteCapacityModel.__table__)


class Item(Base):
    __table__ = copy_table(CncQuoteBatchItemModel.__table__)


class Schedule(Base):
    __table__ = copy_table(CncQuoteScheduleModel.__table__)


class Round(Base):
    __table__ = copy_table(CncQuoteScheduleRoundModel.__table__)


class ScheduleScanTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = QuoteDatabase()
        await self.db.asyncSetUp()
        self.sessions = self.db.sessions
        self.repo = ScheduleRepository(self.sessions, capacity_limit=10)
        async with self.sessions() as db, db.begin():
            db.add(Capacity(id=1, version=0))

    async def asyncTearDown(self):
        await self.db.asyncTearDown()

    async def test_scan_due_admittance_creates_batch_items_and_round(self):
        actor_id = 1
        now = datetime.now(UTC)
        create_data = ScheduleCreate(
            name="Scan Test",
            interval_minutes=15,
            targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[5])],
        )
        snapshot = {"items": [{"config_id": 1, "account_id": 2, "file_name": "part.step", "requested": {"quantity": "5"}}]}
        sched_id = await self.repo.create(actor_id, create_data, snapshot)

        # Force next_run_at to now so it is due
        async with self.sessions() as db, db.begin():
            row = await db.get(Schedule, sched_id)
            row.next_run_at = now - timedelta(seconds=10)

        results = await self.repo.scan_due(clock_now=now)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "RUNNING")
        self.assertEqual(results[0]["round_no"], 1)
        batch_id = results[0]["batch_id"]

        # Verify batch and items in DB
        async with self.sessions() as db:
            batch = await db.get(Batch, batch_id)
            self.assertIsNotNone(batch)
            self.assertEqual(batch.source, "schedule")

            items = (await db.scalars(select(Item).where(Item.batch_id == batch_id))).all()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].config_id, 1)

            sched = await db.get(Schedule, sched_id)
            self.assertGreater(ensure_utc(sched.next_run_at), now)

    async def test_scan_due_overlap_skipped_when_previous_round_running(self):
        actor_id = 1
        now = datetime.now(UTC)
        create_data = ScheduleCreate(
            name="Overlap Test",
            interval_minutes=15,
            targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[1])],
        )
        sched_id = await self.repo.create(actor_id, create_data, {"items": []})

        # Add an active RUNNING round
        async with self.sessions() as db, db.begin():
            sched = await db.get(Schedule, sched_id)
            sched.next_run_at = now - timedelta(seconds=5)
            r = Round(
                id=str(uuid4()),
                schedule_id=sched_id,
                round_no=1,
                scheduled_for=now - timedelta(minutes=15),
                status="RUNNING",
                schedule_revision=1,
                created_at=now,
            )
            db.add(r)

        results = await self.repo.scan_due(clock_now=now)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "SKIPPED_OVERLAP")

        async with self.sessions() as db:
            rounds = (await db.scalars(select(Round).where(Round.schedule_id == sched_id).order_by(Round.round_no))).all()
            self.assertEqual(len(rounds), 2)
            self.assertEqual(rounds[1].status, "SKIPPED_OVERLAP")
            self.assertEqual(rounds[1].skip_reason, "PREVIOUS_ROUND_RUNNING")

    async def test_scan_due_missed_slot_during_extended_downtime(self):
        actor_id = 1
        now = datetime.now(UTC)
        create_data = ScheduleCreate(
            name="Missed Slot Test",
            interval_minutes=15,
            targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[1])],
        )
        sched_id = await self.repo.create(actor_id, create_data, {"items": []})

        # Slot was due 120 seconds ago (> 60s grace period)
        async with self.sessions() as db, db.begin():
            sched = await db.get(Schedule, sched_id)
            sched.next_run_at = now - timedelta(seconds=120)

        results = await self.repo.scan_due(clock_now=now, grace_period_seconds=60)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "MISSED")

        async with self.sessions() as db:
            rounds = (await db.scalars(select(Round).where(Round.schedule_id == sched_id))).all()
            self.assertEqual(len(rounds), 1)
            self.assertEqual(rounds[0].status, "MISSED")
            self.assertEqual(rounds[0].skip_reason, "MISSED_SLOT_DOWNTIME")

    async def test_scan_due_capacity_wait_when_queue_full(self):
        actor_id = 1
        now = datetime.now(UTC)
        repo_limited = ScheduleRepository(self.sessions, capacity_limit=2)
        create_data = ScheduleCreate(
            name="Capacity Limit Test",
            interval_minutes=15,
            targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[1, 2, 3])],
        )
        snapshot = {
            "items": [
                {"config_id": 1, "account_id": 2, "requested": {"quantity": "1"}},
                {"config_id": 1, "account_id": 2, "requested": {"quantity": "2"}},
                {"config_id": 1, "account_id": 2, "requested": {"quantity": "3"}},
            ]
        }
        sched_id = await repo_limited.create(actor_id, create_data, snapshot)

        async with self.sessions() as db, db.begin():
            sched = await db.get(Schedule, sched_id)
            sched.next_run_at = now - timedelta(seconds=10)

        results = await repo_limited.scan_due(clock_now=now)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "CAPACITY_WAIT")

        async with self.sessions() as db:
            rounds = (await db.scalars(select(Round).where(Round.schedule_id == sched_id))).all()
            self.assertEqual(len(rounds), 1)
            self.assertEqual(rounds[0].status, "CAPACITY_WAIT")
            self.assertEqual(rounds[0].skip_reason, "BATCH_CAPACITY_EXCEEDED")

        # A later scan may admit the original slot after capacity becomes free.
        repo_limited.capacity_limit = 4
        recovered = await repo_limited.scan_due(clock_now=now + timedelta(minutes=20))
        self.assertEqual(recovered[0]["status"], "RUNNING")
        async with self.sessions() as db:
            rounds = (await db.scalars(select(Round).where(Round.schedule_id == sched_id))).all()
            self.assertEqual(len(rounds), 1)
            self.assertEqual(rounds[0].round_no, 1)
            self.assertEqual(ensure_utc(rounds[0].scheduled_for), now - timedelta(seconds=10))

    async def test_completed_previous_batch_allows_next_round(self):
        now = datetime.now(UTC)
        data = ScheduleCreate(name="repeat", interval_minutes=15, targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[1])])
        snapshot = {"items": [{"config_id": 1, "account_id": 2, "requested": {"quantity": "1"}}]}
        schedule_id = await self.repo.create(1, data, snapshot)
        async with self.sessions() as db, db.begin():
            sched = await db.get(Schedule, schedule_id)
            sched.next_run_at = now
        first = (await self.repo.scan_due(clock_now=now))[0]
        async with self.sessions() as db, db.begin():
            batch = await db.get(Batch, first["batch_id"])
            batch.status = "COMPLETED"
            item = await db.scalar(select(Item).where(Item.batch_id == batch.id))
            item.exec_status = "COMPLETED"
            sched = await db.get(Schedule, schedule_id)
            sched.next_run_at = now + timedelta(minutes=15)
        second = (await self.repo.scan_due(clock_now=now + timedelta(minutes=15)))[0]
        self.assertEqual(second["status"], "RUNNING")
        async with self.sessions() as db:
            rounds = (await db.scalars(select(Round).where(Round.schedule_id == schedule_id).order_by(Round.round_no))).all()
            self.assertEqual([r.status for r in rounds], ["COMPLETED", "RUNNING"])

    async def test_duplicate_frozen_targets_are_admitted_once(self):
        now = datetime.now(UTC)
        data = ScheduleCreate(name="duplicates", interval_minutes=15, targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[1, 1])])
        item = {"config_id": 1, "account_id": 2, "requested": {"quantity": "1"}}
        schedule_id = await self.repo.create(1, data, {"items": [item, item]})
        async with self.sessions() as db, db.begin():
            sched = await db.get(Schedule, schedule_id)
            sched.next_run_at = now
        batch_id = (await self.repo.scan_due(clock_now=now))[0]["batch_id"]
        async with self.sessions() as db:
            items = (await db.scalars(select(Item).where(Item.batch_id == batch_id))).all()
            self.assertEqual(len(items), 1)

    async def test_stale_validation_does_not_admit_a_changed_schedule(self):
        now = datetime.now(UTC)
        data = ScheduleCreate(name="stale", interval_minutes=15, targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[1])])
        schedule_id = await self.repo.create(1, data, {"items": [{"config_id": 1, "account_id": 2, "requested": {"quantity": "1"}}]})
        async with self.sessions() as db, db.begin():
            sched = await db.get(Schedule, schedule_id)
            sched.next_run_at = now
            sched.revision = 2
        results = await self.repo.scan_due(clock_now=now, validated={schedule_id: (1, now)})
        self.assertEqual(results, [])
        async with self.sessions() as db:
            self.assertEqual((await db.scalars(select(Round))).all(), [])

    async def test_batch_terminal_state_immediately_settles_round(self):
        from app.modules.cnc.batch.repository import BatchRepository

        now = datetime.now(UTC)
        data = ScheduleCreate(name="settle", interval_minutes=15, targets=[ScheduleTarget(config_id=1, account_id=2, quantities=[1])])
        schedule_id = await self.repo.create(1, data, {"items": [{"config_id": 1, "account_id": 2, "requested": {"quantity": "1"}}]})
        async with self.sessions() as db, db.begin():
            sched = await db.get(Schedule, schedule_id)
            sched.next_run_at = now
        batch_id = (await self.repo.scan_due(clock_now=now))[0]["batch_id"]
        async with self.sessions() as db, db.begin():
            item = await db.scalar(select(Item).where(Item.batch_id == batch_id))
            item.exec_status = "COMPLETED"
            await BatchRepository.aggregate(db, batch_id)
        async with self.sessions() as db:
            round_row = await db.scalar(select(Round).where(Round.batch_id == batch_id))
            self.assertEqual(round_row.status, "COMPLETED")
            self.assertIsNotNone(round_row.finished_at)


if __name__ == "__main__":
    unittest.main()
