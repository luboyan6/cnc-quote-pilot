# Synthetic browser E2E execution notes

Initial date: 2026-10-21; independent review resumed 2026-10-22.
Task: `cnc-browser-reuse` (BR-03/04/05/06).

## Test boundary and ownership

Added only `backend/tests/cnc/browser/test_browser_e2e.py`, its same-directory `browser_fixture.html`, and this note. The synthetic deterministic adapter and intercepted server are test-only. They reuse the component's real BrowserExecutor, QuoteWorkflow, encrypted SessionCodec, official Locator and upload helpers, and the shared test-only MemoryIntents. No reference repository or provider configuration was changed.

Every browser is a new isolated headless launch; no CDP, personal profile or existing browser session is used. Initial runs explicitly used `channel="chrome"`. After the review resumed, the test-only `CNC_BROWSER_CHANNEL` selector defaults to the SDK-managed browser (`None`); setting it to `chrome` reproduces the system-channel runs. The executor's production channel policy is unchanged. Exact `https://fixture.example.com` responses are fulfilled with official Playwright routing. Any other URL falls through to the component's guard and unchanged public-only SOCKS policy. This proves browser/DOM integration, not live provider/network transport behavior. Synthetic geometry is explicit fixture data, not a parsed real CAD result. The MemoryIntents object persists across two browser launches within a test; it does not prove durable storage across application processes.

The suite is opt-in with `CNC_BROWSER_E2E=1`. The explicit E2E run must execute its cases; a default-discovery skip is not E2E acceptance. A missing Playwright/browser causes failure, not an availability skip.

## Environment and commands

Executed from `E:/AIWorkspace/cnc-quote-pilot/backend` with its `.venv/Scripts/python.exe`: Python **3.12.13**, Playwright **1.58.0**, local Chrome channel **155.0.8059.85** (installed executable version inspected). The full workflow test also emits the running Chrome version for the final run record. This channel test does not establish managed SDK Chromium installation/deployment compatibility.

```powershell
$env:CNC_BROWSER_E2E='1'
$env:CNC_BROWSER_CHANNEL='chrome'
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests/cnc/browser -p test_browser_e2e.py -v
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests/cnc/browser -p test_browser_e2e.py -k forbidden_redirect -v
& '.\.venv\Scripts\python.exe' -m basedpyright tests/cnc/browser/test_browser_e2e.py
& '.\.venv\Scripts\python.exe' -m ruff check --no-fix tests/cnc/browser/test_browser_e2e.py
& '.\.venv\Scripts\python.exe' -m ruff format --check tests/cnc/browser/test_browser_e2e.py
```

## Observed runs before core review fix

- Initial full suite: **10 tests, 64.733 s, exit 1; 9 passed, 1 error** (forbidden redirect). No skipped cases. Assertion inside BrowserExecutor scope was sanitized to `browser_failed` by the component's fixed error boundary.
- Diagnostic edit moved the redirect reason assertion outside that boundary. Targeted run: **1 test, 3.931 s, exit 1; 1 failure**. Observed `Reason.BROWSER_FAILED`, expected `Reason.POLICY_BLOCKED`. Actual page, browser and account lease release assertions passed before this failure.
- This revealed an official routing limitation: the redirected hop is not re-routed. The SOCKS allowlist still denies its destination; without a context request observer the active lease does not record the forbidden redirect. Root and independent checker were informed; only the checker owns the core fix.
- After the checker's synchronous context request observer fix: targeted redirect run **1 test, 4.039 s, exit 0, OK**. The observer records the forbidden hop; the unchanged SOCKS policy denies the connection. The Windows callback warning still occurs independently.
- Ruff lint/format and basedpyright on the E2E module: **passed**, `0 errors, 0 warnings, 0 notes` for basedpyright.
- A real native Locator-timeout test was then added to verify exactly three attempts with no mutation. Final rerun results are recorded below after the review fix; the initial ten-case count must not be reused as the final count.

## Coverage

