"""Xometry quote-only methods on the existing guarded, single-owner Page.

The DOM binding is reviewed engineering input, never platform JSON, request
data, a model-produced locator or a public-testdrive fallback. No production
binding is supplied until managed upload/readback/result evidence is available.
"""

import hashlib
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from app.modules.cnc.browser.contracts import (
    Authentication,
    AuthStatus,
    DeclarationReceipt,
    Geometry,
    IntentKey,
    LeadTime,
    Operation,
    Parameters,
    PriceScope,
    QuoteFreshness,
    QuoteObservation,
    SubmissionReceipt,
    UploadReceipt,
    require_identity,
)
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import StepPayload, upload_step
from app.modules.cnc.browser.lead_time import DayBasis, LeadTimeDate, LeadTimeKind
from app.modules.cnc.browser.workflow import KNOWN_CURRENCIES
from app.modules.cnc.login.providers import resolve_provider

from .contracts import ExportDeclaration, ExportDeclarationOption, ProvisionalQuote, QuoteError, QuoteSnapshot


@dataclass(frozen=True)
class DOMValue:
    """One uniquely observed value, with an explicitly reviewed representation."""

    selector: str
    attribute: str | None = None
    prefix: str = ""


@dataclass(frozen=True)
class ParameterControl:
    key: str
    control: str
    saved: DOMValue
    mode: Literal["input", "select", "options"]
    options: str | None = None
    option_title: str | None = None
    # Explicit source-reviewed aliases only. Exact option titles remain distinct.
    values: tuple[tuple[str, str], ...] = ()
    search: str | None = None


@dataclass(frozen=True)
class XometryDOMBinding:
    """All fields need current managed-route evidence before registration.

    This is deliberately not populated from old candidate selectors. Tests can
    supply synthetic DOM bindings without making them production registration.
    File/part fields are relative to the single newly created part row; quote
    fields are relative to its quote root. Dimensions must explicitly be mm and
    volume mm3 in the reviewed source. No inferred units/currency or JS readers.
    """

    version: str
    evidence: str
    max_size: int
    entry_paths: tuple[str, ...]
    primary_input: str
    part_rows: str
    part_id: DOMValue
    file_id: DOMValue
    file_name: DOMValue
    file_size: DOMValue
    geometry: tuple[DOMValue, DOMValue, DOMValue, DOMValue]
    process: DOMValue
    parameters: tuple[ParameterControl, ...]
    save_button: str
    declaration_root: str
    declaration_statement: DOMValue
    declaration_no: str
    declaration_yes: str
    declaration_continue: str
    quote_root: str
    quote_id: DOMValue
    quote_part_id: DOMValue
    quote_revision: DOMValue
    quote_priced_at: DOMValue
    quote_quantity: DOMValue
    quote_status: DOMValue
    quote_amount: DOMValue
    quote_currency: DOMValue
    quote_scope: DOMValue
    quote_lead: DOMValue
    # Map exact observed provider labels, not substrings or guessed defaults.
    statuses: tuple[tuple[str, Literal["QUOTED", "REFERENCE_ESTIMATE", "PENDING_REVIEW"]], ...]
    scopes: tuple[tuple[str, Literal["unit", "line"]], ...]
    lead_kind: LeadTimeKind = LeadTimeKind.DURATION
    lead_date: DOMValue | None = None
    lead_start: str | None = None
    # The deployed V2 experiment is distinct from the public test drive. Only
    # a source-reviewed binding may opt into its exact query representation.
    part_config_variant: Literal["legacy", "v2"] = "legacy"

    def __post_init__(self):
        if not self.version or not self.evidence or type(self.max_size) is not int or self.max_size <= 0:
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        if not self.entry_paths or any(not path.startswith("/quoting/") or "testdrive" in path for path in self.entry_paths):
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        if self.part_config_variant not in {"legacy", "v2"}:
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        keys = [control.key for control in self.parameters]
        if len(set(keys)) != len(keys) or not {"material", "quantity"}.issubset(keys):
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        if not self.statuses or not self.scopes or len(dict(self.statuses)) != len(self.statuses) or len(dict(self.scopes)) != len(self.scopes):
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")


async def _unique(locator, *, visible=True):
    if await locator.count() != 1 or (visible and not await locator.is_visible()):
        raise QuoteError("XOMETRY_PAGE_UNSUPPORTED")
    return locator


