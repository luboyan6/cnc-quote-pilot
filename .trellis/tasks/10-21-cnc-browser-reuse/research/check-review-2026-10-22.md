# Independent continuation review — 2026-10-22

Reviewer: dispatched `trellis-check`. Scope: the complete shared browser
component, its isolated unit/Mock/TCP tests, browser test assertions, current
design/specification, and component acceptance evidence. The reviewer owns only
this new record; the main session owns report/PRD/spec/task status updates.
No source code, machine privilege, provider configuration, or original task
metadata was changed by this reviewer. No commit or archive was performed.

## Findings (fixed)

No new code defects requiring a local fix were found. The earlier review's
corrections remain present, including exact public-IP policy, mutation intent
guards, current quote validation, and Windows accepted-socket lifecycle rules.

## Findings (not fixed)

- The Windows required symlink-escape test still explicitly skips because the
  runner lacks symlink privilege. This remains a skip in the Windows result;
  the missing required behavior now has a separate actual Ubuntu execution
  with zero skips, reviewed below. No machine privilege change was needed.
- The broader Ubuntu 62-test diagnostic has two unresolved immediate-port-bind
  errors in `test_windows_streams.WindowsListenerTests`:
  `test_active_callback_cancelled_and_real_stream_writer_closed` and
  `test_real_streams_handoff_cancellation_closes_via_public_api`.
  Both directly exercise the explicitly Windows-only adapter on Linux and
  fail the test helper's bare `probe.bind(address)` with errno 98. These
  portability errors are retained rather than changing the supported-host
  Windows assertions or adding skips. Production Unix dispatch uses
  `asyncio.start_server`, and all 16 supported Windows adapter regressions
  pass. This review does not certify the complete 62-test suite on Linux.
- Real provider authentication, geometry, prices and lead times, durable
  application IntentStore/state/ACL, distributed leases, scheduling, recovery
  Agent, handoff UI and deployment-browser E2E remain separate original-task
  integration/live gates. None is established by unit tests or synthetic pages.
- Whole-application DB/Redis fixtures and repository-wide unrelated typing
  debt are outside this isolated component review. Checks use existing backend
  configurations unchanged.

## Verification

Executed from `backend/` during this review:

| Command | Result |
| --- | --- |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/browser tests/cnc/browser` | PASS, all checks passed |
| `.venv/Scripts/ruff.exe format --check app/modules/cnc/browser tests/cnc/browser` | PASS, 18 files already formatted |
| `.venv/Scripts/python.exe -m basedpyright app/modules/cnc/browser tests/cnc/browser --project pyrightconfig.json` | PASS, 0 errors / 0 warnings / 0 notes |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p 'test_[epsw]*.py' -v` | 62 tests / 1.365 s / exit 0: 61 PASS, 1 explicit OS-symlink skip |
| `uv lock --check --offline` | PASS, resolved 109 packages |

All 16 Windows socket ownership/listener/TCP tests passed, including real
abortive TCP close and SOCKS refusal, cancellation before task startup and
during actual Streams initialization, remaining tracked through writer closure,
port release, and unknown shutdown failures alongside a delivered read reset.
Expected fixed `policy_blocked` logs and two asyncio slow-task diagnostics
appeared; there was no test failure, transport/resource warning or cleanup
failure.

Source-path review covered contracts, files, policy, scope-bound state,
executor admission/lifecycle, read-only retry, all three mutation intents,
freshness/Decimal/geometry validation, the vendored proxy, and the narrow
Windows Streams adapter. The adapter uses owned public sockets and Streams;
unknown shutdown failures remain observable. No global error filter, private
transport patch, alternate SOCKS protocol, or production policy bypass was found.
Third-party attribution and fixed-reason logging remain explicit.
Read-only SHA-256 comparison also confirmed that the vendored full MIT license
equals `E:/AIWorkspace/deer-flow/LICENSE`:
`b23dff4d4bac8d17b6efaaa7e88c2b730149c4dda45699ce676b719cfdffe7e1`.

Existing full managed Headless Shell 145 and Chrome 155 synthetic E2E results
remain 11/11 each as documented in `check-review.md` and
`docs/browser-test-report.md`. This continuation did not change the source/test
code or repeat those browser runs. Reviewed assertions still reject cleanup
failure notes on cancellation and verify release after forbidden redirects,
subresources and popups. Those Windows synthetic results do not verify Linux
deployment or real providers.

## Final acceptance follow-up

Independently read the parallel implementer's complete
[Linux validation record](linux-validation-2026-10-22.md), including environment
preparation/import failures, exact successful commands, original outputs,
broader-suite failures and both bounded TCP diagnostic observations. The
reviewer did not repeat these unchanged successful tests.

| Reviewed Ubuntu execution | Actual recorded result |
| --- | --- |
| Original required symlink test | 1/1 PASS / 0.024 s / 0 skips / exit 0 |
| Original four cross-platform modules | 46/46 PASS / 3.385 s / 0 errors / 0 failures / 0 skips / exit 0 |
| Broader diagnostic including direct Windows adapter tests | 62 tests / 7.300 s / 58 PASS / 2 errors / 2 existing Windows-specific skips / exit 1 |

The required file SHA-256 is unchanged across Ubuntu execution, and the
reviewer's separate Windows on-disk SHA-256 read matches it exactly:
`17209160855a9ea821bb103e74dd36a7cd9c1d5535839c02f65e9f314dd71a61`.
The original test creates a real symlink from the trusted directory to an
external STEP file and requires the existing validator to reject it. It does
not replace path resolution with a Mock or change the production policy.

The first immediate kernel snapshot included a transient LISTEN row, so it is
not treated as proof of absent kernel state. The final bounded reproduction,
after closing both ends and yielding 100 ms, recorded only TIME_WAIT (`06`),
no LISTEN (`0A`), connection refusal (111), listener descriptor -1 and empty
owned handle/task sets. This supports a kernel-state explanation for the
diagnostic bind errors; it does not turn either failed original Linux test
into a pass or establish the exact state of every earlier connection.

Reviewed the synchronized `docs/browser-test-report.md`, runtime setup, BR PRD
and implementation plan, and backend executor specification. They distinguish
Windows's 61 passes plus one skip, Ubuntu's actual symlink/cross-platform
passes, the failed broader Linux diagnostic, and synthetic versus real-provider
acceptance. Previous Windows failure/skip history remains preserved. The main
session owns final task metadata and subsequent original task-01 work.

**Independent component acceptance: PASS.** Existing BR-01/02/03/05/06
evidence remains valid, and BR-04's previously missing OS symlink case is now
actually executed with zero skips. Supported Windows lifecycle/adapter/browser
results plus Ubuntu file-boundary/cross-platform results meet the existing
shared-component gates. This conclusion does not claim a green full Linux
suite, Linux browser/deployment support, production stores/leases, real
providers, or completion of the original 01–05 tasks. No new source/test fix,
commit or archive was performed in this continuation review.
