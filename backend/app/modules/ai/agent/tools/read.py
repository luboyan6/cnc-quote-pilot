"""Read-only CNC tools that revalidate identity, permissions and ownership."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langchain_core.tools import BaseTool, tool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload, with_loader_criteria

from app.core.base_schema import AuthSchema, CoreUserSchema
from app.core.database import async_db_session
from app.modules.cnc.batch.repository import BatchRepository
from app.modules.cnc.cnc_account.service import CncAccountService
from app.modules.cnc.cnc_part.service import CncPartService
from app.modules.cnc.cnc_part_config.service import CncPartConfigService
from app.modules.cnc.cnc_quote_result.evidence import resolve_private_evidence_path
from app.modules.cnc.cnc_quote_result.schema import CncQuoteResultQueryParam
from app.modules.cnc.cnc_quote_result.service import CncQuoteResultService
from app.modules.cnc.monitor.repository import ScheduleRepository
from app.modules.cnc.quote.service import get_quote_service
from app.modules.system.auth.service import LoginService
from app.modules.system.menu.model import MenuModel
from app.modules.system.role.model import RoleModel
from app.modules.system.user.model import UserModel

RefreshAuth = Callable[[], Awaitable[AuthSchema]]


async def _current_auth(actor_id: int, refresh_auth: RefreshAuth, db: AsyncSession) -> AuthSchema:
    session_auth = await refresh_auth()
    if actor_id <= 0 or session_auth.user.id != actor_id:
        raise PermissionError("ACTOR_UNAVAILABLE")
    stmt = (
        select(UserModel)
        .where(UserModel.id == actor_id, UserModel.is_deleted.is_(False), UserModel.status == 0)
        .options(
            selectinload(UserModel.roles).selectinload(RoleModel.menus),
            with_loader_criteria(RoleModel, RoleModel.is_deleted.is_(False)),
            with_loader_criteria(MenuModel, MenuModel.is_deleted.is_(False)),
        )
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise PermissionError("ACTOR_UNAVAILABLE")
    permissions, menu_ids = LoginService._collect_permissions(user)
    return AuthSchema(user=CoreUserSchema.model_validate(user), permissions=permissions, menu_ids=menu_ids)


def _allowed(auth: AuthSchema, permission: str) -> bool:
    return auth.user.is_superuser or permission in auth.permissions or "*:*:*" in auth.permissions


def _require(auth: AuthSchema, *permissions: str) -> None:
    if not all(_allowed(auth, permission) for permission in permissions):
        raise PermissionError("PERMISSION_DENIED")


def _own(item: Any, actor_id: int) -> None:
    # CRUD also applies role data scope; Agent tools restrict to this actor.
    if item.created_id != actor_id:
        raise PermissionError("RECORD_UNAVAILABLE")


async def build_read_tools(actor_id: int, refresh_auth: RefreshAuth, sessions: async_sessionmaker[AsyncSession] = async_db_session) -> list[BaseTool]:
    """Bind trusted server identity, never model-supplied actor or credentials.

    The initial permission set determines the advertised catalog. Every call
    reloads the user, roles and menus and checks permissions again.
    """
    async with sessions() as db:
        initial = await _current_auth(actor_id, refresh_auth, db)

    @tool
    async def cnc_part_detail(part_id: int) -> dict[str, Any]:
        """Read metadata for one of the current user's drawings by ID."""
        if part_id <= 0:
            raise ValueError("INVALID_PART_ID")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_part:detail")
            item = await CncPartService(auth, db).detail(part_id)
            _own(item, actor_id)
            return {"id": item.id, "file_name": item.file_name}

    @tool
    async def cnc_config_detail(config_id: int) -> dict[str, Any]:
        """Read one of the current user's CNC configuration summaries by ID."""
        if config_id <= 0:
            raise ValueError("INVALID_CONFIG_ID")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_part_config:detail")
            item = await CncPartConfigService(auth, db).detail(config_id)
            _own(item, actor_id)
            return item.model_dump(include={"id", "name", "part_id", "site_type", "material", "quantity", "surface_finish", "tolerance", "enabled"}, mode="json")

    @tool
    async def cnc_account_detail(account_id: int) -> dict[str, Any]:
        """Read the current user's account status without credentials or URLs."""
        if account_id <= 0:
            raise ValueError("INVALID_ACCOUNT_ID")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_account:detail")
            item = await CncAccountService(auth, db).detail(account_id)
            _own(item, actor_id)
            return item.model_dump(include={"id", "alias", "platform_id", "platform_name", "enabled", "session_status", "has_credentials"}, mode="json")

    @tool
    async def cnc_quote_status(config_id: int, run_id: str) -> dict[str, Any]:
        """Read the current user's existing quote run status; never start a quote."""
        if config_id <= 0:
            raise ValueError("INVALID_CONFIG_ID")
        run_id = str(UUID(run_id))
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_part_config:update", "module_cnc:cnc_account:update")
            config = await CncPartConfigService(auth, db).detail(config_id)
            _own(config, actor_id)
            view = await get_quote_service().status(auth, config_id, run_id)
            return view.model_dump(include={"run_id", "config_id", "platform_name", "status", "stage"}, mode="json")

    @tool
    async def cnc_quote_result_detail(result_id: int) -> dict[str, Any]:
        """Read one of the current user's persisted quote results by ID."""
        if result_id <= 0:
            raise ValueError("INVALID_RESULT_ID")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_quote_result:query", "module_cnc:cnc_quote_result:detail")
            service = CncQuoteResultService(auth, db)
            row = await service.get_authorized_record(result_id)
            _own(row, actor_id)
            item = await service.detail(result_id)
            data = item.model_dump(
                include={
                    "id", "run_id", "batch_id", "item_id", "round_id", "config_id", "part_id", "platform_id",
                    "platform_name", "quote_status", "unit_price", "total_amount", "tax_amount", "discount_amount",
                    "shipping_amount", "tax_included", "currency", "price_scope", "lead_time_raw", "quantity",
                    "material", "surface_finish", "tolerance", "evidence_id", "evidence_state", "quoted_at",
                    "observed_at", "error_code", "duration_seconds", "queue_ms", "active_execution_ms",
                },
                mode="json",
            )
            data["evidence_available"] = resolve_private_evidence_path(row) is not None
            return data

    def owner_scope(auth: AuthSchema) -> AuthSchema:
        # Agent reporting remains actor-private even for a superuser.
        return auth.model_copy(update={"user": auth.user.model_copy(update={"is_superuser": False})})

    @tool
    async def cnc_quote_statistics(part_id: int | None = None) -> dict[str, Any]:
        """Summarize the current user's persisted quote outcomes and rates."""
        if part_id is not None and part_id <= 0:
            raise ValueError("INVALID_PART_ID")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_quote_result:query")
            stats = await CncQuoteResultService(owner_scope(auth), db).get_stats(CncQuoteResultQueryParam(part_id=part_id))
            data = stats.model_dump(mode="json")
            data["platform_stats_truncated"] = len(data["platform_stats"]) > 30
            data["platform_stats"] = data["platform_stats"][:30]
            return data

    @tool
    async def cnc_quote_history(part_id: int, limit: int = 30) -> list[dict[str, Any]]:
        """Read owned price observations; compare only when a verified key is present."""
        if part_id <= 0 or not 1 <= limit <= 50:
            raise ValueError("INVALID_HISTORY_REQUEST")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_quote_result:query")
            history = await CncQuoteResultService(owner_scope(auth), db).get_history_prices(
                CncQuoteResultQueryParam(part_id=part_id), limit=limit
            )
            return [item.model_dump(exclude={"evidence_screenshot"}, mode="json") for item in history]

    @tool
    async def cnc_batch_status(batch_id: str) -> dict[str, Any]:
        """Read the status and item counts of one of the user's existing batches."""
        batch_id = str(UUID(batch_id))
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_quote_batch:detail")
        data = await BatchRepository(sessions).detail(actor_id, batch_id)
        return jsonable_encoder(data)

    @tool
    async def cnc_batch_items(batch_id: str, offset: int = 0, limit: int = 30) -> list[dict[str, Any]]:
        """Read a bounded page of individual items in one owned batch."""
        batch_id = str(UUID(batch_id))
        if not 0 <= offset <= 1_000_000 or not 1 <= limit <= 50:
            raise ValueError("INVALID_BATCH_PAGE")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_quote_batch:detail")
        items = await BatchRepository(sessions).items(actor_id, batch_id, offset, limit)
        allowed = {
            "id", "batch_id", "config_id", "account_id", "exec_status", "quote_kind", "run_id", "attempt_count",
            "max_attempts", "error_code", "created_at", "started_at", "finished_at", "file_name",
        }
        return jsonable_encoder([
            {key: value for key, value in item.items() if key in allowed} | {"quantity": item["requested"].get("quantity")}
            for item in items
        ])

    @tool
    async def cnc_monitor_status(schedule_id: str, limit: int = 10) -> dict[str, Any]:
        """Read one owned monitoring schedule and its latest recorded rounds."""
        schedule_id = str(UUID(schedule_id))
        if not 1 <= limit <= 20:
            raise ValueError("INVALID_ROUND_LIMIT")
        async with sessions() as db:
            auth = await _current_auth(actor_id, refresh_auth, db)
            _require(auth, "module_cnc:cnc_quote_schedule:detail")
        repository = ScheduleRepository(sessions)
        schedule = await repository.detail(actor_id, schedule_id)
        rounds = await repository.rounds(actor_id, schedule_id, limit=limit)
        allowed = {"id", "name", "interval_minutes", "timezone", "next_run_at", "status", "revision", "last_round_at", "pause_reason"}
        return {"schedule": {key: value for key, value in schedule.items() if key in allowed}, "rounds": rounds}

    specs = [
        (cnc_part_detail, ("module_cnc:cnc_part:detail",)),
        (cnc_config_detail, ("module_cnc:cnc_part_config:detail",)),
        (cnc_account_detail, ("module_cnc:cnc_account:detail",)),
        (cnc_quote_status, ("module_cnc:cnc_part_config:update", "module_cnc:cnc_account:update")),
        (cnc_quote_result_detail, ("module_cnc:cnc_quote_result:query", "module_cnc:cnc_quote_result:detail")),
        (cnc_quote_statistics, ("module_cnc:cnc_quote_result:query",)),
        (cnc_quote_history, ("module_cnc:cnc_quote_result:query",)),
        (cnc_batch_status, ("module_cnc:cnc_quote_batch:detail",)),
        (cnc_batch_items, ("module_cnc:cnc_quote_batch:detail",)),
        (cnc_monitor_status, ("module_cnc:cnc_quote_schedule:detail",)),
    ]
    return [item for item, permissions in specs if all(_allowed(initial, permission) for permission in permissions)]
