"""Public quote DTOs never contain paths, browser state or remote references."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.cnc.browser.contracts import Parameters, QuoteObservation
from app.modules.cnc.browser.files import StepPayload, TrustedStep
from app.modules.cnc.login.contracts import AccountSnapshot, LoginError

QuoteStatus = Literal["STARTING", "AUTHENTICATING", "RUNNING", "WAITING_HUMAN", "QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW", "FAILED", "CANCELLED"]
TERMINAL = frozenset({"QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW", "FAILED", "CANCELLED"})


class QuoteError(LoginError):
    """A fixed reason safe for the private API and owner task."""


class StartQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    account_id: int | None = Field(None, ge=1, strict=True)
    request_id: UUID


class QuoteAccount(BaseModel):
    id: int
    alias: str
    masked_username: str


class QuoteResult(BaseModel):
    status: Literal["QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW"]
    amount: str | None = None
    currency: str | None = None
    price_scope: Literal["unit", "line"] | None = None
    lead_time: dict[str, Any] | None = None
    effective: dict[str, str]
    priced_at: datetime | None = None
    observed_at: datetime
    tax_included: bool | None = None
    shipping_included: bool | None = None
    freshness: str | None = None


class QuoteRunView(BaseModel):
    run_id: str
    config_id: int
    account_id: int
    platform_name: str
    masked_username: str
    file_name: str
    status: QuoteStatus
    stage: str
    reason: str
    can_input: bool = False
    requested: dict[str, str]
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 720})
    expires_at: datetime
    result: QuoteResult | None = None


@dataclass(frozen=True, repr=False)
class ProvisionalQuote:
    """Provider-confirmed estimate/review, never accepted by validate_quote.

    The trusted adapter must carry the same run/file/parameters and explicit
    current-page status evidence; a missing price cannot imply review status.
    """

    status: Literal["REFERENCE_ESTIMATE", "PENDING_REVIEW"]
    observation: QuoteObservation
    evidence_code: str
    current_verified: bool
    platform_priced_at: datetime | None = None


@dataclass(frozen=True, repr=False)
class QuoteSnapshot:
    config_id: int
    part_id: int
    account: AccountSnapshot
    config_revision: str
    file_name: str
    step: TrustedStep
    payload: StepPayload = field(repr=False)
    requested: Parameters
    provider_code: str

    @property
    def frozen(self) -> dict[str, Any]:
        return {
            "config_revision": self.config_revision,
            "account_revision": self.account.revision,
            "sha256": self.payload.sha256,
            "size": len(self.payload.buffer),
            "requested": dict(self.requested.values),
            "provider_code": self.provider_code,
            "contract_version": "config-quote-v1",
        }
