import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import uuid4

from sqlalchemy import Table, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.exceptions import CustomException
from app.modules.cnc.cnc_quote_result.comparison import COMPARISON_RULE_VERSION, build_comparison_key
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
            await conn.run_sync(lambda sync_conn: cast(Table, CncQuoteResultModel.__table__).create(sync_conn, checkfirst=True))

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
        comparison_version: int | None = None,
        file_sha256: str | None = None,
        material: str | None = None,
        price_scope: str | None = None,
        lead_time_raw: str | None = None,
        tax_included: bool | None = None,
        shipping_included: bool | None = None,
        discount_amount: Decimal | None = None,
        extra_params: dict | None = None,
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
            comparison_version=comparison_version,
            file_sha256=file_sha256,
            material=material,
            price_scope=price_scope,
            lead_time_raw=lead_time_raw,
            tax_included=tax_included,
            discount_amount=discount_amount,
            extra_params=extra_params,
            effective_snapshot={"shipping_included": shipping_included},
            queue_ms=2000,
            active_execution_ms=15000,
            total_wall_ms=17000,
            duration_seconds=Decimal("15.00"),
            evidence_id="ev-123",
            evidence_state="available",
            evidence_screenshot="private/legacy-evidence.png",
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

    async def _insert_comparable(
        self, session: AsyncSession, *, unit_price: Decimal, observed_at: datetime,
        file_sha256: str = "ab" * 32, material: str = "AL6061", shipping_included: bool = False,
    ) -> CncQuoteResultModel:
        key = build_comparison_key(
            platform_code="jlc_cnc_cn", account_condition=10, file_sha256=file_sha256,
            quantity=1, currency="CNY", price_scope="unit", quote_kind="QUOTED",
            material=material, extra_params={}, lead_time_tier="5 days", tax_included=True,
            shipping_included=shipping_included, discount_amount=Decimal("0"),
        )
        self.assertIsNotNone(key)
        return await self._insert_result(
            session, unit_price=unit_price, observed_at=observed_at, comparison_key=key,
            comparison_version=COMPARISON_RULE_VERSION, file_sha256=file_sha256, material=material,
            price_scope="unit", lead_time_raw="5 days", tax_included=True,
            shipping_included=shipping_included, discount_amount=Decimal("0"), extra_params={},
        )

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

    async def test_page_returns_visible_items_and_has_next(self):
        async with self.session_maker() as db, db.begin():
            await self._insert_result(db, actor_id=101)
            await self._insert_result(db, actor_id=101)
            await self._insert_result(db, actor_id=102)

        async with self.session_maker() as db:
            service = CncQuoteResultService(self.user1_auth, db)
            first = await service.page(page_no=1, page_size=1)
            second = await service.page(page_no=2, page_size=1)
            self.assertEqual(first.total, 2)
            self.assertEqual(len(first.items), 1)
            self.assertTrue(first.has_next)
            self.assertEqual(len(second.items), 1)
            self.assertFalse(second.has_next)
            self.assertNotEqual(first.items[0].id, second.items[0].id)

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

    async def test_stats_keep_unknown_platform_and_currency_unknown(self):
        async with self.session_maker() as db, db.begin():
            unknown = await self._insert_result(db, actor_id=101, unit_price=Decimal("100"))
            named_only_by_id = await self._insert_result(db, actor_id=101, platform_id=1, unit_price=Decimal("200"))
            await db.execute(
                update(CncQuoteResultModel).where(CncQuoteResultModel.id == unknown.id).values(
                    platform_id=None, platform_name=None, platform_code=None, currency=None,
                )
            )
            await db.execute(
                update(CncQuoteResultModel).where(CncQuoteResultModel.id == named_only_by_id.id).values(
                    platform_name=None, platform_code=None, currency=None,
                )
            )

        async with self.session_maker() as db:
            stats = await CncQuoteResultService(self.user1_auth, db).get_stats()
            self.assertEqual(stats.total_quotes, 2)
            self.assertEqual(len(stats.platform_stats), 2)
            by_id = {item.platform_id: item for item in stats.platform_stats}
            for platform_id in (None, 1):
                self.assertIsNone(by_id[platform_id].platform_name)
                self.assertIsNone(by_id[platform_id].platform_code)
                self.assertIsNone(by_id[platform_id].currency)
            self.assertEqual(by_id[None].min_unit_price, "100.0000")
            self.assertEqual(by_id[1].min_unit_price, "200.0000")

    async def test_history_prices_chronological_ordering_and_group_diffs(self):
        base_time = datetime(2026, 10, 28, 10, 0, 0, tzinfo=UTC)
        async with self.session_maker() as db, db.begin():
            # Point 1 (earliest): price = 100
            first = await self._insert_comparable(db, unit_price=Decimal("100.00"), observed_at=base_time)
            # Point 2 (+1 hour): price = 115 (+15, +0.1500)
            await self._insert_comparable(db, unit_price=Decimal("115.00"), observed_at=base_time + timedelta(hours=1))
            # Point 3 (+2 hours): price = 115 (+0, +0.0000, identical price observation retained)
            await self._insert_comparable(db, unit_price=Decimal("115.00"), observed_at=base_time + timedelta(hours=2))
            # Point in different comparison group: price = 200
            await self._insert_comparable(db, unit_price=Decimal("200.00"), material="AL7075", observed_at=base_time + timedelta(hours=1))

        async with self.session_maker() as db:
            s1 = CncQuoteResultService(self.user1_auth, db)
            # Query group-A
            points = await s1.get_history_prices(search=CncQuoteResultQueryParam(comparison_key=first.comparison_key))
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

    async def test_unknown_and_legacy_keys_never_compare_or_fabricate_fields(self):
        base_time = datetime(2026, 10, 28, 10, 0, 0, tzinfo=UTC)
        async with self.session_maker() as db, db.begin():
            first = await self._insert_result(db, comparison_key=None, unit_price=Decimal("100"), observed_at=base_time)
            await self._insert_result(db, comparison_key=None, unit_price=Decimal("150"), observed_at=base_time + timedelta(hours=1))
            # A persisted v1 key can have been created with no file, material or scope.
            await self._insert_result(db, comparison_key="old-v1-key", comparison_version=1, unit_price=Decimal("200"), observed_at=base_time + timedelta(hours=2))
            await self._insert_result(db, comparison_key="old-v1-key", comparison_version=1, unit_price=Decimal("250"), observed_at=base_time + timedelta(hours=3))
            # Do not allow a spoofed v2 key to make incomplete snapshots comparable.
            await self._insert_result(db, comparison_key="fake-v2-key", comparison_version=COMPARISON_RULE_VERSION, unit_price=Decimal("300"), observed_at=base_time + timedelta(hours=4))
            await self._insert_result(db, comparison_key="fake-v2-key", comparison_version=COMPARISON_RULE_VERSION, unit_price=Decimal("350"), observed_at=base_time + timedelta(hours=5))
            await db.execute(
                update(CncQuoteResultModel).where(CncQuoteResultModel.id == first.id).values(
                    currency=None, quantity=None, platform_id=None, platform_name=None,
                    duration_seconds=None, quoted_at=None,
                )
            )

        async with self.session_maker() as db:
            points = await CncQuoteResultService(self.user1_auth, db).get_history_prices()
            self.assertEqual(len(points), 6)
            for point in points:
                self.assertIsNone(point.comparison_key)
                self.assertIsNone(point.price_diff)
                self.assertIsNone(point.change_rate)
                self.assertEqual(point.evidence_id, "ev-123")
                self.assertIsNone(point.evidence_screenshot)
            self.assertIsNone(points[0].currency)
            self.assertIsNone(points[0].quantity)
            self.assertIsNone(points[0].platform_id)
            self.assertIsNone(points[0].platform_name)
            self.assertIsNone(points[0].duration_seconds)
            self.assertIsNone(points[0].quoted_time)

    async def test_different_material_file_and_terms_do_not_mix_with_verified_series(self):
        base_time = datetime(2026, 10, 28, 10, 0, 0, tzinfo=UTC)
        async with self.session_maker() as db, db.begin():
            first = await self._insert_comparable(db, unit_price=Decimal("100"), observed_at=base_time)
            material = await self._insert_comparable(db, unit_price=Decimal("200"), material="AL7075", observed_at=base_time + timedelta(minutes=1))
            file = await self._insert_comparable(db, unit_price=Decimal("300"), file_sha256="cd" * 32, observed_at=base_time + timedelta(minutes=2))
            shipping = await self._insert_comparable(db, unit_price=Decimal("400"), shipping_included=True, observed_at=base_time + timedelta(minutes=3))
            again = await self._insert_comparable(db, unit_price=Decimal("110"), observed_at=base_time + timedelta(minutes=4))
            # Even a current-version key cannot override the stored actual dimensions.
            forged = await self._insert_comparable(db, unit_price=Decimal("500"), material="AL7075", observed_at=base_time + timedelta(minutes=5))
            forged.comparison_key = first.comparison_key

        async with self.session_maker() as db:
            points = await CncQuoteResultService(self.user1_auth, db).get_history_prices()
            by_id = {point.id: point for point in points}
            self.assertEqual(by_id[again.id].price_diff, "+10.0000")
            self.assertEqual(by_id[again.id].change_rate, "+0.1000")
            for item in (material, file, shipping):
                self.assertNotEqual(by_id[item.id].comparison_key, by_id[first.id].comparison_key)
                self.assertIsNone(by_id[item.id].price_diff)
            self.assertIsNone(by_id[forged.id].comparison_key)
            self.assertIsNone(by_id[forged.id].price_diff)
