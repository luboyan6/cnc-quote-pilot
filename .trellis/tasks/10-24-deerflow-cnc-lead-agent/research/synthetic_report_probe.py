"""Run the configured model against synthetic, in-memory quote data only."""

import asyncio
import json
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ["LANGSMITH_TRACING"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))
logging.disable(logging.CRITICAL)


async def main():
    from langgraph.checkpoint.memory import InMemorySaver
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config.setting import settings
    from app.core.base_model import MappedBase
    from app.core.base_schema import AuthSchema, CoreUserSchema
    from app.modules.ai.agent.service import AgentService
    from app.modules.ai.agent.tools import build_read_tools
    from app.modules.cnc.cnc_quote_result.model import CncQuoteResultModel
    from app.modules.system.dept.model import DeptModel
    from app.modules.system.menu.model import MenuModel
    from app.modules.system.position.model import PositionModel
    from app.modules.system.role.model import RoleDeptsModel, RoleMenusModel, RoleModel
    from app.modules.system.user.model import UserModel, UserPositionsModel, UserRolesModel

    config = {
        "model_id": settings.OPENAI_MODEL,
        "base_url": settings.OPENAI_BASE_URL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0,
    }
    if not all(config[key] for key in ("model_id", "base_url", "api_key")):
        print(json.dumps({"configuration_complete": False}))
        return 1

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    models = [
        DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel,
        RoleMenusModel, UserPositionsModel, UserRolesModel, CncQuoteResultModel,
    ]
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
        async with sessions.begin() as db:
            db.add_all([
                UserModel(id=7, username="synthetic", password="synthetic", name="Synthetic"),
                RoleModel(id=1, name="reader", code="synthetic-reader"),
                MenuModel(id=1, name="results", permission="module_cnc:cnc_quote_result:query"),
                UserRolesModel(user_id=7, role_id=1), RoleMenusModel(role_id=1, menu_id=1),
                CncQuoteResultModel(id=1, created_id=7, part_id=42, quote_status="QUOTED", unit_price=Decimal("12.34"), currency="USD"),
                CncQuoteResultModel(id=2, created_id=7, part_id=42, quote_status="REFERENCE_ESTIMATE", unit_price=Decimal("13.00"), currency="USD"),
            ])

        async def refresh():
            return AuthSchema(user=CoreUserSchema(id=7))

        tools = await build_read_tools(7, refresh, sessions)
        service = AgentService(InMemorySaver(), timeout=90)
        events = []
        try:
            async with asyncio.timeout(100):
                async for event in service.stream(
                    actor_id=7,
                    session_id="synthetic-report-session",
                    turn_id="synthetic-report-turn",
                    message="请调用 cnc_quote_statistics 工具统计图纸 42 的报价结果，并报告正式报价和参考估价的数量。",
                    skills=["cnc-quote-report"],
                    model_config=config,
                    tools=tools,
                ):
                    events.append((event.type, event.payload.get("name")))
        finally:
            await service.close()
        success = (
            ("skill.activated", "cnc-quote-report") in events
            and ("tool.completed", "cnc_quote_statistics") in events
            and events[-1:] == [("turn.completed", None)]
        )
        print(json.dumps({"synthetic_record_only": True, "events": events, "report_chain_passed": success}))
        return 0 if success else 1
    except Exception as exc:
        print(json.dumps({"synthetic_record_only": True, "error_type": type(exc).__name__}))
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
