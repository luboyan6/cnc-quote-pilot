from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin
from app.modules.cnc.cnc_platform.model import CncPlatformModel


class CncAccountModel(ModelMixin, UserMixin):
    """
    网站账号模型 (CncAccountModel)

    【业务概述】
    表示第三方 CNC 制造/报价平台的账号实体（例如立创 CNC、Xometry、捷配等）。
    支持自动化登录（Playwright/CDP）、会话保活、凭据安全加密存储、
    以及多任务并发报价时的分布式租约（Fencing Token）互斥控制。

    【核心设计与字段说明】
    1. 基础标识与所属平台:
       - id (int): 账号记录的主键 ID (IDENTITY 自增)。
       - platform_id (int | None): 关联的 CNC 平台 ID，外键指向 cnc_platform.id。
       - alias (str | None): 平台账号别名（便于人工或 Agent 识别展示，平台内唯一）。
       - username (str): 登录账号用户名 / 手机号 / 邮箱。
       - password (str): 明文密码过渡字段（落库后会被加密转存至 credential_ciphertext 并清空置空）。
       - login_url (str | None): 覆盖平台的个性化登录地址（若为空则默认使用所属平台的 login_url）。
       - login_method (str | None): 登录方式字典：
         * PASSWORD: 账号密码自动登录
         * OTP: 短信或邮箱一次性验证码
         * SSO: 单点登录
         * MANUAL_SESSION: 人工在浏览器中初始化会话

    2. 安全凭据与会话管理 (Agent 核心依赖):
       - credential_ciphertext (bytes | None): 加密保存的敏感登录凭据 JSON（含账号/密码等），
         查询接口对前端和普通 Agent 脱敏，不得明文返回。
       - session_ciphertext (bytes | None): 加密保存的浏览器持久化状态 (Playwright storage_state / Cookie)，
         禁止明文存储或外泄。
       - key_id (str | None): 加密密钥标识版本（实际密钥由 KMS 或环境变量管理，禁止入库）。
       - account_fingerprint (str | None): 经规范化提取的平台用户唯一指纹（用于防止同站重复录入真实账号）。
       - session_status (str | None): 登录会话状态机字典：
         * UNKNOWN: 未核实 / 刚录入
         * VALID: 会话有效，可直接用于自动化报价
         * EXPIRED: 会话已过期，需要重新登录或刷新
         * CHALLENGE: 触发风控、滑动验证码或二次多因素认证
         * REVOKED: 已撤销 / 凭据已失效
       - session_version (int | None): 认证版本号，凭据变更或登出时自增，使旧任务失效。
       - last_verified_at (datetime | None): 最近一次成功验证登录态的时间戳。
       - auth_expires_at (datetime | None): 预估的会话失效时间（仅供 Agent 决策参考，使用前仍需实际验证）。
       - enabled (bool | None): 账号启用开关（true=启用，false=停用，停用时禁止用于报价）。
       - authorization_note (str | None): 授权使用说明依据或合规备注。

    3. 商业环境与报价配置:
       - pricing_context_json (dict | None): 当前账号在平台的等级、税率、折扣、默认收货地址等环境参数。

    4. 分布式并发与互斥租约 (Agent 调度机制):
       - lease_owner (str | None): 当前持有该账号的 Worker / Agent 实例唯一标识。为空表示空闲可用。
       - lease_until (datetime | None): 租约截止时间。超过此时间视为租约已过期，可被新任务接管。
       - lease_token (int | None): 单调递增的防护令牌（Fencing Token）。每次领取或续租时递增，
         写回数据时带条件校验，彻底消除网络分区或僵尸 Agent 造成的并发冲突。

    5. 审计与数据隔离 (继承自 ModelMixin & UserMixin):
       - created_id / updated_id (int): 创建者/更新者用户 ID，非超级用户只能访问自己创建的账号。
       - created_time / updated_time (datetime): 创建与最后更新时间。
       - is_deleted (bool): 软删除标记。

    【关联关系】
    - platform (CncPlatformModel): 多对一关联所属 CNC 平台信息（支持 joinedload 快速加载）。
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
        """
        判断账号是否已配置有效凭据。
        
        返回值:
        - bool: 只要配置了密文凭据 (credential_ciphertext) 或暂存密码 (password)，即返回 True。
        """
        return bool(self.credential_ciphertext or self.password)

    @property
    def platform_name(self) -> str | None:
        """
        获取所属 CNC 平台的显示名称（如 '立创CNC', 'Xometry'）。
        
        返回值:
        - str | None: 平台名称；若未关联平台则返回 None。
        """
        return self.platform.name if self.platform else None

    @property
    def platform_login_url(self) -> str | None:
        """
        获取所属平台的标准登录入口 URL。
        
        返回值:
        - str | None: 平台的登录 URL；若未配置或未关联则返回 None。
        """
        return self.platform.login_url if self.platform else None

    @property
    def platform_quote_entry_url(self) -> str | None:
        """
        获取所属平台的在线报价入口 URL。
        
        返回值:
        - str | None: 平台的报价入口 URL；若未配置或未关联则返回 None。
        """
        return self.platform.quote_entry_url if self.platform else None
