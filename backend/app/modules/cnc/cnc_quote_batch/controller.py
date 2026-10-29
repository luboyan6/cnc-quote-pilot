"""Private batch commands under the existing authentication/audit boundary."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Security

from app.common.response import SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.modules.cnc.batch.contracts import BatchError, BatchRequest
from app.modules.cnc.batch.service import get_batch_service
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.routes import PrivateAccountRoute
from app.modules.cnc.recovery.contracts import RecoveryError

CncQuoteBatchRouter = APIRouter(prefix="/cnc_quote_batch", tags=["CNC 批量报价"], route_class=PrivateAccountRoute)


async def action(auth, permission, operation, *args):
    service = get_batch_service()
    try:
        auth = await service.authorize(auth, permission, for_run=permission in ("create", "retry"))
        return SuccessResponse(data=await operation(auth.user.id, *args))
    except (BatchError, RecoveryError) as exc:
        raise HTTPException(exc.status_code, exc.reason) from None
    except (LoginError, BrowserStop) as exc:
        raise HTTPException(400, str(exc.reason)) from None


@CncQuoteBatchRouter.post("/preview")
async def preview(data: BatchRequest, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:create"]))]):
    service = get_batch_service()

    async def invoke(_):
        return await service.preview(auth, data)

    return await action(auth, "create", invoke)


@CncQuoteBatchRouter.post("/create")
async def create(data: BatchRequest, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:create"]))]):
    service = get_batch_service()

    async def invoke(_):
        return await service.create(auth, data)

    return await action(auth, "create", invoke)


@CncQuoteBatchRouter.get("/list")
async def list_batches(
    auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:query"]))], offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 50
):
    return await action(auth, "query", get_batch_service().repository.list, offset, limit)


@CncQuoteBatchRouter.get("/detail/{id}")
async def detail(id: UUID, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:detail"]))]):
    return await action(auth, "detail", get_batch_service().repository.detail, str(id))


@CncQuoteBatchRouter.get("/{id}/items")
async def items(
    id: UUID, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:detail"]))], offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=200)] = 100
):
    return await action(auth, "detail", get_batch_service().repository.items, str(id), offset, limit)


@CncQuoteBatchRouter.post("/{id}/cancel")
async def cancel(id: UUID, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:cancel"]))]):
    return await action(auth, "cancel", get_batch_service().repository.cancel, str(id))


@CncQuoteBatchRouter.get("/items/{id}/attempts")
async def attempts(id: UUID, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:detail"]))]):
    return await action(auth, "detail", get_batch_service().repository.attempts, str(id))


@CncQuoteBatchRouter.post("/items/{id}/retry")
async def retry_item(id: UUID, auth: Annotated[AuthSchema, Security(AuthPermission(["module_cnc:cnc_quote_batch:retry"]))]):
    return await action(auth, "retry", get_batch_service().repository.retry_item, str(id))
