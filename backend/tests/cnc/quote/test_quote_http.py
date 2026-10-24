"""Actual quote routes: both permissions, strict commands, private audit."""

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import httpx
from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import handle_exception
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.quote import routes
from app.modules.cnc.quote.contracts import QuoteAccount, QuoteRunView
from app.plugin.module_cnc.cnc_part_config.controller import CncPartConfigRouter

PERMISSIONS = ["module_cnc:cnc_part_config:query", "module_cnc:cnc_part_config:update", "module_cnc:cnc_account:query", "module_cnc:cnc_account:update"]


class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.auth = AuthSchema(user=CoreUserSchema(id=7), permissions=PERMISSIONS.copy())
        self.run_id = str(uuid4())
        self.view = QuoteRunView(run_id=self.run_id, config_id=5, account_id=31, platform_name="Synthetic", masked_username="sy***@example.test", file_name="synthetic.step", status="WAITING_HUMAN", stage="login", reason="MANUAL_LOGIN_REQUIRED", can_input=True, requested={"material": "Al", "quantity": "2"}, expires_at=datetime.now(UTC) + timedelta(minutes=30))
        self.service = SimpleNamespace(repository=SimpleNamespace(accounts=AsyncMock(return_value=[QuoteAccount(id=31, alias="Synthetic", masked_username="sy***@example.test")])), start=AsyncMock(return_value=self.view), status=AsyncMock(return_value=self.view), command=AsyncMock(return_value=self.view))
        self.audit = AsyncMock()
        self.patches = [patch.object(routes, "get_quote_service", return_value=self.service), patch("app.modules.cnc.login.routes._write_operation_log_async", self.audit), patch("app.core.exceptions.logger.warning"), patch("app.core.exceptions.logger.error")]
        self.mocks = [item.start() for item in self.patches]
        app = FastAPI()
        handle_exception(app)
        app.include_router(CncPartConfigRouter, prefix="/cnc")

        async def auth():
            return self.auth

        app.dependency_overrides[get_current_user] = auth
        self.app = app
        self.base = "/cnc/cnc_part_config/5/quote"
        self.run = self.base + "/runs/" + self.run_id
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()
        for item in reversed(self.patches):
            item.stop()

    async def test_each_run_endpoint_requires_both_update_permissions(self):
        requests = [("POST", self.base + "/runs", {"request_id": str(uuid4())}), ("GET", self.run, None), ("GET", self.run + "/frame", None), ("POST", self.run + "/input", {"kind": "key", "key": "Enter"}), ("POST", self.run + "/resume", None), ("DELETE", self.run, None)]
        for missing in ["module_cnc:cnc_part_config:update", "module_cnc:cnc_account:update"]:
            self.auth.permissions = [value for value in PERMISSIONS if value != missing]
            for method, path, body in requests:
                with self.subTest(missing=missing, method=method, path=path):
                    self.assertEqual((await self.client.request(method, path, json=body)).status_code, 403)
        self.service.start.assert_not_awaited()
        self.service.command.assert_not_awaited()

    async def test_accounts_require_config_query_or_detail_and_account_query(self):
        for permissions, expected in [(["module_cnc:cnc_part_config:query"], 403), (["module_cnc:cnc_account:query"], 403), (["module_cnc:cnc_part_config:detail", "module_cnc:cnc_account:query"], 200)]:
            self.auth.permissions = permissions
            self.assertEqual((await self.client.get(self.base + "/accounts")).status_code, expected)

    async def test_run_commands_are_credential_free_and_text_audit_is_empty(self):
        response = await self.client.post(self.base + "/runs", json={"account_id": 31, "request_id": str(uuid4())})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["run_id"], self.run_id)
        secret = "synthetic-private-otp"
        response = await self.client.post(self.run + "/input", json={"kind": "text", "text": secret})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.command.await_args.args[4].text, secret)
        self.assertNotIn(secret, response.text)
        for call in self.audit.await_args_list:
            self.assertEqual(call.args[0]["request_payload"], "{}")
            self.assertEqual(call.args[0]["response_json"], "{}")
        self.assertNotIn(secret, str(self.audit.await_args_list))

    async def test_rejected_input_and_storage_exceptions_are_sanitized(self):
        secret = "synthetic-never-log"
        response = await self.client.post(self.run + "/input", json={"kind": "text", "text": secret, "script": secret})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(secret, response.text)
        self.service.start.side_effect = SQLAlchemyError(secret)
        response = await self.client.post(self.base + "/runs", json={"request_id": str(uuid4())})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(secret, response.text)
        self.assertNotIn(secret, str(self.mocks[2].call_args_list))
        self.assertNotIn(secret, str(self.mocks[3].call_args_list))

    async def test_file_stop_uses_fixed_reason_without_global_exception_logging(self):
        # A changed frozen file fails repository.validate() with BrowserStop.
        # It must remain a safe business failure at every HTTP entry point.
        for action, method, path, body in [
            (self.service.start, "POST", self.base + "/runs", {"request_id": str(uuid4())}),
            (self.service.status, "GET", self.run, None),
            (self.service.command, "POST", self.run + "/resume", None),
        ]:
            action.side_effect = BrowserStop(Reason.FILE_INVALID)
            with self.subTest(method=method, path=path), patch("app.core.exceptions.logger.opt") as trace:
                response = await self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["msg"], "file_invalid")
                self.assertFalse(any(call.kwargs.get("exception") for call in trace.call_args_list))
                trace.return_value.error.assert_not_called()

    async def test_frame_is_private_binary_and_routes_are_unique(self):
        self.service.command.return_value = b"\xff\xd8synthetic\xff\xd9"
        response = await self.client.get(self.run + "/frame")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        paths = [path for path in self.app.openapi()["paths"] if "/quote/" in path]
        self.assertEqual(len(paths), 6)
        self.assertEqual(sum(len([method for method in operations if method in {"get", "post", "delete"}]) for path, operations in self.app.openapi()["paths"].items() if "/quote/" in path), 7)
