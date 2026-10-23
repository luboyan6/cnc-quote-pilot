import asyncio
import sys
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from _support import POLICY, SCOPE, FakeHarness, codec

from app.modules.cnc.browser.contracts import Authentication, AuthStatus
from app.modules.cnc.browser.errors import BrowserStop, Reason
from app.modules.cnc.browser.session import BrowserExecutor
from app.modules.cnc.browser.third_party.egress import BrowserEgressProxy


class OptionalDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_module_import_and_missing_sdk_start_have_fixed_reason(self):
        # Core module is already imported without needing the optional SDK.
        executor = BrowserExecutor(codec())
        with patch.dict(sys.modules, {"playwright.async_api": None}):
            with self.assertRaises(BrowserStop) as failure:
                async with executor.session(SCOPE, POLICY):
                    self.fail("optional SDK absent")
            self.assertEqual(failure.exception.reason, Reason.DEPENDENCY_MISSING)
            self.assertEqual(executor.active_count, 0)


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.harness = FakeHarness()
        self.codec = codec()
        self.executor = BrowserExecutor(self.codec, capacity=2)
        manager_patch = patch("app.modules.cnc.browser.session._playwright_manager", side_effect=self.harness.manager)
        proxy_patch = patch("app.modules.cnc.browser.session.BrowserEgressProxy", side_effect=self.harness.proxy)
        manager_patch.start()
        proxy_patch.start()
        self.addCleanup(manager_patch.stop)
        self.addCleanup(proxy_patch.stop)

    def assert_all_closed(self):
        self.assertEqual(self.executor.active_count, 0)
        for context in self.harness.contexts:
            context.close.assert_awaited_once()
        for browser in self.harness.browsers:
            browser.close.assert_awaited_once()
        for manager in self.harness.managers:
            manager.__aexit__.assert_awaited_once()
        for proxy in self.harness.proxies:
            proxy.close.assert_awaited_once()

    async def test_same_account_exclusive_even_owner_changes_and_other_context_isolated(self):
        async with self.executor.session(SCOPE, POLICY) as first:
            self.assertEqual(self.executor.active_count, 1)
            with self.assertRaises(BrowserStop) as failure:
                async with self.executor.session(replace(SCOPE, owner_id="other-owner"), POLICY):
                    self.fail("same account must be exclusive")
            self.assertEqual(failure.exception.reason, Reason.SESSION_BUSY)
            async with self.executor.session(replace(SCOPE, account_id="second"), POLICY) as second:
                self.assertIsNot(first.page, second.page)
                self.assertIsNot(first._context, second._context)
                self.assertIsNone(self.harness.contexts[1].kwargs["storage_state"])
                self.assertEqual(self.harness.contexts[0].kwargs["service_workers"], "block")
                self.assertFalse(self.harness.contexts[0].kwargs["accept_downloads"])
                self.assertEqual(self.harness.browsers[0].kwargs["proxy"]["bypass"], "<-loopback>")
                with self.assertRaises(BrowserStop) as failure:
                    async with self.executor.session(replace(SCOPE, account_id="third"), POLICY):
                        pass
                self.assertEqual(failure.exception.reason, Reason.CAPACITY)
        self.assert_all_closed()

    async def test_single_consumer_same_loop_and_default_capacity(self):
        default = BrowserExecutor(self.codec)
        async with default.session(SCOPE, POLICY) as session:
            with self.assertRaises(BrowserStop) as failure:
                async with default.session(replace(SCOPE, account_id="another"), POLICY):
                    pass
            self.assertEqual(failure.exception.reason, Reason.CAPACITY)

            async def other_consumer():
                return session.page

            with self.assertRaises(BrowserStop) as failure:
                await asyncio.create_task(other_consumer())
            self.assertEqual(failure.exception.reason, Reason.WRONG_CONSUMER)

        def other_loop():
            async def run():
                async with default.session(SCOPE, POLICY):
                    pass

            return asyncio.run(run())

        with self.assertRaises(BrowserStop) as failure:
            await asyncio.to_thread(other_loop)
        self.assertEqual(failure.exception.reason, Reason.WRONG_CONSUMER)

    async def test_auth_required_export_encrypted_scope_and_indexeddb(self):
        async with self.executor.session(SCOPE, POLICY) as session:
            with self.assertRaises(BrowserStop):
                await session.export_encrypted_state()
            session.confirm_authentication(Authentication(AuthStatus.AUTHENTICATED, SCOPE))
            encrypted = await session.export_encrypted_state()
            self.harness.contexts[0].storage_state.assert_awaited_once_with(indexed_db=True)
        async with self.executor.session(SCOPE, POLICY, encrypted_state=encrypted):
            self.assertEqual(self.harness.contexts[1].kwargs["storage_state"], {"cookies": [], "origins": []})
        with self.assertRaises(BrowserStop) as failure:
            async with self.executor.session(replace(SCOPE, account_id="another"), POLICY, encrypted_state=encrypted):
                pass
        self.assertEqual(failure.exception.reason, Reason.SESSION_INVALID)
        self.assert_all_closed()

    async def test_context_guard_covers_subresource_redirect_and_popup_urls(self):
        for url in ("https://127.0.0.1/metadata", "https://other.example.com/redirected", "http://fixture.example.com/subresource"):
            async with self.executor.session(SCOPE, POLICY) as session:
                context = self.harness.contexts[-1]
                route = SimpleNamespace(request=SimpleNamespace(url=url), abort=AsyncMock(), continue_=AsyncMock())
                await context.routes[0](route)
                route.abort.assert_awaited_once_with("blockedbyclient")
                route.continue_.assert_not_awaited()
                with self.assertRaises(BrowserStop):
                    session.check_active()
        self.assert_all_closed()

    async def test_redirect_request_event_preserves_policy_stop_without_second_route(self):
        async with self.executor.session(SCOPE, POLICY) as session:
            context = self.harness.contexts[-1]
            observe = context.listeners["request"]
            observe(SimpleNamespace(url="https://fixture.example.com/start"))
            session.check_active()

            async def redirected_goto(*args, **kwargs):
                # SDK emits the redirected request even when routing only
                # intercepted its initial URL. No second route callback here.
                observe(SimpleNamespace(url="https://forbidden.invalid/?token=secret"))
                raise RuntimeError("synthetic network failure token=secret")

            context.page.goto.side_effect = redirected_goto
            with self.assertRaises(BrowserStop) as failure:
                await session.goto("https://fixture.example.com/redirect")
            self.assertEqual(failure.exception.reason, Reason.POLICY_BLOCKED)
            self.assertNotIn("secret", str(failure.exception))
            with self.assertRaises(BrowserStop):
                session.check_active()
        self.assert_all_closed()

    async def test_actions_validate_before_navigation_and_websockets_blocked(self):
        async with self.executor.session(SCOPE, POLICY) as session:
            with self.assertRaises(BrowserStop):
                await session.goto("https://127.0.0.1/?secret")
            session.page.goto.assert_not_awaited()
            await session.goto("https://fixture.example.com/")
            session.page.goto.assert_awaited_once()
            socket_route = SimpleNamespace(close=AsyncMock())
            await self.harness.contexts[-1].websocket_routes[0](socket_route)
            socket_route.close.assert_awaited_once_with(code=1008, reason="policy_blocked")
        self.assert_all_closed()

    async def test_failure_during_launch_and_body_is_sanitized_resources_released(self):
        self.harness.launch_error = RuntimeError("password=secret")
        with self.assertRaises(BrowserStop) as failure:
            async with self.executor.session(SCOPE, POLICY):
                pass
        self.assertEqual(str(failure.exception), "browser_failed")
        self.assert_all_closed()

    async def test_constructor_failure_never_reserves_account_and_next_session_succeeds(self):
        with patch("app.modules.cnc.browser.session.BrowserEgressProxy", side_effect=RuntimeError("secret constructor failure")):
            with self.assertRaises(BrowserStop) as failure:
                async with self.executor.session(SCOPE, POLICY):
                    self.fail("constructor failed")
            self.assertEqual(failure.exception.reason, Reason.BROWSER_FAILED)
            self.assertNotIn("secret", str(failure.exception))
            self.assertEqual(self.executor.active_count, 0)
        async with self.executor.session(SCOPE, POLICY):
            self.assertEqual(self.executor.active_count, 1)
        self.assert_all_closed()

    async def test_body_error_and_close_failure_still_release_all_resources(self):
        with self.assertRaises(BrowserStop) as failure:
            async with self.executor.session(SCOPE, POLICY):
                self.harness.contexts[-1].close.side_effect = OSError("cookie=secret")
                raise RuntimeError("url?token=secret")
        self.assertEqual(str(failure.exception), "browser_failed")
        self.assertIn("browser_cleanup_failed", failure.exception.__notes__)
        self.assert_all_closed()

    async def test_close_failure_is_explicit_without_body_failure(self):
        with self.assertRaises(BrowserStop) as failure:
            async with self.executor.session(SCOPE, POLICY):
                self.harness.contexts[-1].close.side_effect = OSError("secret")
        self.assertEqual(failure.exception.reason, Reason.CLEANUP_FAILED)
        self.assert_all_closed()

    async def test_proxy_transport_close_timeout_is_visible_and_other_resources_close(self):
        async def never_closed():
            await asyncio.Event().wait()

        proxy = BrowserEgressProxy(POLICY.resolve)
        server = SimpleNamespace(close=Mock(), wait_closed=AsyncMock(side_effect=never_closed))
        with (
            patch("app.modules.cnc.browser.session.BrowserEgressProxy", return_value=proxy),
            patch.object(proxy, "start", new_callable=AsyncMock, return_value="socks5://127.0.0.1:12345"),
            patch.object(proxy, "_server", server),
            patch("app.modules.cnc.browser.third_party.egress._CLOSE_TIMEOUT_S", 0.01),
        ):
            with self.assertRaises(BrowserStop) as failure:
                async with asyncio.timeout(1):
                    async with self.executor.session(SCOPE, POLICY):
                        pass
            self.assertEqual(failure.exception.reason, Reason.CLEANUP_FAILED)
        server.close.assert_called_once()
        server.wait_closed.assert_awaited_once()
        self.assert_all_closed()

    async def test_cancellation_during_cleanup_still_finishes_every_close(self):
        close_started = asyncio.Event()
        release_close = asyncio.Event()

        async def run():
            async with self.executor.session(SCOPE, POLICY):

                async def slow_close():
                    close_started.set()
                    await release_close.wait()

                self.harness.contexts[-1].close.side_effect = slow_close

        task = asyncio.create_task(run())
        async with asyncio.timeout(2):
            await close_started.wait()
        task.cancel()
        release_close.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assert_all_closed()

    async def test_completed_cleanup_failure_is_reported_when_consumer_is_cancelled(self):
        async def run():
            consumer = asyncio.current_task()
            assert consumer is not None
            async with self.executor.session(SCOPE, POLICY):

                async def failing_close():
                    consumer.cancel()
                    raise OSError("secret close failure")

                self.harness.contexts[-1].close.side_effect = failing_close

        with self.assertRaises(asyncio.CancelledError) as failure:
            await asyncio.create_task(run())
        self.assertIn("browser_cleanup_failed", failure.exception.__notes__)
        self.assert_all_closed()

    async def test_cancellation_during_launch_and_during_body_cleans_resources(self):
        for phase in ("launch", "body"):
            with self.subTest(phase=phase):
                self.harness.launch_wait = asyncio.Event() if phase == "launch" else None
                entered = asyncio.Event()

                async def run(entered=entered):
                    async with self.executor.session(SCOPE, POLICY):
                        entered.set()
                        await asyncio.Event().wait()

                task = asyncio.create_task(run())
                async with asyncio.timeout(2):
                    if phase == "body":
                        await entered.wait()
                    else:
                        while not self.harness.managers:
                            await asyncio.sleep(0)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assert_all_closed()
