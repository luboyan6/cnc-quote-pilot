"""Fresh official SDK contexts, same-loop leases and cancellation-safe ownership."""

import asyncio
import platform
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from .contracts import Authentication, AuthStatus, SessionScope
from .errors import BrowserStop, Reason
from .policy import BrowserPolicy
from .state import SessionCodec
from .third_party.egress import BrowserEgressProxy

# Headless Chromium advertises "HeadlessChrome" and `navigator.webdriver=true`.
# Both are unconditional bot signals to a risk-control widget, which then
# forces a slider challenge on every credential submit. The UA is rebuilt from
# the real browser version so it stays consistent with the engine actually used.
_PLATFORM_TOKENS = {
    "Windows": "Windows NT 10.0; Win64; x64",
    "Darwin": "Macintosh; Intel Mac OS X 10_15_7",
    "Linux": "X11; Linux x86_64",
}
_CHROMIUM_ARGS = (
    "--disable-quic",
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--disable-blink-features=AutomationControlled",
)


def desktop_user_agent(version: str) -> str:
    token = _PLATFORM_TOKENS.get(platform.system(), _PLATFORM_TOKENS["Linux"])
    return f"Mozilla/5.0 ({token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"


def _playwright_manager() -> Any:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise BrowserStop(Reason.DEPENDENCY_MISSING) from None
    return async_playwright()


async def finish_cleanup(cleanup: Awaitable[Any]) -> tuple[Any, bool]:
    """Finish even if the consumer is cancelled; never leak an unawaited task."""

    async def run_cleanup() -> Any:
        return await cleanup

    task = asyncio.create_task(run_cleanup())
    cancelled = False
    while True:
        try:
            return await asyncio.shield(task), cancelled
        except asyncio.CancelledError:
            cancelled = True
            if task.done():
                if task.cancelled():
                    raise BrowserStop(Reason.CLEANUP_FAILED) from None
                return task.result(), True


class BrowserSession:
    """Only a trusted adapter gets this object. Do not register it as a model tool."""

    def __init__(self, scope: SessionScope, policy: BrowserPolicy, codec: SessionCodec) -> None:
        self.scope = scope
        self.policy = policy
        self._codec = codec
        self._owner = asyncio.current_task()
        self._page: Any = None
        self._context: Any = None
        self._authenticated = False
        self._policy_blocked = False
        self._closed = False

    def check_active(self) -> None:
        if asyncio.current_task() is not self._owner or self._closed:
            raise BrowserStop(Reason.WRONG_CONSUMER)
        if self._policy_blocked:
            raise BrowserStop(Reason.POLICY_BLOCKED)

    @property
    def page(self) -> Any:
        self.check_active()
        return self._page

    def invalidate_authentication(self) -> None:
        self.check_active()
        self._authenticated = False

    def confirm_authentication(self, auth: Authentication) -> None:
        self.check_active()
        self._authenticated = False
        if auth.status == AuthStatus.CHALLENGE:
            raise BrowserStop(Reason.CHALLENGE)
        if auth.status != AuthStatus.AUTHENTICATED:
            raise BrowserStop(Reason.AUTH_REQUIRED)
        if auth.scope != self.scope:
            raise BrowserStop(Reason.IDENTITY_MISMATCH)
        self._authenticated = True

    async def goto(self, url: str) -> None:
        self.check_active()
        self.policy.validate_url(url)
        try:
            await self._page.goto(url, wait_until="domcontentloaded")
            self.check_active()
        except BrowserStop:
            raise
        except Exception:
            raise BrowserStop(Reason.POLICY_BLOCKED if self._policy_blocked else Reason.BROWSER_FAILED) from None

    async def export_encrypted_state(self) -> str:
        self.check_active()
        if not self._authenticated:
            raise BrowserStop(Reason.AUTH_REQUIRED)
        try:
            state = await self._context.storage_state(indexed_db=True)
            self.check_active()
            return self._codec.seal(self.scope, state, self.policy)
        except BrowserStop:
            raise
        except Exception:
            raise BrowserStop(Reason.SESSION_INVALID) from None

    def _observe_request(self, request: Any) -> None:
        # Playwright routing does not run again for every redirected hop. Request
        # events retain the policy stop, while the proxy denies actual egress.
        if self.policy.blocks_optional_resource(request):
            return
        try:
            self.policy.validate_url(request.url)
        except BrowserStop:
            self._policy_blocked = True

    async def _guard_request(self, route: Any) -> None:
        # Context routes cover pages/subresources; the proxy guards connections.
        if self.policy.blocks_optional_resource(route.request):
            await route.abort("blockedbyclient")
            return
        try:
            self.policy.validate_url(route.request.url)
        except BrowserStop:
            self._policy_blocked = True
            await route.abort("blockedbyclient")
        else:
            await route.continue_()

    async def _guard_websocket(self, route: Any) -> None:
        # No WebSocket egress is ever granted. Pages keep a notification socket
        # open for their whole lifetime, so treating that channel as an unknown
        # destination aborted the session of every such page; the socket is
        # refused silently instead and the page continues without live pushes.
        await route.close(code=1008, reason=Reason.POLICY_BLOCKED.value)


