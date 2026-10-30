"""Owned, in-process source Agent execution and checkpoint projection.

This service is not exposed by the public router while the integration gate is
closed. Its caller must obtain the authenticated user and model configuration
from the server, and supply a callback that revalidates the login session.
"""

from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from contextlib import aclosing
from typing import Any, cast
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.modules.ai.agent.events import AgentEvent, evidence_reference
from app.modules.ai.agent.service import AgentService
from app.modules.ai.agent.tools.read import _current_auth, _require, build_read_tools
from app.modules.cnc.cnc_drawing_upload.service import DrawingUploadService

from .source_repository import SourceChatRepository, VisibleMessage


class DrawingReferenceUnavailable(Exception):
    """An uploaded drawing could not be safely attached to this turn."""


def _visible_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str))
    return ""


class SourceChatService:
    def __init__(
        self,
        auth: AuthSchema,
        agent: AgentService,
        refresh_auth: Callable[[], Awaitable[AuthSchema]],
        sessions: async_sessionmaker[AsyncSession] = async_db_session,
    ) -> None:
        if auth.user.id <= 0:
            raise PermissionError("CHAT_OWNER_UNAVAILABLE")
        self.auth = auth
        self.agent = agent
        self.refresh_auth = refresh_auth
        self.sessions = sessions

    async def _require_session(self, session_id: str) -> None:
        async with self.sessions() as db:
            if await SourceChatRepository(db, self.auth.user.id).get(session_id) is None:
                raise LookupError("CHAT_SESSION_UNAVAILABLE")

    async def _require_current_auth(self) -> None:
        current = await self.refresh_auth()
        if current.user.id != self.auth.user.id:
            raise PermissionError("CHAT_OWNER_UNAVAILABLE")

    async def _drawing_references(self, request_ids: list[UUID]) -> list[str]:
        if not request_ids:
            return []
        async with self.sessions() as db:
            current = await _current_auth(self.auth.user.id, self.refresh_auth, db)
            _require(current, "module_cnc:cnc_part:detail")
        uploads = DrawingUploadService(current, self.sessions)
        references: list[str] = []
        for request_id in request_ids:
            try:
                result = await uploads.status(request_id)
            except CustomException as exc:
                raise DrawingReferenceUnavailable("CHAT_DRAWING_UNAVAILABLE") from exc
            if result.state != "READY" or result.part_id is None:
                raise DrawingReferenceUnavailable("CHAT_DRAWING_UNAVAILABLE")
            references.append(f"图纸 ID: {result.part_id}；SHA-256: {result.sha256}；大小: {result.size_bytes} 字节")
        return references

    async def repair_history(self, session_id: str) -> bool:
        """Rebuild visible human/assistant messages from the owned checkpoint."""
        await self._require_current_auth()
        await self._require_session(session_id)
        thread_id = self.agent._thread_id(self.auth.user.id, session_id)
        checkpoint = await self.agent.checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
        if checkpoint is None:
            return False
        raw_messages = checkpoint.checkpoint.get("channel_values", {}).get("messages", [])
        if not isinstance(raw_messages, list):
            raise ValueError("CHAT_CHECKPOINT_INVALID")
        messages: list[VisibleMessage] = []
        pending_evidence: list[int] = []
        for message in raw_messages:
            if isinstance(message, ToolMessage):
                if message.status != "error" and (reference := evidence_reference(message.name, message.content)) is not None:
                    result_id = reference["result_id"]
                    if result_id not in pending_evidence and len(pending_evidence) < 50:
                        pending_evidence.append(result_id)
                continue
            if not isinstance(message, HumanMessage | AIMessage):
                continue
            if isinstance(message, HumanMessage):
                pending_evidence.clear()
            content = _visible_text(message.content)
            if not content:
                continue
            if not message.id:
                raise ValueError("CHAT_CHECKPOINT_MESSAGE_ID_MISSING")
            role = "user" if isinstance(message, HumanMessage) else "assistant"
            references = tuple(pending_evidence) if role == "assistant" else ()
            messages.append(VisibleMessage(source_id=message.id, role=role, content=content, position=len(messages), evidence_result_ids=references))
            if role == "assistant":
                pending_evidence.clear()
        async with self.sessions.begin() as db:
            await SourceChatRepository(db, self.auth.user.id).project(session_id, messages)
        return bool(messages)

    async def stream(
        self,
        *,
        session_id: str,
        turn_id: str,
        message: str,
        skills: list[str] | None,
        model_config: Mapping[str, Any] | None,
        drawing_uploads: list[UUID] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Run only after numeric ownership; expose no model configuration."""
        await self._require_current_auth()
        await self._require_session(session_id)
        references = await self._drawing_references(drawing_uploads or [])
        if references:
            attachment_text = "已保存的本地图纸（引用不代表授权向第三方传输）：\n" + "\n".join(references)
            message = f"{message.strip()}\n\n{attachment_text}" if message.strip() else attachment_text
        tools = await build_read_tools(self.auth.user.id, self.refresh_auth, self.sessions)
        config = model_config if model_config is not None else {
            "model_id": settings.OPENAI_MODEL,
            "base_url": settings.OPENAI_BASE_URL,
            "api_key": settings.OPENAI_API_KEY,
            "temperature": 0.7,
        }
        stream = cast(
            AsyncGenerator[AgentEvent, None],
            self.agent.stream(
                actor_id=self.auth.user.id,
                session_id=session_id,
                turn_id=turn_id,
                message=message,
                skills=skills,
                model_config=config,
                tools=tools,
            ),
        )
        async with aclosing(stream):
            async for event in stream:
                if event.type in {"turn.completed", "turn.stopped"}:
                    try:
                        saved = await self.repair_history(session_id)
                    except Exception:
                        if event.type == "turn.completed":
                            # The checkpoint is retained and can be repaired on
                            # retry; never claim a durable completed turn here.
                            yield event.model_copy(update={"type": "turn.failed", "payload": {"code": "CHAT_HISTORY_UNAVAILABLE"}})
                            return
                        event = event.model_copy(update={"payload": {"history_status": "unavailable"}})
                    else:
                        if event.type == "turn.completed" and not saved:
                            yield event.model_copy(update={"type": "turn.failed", "payload": {"code": "CHAT_HISTORY_UNAVAILABLE"}})
                            return
                        if event.type == "turn.stopped":
                            event = event.model_copy(update={"payload": {"history_status": "ready" if saved else "not_saved"}})
                yield event
