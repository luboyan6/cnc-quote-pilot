"""Inspected login UI and read-only identity contracts; never infer auth from a URL.

Evidence: task02/research/login-provider-evidence-2026-10-22.md.
"""

import asyncio
import random
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.modules.cnc.browser.policy import BrowserPolicy

from .contracts import LoginError

# Observed public analytics/QR dependencies: block them rather than allowing
# their nested ad networks or private-network probes. Exact hostnames only.
OPTIONAL_RESOURCES = frozenset(
    {
        "www.googletagmanager.com",
        "www.google-analytics.com",
        "analytics.google.com",
        "stats.g.doubleclick.net",
        "googleads.g.doubleclick.net",
        "ad.doubleclick.net",
        "cm.g.doubleclick.net",
        "fonts.googleapis.com",
        "event-data-cdn.xometry.net",
        "event-data-api.xometry.net",
        "edge.fullstory.com",
        "rs.fullstory.com",
        "js.hs-scripts.com",
        "js.hubspot.com",
        "js.hs-analytics.net",
        "js.hs-banner.com",
        "js.hsadspixel.net",
        "api.hubapi.com",
        "cta-service-cms2.hubspot.com",
        "perf-na1.hsforms.com",
        "bat.bing.com",
        "cdn.sprig.com",
        "fast.appcues.com",
        "tag.demandbase.com",
        "tag-logger.demandbase.com",
        "s.company-target.com",
        "api.company-target.com",
        "segments.company-target.com",
        "snap.licdn.com",
        "px.ads.linkedin.com",
        "www.linkedin.com",
        "www.redditstatic.com",
        "alb.reddit.com",
        "cdn.taboola.com",
        "trc.taboola.com",
        "trc-events.taboola.com",
        "tags.srv.stackadapt.com",
        "bttrack.com",
        "cdn.bttrack.com",
        "dx.mountain.com",
        "px.mountain.com",
        "gs.mountain.com",
        "tag.simpli.fi",
        "api3941.d41.co",
        "cdn-0.d41.co",
        "bzr.openai.com",
        "bzrcdn.openai.com",
        "ingress.us1.rum-ingress-coralogix.com",
        "rcg.conviva.com",
        # Current quote-app instrumentation (official env.js/app source plus
        # managed request evidence, 2026-10-23). Denied subresources only;
        # these exact hosts never become allowed egress or navigation entries.
        "cloudflare-dns.com",
        "d2d1457e431c55589cd6869389fcdc7da348eb3d.appgw.conviva.com",
        "sentry.mgmt.global.xmtr.io",
        "xometry5836.my.salesforce-scrt.com",
        "xometry5836.my.site.com",
        "js.stripe.com",
        "m.stripe.com",
        "m.stripe.network",
        "r.stripe.com",
        "cdn.segment.com",
        "hm.baidu.com",
        "datasink.jlc.com",
        "fs-web-stream.jlc.com",
        "wework.qpic.cn",
        "open.weixin.qq.com",
        "res.wx.qq.com",
        # QR image the CAS widget requests on its default scan-to-login tab.
        # The account-login tab is the one this provider drives.
        "mp.weixin.qq.com",
        "lp.open.weixin.qq.com",
        "support.weixin.qq.com",
        "localhost.weixin.qq.com",
        "360fenxi.mediav.com",
        "3m.mediav.com",
        "e.so.com",
        "s.union.360.cn",
        "max.dmp.360.cn",
        "fclog.baidu.com",
        "fxgate.baidu.com",
        "ckmap.mediav.com",
        "cm.miaozhen.atm.youku.com",
        "cm.pos.baidu.com",
        "cms.tanx.com",
        # Observed on the Asia entry host. The page ships a large marketing and
        # risk-control stack; all of it is denied, and the email login still
        # completes. `xom_access` / `xom_refresh` are the only cookies the
        # signed-in app needs, so denying these also keeps tracking cookies out
        # of the sealed session state.
        "www.google.com",
        "www.google.co.jp",
        "www.googleadservices.com",
        "doubleclick.net",
        "k.clarity.ms",
        "www.clarity.ms",
        "scripts.clarity.ms",
        "clarity.ms",
        "exp.beschannels.com",
        "cdn.beschannels.com",
        "app.ma.scrmtech.com",
        "local.info.g9hc4.cn",
        "turing.captcha.gtimg.com",
        "turing.captcha.qcloud.com",
        "cdn.dingxiang-inc.com",
        "s3.cn-northwest-1.amazonaws.com.cn",
        # First-party subdomains kept out of the allowlist: the chat widget and
        # error reporting are not needed to sign in or to open the quote page.
        "messenger.xometry.asia",
        "sentry.xometry.asia",
    }
)

