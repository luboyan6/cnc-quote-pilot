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
from app.modules.cnc.cnc_quote_schedule import controller
from app.modules.cnc.monitor.contracts import ScheduleError


class ScheduleHttpTests(unittest.IsolatedAsyncioTestCase):
    def test_api_v1_registration_exposes_schedule_routes(self):
        app = FastAPI()
        app.include_router(api_v1)
        paths = app.openapi()["paths"]
        self.assertIn("/cnc/cnc_quote_schedule/create", paths)
        self.assertIn("/cnc/cnc_quote_schedule/list", paths)
        self.assertIn("/cnc/cnc_quote_schedule/detail/{id}", paths)
        self.assertIn("/cnc/cnc_quote_schedule/{id}/pause", paths)
        self.assertIn("/cnc/cnc_quote_schedule/{id}/resume", paths)
        self.assertIn("/cnc/cnc_quote_schedule/{id}/rounds", paths)

    async def test_schedule_endpoints_permissions_and_responses(self):
        app = FastAPI()
        handle_exception(app)
        app.include_router(controller.CncQuoteScheduleRouter, prefix="/cnc")

        auth = AuthSchema(
            user=CoreUserSchema(id=7),
            permissions=[
                "module_cnc:cnc_quote_schedule:create",
                "module_cnc:cnc_quote_schedule:query",
                "module_cnc:cnc_quote_schedule:detail",
                "module_cnc:cnc_quote_schedule:update",
            ],
        )

        async def current():
            return auth

        app.dependency_overrides[get_current_user] = current

        sched_id = str(uuid4())
        service = SimpleNamespace(
            authorize=AsyncMock(return_value=auth),
            create=AsyncMock(return_value={"id": sched_id, "name": "Test Sched"}),
            list=AsyncMock(return_value={"total": 1, "items": [{"id": sched_id}]}),
            detail=AsyncMock(return_value={"id": sched_id, "name": "Test Sched"}),
            pause=AsyncMock(return_value={"id": sched_id, "status": "PAUSED"}),
            resume=AsyncMock(return_value={"id": sched_id, "status": "ENABLED"}),
            rounds=AsyncMock(return_value=[{"round_no": 1, "status": "RUNNING"}]),
        )

        with (
            patch.object(controller, "get_monitor_service", return_value=service),
            patch("app.modules.cnc.login.routes._write_operation_log_async", AsyncMock()),
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                # 1. Create
                body = {
                    "name": "Test Sched",
                    "interval_minutes": 60,
                    "targets": [{"config_id": 1, "quantities": [5]}],
                }
                resp = await client.post("/cnc/cnc_quote_schedule/create", json=body)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["data"]["name"], "Test Sched")

                # 2. List
                resp = await client.get("/cnc/cnc_quote_schedule/list")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["data"]["total"], 1)

                # 3. Detail
                resp = await client.get(f"/cnc/cnc_quote_schedule/detail/{sched_id}")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["data"]["id"], sched_id)

                # 4. Pause
                resp = await client.post(f"/cnc/cnc_quote_schedule/{sched_id}/pause")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["data"]["status"], "PAUSED")

                # 5. Resume
                resp = await client.post(f"/cnc/cnc_quote_schedule/{sched_id}/resume")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.json()["data"]["status"], "ENABLED")

                # 6. Rounds
                resp = await client.get(f"/cnc/cnc_quote_schedule/{sched_id}/rounds")
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(len(resp.json()["data"]), 1)

                # 7. Error handling
                service.detail.side_effect = ScheduleError("SCHEDULE_NOT_FOUND", 404)
                resp = await client.get(f"/cnc/cnc_quote_schedule/detail/{sched_id}")
                self.assertEqual(resp.status_code, 404)
                self.assertIn("SCHEDULE_NOT_FOUND", resp.text)


if __name__ == "__main__":
    unittest.main()
