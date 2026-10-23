"""Isolated owner-task tests; no platform credentials or site-wide fixtures."""

import asyncio
import sys
import unittest
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.modules.cnc.browser.contracts import SessionScope
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.policy import BrowserPolicy
from app.modules.cnc.login.contracts import AccountSnapshot, LoginError, LoginInput
from app.modules.cnc.login.runtime import LoginManager

ACCOUNT = AccountSnapshot(12, 3, 3, 2, "Synthetic", "sample@example.com", "synthetic-password", "PASSWORD", "https://fixture.example.com/login", "https://fixture.example.com/quote", "revision1", None)


class FakeRepository:
    def __init__(self):
        self.claims = 0
        self.releases = []
        self.states = []
        self.lost = False

    async def claim(self, account, owner):
        self.claims += 1
        return self.claims

    async def renew(self, account, owner, token, *, state=None):
        if self.lost:
            raise LoginError("ACCOUNT_CHANGED_OR_LEASE_LOST")
        if state:
            self.states.append(state)

    async def release(self, account, owner, token):
        self.releases.append((account.id, owner, token))


class FakeExecutor:
    def __init__(self):
        self.active = 0
        self.sessions = []
        self.pause: asyncio.Event | None = None
        self.page = None

    @asynccontextmanager
    async def session(self, scope, policy, encrypted_state=None):
        self.active += 1
        owner = asyncio.current_task()
        page = SimpleNamespace(
            set_viewport_size=AsyncMock(),
            on=lambda *args: None,
            screenshot=AsyncMock(return_value=b"\xff\xd8synthetic-jpeg\xff\xd9"),
            mouse=SimpleNamespace(click=AsyncMock(), wheel=AsyncMock()),
            keyboard=SimpleNamespace(press=AsyncMock(), insert_text=AsyncMock()),
        )
        self.page = page

        def check():
            if asyncio.current_task() is not owner:
                raise BrowserStop(Reason.WRONG_CONSUMER)

        async def goto(url):
            check()
            if self.pause:
                await self.pause.wait()

        async def export():
            check()
            return "encrypted-synthetic-state"

        session = SimpleNamespace(page=page, scope=scope, check_active=check, goto=goto, invalidate_authentication=check, confirm_authentication=lambda auth: check(), export_encrypted_state=export)
        self.sessions.append(session)
        try:
            yield session
        finally:
            self.active -= 1


class SanitizingExecutor(FakeExecutor):
    """Match the shared executor's exception boundary without starting Chromium."""

    @asynccontextmanager
    async def session(self, scope, policy, encrypted_state=None):
        try:
            async with super().session(scope, policy, encrypted_state) as session:
                yield session
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            reason = exc.reason if isinstance(exc, BrowserStop) else Reason.BROWSER_FAILED
            raise BrowserStop(reason) from None


class FakeProvider:
    code = "synthetic"
    policy = BrowserPolicy(frozenset({"fixture.example.com"}))

    def __init__(self, authenticated=False, challenge=False):
        self.authenticated = authenticated
        self.challenge = challenge
        self.submissions = 0
        self.verifications = 0

    async def verify(self, session, username):
        session.check_active()
        self.verifications += 1
        return self.authenticated

    async def submit(self, session, username, password, quote_url):
        session.check_active()
        self.submissions += 1
        self.authenticated = not self.challenge
        return True