IDENTITY_FETCH = """async ({url, fields}) => {
  const values = [];
  try {
    const r = await fetch(url, {credentials:'include', redirect:'error',
      signal:AbortSignal.timeout(2500), headers:{Accept:'application/json'}});
    if (r.ok) {
      const body = await r.json();
      const user = body.data || body.user || body;
      if (user && typeof user === 'object') {
        for (const k of fields) {
          const v = user[k];
          if (typeof v === 'string' && v.trim()) values.push(v.trim());
        }
      }
    }
  } catch {}
  if (url.includes('jlc')) {
    try {
      const r2 = await fetch('https://passport.jlc.com/api/cas/sso/get-user-info', {
        method: 'POST', credentials: 'include', redirect: 'error',
        signal: AbortSignal.timeout(2500),
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ appId: 'CNC_BIZ_GATEWAY' })
      });
      if (r2.ok) {
        const body2 = await r2.json();
        const user2 = body2.data || body2.user || body2;
        if (user2 && typeof user2 === 'object') {
          for (const k of fields) {
            const v = user2[k];
            if (typeof v === 'string' && v.trim()) values.push(v.trim());
          }
        }
      }
    } catch {}
  }
  return [...new Set(values)];
}"""

# The Asia site has no REST identity route: every read goes through one
# GraphQL endpoint, and `getMe` answers 401 for a guest. The signed-in
# payload echoes `email` and `phone`, so no trust-on-first-use binding is
# needed here.
XOMETRY_ASIA_IDENTITY = """async ({url, fields}) => {
  const values = [];
  try {
    const r = await fetch(url, {
      method: 'POST', credentials: 'include', redirect: 'error',
      signal: AbortSignal.timeout(2500),
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ operationName: 'getMe', query: 'query getMe { me { id email phone name } }' }),
    });
    if (!r.ok) return [];
    const body = await r.json();
    const person = body && body.data && body.data.me;
    if (person && typeof person === 'object') {
      for (const k of fields) {
        const v = person[k];
        if (typeof v === 'string' && v.trim()) values.push(v.trim());
      }
    }
  } catch {}
  return [...new Set(values)];
}"""

# A matching identity endpoint can coexist with a signed-out quote UI. These
# observed controls are negative readiness evidence only, never account identity.
XOMETRY_SIGNIN_REQUIRED = """() => {
  if (!location.pathname.startsWith('/quoting/')) return false;
  const visible = el => !!el && el.getClientRects().length > 0 &&
    getComputedStyle(el).visibility !== 'hidden';
  const labelled = (selector, text) => [...document.querySelectorAll(selector)]
    .some(el => visible(el) && el.textContent.trim() === text);
  return labelled('#header-login-register-button', 'Log In / Register') ||
    labelled('[data-testid="Alert-upload-view-error"]', 'Sign in to start a new quote.');
}"""

# A delayed password redirect can outlive the click timeout. Reconciliation
# requires a settled, observed account header before the separate API identity
# check; a transient empty app shell must not satisfy login completion.
XOMETRY_POST_LOGIN_READY = """() => {
  if (document.readyState !== 'complete' || !location.pathname.startsWith('/quoting/')) return false;
  const visible = el => !!el && el.getClientRects().length > 0 &&
    getComputedStyle(el).visibility !== 'hidden';
  const labelled = (selector, text) => [...document.querySelectorAll(selector)]
    .some(el => visible(el) && el.textContent.trim() === text);
  const challenge = [...document.querySelectorAll(
    'input#username[name="username"],input#password[name="password"],input[autocomplete="one-time-code"],iframe[src*="captcha"],iframe[title*="challenge"],iframe[title*="Challenge"],[data-sitekey]'
  )].some(visible);
  const accounts = [...document.querySelectorAll('#header-my-account-button')].filter(visible);
  const accountReady = accounts.length === 1 && accounts[0].matches('button') &&
    accounts[0].textContent.trim() === 'My Account' &&
    !accounts[0].matches(':disabled') && accounts[0].getAttribute('aria-disabled') !== 'true';
  return !challenge && accountReady &&
    !labelled('#header-login-register-button', 'Log In / Register') &&
    !labelled('[data-testid="Alert-upload-view-error"]', 'Sign in to start a new quote.');
}"""


