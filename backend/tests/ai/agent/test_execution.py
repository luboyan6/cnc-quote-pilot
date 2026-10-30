import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import PrivateAttr

from app.modules.ai.agent.events import evidence_reference
from app.modules.ai.agent.service import AgentService
from app.modules.ai.agent.skills import SkillCatalog


class BlockingModel(BaseChatModel):
    _started: asyncio.Event = PrivateAttr()
    _closed: asyncio.Event = PrivateAttr()

    def __init__(self, started: asyncio.Event, closed: asyncio.Event):
        super().__init__()
        self._started = started
        self._closed = closed

    @property
    def _llm_type(self) -> str:
        return "controlled-test"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise AssertionError("synchronous generation must not run")

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs) -> AsyncIterator[ChatGenerationChunk]:
        self._started.set()
        try:
            await asyncio.Event().wait()
            yield ChatGenerationChunk(message=AIMessageChunk(content="unreachable"))
        finally:
            self._closed.set()


class ReplyModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "controlled-test"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="ok"))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs) -> AsyncIterator[ChatGenerationChunk]:
        yield ChatGenerationChunk(message=AIMessageChunk(content="ok"))


def model_factory(model: BaseChatModel):
    @asynccontextmanager
    async def create(config: dict[str, Any]):
        yield model

    return create


def request(service: AgentService, actor_id: int = 1, turn_id: str = "turn"):
    return service.stream(actor_id=actor_id, session_id="session", turn_id=turn_id, message="hi", skills=[], model_config={}, tools=[])


@pytest.mark.asyncio
async def test_native_graph_cancel_before_first_token_awaits_model_cleanup():
    started, closed = asyncio.Event(), asyncio.Event()
    service = AgentService(InMemorySaver(), model_factory=model_factory(BlockingModel(started, closed)))
    stream = request(service)
    assert (await anext(stream)).type == "turn.started"
    pending = asyncio.create_task(anext(stream))
    await asyncio.wait_for(started.wait(), 2)
    before = time.monotonic()
    assert await asyncio.wait_for(service.stop(1, "session", "turn"), 1)
    assert closed.is_set()
    assert time.monotonic() - before < 1
    assert (await pending).type == "turn.stopped"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    await service.close()


@pytest.mark.asyncio
async def test_stream_has_one_terminal_and_owner_namespaces_are_distinct():
    service = AgentService(InMemorySaver(), model_factory=model_factory(ReplyModel()))
    events = [event async for event in request(service)]
    assert [e.type for e in events] == ["turn.started", "text.delta", "turn.completed"]
    assert [e.seq for e in events] == [1, 2, 3]
    assert events[1].payload == {"text": "ok"}
    assert service._thread_id(1, "session") != service._thread_id(2, "session")
    await service.close()


@pytest.mark.asyncio
async def test_authorized_tool_output_emits_only_a_safe_evidence_reference():
    class ToolModel(ReplyModel):
        def bind_tools(self, tools, **kwargs):
            return self

        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            if any(isinstance(message, ToolMessage) for message in messages):
                yield ChatGenerationChunk(message=AIMessageChunk(content="done"))
            else:
                yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[{
                    "name": "cnc_quote_result_detail", "args": '{"result_id":9}', "id": "call-1", "index": 0,
                }]))

    @tool
    async def cnc_quote_result_detail(result_id: int) -> dict:
        """Read one synthetic result."""
        return {"id": result_id, "evidence_available": True, "private": "not-in-event"}

    service = AgentService(InMemorySaver(), model_factory=model_factory(ToolModel()))
    try:
        events = [event async for event in service.stream(
            actor_id=1, session_id="session", turn_id="turn", message="show evidence", skills=["cnc-quote-result"],
            model_config={}, tools=[cnc_quote_result_detail],
        )]
        references = [event.payload for event in events if event.type == "evidence.available"]
        assert references == [{"result_id": 9}]
        assert "not-in-event" not in str([event.model_dump() for event in events])
        assert events[-1].type == "turn.completed"
    finally:
        await service.close()


