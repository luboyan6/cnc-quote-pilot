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

from .schema import CncPartCreateSchema, CncPartOutSchema, CncPartQueryParam, CncPartUpdateSchema
from .service import CncPartService

CncPartRouter = APIRouter(route_class=OperationLogRoute, prefix="/cnc_part", tags=["图纸文件模块"])


@CncPartRouter.get("/detail/{id}", summary="获取图纸文件详情", response_model=ResponseSchema[CncPartOutSchema])
async def get_obj_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:detail"]))],
    id: Annotated[int, Path(description="图纸文件ID", ge=1)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartService(auth, db)
    result_dict = await service.detail(id=id)
    return SuccessResponse(data=result_dict, msg="获取图纸文件详情成功")


@CncPartRouter.get("/list", summary="分页查询图纸文件", response_model=ResponseSchema[PageResultSchema[CncPartOutSchema]])
async def get_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CncPartQueryParam, Query()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartService(auth, db)
    result_dict = await service.page(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result_dict, msg="查询图纸文件列表成功")


@CncPartRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建图纸文件", response_model=ResponseSchema[CncPartOutSchema])
async def create_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:create"]))],
    data: Annotated[CncPartCreateSchema, Body(description="创建参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartService(auth, db)
    result_dict = await service.create(data=data)
    return SuccessResponse(data=result_dict, msg="创建图纸文件成功")


@CncPartRouter.put("/update/{id}", summary="修改图纸文件", response_model=ResponseSchema[CncPartOutSchema])
async def update_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:update"]))],
    id: Annotated[int, Path(description="图纸文件ID", ge=1)],
    data: Annotated[CncPartUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartService(auth, db)
    result_dict = await service.update(id=id, data=data)
    return SuccessResponse(data=result_dict, msg="修改图纸文件成功")


@CncPartRouter.delete("/delete", summary="删除图纸文件", response_model=ResponseSchema[None])
async def delete_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:delete"]))],
    ids: Annotated[list[int], Body(description="ID列表")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartService(auth, db)
    await service.delete(ids=ids)
    return SuccessResponse(msg="删除图纸文件成功")


@CncPartRouter.patch("/status/batch", summary="批量修改图纸文件状态", response_model=ResponseSchema[None])
async def batch_set_available_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:patch"]))],
    data: Annotated[BatchSetAvailable, Body(description="状态设置")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartService(auth, db)
    await service.set_available(data=data)
    return SuccessResponse(msg="批量修改图纸文件状态成功")


@CncPartRouter.post("/export", summary="导出图纸文件")
async def export_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:export"]))],
    search: Annotated[CncPartQueryParam, Body()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> StreamingResponse:
    service = CncPartService(auth, db)
    result_dict_list = await service.get_list(search=search)
    export_result = await CncPartService.batch_export(obj_list=[item.model_dump() for item in result_dict_list])

    return StreamResponse(
        data=bytes2file_response(export_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=cnc_part.xlsx"},
    )


@CncPartRouter.post("/import", summary="导入图纸文件", response_model=ResponseSchema[str])
async def import_obj_list_controller(
    file: Annotated[UploadFile, File(description="导入文件")],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part:import"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncPartService(auth, db)
    batch_import_result = await service.batch_import(file=file, update_support=True)
    return SuccessResponse(data=batch_import_result, msg="导入图纸文件成功")


@CncPartRouter.post("/download/template", summary="获取图纸文件导入模板", dependencies=[Security(AuthPermission(["module_cnc:cnc_part:download"]))])
async def export_obj_template_controller() -> StreamingResponse:
    import_template_result = CncPartService.import_template_download()

    return StreamResponse(
        data=bytes2file_response(import_template_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={urllib.parse.quote('图纸文件导入模板.xlsx')}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
