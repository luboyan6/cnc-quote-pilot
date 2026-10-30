"""Legacy chat transport regression tests with no network or model calls."""

import asyncio
import json
import time
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.modules.ai.chat import controller


class Socket:
    def __init__(self):
        self.app = SimpleNamespace(state=SimpleNamespace(redis=object()))
        self.incoming = asyncio.Queue()
        self.sent = asyncio.Queue()
        self.messages = []

    async def receive_text(self):
        item = await self.incoming.get()
        if item is None:
            raise WebSocketDisconnect()
        return json.dumps(item)

    async def send_text(self, value):
        self.messages.append(value)
        await self.sent.put(value)


def user():
    return AuthSchema(user=CoreUserSchema(id=10, username="alice"), permissions=["module_ai:chat:query"])


@pytest.mark.asyncio
async def test_capabilities_remain_v1_until_source_startup_gate_passes(monkeypatch):
    monkeypatch.setattr(controller.settings, "AI_CHAT_ENGINE", "agno")
    response = await controller.chat_capabilities_controller(user())
    assert json.loads(response.body)["data"] == {"protocol_version": 1, "source_available": False}

    monkeypatch.setattr(controller.settings, "AI_CHAT_ENGINE", "deerflow_source")
    response = await controller.chat_capabilities_controller(user())
    assert json.loads(response.body)["data"] == {"protocol_version": 1, "source_available": False}


async def read(socket):
    return await asyncio.wait_for(socket.sent.get(), timeout=1)


async def close(socket, handler):
    await socket.incoming.put(None)
    await asyncio.wait_for(handler, timeout=1)


@pytest.fixture(autouse=True)
def default_model(monkeypatch):
    async def get_config(_redis, _user):
        return None

    monkeypatch.setattr(controller, "get_user_model_config", get_config)


