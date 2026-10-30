# Xometry login timeout verification — 2026-10-26

## Scope and finding

Resumed the interrupted login-submit timeout correction. Reviewed the existing
Xometry-only `submit` timeout branch, bounded same-Page reconciliation and its
unit/local Chromium regressions. No real provider, credentials or application
database operations were performed by this worker.

The positive DOM guard accepted a visible disabled `My Account` button as settled
readiness. Tightened only `XOMETRY_POST_LOGIN_READY` in
`backend/app/modules/cnc/login/providers.py`: the observed native control must
also be enabled (`:disabled` and `aria-disabled="true"` reject). Added both cases
to `backend/tests/cnc/login/test_xometry_readiness.py`. Existing JLC changes,
ordinary identity verification, runtime ownership and quote registration were
preserved. `test_providers.py` was reviewed and checked without additional edits.

## Verified behavior

- The uncertain credential submission occurs once; reconciliation makes no new
  credential submission or navigation.
- At most three read-only UI attempts run under an eight-second timeout. Empty,
  loading or hidden account shells and visible identifier/password/OTP/captcha
  controls cannot satisfy post-login completion.
- A settled account control remains insufficient without the existing exact
  authenticated identity check. Wrong identity stops immediately, and UI
  readiness is read again after that identity request.
- Navigation-context loss may retry the read; hosted challenges and callbacks
  are preserved. JLC does not enter Xometry reconciliation.
- Local Chromium checks fulfill all requests in process, assert read budgets,
  zero UI writes and unchanged page URL, and cover both disabled-control cases.

## Validation

Commands ran from `backend` with the existing environment. Initial sandbox runs
could not open the external uv cache (`os error 5`); the same commands were rerun
with requested and granted escalation. No dependencies were installed.

| Command | Result |
| --- | --- |
| `uv run --offline python -m unittest discover -s tests/cnc/login -p "test_*.py" -v` | 73 passed, zero skips; 15.383 seconds |
| `uv run --offline python -m unittest discover -s tests/cnc/quote -p test_xometry_runner.py -v` | 9 passed, zero skips; 57.940 seconds |
| `uv run --offline ruff check --no-fix app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed |
| `uv run --offline ruff format --check app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed; three files already formatted |
| `uv run --offline basedpyright app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Zero errors, warnings or notes |

These are isolated code/owner checks. Live login readiness, production binding,
the selected frozen file's upload/parameter receipts and a current genuine quote
remain separate acceptance work coordinated by the main session. This report
does not mark the overall task complete.

## Follow-up: normal successful submission

Following the main session's updated design and real-page evidence, extended
`LoginProvider.submit` so a normal successful Xometry `_submit` also completes
the same read-only reconciliation before returning true. A normal false result
remains false; normal JLC results and its timeout behavior remain unchanged.
The credential action is called once. The normal-success reconciliation occurs
outside the credential-action timeout handler, so a read error cannot trigger a
second pass. The existing eight-second completion budget and owner timeout were
not increased; runtime and restored-session verification were not changed.

The positive guard now requires exactly one visible native account button,
rejecting duplicate and non-button matches in addition to disabled controls.
The local Chromium matrix is reused for both normal true and timeout outcomes:
settled account, empty/loading/hidden/disabled/aria-disabled/duplicate/non-native
account controls, guest/sign-in/password/OTP/captcha blockers, absent identity
and wrong identity. Both paths assert one credential delegation, no navigation,
zero UI writes and exact identity-read budgets. The delayed-hydration unit case
also covers both paths; another unit case preserves normal false and JLC return
behavior without reconciliation.

### Final follow-up checks

- Full login suite after the final test edit:
  `uv run --offline python -m unittest discover -s tests/cnc/login -p "test_*.py" -q`
  — **74 passed, zero skips**, 16.873 seconds.
- Owner regressions:
  `uv run --offline python -m unittest discover -s tests/cnc/quote -p test_xometry_runner.py -v`
  — **9 passed, zero skips**, 61.344 seconds.
- Ruff lint, Ruff format check and basedpyright on the same three owned
  code/test files — **passed**; zero type errors, warnings or notes.

One earlier follow-up login run passed 74 tests before the test closure's Ruff
warning was fixed by binding its loop-local page argument. The next full run
had one timing-sensitive failure in the unchanged
`test_idle_and_max_lifetime_release_resources`: its 30 ms idle deadline raced the
frame request, which returned `SESSION_CLOSED`. The unchanged test passed on an
isolated rerun (1 test, 0.105 seconds), and the subsequent full suite passed as
reported above. No `runtime.py` or `test_runtime.py` edits were made; the failed
attempt is retained here separately from the final pass.

The follow-up touched only `providers.py`, `test_providers.py`,
`test_xometry_readiness.py` and this report. No real provider, credential,
application-database, binding, quote or cookie operation was performed by this
worker. The change prevents a hydrating shell from reporting completed login;
it does not establish that the live site's legacy/new authentication bridge is
working.
