# Browser implementation handoff (BR, 2026-10-21)

## Scope and ownership

This implementer changed only `backend/app/modules/cnc/`, unit/Mock fixtures and
tests in `backend/tests/cnc/browser/`, and this note. The main session owns task
revisions, dependency manifest/lock, design/report/spec files and final audit.
The separately assigned synthetic E2E worker owns `test_browser_e2e.py` and its
fixture. No reference repository, app route, database, scheduler, Agent factory,
provider config, existing user edit or global Python environment was changed.

The reviewed Trellis PRD/design/implement and `implement.jsonl` were loaded before
writing code, including the complete saved native hook output and backend/reuse
guides. The source analysis and task revisions already existed when implementation
started, preserving the required execution order. No further agent was spawned.

## Delivered symbols and reuse boundaries

| File under `backend/app/modules/cnc/browser/` | Contracts / behavior |
| --- | --- |
| `errors.py` | `Reason`, `BrowserStop`: only fixed public reason codes; no raw URL, DOM, credential or SDK error in exception strings. |
| `contracts.py` | `SessionScope`, `Parameters`, `Authentication`, geometry/receipt/quote types, `IntentStore`, `PlatformAdapter`. Provider operations are deterministic trusted methods; model tools never receive Page/Context/JS/click capabilities. |
| `files.py` | `TrustedStep.read_verified`, `StepPayload`, `upload_step`, `upload_step_with_chooser`: trusted root, extension/header/trailer/size/hash checks; official SDK buffer upload of verified immutable bytes. `max_size` is mandatory and must use a verified platform limit, not a broad implicit fallback. |
| `policy.py` | `BrowserPolicy`: exact immutable DNS host set; HTTPS/443; no credentials, encoded host escape, IP literal or wildcard; public-only all-address DNS resolver hook, rejecting mixed/private/site-local/special answers. |
| `state.py` | `SessionCodec`: inject the existing `CryptoUtil.encrypt/decrypt` via `SessionCodec(CryptoUtil)` in the later product integration. The scope and state are encrypted together, rebound on restore and kept in memory. No plaintext fallback/file/log/checkpoint. Test crypto is direct established Fernet, not a new cipher. |
| `session.py` | `BrowserExecutor.session`, `BrowserSession`: optional SDK lazy import, fresh headless Chromium/Chrome, isolated contexts, same-loop/task ownership, default capacity 1, account exclusivity even if owner changes, per-session pinned proxy. Context routes protect redirects/subresources/popups; service workers/downloads/WebSockets blocked. Auth revalidation precedes encrypted state export (`indexed_db=True`). Bounded shielded cleanup independently attempts every resource and reports cleanup failure. |
| `workflow.py` | `QuoteRequest`, `QuoteWorkflow`, `read_with_retry`, `validate_quote`: authenticate → upload → configure/Apply → full effective readback → submit → exact quote validation. Only reads retry, at most 2 retries/3 attempts with per-attempt deadline. Unknown mutations never replay. |
| `third_party/egress.py` | Independently vendored DeerFlow `BrowserEgressProxy`, using its original vetted-IP resolver hook and literal-IP connection mechanism. No SOCKS/CDP/Ref protocol rewrite or framework transplant. |

`IntentStore` is mandatory and has no application memory implementation. A
production store must durably commit a claim before the action and atomically
enforce uniqueness on `(scope, item, execution_generation, operation)`, excluding
fingerprint. It must freeze file/parameters by `(scope, item)` across generations,
and never overwrite a confirmed receipt when marking an unknown result. Changed
inputs require a new item; retrying an item retains the same generation.

Uploads, final quote submission, and configuration Apply/save each receive a
claim, so configuration reentry also cannot silently mutate the remote object.
Existing confirmed receipts can be reused after validation; CLAIMED/UNCERTAIN
records allow only adapter read-only reconciliation or a typed human-stop reason.
Timeout, cancellation, browser reconstruction, evidence/storage failure, or a
fresh workflow instance cannot grant mutation replay. The fixture `MemoryIntents`
exists only under tests and is not durable production evidence.