@pytest.mark.asyncio
async def test_stop_before_first_chunk_awaits_cleanup_and_has_one_terminal(monkeypatch):
    started, cleaned = asyncio.Event(), asyncio.Event()

    class Chat:
        def __init__(self, _auth):
            pass

        async def chat_query(self, **_kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
                yield "unreachable"
            finally:
                cleaned.set()

    monkeypatch.setattr(controller, "ChatService", Chat)
    socket = Socket()
    handler = asyncio.create_task(controller._run_legacy_socket(socket, user()))
    await socket.incoming.put({"message": "hello", "session_id": "s1"})
    await asyncio.wait_for(started.wait(), timeout=1)
    before = time.monotonic()
    await socket.incoming.put({"action": "stop", "session_id": "s1"})
    assert await read(socket) == "[STOPPED]"
    assert cleaned.is_set()
    assert time.monotonic() - before < 1
    await close(socket, handler)
    assert socket.messages == ["[STOPPED]"]


@pytest.mark.asyncio
async def test_stop_for_other_session_does_not_cancel_active_turn(monkeypatch):
    started, cleaned = asyncio.Event(), asyncio.Event()

    class Chat:
        def __init__(self, _auth):
            pass

        async def chat_query(self, **_kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
                yield "unreachable"
            finally:
                cleaned.set()

    monkeypatch.setattr(controller, "ChatService", Chat)
    socket = Socket()
    handler = asyncio.create_task(controller._run_legacy_socket(socket, user()))
    await socket.incoming.put({"message": "hello", "session_id": "s1"})
    await asyncio.wait_for(started.wait(), timeout=1)
    await socket.incoming.put({"action": "stop", "session_id": "s2"})
    assert await read(socket) == "当前没有正在进行的生成任务"
    assert not cleaned.is_set()
    await socket.incoming.put({"action": "stop", "session_id": "s1"})
    assert await read(socket) == "[STOPPED]"
    assert cleaned.is_set()
    await close(socket, handler)


@pytest.mark.asyncio
async def test_normal_completion_keeps_legacy_text_and_done(monkeypatch):
    class Chat:
        def __init__(self, _auth):
            pass

        async def chat_query(self, **_kwargs):
            yield "hello"
            yield " world"

    monkeypatch.setattr(controller, "ChatService", Chat)
    socket = Socket()
    handler = asyncio.create_task(controller._run_legacy_socket(socket, user()))
    await socket.incoming.put({"message": "hello", "session_id": "s1"})
    assert [await read(socket) for _ in range(3)] == ["hello", " world", "[DONE]"]
    await close(socket, handler)


@pytest.mark.asyncio
async def test_disconnect_waits_for_generation_cleanup(monkeypatch):
    started, cleaning, release, cleaned = (asyncio.Event() for _ in range(4))

    class Chat:
        def __init__(self, _auth):
            pass

        async def chat_query(self, **_kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
                yield "unreachable"
            finally:
                cleaning.set()
                await release.wait()
                cleaned.set()

    monkeypatch.setattr(controller, "ChatService", Chat)
    socket = Socket()
    handler = asyncio.create_task(controller._run_legacy_socket(socket, user()))
    await socket.incoming.put({"message": "hello", "session_id": "s1"})
    await asyncio.wait_for(started.wait(), timeout=1)
    await socket.incoming.put(None)
    await asyncio.wait_for(cleaning.wait(), timeout=1)
    assert not handler.done()
    release.set()
    await asyncio.wait_for(handler, timeout=1)
    assert cleaned.is_set()


@pytest.mark.asyncio
async def test_invalid_message_is_reported_and_socket_remains_usable(monkeypatch):
    class Chat:
        def __init__(self, _auth):
            pass

        async def chat_query(self, **_kwargs):
            yield "response"

    monkeypatch.setattr(controller, "ChatService", Chat)
    socket = Socket()
    handler = asyncio.create_task(controller._run_legacy_socket(socket, user()))
    await socket.incoming.put(["not an object"])
    assert "消息格式错误" in await read(socket)
    await socket.incoming.put({"message": "hello"})
    assert [await read(socket), await read(socket)] == ["response", "[DONE]"]
    await close(socket, handler)


@pytest.mark.asyncio
async def test_stop_cleans_model_even_if_the_sender_is_slow(monkeypatch):
    sending, release_sender, producing, cleaned = (asyncio.Event() for _ in range(4))

    class SlowSocket(Socket):
        async def send_text(self, value):
            if not sending.is_set():
                sending.set()
                await release_sender.wait()
            await super().send_text(value)

    class Chat:
        def __init__(self, _auth):
            pass

        async def chat_query(self, **_kwargs):
            try:
                for number in range(100):
                    if number == 33:
                        producing.set()
                    yield str(number)
            finally:
                cleaned.set()

    monkeypatch.setattr(controller, "ChatService", Chat)
    socket = SlowSocket()
    handler = asyncio.create_task(controller._run_legacy_socket(socket, user()))
    await socket.incoming.put({"message": "hello", "session_id": "s1"})
    await asyncio.wait_for(sending.wait(), timeout=1)
    await asyncio.wait_for(producing.wait(), timeout=1)
    await socket.incoming.put({"action": "stop", "session_id": "s1"})
    await asyncio.wait_for(cleaned.wait(), timeout=1)
    release_sender.set()
    assert await read(socket) == "0"  # This send started before stop.
    assert await read(socket) == "[STOPPED]"
    await close(socket, handler)
    assert socket.messages == ["0", "[STOPPED]"]


@pytest.mark.asyncio
async def test_sender_failure_during_stop_does_not_interrupt_async_cleanup(monkeypatch):
    sending, fail_sender, cleaning, release_cleanup, cleaned, interrupted = (asyncio.Event() for _ in range(6))

    class FailingSocket(Socket):
        async def send_text(self, value):
            sending.set()
            await fail_sender.wait()
            raise RuntimeError("socket closed")

    class Chat:
        def __init__(self, _auth):
            pass

        async def chat_query(self, **_kwargs):
            try:
                yield "first"
                await asyncio.Event().wait()
            finally:
                cleaning.set()
                try:
                    await release_cleanup.wait()
                    cleaned.set()
                except asyncio.CancelledError:
                    interrupted.set()
                    raise

    monkeypatch.setattr(controller, "ChatService", Chat)
    socket = FailingSocket()
    handler = asyncio.create_task(controller._run_legacy_socket(socket, user()))
    await socket.incoming.put({"message": "hello", "session_id": "s1"})
    await asyncio.wait_for(sending.wait(), timeout=1)
    await socket.incoming.put({"action": "stop", "session_id": "s1"})
    await asyncio.wait_for(cleaning.wait(), timeout=1)
    fail_sender.set()
    await asyncio.sleep(0)
    release_cleanup.set()
    with pytest.raises(RuntimeError, match="socket closed"):
        await asyncio.wait_for(handler, timeout=1)
    assert cleaned.is_set()
    assert not interrupted.is_set()
