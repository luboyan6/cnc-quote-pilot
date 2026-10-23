"""Pure domain contracts. Platform adapters, ACL and durable stores are injected."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from .errors import BrowserStop, Reason
from .lead_time import DayBasis as DayBasis
from .lead_time import LeadTime as LeadTime
from .lead_time import LeadTimeDate as LeadTimeDate
from .lead_time import LeadTimeKind as LeadTimeKind

if TYPE_CHECKING:
    from .files import StepPayload
    from .session import BrowserSession


def require_identity(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 200 or any(ord(char) < 32 for char in value):
        raise BrowserStop(Reason.INVALID_INPUT)


@dataclass(frozen=True, repr=False)
class SessionScope:
    """Server-resolved account ownership, never constructed from model/page text."""

    owner_id: str
    platform_code: str
    account_id: str

    def __post_init__(self) -> None:
        for value in (self.owner_id, self.platform_code, self.account_id):
            require_identity(value)

    def as_dict(self) -> dict[str, str]:
        return {"owner_id": self.owner_id, "platform_code": self.platform_code, "account_id": self.account_id}


@dataclass(frozen=True)
class Parameters:
    """Full effective values in explicit platform units; no fuzzy matching/defaults."""

    values: tuple[tuple[str, str], ...] = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.values, tuple) or not self.values:
            raise BrowserStop(Reason.INVALID_INPUT)
        for pair in self.values:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise BrowserStop(Reason.INVALID_INPUT)
            for value in pair:
                require_identity(value)
        if len(dict(self.values)) != len(self.values):
            raise BrowserStop(Reason.INVALID_INPUT)
        object.__setattr__(self, "values", tuple(sorted(self.values)))

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "Parameters":
        return cls(tuple(values.items()))


class AuthStatus(StrEnum):
    AUTHENTICATED = "authenticated"
    EXPIRED = "expired"
    CHALLENGE = "challenge"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Authentication:
    status: AuthStatus
    scope: SessionScope | None = field(default=None, repr=False)


@dataclass(frozen=True)
class Geometry:
    x_mm: Decimal
    y_mm: Decimal
    z_mm: Decimal
    volume_mm3: Decimal

    def validate(self) -> None:
        if any(not isinstance(v, Decimal) or not v.is_finite() or v <= 0 for v in (self.x_mm, self.y_mm, self.z_mm, self.volume_mm3)):
            raise BrowserStop(Reason.GEOMETRY_INVALID)


@dataclass(frozen=True)
class UploadReceipt:
    reference: str = field(repr=False)
    sha256: str
    geometry: Geometry


@dataclass(frozen=True)
class ConfigurationReceipt:
    effective: Parameters


@dataclass(frozen=True)
class SubmissionReceipt:
    reference: str = field(repr=False)
    upload_reference: str = field(repr=False)
    effective: Parameters


class Operation(StrEnum):
    UPLOAD = "upload"
    CONFIGURE = "configure"
    SUBMIT = "submit"


class IntentState(StrEnum):
    CLAIMED = "claimed"
    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"


MutationReceipt = UploadReceipt | ConfigurationReceipt | SubmissionReceipt


@dataclass(frozen=True)
class IntentKey:
    scope: SessionScope = field(repr=False)
    item_id: str = field(repr=False)
    execution_generation: str = field(repr=False)
    operation: Operation
    fingerprint: str

    @property
    def identity(self) -> tuple[SessionScope, str, str, Operation]:
        """The DB uniqueness key EXCLUDES fingerprint; changed inputs must conflict."""
        return self.scope, self.item_id, self.execution_generation, self.operation


@dataclass(frozen=True)
class IntentRecord:
    key: IntentKey
    state: IntentState
    receipt: MutationReceipt | None = None


@dataclass(frozen=True)
class IntentClaim:
    is_new: bool
    record: IntentRecord


class IntentStore(Protocol):
    """Required production port: atomic, durable and scoped by server-owned ACL.

    claim commits BEFORE returning is_new=True. A unique key on key.identity
    returns prior CLAIMED/UNCERTAIN/CONFIRMED instead of granting replay. Also
    freeze fingerprint by (scope, item_id), across operations and generations;
    changed bytes/parameters require a NEW item. Claimed already means uncertain
    after a crash. confirm/mark_uncertain must not erase a confirmed receipt or
    another claim. No default in-memory implementation is supplied.
    """

    async def claim(self, key: IntentKey) -> IntentClaim: ...
    async def confirm(self, key: IntentKey, receipt: MutationReceipt) -> None: ...
    async def mark_uncertain(self, key: IntentKey) -> None: ...


class PriceScope(StrEnum):
    UNIT = "unit"
    LINE = "line"


class QuoteFreshness(StrEnum):
    RECALCULATED = "RECALCULATED"
    CURRENT_CONFIRMED = "CURRENT_CONFIRMED"
    CACHE_UNVERIFIED = "CACHE_UNVERIFIED"


@dataclass(frozen=True)
class QuoteObservation:
    scope: SessionScope = field(repr=False)
    item_id: str = field(repr=False)
    execution_generation: str = field(repr=False)
    upload_reference: str = field(repr=False)
    submission_reference: str = field(repr=False)
    sha256: str
    effective: Parameters
    geometry: Geometry
    amount: Decimal | None
    currency: str | None
    price_scope: PriceScope | None
    lead_time: LeadTime | None
    freshness: QuoteFreshness
    priced_at: datetime
    observed_at: datetime


@dataclass(frozen=True)
class ValidatedQuote:
    """Only the validator constructs successful results; exact decimal serialization."""

    observation: QuoteObservation = field(repr=False)

    def as_dict(self) -> dict:
        quote = self.observation
        lead = quote.lead_time
        scope = quote.price_scope
        if lead is None or scope is None or quote.amount is None:
            raise BrowserStop(Reason.QUOTE_INVALID)
        return {
            "status": "QUOTED",
            "amount": str(quote.amount),
            "currency": quote.currency,
            "price_scope": scope.value,
            "freshness": quote.freshness.value,
            "lead_time": lead.as_dict(),
            "effective": dict(quote.effective.values),
            "priced_at": quote.priced_at.isoformat(),
            "observed_at": quote.observed_at.isoformat(),
        }


def item_fingerprint(sha256: str, parameters: Parameters) -> str:
    frozen = json.dumps({"sha256": sha256, "parameters": parameters.values}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(frozen.encode()).hexdigest()


class PlatformAdapter(Protocol):
    """Trusted deterministic code, never an agent or an untrusted config executor.

    Authentication/extraction/read_effective/reconcile MUST be read-only.
    Upload uses the verified StepPayload buffer via official SDK helpers.
    Configure is guarded too because Apply/save can mutate remote state.
    CURRENT_CONFIRMED freshness requires explicit current same-request remote
    evidence, not merely a recent timestamp, catalog entry or cached price.
    No order/payment methods, raw JS/model tools, or generic click interface.
    """

    async def authenticate(self, session: "BrowserSession") -> Authentication: ...
    async def upload(self, session: "BrowserSession", payload: "StepPayload") -> UploadReceipt: ...
    async def configure(self, session: "BrowserSession", upload: UploadReceipt, requested: Parameters) -> None: ...
    async def read_effective(self, session: "BrowserSession", upload: UploadReceipt) -> Parameters: ...
    async def submit(self, session: "BrowserSession", upload: UploadReceipt, requested: Parameters) -> SubmissionReceipt: ...
    async def extract_quote(self, session: "BrowserSession", upload: UploadReceipt, submission: SubmissionReceipt) -> QuoteObservation: ...
    async def reconcile(self, session: "BrowserSession", key: IntentKey) -> MutationReceipt | None: ...
