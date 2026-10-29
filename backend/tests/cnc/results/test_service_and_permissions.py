import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.exceptions import CustomException
from app.modules.cnc.cnc_quote_result.model import CncQuoteResultModel
from app.modules.cnc.cnc_quote_result.schema import CncQuoteResultQueryParam
from app.modules.cnc.cnc_quote_result.service import CncQuoteResultService


class TestQuoteResultService(unittest.IsolatedAsyncioTestCase):
    _id_seq = 0

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        # Create table in memory
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: CncQuoteResultModel.__table__.create(sync_conn, checkfirst=True))

        # Auth schemas for testing RBAC
        self.user1_auth = AuthSchema(user=CoreUserSchema(id=101, username="user1", is_superuser=False))
        self.user2_auth = AuthSchema(user=CoreUserSchema(id=102, username="user2", is_superuser=False))
        self.admin_auth = AuthSchema(user=CoreUserSchema(id=1, username="admin", is_superuser=True))

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _insert_result(
        self,
        session: AsyncSession,
        *,
        actor_id: int = 101,
        quote_status: str = "QUOTED",
        success: bool = True,
        unit_price: Decimal | None = Decimal("100.00"),
        total_amount: Decimal | None = Decimal("100.00"),
        platform_id: int = 2,
        platform_code: str = "jlc_cnc_cn",
        currency: str = "CNY",
        quantity: int = 1,
        comparison_key: str | None = "comp-key-1",
        batch_id: str | None = "batch-1",
        round_id: str | None = "round-1",
        observed_at: datetime | None = None,
        is_deleted: bool = False,
    ) -> CncQuoteResultModel:
        TestQuoteResultService._id_seq += 1
        now = observed_at or datetime.now(UTC)
        row = CncQuoteResultModel(
            id=TestQuoteResultService._id_seq,
            uuid=str(uuid4()),
            run_id=str(uuid4()),
            batch_id=batch_id,
            round_id=round_id,
            config_id=1,
            config_name="测试配置",
            part_id=1,
            part_name="test.step",
            platform_id=platform_id,
            platform_code=platform_code,
            platform_name="嘉立创" if platform_id == 2 else "Xometry",
            account_id=10,
            account_alias="acc1",
            quote_status=quote_status,
            success=success,
            unit_price=unit_price,
            total_amount=total_amount,
            currency=currency,
            quantity=quantity,
            comparison_key=comparison_key,
            queue_ms=2000,
            active_execution_ms=15000,
            total_wall_ms=17000,
            duration_seconds=Decimal("15.00"),
            evidence_id="ev-123",
            evidence_state="available",
            quoted_at=now,
            observed_at=now,
            created_id=actor_id,
            updated_id=actor_id,
            created_time=now,
            updated_time=now,
            is_deleted=is_deleted,
        )
        session.add(row)
        await session.flush()
        return row

    async def test_cross_user_detail_and_soft_delete_rejection(self):
        async with self.session_maker() as db, db.begin():
            r1 = await self._insert_result(db, actor_id=101)
            r_deleted = await self._insert_result(db, actor_id=101, is_deleted=True)

        async with self.session_maker() as db:
            # 1. Owner can view own record
            s1 = CncQuoteResultService(self.user1_auth, db)
            detail = await s1.detail(r1.id)
            self.assertEqual(detail.id, r1.id)

            # 2. Other user accessing r1 raises 403 Forbidden
            s2 = CncQuoteResultService(self.user2_auth, db)
            with self.assertRaises(CustomException) as ctx:
                await s2.detail(r1.id)
            self.assertEqual(ctx.exception.code, 403)

            # 3. Soft-deleted record returns 404 Not Found
            with self.assertRaises(CustomException) as ctx:
                await s1.detail(r_deleted.id)
            self.assertEqual(ctx.exception.code, 404)

            # 4. Superuser can view any non-deleted record
            s_admin = CncQuoteResultService(self.admin_auth, db)
            admin_detail = await s_admin.detail(r1.id)
            self.assertEqual(admin_detail.id, r1.id)

    async def test_stats_metrics_recalculation_and_quote_kind_separation(self):
        async with self.session_maker() as db, db.begin():
            # 1 QUOTED
            await self._insert_result(db, actor_id=101, quote_status="QUOTED", success=True)
            # 1 REFERENCE_ESTIMATE (must NOT be counted as formal quote)
            await self._insert_result(db, actor_id=101, quote_status="REFERENCE_ESTIMATE", success=True)
            # 1 PENDING_REVIEW
            await self._insert_result(db, actor_id=101, quote_status="PENDING_REVIEW", success=True)
            # 1 FAILED
            await self._insert_result(db, actor_id=101, quote_status="FAILED", success=False, unit_price=None)
            # 1 Other user record (should not leak into user1 stats)
            await self._insert_result(db, actor_id=102, quote_status="QUOTED", success=True)

        async with self.session_maker() as db:
            s1 = CncQuoteResultService(self.user1_auth, db)
            stats = await s1.get_stats()

            self.assertEqual(stats.total_quotes, 4)
            self.assertEqual(stats.quoted_quotes, 1)
            self.assertEqual(stats.reference_estimate_quotes, 1)
            self.assertEqual(stats.pending_review_quotes, 1)
            self.assertEqual(stats.failed_quotes, 1)
            self.assertEqual(stats.completed_quotes, 3)

            # Denominator = completed (3) + failed (1) = 4
            self.assertEqual(stats.total_items, 4)
            # Completion rate = 3 / 4 = 75.0%
            self.assertEqual(stats.completion_rate, "75.0%")
            # Formal quote rate = 1 / 4 = 25.0%
            self.assertEqual(stats.formal_quote_rate, "25.0%")

    async def test_stats_zero_denominator_yields_none(self):
        async with self.session_maker() as db:
            s1 = CncQuoteResultService(self.user1_auth, db)
            stats = await s1.get_stats()

            self.assertEqual(stats.total_items, 0)
            self.assertIsNone(stats.completion_rate)
            self.assertIsNone(stats.formal_quote_rate)

    async def test_history_prices_chronological_ordering_and_group_diffs(self):
        base_time = datetime(2026, 10, 28, 10, 0, 0, tzinfo=UTC)
        async with self.session_maker() as db, db.begin():
            # Point 1 (earliest): price = 100
            await self._insert_result(
                db, actor_id=101, unit_price=Decimal("100.00"), comparison_key="group-A", observed_at=base_time
            )
            # Point 2 (+1 hour): price = 115 (+15, +0.1500)
            await self._insert_result(
                db, actor_id=101, unit_price=Decimal("115.00"), comparison_key="group-A", observed_at=base_time + timedelta(hours=1)
            )
            # Point 3 (+2 hours): price = 115 (+0, +0.0000, identical price observation retained)
            await self._insert_result(
                db, actor_id=101, unit_price=Decimal("115.00"), comparison_key="group-A", observed_at=base_time + timedelta(hours=2)
            )
            # Point in different comparison group: price = 200
            await self._insert_result(
                db, actor_id=101, unit_price=Decimal("200.00"), comparison_key="group-B", observed_at=base_time + timedelta(hours=1)
            )

        async with self.session_maker() as db:
            s1 = CncQuoteResultService(self.user1_auth, db)
            # Query group-A
            points = await s1.get_history_prices(search=CncQuoteResultQueryParam(comparison_key="group-A"))
            self.assertEqual(len(points), 3)

            # Ascending chronological order
            self.assertEqual(points[0].unit_price, "100.0000")
            self.assertIsNone(points[0].price_diff)
            self.assertIsNone(points[0].change_rate)

            self.assertEqual(points[1].unit_price, "115.0000")
            self.assertEqual(points[1].price_diff, "+15.0000")
            self.assertEqual(points[1].change_rate, "+0.1500")

            self.assertEqual(points[2].unit_price, "115.0000")
            self.assertEqual(points[2].price_diff, "+0.0000")
            self.assertEqual(points[2].change_rate, "+0.0000")
