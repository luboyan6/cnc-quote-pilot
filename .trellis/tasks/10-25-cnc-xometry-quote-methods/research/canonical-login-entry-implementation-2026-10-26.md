# Canonical Xometry login entry — implementation, 2026-10-26

## Change boundary

Replaced only the fixed Xometry fallback in
`backend/app/modules/cnc/login/providers.py::LoginProvider._submit`:
`https://www.xometry.com/account/login/` becomes
`https://xometry.com/login`. Current official header source
`/_next/static/chunks/c5ab5fec30a829d4.js::navigateToAuthHostLogin` uses that
canonical entry; earlier guarded evidence shows the obsolete route can finish
on a page without usable login controls. Source/observation records are
`site-auth-source-2026-10-25.md` and `managed-auth-diagnostic-result.json`.

The already-hosted identifier page remains in place, and the existing identifier
and password action, false/timeout behavior, same-Page completion checks and
exact identity verification remain unchanged. No runtime, JLC, policy, trusted
host, authentication storage, quote binding, frontend or migration was changed.
Existing parallel workspace changes were preserved.

## Regression coverage

Added six tests to `backend/tests/cnc/login/test_providers.py`, exercising the
actual public `submit` and underlying `_submit`, with synthetic form controls:

- Canonical navigation occurs once, identifier/password are each filled once,
  and the final same-session completion check still runs.
- An existing hosted identifier form is reused without navigation.
- A canonical entry that does not redirect to the hosted form sends no
  credentials and does not claim completion.
- Missing, duplicate or hidden identifier controls retain manual recovery.
- An unavailable or duplicate password form does not repeat the identifier
  submission or send a password.
- A final password-click timeout invokes completion reconciliation once,
  without another navigation, identifier/password fill or credential action.

The existing local Chromium readiness matrix and Xometry owner regressions
continue to cover unchanged UI/identity, declaration and intent behavior.

## Validation

Commands ran from `backend` using the existing virtual environment. No new
dependencies, live credentials or application database operations were used.

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/login -p test_providers.py -v` | 26 passed; zero skips; 0.231 seconds |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/login -p 'test_*.py' -q` | 80 passed; zero skips; 13.793 seconds |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/quote -p test_xometry_runner.py -v` | 9 passed; zero skips; 48.202 seconds |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py` | Passed |
| `.venv/Scripts/ruff.exe format --check app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py` | Passed; both already formatted |
| `.venv/Scripts/basedpyright.exe app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py` | Zero errors, warnings or notes |

The full login suite emitted its expected synthetic decryption/error-path and
HTTP/SQL logs, plus asyncio scheduling diagnostics under concurrent browser
tests; all assertions passed on the first run. No test/source timing budgets
were altered.

## Acceptance limits

This is a correction of an observed obsolete entry. It does **not** establish
that the site's legacy/new identity bridge works. The main session's independent
live diagnostic still observes legacy app before login, Next app after callback,
and absent new-UI `_identity_cache`. No live platform operation was performed by
this implementation worker. Same-file upload receipts, positive geometry,
complete saved parameters and a current real quote remain incomplete;
production quote binding stays disabled. No commit or archive was performed.
