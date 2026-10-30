"""Runs only against an explicitly provided, disposable PostgreSQL database."""

import asyncio
import os
import threading
from uuid import uuid4

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.modules.ai.agent.checkpoint import _SelectorBridge, postgres_checkpointer
from app.modules.ai.agent.graph import build_graph
from app.modules.ai.agent.skills import SkillCatalog


@pytest.mark.asyncio
async def test_postgres_checkpoint_survives_saver_restart():
    dsn = os.environ.get("CNC_TEST_AGENT_PG_DSN")
    if not dsn:
        pytest.skip("Set CNC_TEST_AGENT_PG_DSN to a disposable PostgreSQL instance")
    # Explicit setup belongs to deployment/test preparation, never a request.
    async def setup() -> None:
        async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
            await saver.setup()

    await asyncio.to_thread(lambda: asyncio.run(setup(), loop_factory=asyncio.SelectorEventLoop))
    config = {"configurable": {"thread_id": f"isolated-agent-{uuid4()}"}}
    async with postgres_checkpointer(dsn) as saver:
        graph = build_graph(model=FakeListChatModel(responses=["first answer"]), tools=[], catalog=SkillCatalog(), checkpointer=saver)
        await graph.ainvoke({"messages": [HumanMessage(content="first question")], "skill_context": []}, config=config)
    async with postgres_checkpointer(dsn) as saver:
        graph = build_graph(model=FakeListChatModel(responses=["second answer"]), tools=[], catalog=SkillCatalog(), checkpointer=saver)
        before = await graph.aget_state(config)
        assert [message.content for message in before.values["messages"]] == ["first question", "first answer"]
        assert [item async for item in saver.alist(config, limit=3)]
        await graph.ainvoke({"messages": [HumanMessage(content="second question")]}, config=config)
        after = await graph.aget_state(config)
        assert [message.content for message in after.values["messages"]] == ["first question", "first answer", "second question", "second answer"]


@pytest.mark.asyncio
async def test_selector_bridge_waits_for_cancelled_operation_and_joins():
    started, cleaned = threading.Event(), threading.Event()
    bridge = _SelectorBridge()

    async def operation() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0.05)
            cleaned.set()

    try:
        task = asyncio.create_task(bridge.call(operation()))
        assert await asyncio.to_thread(started.wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cleaned.is_set()
    finally:
        await bridge.close()
    assert not bridge.thread.is_alive()
