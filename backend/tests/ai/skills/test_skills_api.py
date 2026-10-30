"""Exercise the HTTP catalog against real, isolated permission records."""

from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.routers import DOMAIN_CONTROLLERS, api_v1
from app.common.enums import RET
from app.config.setting import settings
from app.core.base_model import MappedBase
from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import CustomException, handle_exception
from app.modules.ai.agent.skills import SkillCatalog
from app.modules.ai.skills import service as skill_service
from app.modules.ai.skills.controller import SkillRouter
from app.modules.system.dept.model import DeptModel
from app.modules.system.menu.model import MenuModel
from app.modules.system.position.model import PositionModel
from app.modules.system.role.model import RoleDeptsModel, RoleMenusModel, RoleModel
from app.modules.system.user.model import UserModel, UserPositionsModel, UserRolesModel


@pytest.mark.asyncio
async def test_skill_routes_match_live_permissions_and_handle_revocation(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    models = [DeptModel, MenuModel, PositionModel, RoleModel, UserModel, RoleDeptsModel, RoleMenusModel, UserPositionsModel, UserRolesModel]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: MappedBase.metadata.create_all(sync, tables=[model.__table__ for model in models]))
    async with sessions() as db, db.begin():
        db.add_all([
            UserModel(id=7, username="part-user", password="hash", name="Part User"),
            UserModel(id=9, username="config-user", password="hash", name="Config User"),
            RoleModel(id=1, name="part-reader", code="part-reader"),
            RoleModel(id=2, name="config-reader", code="config-reader"),
            MenuModel(id=1, name="chat", permission="module_ai:chat:query"),
            MenuModel(id=2, name="part", permission="module_cnc:cnc_part:detail"),
            MenuModel(id=3, name="config", permission="module_cnc:cnc_part_config:detail"),
            UserRolesModel(user_id=7, role_id=1),
            UserRolesModel(user_id=9, role_id=2),
            RoleMenusModel(role_id=1, menu_id=1),
            RoleMenusModel(role_id=1, menu_id=2),
            RoleMenusModel(role_id=2, menu_id=1),
            RoleMenusModel(role_id=2, menu_id=3),
        ])

    monkeypatch.setattr(settings, "AI_CHAT_ENGINE", "deerflow_source")
    monkeypatch.setattr(skill_service, "async_db_session", sessions)
    app = FastAPI()
    handle_exception(app)
    app.include_router(api_v1)
    app.state.agent_service = SimpleNamespace(catalog=SkillCatalog())
    current = [AuthSchema(user=CoreUserSchema(id=7), permissions=["module_ai:chat:query"])]

    async def authenticated():
        return current[0]

    app.dependency_overrides[get_current_user] = authenticated
    try:
        paths = app.openapi()["paths"]
        assert "/ai/skills/list" in paths
        assert "/ai/skills/detail/{name}" in paths
        assert DOMAIN_CONTROLLERS["/ai"].count(SkillRouter) == 1

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = await client.get("/ai/skills/list")
            assert first.status_code == 200
            assert [item["name"] for item in first.json()["data"]] == ["cnc-assistant", "cnc-part"]
            assert set(first.json()["data"][1]) == {"name", "description", "allowed_tools"}

            detail = await client.get("/ai/skills/detail/cnc-part")
            assert detail.status_code == 200
            assert detail.json()["data"]["allowed_tools"] == ["cnc_part_detail"]
            assert "本人图纸" in detail.json()["data"]["content"]
            assert "path" not in detail.json()["data"]
            assert (await client.get("/ai/skills/detail/cnc-config")).status_code == 404
            assert (await client.get("/ai/skills/detail/no-such-skill")).status_code == 404

            # A different actor sees only the capabilities granted to them.
            current[0] = AuthSchema(user=CoreUserSchema(id=9), permissions=["module_ai:chat:query"])
            second = await client.get("/ai/skills/list")
            assert [item["name"] for item in second.json()["data"]] == ["cnc-assistant", "cnc-config"]
            assert (await client.get("/ai/skills/detail/cnc-part")).status_code == 404

            # The original login snapshot still has chat permission, but the
            # database role/menu changes take effect on the next request.
            current[0] = AuthSchema(user=CoreUserSchema(id=7), permissions=["module_ai:chat:query"])
            async with sessions() as db, db.begin():
                await db.execute(update(MenuModel).where(MenuModel.id == 2).values(is_deleted=True))
            revoked = await client.get("/ai/skills/list")
            assert [item["name"] for item in revoked.json()["data"]] == ["cnc-assistant"]
            assert (await client.get("/ai/skills/detail/cnc-part")).status_code == 404

            async with sessions() as db, db.begin():
                await db.execute(update(MenuModel).where(MenuModel.id == 1).values(is_deleted=True))
            assert (await client.get("/ai/skills/list")).status_code == 403

            async with sessions() as db, db.begin():
                await db.execute(update(MenuModel).where(MenuModel.id == 1).values(is_deleted=False))
                await db.execute(update(UserModel).where(UserModel.id == 7).values(is_deleted=True))
            assert (await client.get("/ai/skills/list")).status_code == 401

            # Without a live source runtime, Agno cannot advertise these skills.
            monkeypatch.setattr(settings, "AI_CHAT_ENGINE", "agno")
            assert (await client.get("/ai/skills/list")).json()["data"] == []
            assert (await client.get("/ai/skills/detail/cnc-assistant")).status_code == 404

            async def unauthenticated():
                raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code)

            app.dependency_overrides[get_current_user] = unauthenticated
            assert (await client.get("/ai/skills/list")).status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unavailable_and_invalid_skill_names_share_the_same_error():
    service = skill_service.SkillService(AuthSchema(user=CoreUserSchema(id=1)), None)
    for name in ("cnc-part", "../secret", "unknown"):
        with pytest.raises(CustomException) as exc:
            await service.detail(name)
        assert exc.value.code == RET.NOT_FOUND.code