1. Native `set_input_files`: browser File API bytes, MIME, anonymized name, length and SHA-256 are received by the synthetic endpoint; upload receipt is read from actual DOM.
2. Dynamic picker uses official `expect_file_chooser` and `set_files`; browser reads the same verified bytes.
3. Delayed disabled Apply button becomes actionable asynchronously; native `Locator.click()` auto-waits without a test sleep. Actual process/material/quantity/finish/unit controls and complete effective fields are read back.
4. QuoteWorkflow accepts a same-execution synthetic quote with exact Decimal string `123.4500`, USD, line scope, geometry and 5–7 business-day fields; cache-unverified freshness is rejected.
5. Actual Cookie/localStorage survive an encrypted export/import into a new browser. Re-authentication is mandatory before another export. Concurrent different-account browsers do not leak either value; same account admission and cross-account encrypted-state restoration are refused.
6. Expired and challenge states are read from DOM and stop before any intent/upload/configure/submit.
7. Native Locator timeout retries are bounded to three attempts and do not mutate the synthetic server.
8. Synthetic submit occurs once, then receipt loss is injected. Rebuilding the browser reads persisted synthetic remote state and reconciles only; upload/Apply/submit counts remain exactly one each.
9. Real subresource, redirect and popup requests to a forbidden host are rejected; the active session stops with a fixed reason.
10. Every case checks real page/browser closure and released admission. Cancellation uses the task that owns the browser; no production ownership guard is weakened.

## Windows callback warning observed

The initial run also emitted repeated Windows asyncio callbacks and `ResourceWarning` messages, separate from test assertions. Sanitized representative (intermediate library frames omitted):

```text
Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)
  asyncio/events.py, in _run
    self._context.run(self._callback, *self._args)
  asyncio/proactor_events.py:165, in _call_connection_lost
    self._sock.shutdown(socket.SHUT_RDWR)
ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host
ResourceWarning: unclosed transport <_ProactorSocketTransport closing ...>
browser egress policy_blocked
```

The initial real page/browser/lease cleanup assertions passed. This alone does not establish that all Windows proxy transports close cleanly. Local Python 3.12.13 source confirms `proactor_events.py:165` calls socket `shutdown()` before `close()`/server detach without an inner `finally`; the observed reset interrupts those remaining statements. This is a material transport cleanup limitation, not only verbose logging. The independent checker and root are assessing how the component should report the timeout/failure. No global exception/log suppression, stdlib patch, private socket access, private-network switch or bypass was added to the test. Rejected Chrome background connections are distinguished from forbidden page-originated requests. Raw repetitive local logs are not committed.

## Historical pre-adapter reviewed runs

- Historical system-Chrome full rerun after cleanup failures were made visible:
  **11 tests, 60.903 s, exit 1, `FAILED (errors=11)`**, as recorded by the E2E
  worker/root at the interrupted review handoff. The error count includes
  unittest subtest events and does not mean exactly eleven distinct test
  methods each failed. It is not acceptance. The former cancellation test
  caught `CancelledError` without checking its cleanup-failure note; the
  independent reviewer fixed that gap on 2026-10-22.
- The current cancellation test explicitly rejects
  `browser_cleanup_failed` in the expected cancellation's notes. Page/browser
  closure and released admission alone cannot hide proxy cleanup failure.
- SDK-managed Chromium **145.0.7632.6 / build 1208**, Playwright **1.58.0**,
  CPython **3.12.13**, was installed into the workspace runtime cache by the
  main session. Independent targeted checks on 2026-10-22: normal workflow
  **1 PASS / 2.156 s**; strict cancellation **1 PASS / 1.227 s**; forbidden
  redirect **1 ERROR / 3.423 s**, with the same Proactor 10054/unclosed transport
  followed by the component's explicit `browser_cleanup_failed`.
- The three targeted processes ran concurrently and additionally exposed
  existing shared application-log rotation contention (`WinError 32`). The
  complete managed-browser rerun uses one process to remove this confounder;
  no application logging behavior was changed.
- Complete managed-browser run in one process: **11 tests, 27.634 s, exit 1;
  10 passed, 1 error, 0 skipped**. Only
  `test_forbidden_redirect_is_blocked_and_resources_release` errored, at
  executor context exit with `browser_cleanup_failed`, following the same
  Proactor 10054 and unclosed socket/transport warnings. The other ten cases,
  including strict cancellation, passed. The single-process run had no
  `WinError 32` logging contention. Its raw local diagnostics remain in the
  private temporary `cnc-br-managed-e2e-2026-10-22.log` and are not committed.
