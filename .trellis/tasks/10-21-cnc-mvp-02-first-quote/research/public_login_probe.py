"""Read-only disposable browser probe. Never reads saved accounts or submits login."""

import asyncio
import json
import sys
from urllib.parse import urlsplit

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as sdk:
        browser = await sdk.chromium.launch(headless=True)
        try:
            for url in sys.argv[1:] or ("https://www.xometry.com/quoting/home/", "https://www.jlc-cnc.com/cncOrder/#/placeOrder"):
                context = await browser.new_context()
                page = await context.new_page()
                hosts = set()
                page.on("request", lambda request: hosts.add(urlsplit(request.url).hostname))
                try:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    except Exception:
                        # A slow analytics resource does not erase an already
                        # rendered public login document from this observation.
                        pass
                    await page.wait_for_timeout(4000)
                    if "passport.jlc.com" in url:
                        await page.get_by_role("button", name="账号登录", exact=True).click(timeout=5000)
                        await page.wait_for_timeout(1000)
                    if "xometry.com" in url:
                        login = page.get_by_text("Log In", exact=True)
                        if await login.count() == 1:
                            await login.click(timeout=10000, no_wait_after=True, force=True)
                            await page.wait_for_timeout(4000)
                    if "jlc-cnc.com" in url:
                        login = page.get_by_role("button", name="登录", exact=True)
                        try:
                            await login.wait_for(state="visible", timeout=15000)
                            await login.click(timeout=5000, no_wait_after=True, force=True)
                            await page.wait_for_timeout(3000)
                        except Exception:
                            pass
                    print(json.dumps({"entry": url, "origin": urlsplit(page.url).hostname,
                                      "path": urlsplit(page.url).path, "hosts": sorted(host for host in hosts if host),
                                      "body": (await page.locator("body").inner_text())[:4500],
                                      "frames": [{"host": urlsplit(frame.url).hostname, "path": urlsplit(frame.url).path,
                                                  "body": (await frame.locator("body").inner_text(timeout=3000))[:2500],
                                                  "inputs": await frame.locator("input").evaluate_all("ns=>ns.map(n=>({name:n.name,id:n.id,type:n.type,placeholder:n.placeholder}))")}
                                                 for frame in page.frames if urlsplit(frame.url).hostname in {"passport.jlc.com", "login.xometry.com", "www.xometry.com"}],
                                      "scripts": await page.locator("script[src]").evaluate_all("nodes => nodes.map(n => n.src).filter(s=>s.includes('jlc')||s.includes('instant-quote')||s.endsWith('/env.js'))"),
                                      "links": await page.locator("a").evaluate_all("nodes => nodes.filter(n=>/Log In|登录/.test(n.innerText)).map(n=>({text:n.innerText,href:n.getAttribute('href'),html:n.outerHTML.slice(0,500)}))"),
                                      "controls": await page.locator("input,button,form").evaluate_all(
                                          "nodes => nodes.filter(n=>n.checkVisibility()).map(n => ({tag:n.tagName,id:n.id,type:n.type,name:n.name,"
                                          "placeholder:n.placeholder,label:n.getAttribute('aria-label'),text:n.innerText?.slice(0,120)}))")}, ensure_ascii=False), flush=True)
                except Exception as exc:
                    print(json.dumps({"entry": url, "error": type(exc).__name__, "hosts": sorted(host for host in hosts if host)}, ensure_ascii=False), flush=True)
                finally:
                    await context.close()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
