"""Actual account router contracts with isolated auth/repository boundaries.

No site startup, database, Redis, provider credentials or live platform is used.
Runtime/provider/lease behavior has separate tests; these exercise routing,
permission enforcement, repeated access checks and private payload handling.
"""

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import httpx
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import handle_exception
from app.modules.cnc.login.contracts import LoginError, LoginView
from app.plugin.module_cnc.cnc_account import controller

ACCOUNT_ID = 31
SESSION_ID = "synthetic-session-reference-12345"
BASE = f"/cnc/cnc_account/login/{ACCOUNT_ID}"
SESSION_PATH = f"{BASE}/sessions/{SESSION_ID}"
UPDATE_PERMISSION = "module_cnc:cnc_account:update"


class LoginHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.auth = AuthSchema(user=CoreUserSchema(id=7, is_superuser=False), permissions=[UPDATE_PERMISSION])
        self.view = LoginView(
            session_id=SESSION_ID,
            account_id=ACCOUNT_ID,
            platform_name="Synthetic platform",
            username="sy***@example.test",
            status="WAITING_HUMAN",
            reason="CHALLENGE_REQUIRED",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        self.account = SimpleNamespace(id=ACCOUNT_ID, actor_id=7)
        self.manager = SimpleNamespace(
            repository=SimpleNamespace(load=AsyncMock(return_value=self.account)),
            start=AsyncMock(return_value=self.view),
            command=AsyncMock(return_value=self.view),
            revoke=AsyncMock(),
            accounts={},
        )
        self.audit = AsyncMock()
        self.patches = [
            patch.object(controller, "get_login_manager", return_value=self.manager),
            patch("app.modules.cnc.login.routes._write_operation_log_async", self.audit),
            patch("app.core.exceptions.logger.warning"),
            patch("app.core.exceptions.logger.error"),
        ]
        self.mocks = [item.start() for item in self.patches]
        app = FastAPI()
        handle_exception(app)
        app.include_router(controller.CncAccountRouter, prefix="/cnc")

        async def current_auth():
            return self.auth

        app.dependency_overrides[get_current_user] = current_auth
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()
        for item in reversed(self.patches):
            item.stop()

    async def test_real_router_checks_current_permission_for_every_login_endpoint(self):
        self.auth.permissions = []
        requests = [
            ("POST", BASE, None),
            ("GET", SESSION_PATH, None),
            ("GET", f"{SESSION_PATH}/frame", None),
            ("POST", f"{SESSION_PATH}/input", {"kind": "key", "key": "Enter"}),
            ("POST", f"{SESSION_PATH}/verify", None),
            ("DELETE", SESSION_PATH, None),
        ]
        for method, path, body in requests:
            with self.subTest(method=method, path=path):
                response = await self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 403)
        self.manager.repository.load.assert_not_awaited()
        self.manager.start.assert_not_awaited()
        self.manager.command.assert_not_awaited()

    async def test_all_session_operations_reload_account_authorization(self):
        responses = [await self.client.post(BASE), await self.client.get(SESSION_PATH)]
        self.manager.command.return_value = b"\xff\xd8synthetic-frame\xff\xd9"
        frame = await self.client.get(f"{SESSION_PATH}/frame")
        self.assertEqual(frame.status_code, 200)
        self.assertEqual(frame.content, b"\xff\xd8synthetic-frame\xff\xd9")
        self.assertEqual(frame.headers["content-type"], "image/jpeg")
        self.assertEqual(frame.headers["cache-control"], "no-store")
        self.assertEqual(frame.headers["x-content-type-options"], "nosniff")
        self.manager.command.return_value = self.view
        responses.extend(
            [
                await self.client.post(f"{SESSION_PATH}/input", json={"kind": "click", "x": 1279, "y": 719}),
                await self.client.post(f"{SESSION_PATH}/verify"),
                await self.client.delete(SESSION_PATH),
            ]
        )
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["account_id"], ACCOUNT_ID)
            self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.manager.repository.load.await_count, 6)
        for call in self.manager.repository.load.await_args_list:
            self.assertIs(call.args[0], self.auth)
            self.assertEqual(call.args[1], ACCOUNT_ID)
        self.assertEqual([call.args[2] for call in self.manager.command.await_args_list], ["status", "frame", "input", "verify", "close"])

    async def test_text_input_is_delivered_but_never_echoed_or_audited(self):
        secret = "synthetic-one-time-code-must-stay-private"
        response = await self.client.post(f"{SESSION_PATH}/input", json={"kind": "text", "text": secret})
        self.assertEqual(response.status_code, 200)
        payload = self.manager.command.await_args.args[3]
        self.assertEqual(payload.kind, "text")
        self.assertEqual(payload.text, secret)
        self.assertNotIn(secret, response.text)
        self.audit.assert_awaited_once()
        record = self.audit.await_args.args[0]
        self.assertEqual(record["request_payload"], "{}")
        self.assertEqual(record["response_json"], "{}")
        self.assertNotIn(secret, str(record))

    async def test_rejected_input_never_reaches_global_raw_validation_logger(self):
        secret = "synthetic-rejected-secret-do-not-log"
        invalid_inputs = [
            {"kind": "text", "text": secret, "password": secret},
            {"kind": "click", "x": -1, "y": 4, "text": secret},
            {"kind": "text", "text": secret * 20},
        ]
        for body in invalid_inputs:
            with self.subTest(kind=body["kind"]):
                response = await self.client.post(f"{SESSION_PATH}/input", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn(secret, response.text)
                self.assertNotIn(secret, str(self.mocks[2].call_args_list))
                self.assertNotIn(secret, str(self.mocks[3].call_args_list))
        self.manager.command.assert_not_awaited()
        self.manager.repository.load.assert_not_awaited()

    async def test_disabled_owner_account_revokes_existing_session_and_denies_frame(self):
        self.manager.accounts[ACCOUNT_ID] = SimpleNamespace(account=SimpleNamespace(actor_id=7))
        self.manager.repository.load.side_effect = LoginError("ACCOUNT_DISABLED")
        response = await self.client.get(f"{SESSION_PATH}/frame")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["msg"], "ACCOUNT_DISABLED")
        self.assertNotIn("image/jpeg", response.headers["content-type"])
        self.manager.revoke.assert_awaited_once_with(ACCOUNT_ID)
        self.manager.command.assert_not_awaited()

    async def test_unauthorized_actor_cannot_close_another_actors_session(self):
        self.manager.accounts[ACCOUNT_ID] = SimpleNamespace(account=SimpleNamespace(actor_id=99))
        self.manager.repository.load.side_effect = LoginError("ACCOUNT_UNAVAILABLE")
        response = await self.client.delete(SESSION_PATH)
        self.assertEqual(response.status_code, 400)
        self.manager.revoke.assert_not_awaited()
        self.manager.command.assert_not_awaited()

    async def test_storage_errors_do_not_expose_sql_ciphertext_or_parameters(self):
        secret = "synthetic-private-ciphertext"
        for failure, status in ((SQLAlchemyError(secret), 500), (IntegrityError("UPDATE accounts", {"credential_ciphertext": secret}, RuntimeError(secret)), 409)):
            with self.subTest(failure=type(failure).__name__):
                self.manager.repository.load.side_effect = failure
                response = await self.client.post(BASE)
                self.assertEqual(response.status_code, status)
                self.assertNotIn(secret, response.text)
                self.assertNotIn(secret, str(self.mocks[2].call_args_list))
                self.assertNotIn(secret, str(self.mocks[3].call_args_list))


if __name__ == "__main__":
    unittest.main()