- **At that pre-adapter stage, browser acceptance failed and BR-03 was not
  passed.** SDK-matched Chromium established ordinary upload/quote/cancellation
  behavior but did not eliminate forbidden-redirect transport cleanup failure.
  Subsequent repair and final complete results are recorded below; no success
  assertion or cleanup failure was weakened.

Managed-browser command (backend working directory):

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='E:/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/playwright-browsers'
$env:CNC_BROWSER_E2E='1'
$env:CNC_BROWSER_CHANNEL=''
& '.venv/Scripts/python.exe' -B -m unittest discover -s tests/cnc/browser -p test_browser_e2e.py -v
```

## Reviewed Windows adapter and current results (2026-10-22)

The design was amended before implementation of a local Windows accepted-stream
adapter. It uses public socket acceptance/detach and Streams ownership, handles
only the owned socket's exact shutdown reset 10054, and recognizes terminal
read reset 64 only as the identical public reader exception. Independent shutdown
outcomes retain unexpected shutdown errors. No system runtime/private transport
patch, global filter, DNS/SOCKS rewrite, network bypass, or assertion weakening
was used. The earlier failed runs above remain historical evidence.

Independent complete verification after that implementation:

| Check | Actual result |
| --- | --- |
| Unit/Mock/local TCP, including 16 Windows ownership/reset cases | 62 discovered, 61 PASS, 1 OS symlink UNVERIFIED skip; 1.444 s |
| Ruff lint and format | PASS; 18 files already formatted |
| Existing configured basedpyright, all core and browser tests | PASS; 0 errors, 0 warnings, 0 notes |
| Managed Chromium 145.0.7632.6/build1208, complete E2E | 11 PASS, 23.707 s, exit 0, no skips |
| System Chrome 155.0.8059.85, complete original-environment reproduction | 11 PASS, 37.981 s, exit 0, no skips |

Strict cancellation now rejects a cleanup-failure note. Managed-browser output
contained the expected fixed policy-refusal warning and no Proactor/resource
warning. System Chrome's returned final 90 log lines contained expected fixed
background policy refusals, all remaining test successes and the passing summary.
The main session subsequently read both logs completely with a normal tool
worker (Chrome: 205 lines / 6296 tokens; managed: 20 lines / 515 tokens) and
confirmed no resource/Proactor/reset/cleanup/logging errors or traceback/failure
markers anywhere. Logs are private
temporary files named `cnc-br-managed-e2e-fixed-2026-10-22.log` and
`cnc-br-chrome-e2e-fixed-2026-10-22.log` under the process's `TEMP` directory.

The fresh command to scan those entire logs was **not executed**: process creation
failed with `CreateProcessWithLogonW ... 1909` before starting the scan. This is a
new tool environment limitation, not a failure of the completed browser runs.
No account, privilege or operating-system setting was changed. The main session
completed the read-only scan using its ordinary working execution tool. Its scan
of `ResourceWarning|_ProactorBasePipeTransport|browser_cleanup_failed|Logging error|WinError|Exception in callback|ConnectionResetError|Traceback|FAILED`
returned no matches in either complete log. The scan is therefore verified;
the child's one process-creation failure is retained as a transient tool event.

The main session's separate sandbox-external retry of the original OS symlink
test also remained skipped: one test, 0.023 s, `OK (skipped=1)`, with the same
unavailable-privilege reason. No account/privilege setting changed. This required
BR-04 case remains unverified and is not part of the passing browser E2E count.

## Live acceptance remaining

RapidDirect and Xometry US E2/E3, real login/session/device binding, real STEP parser/geometry, effective provider fields, fresh true price/lead time, production durable IntentStore, production leases/egress deployment and human-handoff UI: **未验证**. These fixtures cannot mark original task-01–05 live gates complete. No real credentials, CAD upload, provider submission, order, payment or challenge bypass was attempted.
