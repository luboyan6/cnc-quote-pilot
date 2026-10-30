from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.core.base_schema import BaseSchema


class CncQuoteResultOutSchema(BaseSchema):
    """报价结果展示表输出模型"""

    id: int = Field(description="主键ID")
    uuid: str | None = Field(default=None, description="UUID")
    run_id: str | None = Field(default=None, description="报价运行ID")
    batch_id: str | None = Field(default=None, description="批次ID")
    item_id: str | None = Field(default=None, description="批次子项ID")
    round_id: str | None = Field(default=None, description="监测轮次ID")
    config_id: int | None = Field(default=None, description="图纸参数配置ID")
    config_name: str | None = Field(default=None, description="配置名称")
    part_id: int | None = Field(default=None, description="图纸零件ID")
    part_name: str | None = Field(default=None, description="图纸零件文件名")
    platform_id: int | None = Field(default=None, description="平台ID")
    platform_code: str | None = Field(default=None, description="平台代号")
    platform_name: str | None = Field(default=None, description="平台名称")
    account_id: int | None = Field(default=None, description="执行账号ID")
    account_alias: str | None = Field(default=None, description="执行账号别名")

    quote_status: str = Field(description="报价状态: QUOTED, REFERENCE_ESTIMATE, PENDING_REVIEW, FAILED, CANCELLED")
    success: bool = Field(default=True, description="是否报价成功")

    unit_price: Decimal | None = Field(default=None, description="单价")
    total_amount: Decimal | None = Field(default=None, description="总金额")
    tax_amount: Decimal | None = Field(default=None, description="税额")
    discount_amount: Decimal | None = Field(default=None, description="优惠减免金额")
    shipping_amount: Decimal | None = Field(default=None, description="预估运费")
    tax_included: bool | None = Field(default=None, description="是否含税")
    currency: str | None = Field(default=None, description="币种(CNY/USD)，未知为空")
    price_scope: str | None = Field(default=None, description="价格口径(unit/line)")

    lead_time_raw: str | None = Field(default=None, description="交期原文")
    lead_time_json: Any = Field(default=None, description="结构化交期档位")
    platform_quote_id: str | None = Field(default=None, description="站方报价单号")

    material: str | None = Field(default=None, description="材质")
    surface_finish: str | None = Field(default=None, description="表面处理")
    quantity: int | None = Field(default=1, description="数量")
    tolerance: str | None = Field(default=None, description="精度公差")
    roughness: str | None = Field(default=None, description="表面粗糙度")
    extra_params: dict | None = Field(default=None, description="额外生效参数快照")
    file_sha256: str | None = Field(default=None, description="图纸文件SHA256哈希")
    comparison_key: str | None = Field(default=None, description="可比维度指纹")
    comparison_version: int | None = Field(default=None, description="可比规则版本")
    effective_snapshot: dict | None = Field(default=None, description="有效参数与商业条件快照")

    elapsed_ms: int | None = Field(default=0, description="执行耗时(毫秒)")
    duration_seconds: Decimal | None = Field(default=None, description="执行耗时(秒)")
    queue_ms: int | None = Field(default=0, description="排队耗时(毫秒)")
    active_execution_ms: int | None = Field(default=0, description="活跃执行耗时(毫秒)")
    human_wait_ms: int | None = Field(default=0, description="等待人工耗时(毫秒)")
    reconcile_ms: int | None = Field(default=0, description="核对耗时(毫秒)")
    total_wall_ms: int | None = Field(default=0, description="总自然耗时(毫秒)")

    evidence_id: str | None = Field(default=None, description="受控私有证据ID")
    evidence_state: str | None = Field(default=None, description="证据状态")
    evidence_screenshot: str | None = Field(default=None, description="截图证据相对路径")
    quoted_at: datetime | None = Field(default=None, description="报价时间")
    observed_at: datetime | None = Field(default=None, description="观测读取时间")
    error_code: str | None = Field(default=None, description="错误码")
    error_message: str | None = Field(default=None, description="错误信息")

    created_time: datetime | None = Field(default=None, description="创建时间")
    updated_time: datetime | None = Field(default=None, description="更新时间")
    created_id: int | None = Field(default=None, description="创建人ID")


class CncQuoteResultQueryParam(BaseModel):
    """报价结果查询过滤参数"""

    config_id: int | None = Field(default=None, description="图纸参数配置ID")
    part_id: int | None = Field(default=None, description="零件图纸ID")
    platform_id: int | None = Field(default=None, description="平台ID")
    batch_id: str | None = Field(default=None, description="批次ID")
    round_id: str | None = Field(default=None, description="监测轮次ID")
    quote_status: str | None = Field(default=None, description="报价状态")
    quote_kind: str | None = Field(default=None, description="报价性质")
    success: bool | None = Field(default=None, description="是否成功")
    part_name: str | None = Field(default=None, description="图纸名称(模糊匹配)")
    config_name: str | None = Field(default=None, description="配置名称(模糊匹配)")
    currency: str | None = Field(default=None, description="币种")
    comparison_key: str | None = Field(default=None, description="可比键指纹")
    created_time_start: datetime | None = Field(default=None, description="创建时间范围-起始")
    created_time_end: datetime | None = Field(default=None, description="创建时间范围-结束")


class CncPlatformStatItem(BaseModel):
    """各平台统计指标"""

    platform_id: int | None = None
    platform_name: str | None = None
    platform_code: str | None = None
    total_quotes: int = 0
    formal_quotes: int = 0
    reference_estimates: int = 0
    pending_reviews: int = 0
    success_quotes: int = 0
    failed_quotes: int = 0
    success_rate: float = 0.0
    formal_quote_rate: str | None = None
    avg_duration_seconds: float = 0.0
    min_unit_price: str | None = None
    max_unit_price: str | None = None
    currency: str | None = None
    latest_quote_time: datetime | None = None


class CncQuoteStatsOutSchema(BaseModel):
    """报价大盘/报表聚合统计输出"""

    total_quotes: int = 0
    total_items: int = 0
    completed_quotes: int = 0
    quoted_quotes: int = 0
    reference_estimate_quotes: int = 0
    pending_review_quotes: int = 0
    success_quotes: int = 0
    failed_quotes: int = 0
    cancelled_quotes: int = 0
    waiting_human_quotes: int = 0
    reconciling_quotes: int = 0
    overall_success_rate: float = 0.0
    completion_rate: str | None = None
    formal_quote_rate: str | None = None
    avg_duration_seconds: float = 0.0
    avg_queue_seconds: float = 0.0
    avg_exec_seconds: float = 0.0
    fastest_seconds: float = 0.0
    longest_seconds: float = 0.0
    platform_stats: list[CncPlatformStatItem] = []


class CncHistoryPriceItem(BaseModel):
    """历史价格折线数据点"""

    id: int
    config_id: int | None = None
    config_name: str | None = None
    part_id: int | None = None
    part_name: str | None = None
    platform_id: int | None = None
    platform_name: str | None = None
    platform_code: str | None = None
    unit_price: str = "0.0000"
    total_amount: str | None = None
    price_diff: str | None = None
    change_rate: str | None = None
    currency: str | None = None
    quantity: int | None = None
    quote_kind: str = "QUOTED"
    comparison_key: str | None = None
    material: str | None = None
    surface_finish: str | None = None
    duration_seconds: float | None = None
    evidence_id: str | None = None
    evidence_screenshot: str | None = None
    quoted_time: datetime | None = None
    observed_at: datetime | None = None
