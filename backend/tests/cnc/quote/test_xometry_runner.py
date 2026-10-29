"""Declared-file decisions and delayed saves through the real durable owner."""

import asyncio
from urllib.parse import urlsplit
from uuid import uuid4

import test_quote_runner as original
from _quote_support import STEP, CncQuoteIntentModel, CncQuoteRunModel, Part, QuoteDatabase, browser_manager, wait_for
from sqlalchemy import select, update

from app.modules.cnc.browser.contracts import ConfigurationReceipt, DeclarationReceipt, Operation
from app.modules.cnc.login.contracts import LoginInput
from app.modules.cnc.quote.contracts import ExportDeclaration, ExportDeclarationDecision, ExportDeclarationOption, QuoteError, StartQuote
from app.modules.cnc.quote.providers import AdapterBinding
from app.modules.cnc.quote.service import QuoteService


def declaration(identity="a"):
    return ExportDeclaration(
        declaration_id=identity * 64,
        statement="Synthetic current-file export declaration.",
        options=[ExportDeclarationOption(value="not_controlled", label="No, this file is not controlled."), ExportDeclarationOption(value="controlled", label="Yes, this file is controlled.")],
    )


class DeclaringAdapter(original.Adapter):
    def __init__(self, snapshot, run_id, sessions):
        super().__init__(snapshot, run_id)
        self.sessions = sessions
        self.pending = True
        self.manual_reason = "QUOTE_EXPORT_DECLARATION_REQUIRED"
        self.export_declaration = declaration()
        self.current_declaration = self.export_declaration
        self.continues = 0
        self.unconfirmed = False
        self.attempt = None
        self.decision_seen_before_continue = None

    async def read_export_declaration(self, session):
        session.check_active()
        self.export_declaration = self.current_declaration
        return self.current_declaration

    def can_reauthenticate(self, session):
        session.check_active()
        return urlsplit(getattr(session.page, "url", "")).hostname == "login.xometry.com"

    async def continue_declaration(self, session, current, choice):
        session.check_active()
        self.mutation_tasks.append(asyncio.current_task())
        self.continues += 1
        self.attempt = (current.declaration_id, choice)
        async with self.sessions() as db:
            row = await db.scalar(select(CncQuoteRunModel).where(CncQuoteRunModel.run_id == self.run_id))
            intent = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.run_id == self.run_id, CncQuoteIntentModel.operation == "declaration"))
            self.decision_seen_before_continue = row.frozen["export_declaration_decision"]
            if intent.state != "claimed":
                raise AssertionError("Continue before durable claim")
        if self.unconfirmed:
            raise TimeoutError
        self.current_declaration = self.export_declaration = None
        self.manual_reason = None
        return DeclarationReceipt(current.declaration_id, choice, self.uploaded.sha256, self.uploaded.reference)

    async def reconcile(self, session, key):
        session.check_active()
        if key.operation == Operation.UPLOAD:
            return self.uploaded if self.current_declaration is None else None
        if key.operation == Operation.DECLARATION and self.current_declaration is None and self.attempt is not None:
            return DeclarationReceipt(*self.attempt, self.uploaded.sha256, self.uploaded.reference)
        return None


class DelayedSaveAdapter(original.Adapter):
    def __init__(self, snapshot, run_id):
        super().__init__(snapshot, run_id)
        self.save_observations = 0

    async def configure(self, session, upload, requested):
        await super().configure(session, upload, requested)
        raise TimeoutError

    async def reconcile(self, session, key):
        session.check_active()
        if key.operation == Operation.CONFIGURE:
            self.save_observations += 1
            return ConfigurationReceipt(self.effective) if self.save_observations >= 2 else None
        return None


