"""Synthetic full pipeline on the real login owner and durable quote store."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from _quote_support import ACCOUNT, STEP, CncQuoteIntentModel, QuoteDatabase, Role, User, browser_manager, wait_for
from sqlalchemy import select, update

from app.modules.cnc.browser.contracts import (
    DayBasis,
    Geometry,
    IntentState,
    LeadTime,
    Parameters,
    PriceScope,
    QuoteFreshness,
    QuoteObservation,
    SubmissionReceipt,
    UploadReceipt,
)
from app.modules.cnc.login.contracts import LoginError, LoginInput
from app.modules.cnc.quote.contracts import ProvisionalQuote, StartQuote
from app.modules.cnc.quote.providers import AdapterBinding
from app.modules.cnc.quote.service import QuoteService


class Adapter:
    def __init__(self, snapshot, run_id):
        self.snapshot, self.run_id = snapshot, run_id
        self.geometry = Geometry(*(Decimal("1") for _ in range(4)))
        self.uploaded = UploadReceipt("synthetic-upload", snapshot.payload.sha256, self.geometry)
        self.effective = snapshot.requested
        self.uploads = self.configurations = self.submissions = 0
        self.pending = False
        self.pause = None
        self.mismatch = False
        self.outcome = "QUOTED"
        self.cache = False
        self.manual_reason = None
        self.stale_recalculation = False
        self.reconcile_count = 0
        self.session = None
        self.mutation_tasks = []

    async def upload(self, session, payload):
        session.check_active()
        self.session = session
        self.mutation_tasks.append(asyncio.current_task())
        self.uploads += 1
        if payload.buffer != STEP:
            raise AssertionError("wrong frozen payload")
        if self.pause:
            await self.pause.wait()
        if self.pending:
            raise TimeoutError
        return self.uploaded

    async def configure(self, session, upload, requested):
        session.check_active()
        self.mutation_tasks.append(asyncio.current_task())
        self.configurations += 1

    async def read_effective(self, session, upload):
        session.check_active()
        return Parameters.from_mapping({"material": "wrong", "quantity": "1"}) if self.mismatch else self.effective

    async def submit(self, session, upload, requested):
        session.check_active()
        self.mutation_tasks.append(asyncio.current_task())
        self.submissions += 1
        return SubmissionReceipt("synthetic-submission", upload.reference, requested)

    async def reconcile(self, session, key):
        session.check_active()
        self.reconcile_count += 1
        return self.uploaded if self.reconcile_count > 1 else None

    async def extract_quote(self, session, upload, submission):
        session.check_active()
        now = datetime.now(UTC)
        quote = QuoteObservation(
            session.scope, self.run_id, "1", upload.reference, submission.reference,
            upload.sha256, self.effective, self.geometry, Decimal("12.30"), "USD", PriceScope.UNIT,
            LeadTime("3 business days", 3, 3, DayBasis.BUSINESS),
            QuoteFreshness.CACHE_UNVERIFIED if self.cache else QuoteFreshness.CURRENT_CONFIRMED, now, now,
        )
        if self.stale_recalculation:
            quote = replace(quote, freshness=QuoteFreshness.RECALCULATED, priced_at=now - timedelta(seconds=60))
        if self.outcome != "QUOTED":
            if self.outcome == "PENDING_REVIEW":
                quote = replace(quote, amount=None, currency=None, price_scope=None, lead_time=None)
            return ProvisionalQuote(self.outcome, quote, "synthetic-current-status", True)
        return quote


class RunnerTests(QuoteDatabase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.manager, self.browser_repo, self.executor, self.provider = browser_manager()
        self.adapter = None
        self.modify_adapter = lambda adapter: None

        def factory(snapshot, run_id):
            self.adapter = Adapter(snapshot, run_id)
            self.modify_adapter(self.adapter)
            return AdapterBinding(self.adapter, "synthetic-v1", 1000)

        self.service = QuoteService(self.repo, self.manager, factory)

    async def asyncTearDown(self):
        await self.manager.close_all()
        await super().asyncTearDown()

    async def start(self):
        self.data = StartQuote(request_id=uuid4())
        view = await self.service.start(self.auth, 5, self.data)
        self.activity = self.service.activities[view.run_id]
        return view

    async def finish(self, *, timeout_seconds=10):
        await wait_for(lambda: self.activity.terminal, seconds=timeout_seconds)
        await wait_for(lambda: not self.manager.accounts)
        return await self.service.status(self.auth, 5, self.activity.activity_id)

    async def test_full_pipeline_same_owner_exact_buffer_params_and_durable_result(self):
        initial = await self.start()
        view = await self.finish()
        self.assertEqual(view.status, "QUOTED")
        self.assertEqual(view.result.amount, "12.30")
        self.assertEqual(view.result.effective, {"material": "Aluminum 6061", "quantity": "2"})
        self.assertEqual((self.adapter.uploads, self.adapter.configurations, self.adapter.submissions), (1, 1, 1))
        self.assertEqual(len(set(self.adapter.mutation_tasks)), 1)
        self.assertEqual(self.provider.submit.await_count, 0)
        self.assertEqual(self.executor.active, 0)
        self.assertEqual(len(self.browser_repo.releases), 1)
        persisted = await self.repo.find(self.auth, 5, run_id=view.run_id)
        self.assertEqual(persisted.result.amount, "12.30")
        repeated = await self.service.start(self.auth, 5, self.data)
        self.assertEqual(repeated.run_id, initial.run_id)
        self.assertEqual(self.browser_repo.claims, 1)
        self.assertEqual(self.activity.snapshot.account.password, "")
        self.assertEqual(self.activity.snapshot.payload.buffer, b"")

    async def test_account_login_entry_is_exclusive_during_quote(self):
        gate = asyncio.Event()
        self.modify_adapter = lambda adapter: setattr(adapter, "pause", gate)
        await self.start()
        await wait_for(lambda: self.adapter is not None and self.adapter.uploads == 1)
        with self.assertRaisesRegex(LoginError, "ACCOUNT_BUSY"):
            await self.manager.start(ACCOUNT)
        owned = self.manager.accounts[31]
        with self.assertRaisesRegex(LoginError, "ACCOUNT_BUSY"):
            await self.manager.command(ACCOUNT, owned.session_id, "frame")
        gate.set()
        self.assertEqual((await self.finish()).status, "QUOTED")

    async def test_cancel_mid_upload_marks_uncertain_and_does_not_resend(self):
        gate = asyncio.Event()
        self.modify_adapter = lambda adapter: setattr(adapter, "pause", gate)
        view = await self.start()
        await wait_for(lambda: self.adapter is not None and self.adapter.uploads == 1)
        stopped = await self.service.command(self.auth, 5, view.run_id, "close")
        self.assertEqual(stopped.status, "CANCELLED")
        async with self.sessions() as db:
            intent = await db.scalar(select(CncQuoteIntentModel))
            self.assertEqual(intent.state, IntentState.UNCERTAIN.value)
        repeated = await self.service.start(self.auth, 5, self.data)
        self.assertEqual(repeated.status, "CANCELLED")
        self.assertEqual(self.adapter.uploads, 1)
        self.assertEqual(self.executor.active, 0)

    async def test_slow_parser_reconciles_read_only_without_second_upload(self):
        self.modify_adapter = lambda adapter: setattr(adapter, "pending", True)
        await self.start()
        # Two deliberately paced observations plus per-phase real SQLite
        # transactions can exceed the ordinary 10 s fixture wait on Windows.
        view = await self.finish(timeout_seconds=30)
        self.assertEqual(view.status, "QUOTED")
        self.assertEqual(self.adapter.uploads, 1)
        self.assertEqual(self.adapter.reconcile_count, 2)
        async with self.sessions() as db:
            upload = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.operation == "upload"))
            self.assertEqual(upload.state, IntentState.CONFIRMED.value)

    async def test_export_declaration_is_manual_and_resume_never_uploads_again(self):
        def modify(adapter):
            adapter.pending = True
            adapter.manual_reason = "QUOTE_EXPORT_DECLARATION_REQUIRED"

        self.modify_adapter = modify
        view = await self.start()
        await wait_for(lambda: self.activity.can_input)
        self.assertEqual(self.activity.view.reason, "QUOTE_EXPORT_DECLARATION_REQUIRED")
        navigation = list(self.executor.navigation)
        await self.service.command(self.auth, 5, view.run_id, "input", LoginInput(kind="key", key="Enter"))
        self.adapter.manual_reason = None
        await self.service.command(self.auth, 5, view.run_id, "resume")
        self.assertEqual((await self.finish()).status, "QUOTED")
        self.assertEqual(self.adapter.uploads, 1)
        self.assertEqual(self.executor.navigation, navigation)

    async def test_paced_parse_accepts_frames_without_parallel_manual_input(self):
        self.modify_adapter = lambda adapter: setattr(adapter, "pending", True)
        view = await self.start()
        await wait_for(lambda: self.activity.view.stage == "parse")
        async with asyncio.timeout(2):
            frame = await self.service.command(self.auth, 5, view.run_id, "frame")
        self.assertTrue(frame.startswith(b"\xff\xd8"))
        with self.assertRaisesRegex(LoginError, "QUOTE_MANUAL_INPUT_NOT_ALLOWED"):
            await self.service.command(self.auth, 5, view.run_id, "input", LoginInput(kind="key", key="Enter"))
        self.assertEqual((await self.finish()).status, "QUOTED")

    async def test_effective_mismatch_and_cached_quote_cannot_succeed(self):
        self.modify_adapter = lambda adapter: setattr(adapter, "mismatch", True)
        await self.start()
        result = await self.finish()
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.reason, "parameters_mismatch")
        self.assertEqual(self.adapter.submissions, 0)
        self.modify_adapter = lambda adapter: setattr(adapter, "cache", True)
        await self.start()
        result = await self.finish()
        self.assertEqual(result.status, "FAILED")
        self.assertIsNone(result.result)

    async def test_estimate_and_actual_review_are_distinct_terminal_types(self):
        for status in ["REFERENCE_ESTIMATE", "PENDING_REVIEW"]:
            self.modify_adapter = lambda adapter, value=status: setattr(adapter, "outcome", value)
            await self.start()
            view = await self.finish()
            self.assertEqual(view.status, status)
            self.assertEqual(view.result.status, status)
            self.assertEqual(view.result.amount, "12.30" if status == "REFERENCE_ESTIMATE" else None)

    async def test_estimate_recalculated_before_run_is_rejected(self):
        def modify(adapter):
            adapter.outcome = "REFERENCE_ESTIMATE"
            adapter.stale_recalculation = True

        self.modify_adapter = modify
        await self.start()
        view = await self.finish()
        self.assertEqual(view.status, "FAILED")
        self.assertEqual(view.reason, "quote_invalid")
        self.assertIsNone(view.result)

    async def test_login_challenge_input_then_same_run_resume(self):
        self.provider.verify.return_value = False
        self.provider.submit.return_value = False
        view = await self.start()
        await wait_for(lambda: self.activity.can_input)
        self.assertEqual(self.activity.view.stage, "login")
        await self.service.command(self.auth, 5, view.run_id, "input", LoginInput(kind="key", key="Enter"))
        self.executor.page.keyboard.press.assert_awaited_once_with("Enter")
        self.provider.verify.return_value = True
        await self.service.command(self.auth, 5, view.run_id, "resume")
        final = await self.finish()
        self.assertEqual(final.status, "QUOTED")
        self.assertEqual(final.run_id, view.run_id)
        self.assertEqual(self.adapter.uploads, 1)
        self.assertEqual(self.browser_repo.claims, 1)

    async def test_mid_quote_identity_resume_is_read_only_without_navigation(self):
        original = None

        async def upload(session, payload):
            result = await original(session, payload)
            self.provider.verify.return_value = False
            return result

        def modify(adapter):
            nonlocal original
            original = adapter.upload
            adapter.upload = upload

        self.modify_adapter = modify
        view = await self.start()
        await wait_for(lambda: self.activity.can_input)
        before = list(self.executor.navigation)
        self.provider.verify.return_value = True
        await self.service.command(self.auth, 5, view.run_id, "resume")
        result = await self.finish()
        self.assertEqual(result.status, "QUOTED")
        self.assertEqual(self.executor.navigation, before)
        self.assertEqual(self.adapter.uploads, 1)

    async def test_missing_admitted_adapter_is_explicit_failure_zero_mutations(self):
        self.service.adapter_factory = lambda snapshot, run_id: None
        await self.start()
        result = await self.finish()
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.reason, "PROVIDER_AUTOMATION_UNVERIFIED")
        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(CncQuoteIntentModel)))
        self.assertEqual(self.executor.active, 0)

    async def test_store_confirmation_failure_does_not_retry_mutation(self):
        gate = asyncio.Event()
        self.modify_adapter = lambda adapter: setattr(adapter, "pause", gate)
        await self.start()
        await wait_for(lambda: self.adapter is not None and self.adapter.uploads == 1)
        self.activity.intents.confirm = AsyncMock(side_effect=RuntimeError("synthetic-private-write-error"))
        gate.set()
        result = await self.finish()
        self.assertEqual(result.status, "FAILED")
        self.assertNotIn("synthetic-private", result.model_dump_json())
        self.assertEqual(self.adapter.uploads, 1)

    async def test_role_revoked_after_upload_stops_before_configure(self):
        original = None

        async def upload(session, payload):
            receipt = await original(session, payload)
            async with self.sessions() as db, db.begin():
                await db.execute(update(Role).values(status=1))
            return receipt

        def modify(adapter):
            nonlocal original
            original = adapter.upload
            adapter.upload = upload

        self.modify_adapter = modify
        await self.start()
        await wait_for(lambda: self.activity.terminal)
        await wait_for(lambda: not self.manager.accounts)
        self.assertEqual(self.activity.view.status, "FAILED")
        self.assertEqual(self.activity.view.reason, "QUOTE_PERMISSION_REVOKED")
        self.assertEqual(self.adapter.uploads, 1)
        self.assertEqual(self.adapter.configurations, 0)
        self.assertEqual(self.adapter.submissions, 0)

    async def test_role_revoked_during_identity_read_stops_before_upload_claim(self):
        calls = 0

        async def verify(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                async with self.sessions() as db, db.begin():
                    await db.execute(update(Role).values(status=1))
            return True

        self.provider.verify.side_effect = verify
        await self.start()
        await wait_for(lambda: self.activity.terminal)
        await wait_for(lambda: not self.manager.accounts)
        self.assertEqual(self.activity.view.status, "FAILED")
        self.assertEqual(self.activity.view.reason, "QUOTE_PERMISSION_REVOKED")
        self.assertEqual(self.adapter.uploads, 0)
        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(CncQuoteIntentModel)))

    async def test_actor_disabled_before_owner_start_has_no_browser_navigation(self):
        original = self.manager.start

        async def start(account, *, quote_activity=None):
            async with self.sessions() as db, db.begin():
                await db.execute(update(User).where(User.id == 7).values(status=1))
            return await original(account, quote_activity=quote_activity)

        self.manager.start = start
        await self.start()
        await wait_for(lambda: self.activity.terminal)
        await wait_for(lambda: not self.manager.accounts)
        self.assertEqual(self.activity.view.reason, "QUOTE_ACTOR_UNAVAILABLE")
        self.assertEqual(self.executor.navigation, [])
        self.provider.submit.assert_not_awaited()

    async def test_result_store_failure_cannot_publish_quoted_and_orphan_can_settle(self):
        original_save = self.repo.save

        async def save(view, **kwargs):
            if view.status in {"QUOTED", "FAILED"}:
                raise RuntimeError("synthetic-private-result-store-failure")
            await original_save(view, **kwargs)

        self.repo.save = save
        view = await self.start()
        await wait_for(lambda: not self.manager.accounts)
        observed = await self.service.status(self.auth, 5, view.run_id)
        self.assertNotEqual(observed.status, "QUOTED")
        self.assertIsNone(observed.result)
        self.assertFalse(observed.can_input)
        closed = await self.service.command(self.auth, 5, view.run_id, "close")
        self.assertEqual(closed.status, "CANCELLED")

    async def test_next_quote_waits_for_terminal_browser_cleanup_before_claim(self):
        gate = asyncio.Event()
        self.executor.cleanup_gate = gate
        first = await self.start()
        await wait_for(lambda: self.activity.terminal and self.executor.cleanup_entered)
        second_start = asyncio.create_task(self.service.start(self.auth, 5, StartQuote(request_id=uuid4())))
        await asyncio.sleep(0.1)
        self.assertFalse(second_start.done())
        self.assertEqual(self.browser_repo.claims, 1)
        self.executor.cleanup_gate = None
        gate.set()
        second = await second_start
        self.activity = self.service.activities[second.run_id]
        self.assertNotEqual(first.run_id, second.run_id)
        self.assertEqual((await self.finish()).status, "QUOTED")
        self.assertEqual(self.browser_repo.claims, 2)
        self.assertEqual(len(self.browser_repo.releases), 2)
