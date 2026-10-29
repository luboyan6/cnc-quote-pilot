"""Actual SQLite query services, data scopes and unconditional mutation denial."""

import json
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
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.config.setting import settings
from app.core.base_model import MappedBase
from app.core.base_schema import JWTPayloadSchema
from app.core.security import create_access_token
from app.modules.cnc.cnc_account.model import CncAccountModel
from app.modules.cnc.cnc_part.model import CncPartModel
from app.modules.cnc.cnc_platform.model import CncPlatformModel
from app.modules.cnc.login import actions
from app.modules.cnc.login.contracts import LoginView
from app.modules.cnc.login.credentials import seal_credentials
from app.modules.cnc.login.repository import LoginRepository
from app.modules.cnc.mcp import mcp_lifespan, register_mcp, server, tools
from app.modules.system.dept.model import DeptModel
from app.modules.system.menu.model import MenuModel
from app.modules.system.position.model import PositionModel
from app.modules.system.role.model import RoleDeptsModel, RoleMenusModel, RoleModel
from app.modules.system.user.model import UserModel, UserPositionsModel, UserRolesModel
from app.utils.crypto_util import CryptoUtil

SECRET = "synthetic-database-credential-private"
MUTATION_TOOLS = tuple(f"{module}_{operation}" for module in ("cnc_account", "cnc_part", "cnc_part_config") for operation in ("create", "update", "delete", "set_status"))


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(column, compiler, **kwargs):
    """The real account model uses PostgreSQL JSONB; SQLite is an isolated test dialect."""
    return "JSON"


class McpDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", hide_parameters=True)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        models = [DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel, RoleMenusModel, UserPositionsModel, UserRolesModel, CncPlatformModel, CncAccountModel, CncPartModel]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
        async with self.sessions() as db, db.begin():
            db.add_all([UserModel(id=7, username="first", password="synthetic-hash", name="First"), UserModel(id=9, username="second", password="synthetic-hash", name="Second")])
            db.add(RoleModel(id=1, name="Self", code="mcp-self", data_scope=1))
            db.add(UserRolesModel(user_id=7, role_id=1))
            db.add(CncPlatformModel(id=1, name="Synthetic platform", login_url="https://platform.test/login", quote_entry_url="https://platform.test/quote"))
            db.add_all(
                [
                    CncPartModel(id=42, file_name="first.step", file_path="/drawings/first.step", created_id=7, upload_authorized=False),
                    CncPartModel(id=43, file_name="second.step", file_path="/drawings/second.step", created_id=9, upload_authorized=False),
                ]
            )
            db.add_all(
                [
                    CncAccountModel(id=31, platform_id=1, username="first-account", password="", credential_ciphertext=seal_credentials("first-account", SECRET), created_id=7),
                    CncAccountModel(id=32, platform_id=1, username="second-account", password="", credential_ciphertext=seal_credentials("second-account", SECRET), created_id=9),
                ]
            )
        self.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        await self.redis.set("user_session:mcp-db", json.dumps({"session_id": "mcp-db", "user_id": 7, "user_name": "first", "permissions": [item.permission for item in tools.TOOLS]}), ex=3600)
        self.token = create_access_token(JWTPayloadSchema(sub="mcp-db", exp=datetime.now(UTC) + timedelta(hours=1)))
        self.patches = [patch.object(server, "async_db_session", self.sessions), patch.object(settings, "TOKEN_SLIDING_EXPIRE", False)]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()
        await self.redis.aclose()
        await self.engine.dispose()

    @asynccontextmanager
    async def running(self):
        app = FastAPI(root_path="/api/v1")
        app.state.redis = self.redis
        with patch.object(settings, "MCP_ENABLED", True):
            register_mcp(app)
        async with mcp_lifespan(app), httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://localhost", headers={"Authorization": f"Bearer {self.token}"}) as client:
            yield client

    async def rpc(self, client, name, arguments):
        response = await client.post(
            "/api/v1/mcp/",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
            headers={"Accept": "application/json, text/event-stream", "Mcp-Protocol-Version": "2025-11-25"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    async def call(self, client, name, arguments):
        return (await self.rpc(client, name, arguments))["result"]

    async def snapshot_business_rows(self):
        async with self.sessions() as db:
            accounts = (await db.execute(select(CncAccountModel.__table__).order_by(CncAccountModel.id))).all()
            parts = (await db.execute(select(CncPartModel.__table__).order_by(CncPartModel.id))).all()
        return accounts, parts

    async def test_real_services_keep_account_ownership_and_drawing_role_scope(self):
        async with self.running() as client:
            accounts = await self.call(client, "cnc_account_list", {})
            parts = await self.call(client, "cnc_part_list", {})
            self.assertEqual([item["username"] for item in accounts["structuredContent"]["items"]], ["first-account"])
            self.assertEqual(
                accounts["structuredContent"]["items"][0],
                {
                    "id": 31,
                    "username": "first-account",
                    "password": accounts["structuredContent"]["items"][0]["password"],
                    "platform_name": "Synthetic platform",
                    "login_url": "https://platform.test/login",
                    "quote_url": "https://platform.test/quote",
                },
            )
            self.assertNotIn(SECRET, json.dumps(accounts))
            self.assertEqual(json.loads(CryptoUtil.decrypt(accounts["structuredContent"]["items"][0]["password"]))["password"], SECRET)
            self.assertEqual([item["file_name"] for item in parts["structuredContent"]["items"]], ["first.step"])
            self.assertEqual(parts["structuredContent"]["items"][0], {"file_name": "first.step", "file_path": "/drawings/first.step"})
            self.assertNotIn("id", parts["structuredContent"]["items"][0])
            account = await self.call(client, "cnc_account_detail", {"id": 31})
            part = await self.call(client, "cnc_part_detail", {"id": 42})
            self.assertEqual(
                account["structuredContent"],
                {
                    "id": 31,
                    "username": "first-account",
                    "password": accounts["structuredContent"]["items"][0]["password"],
                    "platform_name": "Synthetic platform",
                    "login_url": "https://platform.test/login",
                    "quote_url": "https://platform.test/quote",
                },
            )
            self.assertNotIn(SECRET, json.dumps(account))
            self.assertEqual(part["structuredContent"]["file_name"], "first.step")
            self.assertFalse(part["structuredContent"]["upload_authorized"])
            self.assertNotIn("credential_ciphertext", account["structuredContent"])
            self.assertNotIn("session_ciphertext", account["structuredContent"])
            for name, id_ in [("cnc_account_detail", 32), ("cnc_part_detail", 43)]:
                result = await self.call(client, name, {"id": id_})
                self.assertTrue(result["isError"])
            narrowed = await self.call(client, "cnc_part_list", {"search": {"created_id": 9}})
            self.assertEqual(narrowed["structuredContent"]["items"], [])

    async def test_current_role_scope_expands_drawings_but_account_owner_rule_remains(self):
        async with self.sessions() as db, db.begin():
            await db.execute(update(RoleModel).where(RoleModel.id == 1).values(data_scope=3))
        async with self.running() as client:
            accounts = await self.call(client, "cnc_account_list", {})
            parts = await self.call(client, "cnc_part_list", {})
            self.assertEqual([item["username"] for item in accounts["structuredContent"]["items"]], ["first-account"])
            self.assertEqual([item["file_name"] for item in parts["structuredContent"]["items"]], ["first.step", "second.step"])
            shared_part = await self.call(client, "cnc_part_detail", {"id": 43})
            other_account = await self.call(client, "cnc_account_detail", {"id": 32})
        self.assertEqual(shared_part["structuredContent"]["file_name"], "second.step")
        self.assertTrue(other_account["isError"])

    async def test_mutation_attempts_leave_all_business_rows_unchanged_for_all_users(self):
        baseline = await self.snapshot_business_rows()
        session = json.loads(await self.redis.get("user_session:mcp-db"))
        session["permissions"].extend(f"module_cnc:{module}:{action}" for module in ("cnc_account", "cnc_part") for action in ("create", "update", "delete", "patch"))
        await self.redis.set("user_session:mcp-db", json.dumps(session), ex=3600)
        for superuser in (False, True):
            async with self.sessions() as db, db.begin():
                await db.execute(update(UserModel).where(UserModel.id == 7).values(is_superuser=superuser))
            async with self.running() as client:
                for name in (*MUTATION_TOOLS, "cnc_part_quote"):
                    result = await self.rpc(
                        client, name, {"id": 31, "ids": [31, 42], "status": 1, "data": {"username": "changed", "password": SECRET, "file_name": "changed.step", "upload_authorized": True}}
                    )
                    self.assertEqual(result["error"]["code"], -32602)
                    self.assertNotIn(SECRET, json.dumps(result))
            self.assertEqual(await self.snapshot_business_rows(), baseline)

    async def test_decrypts_stored_password_only_for_permitted_account(self):
        baseline = await self.snapshot_business_rows()
        async with self.running() as client:
            result = await self.call(client, "cnc_account_decrypt_password", {"username": "first-account"})
            self.assertEqual(result["structuredContent"], {"id": 31, "username": "first-account", "password": SECRET})
            for username in ("second-account", "missing-account", "first", "%", "first-account%", "FIRST-ACCOUNT"):
                rejected = await self.call(client, "cnc_account_decrypt_password", {"username": username})
                self.assertTrue(rejected["isError"])
                self.assertNotIn(SECRET, json.dumps(rejected))
        self.assertEqual(await self.snapshot_business_rows(), baseline)

    async def test_decryption_ignores_inaccessible_same_username_but_rejects_ambiguity(self):
        async with self.sessions() as db, db.begin():
            await db.execute(update(CncAccountModel).where(CncAccountModel.id == 32).values(username="first-account", credential_ciphertext=seal_credentials("first-account", "other-owner-secret")))
        async with self.running() as client:
            result = await self.call(client, "cnc_account_decrypt_password", {"username": "first-account"})
            self.assertEqual(result["structuredContent"]["password"], SECRET)
        async with self.sessions() as db, db.begin():
            db.add(CncAccountModel(id=33, platform_id=1, username="first-account", password="", credential_ciphertext=seal_credentials("first-account", "duplicate-account-secret"), created_id=7))
        async with self.running() as client:
            result = await self.call(client, "cnc_account_decrypt_password", {"username": "first-account"})
            self.assertTrue(result["isError"])
            for password in (SECRET, "other-owner-secret", "duplicate-account-secret"):
                self.assertNotIn(password, json.dumps(result))

    async def test_decryption_excludes_deleted_accounts(self):
        async with self.sessions() as db, db.begin():
            await db.execute(update(CncAccountModel).where(CncAccountModel.id == 31).values(is_deleted=True))
        async with self.running() as client:
            result = await self.call(client, "cnc_account_decrypt_password", {"username": "first-account"})
            self.assertTrue(result["isError"])
            self.assertNotIn(SECRET, json.dumps(result))

    async def test_login_loads_and_decrypts_credentials_without_exposing_them(self):
        view = LoginView(
            session_id="synthetic-session-reference-12345",
            account_id=31,
            platform_name="Synthetic platform",
            username="fi***",
            status="STARTING",
            reason="BROWSER_STARTING",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        manager = SimpleNamespace(repository=LoginRepository(self.sessions), start=AsyncMock(return_value=view), accounts={}, revoke=AsyncMock())
        with patch.object(actions, "get_login_manager", return_value=manager):
            async with self.running() as client:
                result = await self.call(client, "cnc_account_login", {"id": 31})
                self.assertEqual(result["structuredContent"]["status"], "STARTING")
                self.assertNotIn(SECRET, json.dumps(result))
                self.assertEqual(manager.start.await_args.args[0].password, SECRET)
                self.assertEqual(manager.start.await_args.args[0].actor_id, 7)
                for account_id in (32, 999):
                    rejected = await self.call(client, "cnc_account_login", {"id": account_id})
                    self.assertTrue(rejected["isError"])
        manager.start.assert_awaited_once()
