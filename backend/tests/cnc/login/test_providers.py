"""Provider identity, egress and credential contracts without live accounts."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.modules.cnc.browser.contracts import SessionScope
from app.modules.cnc.browser.errors import BrowserStop
from app.modules.cnc.browser.policy import BrowserPolicy
from app.modules.cnc.browser.session import BrowserSession
from app.modules.cnc.browser.state import SessionCodec
from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.credentials import read_credentials, seal_credentials
from app.modules.cnc.login.providers import PROVIDERS, resolve_provider
from app.plugin.module_cnc.cnc_account.schema import CncAccountOutSchema
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
    async def test_identity_matches_exact_server_field_and_uses_guarded_page(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(return_value=["OWNER@EXAMPLE.COM"]))
        session = SimpleNamespace(page=page, check_active=lambda: None)
        self.assertTrue(await PROVIDERS[0].verify(session, "owner@example.com"))
        self.assertEqual(page.evaluate.await_args.args[1]["url"], "https://api.xometry.com/v2/users/me")
        self.assertEqual(page.evaluate.await_count, 1)

    async def test_other_authenticated_identity_is_not_relogged_or_overwritten(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(return_value=["different@example.com"]))
        with self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
            await PROVIDERS[0].verify(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com")

    async def test_cookie_or_quote_url_without_server_identity_never_succeeds(self):
        page = SimpleNamespace(url="https://www.xometry.com/quoting/home/", evaluate=AsyncMock(return_value=[]))
        with patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()):
            self.assertFalse(await PROVIDERS[0].verify(SimpleNamespace(page=page, check_active=lambda: None), "owner@example.com"))
        self.assertEqual(page.evaluate.await_count, 3)

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
