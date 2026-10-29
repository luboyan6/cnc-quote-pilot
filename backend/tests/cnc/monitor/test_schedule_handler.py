import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.ap_scheduler import SchedulerUtil
from app.modules.task.cronjob.node.handlers.cnc_monitor import scan_due


class ScheduleHandlerTests(unittest.TestCase):
    def test_leader_registers_single_monitor_scan(self):
        scheduler = MagicMock()
        scheduler.running = False
        with patch("app.core.ap_scheduler.scheduler", scheduler), patch("app.core.ap_scheduler.settings.CNC_BATCH_ENABLED", True):
            SchedulerUtil._start_scheduler_local()
        kwargs = scheduler.add_job.call_args.kwargs
        self.assertEqual(kwargs["id"], "cnc-monitor-scan")
        self.assertEqual(kwargs["seconds"], 60)
        self.assertEqual(kwargs["max_instances"], 1)
        self.assertTrue(kwargs["coalesce"])

    def test_builtin_resolution(self):
        handler = SchedulerUtil.resolve_builtin_handler("builtin:cnc_monitor.scan_due")
        self.assertIsNotNone(handler)
        self.assertEqual(handler, scan_due)

    def test_scan_due_invocation(self):
        fake_results = [{"schedule_id": "s1", "status": "RUNNING", "round_no": 1}]
        with patch("app.modules.task.cronjob.node.handlers.cnc_monitor.get_monitor_service") as mock_get:
            mock_service = AsyncMock()
            mock_service.scan_due.return_value = fake_results
            mock_get.return_value = mock_service

            result = scan_due()
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["dispatched_count"], 1)
            self.assertEqual(result["results"], fake_results)


@pytest.mark.asyncio
async def test_builtin_handler_uses_scheduler_event_loop():
    scheduler = MagicMock()
    scheduler._eventloop = asyncio.get_running_loop()
    service = AsyncMock()
    service.scan_due.return_value = []
    with patch("app.core.ap_scheduler.scheduler", scheduler), patch("app.modules.task.cronjob.node.handlers.cnc_monitor.get_monitor_service", return_value=service):
        result = await asyncio.to_thread(scan_due)
    assert result["status"] == "ok"
    service.scan_due.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
