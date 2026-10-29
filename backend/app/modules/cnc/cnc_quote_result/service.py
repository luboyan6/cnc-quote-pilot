# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from .comparison import compute_price_diff_and_rate
from .crud import CncQuoteResultCRUD
from .evidence import resolve_evidence_path
from .model import CncQuoteResultModel
from .schema import (
    CncHistoryPriceItem,
    CncPlatformStatItem,
    CncQuoteResultOutSchema,
    CncQuoteResultQueryParam,
    CncQuoteStatsOutSchema,
)


class CncQuoteResultService:
    """CNC 报价结果展示与可比价格历史服务层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    def _apply_boundary(self, stmt, search: CncQuoteResultQueryParam | None = None):
        """统一数据边界：RBAC数据范围、软删除与通用字段筛选"""
        stmt = stmt.where(CncQuoteResultModel.is_deleted.is_(False))
        if not self.auth.user.is_superuser:
            stmt = stmt.where(CncQuoteResultModel.created_id == self.auth.user.id)

        if search:
            if search.part_id:
                stmt = stmt.where(CncQuoteResultModel.part_id == search.part_id)
            if search.config_id:
                stmt = stmt.where(CncQuoteResultModel.config_id == search.config_id)
            if search.platform_id:
                stmt = stmt.where(CncQuoteResultModel.platform_id == search.platform_id)
            if search.batch_id:
                stmt = stmt.where(CncQuoteResultModel.batch_id == search.batch_id)
            if search.round_id:
                stmt = stmt.where(CncQuoteResultModel.round_id == search.round_id)
            if search.quote_status:
                stmt = stmt.where(CncQuoteResultModel.quote_status == search.quote_status)
            if search.quote_kind:
                stmt = stmt.where(CncQuoteResultModel.quote_status == search.quote_kind)
            if search.success is not None:
                stmt = stmt.where(CncQuoteResultModel.success.is_(search.success))
            if search.currency:
                stmt = stmt.where(CncQuoteResultModel.currency == search.currency)
            if search.comparison_key:
                stmt = stmt.where(CncQuoteResultModel.comparison_key == search.comparison_key)
            if search.part_name:
                stmt = stmt.where(CncQuoteResultModel.part_name.like(f"%{search.part_name.strip()}%"))
            if search.config_name:
                stmt = stmt.where(CncQuoteResultModel.config_name.like(f"%{search.config_name.strip()}%"))
            if search.created_time_start:
                stmt = stmt.where(CncQuoteResultModel.created_time >= search.created_time_start)
            if search.created_time_end:
                stmt = stmt.where(CncQuoteResultModel.created_time <= search.created_time_end)

        return stmt

    async def get_authorized_record(self, id: int) -> CncQuoteResultModel:
        """获取并验证单条报价结果记录权限。

        规则：
        - 不存在或已被软删除返回 404
        - 存在但属于其他非授权用户返回 403
        """
        raw_obj = await self.db.get(CncQuoteResultModel, id)
        if not raw_obj or raw_obj.is_deleted:
            raise CustomException(msg="该报价结果记录不存在", code=404)

        if not self.auth.user.is_superuser and raw_obj.created_id != self.auth.user.id:
            raise CustomException(msg="无权访问该报价结果记录", code=403)

        return raw_obj

    async def detail(self, id: int) -> CncQuoteResultOutSchema:
        obj = await self.get_authorized_record(id)
        return CncQuoteResultOutSchema.model_validate(obj)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: CncQuoteResultQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[CncQuoteResultOutSchema]:
        """统一数据边界分页检索报价结果"""
        base_query = self._apply_boundary(select(CncQuoteResultModel), search)

        # 统计总数
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.scalar(count_stmt)) or 0

        # 分页排序
        offset = (page_no - 1) * page_size
        stmt = base_query.order_by(desc(CncQuoteResultModel.created_time), desc(CncQuoteResultModel.id))
        stmt = stmt.offset(offset).limit(page_size)

        rows = (await self.db.scalars(stmt)).all()
        items = [CncQuoteResultOutSchema.model_validate(r) for r in rows]

        return PageResultSchema(
            page_no=page_no,
            page_size=page_size,
            total=total,
            rows=items,
        )

    async def delete(self, ids: list[int]) -> None:
        """批量软删除（限制在当前用户授权边界内）"""
        for i in ids:
            obj = await self.get_authorized_record(i)
            obj.is_deleted = True
            obj.updated_time = datetime.utcnow()
        await self.db.flush()

    async def get_stats(self, search: CncQuoteResultQueryParam | None = None) -> CncQuoteStatsOutSchema:
        """计算报价统计大盘指标：严格区分正式报价与参考估价，分子分母可复算"""
        # 1. 总体聚合
        stmt = select(
            func.count(CncQuoteResultModel.id).label("total"),
            func.sum(case((CncQuoteResultModel.quote_status == "QUOTED", 1), else_=0)).label("quoted_count"),
            func.sum(case((CncQuoteResultModel.quote_status == "REFERENCE_ESTIMATE", 1), else_=0)).label("ref_count"),
            func.sum(case((CncQuoteResultModel.quote_status == "PENDING_REVIEW", 1), else_=0)).label("pending_review_count"),
            func.sum(case((CncQuoteResultModel.quote_status == "FAILED", 1), else_=0)).label("failed_count"),
            func.sum(case((CncQuoteResultModel.quote_status == "CANCELLED", 1), else_=0)).label("cancelled_count"),
            func.sum(case((CncQuoteResultModel.quote_status == "WAITING_HUMAN", 1), else_=0)).label("waiting_human_count"),
            func.sum(case((CncQuoteResultModel.quote_status == "RECONCILING", 1), else_=0)).label("reconciling_count"),
            func.avg(CncQuoteResultModel.duration_seconds).label("avg_dur"),
            func.min(CncQuoteResultModel.duration_seconds).label("min_dur"),
            func.max(CncQuoteResultModel.duration_seconds).label("max_dur"),
            func.avg(CncQuoteResultModel.queue_ms).label("avg_queue_ms"),
            func.avg(CncQuoteResultModel.active_execution_ms).label("avg_exec_ms"),
        )
        stmt = self._apply_boundary(stmt, search)

        row = (await self.db.execute(stmt)).first()
        total_quotes = row.total or 0
        quoted_quotes = row.quoted_count or 0
        ref_quotes = row.ref_count or 0
        pending_review_quotes = row.pending_review_count or 0
        failed_quotes = row.failed_count or 0
        cancelled_quotes = row.cancelled_count or 0
        waiting_human_quotes = row.waiting_human_count or 0
        reconciling_quotes = row.reconciling_count or 0

        completed_quotes = quoted_quotes + ref_quotes + pending_review_quotes
        success_quotes = quoted_quotes + ref_quotes

        # 有效终结子项分母 = COMPLETED + FAILED
        total_items = completed_quotes + failed_quotes

        if total_items > 0:
            completion_rate = f"{(completed_quotes / total_items * 100):.1f}%"
            formal_quote_rate = f"{(quoted_quotes / total_items * 100):.1f}%"
            overall_success_rate = round((success_quotes / total_items * 100), 1)
        else:
            completion_rate = None
            formal_quote_rate = None
            overall_success_rate = 0.0

        avg_dur = round(float(row.avg_dur or 0), 2)
        min_dur = round(float(row.min_dur or 0), 2)
        max_dur = round(float(row.max_dur or 0), 2)
        avg_queue_sec = round(float(row.avg_queue_ms or 0) / 1000.0, 2)
        avg_exec_sec = round(float(row.avg_exec_ms or 0) / 1000.0, 2)

        # 2. 分平台指标统计
        plat_stmt = (
            select(
                CncQuoteResultModel.platform_id,
                CncQuoteResultModel.platform_name,
                CncQuoteResultModel.platform_code,
                CncQuoteResultModel.currency,
                func.count(CncQuoteResultModel.id).label("plat_total"),
                func.sum(case((CncQuoteResultModel.quote_status == "QUOTED", 1), else_=0)).label("plat_quoted"),
                func.sum(case((CncQuoteResultModel.quote_status == "REFERENCE_ESTIMATE", 1), else_=0)).label("plat_ref"),
                func.sum(case((CncQuoteResultModel.quote_status == "PENDING_REVIEW", 1), else_=0)).label("plat_review"),
                func.sum(case((CncQuoteResultModel.quote_status == "FAILED", 1), else_=0)).label("plat_failed"),
                func.avg(CncQuoteResultModel.duration_seconds).label("plat_avg_dur"),
                func.min(CncQuoteResultModel.unit_price).label("plat_min_price"),
                func.max(CncQuoteResultModel.unit_price).label("plat_max_price"),
                func.max(CncQuoteResultModel.created_time).label("plat_latest_time"),
            )
            .group_by(
                CncQuoteResultModel.platform_id,
                CncQuoteResultModel.platform_name,
                CncQuoteResultModel.platform_code,
                CncQuoteResultModel.currency,
            )
            .order_by(CncQuoteResultModel.platform_id)
        )
        plat_stmt = self._apply_boundary(plat_stmt, search)

        plat_rows = (await self.db.execute(plat_stmt)).all()
        platform_stats: list[CncPlatformStatItem] = []
        for p in plat_rows:
            p_total = p.plat_total or 0
            p_quoted = p.plat_quoted or 0
            p_ref = p.plat_ref or 0
            p_review = p.plat_review or 0
            p_failed = p.plat_failed or 0
            p_succ = p_quoted + p_ref
            p_finished = p_quoted + p_ref + p_review + p_failed

            p_rate = round((p_succ / p_finished * 100), 1) if p_finished > 0 else 0.0
            p_formal_rate = f"{(p_quoted / p_finished * 100):.1f}%" if p_finished > 0 else None
            p_name = p.platform_name or ("Xometry US" if p.platform_id == 1 else "嘉立创中国")
            p_code = p.platform_code or ("xometry_us" if p.platform_id == 1 else "jlc_cnc_cn")

            min_price_str = f"{p.plat_min_price:.4f}" if p.plat_min_price is not None else None
            max_price_str = f"{p.plat_max_price:.4f}" if p.plat_max_price is not None else None

            platform_stats.append(
                CncPlatformStatItem(
                    platform_id=p.platform_id or 0,
                    platform_name=p_name,
                    platform_code=p_code,
                    total_quotes=p_total,
                    formal_quotes=p_quoted,
                    reference_estimates=p_ref,
                    pending_reviews=p_review,
                    success_quotes=p_succ,
                    failed_quotes=p_failed,
                    success_rate=p_rate,
                    formal_quote_rate=p_formal_rate,
                    avg_duration_seconds=round(float(p.plat_avg_dur or 0), 2),
                    min_unit_price=min_price_str,
                    max_unit_price=max_price_str,
                    currency=p.currency or ("USD" if p.platform_id == 1 else "CNY"),
                    latest_quote_time=p.plat_latest_time,
                )
            )

        return CncQuoteStatsOutSchema(
            total_quotes=total_quotes,
            total_items=total_items,
            completed_quotes=completed_quotes,
            quoted_quotes=quoted_quotes,
            reference_estimate_quotes=ref_quotes,
            pending_review_quotes=pending_review_quotes,
            success_quotes=success_quotes,
            failed_quotes=failed_quotes,
            cancelled_quotes=cancelled_quotes,
            waiting_human_quotes=waiting_human_quotes,
            reconciling_quotes=reconciling_quotes,
            overall_success_rate=overall_success_rate,
            completion_rate=completion_rate,
            formal_quote_rate=formal_quote_rate,
            avg_duration_seconds=avg_dur,
            avg_queue_seconds=avg_queue_sec,
            avg_exec_seconds=avg_exec_sec,
            fastest_seconds=min_dur,
            longest_seconds=max_dur,
            platform_stats=platform_stats,
        )

    async def get_history_prices(
        self,
        search: CncQuoteResultQueryParam | None = None,
        limit: int = 50,
    ) -> list[CncHistoryPriceItem]:
        """获取相同可见范围内最近 N 个实际观测点，按时点升序输出并计算同组差额与变化率。

        规则：
        1. 仅包含有效成功出价（QUOTED 或 REFERENCE_ESTIMATE）且单价非空记录
        2. 先取最近 limit 条（按 observed_at/id 降序），再反转为时点升序
        3. 按可比系列（comparison_key 或 platform/currency/quantity/quote_kind）计算差额与变化率
        4. 前值为 0 时变化率为 null；不同条件不画零线或强制连线
        """
        stmt = (
            select(CncQuoteResultModel)
            .where(
                CncQuoteResultModel.quote_status.in_(["QUOTED", "REFERENCE_ESTIMATE"]),
                CncQuoteResultModel.unit_price.is_not(None),
            )
            .order_by(desc(func.coalesce(CncQuoteResultModel.observed_at, CncQuoteResultModel.created_time)), desc(CncQuoteResultModel.id))
            .limit(limit)
        )
        stmt = self._apply_boundary(stmt, search)

        rows = (await self.db.scalars(stmt)).all()
        # 反转为升序排列
        rows_asc = list(reversed(rows))

        # 按可比分组计算同组差额与变动率
        series_prev_price: dict[str, Decimal | None] = {}
        points: list[CncHistoryPriceItem] = []

        for r in rows_asc:
            unit_price_val = r.unit_price
            price_str = f"{unit_price_val:.4f}" if unit_price_val is not None else "0.0000"
            total_str = f"{r.total_amount:.4f}" if r.total_amount is not None else None

            # 可比键：优先使用已持久化的 comparison_key，无则按核心维度退化系列键
            series_key = r.comparison_key or f"{r.platform_id}_{r.currency}_{r.quantity}_{r.quote_status}"
            prev_price = series_prev_price.get(series_key)

            diff_str, rate_str = compute_price_diff_and_rate(unit_price_val, prev_price)
            series_prev_price[series_key] = unit_price_val

            points.append(
                CncHistoryPriceItem(
                    id=r.id,
                    config_id=r.config_id,
                    config_name=r.config_name,
                    part_id=r.part_id,
                    part_name=r.part_name,
                    platform_id=r.platform_id or 0,
                    platform_name=r.platform_name or ("Xometry US" if r.platform_id == 1 else "嘉立创中国"),
                    platform_code=r.platform_code,
                    unit_price=price_str,
                    total_amount=total_str,
                    price_diff=diff_str,
                    change_rate=rate_str,
                    currency=r.currency or "CNY",
                    quantity=r.quantity or 1,
                    quote_kind=r.quote_status,
                    comparison_key=r.comparison_key,
                    material=r.material,
                    surface_finish=r.surface_finish,
                    duration_seconds=float(r.duration_seconds or 0.0),
                    evidence_id=r.evidence_id,
                    evidence_screenshot=r.evidence_screenshot,
                    quoted_time=r.created_time,
                    observed_at=r.observed_at,
                )
            )

        return points
