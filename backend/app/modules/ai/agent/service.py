"""Own each native asynchronous graph run and await cancellation cleanup."""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import aclosing
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from .events import AgentEvent, EventType, evidence_reference
from .graph import build_graph
from .model_provider import model_from_config
from .skills import SkillCatalog


@dataclass(slots=True)
class _Turn:
    turn_id: str
    task: asyncio.Task[None]


def _cancel_once(task: asyncio.Task[None]) -> None:
    # Repeated cancellation can interrupt an async model/HTTP cleanup that is
    # already running in response to the first cancellation.
    if not task.done() and not task.cancelling():
        task.cancel()


async def _await_cleanup(*tasks: asyncio.Task[None]) -> None:
    """Finish cleanup even if the caller is cancelled while waiting for it."""
    waiter = asyncio.gather(*tasks, return_exceptions=True)
    cancelled = False
    while not waiter.done():
        try:
            await asyncio.shield(waiter)
        except asyncio.CancelledError:
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError


class AgentService:
    """In-process graph execution; caller verifies the session belongs to actor.

    Tools must already be server-constructed and perform their own fresh
    authorization. Tool arguments and results never enter the event stream.
    """

    def __init__(self, checkpointer: BaseCheckpointSaver, catalog: SkillCatalog | None = None, *, model_factory: Callable = model_from_config, queue_size: int = 32, timeout: float = 180.0) -> None:
        if queue_size < 1 or timeout <= 0:
            raise ValueError("INVALID_AGENT_LIMIT")
        self.checkpointer = checkpointer
        self.catalog = catalog or SkillCatalog()
        self.model_factory = model_factory
        self.queue_size = queue_size
        self.timeout = timeout
        self._turns: dict[tuple[int, str], _Turn] = {}
        self._lock = asyncio.Lock()
        self._closed = False

    @staticmethod
    def _thread_id(actor_id: int, session_id: str) -> str:
        return hashlib.sha256(f"{actor_id}:{session_id}".encode()).hexdigest()

    async def stream(
        self,
        *,
        actor_id: int,
        session_id: str,
        turn_id: str,
        message: str,
        skills: list[str] | None,
        model_config: Mapping[str, Any],
        tools: list[BaseTool],
    ) -> AsyncIterator[AgentEvent]:
        if actor_id <= 0 or not session_id or not turn_id or not message.strip():
            raise ValueError("INVALID_AGENT_REQUEST")
        tool_names = {tool.name for tool in tools}
        activated = self.catalog.activate(skills, tool_names) if skills is not None else []
        queue: asyncio.Queue[tuple[EventType, dict[str, Any]]] = asyncio.Queue(maxsize=self.queue_size)
        key = (actor_id, session_id)
        async with self._lock:
            if self._closed:
                raise RuntimeError("AGENT_SERVICE_CLOSED")
            if key in self._turns:
                raise RuntimeError("AGENT_SESSION_BUSY")
            task = asyncio.create_task(self._produce(queue, actor_id, session_id, message, skills, model_config, tools))
            self._turns[key] = _Turn(turn_id, task)

        seq = 0

        def event(kind: EventType, payload: dict[str, Any] | None = None) -> AgentEvent:
            nonlocal seq
            seq += 1
            return AgentEvent(session_id=session_id, turn_id=turn_id, seq=seq, type=kind, payload=payload or {})

        try:
            yield event("turn.started")
            for skill in activated:
                yield event("skill.activated", {"name": skill.name})
            while not task.done() or not queue.empty():
                if task.cancelled():
                    break
                if not queue.empty():
                    kind, payload = queue.get_nowait()
                    yield event(kind, payload)
                    continue
                get_event = asyncio.create_task(queue.get())
                try:
                    await asyncio.wait((get_event, task), return_when=asyncio.FIRST_COMPLETED)
                    # Re-check rather than using the earlier snapshot: a queue
                    # get may complete concurrently with task completion.
                    if get_event.done() and not get_event.cancelled() and not task.cancelled():
                        kind, payload = get_event.result()
                        yield event(kind, payload)
                finally:
                    if not get_event.done():
                        get_event.cancel()
                        await asyncio.gather(get_event, return_exceptions=True)
            if task.cancelled():
                yield event("turn.stopped")
            elif task.exception() is not None:
                yield event("turn.failed", {"code": "AGENT_TURN_FAILED"})
            else:
                yield event("turn.completed")
        finally:
            _cancel_once(task)
            try:
                await _await_cleanup(task)
            finally:
                async with self._lock:
                    if self._turns.get(key, None) and self._turns[key].task is task:
                        del self._turns[key]

    async def _produce(self, queue, actor_id, session_id, message, skills, model_config, tools) -> None:
        async with asyncio.timeout(self.timeout), self.model_factory(model_config) as model:
            graph = build_graph(model=model, tools=tools, catalog=self.catalog, checkpointer=self.checkpointer)
            state: dict[str, Any] = {"messages": [HumanMessage(content=message)]}
            if skills is not None:
                state["skill_context"] = list(dict.fromkeys(skills))
            config = {"configurable": {"thread_id": self._thread_id(actor_id, session_id)}, "recursion_limit": 50}
            stream = graph.astream(state, config=config, stream_mode=["messages", "updates"])
            async with aclosing(stream):
                async for mode, data in stream:
                    if mode == "messages":
                        chunk, _metadata = data
                        if isinstance(chunk, AIMessageChunk):
                            content = chunk.content
                            if isinstance(content, str) and content:
                                await queue.put(("text.delta", {"text": content}))
                            elif isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str) and block["text"]:
                                        await queue.put(("text.delta", {"text": block["text"]}))
                    elif mode == "updates" and isinstance(data, dict):
                        for update in data.values():
                            if not isinstance(update, dict):
                                continue
                            for item in update.get("messages", []):
                                if isinstance(item, AIMessage):
                                    for call in item.tool_calls:
                                        name = call.get("name")
                                        if name in {tool.name for tool in tools}:
                                            await queue.put(("tool.started", {"name": name}))
                                elif isinstance(item, ToolMessage) and item.name in {tool.name for tool in tools}:
                                    kind: EventType = "tool.failed" if item.status == "error" else "tool.completed"
                                    await queue.put((kind, {"name": item.name}))
                                    if item.status != "error" and (reference := evidence_reference(item.name, item.content)) is not None:
                                        await queue.put(("evidence.available", reference))

    async def stop(self, actor_id: int, session_id: str, turn_id: str) -> bool:
        async with self._lock:
            turn = self._turns.get((actor_id, session_id))
            if turn is None or turn.turn_id != turn_id:
                return False
            task = turn.task
            if task.done():
                return False
            _cancel_once(task)
        await _await_cleanup(task)
        return True

    async def close(self) -> None:
        async with self._lock:
            self._closed = True
            tasks = [turn.task for turn in self._turns.values()]
            for task in tasks:
                _cancel_once(task)
        await _await_cleanup(*tasks)