`QUOTED` requires nonzero Decimal geometry; exact full requested/effective
agreement; same scope/item/generation/file/upload/submission; positive finite
Decimal amount; known currency and explicit unit/line scope; nonempty lead time
with positive ordered days and explicit business/calendar basis; and aware fresh
timestamps. `QuoteFreshness` is mandatory, serialized as `RECALCULATED`,
`CURRENT_CONFIRMED`, or `CACHE_UNVERIFIED`. Cache-unverified, untyped string enum
values and stale observations are refused. Recalculation must be in this run;
CURRENT_CONFIRMED requires explicit current same-request evidence in the trusted
adapter, not a recent cache timestamp. No platform adapter/selectors are invented.

## Third-party provenance

- Source repository, read-only: `E:/AIWorkspace/deer-flow`.
- Commit: `f6fe1e9c9e029bf22b8e2eb8e2e23e1258cf0814`.
- Source path: `backend/packages/harness/deerflow/community/browser_automation/egress.py`.
- Original source SHA-256: `34780425170cd5f79adc6029815f361ac1fc3c5b45cb4d926fc8a6b3a4ad7ba6`.
- Source `LICENSE` and copied `third_party/DEERFLOW-LICENSE` have the same SHA-256:
  `b23dff4d4bac8d17b6efaaa7e88c2b730149c4dda45699ce676b719cfdffe7e1`.
- Full unmodified MIT notice copied, preserving Bytedance and DeerFlow Authors.
- Local adaptations are listed in `third_party/README.md`: enforce port 443,
  fixed diagnostic logs without destination/error secrets, track/cancel/join
  accepted handlers with closed-state recheck, local Ruff formatting/import order.
  This prevents a DNS-resolution handler opening a tunnel after session cleanup.
- Other browser capabilities use official optional Playwright async SDK; the main
  session supplies `playwright==1.58.0`, lock and environment installation. No
  DeerFlow harness, WeKnora gateway, BrowserSkill runtime, Agent framework or OS
  file-dialog automation is included.

## Executed verification

All commands below used the existing `backend/.venv`, from the `backend` directory.
No test loaded the unrelated pytest database/Redis fixtures.

```powershell
& '.venv/Scripts/ruff.exe' check --no-fix app/modules/cnc/browser tests/cnc/browser/_support.py tests/cnc/browser/test_policy_files_state.py tests/cnc/browser/test_workflow.py tests/cnc/browser/test_session.py tests/cnc/browser/test_egress.py
& '.venv/Scripts/ruff.exe' format --check app/modules/cnc/browser tests/cnc/browser/_support.py tests/cnc/browser/test_policy_files_state.py tests/cnc/browser/test_workflow.py tests/cnc/browser/test_session.py tests/cnc/browser/test_egress.py
& '.venv/Scripts/python.exe' -m basedpyright app/modules/cnc/browser --project pyrightconfig.json
& '.venv/Scripts/python.exe' -m unittest discover -s tests/cnc/browser -p 'test_*.py' -v
```

Final implementer run at approximately 20:59 Asia/Shanghai:

| Check | Observed result |
| --- | --- |
| Ruff lint `--no-fix` | PASS, `All checks passed!` |
| Scoped basedpyright | PASS, `0 errors, 0 warnings, 0 notes` |
| unittest | 40 tests in 0.957s, 39 PASS, 1 SKIP. `OK (skipped=1)` |
| Explicit skipped case | `test_symlink_escape_rejected`: `UNVERIFIED: Windows symlink privilege unavailable`. Ordinary out-of-root, extension, size/hash and same-length tamper branches passed. |
| Ruff format `--check` | One pending formatting difference in `test_policy_files_state.py` after separating the previously silent symlink branch. Ownership has transferred to independent reviewer for the narrow format/final checks; no claim that this final formatting command passed. |

Earlier iterations corrected test fixtures constructed in asyncSetUp's different
consumer task, added explicit FEC0/10 DNS refusal (Python 3.12 considers it global),
fixed the pre-admission constructor-failure lease leak, and retained the result
when cleanup completion races cancellation. Regression tests cover each. All
source/unit editing stopped at main-session handoff to independent `browser_check`.

Tests exercise actual loopback SOCKS protocol negotiation/rejection and vetted-IP
plumbing; successful remote TLS connections are not claimed. Fake SDK contexts
cover lifecycle/route installation, while separate Chromium synthetic E2E is
owned and reported independently. Test logs contain synthetic values only; egress
logs emit fixed reason codes. No traces or real credentials were collected.