def test_evidence_reference_rejects_wrong_tools_and_malformed_data():
    valid = '{"id":9,"evidence_available":true}'
    assert evidence_reference("cnc_quote_result_detail", valid) == {"result_id": 9}
    for name, content in [
        ("other_tool", valid),
        ("cnc_quote_result_detail", '{"id":true,"evidence_available":true}'),
        ("cnc_quote_result_detail", '{"id":9,"evidence_available":false}'),
        ("cnc_quote_result_detail", "not-json"),
    ]:
        assert evidence_reference(name, content) is None


@pytest.mark.asyncio
async def test_disconnect_and_shutdown_await_active_graph_cleanup():
    started, closed = asyncio.Event(), asyncio.Event()
    service = AgentService(InMemorySaver(), model_factory=model_factory(BlockingModel(started, closed)))
    stream = request(service)
    await anext(stream)
    pending = asyncio.create_task(anext(stream))
    await asyncio.wait_for(started.wait(), 2)
    await asyncio.wait_for(service.close(), 1)
    assert closed.is_set()
    assert (await pending).type == "turn.stopped"
    await stream.aclose()


@pytest.mark.asyncio
async def test_disconnect_cancels_generation_and_releases_owned_turn():
    started, closed = asyncio.Event(), asyncio.Event()
    service = AgentService(InMemorySaver(), model_factory=model_factory(BlockingModel(started, closed)))

    async def consume():
        async for _ in request(service):
            pass

    consumer = asyncio.create_task(consume())
    try:
        await asyncio.wait_for(started.wait(), 2)
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(consumer, 1)
        assert closed.is_set()
        assert not service._turns
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_timeout_closes_model_before_emitting_failed_terminal():
    started, closed = asyncio.Event(), asyncio.Event()
    service = AgentService(InMemorySaver(), model_factory=model_factory(BlockingModel(started, closed)), timeout=1.0)
    try:
        events = [event async for event in request(service)]
        assert started.is_set() and closed.is_set()
        assert [event.type for event in events] == ["turn.started", "turn.failed"]
        assert not service._turns
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_stop_closes_local_openai_http_stream_before_first_token():
    started, body_closed, client_closed = asyncio.Event(), asyncio.Event(), asyncio.Event()

    class SlowBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            started.set()
            await asyncio.Event().wait()
            yield b"data: [DONE]\n\n"

        async def aclose(self):
            body_closed.set()

    async def handler(request):
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=SlowBody())

    @asynccontextmanager
    async def create(config):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:
                yield ChatOpenAI(model="test", api_key="test", base_url="https://test.invalid/v1", http_async_client=client, max_retries=0)
            finally:
                await client.aclose()
                client_closed.set()

    service = AgentService(InMemorySaver(), model_factory=create)
    stream = request(service)
    await anext(stream)
    pending = asyncio.create_task(anext(stream))
    await asyncio.wait_for(started.wait(), 5)
    await asyncio.wait_for(service.stop(1, "session", "turn"), 1)
    assert body_closed.is_set() and client_closed.is_set()
    assert (await pending).type == "turn.stopped"
    await stream.aclose()
    await service.close()


@pytest.mark.asyncio
async def test_stop_closes_real_loopback_tcp_stream():
    started, disconnected = asyncio.Event(), asyncio.Event()

    async def serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            headers = await reader.readuntil(b"\r\n\r\n")
            length = 0
            for line in headers.split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":", 1)[1].strip())
            if length:
                await reader.readexactly(length)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n")
            await writer.drain()
            started.set()
            if await reader.read(1) == b"":
                disconnected.set()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    @asynccontextmanager
    async def create(config):
        async with httpx.AsyncClient(timeout=10) as client:
            yield ChatOpenAI(model="test", api_key="test", base_url=f"http://127.0.0.1:{port}/v1", http_async_client=client, max_retries=0)

    service = AgentService(InMemorySaver(), model_factory=create)
    stream = request(service)
    try:
        await anext(stream)
        pending = asyncio.create_task(anext(stream))
        await asyncio.wait_for(started.wait(), 5)
        await asyncio.wait_for(service.stop(1, "session", "turn"), 1)
        assert (await pending).type == "turn.stopped"
        await asyncio.wait_for(disconnected.wait(), 2)
    finally:
        await stream.aclose()
        await service.close()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_stop_cancels_waiting_native_async_tool(tmp_path):
    started, closed = asyncio.Event(), asyncio.Event()

    @tool
    async def wait_tool() -> str:
        """Wait for a controlled test event."""
        started.set()
        try:
            await asyncio.Event().wait()
            return "unreachable"
        finally:
            closed.set()

    class ToolModel(ReplyModel):
        def bind_tools(self, tools, **kwargs):
            return self

        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[{"name": "wait_tool", "args": "{}", "id": "call-1", "index": 0}]))

    skill = tmp_path / "test-tool"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: test-tool\ndescription: Test\nallowed-tools: [wait_tool]\n---\nUse the tool.", encoding="utf-8")
    service = AgentService(InMemorySaver(), SkillCatalog(tmp_path), model_factory=model_factory(ToolModel()))
    stream = service.stream(actor_id=1, session_id="s", turn_id="t", message="hi", skills=["test-tool"], model_config={}, tools=[wait_tool])
    assert (await anext(stream)).type == "turn.started"
    assert (await anext(stream)).type == "skill.activated"
    assert (await anext(stream)).type == "tool.started"
    pending = asyncio.create_task(anext(stream))
    await asyncio.wait_for(started.wait(), 2)
    await asyncio.wait_for(service.stop(1, "s", "t"), 1)
    assert closed.is_set()
    assert (await pending).type == "turn.stopped"
    await stream.aclose()
    await service.close()


