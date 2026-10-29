"""Private CNC schedule commands under the existing authentication/audit boundary."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Security

from app.common.response import SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.routes import PrivateAccountRoute
from app.modules.cnc.monitor.contracts import (
    ScheduleCreate,
    ScheduleError,
    ScheduleUpdate,
)
from app.modules.cnc.monitor.service import get_monitor_service

CncQuoteScheduleRouter = APIRouter(prefix="/cnc_quote_schedule", tags=["CNC 监测计划"], route_class=PrivateAccountRoute)


async def action(auth, permission: str, operation, *args):
    service = get_monitor_service()
    try:
        auth = await service.authorize(auth, permission)
        return SuccessResponse(data=await operation(auth, *args))
    except ScheduleError as exc:
        raise HTTPException(exc.status_code, exc.reason) from None
    except (LoginError, BrowserStop) as exc:
        raise HTTPException(400, str(exc.reason)) from None


@CncQuoteScheduleRouter.post("/create")
async def create(
    data: ScheduleCreate,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_schedule:create"]))],
):
    service = get_monitor_service()
    return await action(auth, "create", service.create, data)


@CncQuoteScheduleRouter.put("/update/{id}")
async def update(
    id: UUID,
    data: ScheduleUpdate,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_schedule:update"]))],
):
    service = get_monitor_service()
    return await action(auth, "update", service.update, str(id), data)


@CncQuoteScheduleRouter.get("/list")
async def list_schedules(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_schedule:query"]))],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    service = get_monitor_service()
    return await action(auth, "query", service.list, offset, limit)


@CncQuoteScheduleRouter.get("/detail/{id}")
async def detail(
    id: UUID,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_schedule:detail"]))],
):
    service = get_monitor_service()
    return await action(auth, "detail", service.detail, str(id))


@CncQuoteScheduleRouter.post("/{id}/pause")
async def pause(
    id: UUID,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_schedule:update"]))],
):
    service = get_monitor_service()
    return await action(auth, "update", service.pause, str(id))


@CncQuoteScheduleRouter.post("/{id}/resume")
async def resume(
    id: UUID,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_schedule:update"]))],
):
    service = get_monitor_service()
    return await action(auth, "update", service.resume, str(id))


@CncQuoteScheduleRouter.get("/{id}/rounds")
async def rounds(
    id: UUID,
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_schedule:detail"]))],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    service = get_monitor_service()
    return await action(auth, "detail", service.rounds, str(id), offset, limit)
