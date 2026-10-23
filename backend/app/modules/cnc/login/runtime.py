"""One browser owner task, serial bounded commands, fenced persistence."""

import asyncio
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

from app.modules.cnc.browser.contracts import Authentication, AuthStatus, SessionScope
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.browser.session import BrowserExecutor, finish_cleanup
from app.modules.cnc.browser.state import SessionCodec
from app.utils.crypto_util import CryptoUtil

from .contracts import AccountSnapshot, LoginError, LoginInput, LoginStatus, LoginView
from .providers import resolve_provider
from .repository import LoginRepository


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
    last_input: float = 0

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

    async def start(self, account: AccountSnapshot):
        provider = self.provider_resolver(account.login_url, account.quote_url)
        async with self._lock:
            owned = self.accounts.get(account.id)
            if owned and owned.task and not owned.task.done() and owned.status in {"CLOSED", "FAILED"}:
                # Terminal status can precede the final lease release. Never reuse
                # a context that is closing or race a new claim against it.
                await finish_cleanup(owned.task)
                owned = None
            if owned and owned.task and not owned.task.done():
                self._check(owned, account)
                owned.reused = True
            else:
                # Bound retained terminal views as well as active contexts.
                for sid, old in list(self.sessions.items()):
                    if old.task and old.task.done():
                        self.sessions.pop(sid, None)
                owned = OwnedSession(account)
                owned.expires_at = datetime.now(UTC) + timedelta(seconds=self.lifetime_seconds)
                owned.token = await self.repository.claim(account, owned.owner)
                self.sessions[owned.session_id] = owned
                self.accounts[account.id] = owned
                owned.task = asyncio.create_task(self._run(owned, provider), name="cnc-login-owner")
                return owned.view()
        if owned.status == "READY":
            return await self.command(account, owned.session_id, "verify")
        return owned.view()

    def _check(self, owned, account):
        if owned.account.id != account.id or owned.account.actor_id != account.actor_id:
            raise LoginError("SESSION_UNAVAILABLE")
        if owned.account.revision != account.revision:
            if owned.task:
                owned.task.cancel()
            raise LoginError("ACCOUNT_CHANGED")

    async def command(self, account: AccountSnapshot, session_id: str, kind: str, payload: LoginInput | None = None):
        owned = self.sessions.get(session_id)
        if owned is None:
            raise LoginError("SESSION_UNAVAILABLE_ON_THIS_WORKER")
        self._check(owned, account)
        if kind == "close":
            await self._close(owned)
            return owned.view()
        if owned.task is None or owned.task.done():
            if kind == "status":
                return owned.view()
            raise LoginError("SESSION_CLOSED")
        if kind == "status" and owned.status in {"STARTING", "AUTHENTICATING"}:
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
        if not await provider.verify(session, owned.account.username):
            owned.status, owned.reason = "WAITING_HUMAN", "LOGIN_IDENTITY_VERIFICATION_REQUIRED"
            return
        session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, session.scope))
        await self.repository.renew(owned.account, owned.owner, owned.token)
        await session.goto(owned.account.quote_url)
        if not await provider.verify(session, owned.account.username):
            session.invalidate_authentication()
            owned.status, owned.reason = "WAITING_HUMAN", "QUOTE_PAGE_IDENTITY_REQUIRED"
            return
        ciphertext = await session.export_encrypted_state()
        await self.repository.renew(owned.account, owned.owner, owned.token, state=ciphertext)
        owned.status, owned.reason = "READY", "LOGIN_VERIFIED"

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
                await self.repository.renew(owned.account, owned.owner, owned.token)
                await session.goto(owned.account.quote_url)
                await self._verify(owned, session, provider)
                if owned.status != "READY":
                    owned.status, owned.reason = "AUTHENTICATING", "LOGGING_IN"
                    await self.repository.renew(owned.account, owned.owner, owned.token)
                    await session.goto(owned.account.login_url)
                    # Provider controls are reviewed code, never dynamically supplied.
                    if owned.account.login_method == "PASSWORD" and owned.account.password:
                        await self.repository.renew(owned.account, owned.owner, owned.token)
                        try:
                            async with asyncio.timeout(25):
                                submitted = await provider.submit(session, owned.account.username, owned.account.password, owned.account.quote_url)
                        except TimeoutError:
                            raise LoginError("LOGIN_ATTEMPT_UNCONFIRMED") from None
                        if submitted:
                            await self._verify(owned, session, provider)
                        else:
                            owned.status, owned.reason = "WAITING_HUMAN", "PROVIDER_VERIFICATION_REQUIRED"
                    else:
                        owned.status, owned.reason = "WAITING_HUMAN", "MANUAL_LOGIN_REQUIRED"
                while True:
                    remaining = self.idle_seconds - (time.monotonic() - owned.activity)
                    if remaining <= 0:
                        owned.reason = "SESSION_IDLE_EXPIRED"
                        break
                    await self.repository.renew(owned.account, owned.owner, owned.token)
                    try:
                        pending = await asyncio.wait_for(owned.queue.get(), timeout=min(15, remaining))
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
                                owned.activity = time.monotonic()
                                await self._input(session, payload)
                                result = owned.view()
                            elif kind == "verify":
                                owned.activity = time.monotonic()
                                await self._verify(owned, session, provider)
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
            if self.accounts.get(owned.account.id) is owned:
                self.accounts.pop(owned.account.id, None)
            owned.account = replace(owned.account, password="", encrypted_state=None)

    @staticmethod
    async def _input(session, command):
        page = session.page
        if command.kind == "click":
            await page.mouse.click(command.x, command.y)
        elif command.kind == "scroll":
            await page.mouse.wheel(command.delta_x or 0, command.delta_y)
        elif command.kind == "key":
            await page.keyboard.press(command.key)
        elif command.kind == "text":
            await page.keyboard.insert_text(command.text)
        session.check_active()

    async def _close(self, owned):
        if owned.task and not owned.task.done():
            owned.task.cancel()
            try:
                await finish_cleanup(owned.task)
            except (asyncio.CancelledError, BrowserStop):
                # A coroutine cancelled before first execution has no finally.
                await finish_cleanup(self.repository.release(owned.account, owned.owner, owned.token))
                if self.accounts.get(owned.account.id) is owned:
                    self.accounts.pop(owned.account.id, None)
                owned.status, owned.reason = "CLOSED", "SESSION_CLOSED"
                owned.account = replace(owned.account, password="", encrypted_state=None)

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
