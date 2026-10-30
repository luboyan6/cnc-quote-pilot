"""Rollback reads owned source projections while leaving Agno rows untouched."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from agno.db.sqlite import AsyncSqliteDb
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.exceptions import CustomException
from app.modules.ai.chat import crud
from app.modules.ai.chat.model import SourceChatMessage, SourceChatSession
from app.modules.ai.chat.rollback_sessions import RollbackSessionService
from app.modules.ai.chat.schema import ChatSessionCreateSchema, ChatSessionQueryParam, ChatSessionUpdateSchema
from app.modules.ai.chat.source_repository import SourceChatRepository, VisibleMessage


def user(actor_id: int, username: str) -> AuthSchema:
    return AuthSchema(user=CoreUserSchema(id=actor_id, username=username))


@pytest.mark.asyncio
async def test_rollback_merges_owned_readonly_history_without_importing_legacy(tmp_path, monkeypatch):
    path = tmp_path / "chat.sqlite"
    agno = AsyncSqliteDb(db_file=str(path))
    await agno._create_all_tables()
    monkeypatch.setattr(crud, "_get_agno_db", lambda: agno)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    alice = user(1, "alice")
    bob = user(2, "bob")
    service = RollbackSessionService(alice, sessions)
    other = RollbackSessionService(bob, sessions)
    try:
        old = await crud.ChatSessionCRUD(alice).create(ChatSessionCreateSchema(title="legacy"))
        # Old installations have no source tables; the legacy path still works.
        before = await service.page(page_no=1, page_size=10, search=ChatSessionQueryParam())
        assert before.total == 1 and before.items[0].session_id == old.session_id

        async with engine.begin() as connection:
            await connection.run_sync(SourceChatSession.__table__.create)
            await connection.run_sync(SourceChatMessage.__table__.create)
        async with sessions.begin() as db:
            repo = SourceChatRepository(db, 1)
            newest = await repo.create("newest", "new source")
            oldest = await repo.create("oldest", "older source")
            await repo.project("newest", [VisibleMessage("m1", "user", "source question", 0)])
            await SourceChatRepository(db, 2).create("foreign", "foreign source")
            newest.updated_at = datetime.now(UTC) + timedelta(days=1)
            oldest.updated_at = datetime.now(UTC) - timedelta(days=1)

        pages = [await service.page(page_no=n, page_size=1, search=ChatSessionQueryParam()) for n in (1, 2, 3)]
        assert [page.total for page in pages] == [3, 3, 3]
        assert [page.items[0].session_id for page in pages] == ["source:newest", old.session_id, "source:oldest"]
        assert [page.has_next for page in pages] == [True, True, False]
        assert pages[0].items[0].model_dump()["read_only"] is True
        assert (await service.page(page_no=1, page_size=10, search=ChatSessionQueryParam(title="new source"))).total == 1
        detail = await service.get_session("source:newest")
        assert detail.messages[0].content == "source question" and detail.model_dump()["read_only"] is True
        with pytest.raises(CustomException, match="会话不存在"):
            await other.get_session("source:newest")
        with pytest.raises(CustomException, match="分别删除"):
            await service.delete([old.session_id, "source:newest"])
        await service.update("source:newest", ChatSessionUpdateSchema(title="renamed"))
        assert (await service.get_session("source:newest")).title == "renamed"
        await service.delete(["source:newest"])
        with pytest.raises(CustomException, match="会话不存在"):
            await service.get_session("source:newest")
        assert (await crud.ChatSessionCRUD(alice).get_by_id(old.session_id)).session_id == old.session_id
        assert (await other.get_session("source:foreign")).title == "foreign source"
    finally:
        await engine.dispose()
        await agno.close()


@pytest.mark.asyncio
async def test_rollback_does_not_hide_a_partial_source_schema(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'partial.sqlite').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SourceChatSession.__table__.create)
        service = RollbackSessionService(user(1, "alice"), sessions)
        with pytest.raises(RuntimeError, match="AI_SOURCE_CHAT_SCHEMA_INCOMPLETE"):
            await service.page(page_no=1, page_size=10, search=ChatSessionQueryParam())
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rollback_pages_keep_all_sessions_with_equal_timestamps(tmp_path, monkeypatch):
    path = tmp_path / "ties.sqlite"
    agno = AsyncSqliteDb(db_file=str(path))
    await agno._create_all_tables()
    monkeypatch.setattr(crud, "_get_agno_db", lambda: agno)
    timestamp = 1_791_000_000
    monkeypatch.setattr(crud, "time", SimpleNamespace(time=lambda: timestamp))
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    auth = user(1, "alice")
    try:
        old = [await crud.ChatSessionCRUD(auth).create(ChatSessionCreateSchema(title="legacy")) for _ in range(2)]
        async with engine.begin() as connection:
            await connection.run_sync(SourceChatSession.__table__.create)
            await connection.run_sync(SourceChatMessage.__table__.create)
        async with sessions.begin() as db:
            repo = SourceChatRepository(db, 1)
            for session_id in ("first", "second"):
                item = await repo.create(session_id, "source")
                # SQLite strips timezone information; use the same local wall
                # clock that the existing session formatter converts to epoch.
                item.updated_at = datetime.fromtimestamp(timestamp)
        service = RollbackSessionService(auth, sessions)
        pages = [await service.page(page_no=n, page_size=1, search=ChatSessionQueryParam()) for n in range(1, 5)]
        expected = sorted([item.session_id for item in old] + ["source:first", "source:second"])
        assert [page.items[0].session_id for page in pages] == expected
    finally:
        await engine.dispose()
        await agno.close()