@pytest.mark.asyncio
async def test_failed_tool_emits_safe_failure_event(tmp_path):
    @tool
    async def failing_tool() -> str:
        """Raise an internal failure for the event boundary test."""
        raise RuntimeError("private-detail-must-not-be-exposed")

    class ToolModel(ReplyModel):
        def bind_tools(self, tools, **kwargs):
            return self

        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            from langchain_core.messages import ToolMessage

            if any(isinstance(message, ToolMessage) for message in messages):
                yield ChatGenerationChunk(message=AIMessageChunk(content="handled"))
            else:
                yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[{"name": "failing_tool", "args": "{}", "id": "call-1", "index": 0}]))

    skill = tmp_path / "test-tool"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: test-tool\ndescription: Test\nallowed-tools: [failing_tool]\n---\nUse the tool.", encoding="utf-8")
    service = AgentService(InMemorySaver(), SkillCatalog(tmp_path), model_factory=model_factory(ToolModel()))
    try:
        events = [event async for event in service.stream(actor_id=1, session_id="s", turn_id="t", message="hi", skills=["test-tool"], model_config={}, tools=[failing_tool])]
        assert [event.type for event in events] == ["turn.started", "skill.activated", "tool.started", "tool.failed", "text.delta", "turn.completed"]
        assert "private-detail-must-not-be-exposed" not in str([event.model_dump() for event in events])
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_slow_consumer_does_not_hold_cancelled_model_open():
    closed = asyncio.Event()

    class FloodModel(ReplyModel):
        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            try:
                while True:
                    yield ChatGenerationChunk(message=AIMessageChunk(content="x"))
                    await asyncio.sleep(0)
            finally:
                closed.set()

    service = AgentService(InMemorySaver(), model_factory=model_factory(FloodModel()), queue_size=1)
    stream = request(service)
    await anext(stream)
    await asyncio.sleep(0.1)
    await asyncio.wait_for(service.stop(1, "session", "turn"), 1)
    assert closed.is_set()
    assert (await anext(stream)).type == "turn.stopped"
    await stream.aclose()
    await service.close()


@pytest.mark.asyncio
async def test_parallel_users_keep_model_secrets_out_of_state_and_events():
    seen = []

    @asynccontextmanager
    async def create(config):
        seen.append(dict(config))
        yield ReplyModel()

    saver = InMemorySaver()
    service = AgentService(saver, model_factory=create)

    async def run(actor, secret):
        return [event async for event in service.stream(actor_id=actor, session_id="same", turn_id=f"turn-{actor}", message="hi", skills=[], model_config={"api_key": secret, "base_url": f"https://{actor}.invalid", "model_id": f"model-{actor}"}, tools=[])]

    first, second = await asyncio.gather(run(1, "secret-one"), run(2, "secret-two"))
    assert {item["api_key"] for item in seen} == {"secret-one", "secret-two"}
    serialized = str(saver.storage) + str([e.model_dump() for e in first + second])
    assert "secret-one" not in serialized and "secret-two" not in serialized
    assert "1.invalid" not in serialized and "2.invalid" not in serialized
    await service.close()


