"""Real isolated transactions; no platform or configured business DB is used."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.modules.cnc.batch import repository as batch_repository
from app.modules.cnc.batch.contracts import BatchError, BatchRequest, attempt_request_id
from app.modules.cnc.batch.repository import BatchRepository
from app.modules.cnc.batch.service import BatchService
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel, CncQuoteCapacityModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
from app.modules.cnc.quote.contracts import QuoteError, QuoteResult
from tests.cnc.quote._quote_support import Base, Config, Menu, QuoteDatabase, Role, copy_table


class Batch(Base):
    __table__ = copy_table(CncQuoteBatchModel.__table__)


class Capacity(Base):
    __table__ = copy_table(CncQuoteCapacityModel.__table__)


class Item(Base):
    __table__ = copy_table(CncQuoteBatchItemModel.__table__)


class BatchTests(QuoteDatabase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.extra_patches = [
            patch.object(batch_repository, "Batch", Batch),
            patch.object(batch_repository, "Capacity", Capacity),
            patch.object(batch_repository, "Item", Item),
            patch("app.modules.cnc.cnc_quote_batch_item.model.CncQuoteBatchItemModel", Item),
            patch("app.config.setting.settings.CNC_BATCH_ENABLED", True),
        ]
        for p in self.extra_patches:
            p.start()
        async with self.sessions() as db, db.begin():
            db.add(Capacity(id=1, version=0))
            role = await db.get(Role, 1)
            # Explicitly select the relation inside an async session.
            await db.refresh(role, ["menus"])
            role.menus.extend(Menu(id=100 + i, permission="module_cnc:cnc_quote_batch:" + p) for i, p in enumerate(["create", "query", "detail", "cancel"]))
        self.repository = BatchRepository(self.sessions)
        self.service = BatchService(self.repo, self.repository)

    async def asyncTearDown(self):
        for p in reversed(self.extra_patches):
            p.stop()
        await super().asyncTearDown()

    def request(self, quantities=None, id=None):
        return BatchRequest(request_id=id or uuid4(), targets=[{"config_id": 5, "account_id": 31, "quantities": quantities or [1, 2, 5]}])

    async def test_preview_create_idempotency_and_conflict(self):
        data = self.request()
        preview = await self.service.preview(self.auth, data)
        self.assertEqual(preview["item_count"], 3)
        responses = await asyncio.gather(*(self.service.create(self.auth, data) for _ in range(3)))
        self.assertEqual(len({r["id"] for r in responses}), 1)
        with self.assertRaises(BatchError) as error:
            await self.service.create(self.auth, self.request([9], data.request_id))
        self.assertEqual(error.exception.status_code, 409)
        async with self.sessions() as db:
            self.assertEqual((await db.get(Config, 5)).quantity, 2)

    async def test_all_or_nothing_capacity_and_invalid_target(self):
        self.repository.capacity = 2
        with self.assertRaises(BatchError):
            await self.service.create(self.auth, self.request())
        self.assertEqual((await self.repository.list(7))["total"], 0)
        data = self.request([1])
        data.targets.append(data.targets[0].model_copy(update={"config_id": 999}))
        with self.assertRaises(QuoteError):
            await self.service.create(self.auth, data)
        self.assertEqual((await self.repository.list(7))["total"], 0)

    async def test_frozen_source_changes_fail_and_replay_retains_original(self):
        data = self.request([5])
        result = await self.service.create(self.auth, data)
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        self.assertEqual(dict(snapshot.requested.values)["quantity"], "5")
        async with self.sessions() as db, db.begin():
            await db.execute(update(Config).values(material="Steel"))
        with self.assertRaises(QuoteError) as error:
            await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        self.assertEqual(error.exception.reason, "QUOTE_INPUT_CHANGED")
        self.assertEqual((await self.service.create(self.auth, data))["id"], result["id"])

    async def test_cancel_pending_never_creates_run_and_cross_actor_hidden(self):
        result = await self.service.create(self.auth, self.request())
        with self.assertRaises(BatchError):
            await self.repository.cancel(99, result["id"])
        await self.repository.cancel(7, result["id"])
        await self.repository.cancel(7, result["id"])
        self.assertIsNone(await self.repository.claim("owner"))
        self.assertEqual((await self.repository.detail(7, result["id"]))["status"], "CANCELLED")
        self.assertTrue(all(i["run_id"] is None for i in await self.repository.items(7, result["id"])))

    async def test_attempt_fencing_atomic_completion_and_duplicate_result(self):
        result = await self.service.create(self.auth, self.request([5]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, created = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        self.assertTrue(created)
        candidate = view.model_copy(
            update={
                "status": "REFERENCE_ESTIMATE",
                "stage": "complete",
                "result": QuoteResult(status="REFERENCE_ESTIMATE", amount="12.34", currency="USD", price_scope="unit", effective=view.requested, observed_at=datetime.now(UTC)),
            }
        )
        await self.repo.save(candidate)
        await self.repo.save(candidate)
        self.assertEqual((await self.repository.detail(7, result["id"]))["status"], "COMPLETED")
        attempts = await self.repository.attempts(7, claim["id"])
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["run"]["requested"]["quantity"], "5")
        from tests.cnc.quote._quote_support import CncQuoteResultModel

        async with self.sessions() as db:
            rows = (await db.scalars(select(CncQuoteResultModel))).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(getattr(rows[0], "platform_code"), "xometry_us")

    async def test_result_store_failure_cannot_publish_completed(self):
        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)

        async def fail(*args):
            raise RuntimeError("synthetic storage failure")

        with patch.object(self.repo, "_persist_result", fail):
            with self.assertRaises(RuntimeError):
                await self.repo.save(view.model_copy(update={"status": "QUOTED"}))
        self.assertEqual((await self.repository.items(7, result["id"]))[0]["exec_status"], "RUNNING")
        self.assertEqual((await self.repo.find(self.auth, 5, run_id=view.run_id)).status, "STARTING")

    async def test_line_amount_and_unknown_currency_survive_result_projection(self):
        from app.modules.cnc.cnc_quote_result.schema import CncQuoteResultOutSchema
        from tests.cnc.quote._quote_support import CncQuoteResultModel

        for status in ["QUOTED", "FAILED"]:
            created = await self.service.create(self.auth, self.request([1]))
            claim = await self.repository.claim("owner")
            snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
            view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
            result = QuoteResult(status="QUOTED", amount="25.40", price_scope="line", effective=view.requested, observed_at=datetime.now(UTC)) if status == "QUOTED" else None
            await self.repo.save(view.model_copy(update={"status": status, "result": result}))
            async with self.sessions() as db:
                row = await db.scalar(select(CncQuoteResultModel).where(CncQuoteResultModel.__table__.c.run_id == view.run_id))
                projection = CncQuoteResultOutSchema.model_validate(row)
            self.assertIsNone(projection.currency)
            self.assertIsNone(projection.unit_price)
            self.assertEqual(str(projection.total_amount), "25.4000" if status == "QUOTED" else "None")
            self.assertEqual((await self.repository.detail(7, created["id"]))["status"], "COMPLETED" if status == "QUOTED" else "FAILED")

    async def test_cancel_and_stale_owner_fence_mutations(self):
        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repository.cancel(7, result["id"])
        with self.assertRaises(QuoteError):
            await self.repo.validate_claim(view.run_id)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Item).values(claim_token=99))
        with self.assertRaises(QuoteError):
            await self.repo.save(view.model_copy(update={"status": "CANCELLED"}))
        with self.assertRaisesRegex(QuoteError, "BATCH_CLAIM_LOST"):
            await self.repo.stage_shortcut_result(view.model_copy(update={"status": "REFERENCE_ESTIMATE"}), {"kind": "REFERENCE_ESTIMATE"})

    async def test_cancel_waiting_owner_after_quote_permission_revocation(self):
        from app.modules.cnc.batch.dispatcher import QuoteDispatcher
        from app.modules.cnc.quote.service import QuoteService
        from tests.cnc.quote._quote_support import CncQuoteIntentModel, browser_manager, wait_for

        manager, _, _, provider = browser_manager()
        provider.verify.return_value = False
        provider.submit.return_value = False
        self.repo.login.claim = AsyncMock(return_value=1)
        self.repo.login.release = AsyncMock()
        quotes = QuoteService(self.repo, manager, adapter_factory=lambda *_: None)
        dispatcher = QuoteDispatcher(self.service, quotes)
        try:
            result = await self.service.create(self.auth, self.request([1]))
            await dispatcher.tick()
            item = (await self.repository.items(7, result["id"]))[0]
            activity = quotes.activities[item["run_id"]]
            await wait_for(lambda: activity.view.status == "WAITING_HUMAN", seconds=20)
            await self.repo.claim_shortcut(item["run_id"], "upload")
            async with self.sessions() as db, db.begin():
                role = await db.get(Role, 1)
                await db.refresh(role, ["menus"])
                role.menus = [m for m in role.menus if m.permission not in {"module_cnc:cnc_part_config:update", "module_cnc:cnc_account:update"}]
            with self.assertRaisesRegex(QuoteError, "QUOTE_PERMISSION_REVOKED"):
                await self.repo.authorizer.load(7)
            current = await self.service.authorize(self.auth, "cancel", for_run=False)
            await self.repository.cancel(current.user.id, result["id"])
            await dispatcher.tick()
            self.assertEqual((await self.repository.detail(7, result["id"]))["status"], "CANCELLED")
            self.assertFalse(manager.accounts)
            async with self.sessions() as db:
                intent = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.__table__.c.run_id == item["run_id"]))
                self.assertEqual(getattr(intent, "state"), "claimed")
        finally:
            await manager.close_all()

    async def test_stale_or_mismatched_batch_claim_never_stops_an_owner(self):
        from types import SimpleNamespace

        from app.modules.cnc.quote.service import QuoteService

        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        assert claim is not None
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repository.cancel(7, result["id"])
        candidate = claim | {"run_id": view.run_id}
        activity = SimpleNamespace(batch_claim=claim, view=view, snapshot=snapshot, pending_result=False)
        manager = SimpleNamespace(accounts={snapshot.account.id: SimpleNamespace(quote_activity=activity)}, revoke=AsyncMock())
        quotes = QuoteService(self.repo, manager)
        quotes.activities[view.run_id] = activity
        for altered in ({"owner": "other"}, {"token": claim["token"] + 1}, {"actor_id": 99}, {"run_id": str(uuid4())}):
            self.assertEqual(await quotes.stop_cancelled_batch_owner(candidate | altered, self.repository), "claim_lost")
        activity.batch_claim = claim | {"token": claim["token"] + 1}
        self.assertEqual(await quotes.stop_cancelled_batch_owner(candidate, self.repository), "owner_unavailable")
        manager.revoke.assert_not_awaited()
        self.assertEqual((await self.repository.items(7, result["id"]))[0]["exec_status"], "CANCELLING")

    async def test_cancel_without_local_owner_preserves_run_for_reconciliation(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher
        from app.modules.cnc.quote.service import QuoteService

        result = await self.service.create(self.auth, self.request([1]))
        quotes = QuoteService(self.repo, SimpleNamespace(accounts={}, revoke=AsyncMock()))
        dispatcher = QuoteDispatcher(self.service, quotes)
        claim = await self.repository.claim(dispatcher.owner)
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repo.claim_shortcut(view.run_id, "upload")
        await self.repository.cancel(7, result["id"])
        await dispatcher.tick()
        item = (await self.repository.items(7, result["id"]))[0]
        self.assertEqual((item["exec_status"], item["run_id"]), ("RECONCILING", view.run_id))
        self.assertEqual(await self.repository.active(dispatcher.owner), [])
        self.assertIsNone(await self.repository.claim("other-owner"))

    async def test_cancel_preserves_and_commits_already_staged_result(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher
        from app.modules.cnc.quote.service import QuoteService
        from tests.cnc.quote._quote_support import CncQuoteResultModel

        result = await self.service.create(self.auth, self.request([1]))
        quotes = QuoteService(self.repo, SimpleNamespace(accounts={}, revoke=AsyncMock()))
        dispatcher = QuoteDispatcher(self.service, quotes)
        claim = await self.repository.claim(dispatcher.owner)
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repo.claim_shortcut(view.run_id, "upload")
        candidate = view.model_copy(
            update={
                "status": "REFERENCE_ESTIMATE",
                "result": QuoteResult(status="REFERENCE_ESTIMATE", amount="7.50", currency="USD", price_scope="unit", effective=view.requested, observed_at=datetime.now(UTC)),
            }
        )
        await self.repo.stage_shortcut_result(candidate, {"kind": "REFERENCE_ESTIMATE"})
        await self.repository.cancel(7, result["id"])
        await dispatcher.tick()
        self.assertEqual((await self.repository.detail(7, result["id"]))["status"], "COMPLETED")
        async with self.sessions() as db:
            saved = (await db.scalars(select(CncQuoteResultModel).where(CncQuoteResultModel.__table__.c.run_id == view.run_id))).all()
            self.assertEqual(len(saved), 1)
            self.assertEqual(str(getattr(saved[0], "unit_price")), "7.5000")

    async def test_owner_finish_commits_staged_result_before_cancelling(self):
        from app.modules.cnc.quote.runner import QuoteActivity

        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        activity = QuoteActivity(self.auth, snapshot, view, self.repo, lambda *_: None)
        activity.batch_claim = claim
        await self.repo.claim_shortcut(view.run_id, "upload")
        candidate = view.model_copy(
            update={
                "status": "REFERENCE_ESTIMATE",
                "result": QuoteResult(status="REFERENCE_ESTIMATE", amount="7.50", currency="USD", price_scope="unit", effective=view.requested, observed_at=datetime.now(UTC)),
            }
        )
        await self.repo.stage_shortcut_result(candidate, {"kind": "REFERENCE_ESTIMATE"})
        await self.repository.cancel(7, result["id"])
        await activity.finish("SESSION_CLOSED")
        self.assertEqual(activity.view.status, "REFERENCE_ESTIMATE")
        self.assertEqual((await self.repository.detail(7, result["id"]))["status"], "COMPLETED")

    async def test_shutdown_joins_its_shortcut_even_after_actor_permission_loss(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher
        from app.modules.cnc.quote.service import QuoteService

        await self.service.create(self.auth, self.request([1]))
        quotes = QuoteService(self.repo, SimpleNamespace(accounts={}, revoke=AsyncMock()))
        dispatcher = QuoteDispatcher(self.service, quotes)
        claim = await self.repository.claim(dispatcher.owner)
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        activity = SimpleNamespace(batch_claim=claim, view=view, snapshot=snapshot, pending_result=False, finish=AsyncMock())
        quotes.activities[view.run_id] = activity
        started, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def shortcut():
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                cleaning.set()
                await release.wait()

        task = asyncio.create_task(shortcut())
        quotes._jlc_tasks[view.run_id] = task
        await started.wait()
        async with self.sessions() as db, db.begin():
            role = await db.get(Role, 1)
            await db.refresh(role, ["menus"])
            role.menus = [m for m in role.menus if m.permission not in {"module_cnc:cnc_part_config:update", "module_cnc:cnc_account:update"}]
        with self.assertRaisesRegex(QuoteError, "QUOTE_PERMISSION_REVOKED"):
            await self.repo.authorizer.load(7)
        closing = asyncio.create_task(dispatcher.stop())
        try:
            await asyncio.wait_for(cleaning.wait(), timeout=5)
            self.assertFalse(closing.done())
        finally:
            release.set()
            await asyncio.wait_for(closing, timeout=5)
        self.assertTrue(task.done())
        activity.finish.assert_awaited_once_with("SESSION_CLOSED")

    async def test_shutdown_timeout_reports_and_fences_unsettled_run(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher
        from app.modules.cnc.quote.service import QuoteService
        from tests.cnc.quote._quote_support import CncQuoteIntentModel

        result = await self.service.create(self.auth, self.request([1]))
        quotes = QuoteService(self.repo, SimpleNamespace(accounts={}, revoke=AsyncMock()))
        dispatcher = QuoteDispatcher(self.service, quotes, shutdown_timeout=0.05)
        claim = await self.repository.claim(dispatcher.owner)
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repo.claim_shortcut(view.run_id, "upload")
        activity = SimpleNamespace(batch_claim=claim, view=view, snapshot=snapshot, pending_result=False, finish=AsyncMock())
        quotes.activities[view.run_id] = activity
        started, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def shortcut():
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                cleaning.set()
                await release.wait()

        task = asyncio.create_task(shortcut())
        quotes._jlc_tasks[view.run_id] = task
        await started.wait()
        try:
            with self.assertRaisesRegex(RuntimeError, "CNC_BATCH_SHUTDOWN_UNSETTLED"):
                await dispatcher.stop()
            self.assertTrue(cleaning.is_set())
            self.assertFalse(dispatcher.shutdown_pending.done())
            with self.assertRaisesRegex(RuntimeError, "CNC_BATCH_SHUTDOWN_UNSETTLED"):
                await dispatcher.start()
            item = (await self.repository.items(7, result["id"]))[0]
            self.assertEqual((item["exec_status"], item["error_code"]), ("RECONCILING", "BATCH_SHUTDOWN_UNSETTLED"))
            async with self.sessions() as db:
                intent = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.__table__.c.run_id == view.run_id))
                self.assertEqual(getattr(intent, "state"), "claimed")
        finally:
            release.set()
            if dispatcher.shutdown_pending is not None:
                await asyncio.wait_for(dispatcher.shutdown_pending, timeout=5)

    async def test_shutdown_joins_terminal_shortcut_still_releasing_resources(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher
        from app.modules.cnc.quote.service import QuoteService

        await self.service.create(self.auth, self.request([1]))
        quotes = QuoteService(self.repo, SimpleNamespace(accounts={}, revoke=AsyncMock()))
        dispatcher = QuoteDispatcher(self.service, quotes)
        claim = await self.repository.claim(dispatcher.owner)
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        activity = SimpleNamespace(batch_claim=claim, view=view, snapshot=snapshot, terminal=True, pending_result=False, finish=AsyncMock())
        quotes.activities[view.run_id] = activity
        cleaning, release = asyncio.Event(), asyncio.Event()

        async def shortcut_cleanup():
            cleaning.set()
            await release.wait()

        task = asyncio.create_task(shortcut_cleanup())
        quotes._jlc_tasks[view.run_id] = task
        await cleaning.wait()
        closing = asyncio.create_task(dispatcher.stop())
        try:
            await asyncio.sleep(0.05)
            self.assertFalse(closing.done())
            self.assertFalse(task.cancelled())
        finally:
            release.set()
            await asyncio.wait_for(closing, timeout=5)
        self.assertTrue(task.done())
        self.assertFalse(task.cancelled())

    async def test_two_parts_two_platforms_expand_exactly_twelve(self):
        from dataclasses import replace

        from tests.cnc.quote._quote_support import ACCOUNT, Account, Part, Platform

        async with self.sessions() as db, db.begin():
            db.add_all(
                [
                    Part(id=10, file_path=str(self.file)),
                    Platform(id=49, login_url="https://www.jlc-cnc.com", quote_entry_url="https://www.jlc-cnc.com/cncOrder"),
                    Account(id=32, platform_id=49),
                    Config(id=6, site_type=49),
                    Config(id=7, part_id=10),
                    Config(id=8, part_id=10, site_type=49),
                ]
            )
        second = replace(ACCOUNT, id=32, platform_id=49, login_url="https://www.jlc-cnc.com", quote_url="https://www.jlc-cnc.com/cncOrder")

        async def load(auth, id):
            return ACCOUNT if id == 31 else second

        self.login.load.side_effect = load
        data = BatchRequest(request_id=uuid4(), targets=[{"config_id": id, "account_id": 31 if id in {5, 7} else 32, "quantities": [1, 2, 5, 2]} for id in [5, 6, 7, 8]])
        preview = await self.service.preview(self.auth, data)
        created = await self.service.create(self.auth, data)
        self.assertEqual(preview["item_count"], 12)
        self.assertEqual(created["item_count"], 12)
        items = await self.repository.items(7, created["id"])
        self.assertEqual({(i["config_id"], i["account_id"], i["requested"]["quantity"]) for i in items}, {(i["config_id"], i["account_id"], i["requested"]["quantity"]) for i in preview["items"]})

    async def test_remote_candidate_survives_failed_store_and_local_retry(self):
        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repo.claim_shortcut(view.run_id, "upload")
        candidate = view.model_copy(
            update={
                "status": "REFERENCE_ESTIMATE",
                "result": QuoteResult(status="REFERENCE_ESTIMATE", amount="7.50", currency="USD", price_scope="unit", effective=view.requested, observed_at=datetime.now(UTC)),
            }
        )
        await self.repo.stage_shortcut_result(candidate, {"kind": "REFERENCE_ESTIMATE"})
        with patch.object(self.repo, "_persist_result", side_effect=RuntimeError("storage")):
            with self.assertRaises(RuntimeError):
                await self.repo.persist_pending_result(view.run_id)
        self.assertEqual((await self.repository.items(7, result["id"]))[0]["exec_status"], "RUNNING")
        restored = await self.repo.persist_pending_result(view.run_id)
        self.assertEqual(restored.result.amount, "7.50")
        self.assertEqual((await self.repository.detail(7, result["id"]))["status"], "COMPLETED")

    async def test_staged_batch_result_survives_owner_failure(self):
        from app.modules.cnc.quote.runner import QuoteActivity

        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        activity = QuoteActivity(self.auth, snapshot, view, self.repo)
        activity.batch_claim = claim
        candidate = view.model_copy(update={"status": "REFERENCE_ESTIMATE", "result": QuoteResult(status="REFERENCE_ESTIMATE", effective=view.requested, observed_at=datetime.now(UTC))})
        await self.repo.stage_shortcut_result(candidate, {"kind": "REFERENCE_ESTIMATE"})
        activity.pending_result = True
        with self.assertRaisesRegex(QuoteError, "QUOTE_RESULT_PENDING"):
            await self.repo.save(view.model_copy(update={"status": "FAILED"}))
        await activity.finish("BROWSER_UNAVAILABLE")
        self.assertEqual(activity.view.status, "REFERENCE_ESTIMATE")
        self.assertEqual((await self.repository.detail(7, result["id"]))["status"], "COMPLETED")

    async def test_failure_after_claimed_remote_mutation_is_not_retried(self):
        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repo.claim_shortcut(view.run_id, "upload")
        await self.repo.save(view.model_copy(update={"status": "FAILED", "stage": "upload", "reason": "NETWORK_TIMEOUT"}))
        item = (await self.repository.items(7, result["id"]))[0]
        self.assertEqual(item["exec_status"], "RECONCILING")
        self.assertEqual(item["run_id"], view.run_id)
        self.assertIsNone(await self.repository.claim("new-owner"))

    async def test_pre_mutation_network_failure_retries_with_a_new_attempt(self):
        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("owner")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        await self.repo.save(view.model_copy(update={"status": "FAILED", "stage": "login", "reason": "NETWORK_TIMEOUT"}))
        item = (await self.repository.items(7, result["id"]))[0]
        self.assertEqual(item["exec_status"], "RETRY_WAIT")
        self.assertEqual(item["attempt_count"], 1)
        self.assertIsNone(item["run_id"])
        self.assertIsNone(await self.repository.claim("new-owner"))

    async def test_dispatcher_progresses_without_status_reads_after_item_failure(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher

        async def execute(auth, snapshot, request_id, *, batch_claim):
            view, _ = await self.repo.create(auth, snapshot, request_id, batch_claim=batch_claim)
            await self.repo.save(view.model_copy(update={"status": "FAILED", "reason": "SYNTHETIC_PROVIDER_UNAVAILABLE"}))

        dispatcher = QuoteDispatcher(self.service, SimpleNamespace(start_snapshot=execute), interval=0.01)
        await self.service.create(self.auth, self.request([1, 2]))
        await dispatcher.tick()
        await dispatcher.tick()
        async with self.sessions() as db:
            states = (await db.scalars(select(Item.__table__.c.exec_status))).all()
        self.assertEqual(states, ["FAILED", "FAILED"])

    async def test_dispatcher_recovers_a_claim_that_expires_after_startup(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher

        await self.service.create(self.auth, self.request([1]))
        prior = await self.repository.claim("old-process")
        await self.repository.settle_expired_claims()
        self.assertIsNone(await self.repository.claim("new-process"))
        async with self.sessions() as db, db.begin():
            await db.execute(update(Item).where(Item.__table__.c.id == prior["id"]).values(claim_until=datetime.now(UTC) - timedelta(seconds=1)))

        received = []

        async def execute(auth, snapshot, request_id, *, batch_claim):
            received.append(batch_claim)

        dispatcher = QuoteDispatcher(self.service, SimpleNamespace(start_snapshot=execute))
        await dispatcher.tick()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["id"], prior["id"])
        self.assertGreater(received[0]["token"], prior["token"])

    async def test_expired_owners_cannot_renew_or_settle_claims(self):
        await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("old-owner")
        now = datetime.now(UTC)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Item).where(Item.__table__.c.id == claim["id"]).values(claim_until=now + timedelta(seconds=1)))

        # The claim is live when selected, but expires while the lock is held.
        with patch.object(batch_repository, "utcnow", side_effect=[now, now + timedelta(seconds=2)]):
            self.assertEqual(await self.repository.active("old-owner"), [])
        async with self.sessions() as db, db.begin():
            row = await db.get(Item, claim["id"])
            self.assertEqual(getattr(row, "claim_until").replace(tzinfo=UTC), now + timedelta(seconds=1))
            await db.execute(update(Item).where(Item.__table__.c.id == claim["id"]).values(claim_until=now - timedelta(seconds=1)))

        await self.repository.release_wait(claim)
        await self.repository.fail_claim(claim, "STALE_FAILURE")
        async with self.sessions() as db:
            row = await db.get(Item, claim["id"])
            self.assertEqual(getattr(row, "exec_status"), "PENDING")
            self.assertEqual(getattr(row, "claim_owner"), "old-owner")
        await self.repository.settle_expired_claims()
        replacement = await self.repository.claim("new-owner")
        self.assertEqual(replacement["id"], claim["id"])
        self.assertGreater(replacement["token"], claim["token"])

    async def test_expired_run_is_reconciled_without_replay(self):
        from types import SimpleNamespace

        from app.modules.cnc.batch.dispatcher import QuoteDispatcher

        result = await self.service.create(self.auth, self.request([1]))
        claim = await self.repository.claim("old-process")
        snapshot = await self.repo.from_frozen(self.auth, claim["input_snapshot"])
        view, _ = await self.repo.create(self.auth, snapshot, attempt_request_id(claim["id"], 1), batch_claim=claim)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Item).where(Item.__table__.c.id == claim["id"]).values(claim_until=datetime.now(UTC) - timedelta(seconds=1)))

        async def unexpected_execute(*args, **kwargs):
            self.fail("An expired Run must not be replayed")

        dispatcher = QuoteDispatcher(self.service, SimpleNamespace(start_snapshot=unexpected_execute))
        await dispatcher.tick()
        item = (await self.repository.items(7, result["id"]))[0]
        self.assertEqual(item["exec_status"], "RECONCILING")
        self.assertEqual(item["run_id"], view.run_id)
        self.assertEqual(item["error_code"], "BATCH_OWNER_LOST_NO_RETRY")
        self.assertEqual(await self.repository.active("old-process"), [])


def test_strict_input_and_stable_attempt_uuid():
    with pytest.raises(ValueError):
        BatchRequest(request_id=uuid4(), targets=[{"config_id": 5, "quantities": [True]}])
    id = str(uuid4())
    assert attempt_request_id(id, 1) == attempt_request_id(id, 1)
    assert attempt_request_id(id, 1) != attempt_request_id(id, 2)
