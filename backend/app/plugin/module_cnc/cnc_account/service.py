"""Account ACL, encrypted credentials and secret-free import/export."""

from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema
from app.core.exceptions import CustomException
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.credentials import read_credentials, seal_credentials
from app.modules.cnc.login.runtime import get_login_manager
from app.utils.common_util import search_to_dict
from app.utils.excel_util import ExcelUtil

from .crud import CncAccountCRUD
from .schema import CncAccountCreateSchema, CncAccountOutSchema, CncAccountQueryParam, CncAccountUpdateSchema

EXPORT_FIELDS = {
    "id": "ID",
    "platform_id": "平台ID",
    "platform_name": "平台名称",
    "alias": "别名",
    "username": "账号",
    "login_method": "登录方式",
    "enabled": "启用",
    "session_status": "会话状态",
    "last_verified_at": "验证时间",
}
IMPORT_FIELDS = {"平台ID": "platform_id", "别名": "alias", "账号": "username", "密码": "password", "登录方式": "login_method", "启用": "enabled"}


class CncAccountService:
    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    def _search(self, search=None):
        values = search_to_dict(search, {}) or {}
        if not self.auth.user.is_superuser:
            values["created_id"] = ("eq", self.auth.user.id)
        return values

    async def _account(self, id):
        account = await CncAccountCRUD(self.auth, self.db).get(id=id, preload=["platform"])
        if not account or (not self.auth.user.is_superuser and account.created_id != self.auth.user.id):
            raise CustomException(msg="该数据不存在或无权访问")
        return account

    async def detail(self, id: int) -> CncAccountOutSchema:
        return CncAccountOutSchema.model_validate(await self._account(id))

    async def get_list(self, search: CncAccountQueryParam | None = None, order_by=None) -> list[CncAccountOutSchema]:
        rows = await CncAccountCRUD(self.auth, self.db).get_list(search=self._search(search), order_by=order_by, preload=["platform"])
        return [CncAccountOutSchema.model_validate(row) for row in rows]

    async def page(self, page_no: int, page_size: int, search=None, order_by=None) -> PageResultSchema[CncAccountOutSchema]:
        return await CncAccountCRUD(self.auth, self.db).page(
            offset=(page_no - 1) * page_size, limit=page_size, order_by=order_by or [{"id": "asc"}], search=self._search(search), out_schema=CncAccountOutSchema, preload=["platform"]
        )

    async def create(self, data: CncAccountCreateSchema) -> CncAccountOutSchema:
        values = data.model_dump()
        password = values.pop("password")
        values.update(password="", credential_ciphertext=seal_credentials(data.username, password), session_status="UNKNOWN")
        row = await CncAccountCRUD(self.auth, self.db).create(data=values)
        return await self.detail(row.id)

    async def update(self, id: int, data: CncAccountUpdateSchema) -> CncAccountOutSchema:
        account = await self._account(id)
        values = data.model_dump(exclude_unset=True, exclude_none=True)
        password = values.pop("password", None)
        new_username = values.get("username", account.username)
        changed = any(key in values and values[key] != getattr(account, key) for key in ("username", "platform_id", "login_method")) or bool(password)
        if password or changed or (not account.credential_ciphertext and account.password):
            try:
                _, previous = read_credentials(account)
            except LoginError:
                if not password:
                    raise CustomException(msg="原凭据不可用，请重新填写密码") from None
                previous = ""
            values.update(password="", credential_ciphertext=seal_credentials(new_username, password or previous))
        if changed or values.get("enabled") is False:
            await get_login_manager().revoke(id)
            values.update(session_ciphertext=None, session_status="REVOKED", last_verified_at=None, auth_expires_at=None, account_fingerprint=None, session_version=(account.session_version or 0) + 1)
        await CncAccountCRUD(self.auth, self.db).update(id=id, data=values)
        return await self.detail(id)

    async def delete(self, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除对象不能为空")
        for account_id in ids:
            await self._account(account_id)
            await get_login_manager().revoke(account_id)
        await CncAccountCRUD(self.auth, self.db).delete(ids=ids)

    async def set_available(self, data: BatchSetAvailable) -> None:
        for account_id in data.ids:
            await self.update(account_id, CncAccountUpdateSchema.model_validate({"enabled": data.status == 0}))

    @staticmethod
    async def batch_export(obj_list: list[dict[str, Any]]) -> bytes:
        rows = [{key: item.get(key) for key in EXPORT_FIELDS} for item in obj_list]
        return await ExcelUtil.aexport_list2excel(list_data=rows, mapping_dict=EXPORT_FIELDS)

    async def batch_import(self, file: UploadFile, update_support: bool = False) -> str:
        try:
            rows = await ExcelUtil.aread_excel_to_dicts(await file.read())
        except Exception:
            raise CustomException(msg="导入文件无法读取") from None
        finally:
            await file.close()
        if not rows or "账号" not in rows[0] or "密码" not in rows[0]:
            raise CustomException(msg="导入文件须包含账号和密码列")
        success = 0
        errors = []
        for index, row in enumerate(rows, 1):
            try:
                values = {field: row[header] for header, field in IMPORT_FIELDS.items() if row.get(header) is not None}
                data = CncAccountCreateSchema.model_validate(values)
                async with self.db.begin_nested():
                    await self.create(data)
                success += 1
            except Exception:
                errors.append(f"第 {index} 行校验或保存失败")
        return f"成功导入 {success} 条数据" + ("；" + "；".join(errors) if errors else "")

    @staticmethod
    def import_template_download() -> bytes:
        return ExcelUtil.get_excel_template(header_list=list(IMPORT_FIELDS), selector_header_list=[], option_list=[])
