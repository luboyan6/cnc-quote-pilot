"""Inspect owned Xometry login recovery without uploading or changing a quote.

Run from backend with its existing environment. Output deliberately excludes
request/response bodies, headers, storage, form values and raw error messages.
"""

import argparse
import asyncio
import json
import re
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

from managed_login_probe import EXPECTED_HASH, LoginError, LoginManager, QuoteRepository, async_engine
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.modules.cnc.browser.session import BrowserExecutor
from app.modules.cnc.browser.state import SessionCodec
from app.modules.cnc.login.providers import resolve_provider
from app.utils.crypto_util import CryptoUtil

OUTPUT = Path(__file__).with_name("managed-auth-diagnostic-result.json")
KNOWN_PATHS = frozenset(
    {
        "/",
        "/quoting/home",
        "/quoting/home/",
        "/account/login",
        "/account/login/",
        "/login",
        "/login/",
        "/authorize",
        "/oauth/token",
        "/login/callback",
        "/callback",
        "/u/login/identifier",
        "/u/login/password",
        "/u/login",
        "/u/mfa-otp-challenge",
        "/u/mfa-sms-challenge",
        "/v2/users/me",
        "/api/auth/refresh",
        "/env.js",
    }
)
KNOWN_QUERY_KEYS = frozenset(
    {
        "client_id",
        "redirect_uri",
        "response_type",
        "scope",
        "audience",
        "state",
        "code",
        "error",
        "error_description",
        "returnTo",
        "return_to",
        "prompt",
        "screen_hint",
        "vercel_part_config",
        "initialTab",
        "organization",
        "connection",
        "domain",
        "destination",
        "destinationQuerystring",
    }
)
DOM_FLAGS = """() => {
  const visible = e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden';
  const count = selector => [...document.querySelectorAll(selector)].filter(visible).length;
  const exact = (selector, text) => [...document.querySelectorAll(selector)]
    .some(e => visible(e) && e.textContent.trim() === text);
  const text = document.body?.innerText || '';
  const allowed = ['Sign in to start a new quote.', 'Verify your identity',
    'Please verify you are human', 'Access denied', 'Something went wrong',
    'Wrong email or password.', 'Your account has been blocked',
    'Start a New Quote', 'Dashboard'];
  return {
    ready_state: document.readyState,
    identity_cache_visible_to_page: document.cookie.split(';')
      .some(part => part.trim().split('=', 1)[0] === '_identity_cache'),
    identifier_visible_count: count('input#username[name="username"]'),
    password_visible_count: count('input#password[name="password"]'),
    one_time_code_visible_count: count('input[autocomplete="one-time-code"]'),
    captcha_visible_count: count('iframe[src*="captcha"],iframe[title*="challenge"],iframe[title*="Challenge"],[data-sitekey]'),
    guest_header: exact('#header-login-register-button', 'Log In / Register'),
    account_header: exact('#header-my-account-button', 'My Account'),
    uploader_signin_required: exact('[data-testid="Alert-upload-view-error"]', 'Sign in to start a new quote.'),
    primary_file_input_count: document.querySelectorAll('input[type="file"]').length,
    continue_button_visible_count: [...document.querySelectorAll('button')]
      .filter(e => visible(e) && e.textContent.trim() === 'Continue').length,
    visible_known_messages: allowed.filter(value => text.includes(value))
  };
}"""


