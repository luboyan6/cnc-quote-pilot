"""Real Chromium, synthetic HTTPS providers; run explicitly with this filename.

Exercises actual provider selectors, native form navigation/iframe callback,
identity fetch, screenshot and encrypted state recreation. No live credentials
or real CNC mutations occur. Only exact synthetic provider requests are fulfilled.
"""

import asyncio
import json
import sys
import unittest
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from test_runtime import ACCOUNT, FakeRepository

from app.modules.cnc.browser.session import BrowserExecutor
from app.modules.cnc.browser.state import SessionCodec
from app.modules.cnc.login.providers import PROVIDERS
from app.modules.cnc.login.runtime import LoginManager
from app.utils.crypto_util import CryptoUtil


class SyntheticProviderBrowser:
    def __init__(self, provider, *, challenge=False):
        self.provider = provider
        self.challenge = challenge
        self.password_submissions = 0
        self.submitted_username = ""
        self.executor = BrowserExecutor(SessionCodec(CryptoUtil))

    @asynccontextmanager
    async def session(self, scope, policy, *, encrypted_state=None):
        async with self.executor.session(scope, policy, encrypted_state=encrypted_state) as session:
            await session.page.context.route("**/*", self.route)
            yield session

    async def route(self, route):
        parsed = urlsplit(route.request.url)
        if parsed.hostname not in self.provider.hosts:
            await route.fallback()  # Reviewed tracker reaches the real abort guard.
            return
        authenticated = "synthetic-auth=ready" in route.request.headers.get("cookie", "")
        if parsed.hostname == "api.xometry.com" or parsed.path.endswith("queryLoginUser"):
            data = {"email_address": ACCOUNT.username} if self.provider.code == "xometry_us" else {"data": {"customerCode": "SYNTHETIC-123"}}
            await route.fulfill(
                status=200 if authenticated else 401,
                content_type="application/json",
                headers={"Access-Control-Allow-Origin": "https://www.xometry.com", "Access-Control-Allow-Credentials": "true"},
                body=json.dumps(data if authenticated else {}),
            )
            return
        if self.provider.code == "xometry_us":
            await self.xometry(route, parsed)
        else:
            await self.jlc(route, parsed)

    async def xometry(self, route, parsed):
        if parsed.path.startswith("/account/login"):
            await route.fulfill(status=302, headers={"Location": "https://login.xometry.com/u/login/identifier"})
        elif parsed.path == "/u/login/identifier":
            await route.fulfill(
                content_type="text/html; charset=utf-8",
                body="""<form action="/u/login/password" method="post">
              <label for="username">Business Email</label><input id="username" name="username">
              <button type="submit">Continue</button></form>""",
            )
        elif parsed.path == "/u/login/password":
            self.submitted_username = parse_qs(route.request.post_data or "").get("username", [""])[0]
            await route.fulfill(
                content_type="text/html; charset=utf-8",
                body="""<form action="https://www.xometry.com/callback" method="post">
              <label for="password">Password</label><input id="password" name="password" type="password">
              <button type="submit">Continue</button></form>""",
            )
        elif parsed.path == "/callback":
            self.password_submissions += 1
            if self.challenge:
                await route.fulfill(content_type="text/html; charset=utf-8", body='<h1>Verification code</h1><input placeholder="Email code">')
            else:
                await route.fulfill(content_type="text/html; charset=utf-8", headers={"Set-Cookie": "synthetic-auth=ready; Domain=.xometry.com; Path=/; Secure; HttpOnly"}, body="<h1>Signed in</h1>")
        else:
            await route.fulfill(content_type="text/html; charset=utf-8", body='<h1>Synthetic quoting page</h1><script src="https://www.googletagmanager.com/synthetic.js"></script>')

    async def jlc(self, route, parsed):
        if parsed.hostname == "passport.jlc.com" and parsed.path == "/window/login":
            await route.fulfill(
                content_type="text/html; charset=utf-8",
                body="""<button onclick="document.querySelector('form').hidden=false">账号登录</button>
              <form hidden action="/login-submit" method="post"><input name="username" placeholder="请输入手机号码 / 客户编号 / 邮箱">
              <input name="password" type="password" placeholder="请输入登录密码"><button type="submit">登录</button></form>""",
            )
        elif parsed.hostname == "passport.jlc.com" and parsed.path == "/login-submit":
            self.password_submissions += 1
            self.submitted_username = parse_qs(route.request.post_data or "").get("username", [""])[0]
            await route.fulfill(content_type="text/html; charset=utf-8", body="<script>parent.postMessage('synthetic-authenticated','https://www.jlc-cnc.com')</script>")
        elif parsed.path == "/callback":
            await route.fulfill(content_type="application/json", headers={"Set-Cookie": "synthetic-auth=ready; Path=/; Secure; HttpOnly"}, body="{}")
        else:
            await route.fulfill(
                content_type="text/html; charset=utf-8",
                body="""<h1>Synthetic CNC quoting page</h1>
              <button onclick="let f=document.createElement('iframe');f.id='jlc-cas-login-window';f.src='https://passport.jlc.com/window/login';document.body.append(f)">登录</button>
              <script>addEventListener('message',async e=>{if(e.origin==='https://passport.jlc.com'&&e.data==='synthetic-authenticated'){
              await fetch('/callback');document.querySelector('iframe').remove()}})</script>""",
            )


