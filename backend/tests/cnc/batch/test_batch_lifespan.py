"""Lifespan failure paths release all dependencies after stopping the consumer."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from app import lifespan


@pytest.mark.parametrize("failure", [None, "start", "mcp", "body", "stop", "login"])
async def test_shutdown_runs_all_callbacks_even_when_a_stage_fails(failure):
    events = []

    def operation(name):
        async def invoke(*args, **kwargs):
            events.append(name)
            if failure == name:
                raise RuntimeError(name)

        return AsyncMock(side_effect=invoke)

    dispatcher = SimpleNamespace(start=operation("start"), stop=operation("stop"), batches=SimpleNamespace(repository=SimpleNamespace(sessions=object()), quotes=object()))
    recovery = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())

    @asynccontextmanager
    async def mcp(_app):
        if failure == "mcp":
            raise RuntimeError("mcp")
        yield

    app = FastAPI()
    app.state.redis = object()
    with (
        patch("app.settings.CNC_BATCH_ENABLED", True),
        patch("app.settings.WORKERS", 1),
        patch("app.scripts.initialize.InitializeData.init_db", new=AsyncMock()),
        patch("app.modules.ai.chat.crud.init_agno_tables", new=AsyncMock()),
        patch("app.core.redis_crud.redis_connect", new=operation("redis")),
        patch("app.modules.system.params.service.ParamsService.init_cache", new=AsyncMock()),
        patch("app.modules.system.dict.service.DictDataService.init_cache", new=AsyncMock()),
        patch("app.core.ap_scheduler.SchedulerUtil.init_scheduler", new=AsyncMock()),
        patch("app.core.ap_scheduler.SchedulerUtil.shutdown", new=operation("scheduler")),
        patch("app.core.database.async_engine", new=SimpleNamespace(dispose=operation("database"))),
        patch("app.modules.cnc.login.runtime.close_login_sessions", new=operation("login")),
        patch("app.modules.cnc.batch.dispatcher.QuoteDispatcher", return_value=dispatcher),
        patch("app.modules.cnc.recovery.scanner.RecoveryScanner", return_value=recovery),
        patch("app.mcp_lifespan", mcp),
        patch("app.console_start"),
        patch("app.console_end", side_effect=lambda: events.append("console")),
    ):
        if failure:
            with pytest.raises(RuntimeError, match=failure):
                async with lifespan(app):
                    if failure == "body":
                        raise RuntimeError("body")
        else:
            async with lifespan(app):
                pass
    assert events[-6:] == ["stop", "login", "scheduler", "redis", "database", "console"]
    dispatcher.start.assert_awaited_once()
    dispatcher.stop.assert_awaited_once()
    if failure != "start":
        recovery.start.assert_awaited_once()
        recovery.stop.assert_awaited_once()


async def test_unsupported_topology_fails_before_initializing_resources():
    with (
        patch("app.settings.CNC_BATCH_ENABLED", True),
        patch("app.settings.WORKERS", 2),
        patch("app.scripts.initialize.InitializeData.init_db", new=AsyncMock()) as initialize,
    ):
        with pytest.raises(RuntimeError, match="CNC_BATCH_REQUIRES_SINGLE_WORKER"):
            async with lifespan(FastAPI()):
                pass
    initialize.assert_not_awaited()
