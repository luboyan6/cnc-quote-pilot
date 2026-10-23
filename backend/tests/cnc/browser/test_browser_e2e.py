"""Opt-in real fresh Chromium tests on intercepted synthetic HTTPS pages only.

No provider credentials, personal profile, CDP, live CNC platform or real CAD
geometry parser is used. A test-only intercepted server persists synthetic
remote state across browser restarts; it is not an application IntentStore.
"""

import asyncio
import base64
import html
import json
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from _support import GEOMETRY, PARAMS, POLICY, SCOPE, STEP_BYTES, MemoryIntents, codec, fixture_step

from app.modules.cnc.browser.contracts import (
    Authentication,
    AuthStatus,
    DayBasis,
    Geometry,
    IntentKey,
    IntentState,
    LeadTime,
    LeadTimeDate,
    LeadTimeKind,
    MutationReceipt,
    Parameters,
    PriceScope,
    QuoteFreshness,
    QuoteObservation,
    SessionScope,
    SubmissionReceipt,
    UploadReceipt,
)
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.files import StepPayload, upload_step, upload_step_with_chooser
from app.modules.cnc.browser.session import BrowserExecutor, BrowserSession
from app.modules.cnc.browser.workflow import QuoteRequest, QuoteWorkflow

ORIGIN = "https://fixture.example.com"
FIXTURE = Path(__file__).with_name("browser_fixture.html")
BROWSER_CHANNEL = os.environ.get("CNC_BROWSER_CHANNEL") or None


class SyntheticServer:
    """Only exact synthetic HTTPS origin is fulfilled; other hosts reach guards.

    There is no transport/DNS bypass in production code. These fixtures do not
    prove live public egress; the standalone proxy's tests exercise that layer.
    """

    def __init__(self, *, freshness: QuoteFreshness = QuoteFreshness.RECALCULATED, lead_time: LeadTime | None = None) -> None:
        self.counts = {"upload": 0, "configure": 0, "submit": 0}
        self.upload: dict[str, Any] | None = None
        self.effective: dict[str, str] | None = None
        self.quote: dict[str, Any] | None = None
        self.upload_payload: dict[str, Any] | None = None
        self.item_id = self.generation = ""
        self.freshness = freshness
        self.lead_time = lead_time if lead_time is not None else LeadTime("5-7 business days", 5, 7, DayBasis.BUSINESS)

    def state(self) -> dict[str, Any]:
        return {"counts": self.counts, "upload": self.upload, "effective": self.effective, "quote": self.quote}

    async def install(self, session: BrowserSession, *, auth: AuthStatus = AuthStatus.AUTHENTICATED) -> None:
        scope = session.scope

        async def route_fixture(route: Any) -> None:
            parsed = urlsplit(route.request.url)
            if parsed.scheme != "https" or parsed.netloc != "fixture.example.com":
                await route.fallback()
                return
            if parsed.path == "/":
                body = FIXTURE.read_text(encoding="utf-8")
                body = body.replace("__ACCOUNT__", html.escape(scope.account_id, quote=True)).replace("__AUTH__", auth.value)
                body = body.replace("__STATE__", json.dumps(self.state()))
                await route.fulfill(status=200, content_type="text/html", body=body)
                return
            if parsed.path == "/redirect":
                await route.fulfill(status=302, headers={"Location": "https://forbidden.invalid/synthetic-trap"})
                return
            if route.request.method != "POST":
                await route.fulfill(status=404)
                return
            payload = route.request.post_data_json
            if parsed.path == "/synthetic/upload":
                self.counts["upload"] += 1
                self.upload_payload = payload
                self.upload = {
                    "reference": "synthetic-part-1",
                    "sha256": payload["sha256"],
                    "geometry": {"x_mm": "10", "y_mm": "20", "z_mm": "30", "volume_mm3": "6000"},
                }
            elif parsed.path == "/synthetic/configure":
                self.counts["configure"] += 1
                self.effective = payload["effective"]
                self.item_id, self.generation = payload["item_id"], payload["generation"]
            elif parsed.path == "/synthetic/submit":
                self.counts["submit"] += 1
                if self.upload is None or self.effective is None:
                    await route.fulfill(status=409)
                    return
                priced_at = datetime.now(UTC)
                if self.freshness == QuoteFreshness.CACHE_UNVERIFIED:
                    priced_at -= timedelta(seconds=1)
                self.quote = {
                    "reference": "synthetic-quote-1",
                    "item_id": self.item_id,
                    "generation": self.generation,
                    "upload_reference": self.upload["reference"],
                    "sha256": self.upload["sha256"],
                    "effective": self.effective,
                    "geometry": self.upload["geometry"],
                    "amount": "123.4500",
                    "currency": "USD",
                    "price_scope": "line",
                    "lead_time": self.lead_time.as_dict(),
                    "freshness": self.freshness.value,
                    "priced_at": priced_at.isoformat(),
                }
            else:
                await route.fulfill(status=404)
                return
            await route.fulfill(status=200, content_type="application/json", body=json.dumps(self.state()))

        # The later test route only fulfills the exact synthetic origin. Every
        # other request falls through to the component's context-wide guard.
        await session.page.context.route("**/*", route_fixture)
        await session.goto(ORIGIN + "/")


