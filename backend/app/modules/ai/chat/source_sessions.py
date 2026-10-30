"""REST-facing numeric-owner session operations for the gated source engine."""

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.enums import RET
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException

from .model import SourceChatMessage, SourceChatSession
from .schema import ChatSessionCreateSchema, ChatSessionOutSchema, ChatSessionQueryParam, ChatSessionUpdateSchema
from .source_repository import SourceChatRepository


def _as_session(item: SourceChatSession, messages: list[SourceChatMessage] | None = None) -> ChatSessionOutSchema:
    visible = [
        {"id": message.source_id, "role": message.role, "content": message.content, "created_at": None, "evidence_result_ids": message.evidence_result_ids or []}
        for message in messages or []
    ]

    def timestamp(value: datetime) -> int:
        return int(value.timestamp())

    return ChatSessionOutSchema.model_validate(
        {
            "id": item.session_id,
            "session_id": item.session_id,
            "title": item.title,
            "session_data": {"session_name": item.title},
            "created_at": timestamp(item.created_at),
            "updated_at": timestamp(item.updated_at),
            "created_time": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_time": item.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "message_count": len(visible),
            "messages": visible,
            # Existing clients read runs; this is a display projection, not
            # an input to the graph or a second inference-history store.
            "runs": [{"messages": visible}] if visible else [],
        }
    )


class SourceSessionService:
    def __init__(self, auth: AuthSchema, sessions: async_sessionmaker[AsyncSession] = async_db_session) -> None:
        self.auth = auth
        self.sessions = sessions

    async def create(self, data: ChatSessionCreateSchema) -> ChatSessionOutSchema:
        async with self.sessions.begin() as db:
            item = await SourceChatRepository(db, self.auth.user.id).create(uuid.uuid4().hex, data.title)
            return _as_session(item)

    async def get_session(self, session_id: str) -> ChatSessionOutSchema:
        async with self.sessions() as db:
            repo = SourceChatRepository(db, self.auth.user.id)
            item = await repo.get(session_id)
            if item is None:
                raise CustomException(msg="会话不存在", code=RET.NOT_FOUND.code)
            return _as_session(item, await repo.messages(session_id))

    async def page(
        self,
        *,
        page_no: int,
        page_size: int,
        search: ChatSessionQueryParam,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[ChatSessionOutSchema]:
        sort_by: Literal["created_at", "updated_at"] = "updated_at"
        sort_order: Literal["asc", "desc"] = "desc"
        if order_by and order_by[0]:
            field, direction = next(iter(order_by[0].items()))
            if field in {"created_time", "created_at"}:
                sort_by = "created_at"
            if direction == "asc":
                sort_order = "asc"
        async with self.sessions() as db:
            items, total = await SourceChatRepository(db, self.auth.user.id).page(
                offset=(page_no - 1) * page_size, limit=page_size, title=search.title, sort_by=sort_by, sort_order=sort_order
            )
            return PageResultSchema[ChatSessionOutSchema](
                page_no=page_no,
                page_size=page_size,
                total=total,
                has_next=page_no * page_size < total,
                items=[_as_session(item) for item in items],
            )

    async def update(self, session_id: str, data: ChatSessionUpdateSchema) -> None:
        async with self.sessions.begin() as db:
            if not await SourceChatRepository(db, self.auth.user.id).rename(session_id, data.title):
                raise CustomException(msg="会话不存在", code=RET.NOT_FOUND.code)

    async def delete(self, session_ids: list[str]) -> None:
        if not session_ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        async with self.sessions.begin() as db:
            repo = SourceChatRepository(db, self.auth.user.id)
            for session_id in dict.fromkeys(session_ids):
                if not await repo.delete(session_id):
                    raise CustomException(msg="会话不存在", code=RET.NOT_FOUND.code)
