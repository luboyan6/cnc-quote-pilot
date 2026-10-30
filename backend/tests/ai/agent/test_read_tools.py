"""Read tools exercise real SQLite services and current RBAC, not the MCP API."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base_model import MappedBase
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.exceptions import CustomException
from app.modules.ai.agent.graph import build_graph
from app.modules.ai.agent.skills import SkillCatalog
from app.modules.ai.agent.tools import build_read_tools
from app.modules.cnc.batch.contracts import BatchError
from app.modules.cnc.cnc_part.model import CncPartModel
from app.modules.cnc.cnc_quote_batch.model import CncQuoteBatchModel
from app.modules.cnc.cnc_quote_batch_item.model import CncQuoteBatchItemModel
from app.modules.cnc.cnc_quote_result import evidence
from app.modules.cnc.cnc_quote_result.model import CncQuoteResultModel
from app.modules.cnc.cnc_quote_schedule.model import CncQuoteScheduleModel
from app.modules.cnc.cnc_quote_schedule_round.model import CncQuoteScheduleRoundModel
from app.modules.cnc.monitor.contracts import ScheduleError
from app.modules.system.dept.model import DeptModel
from app.modules.system.menu.model import MenuModel
from app.modules.system.position.model import PositionModel
from app.modules.system.role.model import RoleDeptsModel, RoleMenusModel, RoleModel
from app.modules.system.user.model import UserModel, UserPositionsModel, UserRolesModel


@pytest.mark.asyncio
async def test_real_read_tool_scopes_owner_and_rechecks_deleted_permissions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    models = [DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel, RoleMenusModel, UserPositionsModel, UserRolesModel, CncPartModel]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
    async with sessions() as db, db.begin():
        db.add_all([UserModel(id=7, username="first", password="hash", name="First"), UserModel(id=9, username="second", password="hash", name="Second")])
        db.add(RoleModel(id=1, name="reader", code="agent-reader"))
        db.add(MenuModel(id=1, name="detail", permission="module_cnc:cnc_part:detail"))
        db.add_all([UserRolesModel(user_id=7, role_id=1), RoleMenusModel(role_id=1, menu_id=1)])
        db.add_all([CncPartModel(id=42, file_name="first.step", file_path="private/path", created_id=7), CncPartModel(id=43, file_name="other.step", created_id=9)])

    async def refresh() -> AuthSchema:
        return AuthSchema(user=CoreUserSchema(id=7))

    try:
        tools = await build_read_tools(7, refresh, sessions)
        assert [item.name for item in tools] == ["cnc_part_detail"]
        assert [skill.name for skill in SkillCatalog().list({item.name for item in tools})] == ["cnc-assistant", "cnc-part"]
        part = tools[0]
        assert await part.ainvoke({"part_id": 42}) == {"id": 42, "file_name": "first.step"}

        class ToolModel(BaseChatModel):
            @property
            def _llm_type(self):
                return "tool-test"

            def bind_tools(self, tools, **kwargs):
                return self

            def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content="done"))])

            async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
                if any(isinstance(message, ToolMessage) for message in messages):
                    yield ChatGenerationChunk(message=AIMessageChunk(content="found"))
                else:
                    yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_call_chunks=[{"name": "cnc_part_detail", "args": '{"part_id":42}', "id": "call-1", "index": 0}]))

        saver = InMemorySaver()
        graph = build_graph(model=ToolModel(), tools=tools, catalog=SkillCatalog(), checkpointer=saver)
        config = {"configurable": {"thread_id": "test-user-7"}}
        async for _ in graph.astream({"messages": [HumanMessage(content="读取图纸 42")], "skill_context": ["cnc-part"]}, config, stream_mode=["messages", "updates"]):
            pass
        state = (await graph.aget_state(config)).values
        results = [message.content for message in state["messages"] if isinstance(message, ToolMessage)]
        assert len(results) == 1 and "first.step" in str(results[0])
        assert "private/path" not in str(results[0])
        assert state["messages"][-1].content == "found"
        with pytest.raises((PermissionError, CustomException)):
            await part.ainvoke({"part_id": 43})
        async with sessions() as db, db.begin():
            await db.execute(update(MenuModel).where(MenuModel.id == 1).values(is_deleted=True))
        with pytest.raises(PermissionError):
            await part.ainvoke({"part_id": 42})
        async with sessions() as db, db.begin():
            await db.execute(update(MenuModel).where(MenuModel.id == 1).values(is_deleted=False))
            await db.execute(update(RoleModel).where(RoleModel.id == 1).values(is_deleted=True))
        with pytest.raises(PermissionError):
            await part.ainvoke({"part_id": 42})
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_quote_reporting_tools_use_domain_results_and_actor_private_scope(tmp_path, monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    private = tmp_path / "private-evidence"
    private.mkdir()
    (private / "proof.png").write_bytes(b"synthetic image")
    monkeypatch.setattr(evidence, "PRIVATE_EVIDENCE_DIR", private)
    models = [DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel, RoleMenusModel, UserPositionsModel, UserRolesModel, CncQuoteResultModel]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
    async with sessions.begin() as db:
        db.add_all([
            UserModel(id=7, username="report-admin", password="hash", name="Admin", is_superuser=True),
            UserModel(id=9, username="report-other", password="hash", name="Other"),
            CncQuoteResultModel(id=1, created_id=7, part_id=42, quote_status="QUOTED", unit_price=Decimal("100"), currency="USD", evidence_id="proof", evidence_state="available", evidence_screenshot="private/secret.png"),
            CncQuoteResultModel(id=2, created_id=7, part_id=42, quote_status="REFERENCE_ESTIMATE", unit_price=Decimal("120"), currency="USD"),
            CncQuoteResultModel(id=3, created_id=9, part_id=42, quote_status="QUOTED", unit_price=Decimal("999"), currency="USD"),
        ])

    async def refresh() -> AuthSchema:
        return AuthSchema(user=CoreUserSchema(id=7))

    try:
        tools = {item.name: item for item in await build_read_tools(7, refresh, sessions)}
        names = {skill.name for skill in SkillCatalog().list(set(tools))}
        assert {"cnc-quote-result", "cnc-quote-report"} <= names

        detail = await tools["cnc_quote_result_detail"].ainvoke({"result_id": 1})
        assert detail["quote_status"] == "QUOTED" and Decimal(detail["unit_price"]) == Decimal("100")
        assert detail["evidence_available"] is True
        assert "evidence_screenshot" not in detail and "private/secret.png" not in str(detail)
        with pytest.raises((PermissionError, CustomException)):
            await tools["cnc_quote_result_detail"].ainvoke({"result_id": 3})

        stats = await tools["cnc_quote_statistics"].ainvoke({"part_id": 42})
        assert (stats["total_quotes"], stats["quoted_quotes"], stats["reference_estimate_quotes"]) == (2, 1, 1)
        assert stats["total_items"] == 2 and stats["formal_quote_rate"] == "50.0%"
        history = await tools["cnc_quote_history"].ainvoke({"part_id": 42})
        assert {item["id"] for item in history} == {1, 2}
        assert {item["quote_kind"] for item in history} == {"QUOTED", "REFERENCE_ESTIMATE"}
        assert all(item["comparison_key"] is None and item["price_diff"] is None for item in history)
        assert "private/secret.png" not in str(history)
        with pytest.raises(ValueError):
            await tools["cnc_quote_history"].ainvoke({"part_id": 42, "limit": 51})

        async with sessions.begin() as db:
            await db.execute(update(UserModel).where(UserModel.id == 7).values(is_superuser=False))
        with pytest.raises(PermissionError):
            await tools["cnc_quote_statistics"].ainvoke({"part_id": 42})
        assert not {"cnc-quote-result", "cnc-quote-report"} & {
            skill.name for skill in SkillCatalog().list({item.name for item in await build_read_tools(7, refresh, sessions)})
        }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_batch_and_monitor_status_tools_keep_owner_and_round_truth():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    models = [
        DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel, RoleMenusModel,
        UserPositionsModel, UserRolesModel, CncQuoteBatchModel, CncQuoteBatchItemModel,
        CncQuoteScheduleModel, CncQuoteScheduleRoundModel,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
    own_batch, foreign_batch, own_schedule, foreign_schedule = (str(uuid4()) for _ in range(4))
    now = datetime.now(UTC)
    async with sessions.begin() as db:
        db.add_all([
            UserModel(id=7, username="monitor-admin", password="hash", name="Admin", is_superuser=True),
            UserModel(id=9, username="monitor-other", password="hash", name="Other"),
            CncQuoteBatchModel(id=own_batch, actor_id=7, request_id=str(uuid4()), request_fingerprint="a", created_at=now, updated_at=now),
            CncQuoteBatchModel(id=foreign_batch, actor_id=9, request_id=str(uuid4()), request_fingerprint="b", created_at=now, updated_at=now),
            CncQuoteScheduleModel(id=own_schedule, actor_id=7, name="Daily", interval_minutes=60, timezone="UTC", anchor_time=now,
                                  next_run_at=now + timedelta(hours=1), status="PAUSED", target_snapshot={"path": "private/path"},
                                  target_fingerprint="a", created_at=now, updated_at=now),
            CncQuoteScheduleModel(id=foreign_schedule, actor_id=9, name="Other", interval_minutes=60, timezone="UTC", anchor_time=now,
                                  next_run_at=now, status="ENABLED", target_snapshot={}, target_fingerprint="b", created_at=now, updated_at=now),
        ])
        await db.flush()
        db.add_all([
            CncQuoteScheduleRoundModel(id=str(uuid4()), schedule_id=own_schedule, round_no=1, scheduled_for=now,
                                       status="MISSED", schedule_revision=1, skip_reason="MISSED_SLOT_DOWNTIME", created_at=now),
            CncQuoteScheduleRoundModel(id=str(uuid4()), schedule_id=own_schedule, round_no=2, scheduled_for=now + timedelta(hours=1),
                                       status="SKIPPED_OVERLAP", schedule_revision=1, skip_reason="PREVIOUS_ROUND_RUNNING", created_at=now),
        ])
        db.add_all([
            CncQuoteBatchItemModel(
                id=str(uuid4()), batch_id=own_batch, config_id=config_id, account_id=1,
                input_snapshot={"requested": {"quantity": str(quantity)}, "file_name": "part.step", "private": "secret/path"},
                input_fingerprint=f"{config_id}-{quantity}", exec_status="FAILED" if (config_id, quantity) == (4, 5) else "COMPLETED",
                created_at=now, updated_at=now,
            )
            for config_id in range(1, 5) for quantity in (1, 2, 5)
        ])

    async def refresh() -> AuthSchema:
        return AuthSchema(user=CoreUserSchema(id=7))

    try:
        tools = {item.name: item for item in await build_read_tools(7, refresh, sessions)}
        batch = await tools["cnc_batch_status"].ainvoke({"batch_id": own_batch})
        assert batch["status"] == "PARTIAL_FAILED" and batch["counts"] == {"COMPLETED": 11, "FAILED": 1}
        batch_items = await tools["cnc_batch_items"].ainvoke({"batch_id": own_batch, "limit": 20})
        assert {(item["config_id"], item["quantity"]) for item in batch_items} == {
            (config_id, str(quantity)) for config_id in range(1, 5) for quantity in (1, 2, 5)
        }
        assert "secret/path" not in str(batch_items)
        with pytest.raises(ValueError):
            await tools["cnc_batch_items"].ainvoke({"batch_id": own_batch, "limit": 51})
        monitor = await tools["cnc_monitor_status"].ainvoke({"schedule_id": own_schedule})
        assert monitor["schedule"]["status"] == "PAUSED"
        assert [item["status"] for item in monitor["rounds"]] == ["SKIPPED_OVERLAP", "MISSED"]
        assert "private/path" not in str(monitor) and "target_snapshot" not in monitor["schedule"]
        with pytest.raises(BatchError):
            await tools["cnc_batch_status"].ainvoke({"batch_id": foreign_batch})
        with pytest.raises(ScheduleError):
            await tools["cnc_monitor_status"].ainvoke({"schedule_id": foreign_schedule})
        with pytest.raises(ValueError):
            await tools["cnc_monitor_status"].ainvoke({"schedule_id": own_schedule, "limit": 21})
        async with sessions.begin() as db:
            await db.execute(update(UserModel).where(UserModel.id == 7).values(is_superuser=False))
        with pytest.raises(PermissionError):
            await tools["cnc_batch_status"].ainvoke({"batch_id": own_batch})
        with pytest.raises(PermissionError):
            await tools["cnc_monitor_status"].ainvoke({"schedule_id": own_schedule})
    finally:
        await engine.dispose()
