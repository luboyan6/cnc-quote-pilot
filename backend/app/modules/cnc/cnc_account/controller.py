import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Path, Query, Security, UploadFile, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseSchema, StreamResponse, SuccessResponse
from app.core.base_schema import AuthSchema, BatchSetAvailable, PageResultSchema, PaginationQueryParam
from app.core.dependencies import AuthPermission, db_getter
from app.modules.cnc.login.actions import login_action
from app.modules.cnc.login.contracts import LoginInput, LoginView
from app.modules.cnc.login.routes import PrivateAccountRoute
from app.modules.cnc.login.runtime import get_login_manager
from app.utils.common_util import bytes2file_response

from .schema import CncAccountCreateSchema, CncAccountOutSchema, CncAccountQueryParam, CncAccountUpdateSchema
from .service import CncAccountService

CncAccountRouter = APIRouter(route_class=PrivateAccountRoute, prefix="/cnc_account", tags=["网站账号模块"])


async def _login_action(auth, account_id, session_id=None, kind="start", payload=None):
    return await login_action(auth, account_id, session_id, kind, payload, manager=get_login_manager())


LoginAuth = Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:update"]))]
AccountId = Annotated[int, Path(ge=1)]
SessionId = Annotated[str, Path(min_length=20, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


@CncAccountRouter.post("/login/{id}", summary="打开账号平台登录", response_model=ResponseSchema[LoginView])
async def start_login(auth: LoginAuth, id: AccountId) -> JSONResponse:
    """按账号 ID 启动或复用平台登录，服务端解密已保存凭据；返回状态不代表登录成功，READY 才表示身份验证通过。"""
    return SuccessResponse(data=await _login_action(auth, id))


@CncAccountRouter.get("/login/{id}/sessions/{session_id}", summary="读取平台登录状态", response_model=ResponseSchema[LoginView])
async def login_status(auth: LoginAuth, id: AccountId, session_id: SessionId) -> JSONResponse:
    """
    查询指定账号正在进行的交互登录会话实时状态。

    【Agent 调用指南】:
    - 路径: GET /cnc/cnc_account/login/{id}/sessions/{session_id}
    - 作用: 在通过 start_login 发起登录后，轮询或查询当前登录会话阶段（如等待输入验证码、已完成登录等）。
    """
    return SuccessResponse(data=await _login_action(auth, id, session_id, "status"))


@CncAccountRouter.get("/login/{id}/sessions/{session_id}/frame", summary="读取私有浏览器画面")
async def login_frame(auth: LoginAuth, id: AccountId, session_id: SessionId) -> Response:
    frame = await _login_action(auth, id, session_id, "frame")
    return Response(content=frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@CncAccountRouter.post("/login/{id}/sessions/{session_id}/input", summary="控制当前平台登录窗口", response_model=ResponseSchema[LoginView])
async def login_input(auth: LoginAuth, id: AccountId, session_id: SessionId, data: LoginInput) -> JSONResponse:
    return SuccessResponse(data=await _login_action(auth, id, session_id, "input", data))


@CncAccountRouter.post("/login/{id}/sessions/{session_id}/verify", summary="验证当前平台账号身份", response_model=ResponseSchema[LoginView])
async def verify_login(auth: LoginAuth, id: AccountId, session_id: SessionId) -> JSONResponse:
    return SuccessResponse(data=await _login_action(auth, id, session_id, "verify"))


@CncAccountRouter.delete("/login/{id}/sessions/{session_id}", summary="关闭平台登录窗口", response_model=ResponseSchema[LoginView])
async def close_login(auth: LoginAuth, id: AccountId, session_id: SessionId) -> JSONResponse:
    return SuccessResponse(data=await _login_action(auth, id, session_id, "close"))


@CncAccountRouter.get("/detail/{id}", summary="获取网站账号详情", response_model=ResponseSchema[CncAccountOutSchema])
async def get_obj_detail_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:detail"]))],
    id: Annotated[int, Path(description="网站账号ID", ge=1)],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    """
    根据主键 ID 查询网站账号详细信息。

    【Agent 调用指南】:
    - 接口路径: GET /cnc/cnc_account/detail/{id}
    - 权限要求: module_cnc:cnc_account:detail
    - 业务行为: 自动检查当前登录用户的数据权限（非超管只能查询自己创建的账号），联表返回所属平台名称与登录入口，敏感密码字段已脱敏。
    - 返回模型: CncAccountOutSchema（包含 platform_name, session_status, has_credentials 等字段）。
    """
    service = CncAccountService(auth, db)
    result_dict = await service.detail(id=id)
    return SuccessResponse(data=result_dict, msg="获取网站账号详情成功")


@CncAccountRouter.get("/list", summary="分页查询网站账号", response_model=ResponseSchema[PageResultSchema[CncAccountOutSchema]])
async def get_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:query"]))],
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[CncAccountQueryParam, Query()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    """
    分页并按条件过滤查询网站账号列表。

    【Agent 调用指南】:
    - 接口路径: GET /cnc/cnc_account/list
    - 权限要求: module_cnc:cnc_account:query
    - Query 分页参数: page_no (默认1), page_size (默认10), order_by (可选排序列表)
    - Query 过滤参数: platform_id (平台精确匹配), username (用户名模糊搜索), session_status (会话状态), enabled (是否启用) 等
    - 数据隔离: 非超级用户强制注入当前登录用户过滤条件，仅返回当前用户有权访问的账号列表。
    - 返回结构: PageResultSchema[CncAccountOutSchema]（含 items 数组与 total 总数）。
    """
    service = CncAccountService(auth, db)
    result_dict = await service.page(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    return SuccessResponse(data=result_dict, msg="查询网站账号列表成功")


@CncAccountRouter.post("/create", status_code=status.HTTP_201_CREATED, summary="创建网站账号", response_model=ResponseSchema[CncAccountOutSchema])
async def create_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:create"]))],
    data: Annotated[CncAccountCreateSchema, Body(description="创建参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncAccountService(auth, db)
    result_dict = await service.create(data=data)
    return SuccessResponse(data=result_dict, msg="创建网站账号成功")


@CncAccountRouter.put("/update/{id}", summary="修改网站账号", response_model=ResponseSchema[CncAccountOutSchema])
async def update_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:update"]))],
    id: Annotated[int, Path(description="网站账号ID", ge=1)],
    data: Annotated[CncAccountUpdateSchema, Body(description="修改参数")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncAccountService(auth, db)
    result_dict = await service.update(id=id, data=data)
    return SuccessResponse(data=result_dict, msg="修改网站账号成功")


@CncAccountRouter.delete("/delete", summary="删除网站账号", response_model=ResponseSchema[None])
async def delete_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:delete"]))],
    ids: Annotated[list[int], Body(description="ID列表")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncAccountService(auth, db)
    await service.delete(ids=ids)
    return SuccessResponse(msg="删除网站账号成功")


@CncAccountRouter.patch("/status/batch", summary="批量修改网站账号状态", response_model=ResponseSchema[None])
async def batch_set_available_obj_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:patch"]))],
    data: Annotated[BatchSetAvailable, Body(description="状态设置")],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncAccountService(auth, db)
    await service.set_available(data=data)
    return SuccessResponse(msg="批量修改网站账号状态成功")


@CncAccountRouter.post("/export", summary="导出网站账号")
async def export_obj_list_controller(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:export"]))],
    search: Annotated[CncAccountQueryParam, Body()],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> StreamingResponse:
    service = CncAccountService(auth, db)
    result_dict_list = await service.get_list(search=search)
    export_result = await CncAccountService.batch_export(obj_list=[item.model_dump() for item in result_dict_list])

    return StreamResponse(
        data=bytes2file_response(export_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=cnc_account.xlsx"},
    )


@CncAccountRouter.post("/import", summary="导入网站账号", response_model=ResponseSchema[str])
async def import_obj_list_controller(
    file: Annotated[UploadFile, File(description="导入文件")],
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_account:import"]))],
    db: Annotated[AsyncSession, Depends(db_getter)],
) -> JSONResponse:
    service = CncAccountService(auth, db)
    batch_import_result = await service.batch_import(file=file, update_support=True)
    return SuccessResponse(data=batch_import_result, msg="导入网站账号成功")


@CncAccountRouter.post("/download/template", summary="获取网站账号导入模板", dependencies=[Security(AuthPermission(["module_cnc:cnc_account:download"]))])
async def export_obj_template_controller() -> StreamingResponse:
    import_template_result = CncAccountService.import_template_download()

    return StreamResponse(
        data=bytes2file_response(import_template_result),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={urllib.parse.quote('网站账号导入模板.xlsx')}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
