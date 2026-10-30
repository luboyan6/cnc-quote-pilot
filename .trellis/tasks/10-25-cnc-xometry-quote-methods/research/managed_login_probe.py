"""Verify selected drawing/account through the existing owner; no quote mutations."""

import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from loguru import logger

logger.remove()

from app.core.base_model import MappedBase
from app.core.database import async_engine
from app.utils.import_util import ImportUtil

ImportUtil.find_models(MappedBase)

from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.runtime import LoginManager
from app.modules.cnc.quote.repository import QuoteRepository

EXPECTED_HASH = "efb3ef2b45736f2c84507c6be57c5bca505975323a33f7319140d7bff5d72887"


class Inspection:
    """Read-only activity hook so the Page never crosses the login owner task."""

    def __init__(self, repository, auth, snapshot):
        self.repository, self.auth, self.snapshot = repository, auth, snapshot
        self.activity_id = str(uuid4())
        self.terminal = False
        self.can_input = False
        self.ready_for_step = True
        self.poll_interval = 1
        self.done = asyncio.Event()
        self.result = {"quote_mutations": 0, "account_id": snapshot.account.id, "config_id": snapshot.config_id}

    async def check_inputs(self):
        await self.repository.validate(self.auth, self.snapshot)

    async def login_state(self, status, reason):
        if status in {"WAITING_HUMAN", "FAILED", "CLOSED"}:
            self.result.update({"status": status, "reason": reason})
            self.terminal = True
            self.done.set()

    async def advance(self, session, provider):
        await self.check_inputs()
        confirmed = await provider.verify(session, self.snapshot.account.username)
        session.check_active()
        parsed = urlsplit(session.page.url)
        inputs = session.page.locator('input[type="file"]')
        count = await inputs.count()
        self.result.update({
            "status": "READY" if confirmed else "UNVERIFIED",
            "identity_match": confirmed,
            "host": parsed.hostname,
            "path": parsed.path,
            "primary_file_input_count": count,
            "primary_file_accept": await inputs.get_attribute("accept") if count == 1 else None,
            "instant_quote_control_count": await session.page.locator("#dashboard-get-instant-quote-primary").count(),
            "stored_file_matches_selected": self.snapshot.payload.sha256 == EXPECTED_HASH,
            "stored_file_size": len(self.snapshot.payload.buffer),
        })
        self.terminal = True
        self.done.set()

    async def finish(self, reason):
        if "status" not in self.result:
            self.result.update({"status": "STOPPED", "reason": reason})
        self.terminal = True
        self.done.set()


async def main():
    manager = None
    inspection = None
    result = {"quote_mutations": 0}
    try:
        repository = QuoteRepository()
        auth = await repository.authorizer.load(1)
        snapshot = await repository.snapshot(auth, 3, 1)
        if snapshot.part_id != 4 or snapshot.payload.sha256 != EXPECTED_HASH or len(snapshot.payload.buffer) != 589942:
            raise LoginError("QUOTE_INPUT_CHANGED")
        inspection = Inspection(repository, auth, snapshot)
        manager = LoginManager(repository=repository.login, idle_seconds=30, lifetime_seconds=90)
        await manager.start(snapshot.account, quote_activity=inspection)
        await asyncio.wait_for(inspection.done.wait(), timeout=95)
        result = inspection.result
    except Exception as error:
        result = inspection.result if inspection is not None else result
        reason = getattr(error, "reason", None)
        result.update({"status": "STOPPED", "reason": str(reason) if reason is not None else "MANAGED_LOGIN_PROBE_UNAVAILABLE", "error_type": type(error).__name__})
    finally:
        if manager is not None:
            await manager.close_all()
        await async_engine.dispose()
    Path(__file__).with_name("managed-login-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
