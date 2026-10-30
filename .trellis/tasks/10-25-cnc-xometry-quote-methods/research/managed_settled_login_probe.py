"""Observe settled native quote UI before the owner's post-login navigation.

One normal login attempt; no file upload, parameter save or quote submission.
Reuse the existing guarded executor, frozen input checks and account lease.
"""

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime

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
from managed_auth_refresh_probe import settled_account, trusted_home


class SettledProvider(DiagnosticProvider):
    async def submit(self, session, username, password, quote_url):
        submitted = await super().submit(session, username, password, quote_url)
        self.diagnostic.event("single_normal_submit_returned", submitted=bool(submitted))
        # Even a successful click can finish before the new application has
        # hydrated. Only inspect this same Page; never repeat credentials.
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(2)
            await self.diagnostic.observe(f"same-page-settled-login-{attempt + 1}")
            session.check_active()
            if trusted_home(session.page.url):
                flags = await session.page.evaluate(DOM_FLAGS)
                if settled_account(flags):
                    matched = await self.provider.verify(session, username)
                    self.diagnostic.event("same-page-positive-ui-and-identity", verified=bool(matched))
                    return matched
        self.diagnostic.event("same-page-settled-login-not-established")
        return False


class ReadinessActivity(DiagnosticActivity):
    async def advance(self, session, provider):
        await self.check_inputs()
        for attempt in range(3):
            if attempt:
                await asyncio.sleep(1)
            await self.diagnostic.observe(f"post-owner-navigation-settle-{attempt + 1}")
            flags = await session.page.evaluate(DOM_FLAGS)
            session.check_active()
            if trusted_home(session.page.url) and settled_account(flags):
                break
        else:
            raise LoginError("MANAGED_QUOTE_UI_NOT_SETTLED")
        if not await provider.verify(session, self.snapshot.account.username):
            raise LoginError("QUOTE_PAGE_IDENTITY_REQUIRED")
        launch = session.page.locator("#dashboard-get-instant-quote-primary")
        if await launch.count() != 1 or not await launch.is_visible() or not await launch.is_enabled() or (await launch.inner_text()).strip() != "Get an Instant Quote":
            raise LoginError("MANAGED_UPLOAD_ENTRY_UNAVAILABLE")
        await self.check_inputs()
        self.diagnostic.event("native-uploader-open-attempted-once")
        await launch.click(timeout=3000, no_wait_after=True)
        await asyncio.sleep(1)
        await self.diagnostic.observe("settled-primary-uploader")
        if not trusted_home(session.page.url):
            raise LoginError("MANAGED_UPLOAD_ENTRY_UNAVAILABLE")
        flags = await session.page.evaluate(DOM_FLAGS)
        inputs = session.page.locator('input[type="file"]')
        count = await inputs.count()
        accept = await inputs.get_attribute("accept") if count == 1 else None
        self.diagnostic.result.update({
            "status": "UPLOADER_READY" if settled_account(flags) and count == 1 else "UPLOADER_NOT_READY",
            "reason": "UPLOADER_SIGNIN_REQUIRED" if flags["uploader_signin_required"] else "SETTLED_UI_INSPECTED",
            "identity_match": True,
            "primary_file_input_count": count,
            "primary_file_accept": accept,
            "quote_mutations": 0,
        })
        self.terminal = True
        self.done.set()
        self.diagnostic.save()


async def main(app_login=False):
    diagnostic = Diagnostic(app_login=app_login, fresh_context=True)
    filename = "managed-settled-app-login-result-2026-10-26" if app_login else "managed-settled-login-result-2026-10-26"
    diagnostic.output = diagnostic.output.with_name(f"{filename}.json")
    sequence = 2
    while diagnostic.output.exists():
        diagnostic.output = diagnostic.output.with_name(f"{filename}-{sequence}.json")
        sequence += 1
    diagnostic.result.update({"entry_mode": "native-app-login-then-settled-ui" if app_login else "single-normal-login-then-settled-ui", "evidence_filename": diagnostic.output.name})
    manager = None
    try:
        repository = QuoteRepository()
        auth = await repository.authorizer.load(1)
        snapshot = await repository.snapshot(auth, 3, 1)
        if snapshot.part_id != 4 or snapshot.payload.sha256 != EXPECTED_HASH or len(snapshot.payload.buffer) != 589942:
            raise LoginError("QUOTE_INPUT_CHANGED")
        await repository.assert_upload_available(snapshot)
        diagnostic.result["selected_frozen_file_verified"] = True
        activity = ReadinessActivity(repository, auth, snapshot, diagnostic, 0)

        def provider_resolver(login_url, quote_url):
            return SettledProvider(resolve_provider(login_url, quote_url), diagnostic)

        manager = LoginManager(repository=repository.login, executor=DiagnosticExecutor(diagnostic), provider_resolver=provider_resolver, idle_seconds=90, lifetime_seconds=150)
        await manager.start(snapshot.account, quote_activity=activity)
        await asyncio.wait_for(activity.done.wait(), timeout=155)
    except Exception as error:
        reason = getattr(getattr(error, "reason", None), "value", getattr(error, "reason", None))
        safe_reason = reason if isinstance(reason, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}", reason) else "SETTLED_LOGIN_PROBE_UNAVAILABLE"
        diagnostic.result.update({"status": "STOPPED", "reason": safe_reason})
        diagnostic.event("settled_login_probe_exception", category=exception_category(error))
    finally:
        try:
            if manager is not None:
                await manager.close_all()
            diagnostic.result["manager_cleanup_completed"] = True
        except Exception:
            diagnostic.result.update({"manager_cleanup_completed": False, "status": "STOPPED", "reason": "SETTLED_LOGIN_CLEANUP_FAILED"})
        finally:
            await async_engine.dispose()
            diagnostic.result["finished_at"] = datetime.now(UTC).isoformat()
            diagnostic.save()
    print(json.dumps({key: diagnostic.result.get(key) for key in ("status", "reason", "identity_match", "primary_file_input_count", "quote_mutations", "evidence_filename", "manager_cleanup_completed", "executor_active_count_after_exit")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-login", action="store_true", help="Use the official application's reviewed login callback builder.")
    asyncio.run(main(parser.parse_args().app_login))
