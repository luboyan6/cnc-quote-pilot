"""Synthetic fixtures only; MemoryIntents is deliberately outside application code."""

import asyncio
import hashlib
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from cryptography.fernet import Fernet

from app.modules.cnc.browser.contracts import (
    Authentication,
    AuthStatus,
    DayBasis,
    Geometry,
    IntentClaim,
    IntentRecord,
    IntentState,
    LeadTime,
    Parameters,
    PriceScope,
    QuoteFreshness,
    QuoteObservation,
    SessionScope,
    SubmissionReceipt,
    UploadReceipt,
)
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import TrustedStep
from app.modules.cnc.browser.policy import BrowserPolicy
from app.modules.cnc.browser.session import BrowserSession
from app.modules.cnc.browser.state import SessionCodec

if TYPE_CHECKING:
    from app.modules.cnc.browser.workflow import QuoteRequest

SCOPE = SessionScope("synthetic-owner", "synthetic-platform", "synthetic-account")
POLICY = BrowserPolicy(frozenset({"fixture.example.com"}))
PARAMS = Parameters.from_mapping({"process": "CNC milling", "material": "Aluminium 6061", "quantity": "2", "finish": "As machined", "length_unit": "mm"})
GEOMETRY = Geometry(Decimal("10"), Decimal("20"), Decimal("30"), Decimal("6000"))
STEP_BYTES = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"


class TestCrypto:
    """Real established cipher, no home-made production crypto in a fixture."""

    def __init__(self):
        self.fernet = Fernet(Fernet.generate_key())

    def encrypt(self, plain):
        return self.fernet.encrypt(plain.encode()).decode()

    def decrypt(self, cipher):
        return self.fernet.decrypt(cipher.encode()).decode()


def codec():
    return SessionCodec(TestCrypto())


def fixture_step(root):
    path = root / "synthetic.step"
    path.write_bytes(STEP_BYTES)
    return TrustedStep(root, path, hashlib.sha256(STEP_BYTES).hexdigest(), len(STEP_BYTES), 15_000_000)


def fixture_session(scope=SCOPE):
    return BrowserSession(scope, POLICY, codec())


class MemoryIntents:
    """Test double: verifies atomic identity/fingerprint behavior in one loop."""

    def __init__(self):
        self.records = {}
        self.fingerprints = {}
        self.claims = []

    async def claim(self, key):
        identity = (key.scope, key.item_id)
        existing = self.fingerprints.get(identity)
        if existing is not None and existing != key.fingerprint:
            raise BrowserStop(Reason.INTENT_CONFLICT)
        self.fingerprints[identity] = key.fingerprint
        self.claims.append(key)
        if key.identity in self.records:
            return IntentClaim(False, self.records[key.identity])
        record = IntentRecord(key, IntentState.CLAIMED)
        self.records[key.identity] = record
        return IntentClaim(True, record)

    async def confirm(self, key, receipt):
        self.records[key.identity] = IntentRecord(key, IntentState.CONFIRMED, receipt)

    async def mark_uncertain(self, key):
        record = self.records[key.identity]
        if record.state != IntentState.CONFIRMED:
            self.records[key.identity] = IntentRecord(key, IntentState.UNCERTAIN)


class FakeAdapter:
    def __init__(self, step, scope=SCOPE):
        self.scope = scope
        self.request: QuoteRequest | None = None
        self.auth = Authentication(AuthStatus.AUTHENTICATED, scope)
        self.effective = PARAMS
        self.upload_receipt = UploadReceipt("synthetic-part", step.expected_sha256, GEOMETRY)
        self.submission = SubmissionReceipt("synthetic-quote", "synthetic-part", PARAMS)
        self.calls = []
        self.upload_error: Exception | None = None
        self.configure_error: Exception | None = None
        self.submit_error: Exception | None = None
        self.upload_wait: asyncio.Event | None = None
        self.configure_wait: asyncio.Event | None = None
        self.submit_wait: asyncio.Event | None = None
        self.reconciled = {}
        self.quote_changes = {}

    async def authenticate(self, session):
        self.calls.append("authenticate")
        return self.auth

    async def upload(self, session, payload):
        self.calls.append("upload")
        if self.upload_wait is not None:
            await self.upload_wait.wait()
        if self.upload_error:
            raise self.upload_error
        return self.upload_receipt

    async def configure(self, session, upload, requested):
        self.calls.append("configure")
        if self.configure_wait is not None:
            await self.configure_wait.wait()
        if self.configure_error:
            raise self.configure_error

    async def read_effective(self, session, upload):
        self.calls.append("read_effective")
        return self.effective

    async def submit(self, session, upload, requested):
        self.calls.append("submit")
        if self.submit_wait is not None:
            await self.submit_wait.wait()
        if self.submit_error:
            raise self.submit_error
        return self.submission

    async def extract_quote(self, session, upload, submission):
        self.calls.append("extract_quote")
        assert self.request is not None, "Synthetic quote extraction requires its request fixture"
        now = datetime.now(UTC)
        fields = {
            "scope": self.scope,
            "item_id": self.request.item_id,
            "execution_generation": self.request.execution_generation,
            "upload_reference": upload.reference,
            "submission_reference": submission.reference,
            "sha256": upload.sha256,
            "effective": self.effective,
            "geometry": upload.geometry,
            "amount": Decimal("123.4500"),
            "currency": "USD",
            "price_scope": PriceScope.LINE,
            "lead_time": LeadTime("5-7 business days", 5, 7, DayBasis.BUSINESS),
            "freshness": QuoteFreshness.RECALCULATED,
            "priced_at": now,
            "observed_at": now,
        }
        fields.update(self.quote_changes)
        return QuoteObservation(**fields)

    async def reconcile(self, session, key):
        self.calls.append(f"reconcile_{key.operation}")
        return self.reconciled.get(key.operation)


class FakeContext:
    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.page = SimpleNamespace(goto=AsyncMock())
        self.close = AsyncMock()
        self.storage_state = AsyncMock(return_value={"cookies": [], "origins": []})
        self.routes = []
        self.websocket_routes = []
        self.listeners = {}

    def on(self, event, callback):
        self.listeners[event] = callback

    def set_default_timeout(self, value):
        self.timeout = value

    def set_default_navigation_timeout(self, value):
        self.navigation_timeout = value

    async def route(self, pattern, callback):
        self.routes.append(callback)

    async def route_web_socket(self, pattern, callback):
        self.websocket_routes.append(callback)

    async def new_page(self):
        return self.page


class FakeHarness:
    def __init__(self):
        self.browsers = []
        self.contexts = []
        self.managers = []
        self.proxies = []
        self.launch_error: Exception | None = None
        self.launch_wait: asyncio.Event | None = None

    def manager(self):
        manager = SimpleNamespace(start=AsyncMock(), __aexit__=AsyncMock())

        async def launch(**kwargs):
            if self.launch_wait:
                await self.launch_wait.wait()
            if self.launch_error:
                raise self.launch_error

            async def new_context(**context_kwargs):
                context = FakeContext(context_kwargs)
                self.contexts.append(context)
                return context

            browser = SimpleNamespace(close=AsyncMock(), new_context=AsyncMock(side_effect=new_context), kwargs=kwargs)
            self.browsers.append(browser)
            return browser

        manager.start.return_value = SimpleNamespace(chromium=SimpleNamespace(launch=AsyncMock(side_effect=launch)))
        self.managers.append(manager)
        return manager

    def proxy(self, resolver):
        proxy = SimpleNamespace(start=AsyncMock(return_value="socks5://127.0.0.1:12345"), close=AsyncMock())
        self.proxies.append(proxy)
        return proxy
