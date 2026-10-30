"""Inspect one source-grounded auth-refresh GET in the guarded restored owner.

No credential delegation, explicit cookie writes, uploads or quote mutations. Response
content is reduced in the browser to content type and reviewed JSON key flags.
"""

import asyncio
import json
import re
from datetime import UTC, datetime

from managed_auth_bridge_probe import BridgeDiagnostic, BridgeExecutor
from managed_auth_diagnostic import (
    EXPECTED_HASH,
    DiagnosticActivity,
    DiagnosticProvider,
    LoginError,
    LoginManager,
    QuoteRepository,
    async_engine,
    exception_category,
    resolve_provider,
)
from managed_auth_refresh_probe import trusted_home

REFRESH_SHAPE = """async () => {
  try {
    const r = await fetch('/api/auth/refresh', {
      method:'GET', credentials:'include', cache:'no-store',
      headers:{Accept:'application/json'}, signal:AbortSignal.timeout(5000)
    });
    const type = (r.headers.get('content-type') || '').split(';')[0];
    const jsonResponse = type === 'application/json';
    const body = jsonResponse ? await r.json() : null;
    return {status:r.status, redirected:r.redirected, content_type:['application/json','text/html','text/plain'].includes(type) ? type : 'other',
      json_object:!!body && typeof body === 'object' && !Array.isArray(body),
      expires_in_seconds_number:typeof body?.expiresInSeconds === 'number',
      error_key_present:!!body && Object.hasOwn(body,'error')};
  } catch {return {status:0, content_type:'unavailable'};}
}"""


class ContractProvider(DiagnosticProvider):
    async def verify(self, session, username):
        # This probe must inspect refresh even if the legacy identity matches.
        matched = await super().verify(session, username)
        if matched and trusted_home(session.page.url) and not self.diagnostic.result.get("refresh_get_attempted"):
            await self.diagnostic.observe("before-refresh-contract-read")
            self.diagnostic.result["refresh_get_attempted"] = True
            self.diagnostic.event("refresh_contract_get_attempted_once", identity_match=True)
            shape = await session.page.evaluate(REFRESH_SHAPE)
            session.check_active()
            self.diagnostic.result["refresh_contract"] = shape
            await self.diagnostic.observe("after-refresh-contract-read")
        return False

    async def submit(self, session, username, password, quote_url):
        # Never delegate credentials or perform a second diagnostic GET.
        return False


async def main():
    diagnostic = BridgeDiagnostic()
    diagnostic.fresh_context = False
    stem = "managed-refresh-contract-result-2026-10-26"
    diagnostic.output = diagnostic.output.with_name(f"{stem}.json")
    sequence = 2
    while diagnostic.output.exists():
        diagnostic.output = diagnostic.output.with_name(f"{stem}-{sequence}.json")
        sequence += 1
    diagnostic.result.update({"fresh_context_requested": False, "entry_mode": "restored-owner-refresh-contract", "evidence_filename": diagnostic.output.name, "credential_submissions": 0})
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

        def resolver(login_url, quote_url):
            return ContractProvider(resolve_provider(login_url, quote_url), diagnostic)

        manager = LoginManager(repository=repository.login, executor=BridgeExecutor(diagnostic), provider_resolver=resolver, idle_seconds=90, lifetime_seconds=150)
        await manager.start(snapshot.account, quote_activity=activity)
        await asyncio.wait_for(activity.done.wait(), timeout=155)
    except Exception as error:
        reason = getattr(getattr(error, "reason", None), "value", getattr(error, "reason", None))
        diagnostic.result.update({"status": "STOPPED", "reason": reason if isinstance(reason, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}", reason) else "REFRESH_CONTRACT_PROBE_UNAVAILABLE"})
        diagnostic.event("refresh_contract_probe_exception", category=exception_category(error))
    finally:
        try:
            if manager is not None:
                await manager.close_all()
            diagnostic.result["manager_cleanup_completed"] = True
        except Exception:
            diagnostic.result["manager_cleanup_completed"] = False
        finally:
            await async_engine.dispose()
            diagnostic.result["finished_at"] = datetime.now(UTC).isoformat()
            diagnostic.save()
    print(json.dumps({key: diagnostic.result.get(key) for key in ("status", "reason", "refresh_contract", "credential_submissions", "quote_mutations", "evidence_filename", "manager_cleanup_completed", "executor_active_count_after_exit")}))


if __name__ == "__main__":
    asyncio.run(main())