## Remaining integration and evidence limits

- Real RapidDirect/Xometry authentication/upload/geometry/quote/lead time E2/E3:
  **UNVERIFIED**, original live gates unchanged. No draft automation was enabled.
- Real provider deterministic adapters/locators, persistent SQL intent store and
  account leases, app ACL/ownership lookup, encrypted session repository, private
  evidence/retention, S01-S11 budgets, API/Agent factory, scheduler and human UI
  belong to original 02-05 tasks. The component is not wired into product routes.
- Application settings/key-ring integration of the injected CryptoUtil must be
  exercised when that product integration exists; this component's test cipher
  verifies encrypted scope/tamper behavior without reading application secrets.
- Production isolation/egress deployment and reviewed login/CDN host registry are
  required before exposure; loopback proxy trust assumes an isolated worker.
- Windows symlink-escape test needs a symlink-capable runner; it is explicitly
  skipped here. Root contents must remain controlled by the trusted storage ACL.
- Context storage covers cookies/localStorage/IndexedDB via the official SDK;
  sessionStorage, device binding and challenge behavior require real-platform
  evidence. Restoring encrypted state never itself establishes authentication.
- Session admission is process-local; it does not replace distributed leasing.
  Browser rebuilding is separate from durable remote-operation reconciliation.
- No personal browser/CDP, captcha bypass, payment, order creation or automatic
  transaction tool exists. BrowserSkill deployment remains deferred.

## 2026-10-22 Windows accepted-stream repair

The main session resumed the unfinished BR work and persisted the Windows
adapter decision in `docs/browser-implementation-design.md` before dispatching
this narrow implementation. The demonstrated problem was Python 3.12.13 Windows
Proactor shutdown raising peer reset 10054 before normal socket close/server
detach. Prior managed-browser results were 10/11 with forbidden redirect cleanup
still failing; prior system Chrome 155 failures remain historical results, not
overwritten by this targeted repair.

### Changed files and ownership

- New `backend/app/modules/cnc/browser/windows_streams.py` contains the thin
  Windows loopback accepted-stream adapter.
- `third_party/egress.py` selects this listener only on `sys.platform == 'win32'`;
  Unix keeps its original `asyncio.start_server`. SOCKS, egress resolver/public-IP
  policy, port restriction, relay and outbound `_open_first` are unchanged.
- `third_party/README.md` records this additional local adaptation and limits.
- New `backend/tests/cnc/browser/test_windows_streams.py` supplies 16 focused
  tests. Existing unit/E2E files and fixture were not edited in this repair.
- This note is the only task artifact edited by this implementer; main owns all
  design/task/spec/report changes. Reference repositories, interpreter, global
  libraries/settings and private transport/socket state were not changed.

The installed Python source was read for evidence: its Proactor connection-lost
callback calls socket shutdown before close, and its public create_connection
implementation takes a valid preconnected non-SSL socket into a transport before
the transport-initialization await, closing the transport on failure/cancel.
That source inspection did not patch or operate on an existing transport socket.

### Explicit ownership and error behavior

The adapter binds its own nonblocking ephemeral IPv4 loopback listener, uses
public `loop.sock_accept`, then public `socket.detach` to move our accepted
handle into `_AcceptedSocket`. Failed wrapper construction uses
`socket.close(handle)`, not `os.close(handle)`. Public
`asyncio.open_connection(sock=...)` then takes ownership; subsequent cleanup
uses writer close/wait_closed, without manually touching the transferred socket.

