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

from .schema import CncPlatformCreateSchema, CncPlatformOutSchema, CncPlatformQueryParam, CncPlatformUpdateSchema
from .service import CncPlatformService

CncPlatformRouter = APIRouter(route_class=OperationLogRoute, prefix="/cnc_platform", tags=["竞价平台模块"])


@CncPlatformRouter.get("/detail/{id}", summary="获取竞价平台详情", response_model=ResponseSchema[CncPlatformOutSchema])
async def get_obj_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:detail"]))],
    id: Annotated[int, Path(description="竞价平台ID", ge=1)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPlatformService(auth, db)
    result_dict = await service.detail(id=id)
    return SuccessResponse(data=result_dict, msg="获取竞价平台详情成功")


@CncPlatformRouter.get("/list", summary="分页查询竞价平台", response_model=ResponseSchema[PageResultSchema[CncPlatformOutSchema]])
async def get_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CncPlatformQueryParam, Query()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPlatformService(auth, db)
    result_dict = await service.page(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result_dict, msg="查询竞价平台列表成功")


@CncPlatformRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建竞价平台", response_model=ResponseSchema[CncPlatformOutSchema])
async def create_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:create"]))],
    data: Annotated[CncPlatformCreateSchema, Body(description="创建参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPlatformService(auth, db)
    result_dict = await service.create(data=data)
    return SuccessResponse(data=result_dict, msg="创建竞价平台成功")


@CncPlatformRouter.put("/update/{id}", summary="修改竞价平台", response_model=ResponseSchema[CncPlatformOutSchema])
async def update_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:update"]))],
    id: Annotated[int, Path(description="竞价平台ID", ge=1)],
    data: Annotated[CncPlatformUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPlatformService(auth, db)
    result_dict = await service.update(id=id, data=data)
    return SuccessResponse(data=result_dict, msg="修改竞价平台成功")


@CncPlatformRouter.delete("/delete", summary="删除竞价平台", response_model=ResponseSchema[None])
async def delete_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:delete"]))],
    ids: Annotated[list[int], Body(description="ID列表")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPlatformService(auth, db)
    await service.delete(ids=ids)
    return SuccessResponse(msg="删除竞价平台成功")


@CncPlatformRouter.patch("/status/batch", summary="批量修改竞价平台状态", response_model=ResponseSchema[None])
async def batch_set_available_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:patch"]))],
    data: Annotated[BatchSetAvailable, Body(description="状态设置")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPlatformService(auth, db)
    await service.set_available(data=data)
    return SuccessResponse(msg="批量修改竞价平台状态成功")


@CncPlatformRouter.post("/export", summary="导出竞价平台")
async def export_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:export"]))],
    search: Annotated[CncPlatformQueryParam, Body()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> StreamingResponse:
    service = CncPlatformService(auth, db)
    result_dict_list = await service.get_list(search=search)
    export_result = await CncPlatformService.batch_export(obj_list=[item.model_dump() for item in result_dict_list])

    return StreamResponse(
        data=bytes2file_response(export_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=cnc_platform.xlsx"},
    )


@CncPlatformRouter.post("/import", summary="导入竞价平台", response_model=ResponseSchema[str])
async def import_obj_list_controller(
    file: Annotated[UploadFile, File(description="导入文件")],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_platform:import"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPlatformService(auth, db)
    batch_import_result = await service.batch_import(file=file, update_support=True)
    return SuccessResponse(data=batch_import_result, msg="导入竞价平台成功")


@CncPlatformRouter.post("/download/template", summary="获取竞价平台导入模板", dependencies=[Security(AuthPermission(["module_cnc:cnc_platform:download"]))])
async def export_obj_template_controller() -> StreamingResponse:
    import_template_result = CncPlatformService.import_template_download()

    return StreamResponse(
        data=bytes2file_response(import_template_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={urllib.parse.quote('竞价平台导入模板.xlsx')}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
