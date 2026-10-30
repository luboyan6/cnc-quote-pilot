"""Bounded WebSocket transport for the gated in-process source Agent."""

import asyncio
import json
import re
import uuid
from contextlib import aclosing
from dataclasses import dataclass

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.modules.ai.agent.events import AgentEvent

from .schema import ChatQuerySchema
from .service import get_user_model_config
from .source_service import DrawingReferenceUnavailable, SourceChatService

_TERMINAL_TYPES = {"turn.completed", "turn.stopped", "turn.failed"}
_TURN_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


@dataclass(slots=True)
class _Turn:
    session_id: str
    turn_id: str
    protocol: int
    phase: str = "running"
    seq: int = 0
    task: asyncio.Task[None] | None = None


@dataclass(slots=True)
class _Message:
    frames: tuple[str, ...]
    turn: _Turn | None = None
    terminal: bool = False


def _cancel_once(task: asyncio.Task[None] | None) -> None:
    if task is not None and not task.done() and not task.cancelling():
        task.cancel()


def _frames(event: AgentEvent, protocol: int) -> tuple[str, ...]:
    if protocol == 2:
        return (event.model_dump_json(),)
    if event.type == "text.delta":
        text = event.payload.get("text")
        return (text,) if isinstance(text, str) and text else ()
    if event.type == "turn.completed":
        return ("[DONE]",)
    if event.type == "turn.stopped":
        return ("[STOPPED]",)
    if event.type == "turn.failed":
        return ("错误: AI 服务暂时不可用，请稍后重试", "[DONE]")
    return ()


def _control_error(code: str, protocol: int, legacy: str) -> _Message:
    # Control errors are not turn events and must not accidentally terminate
    # the current turn (for example, an old stop arriving after a new turn).
    if protocol == 2:
        return _Message((json.dumps({"type": "request.error", "payload": {"code": code}}, ensure_ascii=False),))
    return _Message((legacy,))


