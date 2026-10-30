"""Filter the live Agent catalog using its actual per-user tool builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.enums import RET
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException

from .schema import SkillDetailSchema, SkillInfoSchema

if TYPE_CHECKING:
    from app.modules.ai.agent.skills import Skill, SkillCatalog


class SkillService:
    """A catalog is available only when owned by an active source AgentService."""

    def __init__(
        self,
        auth: AuthSchema,
        catalog: SkillCatalog | None,
        *,
        sessions: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.auth = auth
        self.catalog = catalog
        self.sessions = sessions or async_db_session

    async def _available_tools(self) -> set[str]:
        # Agent dependencies are optional for Agno deployments. Loading these
        # modules only for an active catalog preserves the old startup path.
        from app.modules.ai.agent.tools import build_read_tools
        from app.modules.ai.agent.tools.read import _allowed, _current_auth

        actor_id = self.auth.user.id

        async def refresh_auth() -> AuthSchema:
            # HTTP authentication already checked the token for this request;
            # _current_auth independently reloads the user's live DB roles.
            return self.auth

        try:
            async with self.sessions() as db:
                current = await _current_auth(actor_id, refresh_auth, db)
            if not _allowed(current, "module_ai:chat:query"):
                raise CustomException(msg="无权限操作", code=RET.FORBIDDEN.code)
            tools = await build_read_tools(actor_id, refresh_auth, self.sessions)
        except PermissionError as exc:
            raise CustomException(msg="认证已失效", code=RET.UNAUTHORIZED.code) from exc
        return {tool.name for tool in tools}

    @staticmethod
    def _info(skill: Skill) -> SkillInfoSchema:
        return SkillInfoSchema(name=skill.name, description=skill.description, allowed_tools=list(skill.allowed_tools))

    async def list(self) -> list[SkillInfoSchema]:
        if self.catalog is None:
            return []
        tools = await self._available_tools()
        return [self._info(skill) for skill in self.catalog.list(tools)]

    async def detail(self, name: str) -> SkillDetailSchema:
        if self.catalog is None:
            raise CustomException(msg="技能不存在或不可用", code=RET.NOT_FOUND.code)
        tools = await self._available_tools()
        try:
            skill = self.catalog.get(name, tools)
        except (OSError, UnicodeError, ValueError) as exc:
            raise CustomException(msg="技能不存在或不可用", code=RET.NOT_FOUND.code) from exc
        return SkillDetailSchema(**self._info(skill).model_dump(), content=skill.content)