def _matches_identity(expected: str, val: str) -> bool:
    val_cf = val.strip().casefold()
    if val_cf == expected:
        return True
    if len(expected) == 11 and expected.isdigit() and len(val_cf) == 11:
        if val_cf[:3] == expected[:3] and val_cf[-4:] == expected[-4:] and val_cf[3:7] == "****":
            return True
    return False


# The quote app ships a driver.js product tour on first visit. Its overlay and
# highlight stage sit above the header, so every pointer target is intercepted
# until the tour is dismissed. Clicking its own skip control is the user path;
# this removes only tour-owned nodes when that click is itself intercepted.
JLC_TOUR_CLEAR = """() => {
  for (const node of document.querySelectorAll('[id^="driver-"], .driver-popover, .driver-overlay')) node.remove();
  for (const node of document.querySelectorAll('.driver-fix-stacking')) node.classList.remove('driver-fix-stacking');
}"""

# `queryLoginUser` never echoes the login identifier: a phone/email sign-in is
# answered with the customer's own codes only. One explicit field is read after
# a proven credential submit and bound to the account for later comparisons.
IDENTITY_CODE_FETCH = """async ({url, field}) => {
  try {
    const r = await fetch(url, {credentials:'include', redirect:'error',
      signal:AbortSignal.timeout(2500), headers:{Accept:'application/json'}});
    if (!r.ok) return "";
    const body = await r.json();
    const user = body.data || body.user || body;
    const value = user && typeof user === 'object' ? user[field] : null;
    return typeof value === 'string' ? value.trim() : "";
  } catch { return ""; }
}"""


def slider_drag_steps(distance: float, rng) -> list[tuple[float, float, int]]:
    """Organic handle path for the Aliyun slider.

    The widget scores the gesture: a uniform sweep to the edge is reset even
    when the handle reaches it. Steps therefore vary in size, occasionally
    hesitate backwards, drift vertically, and always finish exactly on
    `distance`. Returns (offset_x, drift_y, pause_ms) triples.
    """
    steps: list[tuple[float, float, int]] = []
    position = 0.0
    while position < distance:
        step = max(1.0, (distance - position) * rng.uniform(0.04, 0.16))
        if rng.random() < 0.08:
            step = -rng.uniform(1.0, 3.0)
        position = min(distance, position + step)
        steps.append((position, rng.uniform(-1.4, 1.4), rng.randint(8, 34)))
    steps.append((distance, 0.0, rng.randint(40, 90)))
    return steps


async def _first_visible(page, selector: str, timeout_ms: int = 12_000):
    """Return one unambiguous visible match, re-resolving DOM replacement.

    Auth0 replaces the document when it moves from the identifier step to the
    password step, so a single ``wait_for`` can fail with "element is not
    attached" even though the control is about to exist. Polling a fresh
    locator each round keeps that transition from reading as a missing control.
    """
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    while asyncio.get_running_loop().time() < deadline:
        try:
            locator = page.locator(selector)
            count = await locator.count()
        except Exception:
            count = 0
        if count > 1:
            return None
        if count == 1:
            candidate = locator.first
            try:
                await candidate.wait_for(state="visible", timeout=400)
                if await candidate.is_visible():
                    return candidate
            except Exception:
                pass
        try:
            await page.wait_for_timeout(400)
        except Exception:
            return None
    return None


