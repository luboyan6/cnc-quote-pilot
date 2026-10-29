"""Bounded CNC queries, controlled login, explicitly authorized decryption and automated quoting."""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from mcp.types import Tool, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.modules.cnc.cnc_account.schema import CncAccountMcpOutSchema, CncAccountQueryParam
from app.modules.cnc.cnc_account.service import CncAccountService
from app.modules.cnc.cnc_part.schema import CncPartListOutSchema, CncPartOutSchema, CncPartQueryParam
from app.modules.cnc.cnc_part.service import CncPartService
from app.modules.cnc.cnc_part_config.schema import (
    CncPartConfigOutSchema,
    CncPartConfigQueryParam,
)
from app.modules.cnc.cnc_part_config.service import CncPartConfigService
from app.modules.cnc.login.actions import login_action
from app.modules.cnc.login.contracts import LoginView
from app.modules.cnc.login.credentials import read_credentials, seal_credentials

PositiveId = Annotated[int, Field(strict=True, gt=0)]


class StrictArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class AccountSearch(CncAccountQueryParam, StrictArguments):
    pass


class PartSearch(CncPartQueryParam, StrictArguments):
    pass


class PartConfigSearch(CncPartConfigQueryParam, StrictArguments):
    pass


class ListArguments[SearchT: BaseModel](PaginationQueryParam, StrictArguments):
    search: SearchT | None = None
    order_by: list[dict[str, Literal["asc", "desc"]]] | None = None


class DetailArguments(StrictArguments):
    id: PositiveId


class DecryptPasswordArguments(StrictArguments):
    username: str = Field(strict=True, min_length=1, max_length=64, pattern=r"\S", description="需要解密密码的登录账号（用户名/手机/邮箱），精确匹配当前用户可访问的唯一账号")