class XometryOwnerTests(QuoteDatabase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.manager, self.browser_repo, self.executor, self.provider = browser_manager()
        self.mode = "declaration"

        def factory(snapshot, run_id):
            self.adapter = DeclaringAdapter(snapshot, run_id, self.sessions) if self.mode == "declaration" else DelayedSaveAdapter(snapshot, run_id)
            return AdapterBinding(self.adapter, "synthetic-decision-v1", 1000)

        self.service = QuoteService(self.repo, self.manager, factory)

    async def asyncTearDown(self):
        await self.manager.close_all()
        await super().asyncTearDown()

    async def start_waiting(self):
        initial = await self.service.start(self.auth, 5, StartQuote(request_id=uuid4()))
        self.activity = self.service.activities[initial.run_id]
        await wait_for(lambda: self.activity.view.export_declaration is not None, seconds=20)
        return initial

    async def finish(self):
        await wait_for(lambda: self.activity.terminal, seconds=30)
        await wait_for(lambda: not self.manager.accounts)
        return self.activity.view

    def decision(self):
        return ExportDeclarationDecision(declaration_id=self.activity.view.export_declaration.declaration_id, choice="not_controlled")

    async def test_exact_decision_is_committed_before_owner_continue(self):
        initial = await self.start_waiting()
        self.assertFalse(self.activity.view.can_input)
        for kind, payload in [("input", LoginInput(kind="key", key="Enter")), ("resume", None)]:
            with self.assertRaisesRegex(QuoteError, "QUOTE_MANUAL_INPUT_NOT_ALLOWED"):
                await self.service.command(self.auth, 5, initial.run_id, kind, payload)
        await self.service.command(self.auth, 5, initial.run_id, "declaration", self.decision())
        final = await self.finish()
        self.assertEqual(final.status, "QUOTED")
        self.assertEqual(self.adapter.decision_seen_before_continue["sha256"], self.adapter.uploaded.sha256)
        self.assertEqual(self.adapter.decision_seen_before_continue["choice"], "not_controlled")
        self.assertEqual((self.adapter.uploads, self.adapter.continues), (1, 1))
        self.assertEqual(len(set(self.adapter.mutation_tasks)), 1)
        async with self.sessions() as db:
            intent = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.operation == "declaration"))
            self.assertEqual(intent.state, "confirmed")

    async def test_stale_statement_refreshes_prompt_without_claiming_continue(self):
        initial = await self.start_waiting()
        previous = self.decision()
        self.adapter.current_declaration = declaration("b")
        view = await self.service.command(self.auth, 5, initial.run_id, "declaration", previous)
        self.assertEqual(view.reason, "QUOTE_EXPORT_DECLARATION_STALE")
        self.assertEqual(view.export_declaration.declaration_id, "b" * 64)
        self.assertEqual(self.adapter.continues, 0)
        async with self.sessions() as db:
            self.assertIsNone(await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.operation == "declaration")))

    async def test_uncertain_continue_reconciles_without_another_click(self):
        initial = await self.start_waiting()
        decision = self.decision()
        self.adapter.unconfirmed = True
        for _ in range(2):
            view = await self.service.command(self.auth, 5, initial.run_id, "declaration", decision)
            self.assertEqual(view.reason, "QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY")
            self.assertFalse(view.can_input)
        self.assertEqual(self.adapter.continues, 1)
        self.adapter.current_declaration = self.adapter.export_declaration = None
        await self.service.command(self.auth, 5, initial.run_id, "declaration", decision)
        self.assertEqual((await self.finish()).status, "QUOTED")
        self.assertEqual((self.adapter.uploads, self.adapter.continues), (1, 1))

    async def test_identity_expiry_over_declaration_keeps_coordinates_blocked(self):
        initial = await self.start_waiting()
        self.executor.page.url = "https://www.xometry.com/quoting/home/"
        self.provider.verify.return_value = False
        view = await self.service.command(self.auth, 5, initial.run_id, "declaration", self.decision())
        self.assertEqual(view.reason, "LOGIN_IDENTITY_VERIFICATION_REQUIRED")
        self.assertIsNotNone(view.export_declaration)
        self.assertFalse(view.can_input)
        with self.assertRaisesRegex(QuoteError, "QUOTE_MANUAL_INPUT_NOT_ALLOWED"):
            await self.service.command(self.auth, 5, initial.run_id, "input", LoginInput(kind="key", key="Enter"))
        self.assertEqual(self.adapter.continues, 0)

    async def test_hosted_reauthentication_cannot_send_stale_click_to_declaration(self):
        initial = await self.start_waiting()
        decision = self.decision()
        navigation = list(self.executor.navigation)
        self.executor.page.url = "https://login.xometry.com/u/login/password"
        self.provider.verify.return_value = False
        view = await self.service.command(self.auth, 5, initial.run_id, "declaration", decision)
        self.assertIsNone(view.export_declaration)
        self.assertTrue(view.can_input)
        await self.service.command(self.auth, 5, initial.run_id, "input", LoginInput(kind="key", key="Enter"))
        self.executor.page.keyboard.press.assert_awaited_once()
        self.executor.page.url = "https://www.xometry.com/quoting/home/"
        self.provider.verify.return_value = True
        view = await self.service.command(self.auth, 5, initial.run_id, "input", LoginInput(kind="click", x=1, y=1))
        self.executor.page.mouse.click.assert_not_awaited()
        self.assertIsNotNone(view.export_declaration)
        self.assertFalse(view.can_input)
        await self.service.command(self.auth, 5, initial.run_id, "declaration", decision)
        self.assertEqual((await self.finish()).status, "QUOTED")
        self.assertEqual(self.executor.navigation, navigation)

    async def test_delayed_save_reconciles_read_only_in_real_owner(self):
        self.mode = "save"
        initial = await self.service.start(self.auth, 5, StartQuote(request_id=uuid4()))
        self.activity = self.service.activities[initial.run_id]
        self.assertEqual((await self.finish()).status, "QUOTED")
        self.assertEqual(self.adapter.configurations, 1)
        self.assertEqual(self.adapter.save_observations, 2)

    async def test_cancelled_uncertain_save_cannot_be_retried_by_a_new_run(self):
        self.mode = "save"
        initial = await self.service.start(self.auth, 5, StartQuote(request_id=uuid4()))
        self.activity = self.service.activities[initial.run_id]
        await wait_for(lambda: self.activity.configure_pending, seconds=20)
        await self.service.command(self.auth, 5, initial.run_id, "close")
        with self.assertRaisesRegex(QuoteError, "QUOTE_PRIOR_MUTATION_UNCONFIRMED_NO_RETRY"):
            await self.service.start(self.auth, 5, StartQuote(request_id=uuid4()))
        self.assertEqual(self.adapter.configurations, 1)

    async def test_known_different_frozen_file_can_start_without_erasing_prior_claim(self):
        initial = await self.start_waiting()
        old_hash = self.activity.snapshot.payload.sha256
        await self.service.command(self.auth, 5, initial.run_id, "close")
        changed = STEP.replace(b"HEADER;", b"HEADER;\n/* a distinct actual source */")
        self.file.write_bytes(changed)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Part).values(size_bytes=len(changed)))
        new = await self.service.start(self.auth, 5, StartQuote(request_id=uuid4()))
        self.assertNotEqual(new.run_id, initial.run_id)
        current = self.service.activities[new.run_id]
        self.assertNotEqual(current.snapshot.payload.sha256, old_hash)
        async with self.sessions() as db:
            old_run = await db.get(CncQuoteRunModel, initial.run_id)
            prior = await db.scalar(select(CncQuoteIntentModel).where(CncQuoteIntentModel.run_id == initial.run_id))
            self.assertEqual(old_run.frozen["sha256"], old_hash)
            self.assertEqual(prior.state, "uncertain")

    async def test_missing_or_invalid_legacy_frozen_hash_conservatively_blocks_new_file(self):
        initial = await self.start_waiting()
        await self.service.command(self.auth, 5, initial.run_id, "close")
        changed = STEP.replace(b"HEADER;", b"HEADER;\n/* a distinct new file */")
        self.file.write_bytes(changed)
        async with self.sessions() as db, db.begin():
            await db.execute(update(Part).values(size_bytes=len(changed)))
        for prior_hash in (None, "not-a-sha256", "0" * 63, 123):
            with self.subTest(prior_hash=prior_hash):
                async with self.sessions() as db, db.begin():
                    row = await db.get(CncQuoteRunModel, initial.run_id)
                    frozen = {key: value for key, value in row.frozen.items() if key != "sha256"}
                    if prior_hash is not None:
                        frozen["sha256"] = prior_hash
                    row.frozen = frozen
                with self.assertRaisesRegex(QuoteError, "QUOTE_PRIOR_UPLOAD_UNCONFIRMED_NO_RETRY"):
                    await self.service.start(self.auth, 5, StartQuote(request_id=uuid4()))
