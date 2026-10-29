"""Separate credential writes from public account responses."""

from pydantic import BaseModel, ConfigDict, Field

from app.core.base_schema import BaseQueryParam, BaseSchema, UserByQueryParam, UserBySchema
from app.core.validator import DateTimeStr


class CncAccountCreateSchema(BaseModel):
    """网站账号创建入参模型"""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    platform_id: int | None = Field(None, ge=1, description="所属 CNC 平台 ID")
    alias: str | None = Field(None, max_length=100, description="平台账号别名")
    username: str = Field(..., min_length=1, max_length=64, description="账号/手机/邮箱")
    password: str = Field(..., max_length=255, repr=False, description="密码（落库时自动加密并剥离明文）")
    login_url: str | None = Field(None, description="个性化登录地址")
    login_method: str | None = Field("PASSWORD", max_length=24, description="登录方式（PASSWORD/OTP/SSO/MANUAL_SESSION）")
    enabled: bool = Field(True, description="是否启用")
    authorization_note: str | None = Field(None, max_length=2000, description="授权使用说明备注")


class CncAccountUpdateSchema(BaseModel):
    """网站账号更新入参模型"""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    platform_id: int | None = Field(None, ge=1, description="所属 CNC 平台 ID")
    alias: str | None = Field(None, max_length=100, description="平台账号别名")
    username: str | None = Field(None, min_length=1, max_length=64, description="账号/手机/邮箱")
    password: str | None = Field(None, max_length=255, repr=False, description="新密码（留空表示不修改原凭据）")
    login_url: str | None = Field(None, description="个性化登录地址")
    login_method: str | None = Field(None, max_length=24, description="登录方式")
    enabled: bool | None = Field(None, description="是否启用")
    authorization_note: str | None = Field(None, max_length=2000, description="授权使用说明备注")


class CncAccountMcpOutSchema(BaseModel):
    """MCP 账号元数据与加密凭据；明文仅通过独立的授权解密工具获取。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0, description="账号 ID，用于详情与登录工具")
    username: str = Field(description="账号")
    password: str = Field(repr=False, description="加密凭据密文，不能直接填入登录表单；使用 cnc_account_decrypt_password 传入 username 解密")
    platform_name: str | None = Field(default=None, description="登录平台名称")
    login_url: str | None = Field(default=None, description="登录网址")
    quote_url: str | None = Field(default=None, description="报价网址")


class CncAccountOutSchema(BaseSchema, UserBySchema):
    """
    网站账号查询响应模型 (CncAccountOutSchema)

    【Agent 阅读与响应解析说明】:
    包含对外安全公开的账号元数据，已脱敏处理，绝不暴露明文密码或加密私钥。
    提供平台名称与登录 URL 等计算属性，方便 Agent 直接获取上下文信息。

    字段说明:
    - id (int): 账号主键 ID。
    - platform_id (int | None): 所属 CNC 平台的 ID。
    - platform_name (str | None): 所属平台的中文/展示名称（如 '立创CNC'）。
    - platform_login_url (str | None): 所属平台配置的标准登录入口。
    - platform_quote_entry_url (str | None): 所属平台的在线报价入口。
    - alias (str | None): 账号别名。
    - username (str): 登录账号用户名 / 手机号 / 邮箱。
    - login_url (str | None): 账号级别的自定义登录地址（若为空则使用平台的 platform_login_url）。
    - login_method (str | None): 登录方式 (PASSWORD/OTP/SSO/MANUAL_SESSION)。
    - enabled (bool | None): 是否启用（停用的账号不可执行登录与自动报价）。
    - authorization_note (str | None): 授权使用依据与合规备注。
    - session_status (str | None): 当前会话状态 (UNKNOWN/VALID/EXPIRED/CHALLENGE/REVOKED)。
    - last_verified_at (DateTimeStr | None): 上次登录态成功验证的时间。
    - auth_expires_at (DateTimeStr | None): 会话预计过期时间。
    - has_credentials (bool): 是否已录入有效登录凭据（无需暴露密码原文，直接通过此字段判断是否可用）。
    """

    model_config = ConfigDict(from_attributes=True)
    platform_id: int | None = None
    platform_name: str | None = None
    platform_login_url: str | None = None
    platform_quote_entry_url: str | None = None
    alias: str | None = None
    username: str
    login_url: str | None = None
    login_method: str | None = None
    enabled: bool | None = True
    authorization_note: str | None = None
    session_status: str | None = None
    last_verified_at: DateTimeStr | None = None
    auth_expires_at: DateTimeStr | None = None
    has_credentials: bool = False


class CncAccountQueryParam(BaseQueryParam, UserByQueryParam):
    """
    网站账号查询过滤参数 (CncAccountQueryParam)

    【Agent 调用指南】:
    用于列表查询（/cnc_account/list）与导出接口。各字段标注了后端 SQL 构造的操作符：
    - platform_id (int | None): 精确匹配所属平台 ID (q='eq')。
    - alias (str | None): 账号别名模糊搜索 (q='like')。
    - username (str | None): 用户名模糊搜索 (q='like')。
    - login_url (str | None): 登录地址模糊搜索 (q='like')。
    - login_method (str | None): 登录方式模糊搜索 (q='like')。
    - session_status (str | None): 会话状态精确匹配 (q='eq')，例如查询 'VALID' 的可用账号。
    - enabled (bool | None): 启用状态精确匹配 (q='eq')，例如查询 enabled=True。
    - 审计字段 (继承自 UserByQueryParam): created_id, updated_id 等。
    """

    platform_id: int | None = Field(None, description="平台ID精确匹配", json_schema_extra={"q": "eq"})
    alias: str | None = Field(None, description="别名模糊搜索", json_schema_extra={"q": "like"})
    username: str | None = Field(None, description="账号名模糊搜索", json_schema_extra={"q": "like"})
    login_url: str | None = Field(None, description="登录地址模糊搜索", json_schema_extra={"q": "like"})
    login_method: str | None = Field(None, description="登录方式模糊搜索", json_schema_extra={"q": "like"})
    session_status: str | None = Field(None, description="会话状态精确匹配(UNKNOWN/VALID/EXPIRED/CHALLENGE/REVOKED)", json_schema_extra={"q": "eq"})
    enabled: bool | None = Field(None, description="启用状态精确匹配(true=启用, false=停用)", json_schema_extra={"q": "eq"})