class LoginArguments(DetailArguments):
    action: Literal["start", "status", "verify", "close"] = Field("start", description="start 启动/复用登录；status 查询状态；verify 验证身份；close 关闭会话")
    session_id: str | None = Field(None, min_length=20, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", description="status/verify/close 必填，使用 start 返回的 session_id")

    @model_validator(mode="after")
    def validate_session(self):
        if (self.action == "start") != (self.session_id is None):
            raise ValueError("Session ID is required only for session actions")
        return self


class QuoteConfigArguments(StrictArguments):
    config_id: PositiveId = Field(description="图纸参数配置ID（对应前端图纸参数配置页面 cnc_part_config 中的记录ID）")
    lead_time: Literal["加急", "标准", "经济"] = Field("标准", description="期望交期档位（加急、标准、经济），默认标准")
    quantity: PositiveId | None = Field(None, description="加工数量覆盖（可选；未提供时使用配置中的默认数量）")


def _format_mcp_account(item: Any) -> dict[str, Any]:
    # Queries expose the opaque encrypted credential envelope, never plaintext.
    # Legacy passwords are sealed in memory without mutating the queried row.
    if isinstance(item, dict):
        ciphertext = item.get("credential_ciphertext")
        return {
            "id": item.get("id"),
            "username": item.get("username", ""),
            "password": (ciphertext.decode() if isinstance(ciphertext, bytes) else ciphertext) or seal_credentials(item.get("username", ""), item.get("password", "")).decode(),
            "platform_name": item.get("platform_name") or (item.get("platform", {}).get("name") if isinstance(item.get("platform"), dict) else None),
            "login_url": item.get("login_url") or item.get("platform_login_url") or (item.get("platform", {}).get("login_url") if isinstance(item.get("platform"), dict) else None),
            "quote_url": item.get("quote_url") or item.get("platform_quote_entry_url") or (item.get("platform", {}).get("quote_entry_url") if isinstance(item.get("platform"), dict) else None),
        }
    platform = getattr(item, "platform", None)
    login_url = getattr(item, "login_url", None) or (platform.login_url if platform else None)
    quote_url = platform.quote_entry_url if platform else None
    platform_name = platform.name if platform else None
    return {
        "id": item.id,
        "username": item.username,
        "password": bytes(item.credential_ciphertext).decode() if item.credential_ciphertext else seal_credentials(item.username, item.password or "").decode(),
        "platform_name": platform_name,
        "login_url": login_url,
        "quote_url": quote_url,
    }


@dataclass(frozen=True)
class ToolSpec:
    module: Literal["cnc_account", "cnc_part", "cnc_part_config"]
    operation: Literal["list", "detail", "login", "decrypt_password", "quote"]
    action: Literal["query", "detail", "update"]
    arguments: type[BaseModel]
    description: str

    @property
    def name(self) -> str:
        return f"{self.module}_{self.operation}"

    @property
    def permission(self) -> str:
        return f"module_cnc:{self.module}:{self.action}"

    def tool(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            input_schema=self.arguments.model_json_schema(),
            annotations=ToolAnnotations(
                read_only_hint=self.operation != "login",
                destructive_hint=False,
                idempotent_hint=self.operation != "login",
                open_world_hint=self.operation in {"login", "quote"},
            ),
        )

    async def execute(self, auth: AuthSchema, db: AsyncSession, arguments: BaseModel) -> dict[str, Any]:
        """Preserve existing account ownership and controlled login boundaries."""
        if self.module == "cnc_account":
            if self.operation == "login":
                assert isinstance(arguments, LoginArguments)
                result = await login_action(auth, arguments.id, arguments.session_id, arguments.action)
                return LoginView.model_validate(result).model_dump(mode="json")
            service = CncAccountService(auth, db)
            if self.operation == "decrypt_password":
                assert isinstance(arguments, DecryptPasswordArguments)
                account = await service.credential_account_by_username(arguments.username)
                username, password = read_credentials(account)
                return {"id": account.id, "username": username, "password": password}
            if self.operation == "list":
                assert isinstance(arguments, ListArguments)
                result = await service.page(
                    page_no=arguments.page_no,
                    page_size=arguments.page_size,
                    search=arguments.search,
                    order_by=[{key: str(value) for key, value in order.items()} for order in arguments.order_by] if arguments.order_by is not None else None,
                    out_schema=None,
                )
                raw_items = result.get("items", []) if isinstance(result, dict) else getattr(result, "items", [])
                total = result.get("total", len(raw_items)) if isinstance(result, dict) else getattr(result, "total", len(raw_items))
                page_no = result.get("page_no", arguments.page_no) if isinstance(result, dict) else getattr(result, "page_no", arguments.page_no)
                page_size = result.get("page_size", arguments.page_size) if isinstance(result, dict) else getattr(result, "page_size", arguments.page_size)
                items = [_format_mcp_account(item) for item in raw_items]
                return (
                    PageResultSchema[CncAccountMcpOutSchema]
                    .model_validate(
                        {"items": items, "total": total, "page_no": page_no, "page_size": page_size},
                        from_attributes=True,
                    )
                    .model_dump(mode="json")
                )
            assert isinstance(arguments, DetailArguments)
            raw = await service.detail(id=arguments.id, raw=True)
            return CncAccountMcpOutSchema.model_validate(_format_mcp_account(raw)).model_dump(mode="json")

        if self.module == "cnc_part":
            service = CncPartService(auth, db)
            if self.operation == "list":
                assert isinstance(arguments, ListArguments)
                result = await service.page(
                    page_no=arguments.page_no,
                    page_size=arguments.page_size,
                    search=arguments.search,
                    order_by=[{key: str(value) for key, value in order.items()} for order in arguments.order_by] if arguments.order_by is not None else None,
                )
                return PageResultSchema[CncPartListOutSchema].model_validate(result, from_attributes=True).model_dump(mode="json")
            assert isinstance(arguments, DetailArguments)
            result = await service.detail(id=arguments.id)
            return CncPartOutSchema.model_validate(result, from_attributes=True).model_dump(mode="json")

        # cnc_part_config
        config_service = CncPartConfigService(auth, db)
        if self.operation == "list":
            assert isinstance(arguments, ListArguments)
            result = await config_service.page(
                page_no=arguments.page_no,
                page_size=arguments.page_size,
                search=arguments.search,
                order_by=[{key: str(value) for key, value in order.items()} for order in arguments.order_by] if arguments.order_by is not None else None,
            )
            return PageResultSchema[CncPartConfigOutSchema].model_validate(result, from_attributes=True).model_dump(mode="json")
        if self.operation == "detail":
            assert isinstance(arguments, DetailArguments)
            result = await config_service.detail(id=arguments.id)
            return CncPartConfigOutSchema.model_validate(result, from_attributes=True).model_dump(mode="json")
        assert isinstance(arguments, QuoteConfigArguments)
        return await config_service.quote(
            id=arguments.config_id,
            lead_time_pref=arguments.lead_time,
            quantity_override=arguments.quantity,
        )


TOOLS = (
    ToolSpec(
        "cnc_account",
        "list",
        "query",
        ListArguments[AccountSearch],
        "分页查询可访问账号，返回 id、username、加密的 password、platform_name、login_url、quote_url。password 是加密凭据，不能直接填入登录表单；登录使用 cnc_account_login，单独获取明文使用 cnc_account_decrypt_password。遵循账号归属与数据权限。",
    ),
    ToolSpec(
        "cnc_account",
        "detail",
        "detail",
        DetailArguments,
        "按 id 查询可访问账号，返回 id、username、加密的 password、platform_name、login_url、quote_url。登录使用 cnc_account_login；需要明文时调用 cnc_account_decrypt_password。",
    ),
    ToolSpec(
        "cnc_account",
        "login",
        "update",
        LoginArguments,
        "按账号 id 启动或复用受控平台登录，服务端自动解密已保存密码，无需传入密码。action 默认为 start；随后以同一 id、返回的 session_id 和 action=status 查询，verify 重新验证，close 关闭。仅 READY 表示身份验证通过；STARTING/AUTHENTICATING 表示处理中，WAITING_HUMAN 需用户在账号管理登录窗口处理验证码。返回 LoginView，不返回密码或浏览器状态。需要账号 update 权限与账号归属校验；会访问外部平台并更新会话状态。",
    ),
    ToolSpec(
        "cnc_account",
        "decrypt_password",
        "update",
        DecryptPasswordArguments,
        "传入登录账号 username（用户名/手机/邮箱）解密其当前保存的密码，返回 id、username、password（明文），不传 id。精确匹配当前用户可访问的唯一账号；不存在、无权访问或存在多个同名账号时拒绝解密。供需要手动填入登录表单的调用方使用；账号查询展示的 password 为密文。需要账号 update 权限并检查账号归属与数据权限，不接受任意密文。明文属于敏感数据，不应展示给用户或写入日志；cnc_account_login 已自动解密，无需先调用此工具。",
    ),
    ToolSpec(
        "cnc_part",
        "list",
        "query",
        ListArguments[PartSearch],
        "分页查询允许访问的三维零件图纸记录列表，返回图纸 id、file_name、file_path、零件尺寸、单位与第三方平台上传授权状态(upload_authorized)等元数据。仅返回图纸文件元信息与本地路径，不读取或传输图纸二进制数据。在报价前必须先获取可用图纸与本地路径。",
    ),
    ToolSpec(
        "cnc_part",
        "detail",
        "detail",
        DetailArguments,
        "按图纸 id 查询单个三维零件图纸的详细元数据与第三方平台上传授权状态(upload_authorized)。返回零件长宽高尺寸、单位、文件头校验状态(HEADER_VALID)等信息。HEADER_VALID 仅表示文件头校验通过，不代表已核实实际可加工性；upload_authorized 为 true 时方可授权上传至第三方平台报价。",
    ),
    ToolSpec(
        "cnc_part_config",
        "list",
        "query",
        ListArguments[PartConfigSearch],
        "分页查询图纸参数配置列表（对应前端图纸参数配置页面 cnc_part_config），返回配置 id、name、关联图纸ID(part_id)、平台类型(site_type：1=Xometry，2=嘉立创)、材料、表面处理、加工数量及公差等参数。在执行报价前可通过此工具查询待报价的配置ID与参数信息。",
    ),
    ToolSpec(
        "cnc_part_config",
        "detail",
        "detail",
        DetailArguments,
        "按配置 id 查询单个三维零件图纸参数配置详情。返回配置名称、关联图纸ID(part_id)、报价平台类型(site_type)、材料、加工数量、表面处理方式及扩展工艺参数。",
    ),
    ToolSpec(
        "cnc_part_config",
        "quote",
        "query",
        QuoteConfigArguments,
        "针对图纸参数配置页面（cnc_part_config）中指定的配置记录执行自动在线报价（目前支持嘉立创 JLC CNC 平台）。自动读取关联图纸的本地 STEP 文件与配置参数，并在合规安全隔离下（严禁加车下单）获取 3 档生产交期（加急/标准/经济）的价格明细（单价、税费、总计、预计发货时间）与几何分析数据，保存核验凭据截图，返回参考估价结构。",
    ),
)
TOOL_BY_NAME = {tool.name: tool for tool in TOOLS}
