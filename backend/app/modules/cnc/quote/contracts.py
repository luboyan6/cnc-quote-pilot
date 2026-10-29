"""Public quote DTOs never contain paths, browser state or remote references."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.cnc.browser.contracts import DeclarationReceipt, Parameters
from app.modules.cnc.browser.contracts import ProvisionalQuote as ProvisionalQuote
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


class InstantQuote(BaseModel):
    """列表「自动报价」按钮的入参。

    ``export_controlled`` 必须由调用方显式给出，服务端不做推断：
    出口管制声明只能由人按图纸决定。
    """

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    account_id: int = Field(ge=1, strict=True)
    export_controlled: bool | None = None
    quantity_override: int | None = Field(None, ge=1, le=100000, strict=True)
    quote_id: str | None = Field(None, max_length=32)
    tolerance: str | None = Field(None, max_length=120)
    roughness: str | None = Field(None, max_length=120)


ExportChoice = Literal["not_controlled", "controlled"]


class ExportDeclarationOption(BaseModel):
    value: ExportChoice
    label: str = Field(min_length=1, max_length=4000)


class ExportDeclaration(BaseModel):
    """The current displayed declaration, never HTML, credentials or a locator."""

    declaration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    statement: str = Field(min_length=1, max_length=16000)
    options: list[ExportDeclarationOption] = Field(min_length=2, max_length=2)


class ExportDeclarationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    declaration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    choice: ExportChoice


@runtime_checkable
class ExportDeclarationAdapter(Protocol):
    async def read_export_declaration(self, session) -> ExportDeclaration | None: ...
    async def continue_declaration(self, session, declaration: ExportDeclaration, choice: str) -> DeclarationReceipt: ...
    def can_reauthenticate(self, session) -> bool: ...


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
    tax_amount: str | None = None
    total_amount: str | None = None
    discount_amount: str | None = None
    lead_time_tiers: list[dict[str, Any]] | None = None


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
    export_declaration: ExportDeclaration | None = None


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
