"""One lifespan-owned consumer; browser progress never depends on HTTP reads."""

import asyncio
import secrets
from contextlib import suppress

from app.core.logger import logger
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.quote.service import get_quote_service

from .contracts import attempt_request_id
from .service import get_batch_service


class QuoteDispatcher:
    def __init__(self, batches=None, quotes=None, *, interval=1, shutdown_timeout=35):
        self.batches = batches or get_batch_service()
        self.quotes = quotes or get_quote_service()
        self.interval = interval
        self.owner = secrets.token_hex(24)
        self.task = None
        self.stopping = False
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_pending = None

    async def start(self):
        if self.task is None:
            if self.shutdown_pending is not None:
                if not self.shutdown_pending.done():
                    raise RuntimeError("CNC_BATCH_SHUTDOWN_UNSETTLED")
                await self.shutdown_pending
                self.shutdown_pending = None
            self.stopping = False
            await self.batches.repository.settle_expired_claims()
            self.task = asyncio.create_task(self._run(), name="cnc-quote-dispatcher")

    async def stop(self):
        self.stopping = True
        if self.shutdown_pending is None:
            self.shutdown_pending = asyncio.create_task(self._stop_owned())
            self.shutdown_pending.add_done_callback(lambda task: task.exception() if not task.cancelled() else None)
        done, _ = await asyncio.wait({self.shutdown_pending}, timeout=self.shutdown_timeout)
        if done:
            await self.shutdown_pending
            return

        # Do not cancel the cleanup again. Fence still-live Runs where the DB
        # is available, but report failure even if that bounded write fails.
        try:
            async with asyncio.timeout(2):
                for activity in list(self.quotes.activities.values()):
                    claim = getattr(activity, "batch_claim", None)
                    if claim and claim.get("owner") == self.owner:
                        await self.batches.repository.fail_claim(claim, "BATCH_SHUTDOWN_UNSETTLED")
        except Exception:
            logger.warning("CNC batch shutdown reconciliation could not be recorded")
        raise RuntimeError("CNC_BATCH_SHUTDOWN_UNSETTLED")

    async def _stop_owned(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None
        # Join only this dispatcher's local owners before DB disposal. Unlike
        # an HTTP action, shutdown must not depend on the actor retaining RBAC.
        await self.quotes.stop_batch_owners_for_shutdown(self.owner)

    async def tick(self):
        # Claims owned by a previous process may still be valid at startup and
        # expire later. Scan every cycle, before renewing this owner's claims.
        await self.batches.repository.settle_expired_claims()
        active = await self.batches.repository.active(self.owner)
        for item in active:
            if item["run_id"]:
                candidate = await self.batches.quotes.persist_pending_result(item["run_id"])
                if candidate:
                    activity = self.quotes.activities.get(item["run_id"])
                    if activity:
                        activity.view, activity.pending_result = candidate, False
                    continue
            if item["cancel"] and item["run_id"]:
                outcome = await self.quotes.stop_cancelled_batch_owner(item, self.batches.repository)
                if outcome == "owner_unavailable":
                    await self.batches.repository.fail_claim(item, "BATCH_OWNER_LOST_NO_RETRY")
        # Capacity one includes human/reconciliation waits; it is conservative
        # and bounded by the quote owner's existing maximum lifetime.
        if active:
            return
        claim = await self.batches.repository.claim(self.owner)
        if claim is None:
            return
        try:
            auth = await self.batches.quotes.authorizer.load(claim["actor_id"])
            if claim.get("source") == "schedule":
                if not auth.user.is_superuser and "module_cnc:cnc_quote_schedule:create" not in auth.permissions:
                    raise LoginError("SCHEDULE_PERMISSION_DENIED")
            else:
                await self.batches.authorize(auth, "create", for_run=True)
            snapshot = await self.batches.quotes.from_frozen(auth, claim["input_snapshot"])
            await self.quotes.start_snapshot(auth, snapshot, attempt_request_id(claim["id"], claim["attempt_no"]), batch_claim=claim)
        except LoginError as exc:
            if exc.reason in {"CONFIGURATION_BUSY", "ACCOUNT_BUSY"}:
                await self.batches.repository.release_wait(claim)
            else:
                await self.batches.repository.fail_claim(claim, exc.reason)
        except Exception:
            await self.batches.repository.fail_claim(claim, "BATCH_EXECUTION_UNAVAILABLE")

    async def _run(self):
        while not self.stopping:
            try:
                await self.tick()
            except Exception:
                logger.warning("CNC batch dispatch scan failed; durable queue retained")
            await asyncio.sleep(self.interval)
