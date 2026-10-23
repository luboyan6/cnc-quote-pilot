# Independent browser reuse review

Dates: initial review 2026-10-21; resumed review 2026-10-22.
Reviewer: dispatched `trellis-check`. Scope: BR shared
component, isolated tests, dependency changes, source/license evidence, and
related task revisions. Reference repositories were read-only. No commit,
archive, unrelated refactor, or live platform operation was performed.

## Findings (fixed)

- `policy.py`: the review's Python 3.12.13 probe established that deprecated
  IPv6 site-local `fec0::1` is considered global and not reserved. The original
  predicate therefore allowed it. The implementer added explicit
  `IPv6Address.is_site_local` refusal, with single/mixed-answer regressions for
  `fec0::1` and `feff:ffff::1`; independently verified present and passing.
- `session.py`: account admission originally preceded synchronous lease/proxy
  construction outside the protected lifecycle. A constructor failure could
  leave the account permanently busy. The implementer moved construction
  before admission, validates scope/policy types, sanitizes constructor errors,
  and added a failure/next-session regression; independently verified passing.
- `workflow.py`: `StrEnum` equality originally let a string freshness value
  reach a successful result and later fail `.value` serialization. The
  implementer added an explicit `QuoteFreshness` instance check and invalid
  string regression. Time proximity alone is rejected; unverified cache and
  pre-execution recalculation are rejected.
- `tests/cnc/browser/_support.py`: repository-configured basedpyright initially
  found 13 errors caused by inferred `None` fixture fields used as requests,
  Events, and exceptions. The reviewer added the precise optional types and
  a required request assertion. No checker rules or suppressions were changed.
- `tests/cnc/browser/test_workflow.py`: the reviewer added configuration timeout
  and post-Apply readback timeout regressions, and extended cancellation to
  upload/configure/submit. They verify preserved uncertain intents, capped
  read attempts, no repeat Apply/upload, and no premature submit.
- `tests/cnc/browser/test_session.py`: the reviewer added cancellation during
  cleanup and cleanup-failure/cancellation-race regressions. Remaining closers
  must finish and cleanup failure must remain visible on cancellation.
- `session.py`: real-browser redirected navigation bypassed a second route
  callback, so actual proxy refusal was reported as generic browser failure.
  The reviewer added context-scoped request observation and a no-second-route
  regression. This preserves a fixed policy stop for redirected requests;
  actual egress remains enforced by the proxy. The worker's targeted real
  redirected-navigation regression passed after the fix.
- `third_party/egress.py`: inherited cleanup suppressed handler/server close
  failures. Windows E2E exposed genuine Proactor socket cleanup failures. The
  reviewer now attempts the remaining closes and surfaces a fixed failure
  after bounded joins; an integrated never-closed-server regression verifies
  `CLEANUP_FAILED`, other resource close attempts, and account release. Local
  third-party adaptation notes were synchronized.
- `tests/cnc/browser/test_policy_files_state.py`: reviewer applied requested
  local Ruff formatting; no behavioral change.
- `tests/cnc/browser/test_browser_e2e.py`: reviewer fixed the cancellation test
  to reject a cleanup-failure note on an expected `CancelledError`; otherwise
  resource failure could pass unnoticed. Its test-only browser channel now
  defaults to SDK-managed Chromium, with explicit `CNC_BROWSER_CHANNEL=chrome`
  retained for system-channel reproduction. Production options and safety
  policy are unchanged.
- `windows_streams.py`: after the 10/11 managed-browser failure, the design was
  amended before the implementer's narrow Windows accepted-stream adapter.
  Independent review verified public accept/detach/Streams ownership, cleanup
  before task startup and during actual Streams initialization, tracking through
  writer closure, exact shutdown reset 10054 handling, and identical delivered
  reader reset 64 handling. An independent shutdown-outcome record preserves
  unknown shutdown failures even alongside that read reset. Sixteen new
  ownership/real TCP/negative-error tests passed in the independent full suite.
  No global runtime patch/filter, private transport access, DNS/SOCKS rewrite,
  or policy weakening was introduced. Full managed Chromium E2E subsequently
  passed without the former transport warnings.

## Findings (not fixed)

- OS symlink execution is **UNVERIFIED**: Windows rejected creating the test
  symlink without the required privilege. The test reports an explicit skip;
  ordinary real-path root escape, hash, byte-size, extension, and verified
  buffer checks passed. This review did not change machine privileges.
  The main session also retried only the existing symlink test outside the
  sandbox with the approved scoped command: one test, 0.023 s,
  `OK (skipped=1)` and the same explicit unavailable-privilege reason. This
  confirms the required case remains unverified beyond sandbox restrictions;
  it is not a pass and no machine privilege was changed.
- RapidDirect/Xometry authorization, actual login persistence, geometry,
  accurate price/lead-time semantics, provider evidence, and real E2/E3 remain
  **UNVERIFIED**. No platform adapter, persistent production intent/state store,
  distributed lease, deployed browser, recovery Agent, scheduler, or handoff UI
  is delivered by this offline component. Their original task gates remain.
- Full-site type/test checks are outside this change: isolated tests avoid the
  unrelated application's DB/Redis fixtures; the scoped check uses the existing
  backend `pyrightconfig.json` without modifications.

## Verification

Commands from repository root unless `backend/` is indicated:

1. `python -B .trellis/tasks/10-21-cnc-browser-reuse/research/review_task_tree.py`
   — PASS: seven original task metadata records preserved, eight current tasks,
   38 approved original files changed, 29 original files unchanged, no completed
   task reset, unique IDs and acyclic implementation dependencies.
