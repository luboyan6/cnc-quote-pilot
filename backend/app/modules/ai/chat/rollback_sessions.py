"""Expose source-chat projections read-only when the legacy engine is active."""

from typing import Literal

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.enums import RET
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException

from .schema import ChatSessionCreateSchema, ChatSessionOutSchema, ChatSessionQueryParam, ChatSessionUpdateSchema
from .service import ChatService
from .source_sessions import SourceSessionService

_SOURCE_PREFIX = "source:"


def _readonly(item: ChatSessionOutSchema) -> ChatSessionOutSchema:
    data = item.model_dump()
    public_id = _SOURCE_PREFIX + item.session_id
    data.update({"id": public_id, "session_id": public_id, "read_only": True})
    return ChatSessionOutSchema.model_validate(data)


class RollbackSessionService:
    """Keep Agno history intact while making owned source projections visible."""

    def __init__(
        self,
        auth: AuthSchema,
        sessions: async_sessionmaker[AsyncSession] = async_db_session,
        legacy: ChatService | None = None,
    ) -> None:
        self.sessions = sessions
        self.legacy = legacy or ChatService(auth)
        self.source = SourceSessionService(auth, sessions)

    async def _source_tables_exist(self) -> bool:
        async with self.sessions() as db:
            connection = await db.connection()
            present = await connection.run_sync(
                lambda conn: (inspect(conn).has_table("ai_source_chat_session"), inspect(conn).has_table("ai_source_chat_message"))
            )
        if present[0] != present[1]:
            raise RuntimeError("AI_SOURCE_CHAT_SCHEMA_INCOMPLETE")
        return present[0]

    async def get_session(self, session_id: str) -> ChatSessionOutSchema:
        if not session_id.startswith(_SOURCE_PREFIX):
            return await self.legacy.get_session(session_id)
        if not await self._source_tables_exist():
            raise CustomException(msg="会话不存在", code=RET.NOT_FOUND.code)
        return _readonly(await self.source.get_session(session_id.removeprefix(_SOURCE_PREFIX)))

    async def create(self, data: ChatSessionCreateSchema) -> ChatSessionOutSchema:
        return await self.legacy.create(data)

    async def page(
        self,
        *,
        page_no: int,
        page_size: int,
        search: ChatSessionQueryParam,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[ChatSessionOutSchema]:
        if not await self._source_tables_exist():
            return await self.legacy.page(page_no=page_no, page_size=page_size, search=search, order_by=order_by)
        source_first = await self.source.page(page_no=1, page_size=1, search=search, order_by=order_by)
        if not source_first.total:
            return await self.legacy.page(page_no=page_no, page_size=page_size, search=search, order_by=order_by)
        legacy_first = await self.legacy.page(page_no=1, page_size=1, search=search, order_by=order_by)
        total = source_first.total + legacy_first.total
        offset = (page_no - 1) * page_size
        if offset >= total:
            return PageResultSchema[ChatSessionOutSchema](page_no=page_no, page_size=page_size, total=total, has_next=False, items=[])

        # Only the first `offset + page_size` entries of each independently
        # sorted stream can appear in the requested merged page. Include ties
        # at the boundary because Agno does not order equal timestamps by ID.
        needed = offset + page_size
        field: Literal["created_at", "updated_at"] = "updated_at"
        ascending = False
        if order_by and order_by[0]:
            name, direction = next(iter(order_by[0].items()))
            if name in {"created_at", "created_time"}:
                field = "created_at"
            ascending = direction == "asc"

        async def collect(service: ChatService | SourceSessionService, count: int) -> list[ChatSessionOutSchema]:
            limit = min(100, needed)
            collected: list[ChatSessionOutSchema] = []
            index = 1
            target = min(count, needed)
            while len(collected) < count:
                page = await service.page(page_no=index, page_size=limit, search=search, order_by=order_by)
                if not page.items:
                    break
                collected.extend(page.items)
                index += 1
                if len(collected) >= target:
                    boundary = getattr(collected[target - 1], field) or 0
                    if len(collected) >= count or (getattr(collected[-1], field) or 0) != boundary:
                        break
            collected.sort(key=lambda item: item.session_id)
            collected.sort(key=lambda item: getattr(item, field) or 0, reverse=not ascending)
            return collected[:target]

        legacy_items = await collect(self.legacy, legacy_first.total)
        source_items = [_readonly(item) for item in await collect(self.source, source_first.total)]
        combined = legacy_items + source_items
        combined.sort(key=lambda item: item.session_id)
        combined.sort(key=lambda item: getattr(item, field) or 0, reverse=not ascending)
        return PageResultSchema[ChatSessionOutSchema](
            page_no=page_no, page_size=page_size, total=total, has_next=offset + page_size < total,
            items=combined[offset : offset + page_size],
        )

    async def update(self, session_id: str, data: ChatSessionUpdateSchema) -> None:
        if not session_id.startswith(_SOURCE_PREFIX):
            await self.legacy.update(session_id, data)
            return
        if not await self._source_tables_exist():
            raise CustomException(msg="会话不存在", code=RET.NOT_FOUND.code)
        await self.source.update(session_id.removeprefix(_SOURCE_PREFIX), data)

    async def delete(self, session_ids: list[str]) -> None:
        if not session_ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        source_ids = [item.removeprefix(_SOURCE_PREFIX) for item in session_ids if item.startswith(_SOURCE_PREFIX)]
        legacy_ids = [item for item in session_ids if not item.startswith(_SOURCE_PREFIX)]
        # Separate databases cannot provide one atomic mixed-source deletion.
        if source_ids and legacy_ids:
            raise CustomException(msg="请分别删除不同类型的会话")
        if legacy_ids:
            await self.legacy.delete(legacy_ids)
        elif await self._source_tables_exist():
            await self.source.delete(source_ids)
        else:
            raise CustomException(msg="会话不存在", code=RET.NOT_FOUND.code)
