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
from app.modules.cnc.batch.contracts import BatchError
from app.modules.cnc.cnc_quote_batch import controller
from app.modules.cnc.quote.contracts import InstantQuote


class BatchHttpTests(unittest.IsolatedAsyncioTestCase):
    def test_api_v1_registration_exposes_batch_routes_once(self):
        app = FastAPI()
        app.include_router(api_v1)
        with patch("warnings.warn") as warn:
            paths = app.openapi()["paths"]
        self.assertIn("post", paths["/cnc/cnc_quote_batch/create"])
        self.assertIn("get", paths["/cnc/cnc_quote_batch/items/{id}/attempts"])
        self.assertFalse(any("Duplicate Operation ID" in str(call) for call in warn.call_args_list))

    async def test_routes_permissions_conflict_and_unknown_declaration_default(self):
        app = FastAPI()
        handle_exception(app)
        app.include_router(controller.CncQuoteBatchRouter, prefix="/cnc")
        auth = AuthSchema(user=CoreUserSchema(id=7), permissions=[])

        async def current():
            return auth

        app.dependency_overrides[get_current_user] = current
        service = SimpleNamespace(authorize=AsyncMock(return_value=auth), create=AsyncMock(side_effect=BatchError("BATCH_REQUEST_CONFLICT", 409)))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            body = {"request_id": str(uuid4()), "targets": [{"config_id": 5, "quantities": [1, 2]}]}
            with patch.object(controller, "get_batch_service", return_value=service), patch("app.modules.cnc.login.routes._write_operation_log_async", AsyncMock()):
                response = await client.post("/cnc/cnc_quote_batch/create", json=body)
                self.assertEqual(response.status_code, 403)
                service.create.assert_not_awaited()
                auth.permissions = ["module_cnc:cnc_quote_batch:create"]
                response = await client.post("/cnc/cnc_quote_batch/create", json=body)
                self.assertEqual(response.status_code, 409)
                self.assertNotIn("password", response.text)
                response = await client.post("/cnc/cnc_quote_batch/create", json=body | {"password": "private"})
                self.assertEqual(response.status_code, 400)
        paths = app.openapi()["paths"]
        self.assertIn("/cnc/cnc_quote_batch/items/{id}/attempts", paths)
        self.assertEqual(len([p for p in paths if p.endswith("/create")]), 1)
        self.assertIsNone(InstantQuote(account_id=31).export_controlled)