async def run_source_socket(websocket: WebSocket, auth: AuthSchema, chat: SourceChatService, redis: Redis) -> None:
    """Only called after source-engine startup gates and normal WS auth."""
    outgoing: asyncio.Queue[_Message] = asyncio.Queue(maxsize=32)
    active: _Turn | None = None

    async def enqueue(event: AgentEvent, turn: _Turn) -> None:
        frames = _frames(event, turn.protocol)
        if frames:
            await outgoing.put(_Message(frames, turn, event.type in _TERMINAL_TYPES))

    async def fail(turn: _Turn, code: str) -> None:
        turn.phase = "failed"
        turn.seq += 1
        await enqueue(AgentEvent(session_id=turn.session_id, turn_id=turn.turn_id, seq=turn.seq, type="turn.failed", payload={"code": code}), turn)

    async def generate(turn: _Turn, query: ChatQuerySchema) -> None:
        try:
            model_config = await get_user_model_config(redis, auth.user.id)
            stream = chat.stream(
                session_id=turn.session_id, turn_id=turn.turn_id, message=query.message or "", skills=query.skills,
                model_config=model_config, drawing_uploads=query.drawing_uploads,
            )
            async with aclosing(stream):
                async for event in stream:
                    turn.seq = event.seq
                    if event.type in _TERMINAL_TYPES:
                        turn.phase = "completed" if event.type == "turn.completed" else "failed"
                    await enqueue(event, turn)
            if turn.phase == "running":
                await fail(turn, "AGENT_TURN_FAILED")
        except asyncio.CancelledError:
            raise
        except LookupError:
            await fail(turn, "CHAT_SESSION_UNAVAILABLE")
        except PermissionError:
            await fail(turn, "CHAT_OWNER_UNAVAILABLE")
        except DrawingReferenceUnavailable:
            await fail(turn, "CHAT_DRAWING_UNAVAILABLE")
        except CustomException:
            await fail(turn, "CHAT_CONFIGURATION_UNAVAILABLE")
        except Exception:
            await fail(turn, "AGENT_TURN_FAILED")

    async def receive() -> None:
        nonlocal active
        try:
            while True:
                raw = await websocket.receive_text()
                value: object = None
                try:
                    value = json.loads(raw)
                    if not isinstance(value, dict):
                        raise ValueError("invalid request")
                    query = ChatQuerySchema(**value)
                except (ValueError, TypeError):
                    protocol = active.protocol if active else 2 if isinstance(value, dict) and value.get("protocol_version") == 2 else 1
                    await outgoing.put(_control_error("INVALID_REQUEST", protocol, "消息格式错误，请发送JSON格式的消息"))
                    continue
                if query.action == "stop":
                    turn = active
                    if (
                        turn is None
                        or turn.phase != "running"
                        or (query.session_id is not None and query.session_id != turn.session_id)
                        or (query.turn_id is not None and query.turn_id != turn.turn_id)
                        or (turn.protocol == 2 and (query.session_id != turn.session_id or query.turn_id != turn.turn_id))
                    ):
                        protocol = query.protocol_version or (turn.protocol if turn else 1)
                        await outgoing.put(_control_error("NO_ACTIVE_TURN", protocol, "当前没有正在进行的生成任务"))
                        continue
                    turn.phase = "stopping"
                    stop_started = asyncio.get_running_loop().time()
                    _cancel_once(turn.task)
                    if turn.task is not None:
                        await asyncio.shield(asyncio.gather(turn.task, return_exceptions=True))
                    history_status = "unavailable"
                    remaining = 0.9 - (asyncio.get_running_loop().time() - stop_started)
                    if remaining > 0:
                        try:
                            async with asyncio.timeout(remaining):
                                saved = await chat.repair_history(turn.session_id)
                            history_status = "ready" if saved else "not_saved"
                        except Exception:
                            # A deleted session or unavailable DB must not be
                            # resurrected or reported as persisted.
                            pass
                    turn.phase = "stopped"
                    turn.seq += 1
                    await enqueue(
                        AgentEvent(
                            session_id=turn.session_id,
                            turn_id=turn.turn_id,
                            seq=turn.seq,
                            type="turn.stopped",
                            payload={"history_status": history_status},
                        ),
                        turn,
                    )
                    continue
                if active is not None:
                    await outgoing.put(_control_error("TURN_IN_PROGRESS", query.protocol_version or active.protocol, "当前有正在进行的生成任务，请稍后再试"))
                    continue
                protocol = query.protocol_version or 1
                turn_id = query.turn_id or uuid.uuid4().hex
                if (
                    query.action is not None
                    or not query.session_id
                    or len(query.session_id) > 64
                    or (not (query.message or "").strip() and not query.drawing_uploads)
                    or (query.drawing_uploads and protocol != 2)
                    or not _TURN_ID.fullmatch(turn_id)
                    or (protocol == 2 and not query.turn_id)
                ):
                    await outgoing.put(_control_error("INVALID_REQUEST", protocol, "消息格式错误：缺少会话、轮次或消息"))
                    continue
                turn = _Turn(session_id=query.session_id, turn_id=turn_id, protocol=protocol)
                active = turn
                turn.task = asyncio.create_task(generate(turn, query))
        except WebSocketDisconnect:
            return

    async def send() -> None:
        nonlocal active
        while True:
            item = await outgoing.get()
            if item.turn is not None and not item.terminal and item.turn.phase in {"stopping", "stopped"}:
                continue
            for frame in item.frames:
                await websocket.send_text(frame)
            if item.terminal and active is item.turn:
                active = None

    receiver = asyncio.create_task(receive())
    sender = asyncio.create_task(send())
    try:
        done, _ = await asyncio.wait((receiver, sender), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        _cancel_once(receiver)
        _cancel_once(sender)
        if active is not None:
            _cancel_once(active.task)
        tasks = [receiver, sender]
        if active is not None and active.task is not None:
            tasks.append(active.task)
        await asyncio.gather(*tasks, return_exceptions=True)