class SyntheticAdapter:
    """Trusted test adapter reading browser DOM through official Locator APIs."""

    def __init__(self, request: QuoteRequest, *, unknown_submit: bool = False) -> None:
        self.request = request
        self.unknown_submit = unknown_submit
        self.calls: list[str] = []
        self.observed_disabled_apply = False

    @staticmethod
    async def read_json(session: BrowserSession, selector: str) -> dict[str, Any]:
        locator = session.page.locator(selector)
        await locator.wait_for(state="visible")
        return json.loads(await locator.inner_text())

    @staticmethod
    def geometry(value: dict[str, str]) -> Geometry:
        return Geometry(*(Decimal(value[key]) for key in ("x_mm", "y_mm", "z_mm", "volume_mm3")))

    async def authenticate(self, session: BrowserSession) -> Authentication:
        self.calls.append("authenticate")
        body = session.page.locator("body")
        status = AuthStatus(await body.get_attribute("data-auth"))
        account_id = await body.get_attribute("data-account")
        identity = SessionScope(session.scope.owner_id, session.scope.platform_code, account_id)
        return Authentication(status, identity)

    async def upload(self, session: BrowserSession, payload: StepPayload) -> UploadReceipt:
        self.calls.append("upload")
        await upload_step(session.page.locator("#step"), payload)
        value = await self.read_json(session, "#upload-json")
        return UploadReceipt(value["reference"], value["sha256"], self.geometry(value["geometry"]))

    async def configure(self, session: BrowserSession, upload: UploadReceipt, requested: Parameters) -> None:
        self.calls.append("configure")
        page = session.page
        for name, value in requested.values:
            locator = page.locator("#" + name)
            if name == "quantity":
                await locator.fill(value)
            else:
                await locator.select_option(label=value)
        await page.locator("#item-id").fill(self.request.item_id)
        await page.locator("#generation").fill(self.request.execution_generation)
        await page.locator("#arm-apply").click()
        self.observed_disabled_apply = await page.locator("#apply").is_disabled()
        # No sleep/explicit enabled wait: native Locator.click auto-waits.
        await page.locator("#apply").click()
        await page.locator("#effective-json").wait_for(state="visible")

    async def read_effective(self, session: BrowserSession, upload: UploadReceipt) -> Parameters:
        self.calls.append("read_effective")
        return Parameters.from_mapping(await self.read_json(session, "#effective-json"))

    async def submit(self, session: BrowserSession, upload: UploadReceipt, requested: Parameters) -> SubmissionReceipt:
        self.calls.append("submit")
        await session.page.locator("#submit").click()
        value = await self.read_json(session, "#quote-json")
        if self.unknown_submit:
            # The remote synthetic side effect occurred; its receipt is lost.
            raise TimeoutError("synthetic receipt unavailable")
        return SubmissionReceipt(value["reference"], value["upload_reference"], Parameters.from_mapping(value["effective"]))

    async def extract_quote(self, session: BrowserSession, upload: UploadReceipt, submission: SubmissionReceipt) -> QuoteObservation:
        self.calls.append("extract_quote")
        value = await self.read_json(session, "#quote-json")
        return QuoteObservation(
            scope=session.scope,
            item_id=value["item_id"],
            execution_generation=value["generation"],
            upload_reference=value["upload_reference"],
            submission_reference=value["reference"],
            sha256=value["sha256"],
            effective=Parameters.from_mapping(value["effective"]),
            geometry=self.geometry(value["geometry"]),
            amount=Decimal(value["amount"]),
            currency=value["currency"],
            price_scope=PriceScope(value["price_scope"]),
            lead_time=LeadTime.from_dict(value["lead_time"]),
            freshness=QuoteFreshness(value["freshness"]),
            priced_at=datetime.fromisoformat(value["priced_at"]),
            observed_at=datetime.now(UTC),
        )

    async def reconcile(self, session: BrowserSession, key: IntentKey) -> MutationReceipt | None:
        self.calls.append("reconcile_" + key.operation.value)
        # Read the actual synthetic DOM but deliberately decline to confirm an
        # unknown result: this fixture models insufficient reconciliation proof.
        await self.read_json(session, "#quote-json")
        return None


