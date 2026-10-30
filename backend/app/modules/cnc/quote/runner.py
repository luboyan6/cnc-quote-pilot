"""One bounded step at a time, called ONLY by the existing browser owner task."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import monotonic

from app.modules.cnc.browser.contracts import (
    Authentication,
    AuthStatus,
    ConfigurationReceipt,
    DeclarationReceipt,
    IntentKey,
    Operation,
    PriceScope,
    QuoteFreshness,
    SubmissionReceipt,
    UploadReceipt,
    item_fingerprint,
)
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import StepPayload
from app.modules.cnc.browser.workflow import KNOWN_CURRENCIES, QuoteRequest, QuoteWorkflow, validate_quote

from .contracts import TERMINAL, ExportDeclaration, ExportDeclarationAdapter, ExportDeclarationDecision, ProvisionalQuote, QuoteError, QuoteResult
from .providers import AdapterBinding, resolve_quote_adapter
from .repository import DurableIntentStore


class QuoteActivity:
    def __init__(self, auth, snapshot, view, repository, adapter_factory=resolve_quote_adapter):
        self.auth = auth
        self.snapshot = snapshot
        self.view = view
        self.repository = repository
        self.adapter_factory = adapter_factory
        self.intents = DurableIntentStore(repository.sessions)
        self.workflow = QuoteWorkflow(self.intents, read_retries=0, read_timeout_seconds=12)
        self.binding: AdapterBinding | None = None
        self.upload: UploadReceipt | None = None
        self.submitted: SubmissionReceipt | None = None
        self.started_at = datetime.now(UTC)
        self.begun = False
        self.parse_observations = 0
        self.parse_deadline = 0.0
        self.next_step_at = 0.0
        self.phase_deadline = 0.0
        self.configure_pending = False
        self.configure_observations = 0
        self.configure_deadline = 0.0
        self.declaration_reauth = False
        self.pending_declaration: ExportDeclaration | None = None
        self.batch_claim: dict | None = None
        self.export_controlled: bool | None = None
        self.preclaimed_lease: tuple[str, int] | None = None
        self.shortcut_operations: set[str] = set()
        self.pending_result = False
        self.input_guard: Callable[[], Awaitable[None]] = self.check_inputs
        self.mutation_guard: Callable[[str], Awaitable[None]] = self._missing_guard
        self.authenticated_guard: Callable[[str | None, str], Awaitable[None]] = self._missing_guard

    async def _missing_guard(self, *args):
        raise QuoteError("QUOTE_EXECUTION_UNAVAILABLE")

    @property
    def ready_for_step(self):
        return monotonic() >= self.next_step_at

    @property
    def poll_interval(self):
        return max(0.1, min(15.0, self.next_step_at - monotonic()))

    @staticmethod
    def _manual_reason(adapter):
        reason = getattr(adapter, "manual_reason", None)
        return reason if reason in {"QUOTE_EXPORT_DECLARATION_REQUIRED", "QUOTE_PARAMETER_CONFIRMATION_REQUIRED"} else None

    @property
    def activity_id(self):
        return self.view.run_id

    @property
    def terminal(self):
        return self.view.status in TERMINAL

    @property
    def can_input(self):
        return self.view.status == "WAITING_HUMAN"

    async def change(self, status, stage, reason, viewport=None):
        declaration = self.view.export_declaration if status == "WAITING_HUMAN" else None
        update = {"status": status, "stage": stage, "reason": reason, "can_input": status == "WAITING_HUMAN" and declaration is None, "export_declaration": declaration}
        if viewport is not None:
            # 人工要按这个尺寸把点击换算到真实页面坐标，必须回报当前视口而不是默认值。
            update["viewport"] = viewport
        candidate = self.view.model_copy(update=update)
        await self.repository.save(candidate)
        self.view = candidate

    async def login_state(self, status, reason):
        if self.terminal or self.begun:
            return
        mapped = "WAITING_HUMAN" if status == "WAITING_HUMAN" else "AUTHENTICATING"
        if status != "READY":
            await self.change(mapped, "login", reason)

    async def check_inputs(self):
        await self.repository.validate(self.auth, self.snapshot)
        if getattr(self, "batch_claim", None):
            await self.repository.validate_claim(self.activity_id)
        await self.repository.assert_active(self.snapshot.account.actor_id, self.activity_id)
        if self.upload is None:
            await self.repository.assert_upload_available(self.snapshot, run_id=self.activity_id)

    async def _adapter_pause(self, adapter, reason):
        declaration = getattr(adapter, "export_declaration", None)
        if declaration is None and reason == "QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY":
            declaration = self.view.export_declaration
        if declaration is not None and not isinstance(declaration, ExportDeclaration):
            raise QuoteError("QUOTE_EXPORT_DECLARATION_INVALID")
        candidate = self.view.model_copy(update={"status": "WAITING_HUMAN", "stage": "parse", "reason": reason, "can_input": declaration is None, "export_declaration": declaration})
        await self.repository.save(candidate)
        self.view = candidate

    async def declare(self, session, provider, decision: ExportDeclarationDecision):
        await self.check_inputs()
        if not self.can_input or self.binding is None or self.view.export_declaration is None:
            raise QuoteError("QUOTE_EXPORT_DECLARATION_INVALID")
        adapter = self.binding.adapter
        if not isinstance(adapter, ExportDeclarationAdapter):
            raise QuoteError("QUOTE_EXPORT_DECLARATION_INVALID")
        if decision.declaration_id != self.view.export_declaration.declaration_id:
            await self._adapter_pause(adapter, "QUOTE_EXPORT_DECLARATION_STALE")
            return
        session.invalidate_authentication()
        if not await provider.verify(session, self.snapshot.account.username):
            if adapter.can_reauthenticate(session):
                self.declaration_reauth = True
                self.pending_declaration = self.view.export_declaration
                self.view = self.view.model_copy(update={"export_declaration": None})
            await self.change("WAITING_HUMAN", self.view.stage, "LOGIN_IDENTITY_VERIFICATION_REQUIRED")
            return
        session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, session.scope))
        current = await adapter.read_export_declaration(session)
        key = IntentKey(session.scope, self.activity_id, "1", Operation.DECLARATION, item_fingerprint(self.snapshot.payload.sha256, self.snapshot.requested))
        if current is None:
            receipt = await self.binding.adapter.reconcile(session, key)
            if isinstance(receipt, DeclarationReceipt) and receipt.declaration_id == decision.declaration_id and receipt.choice == decision.choice and receipt.sha256 == self.snapshot.payload.sha256:
                await self.intents.confirm(key, receipt)
                self.parse_deadline, self.parse_observations, self.next_step_at = monotonic() + 180, 0, 0
                await self.change("RUNNING", "parse", "QUOTE_CONTINUING")
            else:
                await self._adapter_pause(adapter, "QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY")
            return
        if current.declaration_id != decision.declaration_id or current != self.view.export_declaration:
            await self._adapter_pause(adapter, "QUOTE_EXPORT_DECLARATION_STALE")
            return
        await self.repository.record_declaration(self.auth, self.snapshot, self.activity_id, current, decision.choice)
        await self.check_inputs()
        try:
            receipt = await self.workflow._mutation(
                key, session, self.binding.adapter, lambda: adapter.continue_declaration(session, current, decision.choice), self.snapshot.payload.sha256, self.snapshot.requested
            )
        except BrowserStop as exc:
            if exc.reason != Reason.MUTATION_UNCERTAIN:
                raise
            await self._adapter_pause(adapter, "QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY")
            return
        if not isinstance(receipt, DeclarationReceipt) or receipt.declaration_id != current.declaration_id or receipt.choice != decision.choice:
            raise QuoteError("QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY")
        self.parse_deadline, self.parse_observations, self.next_step_at = monotonic() + 180, 0, 0
        await self.change("RUNNING", "parse", "QUOTE_CONTINUING")

    async def allow_manual_input(self, session):
        if not self.declaration_reauth:
            return self.view.can_input
        adapter = self.binding.adapter if self.binding else None
        if not isinstance(adapter, ExportDeclarationAdapter):
            return False
        if adapter.can_reauthenticate(session):
            return True
        # Authentication may redirect between the status response and a human
        # click. Re-observe the declaration before allowing any more input.
        self.declaration_reauth = False
        current = await adapter.read_export_declaration(session)
        if current is None:
            self.view = self.view.model_copy(update={"export_declaration": self.pending_declaration})
            await self._adapter_pause(adapter, "QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY")
        else:
            await self._adapter_pause(adapter, "QUOTE_EXPORT_DECLARATION_REQUIRED")
        self.pending_declaration = None
        return False

    async def resume(self, session, provider):
        await self.check_inputs()
        if self.declaration_reauth:
            adapter = self.binding.adapter if self.binding else None
            if not isinstance(adapter, ExportDeclarationAdapter):
                raise QuoteError("QUOTE_EXPORT_DECLARATION_INVALID")
            if adapter.can_reauthenticate(session):
                await self.change("WAITING_HUMAN", self.view.stage, "LOGIN_IDENTITY_VERIFICATION_REQUIRED")
                return
            await self.allow_manual_input(session)
            return
        if self.view.export_declaration is not None:
            raise QuoteError("QUOTE_EXPORT_DECLARATION_REQUIRED")
        if not self.begun:
            return
        # This check never navigates away from an uploaded/configured item.
        session.invalidate_authentication()
        if not await provider.verify(session, self.snapshot.account.username):
            await self.change("WAITING_HUMAN", self.view.stage, "LOGIN_IDENTITY_VERIFICATION_REQUIRED")
            return
        session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, session.scope))
        if self.view.stage == "parse":
            self.parse_deadline = monotonic() + 180
            self.parse_observations = 0
            self.next_step_at = 0
        await self.change("RUNNING", self.view.stage, "QUOTE_CONTINUING")

    async def advance(self, session, provider):
        if self.terminal or self.can_input:
            return
        self.phase_deadline = monotonic() + 14
        await self.check_inputs()
        session.check_active()
        session.invalidate_authentication()
        if not await provider.verify(session, self.snapshot.account.username):
            await self.change("WAITING_HUMAN", self.view.stage, "LOGIN_IDENTITY_VERIFICATION_REQUIRED")
            return
        session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, session.scope))
        if not self.begun:
            self.binding = self.adapter_factory(self.snapshot, self.activity_id)
            if self.binding is None:
                raise QuoteError("PROVIDER_AUTOMATION_UNVERIFIED")
            if not self.binding.version or type(self.binding.max_size) is not int or not 0 < len(self.snapshot.payload.buffer) <= self.binding.max_size:
                raise QuoteError("FILE_EXCEEDS_PROVIDER_LIMIT")
            set_guard = getattr(self.binding.adapter, "set_input_guard", None)
            if callable(set_guard):
                set_guard(self.check_inputs)
            self.begun = True
            await self.change("RUNNING", "upload", "UPLOADING_FILE")
            return
        if self.binding is None:
            raise QuoteError("PROVIDER_AUTOMATION_UNVERIFIED")
        adapter = self.binding.adapter
        requested = self.snapshot.requested
        sha256 = self.snapshot.payload.sha256
        fingerprint = item_fingerprint(sha256, requested)

        def key(operation):
            return IntentKey(session.scope, self.activity_id, "1", operation, fingerprint)

        if self.upload is None:
            if self.view.stage == "parse":
                # Reconcile only. The committed upload claim can NEVER grant a
                # second upload after a slow parser or an unconfirmed receipt.
                self.parse_observations += 1
                receipt = await adapter.reconcile(session, key(Operation.UPLOAD))
                if receipt is None:
                    manual_reason = self._manual_reason(adapter)
                    if manual_reason:
                        await self._adapter_pause(adapter, manual_reason)
                    elif self.parse_observations >= 90 or monotonic() >= self.parse_deadline:
                        await self.change("WAITING_HUMAN", "parse", "UPLOAD_RECEIPT_UNCONFIRMED_NO_RETRY")
                    else:
                        self.next_step_at = monotonic() + 2
                    return
                self.workflow._check_receipt(receipt, key(Operation.UPLOAD), sha256, requested, None)
                await self.intents.confirm(key(Operation.UPLOAD), receipt)
            else:

                async def upload_once():
                    # Shorter than the owner phase bound, leaving time to keep
                    # the durable uncertainty and enter read-only reconciliation.
                    budget = min(9.0, self.phase_deadline - monotonic() - 1)
                    if budget <= 0:
                        raise TimeoutError
                    async with asyncio.timeout(budget):
                        return await adapter.upload(session, self.snapshot.payload)

                try:
                    # Identity verification is an external await; permissions or
                    # frozen inputs may change while it is in flight.
                    await self.check_inputs()
                    receipt = await self.workflow._mutation(key(Operation.UPLOAD), session, adapter, upload_once, sha256, requested)
                except BrowserStop as exc:
                    if exc.reason != Reason.MUTATION_UNCERTAIN:
                        raise
                    self.parse_deadline = monotonic() + 180
                    self.next_step_at = monotonic() + 2
                    manual_reason = self._manual_reason(adapter)
                    if manual_reason:
                        await self._adapter_pause(adapter, manual_reason)
                    else:
                        await self.change("RUNNING", "parse", "AWAITING_MODEL_PARSE")
                    return
            if not isinstance(receipt, UploadReceipt):
                raise BrowserStop(Reason.MUTATION_UNCERTAIN)
            self.upload = receipt
            self.next_step_at = 0
            await self.change("RUNNING", "configure", "SETTING_PARAMETERS")
        elif self.view.stage == "configure":
            upload = self.upload

            async def configure():
                await adapter.configure(session, upload, requested)
                return ConfigurationReceipt(await adapter.read_effective(session, upload))

            await self.check_inputs()
            if self.configure_pending:
                self.configure_observations += 1
                receipt = await adapter.reconcile(session, key(Operation.CONFIGURE))
                if receipt is None:
                    if self.configure_observations >= 90 or monotonic() >= self.configure_deadline:
                        await self.change("WAITING_HUMAN", "configure", "QUOTE_CONFIGURATION_UNCONFIRMED_NO_RETRY")
                    else:
                        self.next_step_at = monotonic() + 2
                    return
                self.workflow._check_receipt(receipt, key(Operation.CONFIGURE), sha256, requested, upload)
                await self.intents.confirm(key(Operation.CONFIGURE), receipt)
            else:
                try:
                    await self.workflow._mutation(key(Operation.CONFIGURE), session, adapter, configure, sha256, requested, upload)
                except BrowserStop as exc:
                    if exc.reason != Reason.MUTATION_UNCERTAIN:
                        raise
                    self.configure_pending = True
                    self.configure_deadline = monotonic() + 180
                    self.next_step_at = monotonic() + 2
                    await self.change("RUNNING", "configure", "QUOTE_CONFIGURATION_RECONCILING")
                    return
            self.next_step_at = 0
            await self.change("RUNNING", "quote", "FETCHING_QUOTE")
        elif self.submitted is None:
            upload = self.upload
            effective = await adapter.read_effective(session, upload)
            if effective != requested:
                raise BrowserStop(Reason.PARAMETERS_MISMATCH)
            await self.check_inputs()
            receipt = await self.workflow._mutation(key(Operation.SUBMIT), session, adapter, lambda: adapter.submit(session, upload, requested), sha256, requested, upload)
            if not isinstance(receipt, SubmissionReceipt):
                raise BrowserStop(Reason.MUTATION_UNCERTAIN)
            self.submitted = receipt
            await self.change("RUNNING", "persist", "VALIDATING_QUOTE")
        else:
            observation = await adapter.extract_quote(session, self.upload, self.submitted)
            request = QuoteRequest(self.activity_id, "1", self.snapshot.step, requested)
            if isinstance(observation, ProvisionalQuote):
                result = self._provisional_result(observation, session)
                reason = "PROVIDER_REFERENCE_ESTIMATE" if result.status == "REFERENCE_ESTIMATE" else "PROVIDER_PENDING_REVIEW"
                evidence_code = observation.evidence_code
                actual = observation.observation
            else:
                validated = validate_quote(observation, session, request, self.upload, self.submitted, self.started_at)
                result = QuoteResult.model_validate(validated.as_dict())
                reason = "QUOTE_VERIFIED"
                evidence_code = "SHARED_QUOTE_VALIDATOR_ACCEPTED"
                actual = observation
            # save() commits before any public view is returned as QUOTED.
            candidate = self.view.model_copy(update={"status": result.status, "stage": "complete", "reason": reason, "result": result, "can_input": False})
            evidence = {
                "kind": result.status,
                "provider_evidence_code": evidence_code,
                "adapter_version": self.binding.version,
                "scope": session.scope.as_dict(),
                "item_id": actual.item_id,
                "generation": actual.execution_generation,
                "upload_reference": actual.upload_reference,
                "submission_reference": actual.submission_reference,
                "sha256": actual.sha256,
                "geometry": {name: str(getattr(actual.geometry, name)) for name in ("x_mm", "y_mm", "z_mm", "volume_mm3")},
                "effective": dict(actual.effective.values),
                "freshness": actual.freshness.value,
                "observed_at": actual.observed_at.isoformat(),
                "priced_at": result.priced_at.isoformat() if result.priced_at is not None else None,
            }
            if self.batch_claim:
                # Preserve the already observed quote before attempting the
                # atomic result/Run/item commit; recovery may only retry locally.
                await self.repository.stage_shortcut_result(candidate, evidence)
                self.pending_result = True
            await self.repository.save(candidate, evidence=evidence)
            self.view = candidate
            self.pending_result = False

    def _provisional_result(self, outcome: ProvisionalQuote, session):
        quote = outcome.observation
        session.check_active()
        if not outcome.current_verified or not outcome.evidence_code or outcome.status not in {"REFERENCE_ESTIMATE", "PENDING_REVIEW"}:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if self.upload is None or self.submitted is None:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.scope != session.scope or quote.item_id != self.activity_id or quote.execution_generation != "1":
            raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.sha256 != self.upload.sha256 or quote.upload_reference != self.upload.reference or quote.submission_reference != self.submitted.reference:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.effective != self.snapshot.requested or quote.geometry != self.upload.geometry:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if not isinstance(quote.freshness, QuoteFreshness) or quote.freshness not in {QuoteFreshness.RECALCULATED, QuoteFreshness.CURRENT_CONFIRMED}:
            raise BrowserStop(Reason.QUOTE_INVALID)
        quote.geometry.validate()
        now = datetime.now(UTC)
        if any(not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None for value in (quote.observed_at, quote.priced_at)):
            raise BrowserStop(Reason.QUOTE_INVALID)
        if not self.started_at <= quote.observed_at <= now or (now - quote.observed_at).total_seconds() > 300:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if not now - timedelta(seconds=300) <= quote.priced_at <= quote.observed_at + timedelta(seconds=5):
            raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.freshness == QuoteFreshness.RECALCULATED and quote.priced_at < self.started_at:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if outcome.platform_priced_at is not None:
            value = outcome.platform_priced_at
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None or not now - timedelta(seconds=300) <= value <= quote.observed_at + timedelta(seconds=5):
                raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.amount is not None and (not isinstance(quote.amount, Decimal) or not quote.amount.is_finite() or quote.amount <= 0):
            raise BrowserStop(Reason.QUOTE_INVALID)
        if outcome.status == "REFERENCE_ESTIMATE" and quote.amount is None:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.currency is not None and quote.currency not in KNOWN_CURRENCIES:
            raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.price_scope is not None and not isinstance(quote.price_scope, PriceScope):
            raise BrowserStop(Reason.QUOTE_INVALID)
        if quote.lead_time is not None:
            quote.lead_time.validate()
        return QuoteResult(
            status=outcome.status,
            amount=str(quote.amount) if quote.amount is not None else None,
            currency=quote.currency,
            price_scope=quote.price_scope.value if quote.price_scope is not None else None,
            lead_time=quote.lead_time.as_dict() if quote.lead_time is not None else None,
            effective=dict(quote.effective.values),
            priced_at=outcome.platform_priced_at,
            observed_at=quote.observed_at,
            freshness=quote.freshness.value,
        )

    async def finish(self, reason: str):
        try:
            # A remote observation can be staged immediately before a close
            # interrupts its caller. Preserve it before settling cancellation.
            if (reason == "SESSION_CLOSED" or self.pending_result) and not self.terminal:
                pending = await self.repository.persist_pending_result(self.view.run_id)
                if pending is not None:
                    self.view = pending
            if not self.terminal:
                status = "CANCELLED" if reason == "SESSION_CLOSED" else "FAILED"
                await self.change(status, self.view.stage, "QUOTE_CANCELLED" if status == "CANCELLED" else reason)
        finally:
            # Terminal HTTP views may outlive their browser; retain no plaintext
            # password, encrypted browser state or uploaded file buffer there.
            self.snapshot = replace(self.snapshot, account=replace(self.snapshot.account, password="", encrypted_state=None), payload=StepPayload(b"", self.snapshot.payload.sha256))
            self.binding = None
