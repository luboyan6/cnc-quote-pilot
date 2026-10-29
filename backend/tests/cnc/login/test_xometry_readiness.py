"""Native Xometry sign-in signals on local Chromium; no live provider traffic."""

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.login.providers import PROVIDERS, LoginProvider

HOME = "https://www.xometry.com/quoting/home/"
IDENTITY = "https://api.xometry.com/v2/users/me"


class XometryReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_observed_dom_signals_preserve_identity_and_read_only_verification(self):
        # One local browser exercises the actual DOM/identity fetch in every
        # case; all requests are fulfilled here and none reach Xometry.
        identities = {"email_address": "owner@example.com"}
        requests = []

        async def serve(route):
            request = route.request
            requests.append((request.method, request.url))
            if request.url == IDENTITY:
                await route.fulfill(
                    content_type="application/json",
                    body=json.dumps(identities),
                    headers={"Access-Control-Allow-Origin": "https://www.xometry.com", "Access-Control-Allow-Credentials": "true"},
                )
            elif request.url == HOME:
                await route.fulfill(content_type="text/html", body="<!doctype html><html><body></body></html>")
            else:
                self.fail("Unexpected synthetic request")

        async with async_playwright() as sdk:
            browser = await sdk.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.route("**/*", serve)
                await page.goto(HOME)
                session = SimpleNamespace(page=page, check_active=lambda: None)
                guest_header = '<button id="header-login-register-button">Log In / Register</button>'
                signin_alert = '<div data-testid="Alert-upload-view-error">Sign in to start a new quote.</div><button id="instant-quote-continue" disabled>Start Instant Quote</button>'
                cases = (
                    ("guest header", guest_header, False, 3),
                    ("explicit uploader sign-in", signin_alert, False, 3),
                    ("both signed-out signals", guest_header + signin_alert, False, 3),
                    ("authenticated header", '<button id="header-my-account-button">My Account</button>', True, 1),
                    ("account header cannot override guest state", '<button id="header-my-account-button">My Account</button>' + guest_header, False, 3),
                    ("account header cannot override uploader sign-in", '<button id="header-my-account-button">My Account</button>' + signin_alert, False, 3),
                    ("no explicit negative", "<main>Quote</main>", True, 1),
                    ("hidden guest controls", '<div style="display:none">' + guest_header + signin_alert + "</div>", True, 1),
                    ("other upload validation", '<div data-testid="Alert-upload-view-error">Upload at least 1 CAD file to get started.</div>', True, 1),
                    ("disabled quote action alone", '<button id="instant-quote-continue" disabled>Start Instant Quote</button>', True, 1),
                )
                for label, body, expected, identity_reads in cases:
                    with self.subTest(label=label):
                        await page.set_content(
                            body + "<script>window.uiWrites=0;document.addEventListener('click',()=>window.uiWrites++);document.addEventListener('submit',()=>window.uiWrites++);</script>"
                        )
                        before = len(requests)
                        self.assertEqual(await PROVIDERS[0].verify(session, "owner@example.com"), expected)
                        self.assertEqual(requests[before:], [("GET", IDENTITY)] * identity_reads)
                        self.assertEqual(await page.evaluate("window.uiWrites"), 0)
                        self.assertEqual(page.url, HOME)

                # Neither an authenticated-looking header nor DOM absence can
                # substitute for the exact authenticated account identity.
                await page.set_content('<button id="header-my-account-button">My Account</button>')
                identities.clear()
                before = len(requests)
                self.assertFalse(await PROVIDERS[0].verify(session, "owner@example.com"))
                self.assertEqual(requests[before:], [("GET", IDENTITY)] * 3)
                identities["email_address"] = "different@example.com"
                before = len(requests)
                with self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
                    await PROVIDERS[0].verify(session, "owner@example.com")
                self.assertEqual(requests[before:], [("GET", IDENTITY)])
            finally:
                await browser.close()

    async def test_submitted_login_requires_settled_quote_ui_and_identity_without_another_write(self):
        identities = {"email_address": "owner@example.com"}
        requests = []

        async def serve(route):
            requests.append((route.request.method, route.request.url))
            if route.request.url == IDENTITY:
                await route.fulfill(
                    content_type="application/json",
                    body=json.dumps(identities),
                    headers={"Access-Control-Allow-Origin": "https://www.xometry.com", "Access-Control-Allow-Credentials": "true"},
                )
            elif route.request.url == HOME:
                await route.fulfill(content_type="text/html", body="<!doctype html><html><body></body></html>")
            else:
                self.fail("Unexpected synthetic request")

        account = '<button id="header-my-account-button">My Account</button>'
        cases = (
            ("settled account", account, "complete", True, 1),
            ("empty shell", "<main></main>", "complete", False, 0),
            ("loading account shell", account, "interactive", False, 0),
            ("hidden account", "<div hidden>" + account + "</div>", "complete", False, 0),
            ("disabled account", '<button id="header-my-account-button" disabled>My Account</button>', "complete", False, 0),
            ("aria-disabled account", '<button id="header-my-account-button" aria-disabled="true">My Account</button>', "complete", False, 0),
            ("duplicate account", account + account, "complete", False, 0),
            ("non-native account", '<div id="header-my-account-button">My Account</div>', "complete", False, 0),
            ("guest account", account + '<button id="header-login-register-button">Log In / Register</button>', "complete", False, 0),
            ("uploader requires sign-in", account + '<div data-testid="Alert-upload-view-error">Sign in to start a new quote.</div>', "complete", False, 0),
            ("one-time challenge", account + '<input autocomplete="one-time-code">', "complete", False, 0),
            ("password challenge", account + '<input id="password" name="password" type="password">', "complete", False, 0),
            ("captcha challenge", account + '<iframe title="Challenge" srcdoc=""></iframe>', "complete", False, 0),
        )
        async with async_playwright() as sdk:
            browser = await sdk.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.route("**/*", serve)
                await page.goto(HOME)
                session = SimpleNamespace(page=page, check_active=lambda: None, goto=AsyncMock())
                for outcome in ("returned", "timeout"):
                    identities["email_address"] = "owner@example.com"
                    for label, body, state, expected, identity_reads in cases:
                        with self.subTest(outcome=outcome, label=label):
                            await page.set_content(
                                body + "<script>window.uiWrites=0;document.addEventListener('click',()=>window.uiWrites++);document.addEventListener('submit',()=>window.uiWrites++);</script>"
                            )
                            await page.evaluate("state => Object.defineProperty(document, 'readyState', {configurable:true,get:()=>state})", state)
                            before = len(requests)
                            submit = AsyncMock(return_value=True, side_effect=PlaywrightTimeoutError("synthetic navigation timeout") if outcome == "timeout" else None)
                            with patch.object(LoginProvider, "_submit", new=submit), patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()):
                                self.assertEqual(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", HOME), expected)
                            submit.assert_awaited_once()
                            session.goto.assert_not_awaited()
                            self.assertEqual(requests[before:], [("GET", IDENTITY)] * identity_reads)
                            self.assertEqual(await page.evaluate("window.uiWrites"), 0)
                            self.assertEqual(page.url, HOME)

                    await page.set_content(account)
                    await page.evaluate("() => Object.defineProperty(document, 'readyState', {configurable:true,get:()=> 'complete'})")
                    identities.clear()
                    before = len(requests)
                    submit = AsyncMock(return_value=True, side_effect=PlaywrightTimeoutError("synthetic navigation timeout") if outcome == "timeout" else None)
                    with patch.object(LoginProvider, "_submit", new=submit), patch("app.modules.cnc.login.providers.asyncio.sleep", new=AsyncMock()):
                        self.assertFalse(await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", HOME))
                    submit.assert_awaited_once()
                    self.assertEqual(requests[before:], [("GET", IDENTITY)] * 3)

                    identities["email_address"] = "different@example.com"
                    before = len(requests)
                    submit = AsyncMock(return_value=True, side_effect=PlaywrightTimeoutError("synthetic navigation timeout") if outcome == "timeout" else None)
                    with patch.object(LoginProvider, "_submit", new=submit), self.assertRaisesRegex(LoginError, "IDENTITY_MISMATCH"):
                        await PROVIDERS[0].submit(session, "owner@example.com", "synthetic-password", HOME)
                    submit.assert_awaited_once()
                    self.assertEqual(requests[before:], [("GET", IDENTITY)])
            finally:
                await browser.close()


if __name__ == "__main__":
    unittest.main()
