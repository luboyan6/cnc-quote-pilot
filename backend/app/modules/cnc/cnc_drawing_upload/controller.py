"""Authenticated local drawing upload; no external provider action."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Path, Security, UploadFile
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import DrawingUploadResult
from .service import DrawingUploadService

DrawingUploadRouter = APIRouter(route_class=OperationLogRoute, prefix="/drawing-upload", tags=["图纸文件模块"])


@DrawingUploadRouter.post(
    "/step",
    summary="私有上传 STEP 图纸",
    response_model=ResponseSchema[DrawingUploadResult],
    dependencies=[
        Security(AuthPermission(["module_common:file:upload"])),
        Security(AuthPermission(["module_cnc:cnc_part:create"])),
    ],
)
async def upload_step_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
    request_id: Annotated[UUID, Form(description="稳定的上传请求标识")],
    file: Annotated[UploadFile, File(description="STEP 图纸字节")],
) -> JSONResponse:
    result = await DrawingUploadService(auth).upload(request_id, file)
    return SuccessResponse(data=result, msg="图纸已保存")


@DrawingUploadRouter.get(
    "/status/{request_id}",
    summary="查询图纸上传结果",
    response_model=ResponseSchema[DrawingUploadResult],
    dependencies=[Security(AuthPermission(["module_cnc:cnc_part:query", "module_cnc:cnc_part:detail"]))],
)
async def upload_status_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
    request_id: Annotated[UUID, Path(description="上传请求标识")],
) -> JSONResponse:
    result = await DrawingUploadService(auth).status(request_id)
    return SuccessResponse(data=result, msg="查询成功")
