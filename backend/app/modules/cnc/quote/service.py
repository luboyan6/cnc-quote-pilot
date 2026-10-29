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
        self._jlc_tasks: dict[str, asyncio.Task] = {}
        self._xometry_tasks: dict[str, asyncio.Task] = {}

    async def start(self, auth, config_id, data):
        async with self._start_lock:
            prior = await self.repository.find(auth, config_id, request_id=str(data.request_id))
            if prior:
                return prior
            prior = await self.repository.find(auth, config_id)
            if prior:
                st = await self.status(auth, config_id, prior.run_id)
                if st.reason == "QUOTE_WORKER_UNAVAILABLE_NO_RETRY":
                    await self.repository.cancel_orphan(auth, config_id, prior.run_id)
                else:
                    return st
            snapshot = await self.repository.snapshot(auth, config_id, data.account_id)
            await self.repository.assert_upload_available(snapshot)
            view, created = await self.repository.create(auth, snapshot, str(data.request_id))
            if not created:
                return view
            return await self._launch(auth, snapshot, view)

    async def start_snapshot(self, auth, snapshot, request_id, *, batch_claim=None, export_controlled=None):
        from uuid import uuid4

        async with self._start_lock:
            await self.repository.validate(auth, snapshot)
            await self.repository.assert_upload_available(snapshot)
            lease = None
            if batch_claim:
                owner = str(uuid4())
                lease = (owner, await self.repository.login.claim(snapshot.account, owner))
            try:
                view, created = await self.repository.create(auth, snapshot, str(request_id), batch_claim=batch_claim)
            except BaseException:
                if lease:
                    await self.repository.login.release(snapshot.account, *lease)
                raise
            if not created:
                if lease:
                    await self.repository.login.release(snapshot.account, *lease)
                if view.requested != dict(snapshot.requested.values) or view.account_id != snapshot.account.id:
                    raise QuoteError("CONFIGURATION_BUSY")
                return view
            return await self._launch(auth, snapshot, view, batch_claim=batch_claim, export_controlled=export_controlled, lease=lease)

    async def _launch(self, auth, snapshot, view, *, batch_claim=None, export_controlled=None, lease=None):
        activity = QuoteActivity(auth, snapshot, view, self.repository, self.adapter_factory)
        activity.batch_claim = batch_claim
        activity.export_controlled = export_controlled
        activity.preclaimed_lease = lease
        # Bound retained in-process references without erasing durable runs.
        for key, old in list(self.activities.items()):
            if old.terminal:
                self.activities.pop(key, None)
        self.activities[view.run_id] = activity

        if snapshot.provider_code == "jlc_cnc_cn" and self.adapter_factory is resolve_quote_adapter:
            task = asyncio.create_task(self._run_shortcut(activity, "jlc"))
            self._jlc_tasks[view.run_id] = task
            return activity.view

        if snapshot.provider_code == "xometry_us" and self.adapter_factory is resolve_quote_adapter and batch_claim is None:
            task = asyncio.create_task(self._run_shortcut(activity, "xometry"))
            self._xometry_tasks[view.run_id] = task
            return activity.view

        try:
            if lease:
                await self.manager.start(snapshot.account, quote_activity=activity, lease=lease)
            else:
                await self.manager.start(snapshot.account, quote_activity=activity)
        except Exception as exc:
            if lease:
                await self.repository.login.release(snapshot.account, *lease)
            reason = str(exc.reason) if isinstance(exc, (LoginError, BrowserStop)) else "BROWSER_UNAVAILABLE"
            await activity.finish(str(reason))
        return activity.view

    async def _run_shortcut(self, activity, provider):
        from contextlib import suppress
        from uuid import uuid4

        owner, token = str(uuid4()), None
        lease = self.repository.login
        activity.shortcut_operations = set()

        async def guard():
            await activity.check_inputs()
            await lease.renew(activity.snapshot.account, owner, token)
            if getattr(activity, "batch_claim", None):
                await self.repository.validate_claim(activity.view.run_id)

        async def mutation_guard(operation):
            await guard()
            if operation not in activity.shortcut_operations:
                await self.repository.claim_shortcut(activity.view.run_id, operation)
                activity.shortcut_operations.add(operation)

        async def authenticated_guard(identity, ciphertext):
            from dataclasses import replace

            if identity:
                await lease.bind_identity(activity.snapshot.account, owner, token, identity)
                activity.snapshot = replace(activity.snapshot, account=replace(activity.snapshot.account, identity_code=identity))
            await lease.renew(activity.snapshot.account, owner, token, state=ciphertext)

        async def heartbeat():
            while True:
                await asyncio.sleep(15)
                await guard()

        heartbeat_task = None
        operation_task = None
        try:
            if activity.preclaimed_lease:
                owner, token = activity.preclaimed_lease
            else:
                token = await lease.claim(activity.snapshot.account, owner)
            activity.input_guard, activity.mutation_guard = guard, mutation_guard
            activity.authenticated_guard = authenticated_guard
            heartbeat_task = asyncio.create_task(heartbeat())
            operation_task = asyncio.create_task(self._run_jlc(activity) if provider == "jlc" else self._run_xometry(activity))
            done, _ = await asyncio.wait([heartbeat_task, operation_task], return_when=asyncio.FIRST_COMPLETED)
            if heartbeat_task in done:
                operation_task.cancel()
                with suppress(asyncio.CancelledError):
                    await operation_task
                heartbeat_task.result()
            else:
                await operation_task
        except asyncio.CancelledError:
            if operation_task is not None and not operation_task.done():
                operation_task.cancel()
                with suppress(asyncio.CancelledError):
                    await operation_task
            if not activity.pending_result:
                await activity.finish("SESSION_CLOSED")
        except Exception as exc:
            reason = str(exc.reason) if isinstance(exc, (LoginError, BrowserStop)) else "QUOTE_EXECUTION_FAILED"
            await activity.finish(reason)
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await heartbeat_task
            if token is not None:
                await lease.release(activity.snapshot.account, owner, token)
            self._jlc_tasks.pop(activity.view.run_id, None)
            self._xometry_tasks.pop(activity.view.run_id, None)

    async def _run_jlc(self, activity: QuoteActivity):
        from datetime import UTC, datetime

        from app.core.logger import logger
        from app.modules.cnc.quote.contracts import QuoteResult
        from app.modules.cnc.quote.jlc_quote_service import execute_jlc_quote

        try:
            await activity.change("RUNNING", "login", "CHECKING_LOGIN")
            snapshot = activity.snapshot
            file_path = snapshot.step.path
            req_dict = dict(snapshot.requested.values)
            quantity = int(req_dict.get("quantity", 1))
            material = req_dict.get("material") or "铝合金-6061"
            surface_finish = req_dict.get("surface_finish") or "喷砂+普通阳极氧化 - 本色 - 哑光"
            tolerance = req_dict.get("tolerance") or "GB/T 1804-2000 m级"
            lead_time_pref = req_dict.get("lead_time_pref") or "标准"

            await activity.change("RUNNING", "upload", "UPLOADING_FILE")

            raw = await execute_jlc_quote(
                file_path,
                account=snapshot.account,
                payload=snapshot.payload,
                input_guard=activity.input_guard,
                mutation_guard=activity.mutation_guard,
                authenticated_guard=activity.authenticated_guard,
                quantity=quantity,
                material=material,
                surface_finish=surface_finish,
                tolerance=tolerance,
                lead_time_pref=lead_time_pref,
            )

            # A future reviewed binding must return the actual saved values.
            # Requested/default values alone are not provider readback.
            expected = {"material": material, "quantity": str(quantity), "surface_finish": surface_finish, "tolerance": tolerance}
            effective = raw.get("effective")
            if not isinstance(effective, dict) or any(str(effective.get(key)) != value for key, value in expected.items()):
                raise LoginError("JLC_EFFECTIVE_PARAMETERS_UNVERIFIED")

            await activity.change("RUNNING", "quote", "FETCHING_QUOTE")

            now = datetime.now(UTC)
            pref_tier = raw.get("selected_lead_time") or {}
            all_tiers = raw.get("all_lead_time_tiers") or []

            tier_title = pref_tier.get("tier", "")
            tier_days = pref_tier.get("days", "")
            tier_ship = pref_tier.get("estimated_ship_date", "")

            lead_time_payload = {
                **pref_tier,
                "text": f"{tier_title} {tier_days}",
                "raw_text": f"{tier_title} {tier_days}" + (f" · {tier_ship}" if tier_ship else ""),
                "tiers": all_tiers,
            }

            tax_amt = raw.get("tax_amount") or pref_tier.get("tax_amount") or ""
            total_amt = raw.get("total_amount") or pref_tier.get("total_amount") or ""
            discount_amt = raw.get("discount_amount") or pref_tier.get("discount_amount") or ""

            result = QuoteResult(
                status="REFERENCE_ESTIMATE",
                amount=str(raw["unit_price"]) if raw.get("unit_price") is not None else None,
                currency="CNY",
                price_scope="unit",
                lead_time=lead_time_payload,
                effective={key: str(effective[key]) for key in expected},
                priced_at=now,
                observed_at=now,
                tax_included=True,
                shipping_included=None,
                freshness="CURRENT_CONFIRMED",
                tax_amount=str(tax_amt) if tax_amt else None,
                total_amount=str(total_amt) if total_amt else None,
                discount_amount=str(discount_amt) if discount_amt else None,
                lead_time_tiers=all_tiers,
            )
            candidate = activity.view.model_copy(
                update={
                    "status": "REFERENCE_ESTIMATE",
                    "stage": "complete",
                    "reason": "PROVIDER_REFERENCE_ESTIMATE",
                    "result": result,
                    "can_input": False,
                }
            )
            evidence = {
                "kind": "REFERENCE_ESTIMATE",
                "platform": "嘉立创中国",
                "customer_code": raw.get("customer_code"),
                "file_name": raw.get("file_name"),
                "geometry": raw.get("geometry"),
                "all_lead_time_tiers": raw.get("all_lead_time_tiers"),
                "evidence_screenshot": raw.get("evidence_screenshot"),
                "note": raw.get("note"),
            }
            await activity.input_guard()
            await activity.repository.stage_shortcut_result(candidate, evidence)
            activity.pending_result = True
            await activity.repository.save(candidate, evidence=evidence)
            activity.view = candidate
            activity.pending_result = False
        except asyncio.CancelledError:
            if not activity.pending_result:
                await activity.finish("SESSION_CLOSED")
        except Exception as exc:
            logger.warning("JLC quote execution failed")
            if not getattr(activity, "pending_result", False):
                await activity.finish(str(exc.reason) if isinstance(exc, (LoginError, BrowserStop)) else "QUOTE_EXECUTION_FAILED")

    async def _run_xometry(self, activity: QuoteActivity):
        from datetime import UTC, datetime
        from pathlib import Path

        from app.config.path_conf import BASE_DIR
        from app.core.logger import logger
        from app.modules.cnc.quote.contracts import QuoteResult
        from app.modules.cnc.quote.xometry_quote_service import (
            execute_xometry_quote,
            map_to_xometry_parameters,
        )

        try:
            await activity.change("RUNNING", "login", "CHECKING_LOGIN")
            snapshot = activity.snapshot
            file_path = snapshot.step.path
            if not isinstance(file_path, Path):
                file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = (BASE_DIR / file_path).resolve()

            req_dict = dict(snapshot.requested.values)
            quantity = int(req_dict.get("quantity", 1))
            material = req_dict.get("material") or "铝合金"
            surface_finish = req_dict.get("surface_finish")
            tolerance = req_dict.get("tolerance")
            roughness = req_dict.get("roughness")
            lead_time_pref = req_dict.get("lead_time_pref") or "Standard"

            mapped = map_to_xometry_parameters(
                material=material,
                surface_finish=surface_finish,
                tolerance=tolerance,
                roughness=roughness,
            )

            await activity.change("RUNNING", "upload", "UPLOADING_FILE")

            raw = await execute_xometry_quote(
                file_path,
                account=snapshot.account,
                payload=snapshot.payload,
                input_guard=activity.input_guard,
                mutation_guard=activity.mutation_guard,
                authenticated_guard=activity.authenticated_guard,
                export_controlled=activity.export_controlled,
                quantity=quantity,
                material=mapped["material"],
                surface_finish=mapped["surface_finish"],
                tolerance=mapped["tolerance"],
                roughness=mapped["roughness"],
                lead_time_pref=lead_time_pref,
            )

            await activity.change("RUNNING", "quote", "FETCHING_QUOTE")

            now = datetime.now(UTC)
            pref_tier = raw.get("selected") or {}
            all_tiers = raw.get("tiers") or []

            tier_title = pref_tier.get("tier", "Standard")
            tier_days = pref_tier.get("days", "")
            tier_ship = pref_tier.get("estimated_ship_date", "")

            lead_time_payload = {
                **pref_tier,
                "text": f"{tier_title} {tier_days}".strip(),
                "raw_text": f"{tier_title} {tier_days}" + (f" · {tier_ship}" if tier_ship else ""),
                "tiers": all_tiers,
            }

            clean_effective: dict[str, str] = {}
            for k, v in (raw.get("effective") or {}).items():
                if isinstance(v, dict):
                    clean_effective[k] = str(v.get("total") or v.get("unit") or "")
                elif v is not None:
                    clean_effective[k] = str(v)

            quote_status = raw.get("quote_status")
            if quote_status not in {"QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW"}:
                raise QuoteError("QUOTE_RESULT_INVALID")
            result = QuoteResult(
                status=quote_status,
                amount=str(raw["unit_price"]) if raw.get("unit_price") is not None else (str(raw["total_amount"]) if raw.get("total_amount") is not None else None),
                currency="USD",
                price_scope="unit" if raw.get("unit_price") is not None else ("line" if raw.get("total_amount") is not None else None),
                lead_time=lead_time_payload,
                effective=clean_effective,
                priced_at=now,
                observed_at=now,
                tax_included=None,
                shipping_included=None,
                freshness="CURRENT_CONFIRMED",
                tax_amount=None,
                total_amount=str(raw["total_amount"]) if raw.get("total_amount") is not None else None,
                discount_amount=None,
                lead_time_tiers=all_tiers,
            )
            candidate = activity.view.model_copy(
                update={
                    "status": quote_status,
                    "stage": "complete",
                    "reason": "QUOTE_COMPLETED",
                    "result": result,
                    "can_input": False,
                }
            )
            evidence = {
                "kind": quote_status,
                "platform": "Xometry US",
                "quote_id": raw.get("quote_id"),
                "file_name": raw.get("file_name"),
                "all_lead_time_tiers": all_tiers,
                "evidence_screenshot": raw.get("evidence_screenshot"),
                "note": raw.get("note"),
            }
            await activity.input_guard()
            await activity.repository.stage_shortcut_result(candidate, evidence)
            activity.pending_result = True
            await activity.repository.save(candidate, evidence=evidence)
            activity.view = candidate
            activity.pending_result = False
        except asyncio.CancelledError:
            if not activity.pending_result:
                await activity.finish("SESSION_CLOSED")
        except Exception as exc:
            logger.exception(f"Xometry quote execution failed: {exc}")
            if not getattr(activity, "pending_result", False):
                await activity.finish(str(exc.reason) if isinstance(exc, (LoginError, BrowserStop)) else "QUOTE_EXECUTION_FAILED")

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

    async def stop_cancelled_batch_owner(self, claim, batches):
        """Stop only the live local owner of an already-authorized batch cancel.

        This internal cleanup never grants a browser mutation or an HTTP action.
        It remains available after the actor's execution permission is revoked.
        """
        if not await batches.owns_cancellation(claim):
            return "claim_lost"
        return await self._stop_local_batch_owner(claim)

    async def _stop_local_batch_owner(self, claim):
        from app.modules.cnc.browser.session import finish_cleanup

        activity = self.activities.get(claim["run_id"])
        binding = getattr(activity, "batch_claim", None) if activity else None
        if (
            activity is None
            or not binding
            or any(binding.get(key) != claim[key] for key in ("id", "owner", "token"))
            or activity.view.run_id != claim["run_id"]
            or activity.snapshot.config_id != claim["config_id"]
            or activity.snapshot.account.actor_id != claim["actor_id"]
        ):
            return "owner_unavailable"
        tasks = self._jlc_tasks if claim["run_id"] in self._jlc_tasks else self._xometry_tasks
        task = tasks.get(claim["run_id"])
        if task is not None:
            if not task.done() and not getattr(activity, "terminal", False):
                task.cancel()
            try:
                await finish_cleanup(task)
            except BrowserStop:
                # A task cancelled before its first turn has no finally block.
                pass
            if activity.pending_result:
                pending = await self.repository.persist_pending_result(claim["run_id"])
                if pending is not None:
                    activity.view, activity.pending_result = pending, False
            else:
                await activity.finish("SESSION_CLOSED")
            return "stopped"
        owned = self.manager.accounts.get(activity.snapshot.account.id)
        if owned is None or owned.quote_activity is not activity:
            return "owner_unavailable"
        if getattr(activity, "terminal", False) and owned.task:
            await finish_cleanup(owned.task)
        else:
            await self.manager.revoke(activity.snapshot.account.id)
        return "stopped"

    async def stop_batch_owners_for_shutdown(self, owner):
        """Join this dispatcher's local activities even when actor/DB auth fails."""
        failed = False
        for run_id, activity in list(self.activities.items()):
            binding = getattr(activity, "batch_claim", None)
            if not binding or binding.get("owner") != owner:
                continue
            if getattr(activity, "terminal", False):
                owned = self.manager.accounts.get(activity.snapshot.account.id)
                if run_id not in self._jlc_tasks and run_id not in self._xometry_tasks and (owned is None or owned.quote_activity is not activity):
                    continue
            claim = binding | {"run_id": run_id, "config_id": activity.snapshot.config_id, "actor_id": activity.snapshot.account.actor_id}
            try:
                if await self._stop_local_batch_owner(claim) != "stopped":
                    failed = True
            except Exception:
                failed = True
        if failed:
            raise QuoteError("BATCH_SHUTDOWN_RECONCILIATION_REQUIRED")

    async def status(self, auth, config_id, run_id):
        view, activity = await self._load(auth, config_id, run_id)
        if view.status in TERMINAL:
            return view
        if activity is not None and (run_id in self._jlc_tasks or run_id in self._xometry_tasks):
            return activity.view
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
        if activity is not None and (run_id in self._jlc_tasks or run_id in self._xometry_tasks):
            if kind == "close":
                tasks = self._jlc_tasks if run_id in self._jlc_tasks else self._xometry_tasks
                task = tasks.pop(run_id, None)
                if task and not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                if not activity.pending_result:
                    await activity.finish("SESSION_CLOSED")
                return activity.view
            return activity.view
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
        if kind in {"input", "resume"} and (not activity.can_input or not activity.view.can_input):
            raise QuoteError("QUOTE_MANUAL_INPUT_NOT_ALLOWED")
        if kind == "declaration" and (not activity.can_input or activity.view.export_declaration is None):
            raise QuoteError("QUOTE_EXPORT_DECLARATION_INVALID")
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
