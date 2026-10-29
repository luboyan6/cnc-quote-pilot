"""Provider identity, egress and credential contracts without live accounts."""

import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.modules.cnc.browser.contracts import SessionScope
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.browser.policy import BrowserPolicy
from app.modules.cnc.browser.session import BrowserSession
from app.modules.cnc.browser.state import SessionCodec
from app.modules.cnc.cnc_account.schema import CncAccountOutSchema
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.credentials import read_credentials, seal_credentials
from app.modules.cnc.login.providers import IDENTITY_FETCH, PROVIDERS, XOMETRY_ASIA_IDENTITY, XOMETRY_POST_LOGIN_READY, XOMETRY_SIGNIN_REQUIRED, LoginProvider, resolve_provider, slider_drag_steps
from app.utils.crypto_util import CryptoUtil


class PolicyTests(unittest.IsolatedAsyncioTestCase):
    def session(self):
        policy = BrowserPolicy(frozenset({"fixture.example.com"}), frozenset({"tracking.example.com"}))
        return BrowserSession(SessionScope("owner", "synthetic", "account"), policy, SessionCodec(CryptoUtil))

    async def test_reviewed_optional_resource_is_aborted_without_granting_egress(self):
        session = self.session()
        request = SimpleNamespace(url="https://tracking.example.com/script", is_navigation_request=lambda: False)
        route = SimpleNamespace(request=request, abort=AsyncMock(), continue_=AsyncMock())
        session._observe_request(request)
        await session._guard_request(route)
        route.abort.assert_awaited_once_with("blockedbyclient")
        route.continue_.assert_not_awaited()
        session.check_active()
        with self.assertRaises(ValueError):
            session.policy.resolve("tracking.example.com")

    async def test_optional_host_cannot_be_used_for_top_level_navigation(self):
        session = self.session()
        request = SimpleNamespace(url="https://tracking.example.com/script", is_navigation_request=lambda: True, frame=SimpleNamespace(parent_frame=None))
        session._observe_request(request)
        with self.assertRaises(BrowserStop):
            session.check_active()
        with self.assertRaises(BrowserStop):
            session.policy.validate_url(request.url)

    async def test_optional_subframe_stays_blocked_but_unknown_resource_stops(self):
        session = self.session()
        request = SimpleNamespace(url="https://tracking.example.com/frame", is_navigation_request=lambda: True, frame=SimpleNamespace(parent_frame=object()))
        session._observe_request(request)
        session.check_active()
        session._observe_request(SimpleNamespace(url="https://unknown.example.com/script", is_navigation_request=lambda: False))
        with self.assertRaises(BrowserStop):
            session.check_active()


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    def xometry_form(self, url="https://www.xometry.com/quoting/home/"):
        identifier = SimpleNamespace(count=AsyncMock(return_value=1), wait_for=AsyncMock(), is_visible=AsyncMock(return_value=True), fill=AsyncMock())
        password = SimpleNamespace(count=AsyncMock(return_value=1), wait_for=AsyncMock(), is_visible=AsyncMock(return_value=True), fill=AsyncMock())
        identifier.first = identifier
        password.first = password
        button = SimpleNamespace(click=AsyncMock())
        controls = {'input#username[name="username"]': identifier, 'input#password[name="password"]': password}
        page = SimpleNamespace(url=url, locator=lambda selector: controls[selector], get_by_role=lambda *args, **kwargs: button)

        async def hosted_entry(_url):
            page.url = "https://login.xometry.com/u/login/identifier"

        session = SimpleNamespace(page=page, check_active=lambda: None, goto=AsyncMock(side_effect=hosted_entry))
        return session, identifier, password, button

    async def test_xometry_uses_current_native_login_entry_and_submits_credentials_once(self):
        session, identifier, password, button = self.xometry_form()
        reconcile = AsyncMock(return_value=True)
        with patch.object(LoginProvider, "_reconcile_xometry_login", new=reconcile):
            self.assertTrue(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", "https://www.xometry.com/quoting/home/"))
        session.goto.assert_awaited_once_with("https://xometry.com/login")
        identifier.fill.assert_awaited_once_with("owner@example.com")
        password.fill.assert_awaited_once_with("synthetic-password")
        self.assertEqual(button.click.await_count, 2)
        self.assertTrue(all(call.kwargs == {"timeout": 8000, "no_wait_after": True} for call in button.click.await_args_list))
        reconcile.assert_awaited_once_with(session, "owner@example.com")

    async def test_xometry_already_hosted_identifier_form_is_reused_without_navigation(self):
        session, identifier, password, button = self.xometry_form("https://login.xometry.com/u/login/identifier")
        with patch.object(LoginProvider, "_reconcile_xometry_login", new=AsyncMock(return_value=True)):
            self.assertTrue(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", "https://www.xometry.com/quoting/home/"))
        session.goto.assert_not_awaited()
        identifier.fill.assert_awaited_once()
        password.fill.assert_awaited_once()
        self.assertEqual(button.click.await_count, 2)

    async def test_xometry_native_entry_without_hosted_redirect_does_not_submit_credentials(self):
        session, identifier, password, button = self.xometry_form()
        session.goto.side_effect = None
        reconcile = AsyncMock(return_value=True)
        with patch.object(LoginProvider, "_reconcile_xometry_login", new=reconcile):
            self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", session.page.url))
        session.goto.assert_awaited_once_with("https://xometry.com/login")
        identifier.fill.assert_not_awaited()
        password.fill.assert_not_awaited()
        button.click.assert_not_awaited()
        reconcile.assert_not_awaited()

    async def test_xometry_missing_ambiguous_or_hidden_identifier_preserves_manual_state(self):
        for count, visible in ((0, True), (2, True), (1, False)):
            with self.subTest(count=count, visible=visible):
                session, identifier, password, button = self.xometry_form()
                identifier.count.return_value = count
                identifier.is_visible.return_value = visible
                reconcile = AsyncMock(return_value=True)
                with patch.object(LoginProvider, "_reconcile_xometry_login", new=reconcile):
                    self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", session.page.url))
                session.goto.assert_awaited_once_with("https://xometry.com/login")
                identifier.fill.assert_not_awaited()
                password.fill.assert_not_awaited()
                button.click.assert_not_awaited()
                reconcile.assert_not_awaited()

    async def test_xometry_unavailable_or_ambiguous_password_never_repeats_identifier(self):
        for count, timeout in ((1, True), (0, False), (2, False)):
            with self.subTest(count=count, timeout=timeout):
                session, identifier, password, button = self.xometry_form()
                password.count.return_value = count
                if timeout:
                    password.wait_for.side_effect = PlaywrightTimeoutError("synthetic hosted challenge")
                reconcile = AsyncMock(return_value=True)
                with patch.object(LoginProvider, "_reconcile_xometry_login", new=reconcile):
                    self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", session.page.url))
                session.goto.assert_awaited_once_with("https://xometry.com/login")
                identifier.fill.assert_awaited_once_with("owner@example.com")
                password.fill.assert_not_awaited()
                button.click.assert_awaited_once_with(timeout=8000, no_wait_after=True)
                reconcile.assert_not_awaited()

    async def test_xometry_native_entry_password_click_timeout_reconciles_without_resubmission(self):
        session, identifier, password, button = self.xometry_form()
        button.click.side_effect = [None, PlaywrightTimeoutError("synthetic callback timeout")]
        reconcile = AsyncMock(return_value=False)
        with patch.object(LoginProvider, "_reconcile_xometry_login", new=reconcile):
            self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", session.page.url))
        session.goto.assert_awaited_once_with("https://xometry.com/login")
        identifier.fill.assert_awaited_once_with("owner@example.com")
        password.fill.assert_awaited_once_with("synthetic-password")
        self.assertEqual(button.click.await_count, 2)
        reconcile.assert_awaited_once_with(session, "owner@example.com")

    async def test_identity_matches_exact_server_field_and_uses_guarded_page(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(side_effect=[["OWNER@EXAMPLE.COM"], False]))
        session = SimpleNamespace(page=page, check_active=lambda: None)
        self.assertTrue(await PROVIDERS[0].verify(session, "owner@example.com"))
        self.assertEqual(page.evaluate.await_args_list[0].args[0], IDENTITY_FETCH)
        self.assertEqual(page.evaluate.await_args_list[0].args[1]["url"], "https://api.xometry.com/v2/users/me")
        self.assertEqual(page.evaluate.await_args_list[1].args, (XOMETRY_SIGNIN_REQUIRED,))
        self.assertEqual(page.evaluate.await_count, 2)

    async def test_xometry_guest_shell_can_finish_hydrating_within_identity_retry_budget(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(side_effect=[["owner@example.com"], True, ["owner@example.com"], False]))
        with patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()) as sleep:
            self.assertTrue(await PROVIDERS[0].verify(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com"))
        sleep.assert_awaited_once_with(0.5)
        self.assertEqual(page.evaluate.await_count, 4)

    async def test_xometry_mismatch_during_guest_shell_recheck_still_stops_immediately(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(side_effect=[["owner@example.com"], True, ["different@example.com"]]))
        with patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()) as sleep, self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
            await PROVIDERS[0].verify(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com")
        sleep.assert_awaited_once_with(0.5)
        self.assertEqual(page.evaluate.await_count, 3)

    async def test_other_authenticated_identity_is_not_relogged_or_overwritten(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(return_value=["different@example.com"]))
        with self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
            await PROVIDERS[0].verify(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com")

    async def test_delayed_xometry_login_reconciles_once_without_repeating_credentials_or_navigation(self):
        for outcome in ("returned", "timeout"):
            with self.subTest(outcome=outcome):
                page = SimpleNamespace(url="https://get.xometry.com/", evaluate=AsyncMock(side_effect=[False, True, ["owner@example.com"], False, True]))
                session = SimpleNamespace(page=page, check_active=lambda: None, goto=AsyncMock())

                async def advance_redirect(_seconds, current_page=page):
                    current_page.url = "https://www.xometry.com/quoting/home/"

                submit = AsyncMock(return_value=True, side_effect=PlaywrightTimeoutError("synthetic click navigation timeout") if outcome == "timeout" else None)
                with patch.object(LoginProvider, "_submit", new=submit), patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock(side_effect=advance_redirect)) as sleep:
                    self.assertTrue(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", page.url))
                submit.assert_awaited_once()
                self.assertEqual(sleep.await_count, 2)
                self.assertEqual(page.evaluate.await_args_list[0].args, (XOMETRY_POST_LOGIN_READY,))
                self.assertEqual(page.evaluate.await_count, 5)
                session.goto.assert_not_awaited()

    async def test_unsuccessful_xometry_and_normal_jlc_submissions_keep_their_result(self):
        for provider, expected in ((PROVIDERS[0], False), (PROVIDERS[1], True), (PROVIDERS[1], False)):
            with self.subTest(provider=provider.code, submitted=expected):
                session = SimpleNamespace(page=SimpleNamespace(evaluate=AsyncMock()), check_active=lambda: None, goto=AsyncMock())
                submit = AsyncMock(return_value=expected)
                reconcile = AsyncMock(return_value=True)
                with patch.object(LoginProvider, "_submit", new=submit), patch.object(LoginProvider, "_reconcile_xometry_login", new=reconcile):
                    self.assertEqual(await provider.submit(session, "owner@example.com", "synthetic-password", "https://fixture.example.com/"), expected)
                submit.assert_awaited_once()
                reconcile.assert_not_awaited()
                session.page.evaluate.assert_not_awaited()
                session.goto.assert_not_awaited()

    async def test_quote_shell_regression_during_identity_read_cannot_complete_timed_out_login(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(side_effect=[True, ["owner@example.com"], False, False]))
        session = SimpleNamespace(page=page, check_active=lambda: None, goto=AsyncMock())
        submit = AsyncMock(side_effect=PlaywrightTimeoutError("synthetic timeout"))
        with patch.object(LoginProvider, "_submit", new=submit):
            self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", page.url))
        submit.assert_awaited_once()
        session.goto.assert_not_awaited()

    async def test_timeout_reconciliation_never_accepts_an_unsettled_quote_shell(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(return_value=False))
        session = SimpleNamespace(page=page, check_active=lambda: None, goto=AsyncMock())
        submit = AsyncMock(side_effect=PlaywrightTimeoutError("synthetic timeout"))
        with (
            patch.object(LoginProvider, "_submit", new=submit),
            patch.object(LoginProvider, "verify", new=AsyncMock(return_value=True)) as verify,
            patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()),
        ):
            self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", page.url))
        submit.assert_awaited_once()
        verify.assert_not_awaited()
        self.assertEqual(page.evaluate.await_count, 3)
        session.goto.assert_not_awaited()

    async def test_timeout_reconciliation_stops_on_wrong_account_without_retry(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(side_effect=[True, ["different@example.com"]]))
        submit = AsyncMock(side_effect=PlaywrightTimeoutError("synthetic timeout"))
        with (
            patch.object(LoginProvider, "_submit", new=submit),
            patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()) as sleep,
            self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"),
        ):
            await PROVIDERS[0].submit(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com", "synthetic-password", page.url)
        submit.assert_awaited_once()
        sleep.assert_not_awaited()
        self.assertEqual(page.evaluate.await_count, 2)

    async def test_timeout_read_can_reconcile_a_navigation_context_transition(self):
        page = SimpleNamespace(
            url="https://www.xometry.com/quoting/home/",
            evaluate=AsyncMock(side_effect=[PlaywrightError("Execution context was destroyed, most likely because of a navigation"), True, ["owner@example.com"], False, True]),
        )
        submit = AsyncMock(side_effect=PlaywrightTimeoutError("synthetic timeout"))
        with patch.object(LoginProvider, "_submit", new=submit), patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()) as sleep:
            self.assertTrue(await PROVIDERS[0].submit(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com", "synthetic-password", page.url))
        submit.assert_awaited_once()
        sleep.assert_awaited_once_with(1.5)

    async def test_timeout_never_leaves_hosted_challenge_or_callback_to_find_quote(self):
        for url in ("https://login.xometry.com/u/login/password", "https://www.xometry.com/login/callback"):
            with self.subTest(url=url):
                page = SimpleNamespace(url=url, evaluate=AsyncMock())
                session = SimpleNamespace(page=page, check_active=lambda: None, goto=AsyncMock())
                submit = AsyncMock(side_effect=PlaywrightTimeoutError("synthetic timeout"))
                with patch.object(LoginProvider, "_submit", new=submit), patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()):
                    self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", url))
                submit.assert_awaited_once()
                page.evaluate.assert_not_awaited()
                session.goto.assert_not_awaited()

    async def test_jlc_timeout_does_not_run_xometry_reconciliation(self):
        page = SimpleNamespace(url="https://www.jlc-cnc.com/cncOrder/", evaluate=AsyncMock())
        submit = AsyncMock(side_effect=PlaywrightTimeoutError("synthetic timeout"))
        with patch.object(LoginProvider, "_submit", new=submit), patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()) as sleep:
            self.assertFalse(await PROVIDERS[1].submit(SimpleNamespace(page=page, check_active=lambda: None), "synthetic", "synthetic-password", page.url))
        submit.assert_awaited_once()
        page.evaluate.assert_not_awaited()
        sleep.assert_not_awaited()

    async def test_cookie_or_quote_url_without_server_identity_never_succeeds(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(return_value=[]))
        with patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()):
            self.assertFalse(await PROVIDERS[0].verify(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com"))
        self.assertEqual(page.evaluate.await_count, 3)

    async def test_jlc_identity_matches_masked_phone_and_customercode(self):
        jlc_provider = PROVIDERS[1]
        self.assertEqual(jlc_provider.code, "jlc_cnc_cn")
        # Masked phone matching
        page = SimpleNamespace(url="https://www.jlc-cnc.com/cncOrder/#/placeOrder", evaluate=AsyncMock(return_value=["J14378920", "14271345A", "192****2291"]))
        session = SimpleNamespace(page=page, check_active=lambda: None)
        self.assertTrue(await jlc_provider.verify(session, "19216192291"))
        # CustomerCode matching
        self.assertTrue(await jlc_provider.verify(session, "14271345a"))
        # Mismatch
        with self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
            await jlc_provider.verify(session, "13800138000")

    async def test_jlc_bound_code_is_compared_instead_of_the_login_identifier(self):
        jlc_provider = PROVIDERS[1]
        # queryLoginUser never echoes the phone, so a bound customer code is the
        # only evidence available once the account has logged in once.
        page = SimpleNamespace(url="https://www.jlc-cnc.com/cncOrder/#/", evaluate=AsyncMock(return_value=["14271345A"]))
        session = SimpleNamespace(page=page, check_active=lambda: None)
        self.assertTrue(await jlc_provider.verify(session, "19216192291", "14271345a"))
        with self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
            await jlc_provider.verify(session, "19216192291", "99999999X")

    async def test_identity_code_is_read_from_the_declared_field_only(self):
        jlc_provider = PROVIDERS[1]
        self.assertEqual(jlc_provider.identity_code_field, "customerCode")
        self.assertIsNone(PROVIDERS[0].identity_code_field)
        page = SimpleNamespace(url="https://www.jlc-cnc.com/cncOrder/#/", evaluate=AsyncMock(return_value="14271345A"))
        self.assertEqual(await jlc_provider.identify(SimpleNamespace(page=page, check_active=lambda: None)), "14271345A")
        self.assertEqual(page.evaluate.await_args.args[1], {"url": "https://www.jlc-cnc.com/api/cncPortal/login/queryLoginUser", "field": "customerCode"})
        # A provider without a bound-code field never reads one.
        self.assertEqual(await PROVIDERS[0].identify(SimpleNamespace(page=page, check_active=lambda: None)), "")

    def test_slider_path_ends_exactly_on_target_and_stays_near_the_track(self):
        steps = slider_drag_steps(356.0, random.Random(7))
        self.assertEqual(steps[-1][0], 356.0)
        self.assertGreater(len(steps), 5)
        self.assertTrue(all(-4.0 <= offset <= 360.0 for offset, _, _ in steps))
        self.assertTrue(all(abs(drift) <= 1.4 for _, drift, _ in steps))
        self.assertTrue(all(8 <= pause <= 90 for _, _, pause in steps))

    def xometry_asia_form(self, url="https://get.xometry.asia/sign_in", consent_visible=True):
        email = SimpleNamespace(count=AsyncMock(return_value=1), first=SimpleNamespace(wait_for=AsyncMock(), fill=AsyncMock()))
        password = SimpleNamespace(count=AsyncMock(return_value=1), first=SimpleNamespace(fill=AsyncMock()))
        tab = SimpleNamespace(count=AsyncMock(return_value=1), first=SimpleNamespace(click=AsyncMock()))

        def box(visible, checked):
            option = SimpleNamespace(
                is_visible=AsyncMock(return_value=visible),
                is_checked=AsyncMock(return_value=checked),
                check=AsyncMock(),
            )
            return SimpleNamespace(count=AsyncMock(return_value=1), nth=lambda index: option)

        controls = {
            "input#email": email,
            "input#password": password,
            "#accept": box(consent_visible, False),
            "#remember": box(True, True),
        }
        page = SimpleNamespace(url=url, locator=lambda selector: controls[selector], get_by_text=lambda *args, **kwargs: tab, wait_for_timeout=AsyncMock())

        async def sign_in(*args, **kwargs):
            page.url = "https://get.xometry.asia/dashboard"

        submit = SimpleNamespace(first=SimpleNamespace(click=AsyncMock(side_effect=sign_in)))
        page.get_by_role = lambda *args, **kwargs: submit
        session = SimpleNamespace(page=page, check_active=lambda: None, goto=AsyncMock())
        return session, email, password, tab, controls

    async def test_asia_email_tab_is_selected_consent_accepted_and_submitted_once(self):
        session, email, password, tab, controls = self.xometry_asia_form()
        provider = PROVIDERS[2]
        self.assertEqual(provider.code, "xometry_asia")
        self.assertTrue(await provider.submit(session, "owner@example.com", "synthetic-password", "https://get.xometry.asia/quotes"))
        session.goto.assert_not_awaited()
        tab.first.click.assert_awaited_once_with(timeout=8000)
        email.first.fill.assert_awaited_once_with("owner@example.com")
        password.first.fill.assert_awaited_once_with("synthetic-password")
        controls["#accept"].nth(0).check.assert_awaited_once_with(timeout=5000)
        # Already ticked by the site: never toggled off and on again.
        controls["#remember"].nth(0).check.assert_not_awaited()

    async def test_asia_unaccepted_consent_never_submits_credentials(self):
        session, email, _, _, _ = self.xometry_asia_form(consent_visible=False)
        provider = PROVIDERS[2]
        self.assertFalse(await provider.submit(session, "owner@example.com", "synthetic-password", "https://get.xometry.asia/quotes"))
        # The typed values stay for the human, but the credential action stops.
        email.first.fill.assert_awaited_once()
        self.assertEqual(session.page.url, "https://get.xometry.asia/sign_in")

    async def test_asia_identity_reads_the_graphql_me_payload(self):
        provider = PROVIDERS[2]
        self.assertIsNone(provider.identity_code_field)
        self.assertEqual(urlsplit(provider.identity_url).hostname, "api.xometry.asia")
        page = SimpleNamespace(url="https://get.xometry.asia/quotes", evaluate=AsyncMock(return_value=["anhha9372@gmail.com", "+86 19216192291"]))
        session = SimpleNamespace(page=page, check_active=lambda: None)
        self.assertTrue(await provider.verify(session, "anhha9372@gmail.com"))
        # The provider's own reader is used, not the shared JSON GET fetcher.
        self.assertIs(page.evaluate.await_args.args[0], XOMETRY_ASIA_IDENTITY)
        self.assertEqual(page.evaluate.await_args.args[1], {"url": "https://api.xometry.asia/get/graphql", "fields": ["email", "phone"]})
        with self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
            await provider.verify(session, "someone-else@example.com")

    async def test_asia_resolution_requires_both_urls_on_the_entry_host(self):
        provider = resolve_provider("https://get.xometry.asia/sign_in", "https://get.xometry.asia/quotes")
        self.assertEqual(provider.code, "xometry_asia")
        # The sign-in mutation writes its cookies on the registrable parent.
        self.assertIn("xometry.asia", provider.hosts)
        self.assertNotIn("xometry.asia", provider.entry_hosts)
        with self.assertRaises(LoginError):
            resolve_provider("https://get.xometry.asia/sign_in", "https://www.xometry.com/quoting/home/")

    async def test_asia_timeout_does_not_run_xometry_reconciliation(self):
        page = SimpleNamespace(url="https://get.xometry.asia/sign_in", evaluate=AsyncMock())
        submit = AsyncMock(side_effect=PlaywrightTimeoutError("synthetic timeout"))
        with patch.object(LoginProvider, "_submit", new=submit), patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()) as sleep:
            self.assertFalse(await PROVIDERS[2].submit(SimpleNamespace(page=page, check_active=lambda: None), "synthetic", "synthetic-password", "https://get.xometry.asia/quotes"))
        submit.assert_awaited_once()
        page.evaluate.assert_not_awaited()
        sleep.assert_not_awaited()

    async def test_resource_host_cannot_be_configured_as_platform_entry(self):
        for login, quote in (
            ("https://assets.xometry.com/login", "https://www.xometry.com/quoting/home/"),
            ("https://passport.jlc.com/login", "https://static.jlc-cnc.com/quote"),
            ("https://www.xometry.com/account/login/", "https://www.jlc-cnc.com/cncOrder/"),
            ("https://user:secret@www.xometry.com/", "https://www.xometry.com/quoting/home/"),
            ("http://www.xometry.com/", "https://www.xometry.com/quoting/home/"),
            ("https://[invalid-host/login", "https://www.xometry.com/quoting/home/"),
            ("https://www.xometry.com/account/login/", "https://[invalid-host/quote"),
        ):
            with self.subTest(login=login), self.assertRaises(LoginError):
                resolve_provider(login, quote)


class CredentialTests(unittest.TestCase):
    def test_encrypted_credentials_and_legacy_compatibility(self):
        ciphertext = seal_credentials("synthetic@example.com", "private-synthetic-password")
        self.assertNotIn(b"private-synthetic-password", ciphertext)
        encrypted = SimpleNamespace(username="synthetic@example.com", password="", credential_ciphertext=ciphertext)
        self.assertEqual(read_credentials(encrypted), ("synthetic@example.com", "private-synthetic-password"))
        legacy = SimpleNamespace(username="synthetic@example.com", password="legacy-synthetic", credential_ciphertext=None)
        self.assertEqual(read_credentials(legacy), ("synthetic@example.com", "legacy-synthetic"))

    def test_read_response_excludes_secret_fields_even_when_object_contains_them(self):
        row = SimpleNamespace(
            id=1, username="synthetic", password="private-password", credential_ciphertext=b"private-cipher", session_ciphertext=b"private-state", lease_token=6, key_id="private-key-id"
        )
        result = CncAccountOutSchema.model_validate(row).model_dump()
        for field in ("password", "credential_ciphertext", "session_ciphertext", "lease_token", "key_id"):
            self.assertNotIn(field, result)


if __name__ == "__main__":
    unittest.main()
