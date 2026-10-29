from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class CncQuoteResultModel(ModelMixin, UserMixin):
    """
    CNC 报价结果与历史观测表
    记录每次自动报价执行的报价金额、耗时、状态、成功率指标、历史价格走势及截图证据
    """

    __tablename__: str = "cnc_quote_result"
    __table_args__: tuple = (UniqueConstraint("run_id", name="uq_cnc_result_run"), {"comment": "CNC 报价结果展示与历史观测表"})

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True, nullable=False, comment="自增主键")
    run_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True, comment="报价任务运行标识 (UUID)")
    batch_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True, comment="批次ID")
    item_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True, comment="批次子项ID")
    round_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True, comment="关联监测计划轮次ID")
    config_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True, comment="关联图纸参数配置ID")
    config_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="参数配置名称快照")
    part_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True, comment="关联图纸零件ID")
    part_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="图纸文件名")
    platform_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True, comment="报价平台ID(1=Xometry, 2=嘉立创)")
    platform_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="平台代码")
    platform_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="平台显示名称")
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="执行账号ID")
    account_alias: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="执行账号别名")

    # 报价状态与成功标识
    quote_status: Mapped[str] = mapped_column(String(32), default="QUOTED", index=True, comment="报价性质状态(QUOTED, REFERENCE_ESTIMATE, PENDING_REVIEW, FAILED, CANCELLED)")
    success: Mapped[bool] = mapped_column(Boolean, default=True, index=True, comment="是否报价成功")

    # 价格指标
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True, comment="单件价格")
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True, comment="总金额")
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True, comment="税费")
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True, comment="优惠减免金额")
    shipping_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True, comment="预估运费")
    tax_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True, comment="单价/总金额是否含税(未知为空)")
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="币种(CNY, USD等)；未知为空")
    price_scope: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="价格口径(unit, line)")

    # 交期
    lead_time_raw: Mapped[str | None] = mapped_column(Text, nullable=True, comment="交期原始描述")
    lead_time_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, default=dict, comment="结构化交期档位")
    platform_quote_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="站方报价单号/零件号")

    # 参数快照与可比指纹
    material: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="加工材料")
    surface_finish: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="表面处理")
    quantity: Mapped[int | None] = mapped_column(Integer, default=1, comment="加工数量")
    tolerance: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="加工公差")
    roughness: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="表面粗糙度")
    extra_params: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict, comment="额外请求参数快照")
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="图纸文件SHA256哈希")
    comparison_key: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True, comment="可比维度指纹")
    comparison_version: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1, comment="可比规则版本")
    effective_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict, comment="有效参数与商业条件快照")

    # 分段耗时统计
    elapsed_ms: Mapped[int | None] = mapped_column(BigInteger, default=0, comment="执行有效耗时(毫秒)")
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), default=Decimal("0.00"), comment="执行耗时(秒)")
    queue_ms: Mapped[int | None] = mapped_column(BigInteger, default=0, comment="排队等待耗时(毫秒)")
    active_execution_ms: Mapped[int | None] = mapped_column(BigInteger, default=0, comment="浏览器活跃执行耗时(毫秒)")
    human_wait_ms: Mapped[int | None] = mapped_column(BigInteger, default=0, comment="等待人工介入耗时(毫秒)")
    reconcile_ms: Mapped[int | None] = mapped_column(BigInteger, default=0, comment="回执核对耗时(毫秒)")
    total_wall_ms: Mapped[int | None] = mapped_column(BigInteger, default=0, comment="总自然耗时(毫秒)")

    # 证据与时间
    evidence_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True, comment="受控私有证据ID")
    evidence_state: Mapped[str | None] = mapped_column(String(32), nullable=True, default="available", comment="证据状态(available, migrated, missing)")
    evidence_screenshot: Mapped[str | None] = mapped_column(Text, nullable=True, comment="报价截图相对静态路径(兼容旧数据)")
    quoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="站方出价时间")
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="抓取观测时间")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True, comment="错误码")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因或错误信息")