@unittest.skipUnless(os.environ.get("CNC_BROWSER_E2E") == "1", "Set CNC_BROWSER_E2E=1 to run real managed Chromium synthetic E2E")
class BrowserE2ETests(unittest.IsolatedAsyncioTestCase):
    def make_request(self, root: Path) -> QuoteRequest:
        return QuoteRequest("synthetic-item", "synthetic-generation", fixture_step(root), PARAMS)

    def assert_released(self, executor: BrowserExecutor, page: Any, browser: Any) -> None:
        self.assertEqual(executor.active_count, 0)
        self.assertTrue(page.is_closed())
        self.assertFalse(browser.is_connected())

    async def test_workflow_native_upload_fields_autowait_and_fresh_quote(self) -> None:
        server, intents = SyntheticServer(), MemoryIntents()
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        with tempfile.TemporaryDirectory(prefix="cnc-synthetic-") as temp:
            request = self.make_request(Path(temp))
            adapter = SyntheticAdapter(request)
            async with executor.session(SCOPE, POLICY) as session:
                await server.install(session)
                page, browser = session.page, session.page.context.browser
                print(f"Synthetic E2E runtime: Playwright {version('playwright')}; browser {browser.version}; channel {BROWSER_CHANNEL or 'managed'}; fresh headless profile")
                quote = await QuoteWorkflow(intents, read_timeout_seconds=3).execute(session, adapter, request)
                result = quote.as_dict()
                self.assertEqual(result["status"], "QUOTED")
                self.assertEqual(result["amount"], "123.4500")
                self.assertEqual(result["currency"], "USD")
                self.assertEqual(result["price_scope"], "line")
                self.assertEqual(result["freshness"], "RECALCULATED")
                self.assertEqual(
                    result["lead_time"],
                    {
                        "schema_version": 2,
                        "kind": "duration",
                        "text": "5-7 business days",
                        "source": None,
                        "minimum_days": 5,
                        "maximum_days": 7,
                        "basis": "business_days",
                        "start_point": None,
                        "date": None,
                    },
                )
                self.assertEqual(result["effective"], dict(PARAMS.values))
                self.assertEqual(quote.observation.geometry, GEOMETRY)
                self.assertTrue(adapter.observed_disabled_apply)
                self.assertEqual(server.counts, {"upload": 1, "configure": 1, "submit": 1})
                self.assertEqual(base64.b64decode(server.upload_payload["bytes_base64"]), STEP_BYTES)
                self.assertEqual(server.upload_payload["name"], "part.step")
                self.assertEqual(server.upload_payload["mime_type"], "application/step")
                self.assertEqual(server.upload_payload["size"], len(STEP_BYTES))
                self.assertEqual(server.upload_payload["sha256"], request.step.expected_sha256)
                self.assertEqual(len(intents.records), 3)
                self.assertTrue(all(record.state == IntentState.CONFIRMED for record in intents.records.values()))
                self.assertEqual(await page.locator("#error").inner_text(), "")
            self.assert_released(executor, page, browser)

    async def test_date_lead_time_round_trip_through_dom_preserves_unknown_year(self) -> None:
        for kind in (LeadTimeKind.ARRIVAL_DATE, LeadTimeKind.SHIP_DATE):
            with self.subTest(kind=kind):
                lead = LeadTime("Nov 9", kind=kind, source="synthetic same-request date evidence", date=LeadTimeDate(11, 9))
                server, intents = SyntheticServer(lead_time=lead), MemoryIntents()
                executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
                with tempfile.TemporaryDirectory(prefix="cnc-synthetic-") as temp:
                    request = self.make_request(Path(temp))
                    async with executor.session(SCOPE, POLICY) as session:
                        await server.install(session)
                        page, browser = session.page, session.page.context.browser
                        quote = await QuoteWorkflow(intents, read_timeout_seconds=3).execute(session, SyntheticAdapter(request), request)
                        snapshot = quote.as_dict()["lead_time"]
                        self.assertEqual(snapshot["kind"], kind.value)
                        self.assertEqual(snapshot["text"], "Nov 9")
                        self.assertEqual(snapshot["source"], "synthetic same-request date evidence")
                        self.assertEqual(snapshot["date"], {"month": 11, "day": 9, "year": None})
                        self.assertTrue(all(snapshot[field] is None for field in ("minimum_days", "maximum_days", "basis", "start_point")))
                        self.assertEqual(server.counts, {"upload": 1, "configure": 1, "submit": 1})
                    self.assert_released(executor, page, browser)

    async def test_dynamic_filechooser_uploads_verified_bytes(self) -> None:
        server = SyntheticServer()
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        with tempfile.TemporaryDirectory(prefix="cnc-synthetic-") as temp:
            step = fixture_step(Path(temp))
            async with executor.session(SCOPE, POLICY) as session:
                await server.install(session)
                page, browser = session.page, session.page.context.browser
                await upload_step_with_chooser(page, page.locator("#dynamic-picker"), step.read_verified())
                await page.locator("#upload-reference").wait_for(state="visible")
                self.assertEqual(await page.locator("#dynamic-step").count(), 1)
                self.assertEqual(base64.b64decode(server.upload_payload["bytes_base64"]), STEP_BYTES)
                self.assertEqual(server.upload_payload["sha256"], step.expected_sha256)
                self.assertEqual(server.counts, {"upload": 1, "configure": 0, "submit": 0})
            self.assert_released(executor, page, browser)

    async def test_encrypted_state_restore_and_concurrent_account_isolation(self) -> None:
        state_codec = codec()
        executor = BrowserExecutor(state_codec, channel=BROWSER_CHANNEL, capacity=2, timeout_ms=3000)
        other = SessionScope(SCOPE.owner_id, SCOPE.platform_code, "synthetic-other-account")
        async with executor.session(SCOPE, POLICY) as first:
            await SyntheticServer().install(first)
            first_page, first_browser = first.page, first.page.context.browser
            await first_page.locator("#session-value").fill("synthetic-secret-A")
            await first_page.locator("#sign-in").click()
            first.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, SCOPE))
            encrypted = await first.export_encrypted_state()
            self.assertNotIn("synthetic-secret-A", encrypted)
            with self.assertRaises(BrowserStop) as busy:
                async with executor.session(SCOPE, POLICY):
                    self.fail("Same account unexpectedly admitted")
            self.assertEqual(busy.exception.reason, Reason.SESSION_BUSY)
            async with executor.session(other, POLICY) as second:
                await SyntheticServer().install(second)
                second_page, second_browser = second.page, second.page.context.browser
                self.assertEqual(executor.active_count, 2)
                self.assertEqual(await second_page.evaluate("document.cookie"), "")
                self.assertIsNone(await second_page.evaluate("localStorage.getItem('synthetic_session')"))
                await second_page.locator("#session-value").fill("synthetic-secret-B")
                await second_page.locator("#sign-in").click()
                self.assertEqual(await first_page.evaluate("localStorage.getItem('synthetic_session')"), "synthetic-secret-A")
                self.assertEqual(await second_page.evaluate("localStorage.getItem('synthetic_session')"), "synthetic-secret-B")
            self.assertTrue(second_page.is_closed())
            self.assertFalse(second_browser.is_connected())
        self.assert_released(executor, first_page, first_browser)
        async with executor.session(SCOPE, POLICY, encrypted_state=encrypted) as restored:
            await SyntheticServer().install(restored)
            restored_page, restored_browser = restored.page, restored.page.context.browser
            self.assertIn("synthetic_session=synthetic-secret-A", await restored_page.evaluate("document.cookie"))
            self.assertEqual(await restored_page.evaluate("localStorage.getItem('synthetic_session')"), "synthetic-secret-A")
            with self.assertRaises(BrowserStop) as unverified:
                await restored.export_encrypted_state()
            self.assertEqual(unverified.exception.reason, Reason.AUTH_REQUIRED)
            restored.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, SCOPE))
            self.assertIsInstance(await restored.export_encrypted_state(), str)
        self.assert_released(executor, restored_page, restored_browser)
        with self.assertRaises(BrowserStop) as wrong_scope:
            async with executor.session(other, POLICY, encrypted_state=encrypted):
                self.fail("Encrypted state unexpectedly crossed account boundary")
        self.assertEqual(wrong_scope.exception.reason, Reason.SESSION_INVALID)
        self.assertEqual(executor.active_count, 0)

    async def test_expired_and_challenge_stop_before_any_side_effect(self) -> None:
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        with tempfile.TemporaryDirectory(prefix="cnc-synthetic-") as temp:
            request = self.make_request(Path(temp))
            for status, reason in ((AuthStatus.EXPIRED, Reason.AUTH_REQUIRED), (AuthStatus.CHALLENGE, Reason.CHALLENGE)):
                with self.subTest(status=status):
                    server, intents = SyntheticServer(), MemoryIntents()
                    async with executor.session(SCOPE, POLICY) as session:
                        await server.install(session, auth=status)
                        page, browser = session.page, session.page.context.browser
                        adapter = SyntheticAdapter(request)
                        with self.assertRaises(BrowserStop) as stopped:
                            await QuoteWorkflow(intents).execute(session, adapter, request)
                        self.assertEqual(stopped.exception.reason, reason)
                        self.assertEqual(adapter.calls, ["authenticate"])
                        self.assertEqual(server.counts, {"upload": 0, "configure": 0, "submit": 0})
                        self.assertEqual(intents.records, {})
                    self.assert_released(executor, page, browser)

    async def test_unverified_cached_quote_never_becomes_quoted(self) -> None:
        server, intents = SyntheticServer(freshness=QuoteFreshness.CACHE_UNVERIFIED), MemoryIntents()
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        with tempfile.TemporaryDirectory(prefix="cnc-synthetic-") as temp:
            request = self.make_request(Path(temp))
            async with executor.session(SCOPE, POLICY) as session:
                await server.install(session)
                page, browser = session.page, session.page.context.browser
                with self.assertRaises(BrowserStop) as invalid:
                    await QuoteWorkflow(intents).execute(session, SyntheticAdapter(request), request)
                self.assertEqual(invalid.exception.reason, Reason.QUOTE_INVALID)
                self.assertEqual(server.quote["freshness"], "CACHE_UNVERIFIED")
                self.assertEqual(server.counts["submit"], 1)
            self.assert_released(executor, page, browser)

    async def test_native_locator_timeouts_are_bounded_before_side_effects(self) -> None:
        class TimeoutAdapter(SyntheticAdapter):
            async def authenticate(self, session: BrowserSession) -> Authentication:
                self.calls.append("authenticate_timeout")
                await session.page.locator("#synthetic-missing-identity").inner_text(timeout=80)
                return await super().authenticate(session)

        server, intents = SyntheticServer(), MemoryIntents()
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        with tempfile.TemporaryDirectory(prefix="cnc-synthetic-") as temp:
            request = self.make_request(Path(temp))
            adapter = TimeoutAdapter(request)
            async with executor.session(SCOPE, POLICY) as session:
                await server.install(session)
                page, browser = session.page, session.page.context.browser
                with self.assertRaises(BrowserStop) as timed_out:
                    await QuoteWorkflow(intents, read_retries=2, read_timeout_seconds=1).execute(session, adapter, request)
            self.assert_released(executor, page, browser)
            self.assertEqual(timed_out.exception.reason, Reason.READ_TIMEOUT)
            self.assertEqual(adapter.calls, ["authenticate_timeout"] * 3)
            self.assertEqual(server.counts, {"upload": 0, "configure": 0, "submit": 0})
            self.assertEqual(intents.records, {})

    async def test_unknown_submit_is_not_replayed_after_browser_rebuild(self) -> None:
        server, intents = SyntheticServer(), MemoryIntents()
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        with tempfile.TemporaryDirectory(prefix="cnc-synthetic-") as temp:
            request = self.make_request(Path(temp))
            async with executor.session(SCOPE, POLICY) as session:
                await server.install(session)
                page, browser = session.page, session.page.context.browser
                with self.assertRaises(BrowserStop) as unknown:
                    await QuoteWorkflow(intents).execute(session, SyntheticAdapter(request, unknown_submit=True), request)
                self.assertEqual(unknown.exception.reason, Reason.MUTATION_UNCERTAIN)
                self.assertEqual(server.counts, {"upload": 1, "configure": 1, "submit": 1})
                self.assertEqual(sum(record.state == IntentState.UNCERTAIN for record in intents.records.values()), 1)
            self.assert_released(executor, page, browser)
            async with executor.session(SCOPE, POLICY) as rebuilt:
                await server.install(rebuilt)
                page, browser = rebuilt.page, rebuilt.page.context.browser
                adapter = SyntheticAdapter(request)
                with self.assertRaises(BrowserStop) as still_unknown:
                    await QuoteWorkflow(intents).execute(rebuilt, adapter, request)
                self.assertEqual(still_unknown.exception.reason, Reason.MUTATION_UNCERTAIN)
                self.assertIn("reconcile_submit", adapter.calls)
                self.assertNotIn("upload", adapter.calls)
                self.assertNotIn("configure", adapter.calls)
                self.assertNotIn("submit", adapter.calls)
                self.assertEqual(server.counts, {"upload": 1, "configure": 1, "submit": 1})
            self.assert_released(executor, page, browser)

    async def test_forbidden_subresource_taints_session_and_releases_resources(self) -> None:
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        async with executor.session(SCOPE, POLICY) as session:
            await SyntheticServer().install(session)
            page, browser = session.page, session.page.context.browser
            async with page.expect_event("requestfailed", predicate=lambda request: "forbidden.invalid" in request.url):
                await page.evaluate("fetch('https://forbidden.invalid/synthetic-trap').catch(() => 'blocked')")
            with self.assertRaises(BrowserStop) as stopped:
                session.check_active()
            self.assertEqual(stopped.exception.reason, Reason.POLICY_BLOCKED)
        self.assert_released(executor, page, browser)

    async def test_forbidden_redirect_is_blocked_and_resources_release(self) -> None:
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        async with executor.session(SCOPE, POLICY) as session:
            await SyntheticServer().install(session)
            page, browser = session.page, session.page.context.browser
            with self.assertRaises(BrowserStop) as stopped:
                await session.goto(ORIGIN + "/redirect")
        self.assert_released(executor, page, browser)
        self.assertEqual(stopped.exception.reason, Reason.POLICY_BLOCKED)

    async def test_forbidden_popup_is_blocked_in_its_own_page(self) -> None:
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        async with executor.session(SCOPE, POLICY) as session:
            await SyntheticServer().install(session)
            page, browser = session.page, session.page.context.browser
            failed = asyncio.Event()
            page.context.on("requestfailed", lambda request: failed.set() if "forbidden.invalid" in request.url else None)
            await page.evaluate("window.open('https://forbidden.invalid/synthetic-popup', '_blank')")
            await asyncio.wait_for(failed.wait(), timeout=3)
            with self.assertRaises(BrowserStop) as stopped:
                session.check_active()
            self.assertEqual(stopped.exception.reason, Reason.POLICY_BLOCKED)
        self.assert_released(executor, page, browser)

    async def test_cancellation_releases_actual_browser_and_account_lease(self) -> None:
        executor = BrowserExecutor(codec(), channel=BROWSER_CHANNEL, timeout_ms=3000)
        ready = asyncio.Event()
        captured: dict[str, Any] = {}

        async def consumer() -> None:
            async with executor.session(SCOPE, POLICY) as session:
                await SyntheticServer().install(session)
                captured["page"], captured["browser"] = session.page, session.page.context.browser
                ready.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(consumer())
        try:
            await asyncio.wait_for(ready.wait(), timeout=15)
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError) as cancelled:
                await task
        self.assertNotIn(Reason.CLEANUP_FAILED.value, getattr(cancelled.exception, "__notes__", ()))
        self.assert_released(executor, captured["page"], captured["browser"])


if __name__ == "__main__":
    unittest.main()
