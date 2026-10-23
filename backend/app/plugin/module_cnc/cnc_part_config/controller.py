# -*- coding: utf-8 -*-
import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Path, Query, Security, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, StreamResponse, SuccessResponse
from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.core.router_class import OperationLogRoute
from app.utils.common_util import bytes2file_response

from .schema import CncPartConfigCreateSchema, CncPartConfigOutSchema, CncPartConfigQueryParam, CncPartConfigUpdateSchema
from .service import CncPartConfigService

CncPartConfigRouter = APIRouter(route_class=OperationLogRoute, prefix="/cnc_part_config", tags=["图纸参数配置表模块"])


@CncPartConfigRouter.get("/detail/{id}", summary="获取图纸参数配置表详情", response_model=ResponseSchema[CncPartConfigOutSchema])
async def get_obj_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:detail"]))],
    id: Annotated[int, Path(description="图纸参数配置表ID", ge=1)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartConfigService(auth, db)
    result_dict = await service.detail(id=id)
    return SuccessResponse(data=result_dict, msg="获取图纸参数配置表详情成功")


@CncPartConfigRouter.get("/list", summary="分页查询图纸参数配置表", response_model=ResponseSchema[PageResultSchema[CncPartConfigOutSchema]])
async def get_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CncPartConfigQueryParam, Query()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartConfigService(auth, db)
    result_dict = await service.page(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result_dict, msg="查询图纸参数配置表列表成功")


@CncPartConfigRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建图纸参数配置表", response_model=ResponseSchema[CncPartConfigOutSchema])
async def create_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:create"]))],
    data: Annotated[CncPartConfigCreateSchema, Body(description="创建参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartConfigService(auth, db)
    result_dict = await service.create(data=data)
    return SuccessResponse(data=result_dict, msg="创建图纸参数配置表成功")


@CncPartConfigRouter.put("/update/{id}", summary="修改图纸参数配置表", response_model=ResponseSchema[CncPartConfigOutSchema])
async def update_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:update"]))],
    id: Annotated[int, Path(description="图纸参数配置表ID", ge=1)],
    data: Annotated[CncPartConfigUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartConfigService(auth, db)
    result_dict = await service.update(id=id, data=data)
    return SuccessResponse(data=result_dict, msg="修改图纸参数配置表成功")


@CncPartConfigRouter.delete("/delete", summary="删除图纸参数配置表", response_model=ResponseSchema[None])
async def delete_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:delete"]))],
    ids: Annotated[list[int], Body(description="ID列表")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartConfigService(auth, db)
    await service.delete(ids=ids)
    return SuccessResponse(msg="删除图纸参数配置表成功")


@CncPartConfigRouter.patch("/status/batch", summary="批量修改图纸参数配置表状态", response_model=ResponseSchema[None])
async def batch_set_available_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:patch"]))],
    data: Annotated[BatchSetAvailable, Body(description="状态设置")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartConfigService(auth, db)
    await service.set_available(data=data)
    return SuccessResponse(msg="批量修改图纸参数配置表状态成功")


@CncPartConfigRouter.post("/export", summary="导出图纸参数配置表")
async def export_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:export"]))],
    search: Annotated[CncPartConfigQueryParam, Body()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> StreamingResponse:
    service = CncPartConfigService(auth, db)
    result_dict_list = await service.get_list(search=search)
    export_result = await CncPartConfigService.batch_export(obj_list=[item.model_dump() for item in result_dict_list])

    return StreamResponse(
        data=bytes2file_response(export_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=cnc_part_config.xlsx"},
    )


@CncPartConfigRouter.post("/import", summary="导入图纸参数配置表", response_model=ResponseSchema[str])
async def import_obj_list_controller(
    file: Annotated[UploadFile, File(description="导入文件")],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:import"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartConfigService(auth, db)
    batch_import_result = await service.batch_import(file=file, update_support=True)
    return SuccessResponse(data=batch_import_result, msg="导入图纸参数配置表成功")


@CncPartConfigRouter.post("/download/template", summary="获取图纸参数配置表导入模板", dependencies=[Security(AuthPermission(["module_cnc:cnc_part_config:download"]))])
async def export_obj_template_controller() -> StreamingResponse:
    import_template_result = CncPartConfigService.import_template_download()

    return StreamResponse(
        data=bytes2file_response(import_template_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={urllib.parse.quote('图纸参数配置表导入模板.xlsx')}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
