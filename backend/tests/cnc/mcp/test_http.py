"""Actual MCP SDK/ASGI protocol with real JWT/session checks and isolated storage.

Run with unittest, avoiding the unrelated full-site startup in tests/conftest.py.
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import fakeredis.aioredis
import httpx2
from fastapi import FastAPI
from mcp import Client, ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError
from mcp_types import CLIENT_CAPABILITIES_META_KEY, CLIENT_INFO_META_KEY, PROTOCOL_VERSION_META_KEY

from app.config.setting import Settings, settings
from app.core.base_schema import JWTPayloadSchema
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.core.security import create_access_token
from app.modules.cnc.login import actions
from app.modules.cnc.login.contracts import LoginError, LoginView
from app.modules.cnc.login.credentials import seal_credentials
from app.modules.cnc.mcp import mcp_lifespan, register_mcp, server, tools
from app.utils.crypto_util import CryptoUtil

SECRET = "synthetic-private-password-must-not-be-returned"
ALL_PERMISSIONS = [item.permission for item in tools.TOOLS]
ACCOUNT = {
    "id": 31,
    "username": "synthetic@example.test",
    "password": seal_credentials("synthetic@example.test", SECRET).decode(),
    "platform_name": "Synthetic Platform",
    "login_url": "https://synthetic.test/login",
    "quote_url": "https://synthetic.test/quote",
}
RAW_ACCOUNT = {**ACCOUNT, "password": "", "credential_ciphertext": ACCOUNT["password"].encode()}
PART = {"id": 42, "file_name": "synthetic.step", "file_path": "/drawings/synthetic.step", "upload_authorized": False}
QUERY_TOOLS = {"cnc_account_list", "cnc_account_detail", "cnc_part_list", "cnc_part_detail", "cnc_part_config_list", "cnc_part_config_detail"}
ALL_TOOLS = QUERY_TOOLS | {"cnc_account_login", "cnc_account_decrypt_password", "cnc_part_config_quote"}
MUTATION_TOOLS = tuple(f"{module}_{operation}" for module in ("cnc_account", "cnc_part", "cnc_part_config") for operation in ("create", "update", "delete", "set_status"))


class FakeSession:
    def __init__(self, factory):
        self.factory = factory

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    @asynccontextmanager
    async def begin(self):
        try:
            yield
        except BaseException:
            self.factory.rollbacks += 1
            raise
        else:
            self.factory.commits += 1

    async def execute(self, statement):
        user_id = statement._where_criteria[0].right.value
        user = self.factory.users.get(user_id)
        return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: user))


class FakeSessions:
    def __init__(self):
        self.users = {7: SimpleNamespace(id=7, username="first", is_superuser=False), 9: SimpleNamespace(id=9, username="second", is_superuser=False)}
        self.commits = 0
        self.rollbacks = 0

    def __call__(self):
        return FakeSession(self)


class McpHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        self.sessions = FakeSessions()
        self.messages = []
        # Capture server DEBUG as well as application logs, excluding the test
        # client's own deliberate serialization of synthetic password arguments.
        for name in logging.root.manager.loggerDict:
            if name.startswith(("mcp.client", "httpx2")):
                logging.getLogger(name).setLevel(logging.WARNING)
        self.log_id = logger.add(lambda message: self.messages.append(str(message)), level="DEBUG", filter=lambda record: record["name"].startswith(("app.", "mcp.server")))
        self.patches = [patch.object(server, "async_db_session", self.sessions), patch.object(settings, "TOKEN_SLIDING_EXPIRE", False)]
        for item in self.patches:
            item.start()
        self.token = await self.issue("first-session", 7)

    async def asyncTearDown(self):
        logger.remove(self.log_id)
        for item in reversed(self.patches):
            item.stop()
        await self.redis.aclose()

    async def issue(self, session_id, user_id, permissions=None, **extra):
        payload = {"session_id": session_id, "user_id": user_id, "user_name": f"user-{user_id}", "permissions": ALL_PERMISSIONS if permissions is None else permissions, **extra}
        await self.redis.set(f"user_session:{session_id}", json.dumps(payload), ex=3600)
        return create_access_token(JWTPayloadSchema(sub=session_id, exp=datetime.now(UTC) + timedelta(hours=1)))

    @asynccontextmanager
    async def running(self, token=None, root_path="/api/v1", config=None):
        app = FastAPI(root_path=root_path)
        app.state.redis = self.redis
        with patch("app.modules.cnc.mcp.settings", config or settings.model_copy(update={"MCP_ENABLED": True})):
            register_mcp(app)
        self.active_server = app.state.cnc_mcp
        async with mcp_lifespan(app), httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://localhost", headers={"Authorization": f"Bearer {token or self.token}"}) as http:
            yield http

    @asynccontextmanager
    async def session(self, http, url="http://localhost/api/v1/mcp/"):
        async with streamable_http_client(url, http_client=http) as (read, write), ClientSession(read, write, read_timeout_seconds=5) as client:
            await client.initialize()
            yield client

    async def rpc(self, http, method, params=None, path="/api/v1/mcp/", **headers):
        return await http.post(
            path, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}, headers={"Accept": "application/json, text/event-stream", "Mcp-Protocol-Version": "2025-11-25", **headers}
        )

    async def test_official_client_lists_queries_login_and_decryption_with_correct_hints(self):
        async with self.running() as http, self.session(http) as client:
            result = await client.list_tools()
            self.assertEqual({item.name for item in result.tools}, ALL_TOOLS)
            self.assertTrue(all(item.annotations.read_only_hint == (item.name != "cnc_account_login") for item in result.tools))
            self.assertTrue(all(item.annotations.destructive_hint is False for item in result.tools))
            self.assertTrue(all(item.annotations.idempotent_hint == (item.name != "cnc_account_login") for item in result.tools))
            self.assertTrue(all(item.annotations.open_world_hint == (item.name in {"cnc_account_login", "cnc_part_config_quote"}) for item in result.tools))
            self.assertTrue(all(item.input_schema["additionalProperties"] is False for item in result.tools))
            decrypt_tool = next(item for item in result.tools if item.name == "cnc_account_decrypt_password")
            self.assertEqual(decrypt_tool.input_schema["required"], ["username"])
            self.assertNotIn("id", decrypt_tool.input_schema["properties"])

    async def test_read_result_uses_public_output_schema_and_preserves_query_models(self):
        page = {"items": [{**ACCOUNT, "password": SECRET, "credential_ciphertext": ACCOUNT["password"].encode(), "extra": SECRET}], "total": 1}
        with patch.object(tools.CncAccountService, "page", AsyncMock(return_value=page)) as read:
            async with self.running() as http, self.session(http) as client:
                result = await client.call_tool("cnc_account_list", {"page_size": 5, "search": {"enabled": True}})
        self.assertEqual(result.structured_content["items"][0], ACCOUNT)
        self.assertNotIn(SECRET, result.model_dump_json())
        self.assertNotIn("extra", result.structured_content["items"][0])
        self.assertEqual(read.await_args.kwargs["page_size"], 5)
        self.assertIsInstance(read.await_args.kwargs["search"], tools.AccountSearch)
        self.assertTrue(read.await_args.kwargs["search"].enabled)

    async def test_missing_bearer_and_query_tokens_fail_before_storage(self):
        async with self.running() as http:
            for header in ["", "Basic synthetic", "Bearer "]:
                response = await http.post("/mcp/?token=synthetic-query-token", headers={"Authorization": header}, json={})
                self.assertEqual(response.status_code, 401)
                self.assertIn("WWW-Authenticate", response.headers)
        self.assertEqual(self.sessions.commits, 0)

    async def test_actual_auth_rejects_invalid_expired_refresh_revoked_and_deleted_users(self):
        expired = create_access_token(JWTPayloadSchema(sub="first-session", exp=datetime.now(UTC) - timedelta(seconds=1)))
        refresh = create_access_token(JWTPayloadSchema(sub="first-session", exp=datetime.now(UTC) + timedelta(hours=1), is_refresh=True))
        absent = create_access_token(JWTPayloadSchema(sub="absent-session", exp=datetime.now(UTC) + timedelta(hours=1)))
        disabled = await self.issue("disabled-session", 7, user_status=1)
        async with self.running() as http:
            for token in ["invalid-synthetic-token", expired, refresh, absent, disabled]:
                response = await self.rpc(http, "tools/list", Authorization=f"Bearer {token}")
                self.assertEqual(response.status_code, 401)
            self.sessions.users.clear()
            self.assertEqual((await self.rpc(http, "tools/list")).status_code, 401)

    async def test_revocation_and_permission_changes_apply_to_the_next_request(self):
        async with self.running() as http, self.session(http) as client:
            self.assertEqual({item.name for item in (await client.list_tools()).tools}, ALL_TOOLS)
            await self.issue("first-session", 7, permissions=["module_cnc:cnc_part:query"])
            self.assertEqual([item.name for item in (await client.list_tools()).tools], ["cnc_part_list"])
            with self.assertRaises(MCPError):
                await client.call_tool("cnc_account_detail", {"id": 31})
            await self.redis.delete("user_session:first-session")
            self.assertEqual((await self.rpc(http, "tools/list")).status_code, 401)

    async def test_mutations_and_other_modules_are_unconditionally_unavailable(self):
        mutation_permissions = [f"module_cnc:{module}:{action}" for module in ("cnc_account", "cnc_part", "cnc_part_config") for action in ("create", "update", "delete", "patch")]
        await self.issue("first-session", 7, permissions=[*ALL_PERMISSIONS, *mutation_permissions])
        with patch.object(tools.CncAccountService, "create", AsyncMock()) as create:
            for superuser in (False, True):
                self.sessions.users[7].is_superuser = superuser
                async with self.running() as http:
                    for name in (*MUTATION_TOOLS, "cnc_part_quote", "cnc_quote_run", "cnc_platform_list", SECRET):
                        response = await self.rpc(http, "tools/call", {"name": name, "arguments": {"id": 31, "ids": [31], "data": {"username": "x", "password": SECRET}}})
                        self.assertEqual(response.json()["error"]["code"], -32602)
                        self.assertNotIn(SECRET, response.text)
        create.assert_not_awaited()

    async def test_stale_write_setting_cannot_expand_catalog_or_enable_mutations(self):
        with patch.dict(os.environ, {"MCP_ALLOW_WRITES": "true"}):
            config = Settings(_env_file=None, MCP_ENABLED=True, MCP_ALLOW_WRITES=True)
        self.assertNotIn("MCP_ALLOW_WRITES", Settings.model_fields)
        self.assertFalse(hasattr(config, "MCP_ALLOW_WRITES"))
        self.sessions.users[7].is_superuser = True
        async with self.running(config=config) as http:
            self.assertEqual({item["name"] for item in (await self.rpc(http, "tools/list")).json()["result"]["tools"]}, ALL_TOOLS)
            for name in MUTATION_TOOLS:
                response = await self.rpc(http, "tools/call", {"name": name, "arguments": {"data": {"username": "x", "password": SECRET}}})
                self.assertEqual(response.json()["error"]["code"], -32602)
                self.assertNotIn(SECRET, response.text)

    async def test_part_queries_preserve_output_and_existing_filter_models(self):
        with (
            patch.object(tools.CncPartService, "detail", AsyncMock(return_value=PART)) as detail,
            patch.object(tools.CncPartService, "page", AsyncMock(return_value={"items": [PART], "total": 1})) as page,
        ):
            async with self.running() as http, self.session(http) as client:
                result = await client.call_tool("cnc_part_detail", {"id": 42})
                listed = await client.call_tool("cnc_part_list", {"search": {"upload_authorized": False}, "order_by": [{"id": "desc"}]})
        self.assertFalse(result.structured_content["upload_authorized"])
        self.assertEqual(listed.structured_content["items"][0], {"file_name": "synthetic.step", "file_path": "/drawings/synthetic.step"})
        self.assertNotIn("id", listed.structured_content["items"][0])
        detail.assert_awaited_once_with(id=42)
        self.assertIsInstance(page.await_args.kwargs["search"], tools.PartSearch)
        self.assertFalse(page.await_args.kwargs["search"].upload_authorized)
        self.assertEqual(page.await_args.kwargs["order_by"], [{"id": "desc"}])

    async def test_invalid_arguments_never_echo_credentials_or_reach_service(self):
        cases = [
            ("cnc_account_login", {"id": 31, "password": SECRET}),
            ("cnc_account_login", {"id": 31, "action": "status"}),
            ("cnc_account_login", {"id": 31, "session_id": "synthetic-session-reference-12345"}),
            ("cnc_account_login", {"id": 31, "action": "input"}),
            ("cnc_account_login", {"id": 31, "action": "close", "session_id": SECRET + "/"}),
            ("cnc_account_decrypt_password", {"id": True}),
            ("cnc_account_decrypt_password", {"id": 31}),
            ("cnc_account_decrypt_password", {"username": ""}),
            ("cnc_account_decrypt_password", {"username": "   "}),
            ("cnc_account_decrypt_password", {"username": True}),
            ("cnc_account_decrypt_password", {"username": "x" * 65}),
            ("cnc_account_decrypt_password", {"username": ACCOUNT["username"], "ciphertext": SECRET}),
            ("cnc_account_detail", {"id": 31, "password": SECRET}),
            ("cnc_account_list", {"search": {"password": SECRET}}),
            ("cnc_part_list", {"search": {"extra": SECRET}}),
            ("cnc_account_detail", {"id": True}),
            ("cnc_account_list", {"page_no": 0}),
            ("cnc_part_list", {"order_by": [{"id": "invalid"}]}),
            ("cnc_part_detail", {"id": 0}),
            ("cnc_part_list", {"page_size": 101}),
        ]
        with patch.object(tools.CncAccountService, "detail", AsyncMock()) as detail:
            async with self.running() as http, self.session(http) as client:
                for name, args in cases:
                    result = await client.call_tool(name, args)
                    self.assertTrue(result.is_error)
                    self.assertNotIn(SECRET, result.model_dump_json())
        detail.assert_not_awaited()
        self.assertNotIn(SECRET, "".join(self.messages))

    async def test_malformed_envelopes_and_params_are_private_for_legacy_and_modern_protocols(self):
        bodies = [
            {"jsonrpc": "2.0", "id": {}, "method": "tools/call", "params": {"password": SECRET}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": [SECRET], "arguments": {"password": SECRET}}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "cnc_account_detail", "arguments": [SECRET]}},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"password": SECRET}},
        ]
        async with self.running() as http:
            for version in ["2025-11-25", "2026-07-28"]:
                for body in bodies:
                    payload = {
                        **body,
                        "params": {**body["params"], "_meta": {PROTOCOL_VERSION_META_KEY: version, CLIENT_INFO_META_KEY: {"name": "synthetic-test", "version": "1"}, CLIENT_CAPABILITIES_META_KEY: {}}},
                    }
                    response = await http.post("/mcp/", json=payload, headers={"Accept": "application/json, text/event-stream", "Mcp-Protocol-Version": version, "Mcp-Method": "tools/call"})
                    self.assertIn("application/json", response.headers.get("content-type", ""), (version, bodies.index(body), response.status_code))
                    self.assertIn("error", response.json())
                    self.assertNotIn(SECRET, response.text)
                    if body["id"] == {}:
                        self.assertIsNone(response.json()["id"])
        self.assertNotIn(SECRET, "".join(self.messages))

    async def test_query_business_and_storage_failures_are_private(self):
        for fault in [CustomException(msg=SECRET), RuntimeError(SECRET)]:
            with patch.object(tools.CncAccountService, "detail", AsyncMock(side_effect=fault)):
                async with self.running() as http, self.session(http) as client:
                    result = await client.call_tool("cnc_account_detail", {"id": 31})
                    self.assertTrue(result.is_error)
                    self.assertNotIn(SECRET, result.model_dump_json())
        self.assertGreaterEqual(self.sessions.rollbacks, 2)
        self.assertNotIn(SECRET, "".join(self.messages))

    async def test_authentication_infrastructure_failure_is_unavailable(self):
        with patch.object(server, "_authenticate", AsyncMock(side_effect=RuntimeError(SECRET))):
            async with self.running() as http:
                result = await self.rpc(http, "tools/list")
        self.assertEqual(result.status_code, 503)
        self.assertNotIn(SECRET, result.text)
        self.assertNotIn(SECRET, "".join(self.messages))

    async def test_invalid_host_origin_and_oversized_body_fail_closed(self):
        async with self.running() as http:
            self.assertEqual((await self.rpc(http, "tools/list", Host="untrusted.example.test")).status_code, 421)
            self.assertEqual((await self.rpc(http, "tools/list", Origin="https://untrusted.example.test")).status_code, 403)
            large = await http.post("/mcp/", content=b"x" * (server.MAX_REQUEST_BYTES + 1))
            self.assertEqual(large.status_code, 413)

    async def test_concurrent_requests_keep_user_permissions_separate(self):
        other = await self.issue("second-session", 9, permissions=["module_cnc:cnc_part:query"])
        await self.issue("first-session", 7, permissions=["module_cnc:cnc_account:detail"])
        async with self.running() as http:
            first, second = await asyncio.gather(self.rpc(http, "tools/list"), self.rpc(http, "tools/list", Authorization=f"Bearer {other}"))
        self.assertEqual([item["name"] for item in first.json()["result"]["tools"]], ["cnc_account_detail"])
        self.assertEqual([item["name"] for item in second.json()["result"]["tools"]], ["cnc_part_list"])

    async def test_modern_official_client_discovers_and_calls_all_four_queries_over_http(self):
        with (
            patch.object(tools.CncPartService, "detail", AsyncMock(return_value=PART)),
            patch.object(tools.CncPartService, "page", AsyncMock(return_value={"items": [PART], "total": 1})),
            patch.object(tools.CncAccountService, "detail", AsyncMock(return_value=RAW_ACCOUNT)),
            patch.object(tools.CncAccountService, "page", AsyncMock(return_value={"items": [RAW_ACCOUNT], "total": 1})),
        ):
            async with self.running() as http, Client(streamable_http_client("http://localhost/api/v1/mcp/", http_client=http), mode="2026-07-28") as client:
                for name, arguments in [("cnc_account_list", {}), ("cnc_account_detail", {"id": 31}), ("cnc_part_list", {}), ("cnc_part_detail", {"id": 42})]:
                    result = await client.call_tool(name, arguments)
                    self.assertFalse(result.is_error)
                    self.assertNotIn(SECRET, result.model_dump_json())

    async def test_direct_and_prefixed_paths_support_queries_and_reject_subpaths(self):
        async with self.running() as http:
            for path in ["/mcp/", "/api/v1/mcp/"]:
                response = await self.rpc(http, "tools/list", path=path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual({item["name"] for item in response.json()["result"]["tools"]}, ALL_TOOLS)
            self.assertEqual((await self.rpc(http, "tools/list", path="/api/v1/mcp/unregistered")).status_code, 404)

    async def test_disabled_registration_and_independent_application_settings(self):
        app = FastAPI()
        with patch.object(settings, "MCP_ENABLED", False):
            register_mcp(app)
        self.assertFalse(hasattr(app.state, "cnc_mcp"))
        async with mcp_lifespan(app):
            self.assertFalse(hasattr(app.state, "cnc_mcp"))
        async with self.running() as first:
            first_server = self.active_server
            second_config = settings.model_copy(update={"MCP_ENABLED": True, "MCP_ALLOWED_HOSTS": ["localhost", "other.example.test"]})
            async with self.running(config=second_config) as second:
                self.assertIsNot(first_server, self.active_server)
                self.assertEqual((await self.rpc(second, "tools/list", Host="other.example.test")).status_code, 200)
            self.assertEqual((await self.rpc(first, "tools/list", Host="other.example.test")).status_code, 421)
            self.assertEqual(len((await self.rpc(first, "tools/list")).json()["result"]["tools"]), len(ALL_TOOLS))

    async def test_login_and_decryption_require_update_permission_on_discovery_and_call(self):
        await self.issue("first-session", 7, permissions=["module_cnc:cnc_account:query", "module_cnc:cnc_account:detail"])
        with patch.object(tools, "login_action", AsyncMock()) as login, patch.object(tools.CncAccountService, "credential_account_by_username", AsyncMock()) as lookup:
            async with self.running() as http, self.session(http) as client:
                self.assertEqual({item.name for item in (await client.list_tools()).tools}, {"cnc_account_list", "cnc_account_detail"})
                for name, arguments in (("cnc_account_login", {"id": 31}), ("cnc_account_decrypt_password", {"username": ACCOUNT["username"]})):
                    with self.assertRaises(MCPError):
                        await client.call_tool(name, arguments)
        login.assert_not_awaited()
        lookup.assert_not_awaited()

    async def test_login_uses_shared_action_and_never_returns_password(self):
        session_id = "synthetic-session-reference-12345"
        snapshot = SimpleNamespace(id=31, actor_id=7, password=SECRET)
        view = LoginView(
            session_id=session_id, account_id=31, platform_name="Synthetic", username="sy***", status="WAITING_HUMAN", reason="CHALLENGE_REQUIRED", expires_at=datetime.now(UTC) + timedelta(minutes=30)
        )
        manager = SimpleNamespace(
            repository=SimpleNamespace(load=AsyncMock(return_value=snapshot)), start=AsyncMock(return_value=view), command=AsyncMock(return_value=view), revoke=AsyncMock(), accounts={}
        )
        with patch.object(actions, "get_login_manager", return_value=manager):
            async with self.running() as http, self.session(http) as client:
                result = await client.call_tool("cnc_account_login", {"id": 31})
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content["status"], "WAITING_HUMAN")
                self.assertNotIn(SECRET, result.model_dump_json())
                for action in ("status", "verify", "close"):
                    result = await client.call_tool("cnc_account_login", {"id": 31, "action": action, "session_id": session_id})
                    self.assertFalse(result.is_error)
                manager.repository.load.side_effect = LoginError("ACCOUNT_DISABLED")
                manager.accounts[31] = SimpleNamespace(account=snapshot)
                rejected = await client.call_tool("cnc_account_login", {"id": 31})
                self.assertTrue(rejected.is_error)
        manager.start.assert_awaited_once_with(snapshot)
        self.assertEqual(manager.repository.load.await_count, 5)
        self.assertEqual([call.args[2] for call in manager.command.await_args_list], ["status", "verify", "close"])
        manager.revoke.assert_awaited_once_with(31)
        self.assertNotIn(SECRET, "".join(self.messages))

    async def test_queries_encrypt_legacy_password_without_decrypting(self):
        raw = {**ACCOUNT, "password": SECRET}
        with patch.object(tools.CncAccountService, "detail", AsyncMock(return_value=raw)), patch.object(tools, "read_credentials", side_effect=AssertionError("query must not decrypt")):
            async with self.running() as http, self.session(http) as client:
                result = await client.call_tool("cnc_account_detail", {"id": 31})
        self.assertFalse(result.is_error)
        cipher = result.structured_content["password"]
        self.assertNotIn(SECRET, result.model_dump_json())
        self.assertEqual(json.loads(CryptoUtil.decrypt(cipher))["password"], SECRET)

    async def test_decryption_failure_does_not_echo_or_log_credentials(self):
        account = SimpleNamespace(username=ACCOUNT["username"], credential_ciphertext=seal_credentials("wrong-user", SECRET), password="")
        with patch.object(tools.CncAccountService, "credential_account_by_username", AsyncMock(return_value=account)):
            async with self.running() as http, self.session(http) as client:
                result = await client.call_tool("cnc_account_decrypt_password", {"username": ACCOUNT["username"]})
        self.assertTrue(result.is_error)
        self.assertNotIn(SECRET, result.model_dump_json())
        self.assertNotIn(SECRET, "".join(self.messages))

    async def test_explicit_decryption_returns_plaintext_without_server_logging(self):
        account = SimpleNamespace(id=31, username=ACCOUNT["username"], credential_ciphertext=RAW_ACCOUNT["credential_ciphertext"], password="")
        with patch.object(tools.CncAccountService, "credential_account_by_username", AsyncMock(return_value=account)) as lookup:
            async with self.running() as http, self.session(http) as client:
                result = await client.call_tool("cnc_account_decrypt_password", {"username": ACCOUNT["username"]})
        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content, {"id": 31, "username": ACCOUNT["username"], "password": SECRET})
        self.assertEqual(json.loads(result.content[0].text), result.structured_content)
        lookup.assert_awaited_once_with(ACCOUNT["username"])
        self.assertNotIn(SECRET, "".join(self.messages))
    async def test_part_config_queries_and_quote_tool(self):
        sample_config = {
            "id": 10,
            "name": "JLC-Test-Part",
            "site_type": 2,
            "material": "铝合金-6061",
            "quantity": 1,
            "surface_finish": "喷砂+普通阳极氧化 - 本色 - 哑光",
            "extra_params": {"tolerance": "GB/T 1804-2000 m级"},
            "enabled": True,
            "part_id": 42,
        }
        quote_result = {
            "config_id": 10,
            "config_name": "JLC-Test-Part",
            "platform": "jlc_cnc_cn",
            "quote_status": "REFERENCE_ESTIMATE",
            "unit_price": "133.86",
            "selected_lead_time": {"lead_days": 6, "total_price": "133.86"},
        }
        with (
            patch.object(tools.CncPartConfigService, "detail", AsyncMock(return_value=sample_config)),
            patch.object(tools.CncPartConfigService, "page", AsyncMock(return_value={"items": [sample_config], "total": 1})),
            patch.object(tools.CncPartConfigService, "quote", AsyncMock(return_value=quote_result)),
        ):
            async with self.running() as http, self.session(http) as client:
                detail_res = await client.call_tool("cnc_part_config_detail", {"id": 10})
                self.assertEqual(detail_res.structured_content["name"], "JLC-Test-Part")
                self.assertEqual(detail_res.structured_content["site_type"], 2)

                list_res = await client.call_tool("cnc_part_config_list", {"page_size": 10, "search": {"site_type": 2}})
                self.assertEqual(list_res.structured_content["items"][0]["name"], "JLC-Test-Part")

                quote_res = await client.call_tool("cnc_part_config_quote", {"config_id": 10, "lead_time": "标准"})
                self.assertEqual(quote_res.structured_content["quote_status"], "REFERENCE_ESTIMATE")
                self.assertEqual(quote_res.structured_content["unit_price"], "133.86")