async def settled(manager, view):
    for _ in range(100):
        owned = manager.sessions[view.session_id]
        if owned.status not in {"STARTING", "AUTHENTICATING"}:
            return owned.view()
        await asyncio.sleep(0.005)
    raise AssertionError("Owner did not settle")


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repo = FakeRepository()
        self.executor = FakeExecutor()
        self.provider = FakeProvider()
        self.manager = LoginManager(self.repo, self.executor, lambda *_: self.provider)

    async def asyncTearDown(self):
        await self.manager.close_all()

    async def test_expired_session_submits_once_then_reuses_without_submission(self):
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        self.assertEqual(view.status, "READY")
        self.assertEqual(self.provider.submissions, 1)
        duplicate = await self.manager.start(ACCOUNT)
        self.assertTrue(duplicate.reused)
        self.assertEqual(duplicate.session_id, view.session_id)
        self.assertEqual(self.provider.submissions, 1)
        self.assertEqual(self.repo.claims, 1)
        self.assertNotIn(ACCOUNT.password, view.model_dump_json())
        self.assertNotIn(ACCOUNT.username, view.model_dump_json())

    async def test_valid_identity_skips_credentials_and_saves_encrypted_state(self):
        self.provider.authenticated = True
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        self.assertEqual(view.status, "READY")
        self.assertEqual(self.provider.submissions, 0)
        self.assertEqual(self.repo.states, ["encrypted-synthetic-state"])
        frame = await self.manager.command(ACCOUNT, view.session_id, "frame")
        assert isinstance(frame, bytes)
        self.assertTrue(frame.startswith(b"\xff\xd8"))

    async def test_challenge_never_succeeds_until_actual_identity_verified(self):
        self.provider.challenge = True
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        self.assertEqual(view.status, "WAITING_HUMAN")
        again = await self.manager.command(ACCOUNT, view.session_id, "verify")
        self.assertEqual(again.status, "WAITING_HUMAN")
        self.assertFalse(self.repo.states)
        self.assertEqual(self.provider.submissions, 1)
        self.provider.authenticated = True
        verified = await self.manager.command(ACCOUNT, view.session_id, "verify")
        self.assertEqual(verified.status, "READY")

    async def test_actor_and_account_isolation(self):
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        for other in (replace(ACCOUNT, actor_id=4), replace(ACCOUNT, id=99)):
            with self.assertRaisesRegex(LoginError, "SESSION_UNAVAILABLE"):
                await self.manager.command(other, view.session_id, "frame")
        self.assertEqual(self.executor.active, 1)

    async def test_changed_credentials_cancel_context(self):
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        with self.assertRaisesRegex(LoginError, "ACCOUNT_CHANGED"):
            await self.manager.command(replace(ACCOUNT, revision="new-revision"), view.session_id, "input", LoginInput(kind="text", text="private OTP"))
        await asyncio.wait_for(asyncio.shield(self.manager.sessions[view.session_id].task), timeout=1)
        self.assertEqual(self.executor.active, 0)
        self.assertEqual(self.manager.sessions[view.session_id].account.password, "")

    async def test_immediate_close_releases_prestart_lease_and_can_reopen(self):
        view = await self.manager.start(ACCOUNT)
        closed = await self.manager.command(ACCOUNT, view.session_id, "close")
        self.assertEqual(closed.status, "CLOSED")
        self.assertEqual(len(self.repo.releases), 1)
        self.assertFalse(self.manager.accounts)
        await self.manager.start(ACCOUNT)
        self.assertEqual(self.repo.claims, 2)

    async def test_lease_loss_stops_owner_and_settles_command(self):
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        self.repo.lost = True
        try:
            await self.manager.command(ACCOUNT, view.session_id, "verify")
        except LoginError:
            pass
        await asyncio.wait_for(asyncio.shield(self.manager.sessions[view.session_id].task), timeout=1)
        self.assertEqual(self.executor.active, 0)
        self.assertEqual(self.manager.sessions[view.session_id].status, "FAILED")
        self.assertEqual(len(self.repo.releases), 1)

    async def test_input_runs_in_owner_task_and_rate_limits(self):
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        await self.manager.command(ACCOUNT, view.session_id, "input", LoginInput(kind="text", text="private input"))
        self.executor.page.keyboard.insert_text.assert_awaited_once_with("private input")
        with self.assertRaisesRegex(LoginError, "INPUT_RATE_LIMITED"):
            await self.manager.command(ACCOUNT, view.session_id, "input", LoginInput(kind="key", key="Enter"))

    async def test_idle_and_max_lifetime_release_resources(self):
        self.manager.idle_seconds = 0.03
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        await self.manager.command(ACCOUNT, view.session_id, "frame")
        await asyncio.wait_for(asyncio.shield(self.manager.sessions[view.session_id].task), timeout=1)
        self.assertEqual(self.manager.sessions[view.session_id].status, "CLOSED")
        self.assertEqual(self.executor.active, 0)
        self.manager.idle_seconds = 300
        self.manager.lifetime_seconds = 0.03
        view = await self.manager.start(ACCOUNT)
        await asyncio.wait_for(asyncio.shield(self.manager.sessions[view.session_id].task), timeout=1)
        self.assertEqual(self.manager.sessions[view.session_id].reason, "SESSION_LIFETIME_EXPIRED")

    async def test_shutdown_during_navigation_releases_all(self):
        self.executor.pause = asyncio.Event()
        await self.manager.start(ACCOUNT)
        await asyncio.sleep(0.01)
        await self.manager.close_all()
        self.assertEqual(self.executor.active, 0)
        self.assertFalse(self.manager.accounts)
        self.assertEqual(len(self.repo.releases), 1)

    async def test_close_settles_the_current_command_before_returning(self):
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        entered = asyncio.Event()

        async def pending_screenshot(**kwargs):
            entered.set()
            await asyncio.Event().wait()

        self.executor.page.screenshot.side_effect = pending_screenshot
        request = asyncio.create_task(self.manager.command(ACCOUNT, view.session_id, "frame"))
        await asyncio.wait_for(entered.wait(), timeout=1)
        await self.manager.command(ACCOUNT, view.session_id, "close")
        with self.assertRaisesRegex(LoginError, "SESSION_CLOSED"):
            await asyncio.wait_for(request, timeout=0.1)
        self.assertEqual(self.executor.active, 0)
        self.assertEqual(len(self.repo.releases), 1)

    async def test_identity_failure_reason_survives_shared_executor_cleanup(self):
        self.manager.executor = SanitizingExecutor()
        self.provider.verify = AsyncMock(side_effect=LoginError("IDENTITY_MISMATCH"))
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        self.assertEqual((view.status, view.reason), ("FAILED", "IDENTITY_MISMATCH"))
        self.assertEqual(self.provider.submissions, 0)
        self.assertFalse(self.repo.states)
        self.assertEqual(self.manager.executor.active, 0)

    async def test_lease_loss_reason_survives_shared_executor_cleanup(self):
        self.manager.executor = SanitizingExecutor()
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        self.repo.lost = True
        with self.assertRaises(LoginError):
            await self.manager.command(ACCOUNT, view.session_id, "verify")
        await asyncio.wait_for(asyncio.shield(self.manager.sessions[view.session_id].task), timeout=1)
        self.assertEqual(self.manager.sessions[view.session_id].reason, "ACCOUNT_CHANGED_OR_LEASE_LOST")
        self.assertEqual(self.manager.executor.active, 0)

    async def test_unconfirmed_login_never_retries_and_keeps_its_reason(self):
        self.manager.executor = SanitizingExecutor()
        self.provider.submit = AsyncMock(side_effect=TimeoutError)
        view = await settled(self.manager, await self.manager.start(ACCOUNT))
        self.assertEqual((view.status, view.reason), ("FAILED", "LOGIN_ATTEMPT_UNCONFIRMED"))
        self.provider.submit.assert_awaited_once()
        self.assertFalse(self.repo.states)


class InputTests(unittest.TestCase):
    def test_input_rejects_unbounded_and_programmatic_commands(self):
        for data in (
            {"kind": "script", "text": "alert(1)"},
            {"kind": "text", "text": "a" * 257},
            {"kind": "click", "x": 1280, "y": 0},
            {"kind": "key", "key": "Control+L"},
            {"kind": "scroll", "delta_y": 9999},
            {"kind": "click", "x": 2, "y": 3, "text": "secret"},
        ):
            with self.assertRaises(ValueError):
                LoginInput.model_validate(data)

    def test_scope_owner_is_not_actor_override(self):
        scope = SessionScope(str(ACCOUNT.owner_id), "synthetic", str(ACCOUNT.id))
        self.assertEqual(scope.owner_id, "3")
