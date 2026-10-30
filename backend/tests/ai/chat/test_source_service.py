"""Run the compiled graph through the owned source-chat service offline."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.exceptions import CustomException
from app.modules.ai.agent.service import AgentService
from app.modules.ai.chat import source_service
from app.modules.ai.chat.model import SourceChatMessage, SourceChatSession
from app.modules.ai.chat.source_repository import SourceChatRepository
from app.modules.ai.chat.source_service import SourceChatService
from app.modules.ai.chat.source_sessions import SourceSessionService


class ReplyModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "controlled-test"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="answer"))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs) -> AsyncIterator[ChatGenerationChunk]:
        yield ChatGenerationChunk(message=AIMessageChunk(content="answer"))


def user(actor_id: int) -> AuthSchema:
    return AuthSchema(user=CoreUserSchema(id=actor_id, username=f"user-{actor_id}"))


@pytest.mark.asyncio
async def test_real_graph_uses_owned_session_and_repairs_visible_history(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SourceChatSession.__table__.create)
            await conn.run_sync(SourceChatMessage.__table__.create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions.begin() as db:
            await SourceChatRepository(db, 1).create("owned", "test")

        async def no_tools(_actor, _refresh, _sessions):
            return []

        monkeypatch.setattr(source_service, "build_read_tools", no_tools)
        seen = []

        @asynccontextmanager
        async def factory(config):
            seen.append(dict(config))
            yield ReplyModel()

        async def refresh_one():
            return user(1)

        saver = InMemorySaver()
        agent = AgentService(saver, model_factory=factory)
        chat = SourceChatService(user(1), agent, refresh_one, sessions)
        config = {"model_id": "test-model", "base_url": "https://test.invalid", "api_key": "model-secret", "temperature": 0.3}
        try:
            first = [event async for event in chat.stream(session_id="owned", turn_id="one", message="first", skills=[], model_config=config)]
            second = [event async for event in chat.stream(session_id="owned", turn_id="two", message="second", skills=[], model_config=config)]
            assert [event.type for event in first] == ["turn.started", "text.delta", "turn.completed"]
            assert second[-1].type == "turn.completed"
            assert seen == [config, config]
            assert "model-secret" not in str(saver.storage)
            assert "model-secret" not in str([e.model_dump() for e in first + second])

            # Repeated rebuild reads checkpoint message IDs and inserts no duplicates.
            await chat.repair_history("owned")
            async with sessions() as db:
                visible = await SourceChatRepository(db, 1).messages("owned")
                assert [(item.role, item.content) for item in visible] == [
                    ("user", "first"), ("assistant", "answer"), ("user", "second"), ("assistant", "answer")
                ]

            async def refresh_two():
                return user(2)

            other = SourceChatService(user(2), agent, refresh_two, sessions)
            with pytest.raises(LookupError, match="CHAT_SESSION_UNAVAILABLE"):
                _ = [event async for event in other.stream(session_id="owned", turn_id="three", message="steal", skills=[], model_config=config)]
            assert len(seen) == 2
        finally:
            await agent.close()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_projection_error_does_not_report_a_durable_success(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SourceChatSession.__table__.create)
            await conn.run_sync(SourceChatMessage.__table__.create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions.begin() as db:
            await SourceChatRepository(db, 1).create("owned", "test")

        async def no_tools(_actor, _refresh, _sessions):
            return []

        async def refresh():
            return user(1)

        @asynccontextmanager
        async def factory(_config):
            yield ReplyModel()

        async def broken_projection(_session):
            raise OSError("internal detail")

        monkeypatch.setattr(source_service, "build_read_tools", no_tools)
        agent = AgentService(InMemorySaver(), model_factory=factory)
        chat = SourceChatService(user(1), agent, refresh, sessions)
        monkeypatch.setattr(chat, "repair_history", broken_projection)
        try:
            events = [event async for event in chat.stream(session_id="owned", turn_id="one", message="hello", skills=[], model_config={})]
            assert events[-1].type == "turn.failed"
            assert events[-1].payload == {"code": "CHAT_HISTORY_UNAVAILABLE"}
            assert "internal detail" not in str([event.model_dump() for event in events])
        finally:
            await agent.close()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_evidence_reference_survives_projection_repair_and_history_read(monkeypatch):
    class ToolModel(ReplyModel):
        def bind_tools(self, tools, **kwargs):
            return self

        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            if any(isinstance(message, ToolMessage) for message in messages):
                yield ChatGenerationChunk(message=AIMessageChunk(content="result ready"))
            else:
                yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[{
                    "name": "cnc_quote_result_detail", "args": '{"result_id":42}', "id": "call-1", "index": 0,
                }]))

    @tool
    async def cnc_quote_result_detail(result_id: int) -> dict:
        """Read one synthetic result."""
        return {"id": result_id, "evidence_available": True}

    async def tools(_actor, _refresh, _sessions):
        return [cnc_quote_result_detail]

    async def refresh():
        return user(1)

    @asynccontextmanager
    async def factory(_config):
        yield ToolModel()

    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SourceChatSession.__table__.create)
            await conn.run_sync(SourceChatMessage.__table__.create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions.begin() as db:
            await SourceChatRepository(db, 1).create("owned", "test")
        monkeypatch.setattr(source_service, "build_read_tools", tools)
        agent = AgentService(InMemorySaver(), model_factory=factory)
        chat = SourceChatService(user(1), agent, refresh, sessions)
        try:
            events = [event async for event in chat.stream(
                session_id="owned", turn_id="one", message="show", skills=["cnc-quote-result"], model_config={}
            )]
            assert [event.payload for event in events if event.type == "evidence.available"] == [{"result_id": 42}]
            assert events[-1].type == "turn.completed"
            await chat.repair_history("owned")
            detail = await SourceSessionService(user(1), sessions).get_session("owned")
            assert [message.evidence_result_ids for message in detail.messages] == [[], [42]]
            with pytest.raises(CustomException):
                await SourceSessionService(user(2), sessions).get_session("owned")
        finally:
            await agent.close()
    finally:
        await engine.dispose()
