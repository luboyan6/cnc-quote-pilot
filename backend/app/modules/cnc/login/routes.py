"""Metadata-only auditing; input and pixels never enter generic request logs."""

import time

from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.background import BackgroundTask

from app.common.enums import RET
from app.core.exceptions import CustomException
from app.core.router_class import _write_operation_log_async
from app.utils.ip_local_util import get_client_ip


class PrivateAccountRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            started = time.perf_counter()
            try:
                response = await original(request)
            except RequestValidationError:
                # Global validation logs exc.errors(), including rejected inputs.
                raise CustomException(msg="INVALID_ACCOUNT_OR_LOGIN_INPUT") from None
            except IntegrityError:
                # SQL parameters can contain encrypted credentials/state. The
                # generic development error response includes those details.
                raise CustomException(msg="ACCOUNT_DATA_INVALID_OR_CONFLICT", code=RET.CONFLICT.code) from None
            except SQLAlchemyError:
                raise CustomException(msg="ACCOUNT_STORAGE_UNAVAILABLE", code=RET.SERVERERR.code) from None
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            if request.method != "GET":
                response.background = BackgroundTask(
                    _write_operation_log_async,
                    {
                        "username": str(getattr(getattr(request.state, "ctx", None), "user_username", None) or "unknown"),
                        "request_path": request.url.path,
                        "request_method": request.method,
                        "request_payload": "{}",
                        "response_code": response.status_code,
                        "response_json": "{}",
                        "process_time": f"{time.perf_counter() - started:.2f}s",
                        "description": self.summary or "",
                        "request_ip": get_client_ip(request),
                    },
                )
            return response

        return handler
