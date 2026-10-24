# Backend check accompanying Chrome DevTools acceptance — 2026-10-23

## Scope and conclusion

Reviewed the current working tree on `dev`, based on `93dff6ec`, against this task's PRD/design/implementation plan and the CNC quote/login/browser contracts. This reviewer owns quote backend code and isolated backend checks. The coordinating session owns Chrome DevTools, application runtime and live-provider verification; this report does not claim to have performed those checks.

The production factory in `backend/app/modules/cnc/quote/providers.py:25` still returns `None` for both platforms. `QuoteActivity.advance` fails with `PROVIDER_AUTOMATION_UNVERIFIED` before any upload/configure/submit claim. Therefore the production UI cannot currently complete AC-03/04/08 through a real provider. Passing synthetic tests proves the generic runner and guards, not actual Xometry/JLC prices or parameter fidelity. No adapter was enabled, no external provider contacted, no application server restarted, and no business database or runtime DNS setting changed by this reviewer.

## Fixed defect

`QuoteRepository.validate` delegates a frozen file recheck to `TrustedStep.read_verified`. That recheck raises the shared `BrowserStop(file_invalid)` when the file disappears or changes. The HTTP `_action` wrapper formerly caught only `LoginError`, so this expected domain stop escaped into the global exception handler, producing a generic HTTP 500 and exception-stack logging instead of the fixed safe reason.

- Changed `backend/app/modules/cnc/quote/routes.py` to catch `LoginError` and `BrowserStop`, preserving `str(exc.reason)` in `CustomException`.
- Added `test_file_stop_uses_fixed_reason_without_global_exception_logging` in `backend/tests/cnc/quote/test_quote_http.py`. It covers start, status and resume endpoints, checks HTTP 400 / `file_invalid`, and rules out exception-stack/error logger use. It permits ordinary HTTP INFO logging.
- Before the fix: the new test produced three unhandled `BrowserStop` errors, one per endpoint.
- After the fix: all six HTTP test methods pass, including permissions, strict input/privacy and materialized OpenAPI path/method checks.
- Suggested spec sync for the coordinating session: fixed shared `BrowserStop` reasons at quote HTTP boundaries use the same private business-error conversion as login/quote errors; do not send them to the global exception traceback handler.

## Fixed test timing issue

After the HTTP fix, the complete independent unittest run executed 40 methods in 170.440 s: 39 completed and the slow-parser method reached the fixture's 10 s completion wait. The same unchanged method then hit that 10 s limit independently (11.311 s including setup/teardown). No production 15 s phase or 180 s parse limit was reached in the failure trace; the failing frame was `_quote_support.wait_for`.

A diagnostic run with only the test wait extended completed the same behavior assertions. The focused test now passes in 14.537 s with a bounded 30 s fixture wait. `RunnerTests.finish` accepts an optional test wait, and only `test_slow_parser_reconciles_read_only_without_second_upload` supplies 30 s; other methods retain the default 10 s. The original assertions are unchanged: one upload, two read-only reconciliations, final `QUOTED` fixture result and persisted confirmed upload intent. Production deadlines and pacing were not changed. This covers intentional two-second reconciliation delays plus real independent SQLite transactions on the current Windows machine.

The final complete 40-method suite was rerun after this test-only budget adjustment and passed: `Ran 40 tests in 151.056s`, `OK`, exit code 0. This final run retained the 30 s budget only for the slow-parser method. The original 10 s timeout and focused pass remain recorded above to preserve the failure/fix evidence. Scoped Ruff passed again after the test change.

## Verified behavior and limits

The repository and runner tests exercise independent temporary SQLite transactions with the production quote tables/constraints. The browser and platform adapters in quote tests are synthetic; the value `12.30` in those tests is fixture data only.

- Account selection covers zero/one/multiple matches, actor filtering, cross-platform rejection and a non-enum platform primary key (`48`).
- Current user, role and menu authorization is reloaded through `ActorAuthorizer`; tests cover disable/delete/revoke, cached-superuser demotion and permission revocation during identity verification before the next upload claim.
- Config/part ownership, upload authorization, file boundary/hash, scalar parameter encoding and frozen configuration changes are covered. The frozen buffer is what the adapter receives.
- Run uniqueness and durable claim uniqueness are exercised with concurrent real transactions. Cancel, restart, slow parsing and failed intent confirmation preserve claimed/uncertain records and do not authorize a second upload.
- Same-owner execution, account-page exclusion, read-only challenge resume and terminal cleanup are covered. These are owner/runtime fixtures, not live browser authentication.
- The shared validator rejects parameter mismatches, unverified cached quotes and invalid result evidence. Estimates and pending review have distinct terminal types; result-store failure cannot publish `QUOTED`.
- The isolated migration test upgrades only the quote revision in an isolated in-memory database, compares model columns/uniqueness and downgrades. It does not prove the production DB migration history or deployment.

## Findings left for coordination

### Provider activation / live acceptance — incomplete implementation

Evidence: `quote/providers.py:25-30`, `quote/runner.py:118-120`. The factory is unconditionally disabled. This is explicit safe behavior, but leaves the requested real upload, effective-parameter readback and returned price unimplemented/unverified. Recommendation: keep both platforms marked unaccepted until each trusted adapter has its live evidence; do not enable draft selectors or return synthetic/demo prices. Enabling/researching provider support is outside this reviewer scope.

