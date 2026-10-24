"""Fresh quote-local RBAC for long-running activity, independent of JWT cache."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload, with_loader_criteria

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.modules.system.auth.service import LoginService
from app.modules.system.menu.model import MenuModel
from app.modules.system.role.model import RoleModel
from app.modules.system.user.model import UserModel

from .contracts import QuoteError


class ActorAuthorizer:
    def __init__(self, sessions):
        self.sessions = sessions

    async def load(self, actor_id: int, *, for_run: bool = True) -> AuthSchema:
        async with self.sessions() as db:
            statement = (
                select(UserModel)
                .where(UserModel.id == actor_id, UserModel.is_deleted.is_(False), UserModel.status == 0)
                .options(
                    selectinload(UserModel.roles).selectinload(RoleModel.menus),
                    with_loader_criteria(RoleModel, RoleModel.is_deleted.is_(False)),
                    with_loader_criteria(MenuModel, MenuModel.is_deleted.is_(False)),
                )
            )
            user = await db.scalar(statement)
            if user is None:
                raise QuoteError("QUOTE_ACTOR_UNAVAILABLE")
            permissions, menu_ids = LoginService._collect_permissions(user)
            auth = AuthSchema(user=CoreUserSchema.model_validate(user), permissions=permissions, menu_ids=menu_ids)
            groups = [
                {"module_cnc:cnc_part_config:query", "module_cnc:cnc_part_config:detail"},
                {"module_cnc:cnc_account:query"},
            ]
            if for_run:
                groups.extend([{"module_cnc:cnc_part_config:update"}, {"module_cnc:cnc_account:update"}])
            if not auth.user.is_superuser and any(not required.intersection(permissions) for required in groups):
                raise QuoteError("QUOTE_PERMISSION_REVOKED")
            return auth
