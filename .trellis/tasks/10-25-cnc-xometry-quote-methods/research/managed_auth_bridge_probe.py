"""Redacted same-owner login/callback diagnostics; never uploads a drawing.

Uses the actual final provider (one credential delegation at most). Inspect
cookie rejection reasons and app variants, without recording cookie values,
request bodies/headers, tokens, or account identifiers.
"""

import asyncio
import json
import re
from datetime import UTC, datetime

from managed_auth_diagnostic import (
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


class BridgeDiagnostic(Diagnostic):
    def __init__(self):
        super().__init__(fresh_context=True)
        stem = "managed-auth-bridge-result-2026-10-26"
        self.output = self.output.with_name(f"{stem}.json")
        sequence = 2
        while self.output.exists():
            self.output = self.output.with_name(f"{stem}-{sequence}.json")
            sequence += 1
        self.result.update({"entry_mode": "final-provider-callback-diagnostics", "evidence_filename": self.output.name})

    async def attach_cookie_diagnostics(self, session):
        client = await session.page.context.new_cdp_session(session.page)
        await client.send("Network.enable")

        def extra_info(event):
            # Ignore all headers/cookieLine/cookie.value fields. Preserve only
            # finite rejection categories and whether the UI cookie was blocked.
            for blocked in event.get("blockedCookies", []):
                cookie = blocked.get("cookie", {})
                reasons = [reason for reason in blocked.get("blockedReasons", []) if re.fullmatch(r"[A-Za-z]{1,80}", reason)]
                self.event("response_cookie_rejected", identity_cache=cookie.get("name") == "_identity_cache", reasons=reasons)

        client.on("Network.responseReceivedExtraInfo", extra_info)

    async def observe(self, stage):
        observed = await super().observe(stage)
        if not observed or self.session is None:
            return observed
        session = self.session
        try:
            flags = await session.page.evaluate("""() => ({
              app_variant: [...document.scripts].some(s => new URL(s.src || location.href).pathname.startsWith('/_next/'))
                ? 'next' : [...document.scripts].some(s => s.src.includes('/resources/instant-quote-app.')) ? 'legacy' : 'other',
              identity_cache_present: document.cookie.split(';').some(c => c.trim().split('=', 1)[0] === '_identity_cache'),
              ready_state: document.readyState
            })""")
            session.check_active()
            cookies = await session.page.context.cookies(["https://www.xometry.com/quoting/home/"])
            session.check_active()
            flags["identity_cache_in_context"] = any(cookie["name"] == "_identity_cache" for cookie in cookies)
            self.event("auth_bridge_flags", stage=stage, **flags)
        except Exception as error:
            self.event("auth_bridge_read_unavailable", stage=stage, category=exception_category(error))
        return observed


class BridgeExecutor(DiagnosticExecutor):
    # Keep the existing executor and account owner, including its guarded proxy.
    def session(self, scope, policy, *, encrypted_state=None):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def attached():
            async with super(BridgeExecutor, self).session(scope, policy, encrypted_state=encrypted_state) as session:
                await self.diagnostic.attach_cookie_diagnostics(session)
                yield session

        return attached()


async def main():
    diagnostic = BridgeDiagnostic()
    manager = None
    try:
        repository = QuoteRepository()
        auth = await repository.authorizer.load(1)
        snapshot = await repository.snapshot(auth, 3, 1)
        if snapshot.part_id != 4 or snapshot.payload.sha256 != EXPECTED_HASH or len(snapshot.payload.buffer) != 589942:
            raise LoginError("QUOTE_INPUT_CHANGED")
        await repository.assert_upload_available(snapshot)
        diagnostic.result["selected_frozen_file_verified"] = True
        activity = DiagnosticActivity(repository, auth, snapshot, diagnostic, 0)

        def provider_resolver(login_url, quote_url):
            return DiagnosticProvider(resolve_provider(login_url, quote_url), diagnostic)

        manager = LoginManager(repository=repository.login, executor=BridgeExecutor(diagnostic), provider_resolver=provider_resolver, idle_seconds=90, lifetime_seconds=150)
        await manager.start(snapshot.account, quote_activity=activity)
        await asyncio.wait_for(activity.done.wait(), timeout=155)
    except Exception as error:
        reason = getattr(getattr(error, "reason", None), "value", getattr(error, "reason", None))
        safe_reason = reason if isinstance(reason, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}", reason) else "AUTH_BRIDGE_PROBE_UNAVAILABLE"
        diagnostic.result.update({"status": "STOPPED", "reason": safe_reason})
        diagnostic.event("auth_bridge_probe_exception", category=exception_category(error))
    finally:
        try:
            if manager is not None:
                await manager.close_all()
            diagnostic.result["manager_cleanup_completed"] = True
        except Exception:
            diagnostic.result.update({"manager_cleanup_completed": False, "status": "STOPPED", "reason": "AUTH_BRIDGE_CLEANUP_FAILED"})
        finally:
            await async_engine.dispose()
            diagnostic.result["finished_at"] = datetime.now(UTC).isoformat()
            diagnostic.save()
    print(json.dumps({key: diagnostic.result.get(key) for key in ("status", "reason", "quote_mutations", "evidence_filename", "manager_cleanup_completed", "executor_active_count_after_exit")}))


if __name__ == "__main__":
    asyncio.run(main())
