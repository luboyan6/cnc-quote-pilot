"""Source WS protocol against the actual compiled graph and isolated storage."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import PrivateAttr
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.modules.ai.agent.service import AgentService
from app.modules.ai.chat import source_service, source_socket
from app.modules.ai.chat.model import SourceChatMessage, SourceChatSession
from app.modules.ai.chat.source_repository import SourceChatRepository
from app.modules.ai.chat.source_service import SourceChatService


class Socket:
    def __init__(self):
        self.incoming = asyncio.Queue()
        self.outgoing = asyncio.Queue()
        self.sent = []
        self.app = SimpleNamespace(state=SimpleNamespace(redis=object()))

    async def receive_text(self):
        value = await self.incoming.get()
        if value is None:
            raise WebSocketDisconnect()
        return json.dumps(value)

    async def send_text(self, value):
        self.sent.append(value)
        await self.outgoing.put(value)


class Model(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "controlled-test"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="answer"))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs) -> AsyncIterator[ChatGenerationChunk]:
        yield ChatGenerationChunk(message=AIMessageChunk(content="answer"))


class BlockingModel(Model):
    _started: asyncio.Event = PrivateAttr()
    _closed: asyncio.Event = PrivateAttr()

    def __init__(self, started, closed):
        super().__init__()
        self._started, self._closed = started, closed

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs) -> AsyncIterator[ChatGenerationChunk]:
        self._started.set()
        try:
            await asyncio.Event().wait()
            yield ChatGenerationChunk(message=AIMessageChunk(content="unreachable"))
        finally:
            self._closed.set()


def user(actor_id=1):
    return AuthSchema(user=CoreUserSchema(id=actor_id, username=f"user-{actor_id}"))


@asynccontextmanager
async def context(monkeypatch, model):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SourceChatSession.__table__.create)
        await conn.run_sync(SourceChatMessage.__table__.create)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions.begin() as db:
        await SourceChatRepository(db, 1).create("owned", "test")

    async def no_tools(_actor, _refresh, _sessions):
        return []

    async def selected_config(_redis, _actor):
        return {"model_id": "test", "base_url": "https://test.invalid", "api_key": "secret"}

    async def refresh():
        return user()

    @asynccontextmanager
    async def factory(_config):
        yield model

    monkeypatch.setattr(source_service, "build_read_tools", no_tools)
    monkeypatch.setattr(source_socket, "get_user_model_config", selected_config)
    agent = AgentService(InMemorySaver(), model_factory=factory)
    chat = SourceChatService(user(), agent, refresh, sessions)
    socket = Socket()
    handler = asyncio.create_task(source_socket.run_source_socket(socket, user(), chat, socket.app.state.redis))
    socket.handler = handler
    try:
        yield socket, agent, sessions
    finally:
        await socket.incoming.put(None)
        await asyncio.wait_for(handler, timeout=1)
        await agent.close()
        await engine.dispose()


async def read(socket):
    return await asyncio.wait_for(socket.outgoing.get(), timeout=2)


@pytest.mark.asyncio
async def test_v2_streams_real_graph_events_and_projects_history(monkeypatch):
    async with context(monkeypatch, Model()) as (socket, _agent, sessions):
        await socket.incoming.put({"protocol_version": 2, "session_id": "owned", "turn_id": "t1", "message": "hello", "skills": ["cnc-assistant"]})
        events = [json.loads(await read(socket)) for _ in range(4)]
        assert [item["type"] for item in events] == ["turn.started", "skill.activated", "text.delta", "turn.completed"]
        assert [item["seq"] for item in events] == [1, 2, 3, 4]
        assert all(item["session_id"] == "owned" and item["turn_id"] == "t1" for item in events)
        assert events[1]["payload"]["name"] == "cnc-assistant"
        assert "secret" not in str(events)
        async with sessions() as db:
            assert [(m.role, m.content) for m in await SourceChatRepository(db, 1).messages("owned")] == [("user", "hello"), ("assistant", "answer")]


@pytest.mark.asyncio
async def test_v2_stop_awaits_real_model_cleanup_and_rejects_stale_turn(monkeypatch):
    started, closed = asyncio.Event(), asyncio.Event()
    async with context(monkeypatch, BlockingModel(started, closed)) as (socket, agent, sessions):
        await socket.incoming.put({"protocol_version": 2, "session_id": "owned", "turn_id": "t1", "message": "hello", "skills": []})
        assert json.loads(await read(socket))["type"] == "turn.started"
        await asyncio.wait_for(started.wait(), timeout=1)
        await socket.incoming.put({"protocol_version": 2, "action": "stop", "session_id": "owned", "turn_id": "old"})
        assert json.loads(await read(socket))["payload"]["code"] == "NO_ACTIVE_TURN"
        assert not closed.is_set()
        await socket.incoming.put({"protocol_version": 2, "action": "stop", "session_id": "owned", "turn_id": "t1"})
        stopped = json.loads(await read(socket))
        assert stopped["type"] == "turn.stopped" and stopped["seq"] == 2
        assert stopped["turn_id"] == "t1"
        assert stopped["payload"]["history_status"] == "ready"
        assert closed.is_set()
        assert not agent._turns
        assert [json.loads(value)["type"] for value in socket.sent] == ["turn.started", "request.error", "turn.stopped"]
        async with sessions() as db:
            assert [(m.role, m.content) for m in await SourceChatRepository(db, 1).messages("owned")] == [("user", "hello")]


@pytest.mark.asyncio
async def test_delete_before_stop_keeps_tombstone_and_reports_unsaved_history(monkeypatch):
    started, closed = asyncio.Event(), asyncio.Event()
    async with context(monkeypatch, BlockingModel(started, closed)) as (socket, _agent, sessions):
        await socket.incoming.put({"protocol_version": 2, "session_id": "owned", "turn_id": "t1", "message": "hello", "skills": []})
        assert json.loads(await read(socket))["type"] == "turn.started"
        await asyncio.wait_for(started.wait(), timeout=1)
        async with sessions.begin() as db:
            assert await SourceChatRepository(db, 1).delete("owned")
        await socket.incoming.put({"protocol_version": 2, "action": "stop", "session_id": "owned", "turn_id": "t1"})
        stopped = json.loads(await read(socket))
        assert stopped["type"] == "turn.stopped"
        assert stopped["payload"]["history_status"] == "unavailable"
        assert closed.is_set()
        async with sessions() as db:
            assert await SourceChatRepository(db, 1).get("owned") is None
            with pytest.raises(LookupError):
                await SourceChatRepository(db, 1).messages("owned")


@pytest.mark.asyncio
async def test_unversioned_source_stream_keeps_legacy_frames(monkeypatch):
    async with context(monkeypatch, Model()) as (socket, _agent, _sessions):
        await socket.incoming.put({"session_id": "owned", "message": "hello"})
        assert [await read(socket), await read(socket)] == ["answer", "[DONE]"]


@pytest.mark.asyncio
async def test_source_disconnect_closes_the_actual_model_stream(monkeypatch):
    started, closed = asyncio.Event(), asyncio.Event()
    async with context(monkeypatch, BlockingModel(started, closed)) as (socket, agent, _sessions):
        await socket.incoming.put({"protocol_version": 2, "session_id": "owned", "turn_id": "t1", "message": "hello", "skills": []})
        assert json.loads(await read(socket))["type"] == "turn.started"
        await asyncio.wait_for(started.wait(), timeout=1)
        await socket.incoming.put(None)
        await asyncio.wait_for(socket.handler, timeout=1)
        assert closed.is_set()
        assert not agent._turns


@pytest.mark.asyncio
async def test_unversioned_stop_uses_legacy_marker(monkeypatch):
    started, closed = asyncio.Event(), asyncio.Event()
    async with context(monkeypatch, BlockingModel(started, closed)) as (socket, _agent, _sessions):
        await socket.incoming.put({"session_id": "owned", "message": "hello"})
        await asyncio.wait_for(started.wait(), timeout=1)
        await socket.incoming.put({"action": "stop", "session_id": "owned"})
        assert await read(socket) == "[STOPPED]"
        assert closed.is_set()
        assert socket.sent == ["[STOPPED]"]


@pytest.mark.asyncio
async def test_v2_attachment_only_turn_passes_validated_request_to_graph(monkeypatch):
    request_id = uuid4()
    seen = []

    async def references(_chat, request_ids):
        seen.extend(request_ids)
        return ["图纸 ID: 42"]

    monkeypatch.setattr(SourceChatService, "_drawing_references", references)
    async with context(monkeypatch, Model()) as (socket, _agent, sessions):
        await socket.incoming.put({"protocol_version": 2, "session_id": "owned", "turn_id": "t1", "drawing_uploads": [str(request_id)]})
        events = [json.loads(await read(socket)) for _ in range(3)]
        assert [event["type"] for event in events] == ["turn.started", "text.delta", "turn.completed"]
        assert seen == [request_id]
        async with sessions() as db:
            assert "图纸 ID: 42" in (await SourceChatRepository(db, 1).messages("owned"))[0].content


@pytest.mark.asyncio
async def test_v2_unavailable_attachment_fails_before_turn_started(monkeypatch):
    async def unavailable(_chat, _request_ids):
        raise source_service.DrawingReferenceUnavailable("internal")

    monkeypatch.setattr(SourceChatService, "_drawing_references", unavailable)
    async with context(monkeypatch, Model()) as (socket, _agent, sessions):
        await socket.incoming.put({"protocol_version": 2, "session_id": "owned", "turn_id": "t1", "drawing_uploads": [str(uuid4())]})
        event = json.loads(await read(socket))
        assert event["type"] == "turn.failed"
        assert event["payload"] == {"code": "CHAT_DRAWING_UNAVAILABLE"}
        async with sessions() as db:
            assert await SourceChatRepository(db, 1).messages("owned") == []


@pytest.mark.asyncio
async def test_v2_rejects_duplicate_attachment_requests(monkeypatch):
    request_id = str(uuid4())
    async with context(monkeypatch, Model()) as (socket, _agent, _sessions):
        await socket.incoming.put({"protocol_version": 2, "session_id": "owned", "turn_id": "t1", "drawing_uploads": [request_id, request_id]})
        # Invalid requests have no admitted turn or side effects.
        assert json.loads(await read(socket))["payload"]["code"] == "INVALID_REQUEST"