@dataclass(frozen=True)
class LoginProvider:
    code: str
    entry_hosts: frozenset[str]
    hosts: frozenset[str]
    identity_url: str
    identity_fields: tuple[str, ...]
    # Field bound to the account on the first proven credential submit. Only
    # providers whose identity endpoint never echoes the login identifier set
    # this; everything else is matched against the stored username directly.
    identity_code_field: str | None = None
    # Read-only script that returns the declared identity values. Providers
    # whose endpoint is not a plain JSON GET (a GraphQL POST, for instance)
    # supply their own; the rest use the shared IDENTITY_FETCH.
    identity_script: str | None = None

    @property
    def policy(self):
        return BrowserPolicy(self.hosts, OPTIONAL_RESOURCES - self.hosts)

    async def identify(self, session) -> str:
        """Read the provider's own account code; never treated as auth on its own."""
        if self.identity_code_field is None:
            return ""
        if urlsplit(session.page.url).hostname not in self.entry_hosts:
            return ""
        value = await session.page.evaluate(IDENTITY_CODE_FETCH, {"url": self.identity_url, "field": self.identity_code_field})
        session.check_active()
        return value if isinstance(value, str) else ""

    async def verify(self, session, username: str, identity_code: str | None = None) -> bool:
        # Fetch in the guarded Page, never an independent request client that
        # bypasses context routing/proxy. Only explicit identity fields count.
        if urlsplit(session.page.url).hostname not in self.entry_hosts:
            return False
        expected = username.strip().casefold()
        bound = (identity_code or "").strip().casefold()
        script = self.identity_script or IDENTITY_FETCH
        for attempt in range(3):
            identities = await session.page.evaluate(script, {"url": self.identity_url, "fields": list(self.identity_fields)})
            session.check_active()
            if any(_matches_identity(bound or expected, value) for value in identities):
                if self.code != "xometry_us":
                    return True
                signin_required = await session.page.evaluate(XOMETRY_SIGNIN_REQUIRED)
                session.check_active()
                if not signin_required:
                    return True
                # Reuse the existing read-only retry budget for guest-shell
                # hydration before the owner enters its normal login flow.
            elif identities:
                raise LoginError("IDENTITY_MISMATCH")
            if attempt < 2:
                await asyncio.sleep(0.5)
        return False

    async def submit(self, session, username: str, password: str, quote_url: str) -> bool:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        try:
            submitted = await self._submit(session, username, password, quote_url)
        except PlaywrightTimeoutError:
            # Missing/changed controls and challenges preserve the visible page
            # for its human owner. Never resubmit an uncertain login attempt.
            if self.code == "xometry_us":
                return await self._reconcile_xometry_login(session, username)
            return False
        if self.code == "xometry_us" and submitted:
            # A successful click can also return before the quote app settles.
            # Keep completion checks outside the credential-action try block so
            # a failed read cannot start another reconciliation pass.
            return await self._reconcile_xometry_login(session, username)
        return submitted

    async def _reconcile_xometry_login(self, session, username: str) -> bool:
        from playwright.async_api import Error as PlaywrightError

        try:
            # UI readiness never substitutes for the exact server identity.
            # Keep this read-only check bounded; a slower redirect stays manual.
            async with asyncio.timeout(8):
                for attempt in range(3):
                    if attempt:
                        await asyncio.sleep(1.5)
                    session.check_active()
                    route = urlsplit(session.page.url)
                    if route.hostname not in self.entry_hosts or not route.path.startswith("/quoting/"):
                        continue
                    try:
                        settled = await session.page.evaluate(XOMETRY_POST_LOGIN_READY)
                        session.check_active()
                        if settled:
                            if not await self.verify(session, username):
                                return False
                            settled = await session.page.evaluate(XOMETRY_POST_LOGIN_READY)
                            session.check_active()
                            return bool(settled)
                    except PlaywrightError as error:
                        # Only a read racing the observed login redirect may
                        # retry. The credential action above is never repeated.
                        if "execution context was destroyed" not in error.message.lower():
                            raise
        except TimeoutError:
            pass
        return False

    async def _submit(self, session, username: str, password: str, quote_url: str) -> bool:
        page = session.page
        if self.code == "xometry_us":
            if urlsplit(page.url).hostname != "login.xometry.com":
                await session.goto("https://xometry.com/login")
            if urlsplit(page.url).hostname != "login.xometry.com":
                return False
            identifier = await _first_visible(page, 'input#username[name="username"]')
            if identifier is None:
                return False
            await identifier.fill(username)
            # Auth0 schedules the identifier->password navigation after the
            # response, so waiting for it inside click() times out and would
            # abort a submit that actually succeeded. The next control wait is
            # the real settle point.
            await page.get_by_role("button", name="Continue", exact=True).click(timeout=8000, no_wait_after=True)
            password_input = await _first_visible(page, 'input#password[name="password"]')
            if password_input is None:
                return False
            await password_input.fill(password)
            await page.get_by_role("button", name="Continue", exact=True).click(timeout=8000, no_wait_after=True)
            session.check_active()
            return True
        if self.code == "jlc_cnc_cn":
            return await self._submit_jlc(session, username, password, quote_url)
        if self.code == "xometry_asia":
            return await self._submit_xometry_asia(session, username, password)
        return False

    async def _submit_jlc(self, session, username: str, password: str, quote_url: str) -> bool:
        """Observed JLC flow: tour -> header login -> CAS iframe -> account tab.

        The CAS widget opens on the QR tab, so the account tab must be selected
        before the two fields exist. Every step waits for the real control
        instead of assuming the widget finished hydrating.
        """
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        page = session.page
        # The quote page owns the CAS callback (redirectUrl), so start there
        # regardless of which page the runtime navigated to.
        if urlsplit(page.url).hostname != "www.jlc-cnc.com" or not urlsplit(page.url).path.startswith("/cncOrder"):
            await session.goto(quote_url)
        # domcontentloaded returns before the app hydrates the header, so the
        # entry button is awaited instead of assumed.
        login_button = page.locator("button.login-button")
        frame_selector = "iframe#jlc-cas-login-window"
        try:
            await login_button.first.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            return False
        for attempt in range(2):
            # The product tour hydrates after the header and can start between
            # a dismissal and the click. Opening the CAS window is retried, the
            # credentials are not: a second pass only repeats this pointer act.
            await self._dismiss_jlc_tour(page)
            await page.wait_for_timeout(300)
            if await login_button.count() != 1:
                return False
            try:
                await login_button.first.click(timeout=3500)
            except PlaywrightTimeoutError:
                if attempt:
                    return False
                continue
            try:
                await page.locator(frame_selector).first.wait_for(state="visible", timeout=4000)
                break
            except PlaywrightTimeoutError:
                if attempt:
                    return False
        session.check_active()

        frame = page.frame_locator(frame_selector)
        tabs = frame.locator(".base-tabs__nav-item")
        try:
            await tabs.first.wait_for(state="visible", timeout=12000)
        except PlaywrightTimeoutError:
            return False
        account_tab = tabs.filter(has_text="账号登录")
        if await account_tab.count() != 1:
            return False
        await account_tab.first.click(timeout=5000)

        identifier = frame.get_by_placeholder("请输入手机号码 / 客户编号 / 邮箱", exact=True)
        password_input = frame.get_by_placeholder("请输入登录密码", exact=True)
        try:
            await identifier.first.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            return False
        if await identifier.count() != 1 or await password_input.count() != 1:
            return False
        # Typed input keeps the widget's own validation and the risk engine's
        # keystroke signal, which a programmatic value assignment skips.
        await identifier.first.click()
        await identifier.first.type(username, delay=random.randint(45, 95))
        await password_input.first.click()
        await password_input.first.type(password, delay=random.randint(45, 95))
        await self._jlc_keep_signed_in(frame)

        submit = frame.locator("button.submit").filter(has_text="登录")
        if await submit.count() != 1:
            return False
        await submit.first.click(timeout=8000)
        session.check_active()

        await self._jlc_pass_challenge(session, page, frame, frame_selector)
        return await self._jlc_await_outcome(page, frame_selector)

    @staticmethod
    async def _dismiss_jlc_tour(page) -> None:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        skip = page.get_by_role("button", name="跳过", exact=True)
        if await skip.count() > 0:
            try:
                await skip.first.click(timeout=3000)
            except PlaywrightTimeoutError:
                # The tour's own highlight stage can cover its skip control.
                pass
        if await page.locator("#driver-page-overlay").count():
            await page.evaluate(JLC_TOUR_CLEAR)

    @staticmethod
    async def _jlc_keep_signed_in(frame) -> None:
        """Keep the long-lived passport cookie so a verified session is reusable."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        remember = frame.locator(".el-checkbox").filter(has_text="下次自动登录")
        for index in range(await remember.count()):
            option = remember.nth(index)
            if not await option.is_visible():
                continue
            if "is-checked" not in (await option.get_attribute("class") or ""):
                try:
                    await option.click(timeout=3000)
                except PlaywrightTimeoutError:
                    pass
            return

    async def _jlc_pass_challenge(self, session, page, frame, frame_selector: str) -> None:
        """Drag the Aliyun slider once per attempt; a failed drag resets it."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        handle = frame.locator(".aliyunCaptcha-sliding-slider")
        track = frame.locator(".aliyunCaptcha-sliding-text-box")
        try:
            await handle.first.wait_for(state="visible", timeout=2500)
        except PlaywrightTimeoutError:
            return  # No risk-control challenge for this attempt.
        for _ in range(2):
            if not await page.locator(frame_selector).count():
                return
            box = await handle.first.bounding_box()
            rail = await track.first.bounding_box()
            if not box or not rail:
                return
            await self._jlc_drag(session, page, box, rail)
            try:
                await handle.first.wait_for(state="detached", timeout=3500)
            except PlaywrightTimeoutError:
                continue
            return

    @staticmethod
    async def _jlc_drag(session, page, box, rail) -> None:
        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2
        # Release just past the track edge: stopping on it reads as unfinished.
        end_x = rail["x"] + rail["width"] - box["width"] / 2 + 3
        # Approach the handle the way a person does, then hold before pulling.
        await page.mouse.move(start_x - 12, start_y + 6)
        await page.wait_for_timeout(random.randint(180, 320))
        await page.mouse.move(start_x, start_y)
        await page.wait_for_timeout(random.randint(90, 180))
        await page.mouse.down()
        await page.wait_for_timeout(random.randint(60, 140))
        for offset, drift, pause in slider_drag_steps(end_x - start_x, random):
            await page.mouse.move(start_x + offset, start_y + drift)
            await page.wait_for_timeout(pause)
        await page.mouse.up()
        session.check_active()

    @staticmethod
    async def _jlc_await_outcome(page, frame_selector: str) -> bool:
        """The CAS window closes only once the callback returns authenticated."""
        for _ in range(12):
            if not await page.locator(frame_selector).count():
                return True
            await page.wait_for_timeout(500)
        return False

    async def _submit_xometry_asia(self, session, username: str, password: str) -> bool:
        """Observed Asia flow: email tab -> email + password -> consent -> submit.

        The widget opens on the phone tab, which offers only a phone number and
        a one-time code; `input#password` exists only after the email tab is
        selected. Consent starts unchecked, and the submit control is a no-op
        until it is ticked, so an unaccepted form must not be reported as a
        submitted credential.
        """
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        page = session.page
        if urlsplit(page.url).hostname != "get.xometry.asia":
            await session.goto("https://get.xometry.asia/sign_in")
        if urlsplit(page.url).hostname != "get.xometry.asia":
            return False
        email_tab = page.get_by_text("通过邮箱登录", exact=True)
        if await email_tab.count() != 1:
            return False
        await email_tab.first.click(timeout=8000)
        email_input = page.locator("input#email")
        password_input = page.locator("input#password")
        try:
            await email_input.first.wait_for(state="visible", timeout=8000)
        except PlaywrightTimeoutError:
            return False
        if await email_input.count() != 1 or await password_input.count() != 1:
            return False
        await email_input.first.fill(username)
        await password_input.first.fill(password)
        if not await self._xometry_asia_tick(page, "#accept"):
            return False
        # Not fatal: it only lengthens the refresh cookie's life.
        await self._xometry_asia_tick(page, "#remember")
        await page.get_by_role("button", name="登 录").first.click(timeout=8000)
        session.check_active()
        return await self._xometry_asia_await_outcome(page)

    @staticmethod
    async def _xometry_asia_tick(page, selector: str) -> bool:
        """Tick the visible box; both sign-in tabs render their own copy."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        options = page.locator(selector)
        for index in range(await options.count()):
            option = options.nth(index)
            if not await option.is_visible():
                continue
            if await option.is_checked():
                return True
            try:
                await option.check(timeout=5000)
            except PlaywrightTimeoutError:
                return False
            return True
        return False

    @staticmethod
    async def _xometry_asia_await_outcome(page) -> bool:
        """The SPA replaces the document on success and keeps the form on failure."""
        for _ in range(20):
            if urlsplit(page.url).path != "/sign_in":
                return True
            await page.wait_for_timeout(500)
        return False


PROVIDERS = (
    LoginProvider(
        "xometry_us",
        frozenset({"www.xometry.com", "xometry.com", "get.xometry.com", "auth.xometry.com", "login.xometry.com"}),
        frozenset(
            {
                "www.xometry.com",
                "xometry.com",
                "get.xometry.com",
                "auth.xometry.com",
                "login.xometry.com",
                "api.xometry.com",
                "assets.xometry.com",
                # Current authenticated quote-home native image previews;
                # exact business file-delivery host, not a platform entry.
                "us-files.xometry.com",
                "cdn.auth0.com",
                "fonts.gstatic.com",
                "images.prismic.io",
                "xometry-marketing.cdn.prismic.io",
                "featureassets.org",
                "prodregistryv2.org",
            }
        ),
        "https://api.xometry.com/v2/users/me",
        ("email_address", "emailAddress"),
    ),
    LoginProvider(
        "jlc_cnc_cn",
        frozenset({"www.jlc-cnc.com", "jlc-cnc.com", "passport.jlc.com"}),
        frozenset(
            {
                "www.jlc-cnc.com",
                "jlc-cnc.com",
                # CAS writes its session id on the registrable parent domain
                # (`PROD-JLC-CAS-SID`), so the stored state cannot validate
                # without it. Same organisation as the entry hosts.
                "jlc.com",
                "passport.jlc.com",
                "static-passport.jlc.com",
                "static.jlc.com",
                "static.jlc-cnc.com",
                "pbt-pub.jlc.com",
                "g.alicdn.com",
                "o.alicdn.com",
                # Aliyun risk-control widget the passport page loads on a
                # password submit. Exact hosts: the tenant prefix is fixed and
                # the widget cannot reach a verdict without them.
                "1tbpug.captcha-open.aliyuncs.com",
                "1tbpug.captcha-open-b.aliyuncs.com",
                "upload.captcha-open.aliyuncs.com",
                "upload.captcha-open-b.aliyuncs.com",
                "cloudauth-device-dualstack.cn-shanghai.aliyuncs.com",
                "cn-shanghai.device.saf.aliyuncs.com",
            }
        ),
        "https://www.jlc-cnc.com/api/cncPortal/login/queryLoginUser",
        ("userAccount", "customerCode", "customerAccountCode", "email", "emailAddress", "mobile", "phone", "casAccountCode"),
        "customerCode",
    ),
    LoginProvider(
        "xometry_asia",
        frozenset({"get.xometry.asia"}),
        frozenset(
            {
                "get.xometry.asia",
                # The sign-in mutation writes `xom_access` / `xom_refresh` on
                # the registrable parent domain, so a stored state cannot
                # validate without it. Same organisation as the entry host.
                "xometry.asia",
                "api.xometry.asia",
                "fonts.gstatic.com",
            }
        ),
        "https://api.xometry.asia/get/graphql",
        ("email", "phone"),
        identity_script=XOMETRY_ASIA_IDENTITY,
    ),
)


def resolve_provider(login_url: str, quote_url: str) -> LoginProvider:
    try:
        login_host = urlsplit(login_url).hostname
        quote_host = urlsplit(quote_url).hostname
    except (TypeError, ValueError):
        raise LoginError("PLATFORM_UNSUPPORTED_OR_UNTRUSTED") from None
    for provider in PROVIDERS:
        if login_host in provider.entry_hosts and quote_host in provider.entry_hosts:
            try:
                provider.policy.validate_url(login_url)
                provider.policy.validate_url(quote_url)
                return provider
            except Exception:
                break
    raise LoginError("PLATFORM_UNSUPPORTED_OR_UNTRUSTED")
