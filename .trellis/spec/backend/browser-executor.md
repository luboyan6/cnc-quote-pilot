# Shared browser execution contract

## 1. Scope / trigger

Read before changing `backend/app/modules/cnc/browser/` or integrating a provider, state store, account lease, agent or monitoring runner. The component belongs to `cnc-browser-reuse`; 02/03 own real provider adapters and durable application stores, 04 owns scheduling/leases, 05 owns UI and integrated acceptance. See [design](../../../docs/browser-implementation-design.md) and [results](../../../docs/browser-test-report.md).

This component is not an activated provider workflow, complete S01–S11 runner, agent factory, scheduler or handoff UI. Research JSON stays draft/automation_disabled until real gates pass. Both reference repositories are read-only.

## 2. Signatures

Source owners:

- `contracts.py`: `SessionScope(owner_id, platform_code, account_id)`, `Parameters.from_mapping(values)`, typed authentication/geometry/receipts, `PlatformAdapter`, mandatory `IntentStore`.
- `session.py`: `BrowserExecutor(codec, capacity=1, channel=None, timeout_ms=15000)`, async `session(...)`, `BrowserSession.confirm_authentication(...)` and `export_encrypted_state()`.
- `state.py`: `SessionCodec(crypto)` with `seal(scope, state, policy)` / `open(scope, ciphertext, policy)`; production injects existing `CryptoUtil` rather than another cipher.
- `policy.py`: `BrowserPolicy(frozenset(allowed_hosts))`, `validate_url(url)`, `resolve(host)`.
- D-18 optional-resource extension: `BrowserPolicy(allowed_hosts, blocked_resource_hosts=frozenset())`; reviewed exact analytics/QR subresources/subframes are aborted without taint, but never allowed to resolve/connect. Top-level navigation, unknown hosts and all DNS rules remain strict; empty default preserves previous behavior. See [login contract](cnc-account-login.md).
- `files.py`: `TrustedStep(...).read_verified()`, `upload_step(locator, payload)`, `upload_step_with_chooser(page, trigger, payload)`.
- `workflow.py`: `QuoteWorkflow(intents, ...)`, `execute(session, adapter, request)`, `read_with_retry(...)`, `validate_quote(...)`.
- `windows_streams.py`: `start_windows_server(handler)` / `WindowsStreamServer.close()` / `wait_closed()`; Windows-only listener adapter consumed by the vendored proxy, not a public remote server.

The adapter is trusted engineering code; its Page/Context and upload buffers are never model tools or checkpoint data. No default/global account key, personal CDP context or in-memory production intent store is provided.

## 3. Contracts

- Same-loop ownership and fail-fast account/capacity admission are process-local; production multi-process execution needs the application's durable lease. Every owned resource must be released on normal exit, failure and cancellation.
- Proxy handler/server close timeouts must propagate to the executor's fixed cleanup-failure reason while other resources are still attempted. Windows/Python 3.12.13 E2E exposed Proactor shutdown errors preceding socket.close/server detach. The local adapter accepts only its own loopback sockets through public `sock_accept`/`detach`, then transfers ownership through `asyncio.open_connection(sock=...)`; Unix retains `asyncio.start_server`. Never inspect or manually close a socket behind an existing transport, patch the runtime, or add a global exception filter.
- Only the owned accepted socket's exact `ConnectionResetError(winerror=10054)` may bypass redundant shutdown so standard close can continue. A terminal `wait_closed` read reset 64 is recognized only if it is the identical exception already exposed by public `reader.exception()`, after writer close. The socket's independent shutdown-outcome record still makes unexpected shutdown errors fail cleanup; expected read reset must not mask them. Track raw sockets even for tasks cancelled before first execution, and wrapper tasks through actual writer closure. Functional assertions alone never pass BR-03.
- Encrypt the whole versioned scope/state envelope; reject scope mismatches and off-policy cookie/origin domains before browser launch. Use `storage_state(indexed_db=True)` in memory after verified authentication. Session storage/device-bound authentication needs separate provider validation.
- Exact trusted hostnames, HTTPS/443 only, all DNS answers public; explicitly reject IPv6 site-local addresses (`fec0::/10`) as well as private/reserved/link-local/loopback/multicast/unspecified addresses. Python 3.12 can label site-local as `is_global=True`, so that property alone is insufficient. Context routing intercepts supported requests, context-scoped request observation marks forbidden redirected requests as policy stops, and the independently reused MIT proxy rejects actual connections. Do not assume route handlers run for every redirect hop. Service Workers/downloads/unreviewed WebSockets are disabled. No production private-network override for tests or global session taint from unrelated Chrome background refusals.
- Root, expected bytes/hash, parameters, account and platform come from server-side ACL/config. Read and hash STEP bytes once; pass the verified buffer to the official SDK, not a path reopened by the browser. Platform adapters must pass their verified conservative upload limit.
- Atomic durable `IntentStore.claim` commits before granting mutation. Uniqueness is scope/item/generation/operation; fingerprint conflicts cannot create another claim. Freeze file/parameters across the item's generations; changed parameters require a new item. Upload, configure Apply/save and submit are all mutations.
- Confirmed receipts may be re-read; claimed/uncertain records only reconcile through read-only methods or stop for human help. Never delete a claim to retry. Cancellation/receipt-store failure cannot replay a remote mutation. Retry only reviewed read operations, at most two retries/three attempts; preserve outer item/time/recovery budgets in the domain runner.
- Successful quotes require same scope/item/generation/file/upload/submission, exact complete requested/effective parameters, positive finite Decimal money, known currency/price scope/lead time, positive geometry and explicit verified freshness. Time proximity alone does not establish a current quote. Reject unverified cache; recalculation must belong to the current execution, while current confirmation requires actual provider evidence.
- `BrowserStop.reason` is fixed and safe to expose; do not append raw exceptions, URLs, DOM, credentials or token-bearing query/fragment. Real traces/screenshots are private authorized diagnostics, not automatically safe for models/public storage.

