"""Ownership and personal-model selection against isolated dependencies."""

import asyncio
import json
from unittest.mock import Mock

import pytest
from agno.db.sqlite import AsyncSqliteDb
from fakeredis import FakeAsyncRedis

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.exceptions import CustomException
from app.modules.ai.chat import crud, service
from app.modules.ai.chat.schema import ChatQuerySchema, ChatSessionCreateSchema


def auth(actor_id: int, username: str) -> AuthSchema:
    return AuthSchema(user=CoreUserSchema(id=actor_id, username=username))


@pytest.mark.asyncio
async def test_supplied_agno_session_must_belong_to_authenticated_user(tmp_path, monkeypatch):
    db = AsyncSqliteDb(db_file=str(tmp_path / "agno.db"))
    await db._create_all_tables()
    monkeypatch.setattr(crud, "_get_agno_db", lambda: db)
    try:
        alice_crud = crud.ChatSessionCRUD(auth(1, "alice"))
        bob_crud = crud.ChatSessionCRUD(auth(2, "bob"))
        session = await alice_crud.create(ChatSessionCreateSchema(title="private"))
        assert await service._ensure_session(alice_crud, session.session_id) == session.session_id
        with pytest.raises(CustomException, match="会话不存在"):
            await service._ensure_session(bob_crud, session.session_id)

        # The ownership check precedes constructing or invoking the model.
        factory = Mock(side_effect=AssertionError("model must not be constructed"))
        monkeypatch.setattr(service, "AgnoFactory", factory)
        with pytest.raises(CustomException, match="会话不存在"):
            await service.ChatService(auth(2, "bob")).chat_non_stream("hello", session.session_id)
        factory.assert_not_called()
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_model_selection_distinguishes_default_missing_and_selected():
    redis = FakeAsyncRedis(decode_responses=True)
    try:
        assert await service.get_user_model_config(redis, 7) is None
        await redis.set(service._ai_model_active_key(7), "chosen")
        with pytest.raises(CustomException, match="模型配置不可用"):
            await service.get_user_model_config(redis, 7)
        await redis.set(service._ai_model_items_key(7), json.dumps([{"id": "chosen", "model_id": "example"}]))
        assert (await service.get_user_model_config(redis, 7))["model_id"] == "example"
    finally:
        await redis.aclose()


@pytest.mark.asyncio
async def test_redis_failure_does_not_silently_choose_default():
    class Offline:
        async def get(self, _key):
            raise ConnectionError("unavailable")

    with pytest.raises(ConnectionError):
        await service.get_user_model_config(Offline(), 7)


@pytest.mark.asyncio
async def test_chat_query_cancellation_closes_underlying_agno_stream(tmp_path, monkeypatch):
    db = AsyncSqliteDb(db_file=str(tmp_path / "agno.db"))
    await db._create_all_tables()
    monkeypatch.setattr(crud, "_get_agno_db", lambda: db)
    started, closed = asyncio.Event(), asyncio.Event()

    class Agent:
        async def arun(self, **_kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
                yield None
            finally:
                closed.set()

    class Factory:
        def create_agent(self, **_kwargs):
            return Agent()

    monkeypatch.setattr(service, "AgnoFactory", Factory)
    try:
        session = await crud.ChatSessionCRUD(auth(1, "alice")).create(ChatSessionCreateSchema(title="test"))
        stream = service.ChatService(auth(1, "alice")).chat_query(ChatQuerySchema(message="hello", session_id=session.session_id))
        consumer = asyncio.create_task(anext(stream))
        await asyncio.wait_for(started.wait(), timeout=1)
        consumer.cancel()
        await asyncio.gather(consumer, return_exceptions=True)
        await stream.aclose()
        assert closed.is_set()
    finally:
        await db.close()
