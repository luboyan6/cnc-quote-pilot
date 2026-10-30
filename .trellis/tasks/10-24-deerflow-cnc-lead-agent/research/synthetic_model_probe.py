"""Exercise the configured model with an isolated synthetic CNC record.

This script prints only event kinds and error class names. It does not connect
to the project database or send its contents to the model.
"""

import asyncio
import json
import logging
import os
import sys
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
    from app.modules.ai.agent.model_provider import model_from_config
    from app.modules.ai.agent.service import AgentService
    from app.modules.ai.agent.tools import build_read_tools
    from app.modules.cnc.cnc_part.model import CncPartModel
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

    try:
        async with asyncio.timeout(35), model_from_config(config) as model:
            response = await model.ainvoke("Reply with the single word OK.")
            connected = bool(response.content)
    except Exception as exc:
        print(json.dumps({"configuration_complete": True, "model_connected": False, "error_type": type(exc).__name__}))
        return 1

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    models = [DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel, RoleMenusModel, UserPositionsModel, UserRolesModel, CncPartModel]
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
        async with sessions() as db, db.begin():
            db.add(UserModel(id=7, username="synthetic", password="synthetic", name="Synthetic"))
            db.add(RoleModel(id=1, name="reader", code="synthetic-reader"))
            db.add(MenuModel(id=1, name="detail", permission="module_cnc:cnc_part:detail"))
            db.add_all([UserRolesModel(user_id=7, role_id=1), RoleMenusModel(role_id=1, menu_id=1)])
            db.add(CncPartModel(id=42, file_name="synthetic.step", created_id=7))

        async def refresh():
            return AuthSchema(user=CoreUserSchema(id=7))

        tools = await build_read_tools(7, refresh, sessions)
        service = AgentService(InMemorySaver(), timeout=90)
        kinds = []
        try:
            async with asyncio.timeout(100):
                async for event in service.stream(
                    actor_id=7,
                    session_id="synthetic-session",
                    turn_id="synthetic-turn",
                    message="请调用 cnc_part_detail 工具查询图纸 42，然后回答查询到的文件名。",
                    skills=["cnc-part"],
                    model_config=config,
                    tools=tools,
                ):
                    kinds.append(event.type)
        finally:
            await service.close()
        success = connected and "tool.completed" in kinds and kinds[-1:] == ["turn.completed"]
        print(json.dumps({"configuration_complete": True, "model_connected": connected, "synthetic_record_only": True, "events": kinds, "skill_tool_chain_passed": success}))
        return 0 if success else 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
