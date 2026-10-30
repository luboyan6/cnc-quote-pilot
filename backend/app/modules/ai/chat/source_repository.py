"""Numeric-owner session and rebuildable visible history storage.

The caller owns the AsyncSession transaction. Only authenticated server-side
user IDs may be supplied; model input and socket payloads are not trusted IDs.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .model import SourceChatMessage, SourceChatSession


@dataclass(frozen=True, slots=True)
class VisibleMessage:
    source_id: str
    role: Literal["user", "assistant"]
    content: str
    position: int
    evidence_result_ids: tuple[int, ...] = ()


class SourceChatRepository:
    def __init__(self, db: AsyncSession, owner_id: int) -> None:
        if owner_id <= 0:
            raise ValueError("CHAT_OWNER_UNAVAILABLE")
        self.db = db
        self.owner_id = owner_id

    async def get(self, session_id: str, *, lock: bool = False) -> SourceChatSession | None:
        stmt = select(SourceChatSession).where(
            SourceChatSession.session_id == session_id,
            SourceChatSession.owner_id == self.owner_id,
            SourceChatSession.deleted_at.is_(None),
        )
        if lock:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(self, session_id: str, title: str) -> SourceChatSession:
        if not session_id or len(session_id) > 64 or not title.strip() or len(title.strip()) > 200:
            raise ValueError("INVALID_CHAT_SESSION")
        item = SourceChatSession(session_id=session_id, owner_id=self.owner_id, title=title.strip())
        self.db.add(item)
        # The primary key includes tombstones. Reusing a deleted or other
        # user's session ID must fail instead of resurrecting its checkpoint.
        await self.db.flush()
        return item

    async def page(
        self,
        *,
        offset: int,
        limit: int,
        title: str | None = None,
        sort_by: Literal["created_at", "updated_at"] = "updated_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[SourceChatSession], int]:
        if offset < 0 or limit < 1 or limit > 100:
            raise ValueError("INVALID_CHAT_PAGE")
        where = [SourceChatSession.owner_id == self.owner_id, SourceChatSession.deleted_at.is_(None)]
        if title and title.strip():
            # autoescape prevents user-provided '%' and '_' changing the search.
            where.append(SourceChatSession.title.icontains(title.strip(), autoescape=True))
        total = int((await self.db.execute(select(func.count()).select_from(SourceChatSession).where(*where))).scalar_one())
        column = SourceChatSession.created_at if sort_by == "created_at" else SourceChatSession.updated_at
        order = column.asc() if sort_order == "asc" else column.desc()
        rows = await self.db.scalars(select(SourceChatSession).where(*where).order_by(order, SourceChatSession.session_id).offset(offset).limit(limit))
        return list(rows.all()), total

    async def rename(self, session_id: str, title: str) -> bool:
        if not title.strip() or len(title.strip()) > 200:
            raise ValueError("INVALID_CHAT_TITLE")
        item = await self.get(session_id, lock=True)
        if item is None:
            return False
        item.title = title.strip()
        item.updated_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def delete(self, session_id: str) -> bool:
        item = await self.get(session_id, lock=True)
        if item is None:
            return False
        now = datetime.now(UTC)
        item.deleted_at = now
        item.updated_at = now
        await self.db.flush()
        return True

    async def messages(self, session_id: str) -> list[SourceChatMessage]:
        if await self.get(session_id) is None:
            raise LookupError("CHAT_SESSION_UNAVAILABLE")
        rows = await self.db.scalars(select(SourceChatMessage).where(SourceChatMessage.session_id == session_id).order_by(SourceChatMessage.position))
        return list(rows.all())

    async def project(self, session_id: str, messages: list[VisibleMessage]) -> None:
        """Idempotently materialize visible checkpoint messages; never infer state here."""
        session = await self.get(session_id, lock=True)
        if session is None:
            raise LookupError("CHAT_SESSION_UNAVAILABLE")
        if any(not item.source_id or len(item.source_id) > 128 or item.role not in {"user", "assistant"} or item.position < 0 for item in messages):
            raise ValueError("INVALID_CHAT_PROJECTION")
        if len({item.source_id for item in messages}) != len(messages) or len({item.position for item in messages}) != len(messages):
            raise ValueError("INVALID_CHAT_PROJECTION")
        if any(
            len(item.evidence_result_ids) > 50
            or len(item.evidence_result_ids) != len(set(item.evidence_result_ids))
            or (item.role != "assistant" and item.evidence_result_ids)
            or any(type(value) is not int or value <= 0 for value in item.evidence_result_ids)
            for item in messages
        ):
            raise ValueError("INVALID_CHAT_PROJECTION")
        if not messages:
            return
        existing_rows = await self.db.scalars(select(SourceChatMessage).where(SourceChatMessage.session_id == session_id))
        existing = {item.source_id: item for item in existing_rows.all()}
        occupied = {item.position: item.source_id for item in existing.values()}
        for item in messages:
            stored = existing.get(item.source_id)
            if stored is not None:
                if (stored.role, stored.content, stored.position) != (item.role, item.content, item.position):
                    raise ValueError("CHAT_PROJECTION_CONFLICT")
            elif item.position in occupied:
                raise ValueError("CHAT_PROJECTION_CONFLICT")
        added = False
        for item in messages:
            stored = existing.get(item.source_id)
            if stored is None:
                self.db.add(SourceChatMessage(session_id=session_id, source_id=item.source_id, role=item.role, content=item.content, position=item.position, evidence_result_ids=list(item.evidence_result_ids)))
                added = True
            elif (stored.evidence_result_ids or []) != list(item.evidence_result_ids):
                stored.evidence_result_ids = list(item.evidence_result_ids)
                added = True
        if added:
            session.updated_at = datetime.now(UTC)
        await self.db.flush()
