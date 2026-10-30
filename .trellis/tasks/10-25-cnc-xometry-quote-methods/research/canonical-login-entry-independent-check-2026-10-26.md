# Canonical Xometry entry — independent check, 2026-10-26

## Scope

Incremental independent review of the fixed Xometry fallback change from
`https://www.xometry.com/account/login/` to `https://xometry.com/login`, and the
six new `test_providers.py` regressions. Read the current task design's native
entry paragraph, `current-auth-source-2026-10-26.md`, the implementation report,
existing login contracts and the actual changed provider/test code.

No product or test edits were required. No live provider, credential,
authentication-state, application-database or quotation operations were
performed by this reviewer. Runtime, policy, quote bindings and parallel
workspace changes were preserved; no commit/archive action was performed.

## Findings (fixed)

None. No concrete defect was found in the reviewed change.

- The fixed fallback now matches the current official header's separately
  observed native login entry. It does not fabricate a callback/token API or
  derive navigation from untrusted input.
- An already-hosted `login.xometry.com` form still avoids fallback navigation.
  Missing hosted redirect or unusable identifier/password controls still return
  false without repeated credential submission.
- The entry URL is the only provider-source difference from the previous
  independent review: replacing it back in memory reproduces the previous
  SHA-256 `3c003605f5ad15ea89aa0bc25d2774acefb73b78624218db74cb15434de2032a`.
  Credential selectors/actions, completion guards, identity checks, retry
  budgets, JLC and policy configuration are unchanged.
- The six added tests execute actual `submit` and `_submit`, with form controls
  and completion reconciliation mocked. They assert the exact canonical target,
  one fallback navigation, one identifier/password fill, hosted reuse, no
  credentials without hosted redirect, missing/ambiguous/hidden identifier,
  unavailable/ambiguous password, and one final timeout reconciliation without
  resubmission. Removing/reverting the fallback change would fail the exact-URL
  assertions, so the tests meaningfully cover this correction.
- These new mocks establish control flow and delegation. The existing local
  Chromium matrix separately exercises the real DOM/identity completion guard;
  neither suite establishes the remote server's authentication bridge.

## Findings (not fixed)

1. **Spec follow-up belongs to the main session.** At review time,
   `cnc-account-login.md` described the hosted split form and completion checks
   but did not explicitly name the newly verified canonical fallback. Recommend
   adding the exact entry, hosted-form reuse condition and source-evidence link.
   No spec edit was made within this reviewer's assigned provider/test/report
   ownership. This is documentation follow-up, not a provider-code defect.
2. **Live acceptance remains incomplete.** A fixed current native entry alone
   does not prove new-UI identity-cache restoration, usable managed upload,
   exact-file receipts/geometry, complete saved parameters or current quote.
   Those remain with the main session. This review does not activate production
   binding or classify the full task as complete.

## Verification

Main-session follow-up: the canonical fallback, hosted-form reuse and source-evidence contract have now been recorded in `.trellis/spec/backend/cnc-account-login.md`. Documentation finding 1 is resolved; live acceptance finding 2 remains open.

Fresh independent static checks ran from `backend`:

| Command | Result |
| --- | --- |
| `uv run --offline ruff check --no-fix app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed |
| `uv run --offline ruff format --check app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed; three files already formatted |
| `uv run --offline basedpyright app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed; zero errors, warnings or notes |

Reused the final fresh test evidence from the implementation worker and its
`canonical-login-entry-implementation-2026-10-26.md` report, rather than
duplicating unchanged full suites:

| Command from `backend` | Result reported by implementation worker |
| --- | --- |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/login -p test_providers.py -v` | 26 passed; zero skips; 0.231 seconds |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/login -p 'test_*.py' -q` | 80 passed; zero skips; 13.793 seconds |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/quote -p test_xometry_runner.py -v` | 9 passed; zero skips; 48.202 seconds |

The implementation worker confirmed first-attempt success and exit zero for
these checks. This reviewer did not rerun those test suites; source review and
fresh static checks found no additional change requiring repetition. Prior
frontend/broader browser checks remain historical, not fresh evidence here.

Reviewed SHA-256 fingerprints:

| File | SHA-256 |
| --- | --- |
| `backend/app/modules/cnc/login/providers.py` | `32173ac82815ea8df2fae85703c31b3edb21126701833f0785542b6aaf933e03` |
| `backend/tests/cnc/login/test_providers.py` | `f6fd2703fb990980392c6af0ef5ccac210db67534718a50b7966f496400770fd` |
| `backend/tests/cnc/login/test_xometry_readiness.py` | `e09020cfdc6dccf1bfab4b567ff0cd717f301272e3b46120455086a04333d26c` |