def safe_route(value):
    """Keep reviewed route names; unknown token-bearing paths/keys stay omitted."""
    parsed = urlsplit(value)
    keys = {key for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    return {
        "host": parsed.hostname,
        "path": parsed.path if parsed.path in KNOWN_PATHS else "[other-path]",
        "query_keys": sorted(keys & KNOWN_QUERY_KEYS),
        "other_query_key_count": len(keys - KNOWN_QUERY_KEYS),
    }


def exception_category(error):
    if isinstance(error, PlaywrightTimeoutError | TimeoutError):
        return "READ_TIMEOUT"
    if isinstance(error, PlaywrightError):
        message = error.message.lower()
        if any(value in message for value in ("execution context was destroyed", "cannot find context with specified id", "cannot find execution context")):
            return "NAVIGATION_CONTEXT_CHANGED"
        return "PLAYWRIGHT_ERROR"
    return "DOMAIN_OR_OTHER_ERROR"


class Diagnostic:
    def __init__(self, native_entry=False, app_login=False, fresh_context=False):
        self.started = time.monotonic()
        self.session = None
        self.native_entry = native_entry or app_login
        self.app_login = app_login
        self.fresh_context = fresh_context
        filename = "managed-auth-app-login" if app_login else "managed-auth-native-entry" if native_entry else "managed-auth"
        filename += "-fresh-context" if fresh_context else "-diagnostic" if not self.native_entry else ""
        filename += "-result"
        self.output = OUTPUT.with_name(f"{filename}.json")
        if self.native_entry or fresh_context:
            sequence = 2
            while self.output.exists():
                self.output = OUTPUT.with_name(f"{filename}-{sequence}.json")
                sequence += 1
        self.result = {
            "diagnostic_schema": 1,
            "entry_mode": "app-login" if app_login else "native" if native_entry else "existing-provider",
            "fresh_context_requested": fresh_context,
            "evidence_filename": self.output.name,
            "started_at": datetime.now(UTC).isoformat(),
            "config_id": 3,
            "account_id": 1,
            "part_id": 4,
            "quote_mutations": 0,
            "events": [],
            "network_summary": {},
        }

    def save(self):
        self.output.write_text(json.dumps(self.result, indent=2), encoding="utf-8")

    def event(self, kind, **fields):
        # Static-resource traffic cannot consume the DOM/provider/final budget.
        if kind in {"request", "response"}:
            count = self.result.setdefault("ordinary_network_event_count", 0)
            if count >= 80:
                self.result["ordinary_network_events_truncated"] = True
                return
            self.result["ordinary_network_event_count"] = count + 1
        self.result["events"].append({"seconds": round(time.monotonic() - self.started, 3), "kind": kind, **fields})
        self.save()

    def summarize_network(self, kind, resource_type, status=None):
        key = f"{kind}:{resource_type}" + (f":{status}" if status is not None else "")
        summary = self.result["network_summary"]
        summary[key] = summary.get(key, 0) + 1

    def bind(self, session):
        self.session = session
        page = session.page

        def request_seen(request):
            if request.resource_type in {"document", "script", "xhr", "fetch"}:
                route = safe_route(request.url)
                self.summarize_network("request", request.resource_type)
                if route["path"] != "[other-path]":
                    self.event("reviewed_route_request", route=route, resource_type=request.resource_type, method=request.method)
                elif request.resource_type == "document":
                    self.event("request", route=route, resource_type=request.resource_type, method=request.method)

        def response_seen(response):
            request = response.request
            if request.resource_type in {"document", "script", "xhr", "fetch"}:
                route = safe_route(response.url)
                self.summarize_network("response", request.resource_type, response.status)
                if route["path"] != "[other-path]" or response.status >= 400:
                    self.event("reviewed_or_error_response", route=route, status=response.status, resource_type=request.resource_type)
                elif request.resource_type == "document":
                    self.event("response", route=route, status=response.status, resource_type=request.resource_type)

        def request_failed(request):
            self.event("request_failed", route=safe_route(request.url), resource_type=request.resource_type)

        def navigated(frame):
            if frame.parent_frame is None:
                self.event("main_navigation", route=safe_route(frame.url))

        def page_error(error):
            name = getattr(error, "name", "Error")
            self.event("page_error", error_class=name if name in {"Error", "TypeError", "ReferenceError", "SyntaxError", "RangeError", "URIError"} else "OtherError")

        page.context.on("request", request_seen)
        page.context.on("response", response_seen)
        page.context.on("requestfailed", request_failed)
        page.on("framenavigated", navigated)
        page.on("pageerror", page_error)
        self.event("owned_session_attached_before_navigation")

    async def observe(self, stage):
        session = self.session
        if session is None:
            return
        session.check_active()
        deadline = time.monotonic() + 3
        for attempt in range(3):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                async with asyncio.timeout(remaining):
                    await session.page.wait_for_load_state("domcontentloaded", timeout=min(1000, int(remaining * 1000)))
                    flags = await session.page.evaluate(DOM_FLAGS)
                    session.check_active()
                    self.event("dom", stage=stage, route=safe_route(session.page.url), flags=flags)
                    return True
            except TimeoutError:
                self.event("dom_read_transient", stage=stage, reason="READ_TIMEOUT", attempt=attempt + 1)
            except PlaywrightError as error:
                category = exception_category(error)
                self.event("dom_read_transient" if category in {"NAVIGATION_CONTEXT_CHANGED", "READ_TIMEOUT"} else "dom_unavailable", stage=stage, reason=category, attempt=attempt + 1)
                if category not in {"NAVIGATION_CONTEXT_CHANGED", "READ_TIMEOUT"}:
                    raise
            if time.monotonic() < deadline:
                await asyncio.sleep(0.15)
        self.event("dom_unavailable", stage=stage, reason="BOUNDED_READS_EXHAUSTED")
        return False


class DiagnosticExecutor:
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        self.executor = BrowserExecutor(SessionCodec(CryptoUtil), capacity=4)

    @asynccontextmanager
    async def session(self, scope, policy, *, encrypted_state=None):
        try:
            self.diagnostic.result["encrypted_state_restore_used"] = encrypted_state is not None and not self.diagnostic.fresh_context
            state = None if self.diagnostic.fresh_context else encrypted_state
            async with self.executor.session(scope, policy, encrypted_state=state) as session:
                self.diagnostic.bind(session)
                yield session
        finally:
            self.diagnostic.session = None
            self.diagnostic.result["executor_active_count_after_exit"] = self.executor.active_count
            self.diagnostic.save()


class DiagnosticProvider:
    def __init__(self, provider, diagnostic):
        self.provider, self.diagnostic = provider, diagnostic
        self.code, self.policy = provider.code, provider.policy

    async def verify(self, session, username):
        await self.diagnostic.observe("before-identity-and-readiness-check")
        try:
            result = await self.provider.verify(session, username)
        except Exception as error:
            self.diagnostic.event("provider_verify_exception", category=exception_category(error))
            raise
        self.diagnostic.event("identity_and_readiness_result", verified=bool(result))
        await self.diagnostic.observe("after-identity-and-readiness-check")
        return result

    async def submit(self, session, username, password, quote_url):
        await self.diagnostic.observe("before-normal-login-method")
        try:
            if self.diagnostic.native_entry:
                result = await self.native_submit(session, username, password, quote_url)
            else:
                result = await self.provider.submit(session, username, password, quote_url)
        except Exception as error:
            self.diagnostic.event("normal_login_method_exception", category=exception_category(error))
            raise
        self.diagnostic.event("normal_login_method_result", submitted=bool(result))
        await self.diagnostic.observe("after-normal-login-method")
        return result

    async def native_submit(self, session, username, password, quote_url):
        # Current official header source points to xometry.com/login. Prefer the
        # freshly observed native control; never create/repair identity cookies.
        page = session.page
        header = page.locator("#header-login-register-button")
        if self.diagnostic.app_login:
            # Exact deployed redirectToLogin builder for an empty-query www
            # /quoting/home/ entry; no caller-controlled destination is accepted.
            self.diagnostic.event("native_login_entry", observed_header_used=False, reviewed_app_login_builder_used=True)
            await session.goto("https://xometry.com/login?domain=www&destination=%2Fquoting%2Fhome%2F")
        elif await header.count() == 1 and await header.is_visible() and (await header.inner_text()).strip() == "Log In / Register":
            self.diagnostic.event("native_login_entry", observed_header_used=True)
            await header.click(timeout=5000, no_wait_after=True)
        else:
            self.diagnostic.event("native_login_entry", observed_header_used=False)
            await session.goto("https://xometry.com/login")
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            await asyncio.sleep(0.5)
            session.check_active()
            delegate_credentials = False
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=1000)
                session.check_active()
                host = urlsplit(page.url).hostname
                if host == "login.xometry.com":
                    identifier = page.locator('input#username[name="username"]')
                    if await identifier.count() == 1 and await identifier.is_visible():
                        delegate_credentials = bool(await self.diagnostic.observe("native-hosted-identifier-ready"))
                elif host in {"www.xometry.com", "xometry.com"}:
                    flags = await page.evaluate(DOM_FLAGS)
                    session.check_active()
                    if flags["identity_cache_visible_to_page"] and not flags["guest_header"]:
                        if not await self.diagnostic.observe("native-app-return-with-cache-name"):
                            continue
                        verified = await self.provider.verify(session, username)
                        self.diagnostic.event("native_return_identity_and_readiness", verified=bool(verified))
                        return verified
            except PlaywrightError as error:
                category = exception_category(error)
                self.diagnostic.event("native_read_transient" if category in {"NAVIGATION_CONTEXT_CHANGED", "READ_TIMEOUT"} else "native_read_failed", category=category)
                if category not in {"NAVIGATION_CONTEXT_CHANGED", "READ_TIMEOUT"}:
                    raise
                continue
            if delegate_credentials:
                # Credential submission is outside the read-retry block. Never
                # repeat a login mutation after a navigation/read exception.
                self.diagnostic.event("native_hosted_credentials_delegated")
                return await self.provider.submit(session, username, password, quote_url)
        await self.diagnostic.observe("native-entry-bounded-wait-ended")
        return False


