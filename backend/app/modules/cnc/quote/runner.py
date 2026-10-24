"""One bounded step at a time, called ONLY by the existing browser owner task."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import monotonic

from app.modules.cnc.browser.contracts import (
    Authentication,
    AuthStatus,
    ConfigurationReceipt,
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

from .contracts import TERMINAL, ProvisionalQuote, QuoteError, QuoteResult
from .providers import resolve_quote_adapter
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
        self.binding = None
        self.upload = None
        self.submitted = None
        self.started_at = datetime.now(UTC)
        self.begun = False
        self.parse_observations = 0
        self.parse_deadline = 0.0
        self.next_step_at = 0.0
        self.phase_deadline = 0.0

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

    async def change(self, status, stage, reason):
        candidate = self.view.model_copy(update={"status": status, "stage": stage, "reason": reason, "can_input": status == "WAITING_HUMAN"})
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
        await self.repository.assert_active(self.snapshot.account.actor_id, self.activity_id)

    async def resume(self, session, provider):
        await self.check_inputs()
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
                        await self.change("WAITING_HUMAN", "parse", manual_reason)
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
                    await self.change("WAITING_HUMAN" if manual_reason else "RUNNING", "parse", manual_reason or "AWAITING_MODEL_PARSE")
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
            await self.workflow._mutation(key(Operation.CONFIGURE), session, adapter, configure, sha256, requested, upload)
            await self.change("RUNNING", "quote", "FETCHING_QUOTE")
        elif self.submitted is None:
            effective = await adapter.read_effective(session, self.upload)
            if effective != requested:
                raise BrowserStop(Reason.PARAMETERS_MISMATCH)
            await self.check_inputs()
            receipt = await self.workflow._mutation(key(Operation.SUBMIT), session, adapter, lambda: adapter.submit(session, self.upload, requested), sha256, requested, self.upload)
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
            await self.repository.save(candidate, evidence=evidence)
            self.view = candidate

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
            status=outcome.status, amount=str(quote.amount) if quote.amount is not None else None,
            currency=quote.currency, price_scope=quote.price_scope.value if quote.price_scope is not None else None,
            lead_time=quote.lead_time.as_dict() if quote.lead_time is not None else None,
            effective=dict(quote.effective.values), priced_at=outcome.platform_priced_at, observed_at=quote.observed_at,
            freshness=quote.freshness.value,
        )

    async def finish(self, reason: str):
        try:
            if not self.terminal:
                status = "CANCELLED" if reason == "SESSION_CLOSED" else "FAILED"
                await self.change(status, self.view.stage, "QUOTE_CANCELLED" if status == "CANCELLED" else reason)
        finally:
            # Terminal HTTP views may outlive their browser; retain no plaintext
            # password, encrypted browser state or uploaded file buffer there.
            self.snapshot = replace(self.snapshot, account=replace(self.snapshot.account, password="", encrypted_state=None), payload=StepPayload(b"", self.snapshot.payload.sha256))
            self.binding = None
