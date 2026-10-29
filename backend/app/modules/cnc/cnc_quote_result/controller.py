# -*- coding: utf-8 -*-
from typing import Annotated
from fastapi import APIRouter, Body, Depends, Path, Query, Security
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.exceptions import CustomException
from app.core.router_class import OperationLogRoute

from .evidence import resolve_evidence_path
from .schema import (
    CncHistoryPriceItem,
    CncQuoteResultOutSchema,
    CncQuoteResultQueryParam,
    CncQuoteStatsOutSchema,
)
from .service import CncQuoteResultService

CncQuoteResultRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/cnc_quote_result",
    tags=["CNC 报价结果展示与历史报表模块"],
)


@CncQuoteResultRouter.get(
    "/stats",
    summary="获取报价统计概览指标(成功率/正式报价率/平均耗时/平台指标)",
    response_model=ResponseSchema[CncQuoteStatsOutSchema],
)
async def get_quote_stats_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_result:query"]))],
    search: Annotated[CncQuoteResultQueryParam, Query()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncQuoteResultService(auth, db)
    data = await service.get_stats(search=search)
    return SuccessResponse(data=data, msg="获取报价统计指标成功")


@CncQuoteResultRouter.get(
    "/history-prices",
    summary="获取历史价格走势序列",
    response_model=ResponseSchema[list[CncHistoryPriceItem]],
)
async def get_history_prices_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_result:query"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
    search: Annotated[CncQuoteResultQueryParam, Query()] = None,
    limit: Annotated[int, Query(description="返回最多条数", ge=1, le=200)] = 50,
) -> JSONResponse:
    service = CncQuoteResultService(auth, db)
    data = await service.get_history_prices(
        search=search,
        limit=limit,
    )
    return SuccessResponse(data=data, msg="获取历史价格序列成功")


@CncQuoteResultRouter.get(
    "/list",
    summary="分页查询报价结果记录",
    response_model=ResponseSchema[PageResultSchema[CncQuoteResultOutSchema]],
)
async def get_quote_result_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_result:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CncQuoteResultQueryParam, Query()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncQuoteResultService(auth, db)
    result_dict = await service.page(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result_dict, msg="查询报价结果列表成功")


@CncQuoteResultRouter.get(
    "/screenshot/{id}",
    summary="查看/下载报价截图证据原图(受控认证与防越界保护)",
)
async def get_screenshot_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_result:query"]))],
    id: Annotated[int, Path(description="报价结果ID", ge=1)],
    db: Annotated[AsyncSession, Depends(db_getter)],
):
    service = CncQuoteResultService(auth, db)
    row = await service.get_authorized_record(id)
    file_path = resolve_evidence_path(row)

    if not file_path or not file_path.exists():
        raise CustomException(msg="截图证据不存在或已被清理", code=404)

    return FileResponse(
        file_path,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@CncQuoteResultRouter.get(
    "/detail/{id}",
    summary="获取报价结果详情",
    response_model=ResponseSchema[CncQuoteResultOutSchema],
)
async def get_quote_result_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_result:detail", "module_cnc:cnc_quote_result:query"]))],
    id: Annotated[int, Path(description="报价结果ID", ge=1)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncQuoteResultService(auth, db)
    result_dict = await service.detail(id=id)
    return SuccessResponse(data=result_dict, msg="获取报价结果详情成功")


@CncQuoteResultRouter.delete(
    "/delete",
    summary="批量删除报价结果记录",
    response_model=ResponseSchema[None],
)
async def delete_quote_results_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_result:delete"]))],
    ids: Annotated[list[int], Body(description="ID列表")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncQuoteResultService(auth, db)
    await service.delete(ids=ids)
    return SuccessResponse(msg="删除报价结果成功")