class DiagnosticActivity:
    def __init__(self, repository, auth, snapshot, diagnostic, hold_seconds):
        self.repository, self.auth, self.snapshot = repository, auth, snapshot
        self.diagnostic, self.hold_seconds = diagnostic, hold_seconds
        self.activity_id = str(uuid4())
        self.terminal, self.can_input, self.ready_for_step = False, False, True
        self.poll_interval = 1
        self.done = asyncio.Event()
        self.wait_started = None

    async def check_inputs(self):
        await self.repository.validate(self.auth, self.snapshot)

    async def login_state(self, status, reason):
        if status not in {"WAITING_HUMAN", "FAILED", "CLOSED"}:
            return
        self.diagnostic.result.update({"status": status, "reason": reason})
        if self.wait_started is None:
            self.wait_started = time.monotonic()
            await self.diagnostic.observe("owner-final-login-state")
            if status == "WAITING_HUMAN":
                # Observe late callback/hydration once without another login,
                # navigation or mutation; owned READY/persistence is unchanged.
                await asyncio.sleep(5)
                await self.check_inputs()
                await self.diagnostic.observe("owner-waiting-after-five-second-settle")
                session = self.diagnostic.session
                session.check_active()
                provider = resolve_provider(self.snapshot.account.login_url, self.snapshot.account.quote_url)
                try:
                    verified = await provider.verify(session, self.snapshot.account.username)
                    self.diagnostic.result["waiting_settled_identity_readiness_verified"] = bool(verified)
                    self.diagnostic.event("waiting_settled_identity_and_readiness", verified=bool(verified))
                except PlaywrightError as error:
                    self.diagnostic.event("waiting_settled_verification_exception", category=exception_category(error))
            print(json.dumps({"status": status, "reason": reason, "hold_seconds": self.hold_seconds, "quote_mutations": 0}), flush=True)
        if status != "WAITING_HUMAN" or time.monotonic() - self.wait_started >= self.hold_seconds:
            self.terminal = True
            self.done.set()
        self.diagnostic.save()

    async def advance(self, session, provider):
        await self.check_inputs()
        await self.diagnostic.observe("owner-ready-no-quote-action")
        self.diagnostic.result.update({"status": "READY", "reason": "LOGIN_VERIFIED"})
        self.terminal = True
        self.done.set()

    async def finish(self, reason):
        self.diagnostic.result["owner_finish_reason"] = reason
        if "status" not in self.diagnostic.result:
            self.diagnostic.result.update({"status": "STOPPED", "reason": reason})
        self.terminal = True
        self.done.set()
        self.diagnostic.save()


