"""Anonymous, read-only login-page check through the production egress guard."""

import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))

from app.modules.cnc.browser.contracts import SessionScope
from app.modules.cnc.browser.session import BrowserExecutor
from app.modules.cnc.browser.state import SessionCodec
from app.modules.cnc.login.providers import PROVIDERS
from app.utils.crypto_util import CryptoUtil


async def main():
    executor = BrowserExecutor(SessionCodec(CryptoUtil))
    for index, provider in enumerate(PROVIDERS):
        unknown = set()
        try:
            async with executor.session(SessionScope("public-probe", provider.code, "anonymous"), provider.policy) as session:
                page = session.page

                def observe(request):
                    host = urlsplit(request.url).hostname
                    if host and host not in provider.hosts and not provider.policy.blocks_optional_resource(request):
                        unknown.add(host)

                page.context.on("request", observe)
                await session.goto("https://www.xometry.com/account/login/" if index == 0 else "https://www.jlc-cnc.com/cncOrder/#/placeOrder")
                if index == 1:
                    skip = page.get_by_role("button", name="跳过", exact=True)
                    if await skip.count() == 1 and await skip.is_visible():
                        await skip.click(timeout=3000)
                    await page.get_by_role("button", name="登录", exact=True).click(timeout=15000)
                    await page.locator("iframe#jlc-cas-login-window").wait_for(state="visible", timeout=10000)
                    await page.frame_locator("iframe#jlc-cas-login-window").get_by_role("button", name="账号登录", exact=True).click(timeout=10000)
                await page.wait_for_timeout(1500)
                session.check_active()
                print(json.dumps({"platform": provider.code, "result": "PUBLIC_LOGIN_PAGE_VISIBLE", "origin": urlsplit(page.url).hostname,
                                  "unknown_hosts": sorted(unknown)}, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"platform": provider.code, "result": getattr(exc, "reason", type(exc).__name__),
                              "unknown_hosts": sorted(unknown)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
