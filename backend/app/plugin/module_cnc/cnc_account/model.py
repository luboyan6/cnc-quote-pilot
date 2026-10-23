from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin
from app.plugin.module_cnc.cnc_platform.model import CncPlatformModel


class CncAccountModel(ModelMixin, UserMixin):
    """
    网站账号表
    """

    __tablename__: str = "cnc_account"
    __table_args__: dict[str, str] = {"comment": "网站账号"}
    # 现有 PostgreSQL 表使用 IDENTITY；显式保留，避免自动迁移尝试移除其默认值。
    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True, index=True, comment="主键ID")
    platform_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cnc_platform.id"), nullable=True, comment="所属 CNC 平台 ID，关联 cnc_platform.id")
    alias: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="平台网站账号别名（非后台登录名）；Demo 版由后端保证平台内唯一")
    username: Mapped[str] = mapped_column(String(64), nullable=False, comment="账号")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码")
    login_url: Mapped[str | None] = mapped_column(Text, nullable=True, comment="登录地址")
    login_method: Mapped[str | None] = mapped_column(String(24), nullable=True, comment="登录方式；字典：PASSWORD=账号密码，OTP=一次性验证码，SSO=单点登录，MANUAL_SESSION=人工初始化会话")
    credential_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True, comment="应用加密后的登录名和密码等凭据；不向普通查询接口回显；应用加密后的登录身份及秘密，例如登录名/密码的加密 JSON；查询接口不得回显"
    )
    session_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True, comment="应用加密后的浏览器认证状态，禁止明文 Cookie 或 Token；应用加密后的浏览器 storage_state；Cookie、Token 禁止明文保存"
    )
    key_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="外部加密密钥标识；实际密钥不得存入本表；外部密钥标识，实际加密密钥不得存于此表")
    account_fingerprint: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="同平台真实账号的稳定匿名指纹；核实前可空，核实后用于防重复录入；经应用规范化的稳定匿名身份指纹；核实前可空，用于防止同站重复录入真实账号"
    )
    pricing_context_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="当前地区、等级、优惠等报价环境；历史报价另存不可变快照；地区、等级、优惠环境等当前信息；每次报价还须保存不可变商业环境快照"
    )
    session_status: Mapped[str | None] = mapped_column(String(24), nullable=True, comment="会话状态；字典：UNKNOWN=未核实，VALID=有效，EXPIRED=失效，CHALLENGE=待验证码或多因素认证，REVOKED=已撤销")
    session_version: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="认证状态版本号，用于并发更新校验")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近一次实际核对账号身份和登录态的时间")
    auth_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="预计认证到期时间；仅作提示，运行前仍需实际验证")
    enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True, comment="启用开关；字典：false=停用，true=启用")
    authorization_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="第三方账号使用授权说明或依据引用，不保存完整身份证件")
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="当前租约持有者的执行实例标识；未领取时为空")
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="租约到期时间；未领取时为空")
    lease_token: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="递增的账号互斥令牌；领取、续期、释放须条件更新，过期需协调旧实例；账号互斥的 fencing token；领取/续期/释放必须条件更新，过期时还须协调旧执行实例"
    )

    platform: Mapped[CncPlatformModel | None] = relationship("CncPlatformModel", foreign_keys=[platform_id], lazy="joined")

    @property
    def has_credentials(self) -> bool:
        return bool(self.credential_ciphertext or self.password)

    @property
    def platform_name(self) -> str | None:
        return self.platform.name if self.platform else None