async def main(hold_seconds, native_entry=False, app_login=False, fresh_context=False):
    diagnostic = Diagnostic(native_entry, app_login, fresh_context)
    manager = None
    try:
        repository = QuoteRepository()
        auth = await repository.authorizer.load(1)
        snapshot = await repository.snapshot(auth, 3, 1)
        if snapshot.part_id != 4 or snapshot.payload.sha256 != EXPECTED_HASH or len(snapshot.payload.buffer) != 589942:
            raise LoginError("QUOTE_INPUT_CHANGED")
        diagnostic.result["selected_frozen_file_verified"] = True
        activity = DiagnosticActivity(repository, auth, snapshot, diagnostic, hold_seconds)
        executor = DiagnosticExecutor(diagnostic)

        def provider_resolver(login_url, quote_url):
            return DiagnosticProvider(resolve_provider(login_url, quote_url), diagnostic)

        manager = LoginManager(repository=repository.login, executor=executor, provider_resolver=provider_resolver, idle_seconds=hold_seconds + 90, lifetime_seconds=hold_seconds + 150)
        await manager.start(snapshot.account, quote_activity=activity)
        await asyncio.wait_for(activity.done.wait(), timeout=hold_seconds + 155)
    except Exception as error:
        reason = getattr(error, "reason", None)
        reason_value = getattr(reason, "value", reason)
        safe_reason = reason_value if isinstance(reason_value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}", reason_value) else "MANAGED_AUTH_DIAGNOSTIC_UNAVAILABLE"
        diagnostic.result.update({"status": "STOPPED", "reason": safe_reason})
    finally:
        try:
            if manager is not None:
                await manager.close_all()
            diagnostic.result["manager_cleanup_completed"] = True
        except Exception:
            diagnostic.result["manager_cleanup_completed"] = False
            diagnostic.result.update({"status": "STOPPED", "reason": "MANAGED_AUTH_DIAGNOSTIC_CLEANUP_FAILED"})
        finally:
            try:
                await async_engine.dispose()
                diagnostic.result["database_cleanup_completed"] = True
            except Exception:
                diagnostic.result["database_cleanup_completed"] = False
            diagnostic.result["finished_at"] = datetime.now(UTC).isoformat()
            diagnostic.save()
    print(json.dumps({key: diagnostic.result.get(key) for key in ("status", "reason", "quote_mutations", "manager_cleanup_completed", "executor_active_count_after_exit")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    entry = parser.add_mutually_exclusive_group()
    entry.add_argument("--native-entry", action="store_true", help="Research the reviewed native header login entry instead of the legacy fallback; preserves separate evidence output.")
    entry.add_argument("--app-login", action="store_true", help="Research the deployed redirectToLogin builder for www /quoting/home/; preserves separate evidence output.")
    parser.add_argument(
        "--fresh-context", action="store_true", help="Do not restore state into this guarded research context; keep the original account snapshot and persist state only after verified login."
    )
    parser.add_argument(
        "--hold-seconds", type=int, choices=range(0, 241), default=0, metavar="0..240", help="Keep the same waiting owner alive for this bounded interval; does not add a browser UI or retry login."
    )
    options = parser.parse_args()
    asyncio.run(main(options.hold_seconds, options.native_entry, options.app_login, options.fresh_context))
