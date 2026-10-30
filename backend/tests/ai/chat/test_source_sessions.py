"""Source session management and REST integration in a disposable database."""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base_schema import AuthSchema, CoreUserSchema, PaginationQueryParam
from app.core.exceptions import CustomException
from app.modules.ai.agent.service import AgentService
from app.modules.ai.chat import controller, source_service
from app.modules.ai.chat.model import SourceChatMessage, SourceChatSession
from app.modules.ai.chat.schema import AiChatRequestSchema, ChatSessionCreateSchema, ChatSessionQueryParam, ChatSessionUpdateSchema
from app.modules.ai.chat.source_repository import SourceChatRepository, VisibleMessage
from app.modules.ai.chat.source_sessions import SourceSessionService


def user(actor_id: int) -> AuthSchema:
    return AuthSchema(user=CoreUserSchema(id=actor_id, username=f"user-{actor_id}"), permissions=["module_ai:chat:query", "module_ai:chat:detail"])


@pytest.mark.asyncio
async def test_source_crud_owner_isolation_pagination_and_atomic_delete():
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SourceChatSession.__table__.create)
            await conn.run_sync(SourceChatMessage.__table__.create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        own = SourceSessionService(user(1), sessions)
        other = SourceSessionService(user(2), sessions)
        first = await own.create(ChatSessionCreateSchema(title="first"))
        second = await own.create(ChatSessionCreateSchema(title="second"))
        foreign = await other.create(ChatSessionCreateSchema(title="foreign"))
        async with sessions.begin() as db:
            await SourceChatRepository(db, 1).project(first.session_id, [VisibleMessage("message-1", "user", "hello", 0)])
        detail = await own.get_session(first.session_id)
        assert detail.messages[0].content == "hello"
        assert detail.model_dump()["runs"][0]["messages"][0]["role"] == "user"
        assert (await own.page(page_no=1, page_size=1, search=ChatSessionQueryParam(), order_by=[{"created_time": "asc"}])).total == 2
        await own.update(first.session_id, ChatSessionUpdateSchema(title="renamed"))
        assert (await own.page(page_no=1, page_size=10, search=ChatSessionQueryParam(title="renamed"))).total == 1
        with pytest.raises(CustomException, match="会话不存在"):
            await other.get_session(first.session_id)
        with pytest.raises(CustomException, match="会话不存在"):
            await own.delete([second.session_id, foreign.session_id])
        assert (await own.get_session(second.session_id)).session_id == second.session_id
        await own.delete([first.session_id, second.session_id])
        assert (await own.page(page_no=1, page_size=10, search=ChatSessionQueryParam())).total == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_source_rest_nonstream_then_detail_uses_current_user_and_checkpoint(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SourceChatSession.__table__.create)
            await conn.run_sync(SourceChatMessage.__table__.create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        original = SourceSessionService
        monkeypatch.setattr(controller.settings, "AI_CHAT_ENGINE", "deerflow_source")
        monkeypatch.setattr(controller, "SourceSessionService", lambda auth: original(auth, sessions))
        monkeypatch.setattr(controller, "async_db_session", sessions)

        async def fresh_user(*, db, redis, token):
            assert token == "Bearer test-token"
            return user(1)

        async def no_tools(_actor, _refresh, _sessions):
            return []

        async def selected_config(_redis, _actor):
            return {"model_id": "sample", "base_url": "https://test.invalid", "api_key": "secret"}

        @asynccontextmanager
        async def factory(_config):
            yield FakeListChatModel(responses=["answer"])

        monkeypatch.setattr(controller, "get_current_user", fresh_user)
        monkeypatch.setattr(controller, "get_user_model_config", selected_config)
        monkeypatch.setattr(source_service, "build_read_tools", no_tools)
        # Ensure source graph ownership checks and projection use the same DB.
        original_source_service = source_service.SourceChatService
        monkeypatch.setattr(source_service, "SourceChatService", lambda auth, agent, refresh: original_source_service(auth, agent, refresh, sessions))

        agent = AgentService(InMemorySaver(), model_factory=factory)
        request = SimpleNamespace(headers={"authorization": "Bearer test-token"}, app=SimpleNamespace(state=SimpleNamespace(redis=object(), agent_service=agent)))
        try:
            result = await controller.ai_chat_controller(user(1), request.app.state.redis, AiChatRequestSchema(message="hello"), request)
            data = json.loads(result.body)["data"]
            assert data["response"] == "answer"
            sid = data["session_id"]
            detail = await controller.get_session_detail_controller(user(1), sid, request)
            visible = json.loads(detail.body)["data"]["messages"]
            assert [(entry["role"], entry["content"]) for entry in visible] == [("user", "hello"), ("assistant", "answer")]
            listed = await controller.get_session_list_controller(user(1), PaginationQueryParam(), ChatSessionQueryParam())
            assert json.loads(listed.body)["data"]["total"] == 1
            assert "secret" not in str(agent.checkpointer.storage)
        finally:
            await agent.close()
    finally:
        await engine.dispose()