@pytest.mark.asyncio
async def test_same_owned_session_rejects_concurrent_turn_and_wrong_owner_cannot_stop():
    started, closed = asyncio.Event(), asyncio.Event()
    service = AgentService(InMemorySaver(), model_factory=model_factory(BlockingModel(started, closed)))
    stream = request(service)
    await anext(stream)
    pending = asyncio.create_task(anext(stream))
    await asyncio.wait_for(started.wait(), 2)
    competing = request(service, turn_id="another")
    with pytest.raises(RuntimeError, match="AGENT_SESSION_BUSY"):
        await anext(competing)
    assert not await service.stop(2, "session", "turn")
    assert not await service.stop(1, "session", "another")
    await service.stop(1, "session", "turn")
    assert (await pending).type == "turn.stopped"
    await stream.aclose()
    await service.close()


@pytest.mark.asyncio
async def test_stop_does_not_claim_completed_producer_was_stopped():
    service = AgentService(InMemorySaver(), model_factory=model_factory(ReplyModel()))
    stream = request(service)
    try:
        assert (await anext(stream)).type == "turn.started"
        await asyncio.wait_for(asyncio.shield(service._turns[(1, "session")].task), 2)
        assert not await service.stop(1, "session", "turn")
        events = [event async for event in stream]
        assert [event.type for event in events] == ["text.delta", "turn.completed"]
    finally:
        await stream.aclose()
        await service.close()


@pytest.mark.asyncio
async def test_repeated_stop_and_shutdown_do_not_interrupt_model_cleanup():
    started, cleaning, release, cleaned = (asyncio.Event() for _ in range(4))

    class CleanupModel(ReplyModel):
        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
                yield ChatGenerationChunk(message=AIMessageChunk(content="unreachable"))
            finally:
                cleaning.set()
                await release.wait()
                cleaned.set()

    service = AgentService(InMemorySaver(), model_factory=model_factory(CleanupModel()))
    stream = request(service)
    first = second = shutdown = pending = None
    try:
        await anext(stream)
        pending = asyncio.create_task(anext(stream))
        await asyncio.wait_for(started.wait(), 2)
        first = asyncio.create_task(service.stop(1, "session", "turn"))
        await asyncio.wait_for(cleaning.wait(), 2)
        second = asyncio.create_task(service.stop(1, "session", "turn"))
        shutdown = asyncio.create_task(service.close())
        await asyncio.sleep(0.05)
        assert not first.done() and not second.done() and not shutdown.done()
        assert not cleaned.is_set()
        release.set()
        assert await asyncio.wait_for(first, 1)
        assert await asyncio.wait_for(second, 1)
        await asyncio.wait_for(shutdown, 1)
        assert cleaned.is_set()
        assert (await pending).type == "turn.stopped"
    finally:
        release.set()
        for task in (first, second, shutdown, pending):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(*(task for task in (first, second, shutdown, pending) if task is not None), return_exceptions=True)
        await stream.aclose()
        await service.close()


@pytest.mark.asyncio
async def test_cancelled_stop_waiter_does_not_abort_model_cleanup():
    started, cleaning, release, cleaned = (asyncio.Event() for _ in range(4))

    class CleanupModel(ReplyModel):
        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
                yield ChatGenerationChunk(message=AIMessageChunk(content="unreachable"))
            finally:
                cleaning.set()
                await release.wait()
                cleaned.set()

    service = AgentService(InMemorySaver(), model_factory=model_factory(CleanupModel()))
    stream = request(service)
    stop_task = pending = None
    try:
        await anext(stream)
        pending = asyncio.create_task(anext(stream))
        await asyncio.wait_for(started.wait(), 2)
        stop_task = asyncio.create_task(service.stop(1, "session", "turn"))
        await asyncio.wait_for(cleaning.wait(), 2)
        stop_task.cancel()
        await asyncio.sleep(0)
        assert not stop_task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(stop_task, 1)
        assert cleaned.is_set()
        assert (await pending).type == "turn.stopped"
    finally:
        release.set()
        for task in (stop_task, pending):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(*(task for task in (stop_task, pending) if task is not None), return_exceptions=True)
        await stream.aclose()
        await service.close()
