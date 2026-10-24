"""HTTP orchestration never touches a Playwright Page or holds an HTTP DB session."""

import asyncio

from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.runtime import get_login_manager

from .contracts import TERMINAL, QuoteError
from .providers import resolve_quote_adapter
from .repository import QuoteRepository
from .runner import QuoteActivity


class QuoteService:
    def __init__(self, repository=None, manager=None, adapter_factory=resolve_quote_adapter):
        self.repository = repository or QuoteRepository()
        self.manager = manager or get_login_manager()
        self.adapter_factory = adapter_factory
        self.activities: dict[str, QuoteActivity] = {}
        self._start_lock = asyncio.Lock()

    async def start(self, auth, config_id, data):
        async with self._start_lock:
            prior = await self.repository.find(auth, config_id, request_id=str(data.request_id))
            if prior:
                return prior
            prior = await self.repository.find(auth, config_id)
            if prior:
                return await self.status(auth, config_id, prior.run_id)
            snapshot = await self.repository.snapshot(auth, config_id, data.account_id)
            view, created = await self.repository.create(auth, snapshot, str(data.request_id))
            if not created:
                return view
            activity = QuoteActivity(auth, snapshot, view, self.repository, self.adapter_factory)
            # Bound retained in-process references without erasing durable runs.
            for key, old in list(self.activities.items()):
                if old.terminal:
                    self.activities.pop(key, None)
            self.activities[view.run_id] = activity
            try:
                await self.manager.start(snapshot.account, quote_activity=activity)
            except Exception as exc:
                reason = str(exc.reason) if isinstance(exc, (LoginError, BrowserStop)) else "BROWSER_UNAVAILABLE"
                await activity.finish(str(reason))
            return activity.view

    async def _load(self, auth, config_id, run_id):
        try:
            view = await self.repository.find(auth, config_id, run_id=run_id)
        except LoginError:
            prior = self.activities.get(run_id)
            if prior and prior.snapshot.config_id == config_id and prior.snapshot.account.actor_id == auth.user.id:
                await self.manager.revoke(prior.snapshot.account.id)
            raise
        if view is None:
            raise QuoteError("QUOTE_RUN_UNAVAILABLE")
        activity = self.activities.get(run_id)
        if activity and activity.snapshot.account.actor_id != auth.user.id:
            raise QuoteError("QUOTE_RUN_UNAVAILABLE")
        return view, activity

    async def status(self, auth, config_id, run_id):
        view, activity = await self._load(auth, config_id, run_id)
        if view.status in TERMINAL:
            return view
        owned = self.manager.accounts.get(view.account_id)
        if activity is None or owned is None or owned.quote_activity is not activity:
            # A different worker or a restart must not acquire/replay a claimed
            # mutation. Preserve the durable nonterminal record for inspection.
            return view.model_copy(update={"status": "WAITING_HUMAN", "reason": "QUOTE_WORKER_UNAVAILABLE_NO_RETRY", "can_input": False})
        try:
            await self.repository.validate(auth, activity.snapshot)
        except Exception:
            await self.manager.revoke(activity.snapshot.account.id)
            raise
        return activity.view

    async def command(self, auth, config_id, run_id, kind, payload=None):
        view, activity = await self._load(auth, config_id, run_id)
        if view.status in TERMINAL:
            if kind in {"close", "resume"}:
                return view
            raise QuoteError("QUOTE_RUN_CLOSED")
        if activity is None:
            if kind == "close":
                return await self.repository.cancel_orphan(auth, config_id, run_id)
            raise QuoteError("QUOTE_WORKER_UNAVAILABLE_NO_RETRY")
        if kind != "close":
            try:
                await self.repository.validate(auth, activity.snapshot)
            except Exception:
                await self.manager.revoke(activity.snapshot.account.id)
                raise
        if kind in {"input", "resume"} and not activity.can_input:
            raise QuoteError("QUOTE_MANUAL_INPUT_NOT_ALLOWED")
        owned = self.manager.accounts.get(activity.snapshot.account.id)
        if owned is None:
            if kind == "close":
                return await self.repository.cancel_orphan(auth, config_id, run_id)
            raise QuoteError("QUOTE_RUN_CLOSED")
        result = await self.manager.command(activity.snapshot.account, owned.session_id, "verify" if kind == "resume" else kind, payload, activity_id=run_id)
        return result if kind == "frame" else activity.view


_service: QuoteService | None = None


def get_quote_service():
    global _service
    if _service is None:
        _service = QuoteService()
    return _service
