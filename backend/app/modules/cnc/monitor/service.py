from __future__ import annotations

from typing import Any

from app.modules.cnc.batch.contracts import digest
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.quote.repository import QuoteRepository

from .contracts import (
    ScheduleCreate,
    ScheduleError,
    ScheduleUpdate,
)
from .repository import ScheduleRepository


class MonitorService:
    def __init__(self, quote_repository: QuoteRepository | None = None, repository: ScheduleRepository | None = None):
        self.quotes = quote_repository or QuoteRepository()
        self.repository = repository or ScheduleRepository(self.quotes.sessions)

    async def authorize(self, auth, permission: str):
        current = await self.quotes.authorizer.load(auth.user.id)
        if not current.user.is_superuser and f"module_cnc:cnc_quote_schedule:{permission}" not in current.permissions:
            raise ScheduleError("SCHEDULE_PERMISSION_DENIED", 403)
        return current

    async def _normalize_targets(self, auth, targets) -> dict[str, Any]:
        items = {}
        for t in targets:
            for qty in t.quantities:
                snapshot = await self.quotes.snapshot(auth, t.config_id, t.account_id, quantity=qty)
                item_data = snapshot.frozen | {
                    "config_id": t.config_id,
                    "account_id": snapshot.account.id,
                    "file_name": snapshot.file_name,
                    "requested": dict(snapshot.requested.values) | {"quantity": str(qty)},
                }
                items[digest(item_data)] = item_data
        return {"items": list(items.values())}

    async def create(self, auth, data: ScheduleCreate) -> dict[str, Any]:
        auth = await self.authorize(auth, "create")
        snapshot = await self._normalize_targets(auth, data.targets)
        schedule_id = await self.repository.create(auth.user.id, data, snapshot)
        return await self.repository.detail(auth.user.id, schedule_id)

    async def update(self, auth, schedule_id: str, data: ScheduleUpdate) -> dict[str, Any]:
        auth = await self.authorize(auth, "update")
        snapshot = None
        if data.targets is not None:
            snapshot = await self._normalize_targets(auth, data.targets)
        return await self.repository.update(auth.user.id, schedule_id, data, target_snapshot=snapshot)

    async def pause(self, auth, schedule_id: str) -> dict[str, Any]:
        auth = await self.authorize(auth, "update")
        return await self.repository.pause(auth.user.id, schedule_id)

    async def resume(self, auth, schedule_id: str) -> dict[str, Any]:
        auth = await self.authorize(auth, "update")
        # Re-verify targets before resuming
        sched = await self.repository.detail(auth.user.id, schedule_id)
        targets_data = sched.get("target_snapshot", {}).get("items", [])
        for it in targets_data:
            await self.quotes.from_frozen(auth, it)
        return await self.repository.resume(auth.user.id, schedule_id)

    async def list(self, auth, offset: int = 0, limit: int = 50) -> dict[str, Any]:
        auth = await self.authorize(auth, "query")
        return await self.repository.list(auth.user.id, offset, limit)

    async def detail(self, auth, schedule_id: str) -> dict[str, Any]:
        auth = await self.authorize(auth, "detail")
        return await self.repository.detail(auth.user.id, schedule_id)

    async def rounds(self, auth, schedule_id: str, offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        auth = await self.authorize(auth, "detail")
        return await self.repository.rounds(auth.user.id, schedule_id, offset, limit)

    async def scan_due(self, clock_now=None) -> list[dict[str, Any]]:
        validated = {}
        for sched in await self.repository.due(clock_now):
            try:
                auth = await self.quotes.authorizer.load(sched["actor_id"])
                if not auth.user.is_superuser and "module_cnc:cnc_quote_schedule:create" not in auth.permissions:
                    raise ScheduleError("SCHEDULE_PERMISSION_DENIED", 403)
                for item in sched["target_snapshot"].get("items", []):
                    await self.quotes.from_frozen(auth, item)
                validated[sched["id"]] = (sched["revision"], sched["next_run_at"])
            except (LoginError, BrowserStop, ScheduleError):
                await self.repository.pause_invalid(sched["id"], sched["revision"], sched["next_run_at"])
        return await self.repository.scan_due(clock_now=clock_now, validated=validated)


_monitor_service = None


def get_monitor_service() -> MonitorService:
    global _monitor_service
    if _monitor_service is None:
        _monitor_service = MonitorService()
    return _monitor_service
