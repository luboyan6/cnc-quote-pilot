# Final incremental Xometry login check — 2026-10-26

## Scope

Independent review of the latest normal-success completion path and unique,
enabled native account-control requirement in `login/providers.py`,
`login/test_providers.py` and `login/test_xometry_readiness.py`. This review
supersedes the earlier timeout-only review for those extensions. Loaded native
Trellis context, current task artifacts, account-login/browser/quote contracts,
the pause handoff and prior implementation/independent reports. Traced the
existing login owner to confirm how the provider result is consumed.

No product or test edits were necessary. Preserved parallel JLC and other
workspace changes. No real provider traffic, credentials, application database,
cookie transfer, production binding activation, commit or archive operation was
performed by this reviewer. Chromium tests fulfilled all traffic in process.

## Findings (fixed)

None. No concrete defect was found in the reviewed extension.

- `submit` delegates `_submit` exactly once. Xometry normal true and Playwright
  timeout outcomes enter the same bounded read-only completion check. Normal
  false and JLC true/false/timeout outcomes retain their existing behavior.
- Normal-success reconciliation runs outside the credential-action exception
  handler. Its own read error cannot enter the submission-timeout handler and
  cause another completion pass or credential action.
- Completion requires a complete quote page, exactly one visible native
  `button#header-my-account-button` with exact `My Account` text, native and
  ARIA enabled state, and no observed guest/sign-in/credential/challenge signal.
  Empty/loading/hidden/disabled/duplicate/non-native controls fail.
- Positive UI alone cannot succeed: the original guarded exact identity check
  remains required and a positive UI read follows it. Wrong identity propagates
  immediately. Only the observed execution-context navigation transition permits
  a read retry; credentials and navigation are never repeated by reconciliation.
- The three-attempt/eight-second completion budget remains bounded under the
  existing owner timeout. Cancellation and policy/identity failures are not
  converted into successful login. Restored-session verification and runtime
  behavior retain their separately documented contracts.
- Current `cnc-account-login.md` already records both the normal-success and
  timeout contracts, native-control uniqueness and live-acceptance limits; no
  additional spec edit is required for this reviewed extension.

## Findings (not fixed)

No unresolved code defect was identified within this incremental review scope.
The managed site's new-UI identity-cache discrepancy, real selected-file upload,
complete saved parameters, correlated current price and production binding
activation remain separate unfinished acceptance work with the main session.
These isolated checks do not establish those outcomes. No broader source or
runtime change was made to speculate about the site's authentication cause.

## Verification

Fresh commands ran from `backend` using existing dependencies:

| Command | Result |
| --- | --- |
| `uv run --offline python -m unittest discover -s tests/cnc/login -p test_*.py -q` | 74 passed, zero skips; 14.262 seconds |
| `uv run --offline python -m unittest discover -s tests/cnc/quote -p test_xometry_runner.py -v` | 9 passed, zero skips; 27.094 seconds |
| `uv run --offline ruff check --no-fix app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed |
| `uv run --offline ruff format --check app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed; three files already formatted |
| `uv run --offline basedpyright app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed; zero errors, warnings or notes |

All fresh commands completed successfully on the first attempt. The login suite
emits expected fixture diagnostics (intentional HTTP failure responses and
invalid-ciphertext checks) and asyncio slow-task warnings; these did not produce
test failures. Frontend and broader browser suites were not rerun for this
incremental provider-only review; their previous evidence remains historical.

Reviewed SHA-256 fingerprints:

| File | SHA-256 |
| --- | --- |
| `backend/app/modules/cnc/login/providers.py` | `3c003605f5ad15ea89aa0bc25d2774acefb73b78624218db74cb15434de2032a` |
| `backend/tests/cnc/login/test_providers.py` | `ee8030ac1bd9822e8ca43855ca681b06f555e9705e7caa29f3be84f3474851e7` |
| `backend/tests/cnc/login/test_xometry_readiness.py` | `e09020cfdc6dccf1bfab4b567ff0cd717f301272e3b46120455086a04333d26c` |

This completes the handoff's pending incremental independent check, not the
full task's real quotation acceptance gate.
