"""Fixed quote commands under metadata-only auditing and both permissions."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Security
from fastapi.responses import JSONResponse, Response

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.exceptions import CustomException
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.login.contracts import LoginError, LoginInput
from app.modules.cnc.login.routes import PrivateAccountRoute

from .contracts import QuoteAccount, QuoteRunView, StartQuote
from .service import get_quote_service

ConfigId = Annotated[int, Path(ge=1)]
RunId = Annotated[UUID, Path()]
RunAuth = Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:update"]))]
AccountWrite = Security(AuthPermission(["module_cnc:cnc_account:update"]))


async def _action(auth, config_id, run_id=None, kind="status", data=None):
    service = get_quote_service()
    try:
        if kind == "accounts":
            return await service.repository.accounts(auth, config_id)
        if kind == "start":
            return await service.start(auth, config_id, data)
        if kind == "status":
            return await service.status(auth, config_id, str(run_id))
        return await service.command(auth, config_id, str(run_id), kind, data)
    except (LoginError, BrowserStop) as exc:
        raise CustomException(msg=str(exc.reason)) from None


def register_quote_routes(parent: APIRouter) -> None:
    # Keep the child router local: DynamicRouterRegistry inspects every module
    # APIRouter attribute, so exporting an included child would duplicate routes.
    router = APIRouter(route_class=PrivateAccountRoute)

    @router.get("/{id}/quote/accounts", summary="读取可用报价账号", response_model=ResponseSchema[list[QuoteAccount]], dependencies=[Security(AuthPermission(["module_cnc:cnc_account:query"]))])
    async def accounts(id: ConfigId, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_part_config:query", "module_cnc:cnc_part_config:detail"]))]) -> JSONResponse:
        return SuccessResponse(data=await _action(auth, id, kind="accounts"))

    @router.post("/{id}/quote/runs", summary="发起单配置自动报价", response_model=ResponseSchema[QuoteRunView], dependencies=[AccountWrite])
    async def start(id: ConfigId, auth: RunAuth, data: StartQuote) -> JSONResponse:
        return SuccessResponse(data=await _action(auth, id, kind="start", data=data))

    @router.get("/{id}/quote/runs/{run_id}", summary="读取自动报价进度", response_model=ResponseSchema[QuoteRunView], dependencies=[AccountWrite])
    async def status(id: ConfigId, run_id: RunId, auth: RunAuth) -> JSONResponse:
        return SuccessResponse(data=await _action(auth, id, run_id))

    @router.get("/{id}/quote/runs/{run_id}/frame", summary="读取私有报价浏览器画面", dependencies=[AccountWrite])
    async def frame(id: ConfigId, run_id: RunId, auth: RunAuth) -> Response:
        return Response(await _action(auth, id, run_id, "frame"), media_type="image/jpeg", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @router.post("/{id}/quote/runs/{run_id}/input", summary="操作待人工处理报价窗口", response_model=ResponseSchema[QuoteRunView], dependencies=[AccountWrite])
    async def input(id: ConfigId, run_id: RunId, auth: RunAuth, data: LoginInput) -> JSONResponse:
        return SuccessResponse(data=await _action(auth, id, run_id, "input", data))

    @router.post("/{id}/quote/runs/{run_id}/resume", summary="验证并继续当前报价", response_model=ResponseSchema[QuoteRunView], dependencies=[AccountWrite])
    async def resume(id: ConfigId, run_id: RunId, auth: RunAuth) -> JSONResponse:
        return SuccessResponse(data=await _action(auth, id, run_id, "resume"))

    @router.delete("/{id}/quote/runs/{run_id}", summary="停止并释放当前报价", response_model=ResponseSchema[QuoteRunView], dependencies=[AccountWrite])
    async def close(id: ConfigId, run_id: RunId, auth: RunAuth) -> JSONResponse:
        return SuccessResponse(data=await _action(auth, id, run_id, "close"))

    parent.include_router(router)