async def settled(manager, view):
    async with asyncio.timeout(20):
        while manager.sessions[view.session_id].status in {"STARTING", "AUTHENTICATING"}:
            await asyncio.sleep(0.05)
    return manager.sessions[view.session_id].view()


class LoginBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def run_flow(self, index, challenge=False):
        provider = PROVIDERS[index]
        repo = FakeRepository()
        fixture = SyntheticProviderBrowser(provider, challenge=challenge)
        manager = LoginManager(repo, fixture)
        account = replace(
            ACCOUNT,
            username=ACCOUNT.username if index == 0 else "SYNTHETIC-123",
            login_url="https://login.xometry.com/u/login/identifier" if index == 0 else "https://www.jlc-cnc.com/cncOrder/#/placeOrder",
            quote_url="https://www.xometry.com/quoting/home/" if index == 0 else "https://www.jlc-cnc.com/cncOrder/#/placeOrder",
        )
        try:
            view = await settled(manager, await manager.start(account))
            self.assertEqual(view.status, "WAITING_HUMAN" if challenge else "READY", view.reason)
            self.assertEqual(fixture.password_submissions, 1)
            self.assertEqual(fixture.submitted_username, account.username)
            pixels = await manager.command(account, view.session_id, "frame")
            assert isinstance(pixels, bytes)
            self.assertTrue(pixels.startswith(b"\xff\xd8"))
            self.assertGreater(len(pixels), 1000)
            if challenge:
                self.assertFalse(repo.states)
                self.assertEqual((await manager.command(account, view.session_id, "verify")).status, "WAITING_HUMAN")
                self.assertEqual(fixture.password_submissions, 1)
            else:
                await manager.command(account, view.session_id, "close")
                restored = replace(account, encrypted_state=repo.states[-1])
                reopened = await settled(manager, await manager.start(restored))
                self.assertEqual(reopened.status, "READY", reopened.reason)
                self.assertEqual(fixture.password_submissions, 1, "Restored identity must skip credentials")
        finally:
            await manager.close_all()
        self.assertEqual(fixture.executor.active_count, 0)

    async def test_xometry_split_form_and_closed_context_restore(self):
        await self.run_flow(0)

    async def test_jlc_native_iframe_and_closed_context_restore(self):
        await self.run_flow(1)

    async def test_challenge_preserves_human_page_without_repeated_submission(self):
        await self.run_flow(0, challenge=True)


if __name__ == "__main__":
    unittest.main()
