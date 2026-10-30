"""Request-scoped adaptations of DeerFlow skill and safety middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.errors import GraphBubbleUp
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from .skills import SkillCatalog


def _repair_messages(messages: list[Any]) -> list[Any]:
    """Pair interrupted tool calls with safe results; drop orphan results.

    Like the upstream middleware this changes only the outgoing request, never
    the stored checkpoint. Calls are paired within their own assistant turn.
    """
    output: list[Any] = []
    i = 0
    while i < len(messages):
        message = messages[i]
        if isinstance(message, ToolMessage):
            i += 1
            continue
        output.append(message)
        i += 1
        if not isinstance(message, AIMessage) or not message.tool_calls:
            continue
        responses: dict[str, ToolMessage] = {}
        while i < len(messages) and isinstance(messages[i], ToolMessage):
            responses.setdefault(messages[i].tool_call_id, messages[i])
            i += 1
        for call in message.tool_calls:
            call_id = call.get("id")
            if call_id:
                output.append(responses.get(call_id) or ToolMessage(content="TOOL_INTERRUPTED", tool_call_id=call_id, status="error"))
    return output


class SkillAndSafetyMiddleware(AgentMiddleware):
    """Reload active skills and narrow the model's tools on every model call."""

    def __init__(self, catalog: SkillCatalog, tools: set[str]) -> None:
        super().__init__()
        self.catalog = catalog
        self._available_tools = tools

    def _adapt(self, request: ModelRequest) -> ModelRequest:
        names = (request.state or {}).get("skill_context", []) or []
        skills = self.catalog.activate(list(names), self._available_tools)
        allowed = {name for skill in skills for name in skill.allowed_tools}
        declared: list[BaseTool | dict[str, Any]] = [tool for tool in request.tools if not isinstance(tool, dict) and tool.name in allowed]
        messages = _repair_messages(list(request.messages))
        system_parts = []
        if request.system_message:
            system_parts.append(str(request.system_message.content))
        # Strict OpenAI-compatible providers require exactly one leading system message.
        system_parts.extend(str(message.content) for message in messages if isinstance(message, SystemMessage))
        messages = [message for message in messages if not isinstance(message, SystemMessage)]
        system_parts.extend(f"[Active skill: {skill.name}]\n{skill.content}" for skill in skills)
        return request.override(system_message=SystemMessage(content="\n\n".join(system_parts)), messages=messages, tools=declared)

    async def awrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]) -> ModelResponse:
        return await handler(self._adapt(request))

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        name = request.tool_call.get("name", "")
        names = request.state.get("skill_context", []) or []
        skills = self.catalog.activate(list(names), self._available_tools)
        allowed = {tool for skill in skills for tool in skill.allowed_tools}
        if name not in allowed:
            return ToolMessage(content="TOOL_NOT_AVAILABLE", name=name, tool_call_id=str(request.tool_call.get("id") or ""), status="error")
        try:
            return await handler(request)
        except GraphBubbleUp:
            raise
        except Exception:
            # CancelledError and LangGraph control-flow exceptions are not regular
            # tool failures and must continue to unwind the native async stream.
            return ToolMessage(content="TOOL_FAILED", name=name, tool_call_id=str(request.tool_call.get("id") or ""), status="error")
