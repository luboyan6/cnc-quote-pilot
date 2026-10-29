"""Workflow owns sequence; adapters own verified platform details, never agents."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .contracts import (
    ConfigurationReceipt,
    DeclarationReceipt,
    IntentKey,
    IntentState,
    IntentStore,
    LeadTime,
    MutationReceipt,
    Operation,
    Parameters,
    PlatformAdapter,
    PriceScope,
    QuoteFreshness,
    QuoteObservation,
    SubmissionReceipt,
    UploadReceipt,
    ValidatedQuote,
    item_fingerprint,
    require_identity,
)
from .errors import BrowserStop, Reason
from .files import TrustedStep
from .session import BrowserSession, finish_cleanup

KNOWN_CURRENCIES = frozenset({"USD", "EUR", "CNY", "GBP", "JPY", "CAD", "AUD", "CHF", "HKD", "SGD"})


@dataclass(frozen=True)
class QuoteRequest:
    item_id: str
    execution_generation: str
    step: TrustedStep
    requested: Parameters

    def __post_init__(self) -> None:
        require_identity(self.item_id)
        require_identity(self.execution_generation)


def _is_timeout(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, BrowserStop):
        return exc.reason == Reason.READ_TIMEOUT
    # The SDK remains optional on import. Detect only its official timeout type.
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    except ImportError:
        return False
    return isinstance(exc, PlaywrightTimeoutError)


async def read_with_retry[T](action: Callable[[], Awaitable[T]], *, retries: int = 2, timeout_seconds: float = 15) -> T:
    """Only call with reviewed read-only actions; mutations never use this helper."""
    if type(retries) is not int or not 0 <= retries <= 2 or not 0 < timeout_seconds <= 60:
        raise BrowserStop(Reason.INVALID_INPUT)
    for attempt in range(retries + 1):
        try:
            async with asyncio.timeout(timeout_seconds):
                return await action()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if _is_timeout(exc):
                if attempt == retries:
                    raise BrowserStop(Reason.READ_TIMEOUT) from None
            elif isinstance(exc, BrowserStop):
                raise BrowserStop(exc.reason) from None
            else:
                raise BrowserStop(Reason.PAGE_UNKNOWN) from None
    raise BrowserStop(Reason.READ_TIMEOUT)


class QuoteWorkflow:
    """No default store: a fixture store is never production recovery/persistence."""

    def __init__(self, intents: IntentStore, *, read_retries: int = 2, read_timeout_seconds: float = 15, quote_max_age_seconds: int = 300) -> None:
        if intents is None or type(read_retries) is not int or not 0 <= read_retries <= 2:
            raise BrowserStop(Reason.INVALID_INPUT)
        if not 0 < read_timeout_seconds <= 60 or type(quote_max_age_seconds) is not int or not 0 < quote_max_age_seconds <= 600:
            raise BrowserStop(Reason.INVALID_INPUT)
        self._intents = intents
        self._read_retries = read_retries
        self._read_timeout = read_timeout_seconds
        self._max_age = quote_max_age_seconds

    async def _read[T](self, action: Callable[[], Awaitable[T]], session: BrowserSession) -> T:
        session.check_active()
        result = await read_with_retry(action, retries=self._read_retries, timeout_seconds=self._read_timeout)
        session.check_active()
        return result

    @staticmethod
    def _check_receipt(receipt: MutationReceipt, key: IntentKey, sha256: str, params: Parameters, upload: UploadReceipt | None) -> None:
        if key.operation == Operation.UPLOAD and isinstance(receipt, UploadReceipt):
            require_identity(receipt.reference)
            if receipt.sha256 != sha256:
                raise BrowserStop(Reason.FILE_INVALID)
            receipt.geometry.validate()
        elif key.operation == Operation.CONFIGURE and isinstance(receipt, ConfigurationReceipt):
            if receipt.effective != params:
                raise BrowserStop(Reason.PARAMETERS_MISMATCH)
        elif key.operation == Operation.SUBMIT and isinstance(receipt, SubmissionReceipt) and upload is not None:
            require_identity(receipt.reference)
            if receipt.upload_reference != upload.reference or receipt.effective != params:
                raise BrowserStop(Reason.PARAMETERS_MISMATCH)
        elif key.operation == Operation.DECLARATION and isinstance(receipt, DeclarationReceipt):
            require_identity(receipt.declaration_id)
            require_identity(receipt.upload_reference)
            if receipt.sha256 != sha256 or receipt.choice not in {"not_controlled", "controlled"}:
                raise BrowserStop(Reason.MUTATION_UNCERTAIN)
        else:
            raise BrowserStop(Reason.MUTATION_UNCERTAIN)

    async def _mark_uncertain(self, key: IntentKey) -> None:
        try:
            async with asyncio.timeout(5):
                await self._intents.mark_uncertain(key)
        except BaseException:
            # The pre-existing durable CLAIMED record also forbids replay.
            # Never clear/release a claim to retry because this update failed.
            pass

    async def _mutation(
        self,
        key: IntentKey,
        session: BrowserSession,
        adapter: PlatformAdapter,
        action: Callable[[], Awaitable[MutationReceipt]],
        sha256: str,
        params: Parameters,
        upload: UploadReceipt | None = None,
    ) -> MutationReceipt:
        session.check_active()
        try:
            claim = await self._intents.claim(key)
        except BrowserStop as exc:
            raise BrowserStop(Reason.INTENT_CONFLICT if exc.reason == Reason.INTENT_CONFLICT else Reason.STATE_UNAVAILABLE) from None
        except Exception:
            raise BrowserStop(Reason.STATE_UNAVAILABLE) from None
        if claim.record.key != key:
            raise BrowserStop(Reason.INTENT_CONFLICT)
        if not claim.is_new:
            receipt = claim.record.receipt if claim.record.state == IntentState.CONFIRMED else None
            if receipt is None:
                receipt = await self._read(lambda: adapter.reconcile(session, key), session)
                if receipt is None:
                    raise BrowserStop(Reason.MUTATION_UNCERTAIN)
                self._check_receipt(receipt, key, sha256, params, upload)
                try:
                    await self._intents.confirm(key, receipt)
                except Exception:
                    raise BrowserStop(Reason.STATE_UNAVAILABLE) from None
            self._check_receipt(receipt, key, sha256, params, upload)
            return receipt
        if claim.record.state != IntentState.CLAIMED or claim.record.receipt is not None:
            raise BrowserStop(Reason.INTENT_CONFLICT)
        try:
            session.check_active()
            receipt = await action()  # Exactly one attempt, including Apply/save.
            session.check_active()
            self._check_receipt(receipt, key, sha256, params, upload)
            await self._intents.confirm(key, receipt)
            return receipt
        except BaseException as exc:
            _, cancelled = await finish_cleanup(self._mark_uncertain(key))
            if isinstance(exc, asyncio.CancelledError) or cancelled:
                raise asyncio.CancelledError() from None
            if isinstance(exc, BrowserStop):
                raise BrowserStop(exc.reason) from None
            raise BrowserStop(Reason.MUTATION_UNCERTAIN) from None

    async def execute(self, session: BrowserSession, adapter: PlatformAdapter, request: QuoteRequest) -> ValidatedQuote:
        """Small integration helper, not the product S01-S11 runner or agent factory."""
        started_at = datetime.now(UTC)
        session.check_active()
        session.invalidate_authentication()
        auth = await self._read(lambda: adapter.authenticate(session), session)
        session.confirm_authentication(auth)  # Challenge/expiry/wrong identity before upload.
        payload = request.step.read_verified()
        fingerprint = item_fingerprint(payload.sha256, request.requested)

        def key(operation: Operation) -> IntentKey:
            return IntentKey(session.scope, request.item_id, request.execution_generation, operation, fingerprint)

        upload = await self._mutation(key(Operation.UPLOAD), session, adapter, lambda: adapter.upload(session, payload), payload.sha256, request.requested)
        if not isinstance(upload, UploadReceipt):
            raise BrowserStop(Reason.MUTATION_UNCERTAIN)

        async def configure() -> ConfigurationReceipt:
            await adapter.configure(session, upload, request.requested)
            effective = await self._read(lambda: adapter.read_effective(session, upload), session)
            return ConfigurationReceipt(effective)

        await self._mutation(key(Operation.CONFIGURE), session, adapter, configure, payload.sha256, request.requested, upload)
        # Re-read even when configuration intent was already confirmed, as remote
        # values may have changed since then. Never silently re-Apply on mismatch.
        effective = await self._read(lambda: adapter.read_effective(session, upload), session)
        if effective != request.requested:
            raise BrowserStop(Reason.PARAMETERS_MISMATCH)
        submitted = await self._mutation(key(Operation.SUBMIT), session, adapter, lambda: adapter.submit(session, upload, request.requested), payload.sha256, request.requested, upload)
        if not isinstance(submitted, SubmissionReceipt):
            raise BrowserStop(Reason.MUTATION_UNCERTAIN)
        quote = await self._read(lambda: adapter.extract_quote(session, upload, submitted), session)
        if not isinstance(quote, QuoteObservation):
            # This utility returns final quotes only. The application runner
            # persists explicitly provisional results through its separate path.
            raise BrowserStop(Reason.QUOTE_INVALID)
        return validate_quote(quote, session, request, upload, submitted, started_at, max_age_seconds=self._max_age)


def validate_quote(
    quote: QuoteObservation,
    session: BrowserSession,
    request: QuoteRequest,
    upload: UploadReceipt,
    submitted: SubmissionReceipt,
    started_at: datetime,
    *,
    max_age_seconds: int = 300,
) -> ValidatedQuote:
    """Reject ambiguity. An uploaded row/catalog price is not a reliable quote."""
    session.check_active()
    if quote.scope != session.scope or quote.item_id != request.item_id or quote.execution_generation != request.execution_generation:
        raise BrowserStop(Reason.QUOTE_INVALID)
    if quote.upload_reference != upload.reference or quote.submission_reference != submitted.reference or quote.sha256 != upload.sha256:
        raise BrowserStop(Reason.QUOTE_INVALID)
    if quote.effective != request.requested or submitted.effective != request.requested:
        raise BrowserStop(Reason.PARAMETERS_MISMATCH)
    quote.geometry.validate()
    if quote.geometry != upload.geometry:
        raise BrowserStop(Reason.GEOMETRY_INVALID)
    if not isinstance(quote.amount, Decimal) or not quote.amount.is_finite() or quote.amount <= 0:
        raise BrowserStop(Reason.QUOTE_INVALID)
    if quote.currency not in KNOWN_CURRENCIES or not isinstance(quote.price_scope, PriceScope):
        raise BrowserStop(Reason.QUOTE_INVALID)
    lead = quote.lead_time
    if not isinstance(lead, LeadTime):
        raise BrowserStop(Reason.QUOTE_INVALID)
    lead.validate()
    now = datetime.now(UTC)
    if any(not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None for v in (quote.priced_at, quote.observed_at)):
        raise BrowserStop(Reason.QUOTE_INVALID)
    if not started_at <= quote.observed_at <= now + timedelta(seconds=5):
        raise BrowserStop(Reason.QUOTE_INVALID)
    if not now - timedelta(seconds=max_age_seconds) <= quote.priced_at <= quote.observed_at + timedelta(seconds=5):
        raise BrowserStop(Reason.QUOTE_INVALID)
    if not isinstance(quote.freshness, QuoteFreshness) or quote.freshness not in {QuoteFreshness.RECALCULATED, QuoteFreshness.CURRENT_CONFIRMED}:
        raise BrowserStop(Reason.QUOTE_INVALID)
    if quote.freshness == QuoteFreshness.RECALCULATED and quote.priced_at < started_at:
        raise BrowserStop(Reason.QUOTE_INVALID)
    return ValidatedQuote(quote)