class BrowserExecutor:
    """Process-local admission, not a distributed account lease/scheduler.

    Sessions fail fast when busy. Production 02/04 must add persistent account
    leases before using multiple processes. No CDP or persistent profile option.
    """

    def __init__(self, codec: SessionCodec, *, capacity: int = 1, channel: str | None = None, timeout_ms: int = 15_000) -> None:
        if type(capacity) is not int or not 1 <= capacity <= 8 or type(timeout_ms) is not int or not 0 < timeout_ms <= 60_000:
            raise BrowserStop(Reason.INVALID_INPUT)
        if channel not in {None, "chrome"}:
            raise BrowserStop(Reason.INVALID_INPUT)
        self._codec = codec
        self._capacity = capacity
        self._channel = channel
        self._timeout_ms = timeout_ms
        self._loop: asyncio.AbstractEventLoop | None = None
        self._accounts: set[tuple[str, str]] = set()

    @property
    def active_count(self) -> int:
        return len(self._accounts)

    @asynccontextmanager
    async def session(self, scope: SessionScope, policy: BrowserPolicy, *, encrypted_state: str | None = None):
        if not isinstance(scope, SessionScope) or not isinstance(policy, BrowserPolicy):
            raise BrowserStop(Reason.INVALID_INPUT)
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise BrowserStop(Reason.WRONG_CONSUMER)
        self._loop = loop
        account_key = (scope.platform_code, scope.account_id)
        if account_key in self._accounts:
            raise BrowserStop(Reason.SESSION_BUSY)
        if len(self._accounts) >= self._capacity:
            raise BrowserStop(Reason.CAPACITY)
        try:
            lease = BrowserSession(scope, policy, self._codec)
            proxy = BrowserEgressProxy(policy.resolve)
        except Exception:
            raise BrowserStop(Reason.BROWSER_FAILED) from None
        self._accounts.add(account_key)  # No await between check, construction and admission.
        manager = browser = context = None
        failure: BaseException | None = None
        cleanup_errors = False

        async def cleanup() -> bool:
            failed = False
            closers: list[Callable[[], Awaitable[Any]]] = []
            if context is not None:
                closers.append(context.close)
            if browser is not None:
                closers.append(browser.close)
            if manager is not None:
                manager_exit = manager.__aexit__
                closers.append(lambda: manager_exit(None, None, None))
            closers.append(proxy.close)
            for close in closers:
                try:
                    async with asyncio.timeout(5):
                        await close()
                except BaseException:
                    # Each resource still gets a bounded independent close attempt.
                    failed = True
            return failed

        try:
            state = self._codec.open(scope, encrypted_state, policy) if encrypted_state is not None else None
            proxy_url = await proxy.start()
            manager = _playwright_manager()
            playwright = await manager.start()
            browser = await playwright.chromium.launch(
                headless=True,
                channel=self._channel,
                proxy={"server": proxy_url, "bypass": "<-loopback>"},
                args=list(_CHROMIUM_ARGS),
            )
            context_options: dict[str, Any] = {"storage_state": state, "service_workers": "block", "accept_downloads": False}
            version = getattr(browser, "version", "")
            if isinstance(version, str) and version:
                # Only override when the engine reports its version, so the UA
                # stays consistent with the browser actually launched.
                context_options["user_agent"] = desktop_user_agent(version)
            context = await browser.new_context(**context_options)
            lease._context = context
            context.set_default_timeout(self._timeout_ms)
            context.set_default_navigation_timeout(self._timeout_ms)
            context.on("request", lease._observe_request)
            await context.route("**/*", lease._guard_request)
            await context.route_web_socket("**/*", lease._guard_websocket)
            lease._page = await context.new_page()
            yield lease
        except BaseException as exc:
            failure = exc
        finally:
            try:
                cleanup_errors, cancelled_during_cleanup = await finish_cleanup(cleanup())
                if cancelled_during_cleanup and failure is None:
                    failure = asyncio.CancelledError()
            finally:
                lease._closed = True
                lease._authenticated = False
                lease._page = lease._context = None
                self._accounts.discard(account_key)
        if failure is not None:
            if isinstance(failure, asyncio.CancelledError):
                if cleanup_errors:
                    failure.add_note(Reason.CLEANUP_FAILED.value)
                raise failure
            reason = failure.reason if isinstance(failure, BrowserStop) else Reason.BROWSER_FAILED
            safe_failure = BrowserStop(reason)
            if cleanup_errors:
                safe_failure.add_note(Reason.CLEANUP_FAILED.value)
            raise safe_failure from None
        if cleanup_errors:
            raise BrowserStop(Reason.CLEANUP_FAILED)
