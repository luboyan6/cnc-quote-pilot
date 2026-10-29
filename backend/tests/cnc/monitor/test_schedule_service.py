import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel, CncQuoteCapacityModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
from app.modules.cnc.cnc_quote_schedule.model import CncQuoteScheduleModel
from app.modules.cnc.cnc_quote_schedule_round.model import CncQuoteScheduleRoundModel
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.monitor.contracts import (
    ScheduleCreate,
    ScheduleError,
    ScheduleTarget,
    ScheduleUpdate,
    compute_next_slot,
)
from app.modules.cnc.monitor.repository import ScheduleRepository
from app.modules.cnc.monitor.service import MonitorService
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


class ScheduleServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = QuoteDatabase()
        await self.db.asyncSetUp()
        self.sessions = self.db.sessions
        self.repo = ScheduleRepository(self.sessions)
        self.quotes_mock = AsyncMock()
        self.service = MonitorService(quote_repository=self.quotes_mock, repository=self.repo)

    async def asyncTearDown(self):
        await self.db.asyncTearDown()

    def test_compute_next_slot(self):
        anchor = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)
        # Exactly on anchor -> next is anchor
        self.assertEqual(compute_next_slot(anchor, 15, anchor), anchor)
        # 5 mins past anchor -> next slot is anchor + 15m
        now1 = anchor + timedelta(minutes=5)
        self.assertEqual(compute_next_slot(anchor, 15, now1), anchor + timedelta(minutes=15))
        # 20 mins past anchor -> next slot is anchor + 30m
        now2 = anchor + timedelta(minutes=20)
        self.assertEqual(compute_next_slot(anchor, 15, now2), anchor + timedelta(minutes=30))

    async def test_create_and_detail_schedule(self):
        actor_id = 1
        create_data = ScheduleCreate(
            name="Daily Quote",
            interval_minutes=60,
            timezone="Asia/Shanghai",
            targets=[ScheduleTarget(config_id=1, account_id=10, quantities=[5, 10])],
        )
        fake_snapshot = {
            "items": [
                {"config_id": 1, "account_id": 10, "requested": {"quantity": "5"}},
                {"config_id": 1, "account_id": 10, "requested": {"quantity": "10"}},
            ]
        }
        sched_id = await self.repo.create(actor_id, create_data, fake_snapshot)
        detail = await self.repo.detail(actor_id, sched_id)
        self.assertEqual(detail["name"], "Daily Quote")
        self.assertEqual(detail["interval_minutes"], 60)
        self.assertEqual(detail["status"], "ENABLED")
        self.assertEqual(detail["revision"], 1)

    async def test_update_schedule_revision_and_slot(self):
        actor_id = 1
        create_data = ScheduleCreate(
            name="Initial Name",
            interval_minutes=30,
            targets=[ScheduleTarget(config_id=1, account_id=10, quantities=[1])],
        )
        sched_id = await self.repo.create(actor_id, create_data, {"items": []})

        update_data = ScheduleUpdate(
            name="Updated Name",
            interval_minutes=15,
            targets=[ScheduleTarget(config_id=1, account_id=10, quantities=[2])],
        )
        updated = await self.repo.update(actor_id, sched_id, update_data, target_snapshot={"items": [{"qty": 2}]})
        self.assertEqual(updated["name"], "Updated Name")
        self.assertEqual(updated["interval_minutes"], 15)
        self.assertEqual(updated["revision"], 2)

    async def test_pause_and_resume_schedule(self):
        actor_id = 1
        create_data = ScheduleCreate(
            name="Toggle Schedule",
            interval_minutes=60,
            targets=[ScheduleTarget(config_id=1, account_id=10, quantities=[1])],
        )
        sched_id = await self.repo.create(actor_id, create_data, {"items": []})

        # Pause
        paused = await self.repo.pause(actor_id, sched_id, reason="MAINTENANCE")
        self.assertEqual(paused["status"], "PAUSED")
        self.assertEqual(paused["pause_reason"], "MAINTENANCE")

        # Resume
        resumed = await self.repo.resume(actor_id, sched_id)
        self.assertEqual(resumed["status"], "ENABLED")
        self.assertIsNone(resumed["pause_reason"])
        self.assertIsNotNone(resumed["next_run_at"])

    async def test_detail_and_update_forbidden_for_other_actor(self):
        create_data = ScheduleCreate(
            name="Private Schedule",
            interval_minutes=60,
            targets=[ScheduleTarget(config_id=1, account_id=10, quantities=[1])],
        )
        sched_id = await self.repo.create(actor_id=1, data=create_data, target_snapshot={})
        with self.assertRaises(ScheduleError) as ctx:
            await self.repo.detail(actor_id=999, schedule_id=sched_id)
        self.assertEqual(ctx.exception.status_code, 403)

    async def test_due_scan_pauses_schedule_after_permissions_are_revoked(self):
        now = datetime.now(UTC)
        data = ScheduleCreate(name="revoked", interval_minutes=60, targets=[ScheduleTarget(config_id=1, account_id=10, quantities=[1])])
        sched_id = await self.repo.create(actor_id=1, data=data, target_snapshot={"items": []})
        async with self.sessions() as db, db.begin():
            row = await db.get(Schedule, sched_id)
            row.next_run_at = now - timedelta(seconds=1)
        self.quotes_mock.authorizer.load.side_effect = LoginError("QUOTE_PERMISSION_REVOKED")
        self.assertEqual(await self.service.scan_due(clock_now=now), [])
        detail = await self.repo.detail(1, sched_id)
        self.assertEqual(detail["status"], "PAUSED")
        self.assertEqual(detail["pause_reason"], "SCHEDULE_INPUT_OR_PERMISSION_CHANGED")


if __name__ == "__main__":
    unittest.main()
