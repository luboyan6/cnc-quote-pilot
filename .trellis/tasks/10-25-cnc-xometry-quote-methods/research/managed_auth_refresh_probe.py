"""One owned, same-origin GET refresh probe; no credentials or quote actions."""

import asyncio
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from managed_auth_diagnostic import (
    DOM_FLAGS,
    EXPECTED_HASH,
    Diagnostic,
    DiagnosticActivity,
    DiagnosticExecutor,
    DiagnosticProvider,
    LoginError,
    LoginManager,
    QuoteRepository,
    async_engine,
    exception_category,
    resolve_provider,
)
from playwright.async_api import Error as PlaywrightError

REFRESH_GET = """async () => {
  try {
    const response = await fetch('/api/auth/refresh', {
      method: 'GET', credentials: 'include', cache: 'no-store',
      headers: {Accept: 'application/json'}, redirect: 'error',
      signal: AbortSignal.timeout(5000)
    });
    return response.status;
  } catch { return 0; }
}"""


def trusted_home(value):
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "www.xometry.com"
        and parsed.port in {None, 443}
        and not parsed.username
        and not parsed.password
        and parsed.path in {"/quoting/home", "/quoting/home/"}
    )


def settled_account(flags):
    return (
        flags["ready_state"] == "complete"
        and flags["account_header"]
        and not flags["guest_header"]
        and not flags["uploader_signin_required"]
        and not any(flags[key] for key in ("identifier_visible_count", "password_visible_count", "one_time_code_visible_count", "captcha_visible_count"))
    )


class RefreshProvider(DiagnosticProvider):
    async def verify(self, session, username):
        matched = await super().verify(session, username)
        flags = await session.page.evaluate(DOM_FLAGS)
        session.check_active()
        ready = bool(matched and trusted_home(session.page.url) and settled_account(flags))
        self.diagnostic.event("settled_account_readiness", verified=ready)
        return ready

    async def submit(self, session, username, password, quote_url):
        # The existing owner calls this hook once. Never delegate credentials or
        # repeat the GET after a timeout, redirect, or missing confirmation.
        if self.diagnostic.result["refresh_get_attempted"]:
            raise LoginError("LOGIN_ATTEMPT_UNCONFIRMED")
        if not trusted_home(session.page.url) or not trusted_home(quote_url):
            self.diagnostic.event("refresh_get_skipped", reason="TRUSTED_QUOTE_HOME_REQUIRED")
            return False
        await self.diagnostic.observe("before-explicit-refresh-get")
        session.check_active()
        self.diagnostic.result["refresh_get_attempted"] = True
        self.diagnostic.save()
        status = await session.page.evaluate(REFRESH_GET)
        session.check_active()
        self.diagnostic.event("explicit_refresh_get_response", status=status)
        await self.diagnostic.observe("after-explicit-refresh-get")
        if type(status) is not int or not 200 <= status < 300:
            return False
        await session.goto(quote_url)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            try:
                await session.page.wait_for_load_state("domcontentloaded", timeout=1000)
                flags = await session.page.evaluate(DOM_FLAGS)
                session.check_active()
                if trusted_home(session.page.url) and settled_account(flags):
                    return await self.verify(session, username)
            except PlaywrightError as error:
                category = exception_category(error)
                self.diagnostic.event("refresh_settle_read", category=category)
                if category not in {"READ_TIMEOUT", "NAVIGATION_CONTEXT_CHANGED"}:
                    raise
            await asyncio.sleep(0.5)
        await self.diagnostic.observe("refresh-reload-bounded-settle-ended")
        return False


async def main():
    diagnostic = Diagnostic()
    output = Path(__file__).with_name("managed-auth-refresh-result.json")
    sequence = 2
    while output.exists():
        output = output.with_name(f"managed-auth-refresh-result-{sequence}.json")
        sequence += 1
    diagnostic.output = output
    diagnostic.result.update({"entry_mode": "refresh-get-once", "evidence_filename": output.name, "refresh_get_attempted": False, "credential_submissions": 0})
    manager = None
    try:
        repository = QuoteRepository()
        auth = await repository.authorizer.load(1)
        snapshot = await repository.snapshot(auth, 3, 1)
        if snapshot.part_id != 4 or snapshot.payload.sha256 != EXPECTED_HASH or len(snapshot.payload.buffer) != 589942:
            raise LoginError("QUOTE_INPUT_CHANGED")
        diagnostic.result["selected_frozen_file_verified"] = True
        activity = DiagnosticActivity(repository, auth, snapshot, diagnostic, 0)

        def provider_resolver(login_url, quote_url):
            return RefreshProvider(resolve_provider(login_url, quote_url), diagnostic)

        manager = LoginManager(repository=repository.login, executor=DiagnosticExecutor(diagnostic), provider_resolver=provider_resolver, idle_seconds=90, lifetime_seconds=150)
        await manager.start(snapshot.account, quote_activity=activity)
        await asyncio.wait_for(activity.done.wait(), timeout=155)
    except Exception as error:
        value = getattr(getattr(error, "reason", None), "value", getattr(error, "reason", None))
        reason = value if isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}", value) else "MANAGED_AUTH_REFRESH_PROBE_UNAVAILABLE"
        diagnostic.result.update({"status": "STOPPED", "reason": reason})
        diagnostic.event("refresh_probe_exception", category=exception_category(error))
    finally:
        try:
            if manager is not None:
                await manager.close_all()
            diagnostic.result["manager_cleanup_completed"] = True
        except Exception:
            diagnostic.result.update({"manager_cleanup_completed": False, "status": "STOPPED", "reason": "MANAGED_AUTH_REFRESH_CLEANUP_FAILED"})
        finally:
            try:
                await async_engine.dispose()
                diagnostic.result["database_cleanup_completed"] = True
            except Exception:
                diagnostic.result["database_cleanup_completed"] = False
            diagnostic.result["finished_at"] = datetime.now(UTC).isoformat()
            diagnostic.save()
    print(json.dumps({key: diagnostic.result.get(key) for key in ("status", "reason", "evidence_filename", "refresh_get_attempted", "credential_submissions", "quote_mutations", "manager_cleanup_completed", "executor_active_count_after_exit")}))


if __name__ == "__main__":
    asyncio.run(main())
