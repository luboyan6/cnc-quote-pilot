"""One browser owner task, serial bounded commands, fenced persistence."""

import asyncio
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.modules.cnc.browser.contracts import Authentication, AuthStatus, SessionScope
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.browser.session import BrowserExecutor, finish_cleanup
from app.modules.cnc.browser.state import SessionCodec
from app.utils.crypto_util import CryptoUtil

from .contracts import AccountSnapshot, LoginError, LoginInput, LoginStatus, LoginView
from .providers import resolve_provider
from .repository import LoginRepository

if TYPE_CHECKING:
    from app.modules.cnc.quote.contracts import ExportDeclarationDecision


def masked_username(username: str) -> str:
    if "@" in username:
        local, domain = username.rsplit("@", 1)
        return local[:2] + "***@" + domain
    return username[:2] + "***" + username[-2:] if len(username) > 4 else "***"


@asynccontextmanager
async def _login_browser_session(executor, scope, policy, encrypted_state):
    """Carry only fixed login failures across the shared SDK cleanup boundary."""
    failure = None
    async with executor.session(scope, policy, encrypted_state=encrypted_state) as session:
        try:
            yield session
        except LoginError as exc:
            # The executor sanitizes foreign exceptions. Finish its cleanup with
            # a normal exit, then restore this already secret-free domain error.
            failure = exc
    if failure is not None:
        raise failure


@dataclass(repr=False)
class OwnedSession:
    account: AccountSnapshot
    session_id: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    owner: str = field(default_factory=lambda: secrets.token_hex(24))
    token: int = 0
    status: LoginStatus = "STARTING"
    reason: str = "BROWSER_STARTING"
    reused: bool = False
    created: float = field(default_factory=time.monotonic)
    activity: float = field(default_factory=time.monotonic)
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC) + timedelta(minutes=30))
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=16))
    task: asyncio.Task | None = None
    close_task: asyncio.Task | None = None
    last_input: float = 0
    quote_activity: Any = None
    # A credential submit keeps the owner task for up to 25 s. Status polls must
    # observe that state instead of queueing behind it and timing out.
    busy: bool = False

    def view(self):
        return LoginView(
            session_id=self.session_id,
            account_id=self.account.id,
            platform_name=self.account.platform_name,
            username=masked_username(self.account.username),
            status=self.status,
            reason=self.reason,
            reused=self.reused,
            expires_at=self.expires_at,
        )


