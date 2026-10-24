"""Inspected login UI and read-only identity contracts; never infer auth from a URL.

Evidence: task02/research/login-provider-evidence-2026-10-22.md.
"""

import asyncio
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
    }
)

IDENTITY_FETCH = """async ({url, fields}) => {
  try {
    const r = await fetch(url, {credentials:'include', redirect:'error',
      signal:AbortSignal.timeout(2500), headers:{Accept:'application/json'}});
    if (!r.ok) return [];
    const body = await r.json();
    const user = body.data || body.user || body;
    if (!user || typeof user !== 'object') return [];
    return fields.map(k => user[k]).filter(v => typeof v === 'string' && v.trim());
  } catch { return []; }
}"""


@dataclass(frozen=True)
class LoginProvider:
    code: str
    entry_hosts: frozenset[str]
    hosts: frozenset[str]
    identity_url: str
    identity_fields: tuple[str, ...]

    @property
    def policy(self):
        return BrowserPolicy(self.hosts, OPTIONAL_RESOURCES - self.hosts)

    async def verify(self, session, username: str) -> bool:
        # Fetch in the guarded Page, never an independent request client that
        # bypasses context routing/proxy. Only explicit identity fields count.
        if urlsplit(session.page.url).hostname not in self.entry_hosts:
            return False
        expected = username.strip().casefold()
        for attempt in range(3):
            identities = await session.page.evaluate(IDENTITY_FETCH, {"url": self.identity_url, "fields": list(self.identity_fields)})
            session.check_active()
            if any(value.strip().casefold() == expected for value in identities):
                return True
            if identities:
                raise LoginError("IDENTITY_MISMATCH")
            if attempt < 2:
                await asyncio.sleep(0.5)
        return False

    async def submit(self, session, username: str, password: str, quote_url: str) -> bool:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        try:
            return await self._submit(session, username, password, quote_url)
        except PlaywrightTimeoutError:
            # Missing/changed controls and challenges preserve the visible page
            # for its human owner. Never resubmit an uncertain login attempt.
            return False

    async def _submit(self, session, username: str, password: str, quote_url: str) -> bool:
        page = session.page
        if self.code == "xometry_us":
            if urlsplit(page.url).hostname != "login.xometry.com":
                await session.goto("https://www.xometry.com/account/login/")
            if urlsplit(page.url).hostname != "login.xometry.com":
                return False
            identifier = page.locator('input#username[name="username"]')
            if await identifier.count() != 1 or not await identifier.is_visible():
                return False
            await identifier.fill(username)
            await page.get_by_role("button", name="Continue", exact=True).click(timeout=8000)
            password_input = page.locator('input#password[name="password"]')
            try:
                await password_input.wait_for(state="visible", timeout=8000)
            except Exception:
                return False
            if await password_input.count() != 1:
                return False
            await password_input.fill(password)
            await page.get_by_role("button", name="Continue", exact=True).click(timeout=8000)
            session.check_active()
            return True
        if self.code == "jlc_cnc_cn":
            # Keep the native CNC CAS callback/appId: its SDK opens this iframe
            # and exchanges the authentication code in the original quote page.
            if urlsplit(page.url).hostname != "www.jlc-cnc.com":
                await session.goto(quote_url)
            skip = page.get_by_role("button", name="跳过", exact=True)
            if await skip.count() == 1 and await skip.is_visible():
                await skip.click(timeout=3000)
            await page.get_by_role("button", name="登录", exact=True).click(timeout=8000)
            await page.locator("iframe#jlc-cas-login-window").wait_for(state="visible", timeout=8000)
            frame = page.frame_locator("iframe#jlc-cas-login-window")
            await frame.get_by_role("button", name="账号登录", exact=True).click(timeout=5000)
            identifier = frame.get_by_placeholder("请输入手机号码 / 客户编号 / 邮箱", exact=True)
            password_input = frame.get_by_placeholder("请输入登录密码", exact=True)
            if await identifier.count() != 1 or await password_input.count() != 1:
                return False
            await identifier.fill(username)
            await password_input.fill(password)
            await frame.get_by_role("button", name="登录", exact=True).click(timeout=8000)
            session.check_active()
            return True
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
        frozenset({"www.jlc-cnc.com", "jlc-cnc.com", "passport.jlc.com", "static-passport.jlc.com", "static.jlc.com", "static.jlc-cnc.com", "pbt-pub.jlc.com", "g.alicdn.com", "o.alicdn.com"}),
        "https://www.jlc-cnc.com/cncPortal/login/queryLoginUser",
        ("userAccount", "customerCode", "email", "emailAddress", "mobile", "phone", "casAccountCode"),
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
