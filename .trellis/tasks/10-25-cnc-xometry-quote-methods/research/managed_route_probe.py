"""Inspect the owned Xometry route without uploading or changing a quote."""

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from managed_login_probe import (
    EXPECTED_HASH,
    Inspection,
    LoginError,
    LoginManager,
    QuoteRepository,
    async_engine,
)

OUTPUT = Path(__file__).with_name("managed-route-result.json")
HISTORY = "--history" in sys.argv
REFRESH_LOGIN = "--refresh-login" in sys.argv
LEGACY_ENTRY = "--legacy-entry" in sys.argv
if HISTORY:
    OUTPUT = OUTPUT.with_name("managed-history-result.json")
elif REFRESH_LOGIN:
    OUTPUT = OUTPUT.with_name("managed-login-refresh-result.json")
elif LEGACY_ENTRY:
    OUTPUT = OUTPUT.with_name("managed-legacy-entry-result.json")


def redact(value):
    if isinstance(value, str):
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[masked-email]", value)
        return re.sub(r"https?://[^\s]+", "[omitted-url]", value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


class RouteInspection(Inspection):
    def __init__(self, repository, auth, snapshot):
        super().__init__(repository, auth, snapshot)
        self.stage = 0
        self.transition_at = 0
        self.login_refresh_attempted = False
        self.pending_target = None
        self.result["observations"] = []
        self.result["request_failures"] = []
        self.result["response_failures"] = []

    def save(self):
        OUTPUT.write_text(json.dumps(redact(self.result), indent=2), encoding="utf-8")

    async def observe(self, session, label):
        page = session.page
        scope = page.locator('[role="dialog"]')
        if await scope.count() != 1 or not await scope.is_visible():
            scope = page
        controls = await scope.locator("button, a, input, [role=button]").evaluate_all(
            """els => els.filter(e => e.getBoundingClientRect().width || e.type === 'file')
            .map(e => ({tag:e.tagName, id:e.id || null, role:e.getAttribute('role'),
              type:e.getAttribute('type'), testid:e.getAttribute('data-testid'),
              label:(e.getAttribute('aria-label') || e.innerText || '').trim().slice(0,220),
              accept:e.type === 'file' ? e.accept : undefined,
              quote_path:e.tagName === 'A' && e.pathname.startsWith('/quoting/') ? e.pathname : undefined,
              quantity:e.getAttribute('role') === 'spinbutton' || e.type === 'number' ? e.value : undefined
            })).filter(e => e.id || e.testid || e.quote_path || e.role || e.type === 'file').slice(0,100)"""
        )
        headings = await page.locator("h1, h2, [role=dialog]").evaluate_all(
            "els => els.filter(e => e.getBoundingClientRect().width).map(e => ({tag:e.tagName, id:e.id || null, text:e.innerText.slice(0,3500)})).slice(0,15)"
        )
        parsed = urlsplit(page.url)
        fields = await scope.locator("[data-testid]").evaluate_all(
            """els => els.filter(e => /part|material|quantity|process|finish|quote|price|lead|dimension|volume|save|tolerance|roughness|itar|upload|currency/i.test(e.dataset.testid)
              && e.getBoundingClientRect().width).map(e => ({testid:e.dataset.testid,tag:e.tagName,
              text:e.innerText.length <= 1500 ? e.innerText.slice(0,350) : '[container]',
              disabled:e.disabled || e.getAttribute('aria-disabled') === 'true'})).slice(0,100)"""
        )
        self.result["observations"].append(
            {
                "stage": label,
                "host": parsed.hostname,
                "path": parsed.path,
                "query_keys": sorted({key.split("=")[0] for key in parsed.query.split("&") if key}),
                "controls": controls,
                "headings": headings,
                "fields": fields,
            }
        )
        self.save()

    async def advance(self, session, provider):
        await self.check_inputs()
        if not await provider.verify(session, self.snapshot.account.username):
            raise LoginError("QUOTE_PAGE_IDENTITY_REQUIRED")
        session.check_active()
        if self.stage == -3:
            login = session.page.locator("#header-login-register-button")
            if await login.count() != 1 or not await login.is_visible() or (await login.inner_text()).strip() != "Log In / Register":
                raise LoginError("MANAGED_LOGIN_CONTROL_UNAVAILABLE")
            await self.check_inputs()
            await login.click(timeout=4000)
            self.stage = -1
            self.transition_at = time.monotonic()
            return
        if self.stage == -2:
            session.page.set_default_navigation_timeout(8000)
            await self.check_inputs()
            if self.pending_target:
                await session.goto(self.pending_target)
            else:
                launch = session.page.locator("#dashboard-get-instant-quote-primary")
                if await launch.count() != 1 or not await launch.is_visible() or (await launch.inner_text()).strip() != "Get an Instant Quote":
                    raise LoginError("MANAGED_UPLOAD_ENTRY_UNAVAILABLE")
                await launch.click(timeout=4000)
            self.stage = 1
            self.transition_at = time.monotonic()
            return
        if REFRESH_LOGIN and not self.login_refresh_attempted:
            await self.observe(session, "before-ui-login-refresh")
            login = session.page.locator("#header-login-register-button")
            if await login.count() != 1 or not await login.is_visible():
                raise LoginError("MANAGED_LOGIN_CONTROL_UNAVAILABLE")
            if (await login.inner_text()).strip() != "Log In / Register":
                raise LoginError("MANAGED_LOGIN_CONTROL_UNAVAILABLE")
            self.login_refresh_attempted = True
            self.stage = -3
            return
        if self.stage == -1:
            if time.monotonic() - self.transition_at < 6:
                return
            await self.observe(session, "after-ui-login-refresh")
            if urlsplit(session.page.url).hostname not in {"www.xometry.com", "xometry.com"}:
                raise LoginError("MANUAL_LOGIN_REQUIRED")
            self.stage = 0
            return
        if self.stage == 0:

            def failed(request):
                url = urlsplit(request.url)
                if len(self.result["request_failures"]) < 25:
                    self.result["request_failures"].append({"host": url.hostname, "path": url.path, "kind": request.resource_type})
                    self.save()

            def response_seen(response):
                if response.status >= 400 and len(self.result["response_failures"]) < 25:
                    url = urlsplit(response.url)
                    self.result["response_failures"].append({"host": url.hostname, "path": url.path, "status": response.status})
                    self.save()

            session.page.on("requestfailed", failed)
            session.page.on("response", response_seen)
            await self.observe(session, "verified-managed-home")
            use_history = HISTORY or LEGACY_ENTRY
            launch = session.page.locator('a[aria-label^="Configure part "][href^="/quoting/quote/"]').first if use_history else session.page.locator("#dashboard-get-instant-quote-primary")
            if await launch.count() != 1 or not await launch.is_visible():
                raise LoginError("MANAGED_UPLOAD_ENTRY_UNAVAILABLE")
            if not use_history and (await launch.inner_text()).strip() != "Get an Instant Quote":
                raise LoginError("MANAGED_UPLOAD_ENTRY_UNAVAILABLE")
            await self.check_inputs()
            if use_history:
                href = await launch.get_attribute("href")
                if not href or not href.startswith("/quoting/quote/"):
                    raise LoginError("MANAGED_HISTORY_ENTRY_UNAVAILABLE")
                self.pending_target = "https://www.xometry.com" + href
            self.stage = -2
            return
        if time.monotonic() - self.transition_at < 6:
            return
        if LEGACY_ENTRY and self.stage == 1:
            await self.observe(session, "verified-managed-legacy-config")
            account = session.page.locator("#header-my-account-button")
            launch = session.page.locator("#navbar-cta-button")
            if await account.count() != 1 or not await account.is_visible() or await launch.count() != 1 or not await launch.is_visible():
                raise LoginError("MANAGED_UPLOAD_ENTRY_UNAVAILABLE")
            if (await launch.inner_text()).strip() != "Get an Instant Quote":
                raise LoginError("MANAGED_UPLOAD_ENTRY_UNAVAILABLE")
            await self.check_inputs()
            await launch.click(timeout=4000)
            self.stage = 2
            self.transition_at = time.monotonic()
            return
        await self.observe(session, "managed-existing-config" if HISTORY else "managed-primary-uploader")
        self.result.update({"status": "INSPECTED", "identity_match": True, "quote_mutations": 0})
        self.terminal = True
        self.done.set()
        self.save()


async def main():
    manager = None
    inspection = None
    result = {"quote_mutations": 0}
    try:
        repository = QuoteRepository()
        auth = await repository.authorizer.load(1)
        snapshot = await repository.snapshot(auth, 3, 1)
        if snapshot.part_id != 4 or snapshot.payload.sha256 != EXPECTED_HASH or len(snapshot.payload.buffer) != 589942:
            raise LoginError("QUOTE_INPUT_CHANGED")
        await repository.assert_upload_available(snapshot)
        inspection = RouteInspection(repository, auth, snapshot)
        manager = LoginManager(repository=repository.login, idle_seconds=35, lifetime_seconds=110)
        await manager.start(snapshot.account, quote_activity=inspection)
        await asyncio.wait_for(inspection.done.wait(), timeout=115)
        result = inspection.result
    except Exception as error:
        result = inspection.result if inspection is not None else result
        result.update({"status": "STOPPED", "reason": getattr(error, "reason", "MANAGED_ROUTE_PROBE_UNAVAILABLE"), "error_type": type(error).__name__})
    finally:
        if manager is not None:
            await manager.close_all()
        await async_engine.dispose()
    OUTPUT.write_text(json.dumps(redact(result), indent=2), encoding="utf-8")
    print(json.dumps({key: result.get(key) for key in ("status", "reason", "identity_match", "quote_mutations")}))


if __name__ == "__main__":
    asyncio.run(main())
