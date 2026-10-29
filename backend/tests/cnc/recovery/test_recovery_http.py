import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from fastapi import FastAPI

from app.api.v1.routers import api_v1
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import handle_exception
from app.modules.cnc.cnc_quote_batch import controller
from app.modules.cnc.recovery.contracts import RecoveryError


class RecoveryHttpTests(unittest.IsolatedAsyncioTestCase):
    def test_api_v1_registration_exposes_retry_route(self):
        app = FastAPI()
        app.include_router(api_v1)
        paths = app.openapi()["paths"]
        self.assertIn("/cnc/cnc_quote_batch/items/{id}/retry", paths)
        self.assertIn("post", paths["/cnc/cnc_quote_batch/items/{id}/retry"])

    async def test_retry_endpoint_permissions_and_responses(self):
        app = FastAPI()
        handle_exception(app)
        app.include_router(controller.CncQuoteBatchRouter, prefix="/cnc")

        auth = AuthSchema(user=CoreUserSchema(id=7), permissions=["module_cnc:cnc_quote_batch:retry"])

        async def current():
            return auth

        app.dependency_overrides[get_current_user] = current

        item_id = str(uuid4())
        service = SimpleNamespace(
            authorize=AsyncMock(return_value=auth),
            repository=SimpleNamespace(
                retry_item=AsyncMock(return_value={"id": item_id, "exec_status": "PENDING"}),
            ),
        )

        with (
            patch.object(controller, "get_batch_service", return_value=service),
            patch("app.modules.cnc.login.routes._write_operation_log_async", AsyncMock()),
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                # 1. Success case
                resp = await client.post(f"/cnc/cnc_quote_batch/items/{item_id}/retry")
                self.assertEqual(resp.status_code, 200)
                body = resp.json()
                self.assertEqual(body["data"]["exec_status"], "PENDING")
                service.repository.retry_item.assert_awaited_once_with(7, item_id)

                # 2. RecoveryError (e.g. uncertain mutation forbidden)
                service.repository.retry_item = AsyncMock(side_effect=RecoveryError("BATCH_UNCERTAIN_MUTATION_RETRY_FORBIDDEN", 400))
                resp = await client.post(f"/cnc/cnc_quote_batch/items/{item_id}/retry")
                self.assertEqual(resp.status_code, 400)
                self.assertIn("BATCH_UNCERTAIN_MUTATION_RETRY_FORBIDDEN", resp.text)

                # 3. Permission denied case
                service.authorize.side_effect = RecoveryError("BATCH_PERMISSION_REVOKED", 403)
                resp = await client.post(f"/cnc/cnc_quote_batch/items/{item_id}/retry")
                self.assertEqual(resp.status_code, 403)
                self.assertIn("BATCH_PERMISSION_REVOKED", resp.text)


if __name__ == "__main__":
    unittest.main()
