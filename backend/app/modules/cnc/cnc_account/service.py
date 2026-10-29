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
    """
    网站账号业务服务层 (CncAccountService)

    【职责说明】
    负责 CNC 第三方平台账号的业务编排，包括：
    1. 账号列表与详情查询（内置用户归属数据隔离与平台关联预加载）；
    2. 凭据加解密隔离（入库密码加密为 credential_ciphertext，出库接口严禁明文返回）；
    3. 浏览器登录会话撤销与状态流转；
    4. 无敏感密码的 Excel 批量导入与导出。
    """

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        """
        初始化网站账号服务

        参数:
        - auth (AuthSchema): 当前请求用户的认证鉴权上下文，包含 user.id, is_superuser 等
        - db (AsyncSession): SQLAlchemy 异步数据库会话
        """
        self.auth = auth
        self.db = db

    def _search(self, search=None) -> dict[str, Any]:
        """
        构造账号查询的安全过滤条件字典

        【Agent 调用与安全说明】:
        将上层传入的 Pydantic 模型或条件字典转换为 SQLAlchemy 查询过滤字典。
        若当前用户非超级用户 (is_superuser=False)，本方法会自动强制追加 `created_id = auth.user.id`，
        从底层杜绝普通用户水平越权访问其他用户的平台账号。

        参数:
        - search (CncAccountQueryParam | dict | None): 查询参数对象或过滤字典

        返回值:
        - dict[str, Any]: 符合 CRUDBase 条件解析格式的查询字典
        """
        values = search_to_dict(search, {}) or {}
        if not self.auth.user.is_superuser:
            values["created_id"] = ("eq", self.auth.user.id)
        return values

    async def _account(self, id: int):
        """
        内部安全查询单条账号实体模型

        【Agent 逻辑说明】:
        根据主键 ID 查询账号，并通过 `preload=["platform"]` 联表预加载所属平台模型。
        若记录不存在，或当前登录用户不是超管且非该账号的创建人，统一抛出业务异常，
        避免侧信道推测其他账号的存在性。

        参数:
        - id (int): 账号主键 ID

        返回值:
        - CncAccountModel: 数据库实体对象

        异常:
        - CustomException: 当记录不存在或当前用户无权访问时抛出
        """
        account = await CncAccountCRUD(self.auth, self.db).get(id=id, preload=["platform"])
        if not account or (not self.auth.user.is_superuser and account.created_id != self.auth.user.id):
            raise CustomException(msg="该数据不存在或无权访问")
        return account

    async def detail(self, id: int, raw: bool = False) -> Any:
        """
        获取网站账号详情 (Agent 核心查询接口)

        【Agent 调用指南】:
        - 场景: 当 Agent 需要读取某个账号的配置（如登录方式、启用状态、会话有效性 session_status）以决定是否执行自动登录或发起报价时调用。
        - 安全保障: 默认返回值经过 CncAccountOutSchema 转换，密码已彻底剥离，绝不外泄明文凭据或密文密钥。
        - 附带字段: 自动携带关联平台的 platform_name、platform_login_url 以及是否配置凭据 has_credentials。

        参数:
        - id (int): 网站账号 ID
        - raw (bool): 是否返回原始 ORM 实体（供内部或 MCP 凭据解析使用）

        返回值:
        - CncAccountOutSchema | CncAccountModel: 账号对外展示数据模型或原始实体

        异常:
        - CustomException: 账号不存在或当前用户无权查看时抛出
        """
        account = await self._account(id)
        if raw:
            return account
        return CncAccountOutSchema.model_validate(account)

    async def get_list(self, search: CncAccountQueryParam | None = None, order_by=None) -> list[CncAccountOutSchema]:
        """
        按条件获取账号全量列表（不分页）

        【Agent 调用指南】:
        - 场景: 适用于账号下拉选择框、Agent 筛选可用候选账号（如根据 platform_id + enabled=True 寻找可报价账号）。
        - 数据权限: 内部自动施加租户/创建者隔离，普通用户仅能获取自己创建的账号。
        - 性能优化: 自动使用 joinedload 预加载关联的平台信息，单次 SQL 完成查询。

        参数:
        - search (CncAccountQueryParam | None): 过滤条件，支持 platform_id, username, enabled, session_status 等
        - order_by (list[dict[str, str]] | None): 排序规则列表，如 [{"id": "desc"}]

        返回值:
        - list[CncAccountOutSchema]: 脱敏后的账号列表
        """
        rows = await CncAccountCRUD(self.auth, self.db).get_list(search=self._search(search), order_by=order_by, preload=["platform"])
        return [CncAccountOutSchema.model_validate(row) for row in rows]

    async def credential_account_by_username(self, username: str) -> Any:
        """内部凭据查询：按账号精确匹配，保留归属及数据权限，拒绝同名歧义。"""
        search = self._search()
        search["username"] = ("eq", username)
        result = await CncAccountCRUD(self.auth, self.db).page(offset=0, limit=2, order_by=[{"id": "asc"}], search=search, out_schema=None)
        if len(result.items) != 1:
            raise CustomException(msg="账号不存在、无权访问或匹配到多个账号")
        return result.items[0]

    async def page(
        self,
        page_no: int,
        page_size: int,
        search=None,
        order_by=None,
        out_schema: type | None = CncAccountOutSchema,
    ) -> PageResultSchema:
        """
        分页查询网站账号列表 (Agent 核心列表接口)

        【Agent 调用指南】:
        - 场景: 管理后台表格分页呈现，或 Agent 遍历大批量账号记录。
        - 数据权限: 自动应用用户创建者隔离与软删除过滤。
        - 默认排序: 若未指定 order_by，默认按 ID 升序排列 [{"id": "asc"}]。

        参数:
        - page_no (int): 分页页码，从 1 开始
        - page_size (int): 每页记录数（例如 10, 20, 50）
        - search (CncAccountQueryParam | dict | None): 搜索过滤条件
        - order_by (list[dict[str, str]] | None): 排序配置
        - out_schema (type | None): 结果校验 Schema，若为 None 则返回原始模型列表

        返回值:
        - PageResultSchema: 包含 items（账号列表）、total（符合条件总数）、page_no、page_size 等
        """
        return await CncAccountCRUD(self.auth, self.db).page(
            offset=(page_no - 1) * page_size,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=self._search(search),
            out_schema=out_schema,
            preload=["platform"],
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
        if password or changed or account.password:
            try:
                _, previous = read_credentials(account)
            except LoginError:
                if not password:
                    raise CustomException(msg="原凭据不可用，请重新填写密码") from None
                previous = ""
            if password or changed or not account.credential_ciphertext:
                values["credential_ciphertext"] = seal_credentials(new_username, password or previous)
            values["password"] = ""
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
