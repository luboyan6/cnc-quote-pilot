"""Skills available to the authenticated user's running source Agent."""

from typing import Annotated

from fastapi import APIRouter, Path, Request, Security
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import SkillDetailSchema, SkillInfoSchema
from .service import SkillService

SkillRouter = APIRouter(route_class=OperationLogRoute, prefix="/skills", tags=["AI管理"])


def _service(request: Request, auth: AuthSchema) -> SkillService:
    runtime = getattr(request.app.state, "agent_service", None) if settings.AI_CHAT_ENGINE == "deerflow_source" else None
    return SkillService(auth, getattr(runtime, "catalog", None))


@SkillRouter.get("/list", summary="获取可用技能", response_model=ResponseSchema[list[SkillInfoSchema]])
async def list_skills_controller(
    request: Request,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
) -> JSONResponse:
    result = await _service(request, auth).list()
    return SuccessResponse(data=result, msg="获取技能列表成功")


@SkillRouter.get("/detail/{name}", summary="获取可用技能详情", response_model=ResponseSchema[SkillDetailSchema])
async def get_skill_controller(
    request: Request,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_ai:chat:query"]))],
    name: Annotated[str, Path(description="已发布的技能标识")],
) -> JSONResponse:
    result = await _service(request, auth).detail(name)
    return SuccessResponse(data=result, msg="获取技能详情成功")