async def _value(root, field: DOMValue) -> str:
    locator = await _unique(root.locator(field.selector))
    if field.attribute == "value":
        raw = await locator.input_value(timeout=2000)
    elif field.attribute:
        raw = await locator.get_attribute(field.attribute, timeout=2000)
    else:
        raw = await locator.inner_text(timeout=2000)
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 16000:
        raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
    raw = raw.strip()
    if field.prefix:
        if not raw.startswith(field.prefix):
            raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
        raw = raw.removeprefix(field.prefix).strip()
    return raw


def _decimal(value: str) -> Decimal:
    # Locale/units/currency are binding evidence, never guessed from punctuation.
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) is None:
        raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING") from None
    if not result.is_finite() or result <= 0:
        raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
    return result


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
    return result


class XometryQuoteAdapter:
    """Concrete quote methods; the runner owns persistence and mutation claims."""

    def __init__(self, snapshot: QuoteSnapshot, run_id: str, binding: XometryDOMBinding):
        if snapshot.provider_code != "xometry_us":
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        self.snapshot = snapshot
        self.run_id = run_id
        self.binding = binding
        self.manual_reason: str | None = None
        self.export_declaration: ExportDeclaration | None = None
        self._upload_attempted = False
        self._upload: UploadReceipt | None = None
        self._part_id: str | None = None
        self._save_attempted = False
        self._before_revision: str | None = None
        self._saved_revision: str | None = None
        self._saved_at: datetime | None = None
        self._submission: SubmissionReceipt | None = None
        self._declaration_attempt: tuple[str, str] | None = None
        self._input_guard: Callable[[], Awaitable[None]] | None = None

    def set_input_guard(self, guard: Callable[[], Awaitable[None]]) -> None:
        """Bind the owning activity's current authorization/input revalidation."""
        if self._input_guard is not None:
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        self._input_guard = guard

    async def _guard_mutation(self, session) -> None:
        if self._input_guard is None:
            raise QuoteError("XOMETRY_BINDING_UNVERIFIED")
        await self._input_guard()
        self.inspect_page(session)

    def inspect_page(self, session):
        session.check_active()
        parsed = urlsplit(session.page.url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        variant = query.get("vercel_part_config")
        provider = resolve_provider(self.snapshot.account.login_url, self.snapshot.account.quote_url)
        if (
            session.scope.platform_code != "xometry_us"
            or parsed.scheme != "https"
            or parsed.hostname not in provider.entry_hosts
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
            or (variant is not None and (self.binding.part_config_variant != "v2" or variant != ["test"]))
            or not any(parsed.path.startswith(path) for path in self.binding.entry_paths)
            or "testdrive" in parsed.path.lower()
        ):
            raise QuoteError("XOMETRY_PAGE_UNSUPPORTED")
        return session.page

    async def authenticate(self, session) -> Authentication:
        self.inspect_page(session)
        provider = resolve_provider(self.snapshot.account.login_url, self.snapshot.account.quote_url)
        matched = await provider.verify(session, self.snapshot.account.username)
        return Authentication(AuthStatus.AUTHENTICATED if matched else AuthStatus.UNKNOWN, session.scope if matched else None)

    def can_reauthenticate(self, session) -> bool:
        # Only the provider's already observed hosted login surface may accept
        # coordinates while a declaration is pending. Never enable generic
        # clicks over the declaration itself or navigate away to obtain login.
        session.check_active()
        parsed = urlsplit(session.page.url)
        return parsed.scheme == "https" and parsed.hostname == "login.xometry.com" and parsed.port in {None, 443} and not parsed.username and not parsed.password

    def validate_parameters(self, requested: Parameters) -> None:
        controls = {control.key: control for control in self.binding.parameters}
        for key, value in requested.values:
            control = controls.get(key)
            if control is None:
                raise QuoteError("XOMETRY_PARAMETER_UNSUPPORTED")
            if control.values and value not in dict(control.values):
                raise QuoteError("XOMETRY_PARAMETER_UNSUPPORTED")
            if key == "quantity" and (re.fullmatch(r"[1-9][0-9]*", value) is None):
                raise QuoteError("XOMETRY_PARAMETER_UNSUPPORTED")
            if control.mode == "options" and (not control.options or not control.option_title):
                raise QuoteError("XOMETRY_BINDING_UNVERIFIED")

    async def upload(self, session, payload: StepPayload) -> UploadReceipt:
        page = self.inspect_page(session)
        self.validate_parameters(self.snapshot.requested)
        if self._upload_attempted:
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        if payload != self.snapshot.payload or hashlib.sha256(payload.buffer).hexdigest() != payload.sha256 or len(payload.buffer) > self.binding.max_size:
            raise BrowserStop(Reason.FILE_INVALID)
        # A new upload cannot attach itself to an unrelated staged/history part.
        if await page.locator(self.binding.part_rows).count() != 0:
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        control = await _unique(page.locator(self.binding.primary_input), visible=False)
        if await control.get_attribute("type") != "file":
            raise QuoteError("XOMETRY_PAGE_UNSUPPORTED")
        await self._guard_mutation(session)
        self._upload_attempted = True  # Set before awaiting the one SDK mutation.
        await upload_step(control, payload)
        declaration = await self.read_export_declaration(session)
        if declaration is not None:
            raise TimeoutError  # Runner retains its claim and exposes the decision.
        receipt = await self.read_parsed_part(session)
        if receipt is None:
            raise TimeoutError
        return receipt

    async def read_parsed_part(self, session) -> UploadReceipt | None:
        page = self.inspect_page(session)
        if not self._upload_attempted:
            return None
        rows = page.locator(self.binding.part_rows)
        if await rows.count() != 1:
            return None
        row = await _unique(rows)
        try:
            part_id = await _value(row, self.binding.part_id)
            file_id = await _value(row, self.binding.file_id)
            if any(len(value) > 80 for value in (part_id, file_id)):
                return None
            require_identity(part_id)
            require_identity(file_id)
            if await _value(row, self.binding.file_name) != self.snapshot.payload.sdk_payload()["name"]:
                return None
            size = await _value(row, self.binding.file_size)
            if re.fullmatch(r"[1-9][0-9]*", size) is None or int(size) != len(self.snapshot.payload.buffer):
                return None
            numbers = [await _value(row, field) for field in self.binding.geometry]
            geometry = Geometry(*(_decimal(value) for value in numbers))
            geometry.validate()
        except (QuoteError, BrowserStop):
            return None
        receipt = UploadReceipt(f"{part_id}:{file_id}", self.snapshot.payload.sha256, geometry)
        if self._upload is not None and self._upload != receipt:
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        self._part_id, self._upload = part_id, receipt
        return receipt

    async def read_export_declaration(self, session) -> ExportDeclaration | None:
        page = self.inspect_page(session)
        root = page.locator(self.binding.declaration_root)
        if await root.count() == 0 or not await root.is_visible():
            self.export_declaration = None
            self.manual_reason = None
            return None
        await _unique(root)
        statement = await _value(root, self.binding.declaration_statement)
        labels = []
        for selector in (self.binding.declaration_no, self.binding.declaration_yes):
            control = await _unique(root.locator(selector))
            labels.append((await control.inner_text(timeout=2000)).strip())
        options = [ExportDeclarationOption(value=value, label=label) for value, label in zip(("not_controlled", "controlled"), labels, strict=True)]
        identity = json.dumps({"statement": statement, "options": [option.model_dump() for option in options], "sha256": self.snapshot.payload.sha256}, sort_keys=True)
        declaration = ExportDeclaration(declaration_id=hashlib.sha256(identity.encode()).hexdigest(), statement=statement, options=options)
        self.export_declaration = declaration
        self.manual_reason = "QUOTE_EXPORT_DECLARATION_REQUIRED"
        return declaration

    async def continue_declaration(self, session, declaration: ExportDeclaration, choice: str) -> DeclarationReceipt:
        if self._declaration_attempt is not None or not self._upload_attempted:
            raise QuoteError("QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY")
        current = await self.read_export_declaration(session)
        if current != declaration or choice not in {option.value for option in declaration.options}:
            raise QuoteError("QUOTE_EXPORT_DECLARATION_STALE")
        root = self.inspect_page(session).locator(self.binding.declaration_root)
        selector = self.binding.declaration_no if choice == "not_controlled" else self.binding.declaration_yes
        option = await _unique(root.locator(selector))
        button = await _unique(root.locator(self.binding.declaration_continue))
        if (await button.inner_text(timeout=2000)).strip() != "Continue":
            raise QuoteError("XOMETRY_PAGE_UNSUPPORTED")
        self._declaration_attempt = (declaration.declaration_id, choice)
        self.inspect_page(session)
        await option.click(timeout=3000)
        await self._guard_mutation(session)
        await button.click(timeout=3000)
        receipt = await self.reconcile(session, IntentKey(session.scope, self.run_id, "1", Operation.DECLARATION, ""))
        if not isinstance(receipt, DeclarationReceipt):
            raise QuoteError("QUOTE_EXPORT_DECLARATION_UNCONFIRMED_NO_RETRY")
        return receipt

    async def _part(self, session, upload: UploadReceipt):
        current = await self.read_parsed_part(session)
        if current != upload or self._part_id is None:
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        return await _unique(self.inspect_page(session).locator(self.binding.part_rows))

    async def _select_exact(self, session, control: ParameterControl, value: str):
        page = self.inspect_page(session)
        target = dict(control.values).get(value, value)
        locator = await _unique(page.locator(control.control))
        self.inspect_page(session)
        if control.mode == "input":
            await locator.fill(target, timeout=2000)
        elif control.mode == "select":
            await locator.select_option(label=target, timeout=2000)
        else:
            await locator.click(timeout=2000)
            if control.search:
                search = await _unique(page.locator(control.search))
                self.inspect_page(session)
                await search.fill(target, timeout=2000)
            options = page.locator(control.options)
            matches = []
            for index in range(await options.count()):
                option = options.nth(index)
                title = await _unique(option.locator(control.option_title))
                if (await title.inner_text(timeout=2000)).strip() == target:
                    matches.append(option)
            if len(matches) != 1:
                raise QuoteError("XOMETRY_PARAMETER_AMBIGUOUS" if matches else "XOMETRY_PARAMETER_UNSUPPORTED")
            self.inspect_page(session)
            await matches[0].click(timeout=2000)

    async def configure(self, session, upload: UploadReceipt, requested: Parameters) -> None:
        page = self.inspect_page(session)
        self.validate_parameters(requested)
        await self._part(session, upload)
        if self._save_attempted:
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        # This feature is CNC. No implicit fallback to an alternative process.
        if await _value(page, self.binding.process) != "CNC":
            if "process" not in dict(requested.values):
                raise QuoteError("XOMETRY_PARAMETER_UNSUPPORTED")
        quote = await _unique(page.locator(self.binding.quote_root))
        self._before_revision = await _value(quote, self.binding.quote_revision)
        values = dict(requested.values)
        # Binding order is the reviewed dependency order; observe fresh controls
        # and options after each preceding change, never reuse generated IDs.
        for control in self.binding.parameters:
            if control.key in values:
                await self._select_exact(session, control, values[control.key])
        button = await _unique(page.locator(self.binding.save_button))
        if (await button.inner_text(timeout=2000)).strip() != "Save Configuration":
            raise QuoteError("XOMETRY_PAGE_UNSUPPORTED")
        await self._guard_mutation(session)
        self._save_attempted = True
        await button.click(timeout=3000)
        # A still-visible editor or unchanged revision is not a save receipt.
        await self._read_saved_revision(session)
        if await self.read_effective(session, upload) != requested:
            raise BrowserStop(Reason.PARAMETERS_MISMATCH)

    async def _read_saved_revision(self, session):
        if not self._save_attempted or self._before_revision is None:
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        root = await _unique(self.inspect_page(session).locator(self.binding.quote_root))
        revision = await _value(root, self.binding.quote_revision)
        priced_at = _timestamp(await _value(root, self.binding.quote_priced_at))
        if revision == self._before_revision or (self._saved_revision is not None and self._saved_revision != revision):
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        if self._saved_at is not None and self._saved_at != priced_at:
            raise QuoteError("XOMETRY_RECEIPT_UNCONFIRMED")
        self._saved_revision, self._saved_at = revision, priced_at
        return root

    async def read_effective(self, session, upload: UploadReceipt) -> Parameters:
        page = self.inspect_page(session)
        await self._part(session, upload)
        if await _value(page, self.binding.process) != "CNC":
            raise BrowserStop(Reason.PARAMETERS_MISMATCH)
        values = {}
        controls = {control.key: control for control in self.binding.parameters}
        for key, _ in self.snapshot.requested.values:
            control = controls[key]
            raw = await _value(page, control.saved)
            if control.values:
                matches = [canonical for canonical, title in control.values if title == raw]
                if len(matches) != 1:
                    raise QuoteError("XOMETRY_PARAMETER_AMBIGUOUS")
                raw = matches[0]
            values[key] = raw
        return Parameters.from_mapping(values)

    async def submit(self, session, upload: UploadReceipt, requested: Parameters) -> SubmissionReceipt:
        # Save Configuration already causes recalculation. The runner retains a
        # separate submit intent, but this method must not click Save again.
        root = await self._read_saved_revision(session)
        if await self.read_effective(session, upload) != requested:
            raise BrowserStop(Reason.PARAMETERS_MISMATCH)
        if await _value(root, self.binding.quote_part_id) != self._part_id:
            raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
        quote_id = await _value(root, self.binding.quote_id)
        reference = f"{quote_id}:{self._saved_revision}"
        require_identity(reference)
        self._submission = SubmissionReceipt(reference, upload.reference, requested)
        return self._submission

    async def _lead(self, root) -> LeadTime:
        text = await _value(root, self.binding.quote_lead)
        kind = self.binding.lead_kind
        if kind in {LeadTimeKind.DURATION, LeadTimeKind.PRODUCTION_DURATION}:
            match = re.fullmatch(r"(\d+)(?:\s*[-–]\s*(\d+))?\s+(business|calendar)\s+days", text, re.IGNORECASE)
            if match is None:
                raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
            lead = LeadTime(
                text,
                int(match[1]),
                int(match[2] or match[1]),
                DayBasis.BUSINESS if match[3].lower() == "business" else DayBasis.CALENDAR,
                kind=kind,
                source=self.binding.evidence,
                start_point=self.binding.lead_start,
            )
        else:
            if self.binding.lead_date is None:
                raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
            raw = await _value(root, self.binding.lead_date)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw) is None:
                raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
            year, month, day = (int(number) for number in raw.split("-"))
            lead = LeadTime(text, kind=kind, source=self.binding.evidence, date=LeadTimeDate(month, day, year))
        lead.validate()
        return lead

    async def extract_quote(self, session, upload: UploadReceipt, submission: SubmissionReceipt) -> QuoteObservation | ProvisionalQuote:
        if self._submission != submission:
            raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
        root = await self._read_saved_revision(session)
        if f"{await _value(root, self.binding.quote_id)}:{self._saved_revision}" != submission.reference:
            raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
        if await _value(root, self.binding.quote_part_id) != self._part_id:
            raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
        effective = await self.read_effective(session, upload)
        if effective != submission.effective or await _value(root, self.binding.quote_quantity) != dict(effective.values)["quantity"]:
            raise BrowserStop(Reason.PARAMETERS_MISMATCH)
        raw_status = await _value(root, self.binding.quote_status)
        status = dict(self.binding.statuses).get(raw_status)
        if status is None or self._saved_at is None:
            raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
        amount = currency = scope = lead = None
        if status != "PENDING_REVIEW":
            amount = _decimal(await _value(root, self.binding.quote_amount))
            currency = await _value(root, self.binding.quote_currency)
            if currency not in KNOWN_CURRENCIES:
                raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
            raw_scope = await _value(root, self.binding.quote_scope)
            mapped_scope = dict(self.binding.scopes).get(raw_scope)
            if mapped_scope is None:
                raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
            scope, lead = PriceScope(mapped_scope), await self._lead(root)
        # Independent DOM reads can straddle a recalculation. A second complete
        # parameter/stamp check prevents publishing mixed-generation values.
        if await self.read_effective(session, upload) != effective:
            raise BrowserStop(Reason.PARAMETERS_MISMATCH)
        final_root = await self._read_saved_revision(session)
        if f"{await _value(final_root, self.binding.quote_id)}:{self._saved_revision}" != submission.reference:
            raise QuoteError("XOMETRY_QUOTE_EVIDENCE_MISSING")
        observation = QuoteObservation(
            session.scope,
            self.run_id,
            "1",
            upload.reference,
            submission.reference,
            upload.sha256,
            effective,
            upload.geometry,
            amount,
            currency,
            scope,
            lead,
            QuoteFreshness.RECALCULATED,
            self._saved_at,
            datetime.now(UTC),
        )
        if status == "QUOTED":
            return observation
        return ProvisionalQuote(status, observation, self.binding.evidence, True, self._saved_at)

    async def reconcile(self, session, key: IntentKey):
        self.inspect_page(session)
        if key.scope != session.scope or key.item_id != self.run_id or key.execution_generation != "1":
            raise BrowserStop(Reason.INTENT_CONFLICT)
        if key.operation in {Operation.UPLOAD, Operation.DECLARATION}:
            if await self.read_export_declaration(session) is not None:
                return None
            upload = await self.read_parsed_part(session)
            if key.operation == Operation.UPLOAD:
                return upload
            if upload is not None and self._declaration_attempt is not None:
                declaration_id, choice = self._declaration_attempt
                return DeclarationReceipt(declaration_id, choice, upload.sha256, upload.reference)
        if key.operation == Operation.CONFIGURE and self._upload is not None:
            try:
                await self._read_saved_revision(session)
                effective = await self.read_effective(session, self._upload)
            except QuoteError as exc:
                if exc.reason in {"XOMETRY_PAGE_UNSUPPORTED", "XOMETRY_RECEIPT_UNCONFIRMED", "XOMETRY_QUOTE_EVIDENCE_MISSING"}:
                    return None
                raise
            if effective == self.snapshot.requested:
                from app.modules.cnc.browser.contracts import ConfigurationReceipt

                return ConfigurationReceipt(effective)
        if key.operation == Operation.SUBMIT:
            return self._submission
        return None
