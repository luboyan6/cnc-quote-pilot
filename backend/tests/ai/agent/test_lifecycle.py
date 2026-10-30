from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.modules.ai.agent import lifecycle
from app.modules.ai.agent.lifecycle import open_agent_service, require_chat_integration


def test_source_engine_refuses_to_start_before_chat_is_integrated():
    settings = SimpleNamespace(WORKERS=1, DATABASE_TYPE="postgres")
    with pytest.raises(RuntimeError, match="AI_SOURCE_CHAT_INTEGRATION_NOT_READY"):
        require_chat_integration(settings)


@pytest.mark.asyncio
async def test_lifespan_closes_agent_then_saver_on_failure(monkeypatch):
    actions = []

    @asynccontextmanager
    async def saver(dsn):
        try:
            yield InMemorySaver()
        finally:
            actions.append("saver_closed")

    monkeypatch.setattr(lifecycle, "postgres_checkpointer", saver)
    settings = SimpleNamespace(WORKERS=1, DATABASE_TYPE="postgres", DB_URI="postgresql+psycopg://user:pass@localhost/db")
    with pytest.raises(RuntimeError, match="controlled failure"):
        async with open_agent_service(settings) as service:
            raise RuntimeError("controlled failure")
    assert service._closed is True
    assert actions == ["saver_closed"]
