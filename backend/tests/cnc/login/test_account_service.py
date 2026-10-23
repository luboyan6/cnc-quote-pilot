"""Account write/export contracts with the real service and isolated CRUD."""

import sys
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.base_schema import AuthSchema, BatchSetAvailable, CoreUserSchema
from app.core.exceptions import CustomException
from app.modules.cnc.login.credentials import read_credentials, seal_credentials
from app.plugin.module_cnc.cnc_account import service
from app.plugin.module_cnc.cnc_account.schema import CncAccountCreateSchema, CncAccountUpdateSchema


class MemoryCrud:
    def __init__(self):
        self.values = []
        self.account = SimpleNamespace(
            id=31,
            created_id=7,
            username="synthetic",
            password="",
            credential_ciphertext=seal_credentials("synthetic", "old-synthetic-password"),
            session_ciphertext=b"private-state",
            session_status="VALID",
            session_version=1,
            enabled=True,
            platform_id=2,
            login_method="PASSWORD",
        )

    async def get(self, **kwargs):
        return self.account

    async def create(self, data):
        self.values.append(data)
        for key, value in data.items():
            setattr(self.account, key, value)
        return self.account

    async def update(self, id, data):
        self.values.append(data)
        for key, value in data.items():
            setattr(self.account, key, value)
        return self.account


class FakeDb:
    @asynccontextmanager
    async def begin_nested(self):
        yield


class AccountServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.auth = AuthSchema(user=CoreUserSchema(id=7, is_superuser=False))
        self.crud = MemoryCrud()
        self.manager = SimpleNamespace(revoke=AsyncMock())
        self.patches = [patch.object(service, "CncAccountCRUD", return_value=self.crud), patch.object(service, "get_login_manager", return_value=self.manager)]
        for item in self.patches:
            item.start()
        self.service = service.CncAccountService(self.auth, FakeDb())

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()

    async def test_create_encrypts_secret_before_crud_and_omits_it_from_response(self):
        response = await self.service.create(CncAccountCreateSchema(platform_id=2, username="new-synthetic", password="new-synthetic-password"))
        values = self.crud.values[-1]
        self.assertEqual(values["password"], "")
        self.assertNotIn(b"new-synthetic-password", values["credential_ciphertext"])
        self.assertEqual(read_credentials(self.crud.account), ("new-synthetic", "new-synthetic-password"))
        self.assertNotIn("password", response.model_dump())
        self.assertNotIn("credential_ciphertext", response.model_dump())

    async def test_blank_password_preserves_credentials_and_existing_session(self):
        previous = self.crud.account.credential_ciphertext
        await self.service.update(31, CncAccountUpdateSchema(password="", alias="updated alias"))
        self.assertEqual(self.crud.account.credential_ciphertext, previous)
        self.assertEqual(self.crud.account.session_ciphertext, b"private-state")
        self.manager.revoke.assert_not_awaited()

    async def test_username_change_reencrypts_retained_password_and_revokes_session(self):
        await self.service.update(31, CncAccountUpdateSchema(username="changed-synthetic"))
        self.assertEqual(read_credentials(self.crud.account), ("changed-synthetic", "old-synthetic-password"))
        self.assertIsNone(self.crud.account.session_ciphertext)
        self.assertEqual(self.crud.account.session_status, "REVOKED")
        self.manager.revoke.assert_awaited_once_with(31)

    async def test_password_change_and_disable_revoke_current_browser(self):
        await self.service.update(31, CncAccountUpdateSchema(password="changed-synthetic-password"))
        self.assertEqual(read_credentials(self.crud.account)[1], "changed-synthetic-password")
        self.manager.revoke.assert_awaited_once_with(31)
        self.manager.revoke.reset_mock()
        await self.service.set_available(BatchSetAvailable(ids=[31], status=1))
        self.assertFalse(self.crud.account.enabled)
        self.manager.revoke.assert_awaited_once_with(31)

    async def test_another_owner_cannot_edit_or_read_account(self):
        self.crud.account.created_id = 99
        with self.assertRaises(CustomException):
            await self.service.update(31, CncAccountUpdateSchema(password="must-not-save"))
        with self.assertRaises(CustomException):
            await self.service.detail(31)
        self.assertFalse(self.crud.values)
        self.manager.revoke.assert_not_awaited()

    async def test_export_filters_secrets_before_excel_writer(self):
        export = AsyncMock(return_value=b"synthetic-xlsx")
        with patch.object(service.ExcelUtil, "aexport_list2excel", export):
            result = await self.service.batch_export(
                [{"id": 31, "username": "synthetic", "password": "private-password", "credential_ciphertext": "private-cipher", "session_ciphertext": "private-state"}]
            )
        self.assertEqual(result, b"synthetic-xlsx")
        rows = export.await_args.kwargs["list_data"]
        self.assertEqual(rows[0]["username"], "synthetic")
        for secret_field in ("password", "credential_ciphertext", "session_ciphertext"):
            self.assertNotIn(secret_field, rows[0])
            self.assertNotIn(secret_field, export.await_args.kwargs["mapping_dict"])


if __name__ == "__main__":
    unittest.main()