Raw sockets stay owned even when their scheduled callback is cancelled before
the coroutine starts. The listener tracks its accept task, handoff tasks and
writer wrappers through final writer.wait_closed, independently of the vendored
callback's shorter tracking lifetime. Close allows in-progress public Streams
handoff to finish so the returned writer can close; it refuses further accepts,
joins/cancels work under its 1.5s bound (inside the proxy's 2s bound), and reports
unknown failures with a fixed cleanup error. Genuine callback/open/shutdown
faults do not silently become successful closure.

Only `ConnectionResetError(winerror=10054)` is ignored by our socket's shutdown
override. All other shutdown errors propagate and update a separate boolean
outcome record. The listener captures that record before handing off the socket
and checks it after closure, without inspecting any transport-owned socket.

A real abortive TCP close exposed another distinction during the focused tests:
Proactor delivers `ConnectionResetError(winerror=64, errno=22)` to the reader and
writer close waiter. This is ERROR_NETNAME_DELETED, not a missing-winerror case
(an initial hypothesis was corrected by a local synthetic error probe). The
listener classifies only the *identical* reset-64 exception already returned by
public `reader.exception()` as the delivered terminal read result. An unrelated
64 exception, a non-reset OSError, reset 10053 and unknown close failures remain
failures. The independent shutdown outcome prevents an expected read-64 result
from masking an unexpected subsequent shutdown failure. No global exception
filter/handler or private SDK/stdlib mutation was introduced.

### Executed results and commands

Environment: existing backend `.venv`, Python 3.12.13 on Windows. The main session
had installed Playwright's managed browser at
`.trellis/.runtime/playwright-browsers` (Headless Shell 145.0.7632.6, build 1208).
No dependency installation was performed by this repair implementer.

From `backend`:

```powershell
& '.venv/Scripts/ruff.exe' check app/modules/cnc/browser/windows_streams.py app/modules/cnc/browser/third_party/egress.py tests/cnc/browser/test_windows_streams.py
& '.venv/Scripts/ruff.exe' format --check app/modules/cnc/browser/windows_streams.py app/modules/cnc/browser/third_party/egress.py tests/cnc/browser/test_windows_streams.py
& '.venv/Scripts/python.exe' -m basedpyright app/modules/cnc/browser --project pyrightconfig.json
& '.venv/Scripts/python.exe' -m unittest discover -s tests/cnc/browser -p 'test_windows_streams.py' -v

$env:CNC_BROWSER_E2E='1'
Remove-Item -LiteralPath Env:CNC_BROWSER_CHANNEL -ErrorAction SilentlyContinue
$env:PLAYWRIGHT_BROWSERS_PATH='E:/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/playwright-browsers'
& '.venv/Scripts/python.exe' -m unittest discover -s tests/cnc/browser -p 'test_browser_e2e.py' -k forbidden_redirect -v
```

Final narrow run around 08:37 Asia/Shanghai:

| Check | Actual result |
| --- | --- |
| Scoped Ruff lint | PASS, All checks passed |
| Scoped Ruff format check | PASS, 3 files already formatted |
| Core basedpyright | PASS, 0 errors, 0 warnings, 0 notes |
| New focused suite | PASS, 16/16 tests, no skips, 0.390s |
| Actual managed Chromium targeted forbidden redirect | PASS, 1/1 test, 1.290s; strict existing policy/release assertions retained, no cleanup warning/error |

History retained: the first targeted Chromium run after the initial adapter
passed 1/1 in 1.545s. The first focused 13-test run had 12 pass and one error in
the actual TCP RST test; the terminal read-64 distinction above was then resolved
with exact classification and independent unknown-shutdown failure tracking.
A 15/15 intermediate run passed before adding the combined negative case. The
final targeted run above followed all production changes. No complete suite or
system Chrome 155 retest is claimed by this implementer; the independent checker
owns those final regressions and main owns the authoritative test report.

Meaningful coverage includes actual loopback TCP RST, actual forbidden SOCKS
request followed by RST, bind-port reuse, immediate/pending-accept closure,
accepted callbacks cancelled before start, active callback cancellation,
initialization/wrapping/open failures, bounded ownership through writer closure,
and propagation of other socket errors. The actual unpatched Streams cancellation
test schedules cancellation at its transport-initialization await and verifies
peer EOF/port release without manually closing the handed-off socket. Narrow
mocks cover injected error combinations; they are not labelled Chromium E2E.

Remaining limits: Unix execution was not run here; outbound transport behavior
was not widened or separately validated by this repair; complete managed-browser
and system Chrome regressions await independent check. Real RapidDirect/Xometry,
durable product stores, production deployment and original live gates remain
unverified as recorded above. At approximately 08:37 the code and new tests were
released to `browser_check`; no further source/test edits were made by this
implementer after that handoff, and no Git commit/archive was performed.
