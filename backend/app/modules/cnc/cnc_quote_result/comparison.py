# -*- coding: utf-8 -*-
"""CNC 可比价格维度与变化率计算模块。

根据技术与商业口径生成确定性可比指纹（comparison_key）。
同组历史价格之间使用 Decimal 计算差额与百分比变动率，向前端输出规范十进制字符串。
"""

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any

COMPARISON_RULE_VERSION = 1


def build_comparison_key(
    *,
    platform_code: str | None,
    account_condition: str | int | None,
    file_sha256: str | None,
    quantity: int | None,
    currency: str | None,
    price_scope: str | None,
    quote_kind: str | None,
    material: str | None,
    surface_finish: str | None = None,
    tolerance: str | None = None,
    roughness: str | None = None,
    extra_params: dict[str, Any] | None = None,
    lead_time_tier: str | None = None,
    tax_included: bool | None = None,
    version: int = COMPARISON_RULE_VERSION,
) -> str | None:
    """生成确定性可比键。

    只有当报价性质为正式报价（QUOTED）或参考估价（REFERENCE_ESTIMATE），
    且平台、币种、数量、文件哈希等核心维度完备时，才能生成可比较的统一指纹。
    缺失关键口径或失败/取消任务返回 None，标记为不可直接比较。
    """
    if not platform_code or not currency or not quantity:
        return None
    if not quote_kind or quote_kind.strip().upper() not in {"QUOTED", "REFERENCE_ESTIMATE"}:
        return None
    quote_kind = quote_kind.strip().upper()

    # 清洗 extra_params，按键排序并排除下划线私有内部键
    cleaned_extra: list[tuple[str, str]] = []
    if extra_params:
        for k, v in sorted(extra_params.items()):
            if not k.startswith("_") and v is not None:
                cleaned_extra.append((k, str(v).strip()))

    payload = {
        "v": version,
        "platform": platform_code.strip().lower(),
        "account": str(account_condition).strip() if account_condition is not None else "",
        "file_sha256": file_sha256.strip().lower() if file_sha256 else "",
        "quantity": int(quantity),
        "currency": currency.strip().upper(),
        "price_scope": (price_scope or "unit").strip().lower(),
        "quote_kind": quote_kind.strip().upper(),
        "material": (material or "").strip().lower(),
        "surface_finish": (surface_finish or "").strip().lower(),
        "tolerance": (tolerance or "").strip().lower(),
        "roughness": (roughness or "").strip().lower(),
        "extra_params": cleaned_extra,
        "lead_time_tier": (lead_time_tier or "").strip().lower(),
        "tax_included": tax_included,
    }

    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def compute_price_diff_and_rate(
    current: Decimal | str | float | None,
    previous: Decimal | str | float | None,
) -> tuple[str | None, str | None]:
    """计算两次有效观测之间的差额与百分比变化率。

    规则：
    1. 缺少任一观测值时返回 (None, None)
    2. 差额 = current - previous，格式化为带符号十进制字符串 (如 "+10.5000", "-5.0000", "0.0000")
    3. 前值为 0 时，变化率未定义，返回 (diff_str, None)
    4. 变化率 = (current - previous) / previous，输出为带符号十进制字符串 (如 "+0.0520", "-0.1200")
    """
    if current is None or previous is None:
        return None, None

    try:
        curr_dec = Decimal(str(current))
        prev_dec = Decimal(str(previous))
    except (InvalidOperation, ValueError, TypeError):
        return None, None

    diff = curr_dec - prev_dec
    diff_str = f"{diff:+.4f}"

    if prev_dec == Decimal("0"):
        return diff_str, None

    rate = diff / prev_dec
    rate_str = f"{rate:+.4f}"
    return diff_str, rate_str