## 4. Validation and error matrix

| Input / event | Required observable result |
| --- | --- |
| Empty scope / changed state owner | Reject before launch or upload |
| Unknown host, userinfo URL, HTTP, private/mixed/site-local DNS, metadata or disallowed redirect/subresource | Policy stop; no connection to forbidden destination |
| STEP path escape, wrong size/hash/header, oversize | File stop; no file-control action |
| Expired auth, challenge, wrong identity | Auth/human stop before upload; no bypass |
| Read timeout | At most three attempts; cancellation propagates |
| Upload/configure/submit timeout or cancellation | Keep claimed/uncertain intent; reconcile or human, no automatic repeat |
| Changed item fingerprint / duplicate mutation key | Conflict or reuse confirmed receipt, no repeat |
| Effective-field mismatch, zero geometry, float/NaN/missing money or unknown lead time | No QUOTED result |
| Old/unverified cache or recalculated timestamp before execution | No QUOTED result |
| Cleanup component fails | Attempt remaining cleanup, report fixed cleanup failure |
| Windows accepted socket peer reset / already-delivered read reset | Complete bounded writer/listener/task cleanup; unexpected shutdown errors must still fail, including alongside a recognized read reset |

## 5. Good / base / bad cases

- Good: verified adapter uses native Locators and official upload helpers; returns real receipt/geometry/complete effective fields; result validator accepts exact Decimal and current evidence; caller then persists the domain evidence transaction.
- Base: synthetic Chromium E2E passes while platform geometry/quotes remain unverified. Report both levels separately and retain original F/S/M/D live gates.
- Bad: assume a fresh observation timestamp, upload row, catalog auto-price flag, Mock or historical SDK probe establishes a current real quote or automatic model recovery.

## 6. Tests required

Use `backend/tests/cnc/browser/` for isolated unit/Mock, real local TCP ownership/reset regressions and opt-in real Chromium synthetic tests; the final command/count belongs in the report. Cover exact identities, encrypted state isolation/expiry, domain/actual DNS refusal, STEP bytes, full parameter/Decimal/lead-time/freshness checks, read caps, intent replay/cancellation and resource release. Windows regressions must include pre-start cancellation, Streams handoff failure/cancellation, actual peer reset, listener/port release, and unknown shutdown errors alongside a recognized read reset. Do not import the full site's DB/Redis pytest fixtures just to test this independent component.

An OS symlink test skipped for unavailable Windows privilege does not pass the file-boundary criterion. Run the unchanged `test_policy_files_state.FileTests.test_symlink_escape_rejected` on a permitted local Linux runner instead; verify one test actually executed, zero skips, and the unchanged source hash. From `backend`, with the Linux test environment installed, `python -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k symlink -v` is the narrow entry point. Record Windows and Linux results separately. A Linux unit-test pass does not establish Linux Chromium/container deployment. The 2026-10-22 runner setup and exact offline dependency evidence are in the task's [Linux validation record](../../tasks/10-21-cnc-browser-reuse/research/linux-validation-2026-10-22.md); isolated runner dependencies do not change application pins.

Production `IntentStore`, cross-process account lease, real provider login/STEP/quote semantics, actual model recovery, managed deployment browser and scheduled monitoring each need their own integration/live acceptance; in-test stores and intercepted synthetic HTTPS pages do not pass them.

## 7. Wrong vs correct

```python
# Wrong: a mutation timeout or near-current timestamp does not authorize retry/success.
await read_with_retry(lambda: adapter.submit(session, upload, params))

# Correct: QuoteWorkflow owns mutation intents; retries are for reviewed reads only.
quote = await QuoteWorkflow(durable_intents).execute(session, adapter, request)
```

Third-party maintenance: retain the standalone DeerFlow proxy's MIT license, fixed commit/path and exact local adaptation notes. Never copy its runtime/config/tool/Ref framework just to reuse SDK operations. New adapters consume this shared executor rather than creating another browser/session/upload engine.