2. `python .trellis/scripts/task.py validate <task>` for BR, parent, and original
   01–05 — all PASS, including every implement/check manifest.
3. Read-only `git branch --show-current` / `rev-parse HEAD` in both references
   matched recorded commits; sampled symbols and dependency declarations match
   the analysis. Vendored DeerFlow MIT license SHA-256 exactly matches source.
   Actual proxy diff matches the declared port/logging/cleanup adaptations.
4. Backend `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser
   -p 'test_[epsw]*.py' -v` — 62 unit/Mock/TCP discovered: 61 PASS and one OS
   symlink skip (1.444 s). This pattern selects the five isolated modules,
   including 16 Windows accepted-stream tests; browser verification has a
   separate opt-in command/result.
5. Backend `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/browser
   tests/cnc/browser` — PASS. Matching `ruff format --check` — PASS, 18 files
   already formatted.
6. Backend `.venv/Scripts/basedpyright.exe app/modules/cnc/browser
   tests/cnc/browser` — PASS: zero errors, zero warnings, zero notes using
   repository configuration.
7. Backend `uv lock --check --offline` — PASS: resolved 109 packages. Lock diff
   adds optional Playwright 1.58.0 and pyee; existing dependencies are retained.
8. Historical pre-adapter backend E2E with `CNC_BROWSER_E2E=1`, empty
   `CNC_BROWSER_CHANNEL`, and
   `PLAYWRIGHT_BROWSERS_PATH=E:/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/playwright-browsers`:
   `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser
   -p test_browser_e2e.py -v` — **FAIL: 11 tests, 27.634 s, ten PASS,
   one ERROR, no skips**. Forbidden-redirect cleanup reports
   `browser_cleanup_failed` following Proactor10054 and unclosed resources.
   Other cases, including strict cancellation, passed. No log contention
   occurred in this single-process full run. Prior system-Chrome failure
   history and exact boundaries are retained in `e2e-notes.md`.
9. After the reviewed Windows adapter, same managed-browser command/environment:
   **PASS: 11 tests, 23.707 s, no skips**. Actual runtime printed Playwright
   1.58.0 and Chromium 145.0.7632.6. Full output has only the expected fixed
   policy-refusal warning, with no Proactor callback, resource warning or cleanup
   failure. This result supersedes the historical 10/11 execution as the
   current managed-browser result without erasing that failure history.
10. Same complete E2E command with `CNC_BROWSER_CHANNEL=chrome`:
    **PASS: 11 tests, 37.981 s, no skips**, actual Chrome 155.0.8059.85. The
    returned final 90 log lines have expected fixed policy refusals and no
    resource/Proactor failure. The child's subsequent scan process failed before
    starting with `CreateProcessWithLogonW ... 1909`; the main session then read
    both entire logs using its normal tool worker and scanned them successfully.
    No resource/Proactor/reset/cleanup/logging/traceback/failure markers matched
    either complete log. No OS/account workaround or escalation was used.

## BR-03 through BR-06 readiness

| Acceptance | Independent assessment |
| --- | --- |
| BR-03 | PASS for the shared component on the actual Windows/Python3.12/managed145 runtime: isolation, lifecycle failure/cancellation, real TCP reset release and browser reconstruction without mutation replay have executed results. Chrome155 reproduction also passed and the main session's complete-log scans found no transport/resource warnings. Production distributed leases/stores are separate integration gates. |
| BR-04 | PARTIAL / UNVERIFIED: encrypted scope, challenge stops, exact-domain/SSRF, actual forbidden requests, ordinary path/byte/hash failures passed. The real OS symlink escape case was skipped for unavailable privilege and cannot be marked passed. |
| BR-05 | PASS for component/synthetic acceptance: official upload/filechooser bytes, complete fields, exact Decimal/currency/lead time, verified freshness, capped reads and mutation suppression have results. This does not verify provider geometry/prices/lead time. |
| BR-06 | PASS: the synchronized report separates unit/Mock/TCP, managed/system browser runs, historical failures, skips and live-provider unknowns. Original live checkboxes and draft platform inputs remain unchanged. |

## Final full-scope review

On 2026-10-22 the reviewer checked the full shared executor, policy/state/file
helpers, workflow/intent/quote contracts, vendored proxy and attribution, Windows
adapter, all browser test modules, authoritative design, backend specs, runtime
instructions, latest test report and BR PRD. The final main-session report and
PRD now match the executed results: BR-01/02/03/05/06 are component-scoped passes,
BR-04 remains unchecked for the required OS symlink case, and the task remains
in progress. No new code/spec conflict was found after the fixes and complete
lint/type/test runs.

Task audit/context validation previously passed independently; a redundant final
audit/diff command encountered the child's same 1909 process-creation limitation.
The main session owns the final ordinary-tool audit/diff/metadata checks and
journal. No permission/account change was attempted.

Completed browser E2E runs and full-log scans pass; skipped OS validation and
real-platform integration remain unverified, so this record does not declare
every BR acceptance criterion complete. No commit or archive was performed.

### Final main-session audit settlement

The main session's final ordinary sandbox audit processes also failed to start
with Windows1909. Its explicitly approved sandbox-external rerun then passed
the task-baseline audit (original seven metadata records preserved, 38 approved
files changed, 29 untouched), all seven parent/01-05/BR manifest validations,
and `git diff --check`. The original README/frontend environment-file hashes
still match. Session3 was recorded with `add_session.py --no-commit`; BR-04 and
the task remain open. No account reset, OS privilege change, commit or archive
was performed. The full browser/code checks above were not rerun needlessly
after documentation-only synchronization.