### Mixed DNS contract regression — not fixed in reviewer scope

Evidence at the reviewed revision: `browser/policy.py:65-87` filters unsafe answers and permits a remaining public IP. The committed version and current spec require rejecting the entire DNS answer set if any address is unsafe.

`test_policy_files_state.py:49-53` patches `socket.getaddrinfo` with explicit answers, so the failures are independent of the machine's actual fake-IP or DNS configuration. For each of 12 private/special addresses it checks both the single unsafe address and a mixed answer `(8.8.8.8, unsafe)`. The mixed cases did not raise `ValueError`. Addresses include loopback, RFC1918, link-local/metadata, IPv6 ULA/site-local, unspecified, multicast, CGNAT and documentation space.

The browser regression run reported `Ran 94 tests`, `FAILED (failures=12, errors=1, skipped=13)`. The additional error is `test_egress.EgressTests.test_protocol_rejects_non443_unknown_and_mixed_dns_before_connect`: proxy cleanup failed in the mixed-DNS case after the expected refusal did not occur. The run also emitted an unclosed-transport warning. Do not count this run as passed. It was handed to the coordinating session without modifying policy/egress code.

### `.setp` upload/quote compatibility — not fixed in reviewer scope

The part page accepts `.setp` and saves `extension='setp'` (`frontend/web/src/views/module_cnc/cnc_part/index.vue:647`, `:692`). `UploadUtil.validate_file_content_type` accepts the historical alias without normalizing its stored suffix. However `quote/repository.py:87,100` and `browser/files.py:39` allow only `.step/.stp`. A legal authorized Part 21 fixture named `sample.setp` under a temporary trusted root was rejected immediately with `QuoteError(FILE_INVALID)` by `source_file`.

Recommendation: decide and implement consistent alias normalization/validation across upload, quote snapshot and the shared file verifier, with a cross-boundary regression. This crosses the shared browser/file contract and was reported rather than silently changing that boundary.

### Existing controller lint baseline — not changed

Including `app/plugin/module_cnc/cnc_part_config/controller.py` in scoped Ruff reports one `UP009` on its first-line UTF-8 encoding comment. `git show HEAD:backend/app/plugin/module_cnc/cnc_part_config/controller.py` confirms the same comment exists before this work. Quote modules/model/tests are clean; the unrelated generated CRUD header was left intact.

## Commands and results

Commands below run from `backend` with the installed `.venv` tools. No dependency installation/resolution was needed.

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/cnc/quote -q` (before loading the added HTTP test) | 39 passed, 12 subtests passed, 157.98 s. Uses the test harness's temporary SQLite, never the business DB. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p test_quote_http.py -k file_stop -q` (before production fix) | Fails: 3 subtest errors, unhandled `BrowserStop(file_invalid)`. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p test_quote_http.py -q` (after fix) | 6 tests, OK. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p test_*.py -q` (after HTTP fix, before slow-test budget adjustment) | 40 tests run, 39 completed, 1 error at the slow-parser fixture's 10 s wait; 170.440 s. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p test_quote_runner.py -k slow_parser -q` (before test adjustment) | 1 test, error at the same 10 s fixture wait; 11.311 s including setup/teardown. |
| Same focused command after only the slow method's test wait changed to 30 s | 1 test, OK; 14.537 s. Production timeouts and original assertions unchanged. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p test_*.py -q` (final complete rerun after budget adjustment) | 40 tests, OK, exit code 0; 151.056 s. No tests skipped. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/login -p test_*.py -q` | 50 tests, OK. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/upload -p test_*.py -q` | 12 tests, OK. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_*.py -q` | 94 tests run; failures=12, errors=1, skipped=13. See exact DNS finding above. Real Chromium E2E remains opt-in; skipped checks are not passed acceptance. |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/quote app/plugin/module_cnc/cnc_quote tests/cnc/quote` | All checks passed. |
| Same Ruff command additionally including `app/plugin/module_cnc/cnc_part_config/controller.py` | One existing `UP009` encoding-header warning. |
| `.venv/Scripts/basedpyright.exe app/modules/cnc/quote app/plugin/module_cnc/cnc_quote app/plugin/module_cnc/cnc_part_config/controller.py` | 0 errors, 0 warnings, 0 notes. |

Independent unittest commands avoid importing the full application-wide pytest fixtures for these self-contained components. Login, upload and browser runs were read-only with respect to user/business data; their fixture transactions/files and synthetic local sockets are isolated.

Relevant reviewed-file SHA-256 hashes (before any subsequent coordinator edits):

- `quote/providers.py`: `0777935868B6207302299DE5153C2616DF602F2751DE20C3868C25215D2FBB0B`
- `quote/routes.py` after this fix: `0D924B3A44B5473113DC138F2FFB67B0E2098F72CCC1C9D0EA73C6EA1E95509E`
- `browser/policy.py` for the failing mixed-DNS run: `4FB0BEE64735D5338896A4B9A6AF11AF3F5BF17A2DA375A72B03492177C1666C`