class LoginManager:
    def __init__(self, repository=None, executor=None, provider_resolver=resolve_provider, *, idle_seconds: float = 300, lifetime_seconds: float = 1800):
        self.repository = repository or LoginRepository()
        self.codec = SessionCodec(CryptoUtil)
        self.executor = executor or BrowserExecutor(self.codec, capacity=4)
        self.provider_resolver = provider_resolver
        self.idle_seconds = idle_seconds
        self.lifetime_seconds = lifetime_seconds
        self.sessions: dict[str, OwnedSession] = {}
        self.accounts: dict[int, OwnedSession] = {}
        self._lock = asyncio.Lock()

    async def start(self, account: AccountSnapshot, *, quote_activity=None, lease=None):
        provider = self.provider_resolver(account.login_url, account.quote_url)
        async with self._lock:
            owned = self.accounts.get(account.id)
            if owned and owned.close_task and not owned.close_task.done():
                await finish_cleanup(owned.close_task)
                owned = None
            if owned and owned.task and not owned.task.done() and (owned.status in {"CLOSED", "FAILED"} or (owned.quote_activity is not None and owned.quote_activity.terminal)):
                # Terminal status can precede the final lease release. Never reuse
                # a context that is closing or race a new claim against it.
                await finish_cleanup(owned.task)
                owned = None
            if owned and owned.task and not owned.task.done():
                self._check(owned, account)
                if owned.quote_activity is not None:
                    raise LoginError("ACCOUNT_BUSY")
                if quote_activity is not None:
                    owned.quote_activity = quote_activity
                    # Wake the owner rather than using Page from this task.
                    future = asyncio.get_running_loop().create_future()
                    future.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
                    try:
                        owned.queue.put_nowait(("status", None, future))
                    except asyncio.QueueFull:
                        owned.quote_activity = None
                        raise LoginError("SESSION_QUEUE_FULL") from None
                owned.reused = True
            else:
                # Bound retained terminal views as well as active contexts.
                for sid, old in list(self.sessions.items()):
                    if old.task and old.task.done():
                        self.sessions.pop(sid, None)
                owned = OwnedSession(account, quote_activity=quote_activity)
                owned.expires_at = datetime.now(UTC) + timedelta(seconds=self.lifetime_seconds)
                if lease is None:
                    owned.token = await self.repository.claim(account, owned.owner)
                else:
                    owned.owner, owned.token = lease
                self.sessions[owned.session_id] = owned
                self.accounts[account.id] = owned
                owned.task = asyncio.create_task(self._run(owned, provider), name="cnc-login-owner")
                return owned.view()
        if owned.status == "READY" and quote_activity is None:
            return await self.command(account, owned.session_id, "verify")
        return owned.view()

    def _check(self, owned, account):
        if owned.account.id != account.id or owned.account.actor_id != account.actor_id:
            raise LoginError("SESSION_UNAVAILABLE")
        if owned.account.revision != account.revision:
            if owned.task:
                owned.task.cancel()
            raise LoginError("ACCOUNT_CHANGED")

    async def command(self, account: AccountSnapshot, session_id: str, kind: str, payload: "LoginInput | ExportDeclarationDecision | None" = None, *, activity_id: str | None = None):
        owned = self.sessions.get(session_id)
        if owned is None:
            raise LoginError("SESSION_UNAVAILABLE_ON_THIS_WORKER")
        self._check(owned, account)
        if owned.quote_activity is not None and owned.quote_activity.activity_id != activity_id:
            raise LoginError("ACCOUNT_BUSY")
        if owned.quote_activity is None and activity_id is not None:
            raise LoginError("SESSION_UNAVAILABLE")
        if kind == "close":
            await self._close(owned)
            return owned.view()
        if owned.task is None or owned.task.done():
            if kind == "status":
                return owned.view()
            raise LoginError("SESSION_CLOSED")
        if kind == "status" and owned.status in {"STARTING", "AUTHENTICATING"}:
            return owned.view()
        if kind == "status" and owned.busy:
            # The owner is inside a credential submit; report the current phase
            # rather than occupying a queue slot the owner cannot drain yet.
            return owned.view()
        if kind == "frame" and owned.status in {"STARTING", "AUTHENTICATING"}:
            raise LoginError("FRAME_UNAVAILABLE")
        if kind == "input":
            if time.monotonic() - owned.last_input < 0.1:
                raise LoginError("INPUT_RATE_LIMITED")
            owned.last_input = time.monotonic()
        future = asyncio.get_running_loop().create_future()
        try:
            owned.queue.put_nowait((kind, payload, future))
        except asyncio.QueueFull:
            raise LoginError("SESSION_QUEUE_FULL") from None
        try:
            return await asyncio.wait_for(future, timeout=30)
        except TimeoutError:
            raise LoginError("COMMAND_TIMEOUT_NO_RETRY") from None

    async def _verify(self, owned, session, provider):
        await self.repository.renew(owned.account, owned.owner, owned.token)
        session.invalidate_authentication()
        if not await provider.verify(session, owned.account.username, owned.account.identity_code):
            owned.status, owned.reason = "WAITING_HUMAN", "LOGIN_IDENTITY_VERIFICATION_REQUIRED"
            return
        session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, session.scope))
        await self.repository.renew(owned.account, owned.owner, owned.token)
        await session.goto(owned.account.quote_url)
        if not await provider.verify(session, owned.account.username, owned.account.identity_code):
            session.invalidate_authentication()
            owned.status, owned.reason = "WAITING_HUMAN", "QUOTE_PAGE_IDENTITY_REQUIRED"
            return
        ciphertext = await session.export_encrypted_state()
        await self.repository.renew(owned.account, owned.owner, owned.token, state=ciphertext)
        owned.status, owned.reason = "READY", "LOGIN_VERIFIED"

    async def _bind_identity(self, owned, session, provider):
        """Trust on first use: bind the platform account code this submit proved.

        Only reached after a credential submit that the provider accepted, so
        the authenticated session cannot belong to an unrelated visitor. A
        provider whose identity endpoint echoes the login identifier returns no
        code and keeps matching against the stored username.
        """
        if owned.account.identity_code:
            return
        try:
            code = await provider.identify(session)
        except BrowserStop:
            raise
        except Exception:
            # A read racing the login redirect must not fail the whole attempt;
            # `verify` reports the missing identity as a human-action state.
            return
        if not code:
            return
        await self.repository.bind_identity(owned.account, owned.owner, owned.token, code)
        owned.account = replace(owned.account, identity_code=code)

    async def _run(self, owned, provider):
        pending = None
        try:
            scope = SessionScope(str(owned.account.owner_id), provider.code, str(owned.account.id))
            encrypted_state = owned.account.encrypted_state
            if encrypted_state:
                try:
                    self.codec.open(scope, encrypted_state, provider.policy)
                except BrowserStop:
                    encrypted_state = None
            async with asyncio.timeout(self.lifetime_seconds), _login_browser_session(self.executor, scope, provider.policy, encrypted_state) as session:
                await session.page.set_viewport_size({"width": 1280, "height": 720})
                # Unreviewed popups cannot become a second uncontrolled page.
                session.page.on("popup", lambda page: asyncio.create_task(page.close()))
                owned.status, owned.reason = "AUTHENTICATING", "CHECKING_LOGIN"
                if owned.quote_activity is not None:
                    await owned.quote_activity.check_inputs()
                await self.repository.renew(owned.account, owned.owner, owned.token)
                await session.goto(owned.account.quote_url)
                await self._verify(owned, session, provider)
                if owned.status != "READY":
                    owned.status, owned.reason = "AUTHENTICATING", "LOGGING_IN"
                    await self.repository.renew(owned.account, owned.owner, owned.token)
                    await session.goto(owned.account.login_url)
                    # Provider controls are reviewed code, never dynamically supplied.
                    if owned.account.login_method == "PASSWORD" and owned.account.password:
                        if owned.quote_activity is not None:
                            await owned.quote_activity.check_inputs()
                        await self.repository.renew(owned.account, owned.owner, owned.token)
                        owned.busy = True
                        try:
                            async with asyncio.timeout(25):
                                submitted = await provider.submit(session, owned.account.username, owned.account.password, owned.account.quote_url)
                        except TimeoutError:
                            raise LoginError("LOGIN_ATTEMPT_UNCONFIRMED") from None
                        finally:
                            owned.busy = False
                        if submitted:
                            await self._bind_identity(owned, session, provider)
                            await self._verify(owned, session, provider)
                        else:
                            owned.status, owned.reason = "WAITING_HUMAN", "PROVIDER_VERIFICATION_REQUIRED"
                    else:
                        owned.status, owned.reason = "WAITING_HUMAN", "MANUAL_LOGIN_REQUIRED"
                while True:
                    quote = owned.quote_activity
                    if quote is not None:
                        await quote.login_state(owned.status, owned.reason)
                        if quote.terminal:
                            break
                        if owned.status == "READY" and not quote.can_input and quote.ready_for_step:
                            owned.activity = time.monotonic()
                            await self.repository.renew(owned.account, owned.owner, owned.token)
                            # The same owner task retains the Page. Every remote
                            # phase is bounded, with lease renewal between phases.
                            try:
                                async with asyncio.timeout(15):
                                    await quote.advance(session, provider)
                            except TimeoutError:
                                raise LoginError("QUOTE_STAGE_TIMEOUT_NO_RETRY") from None
                            if quote.terminal:
                                break
                    remaining = self.idle_seconds - (time.monotonic() - owned.activity)
                    if remaining <= 0:
                        owned.reason = "SESSION_IDLE_EXPIRED"
                        break
                    await self.repository.renew(owned.account, owned.owner, owned.token)
                    try:
                        interval = quote.poll_interval if quote is not None and owned.status == "READY" and not quote.can_input else 15
                        pending = await asyncio.wait_for(owned.queue.get(), timeout=min(interval, remaining))
                    except TimeoutError:
                        continue
                    kind, payload, future = pending
                    if future.cancelled():
                        pending = None
                        continue
                    try:
                        async with asyncio.timeout(25):
                            session.check_active()
                            if kind == "frame":
                                result = await session.page.screenshot(type="jpeg", quality=65, timeout=8000)
                            elif kind == "input":
                                if quote is not None and (not quote.can_input or not quote.view.can_input):
                                    raise LoginError("QUOTE_MANUAL_INPUT_NOT_ALLOWED")
                                owned.activity = time.monotonic()
                                if quote is None or await quote.allow_manual_input(session):
                                    await self._input(session, payload)
                                result = owned.view()
                            elif kind == "declaration":
                                if quote is None or not quote.can_input or quote.view.export_declaration is None:
                                    raise LoginError("QUOTE_EXPORT_DECLARATION_INVALID")
                                owned.activity = time.monotonic()
                                await quote.declare(session, provider, payload)
                                result = owned.view()
                            elif kind == "verify":
                                owned.activity = time.monotonic()
                                if quote is not None and quote.begun:
                                    await quote.resume(session, provider)
                                else:
                                    await self._verify(owned, session, provider)
                                    if quote is not None:
                                        if owned.status == "READY":
                                            await quote.change("RUNNING", "upload", "QUOTE_CONTINUING")
                                        else:
                                            await quote.login_state(owned.status, owned.reason)
                                result = owned.view()
                            else:
                                result = owned.view()
                        if not future.done():
                            future.set_result(result)
                    except Exception:
                        if not future.done():
                            future.set_exception(LoginError("COMMAND_FAILED_NO_RETRY"))
                        raise
                    finally:
                        # Cancellation is a BaseException: it bypasses the
                        # failure branch but must still settle the active HTTP
                        # command before its queue entry is forgotten.
                        if not future.done():
                            future.set_exception(LoginError("SESSION_CLOSED"))
                        pending = None
        except asyncio.CancelledError:
            owned.reason = "SESSION_CLOSED"
        except TimeoutError:
            owned.reason = "SESSION_LIFETIME_EXPIRED"
        except LoginError as exc:
            owned.status, owned.reason = "FAILED", exc.reason
        except BrowserStop as exc:
            owned.status, owned.reason = "FAILED", exc.reason.value
        except Exception:
            owned.status, owned.reason = "FAILED", "BROWSER_UNAVAILABLE"
        finally:
            if owned.status != "FAILED":
                owned.status = "CLOSED"
            if pending and not pending[2].done():
                pending[2].set_exception(LoginError("SESSION_CLOSED"))
            while not owned.queue.empty():
                _, _, future = owned.queue.get_nowait()
                if not future.done():
                    future.set_exception(LoginError("SESSION_CLOSED"))
            try:
                await finish_cleanup(self.repository.release(owned.account, owned.owner, owned.token))
            except Exception:
                owned.status, owned.reason = "FAILED", "LEASE_RELEASE_FAILED"
            if owned.quote_activity is not None:
                try:
                    await finish_cleanup(owned.quote_activity.finish(owned.reason))
                except Exception:
                    owned.status, owned.reason = "FAILED", "QUOTE_STORAGE_UNAVAILABLE"
            owned.account = replace(owned.account, password="", encrypted_state=None)
            # Keep the owner discoverable until its final quote persistence
            # finishes, so shutdown and a new start both await all cleanup.
            if self.accounts.get(owned.account.id) is owned:
                self.accounts.pop(owned.account.id, None)

    @staticmethod
    async def _input(session, command):
        page = session.page
        if command.kind == "click":
            await page.mouse.click(command.x, command.y)
        elif command.kind == "drag":
            # One press-move-release gesture: a slider cannot be moved by clicks.
            await page.mouse.move(command.x, command.y)
            await page.mouse.down()
            for step in range(1, 13):
                await page.mouse.move(
                    command.x + (command.x2 - command.x) * step / 12,
                    command.y + (command.y2 - command.y) * step / 12,
                )
                await page.wait_for_timeout(16)
            await page.mouse.up()
        elif command.kind == "scroll":
            await page.mouse.wheel(command.delta_x or 0, command.delta_y)
        elif command.kind == "key":
            await page.keyboard.press(command.key)
        elif command.kind == "text":
            await page.keyboard.insert_text(command.text)
        session.check_active()

    async def _close(self, owned):
        # Concurrent close/shutdown calls share one cleanup, including the
        # fallback needed when the owner was cancelled before it first ran.
        if owned.close_task is None:
            owned.close_task = asyncio.create_task(self._close_owned(owned))
        await finish_cleanup(owned.close_task)

    async def _close_owned(self, owned):
        if owned.task:
            if not owned.task.done():
                owned.task.cancel()
            try:
                await finish_cleanup(owned.task)
            except (asyncio.CancelledError, BrowserStop):
                # A coroutine cancelled before first execution has no finally.
                await finish_cleanup(self.repository.release(owned.account, owned.owner, owned.token))
                owned.status, owned.reason = "CLOSED", "SESSION_CLOSED"
                if owned.quote_activity is not None:
                    await finish_cleanup(owned.quote_activity.finish(owned.reason))
                owned.account = replace(owned.account, password="", encrypted_state=None)
                if self.accounts.get(owned.account.id) is owned:
                    self.accounts.pop(owned.account.id, None)

    async def revoke(self, account_id: int):
        owned = self.accounts.get(account_id)
        if owned:
            await self._close(owned)

    async def close_all(self):
        for owned in list(self.accounts.values()):
            await self._close(owned)


_manager: LoginManager | None = None


def get_login_manager():
    global _manager
    if _manager is None:
        _manager = LoginManager()
    return _manager


async def close_login_sessions():
    if _manager is not None:
        await _manager.close_all()
