"""Declaration HTTP privacy and exact-file decisions in independent transactions."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from _quote_support import CncQuoteIntentModel, CncQuoteRunModel, QuoteDatabase, User
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import handle_exception
from app.modules.cnc.browser.contracts import Geometry, IntentKey, IntentState, Operation, SessionScope, UploadReceipt, item_fingerprint
from app.modules.cnc.browser.files import StepPayload
from app.modules.cnc.quote import routes
from app.modules.cnc.quote.contracts import ExportDeclaration, ExportDeclarationOption, QuoteAccount, QuoteError, QuoteRunView, StartQuote
from app.modules.cnc.quote.repository import DurableIntentStore
from app.modules.cnc.quote.service import QuoteService

PERMISSIONS = [
    "module_cnc:cnc_part_config:query",
    "module_cnc:cnc_part_config:update",
    "module_cnc:cnc_account:query",
    "module_cnc:cnc_account:update",
]


def declaration():
    return ExportDeclaration(
        declaration_id="a" * 64,
        statement="Synthetic current declaration for the displayed file. No real file is classified by this test.",
        options=[
            ExportDeclarationOption(value="not_controlled", label="Synthetic not-controlled choice"),
            ExportDeclarationOption(value="controlled", label="Synthetic controlled choice"),
        ],
    )


def application(auth):
    """Materialize the real quote routes without the business app or database."""
    app = FastAPI()
    handle_exception(app)
    parent = APIRouter(prefix="/cnc/cnc_part_config")
    routes.register_quote_routes(parent)
    app.include_router(parent)

    async def current_user():
        return auth

    app.dependency_overrides[get_current_user] = current_user
    return app


class DeclarationHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.auth = AuthSchema(user=CoreUserSchema(id=7), permissions=PERMISSIONS.copy())
        self.run_id = str(uuid4())
        self.view = QuoteRunView(
            run_id=self.run_id,
            config_id=5,
            account_id=31,
            platform_name="Synthetic",
            masked_username="sy***@example.test",
            file_name="synthetic.step",
            status="WAITING_HUMAN",
            stage="parse",
            reason="QUOTE_EXPORT_DECLARATION_REQUIRED",
            can_input=False,
            requested={"material": "Aluminum 6061", "quantity": "2"},
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            export_declaration=declaration(),
        )
        self.service = SimpleNamespace(
            repository=SimpleNamespace(accounts=AsyncMock(return_value=[QuoteAccount(id=31, alias="Synthetic", masked_username="sy***@example.test")])),
            start=AsyncMock(return_value=self.view),
            status=AsyncMock(return_value=self.view),
            command=AsyncMock(return_value=self.view),
        )
        self.audit = AsyncMock()
        self.warning = patch("app.core.exceptions.logger.warning")
        self.error = patch("app.core.exceptions.logger.error")
        self.patches = [
            patch.object(routes, "get_quote_service", return_value=self.service),
            patch("app.modules.cnc.login.routes._write_operation_log_async", self.audit),
            self.warning,
            self.error,
        ]
        self.mocks = [item.start() for item in self.patches]
        self.app = application(self.auth)
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://testserver")
        self.base = "/cnc/cnc_part_config/5/quote"
        self.run = f"{self.base}/runs/{self.run_id}"
        self.body = {"declaration_id": "a" * 64, "choice": "not_controlled"}

    async def asyncTearDown(self):
        await self.client.aclose()
        for item in reversed(self.patches):
            item.stop()

    async def test_current_decision_reaches_typed_owner_command_with_private_audit(self):
        response = await self.client.post(self.run + "/declaration", json=self.body)
        self.assertEqual(response.status_code, 200)
        args = self.service.command.await_args.args
        self.assertEqual(args[:4], (self.auth, 5, self.run_id, "declaration"))
        self.assertEqual(args[4].model_dump(), self.body)
        self.assertEqual(response.json()["data"]["export_declaration"], declaration().model_dump())
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        for call in self.audit.await_args_list:
            self.assertEqual(call.args[0]["request_payload"], "{}")
            self.assertEqual(call.args[0]["response_json"], "{}")
        self.assertTrue(self.audit.await_args_list)
        self.assertNotIn(self.body["declaration_id"], str(self.audit.await_args_list))

    async def test_declaration_requires_both_configuration_and_account_update(self):
        for permission in ("module_cnc:cnc_part_config:update", "module_cnc:cnc_account:update"):
            with self.subTest(missing=permission):
                self.auth.permissions = [value for value in PERMISSIONS if value != permission]
                response = await self.client.post(self.run + "/declaration", json=self.body)
                self.assertEqual(response.status_code, 403)
        self.service.command.assert_not_awaited()

    async def test_invalid_or_extra_decision_fields_are_rejected_without_echo(self):
        secret = "synthetic-declaration-never-echo"
        invalid = [
            {**self.body, "file_path": secret},
            {**self.body, "script": secret},
            {**self.body, "password": secret},
            {**self.body, "choice": secret},
            {**self.body, "choice": None},
            {**self.body, "declaration_id": "A" * 64},
            {**self.body, "declaration_id": "g" * 64},
            {**self.body, "declaration_id": secret},
            {},
        ]
        for body in invalid:
            with self.subTest(keys=list(body), choice=body.get("choice")):
                response = await self.client.post(self.run + "/declaration", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["msg"], "INVALID_ACCOUNT_OR_LOGIN_INPUT")
                self.assertNotIn(secret, response.text)
        self.service.command.assert_not_awaited()
        self.assertNotIn(secret, str(self.audit.await_args_list))
        self.assertNotIn(secret, str(self.mocks[2].call_args_list))
        self.assertNotIn(secret, str(self.mocks[3].call_args_list))

    async def test_stale_and_unconfirmed_decisions_return_fixed_business_reasons(self):
        for reason in ("QUOTE_EXPORT_DECLARATION_STALE", "QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY"):
            self.service.command.side_effect = QuoteError(reason)
            with self.subTest(reason=reason):
                response = await self.client.post(self.run + "/declaration", json=self.body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["msg"], reason)

    async def test_decision_storage_failure_does_not_expose_private_parameters(self):
        secret = "synthetic-private-decision-storage"
        self.service.command.side_effect = SQLAlchemyError(secret)
        response = await self.client.post(self.run + "/declaration", json=self.body)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["msg"], "ACCOUNT_STORAGE_UNAVAILABLE")
        self.assertNotIn(secret, response.text)
        self.assertNotIn(secret, str(self.audit.await_args_list))
        self.assertNotIn(secret, str(self.mocks[2].call_args_list))
        self.assertNotIn(secret, str(self.mocks[3].call_args_list))

    async def test_original_quote_commands_keep_their_request_shapes(self):
        # Existing callers need no declaration fields or replacement body.
        checks = [
            ("GET", self.base + "/accounts", None),
            ("POST", self.base + "/runs", {"request_id": str(uuid4()), "account_id": 31}),
            ("GET", self.run, None),
            ("POST", self.run + "/input", {"kind": "key", "key": "Enter"}),
            ("POST", self.run + "/resume", None),
            ("DELETE", self.run, None),
        ]
        for method, path, body in checks:
            with self.subTest(method=method, path=path):
                response = await self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 200)
        self.service.command.return_value = b"\xff\xd8synthetic\xff\xd9"
        response = await self.client.get(self.run + "/frame")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.content, b"\xff\xd8synthetic\xff\xd9")


class DeclarationPersistenceTests(QuoteDatabase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.snapshot = await self.repo.snapshot(self.auth, 5, 31)
        self.view, _ = await self.repo.create(self.auth, self.snapshot, str(uuid4()))
        self.declaration = declaration()
        self.view = self.view.model_copy(
            update={
                "status": "WAITING_HUMAN",
                "stage": "parse",
                "reason": "QUOTE_EXPORT_DECLARATION_REQUIRED",
                "can_input": False,
                "export_declaration": self.declaration,
            }
        )
        await self.repo.save(self.view)

    async def frozen(self):
        async with self.sessions() as db:
            row = await db.get(CncQuoteRunModel, self.view.run_id)
            return row.frozen

    async def test_exact_file_actor_statement_choice_and_time_are_durable_and_private(self):
        await self.repo.record_declaration(self.auth, self.snapshot, self.view.run_id, self.declaration, "not_controlled")
        decision = (await self.frozen())["export_declaration_decision"]
        self.assertEqual(decision["run_id"], self.view.run_id)
        self.assertEqual(decision["actor_id"], 7)
        self.assertEqual(decision["sha256"], self.snapshot.payload.sha256)
        self.assertEqual(decision["declaration_id"], self.declaration.declaration_id)
        self.assertEqual(decision["statement"], self.declaration.statement)
        self.assertEqual(decision["options"], [option.model_dump() for option in self.declaration.options])
        self.assertEqual(decision["choice"], "not_controlled")
        self.assertEqual(decision["scope"], "xometry_quote_only")
        self.assertIsNotNone(datetime.fromisoformat(decision["decided_at"]).utcoffset())
        public = await self.repo.find(self.auth, 5, run_id=self.view.run_id)
        self.assertNotIn("export_declaration_decision", public.model_dump_json())
        self.assertNotIn(self.snapshot.payload.sha256, public.model_dump_json())
        # Repeated delivery cannot replace the first decision or its time.
        await self.repo.record_declaration(self.auth, self.snapshot, self.view.run_id, self.declaration, "not_controlled")
        self.assertEqual((await self.frozen())["export_declaration_decision"], decision)
        with self.assertRaisesRegex(QuoteError, "QUOTE_EXPORT_DECLARATION_STALE"):
            await self.repo.record_declaration(self.auth, self.snapshot, self.view.run_id, self.declaration, "controlled")
        self.assertEqual((await self.frozen())["export_declaration_decision"], decision)

    async def test_stale_statement_file_actor_and_invalid_choice_never_create_a_decision(self):
        other = AuthSchema(user=CoreUserSchema(id=99))
        changed_file = replace(self.snapshot, payload=StepPayload(self.snapshot.payload.buffer, "b" * 64))
        cases = [
            (self.auth, self.snapshot, self.declaration.model_copy(update={"declaration_id": "b" * 64}), "not_controlled"),
            (self.auth, self.snapshot, self.declaration.model_copy(update={"statement": "A replacement statement"}), "not_controlled"),
            (self.auth, changed_file, self.declaration, "not_controlled"),
            (other, self.snapshot, self.declaration, "not_controlled"),
            (self.auth, self.snapshot, self.declaration, "unrecognized"),
        ]
        for auth, snapshot, displayed, choice in cases:
            with self.subTest(actor=auth.user.id, declaration_id=displayed.declaration_id, choice=choice):
                with self.assertRaisesRegex(QuoteError, "QUOTE_EXPORT_DECLARATION_STALE"):
                    await self.repo.record_declaration(auth, snapshot, self.view.run_id, displayed, choice)
                self.assertNotIn("export_declaration_decision", await self.frozen())

    async def test_another_actor_cannot_use_the_declaration_route_even_as_superuser(self):
        async with self.sessions() as db, db.begin():
            await db.execute(update(User).where(User.id == 99).values(is_superuser=True))
        other = AuthSchema(user=CoreUserSchema(id=99, is_superuser=True), permissions=PERMISSIONS.copy())
        manager = SimpleNamespace(accounts={}, command=AsyncMock(), revoke=AsyncMock())
        service = QuoteService(repository=self.repo, manager=manager)
        with patch.object(routes, "get_quote_service", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=application(other)), base_url="http://testserver") as client:
                response = await client.post(
                    f"/cnc/cnc_part_config/5/quote/runs/{self.view.run_id}/declaration",
                    json={"declaration_id": self.declaration.declaration_id, "choice": "not_controlled"},
                )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["msg"], "QUOTE_RUN_UNAVAILABLE")
        manager.command.assert_not_awaited()
        self.assertNotIn("export_declaration_decision", await self.frozen())

    async def test_cancelled_unconfirmed_upload_blocks_a_new_request_before_creation(self):
        key = IntentKey(
            SessionScope("7", "xometry_us", "31"),
            self.view.run_id,
            "1",
            Operation.UPLOAD,
            item_fingerprint(self.snapshot.payload.sha256, self.snapshot.requested),
        )
        store = DurableIntentStore(self.sessions)
        await store.claim(key)
        cancelled = await self.repo.cancel_orphan(self.auth, 5, self.view.run_id)
        self.assertEqual(cancelled.status, "CANCELLED")
        manager = SimpleNamespace(start=AsyncMock())
        service = QuoteService(repository=self.repo, manager=manager)
        with self.assertRaisesRegex(QuoteError, "QUOTE_PRIOR_UPLOAD_UNCONFIRMED_NO_RETRY"):
            await service.start(self.auth, 5, StartQuote(request_id=uuid4(), account_id=31))
        manager.start.assert_not_awaited()
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(CncQuoteRunModel)), 1)
            intent = await db.scalar(select(CncQuoteIntentModel))
            self.assertEqual(intent.state, IntentState.UNCERTAIN.value)
        self.assertFalse((await store.claim(key)).is_new)

    async def test_current_run_is_excluded_and_confirmed_receipt_releases_the_fence(self):
        key = IntentKey(
            SessionScope("7", "xometry_us", "31"),
            self.view.run_id,
            "1",
            Operation.UPLOAD,
            item_fingerprint(self.snapshot.payload.sha256, self.snapshot.requested),
        )
        store = DurableIntentStore(self.sessions)
        await store.claim(key)
        await self.repo.assert_upload_available(self.snapshot, run_id=self.view.run_id)
        with self.assertRaisesRegex(QuoteError, "QUOTE_PRIOR_UPLOAD_UNCONFIRMED_NO_RETRY"):
            await self.repo.assert_upload_available(self.snapshot)
        receipt = UploadReceipt("synthetic-confirmed-part", self.snapshot.payload.sha256, Geometry(*(Decimal("1") for _ in range(4))))
        await store.confirm(key, receipt)
        await self.repo.assert_upload_available(self.snapshot)
        self.assertEqual((await store.claim(key)).record.state, IntentState.CONFIRMED)
