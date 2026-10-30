# Independent Xometry login timeout check — 2026-10-26

## Scope

Incremental review of the interrupted Xometry submit-timeout reconciliation in
`backend/app/modules/cnc/login/providers.py`,
`backend/tests/cnc/login/test_providers.py` and
`backend/tests/cnc/login/test_xometry_readiness.py`. Loaded the saved complete
native Trellis context and reviewed current task contracts, relevant source and
tests. Preserved concurrent JLC changes. No product/test edits were necessary.
No real provider, credentials, application database or browser operations were
performed by this reviewer.

## Findings (fixed)

None. The reviewed timeout path delegates credential submission once, then uses
at most three same-Page read attempts under an eight-second outer timeout. It
does not navigate, resubmit credentials or modify authentication state.

The positive DOM guard requires a fully loaded quote path, a visible enabled
native My Account control, and absence of the observed guest/sign-in and
credential/OTP/captcha controls. Both native `disabled` and
`aria-disabled="true"` are rejected. The existing guarded identity request must
match the intended account, and positive UI readiness is checked again after
that request. Wrong identity propagates without further attempts. Read retries
are limited to the observed navigation-context transition. JLC does not enter
this reconciliation branch.

## Findings (not fixed)

1. **Ordinary login readiness remains unresolved.**
   `providers.py:224` returns an ordinary successful `_submit` result directly;
   only a Playwright timeout invokes the positive settled-UI reconciliation.
   `LoginProvider.verify` at line 196 remains the earlier exact-identity plus
   negative-UI guard. During an empty hydrating shell, absent negative controls
   can therefore allow the owner at `runtime.py:171` to verify and navigate
   before the eventual guest UI appears. The main session's current live
   diagnostics report that sequence, followed by a guest page after additional
   settling, while the user reports ordinary-browser quoting works. This review
   does not establish the site's underlying authentication cause. Changing the
   normal path or runtime requires coordination and current live evidence; it
   is outside this incremental timeout correction and was left unchanged.
2. **Live quotation acceptance and production binding remain incomplete.**
   This review establishes neither a usable real uploader nor the selected
   frozen file's upload receipt, complete saved parameters or current price.
   Synthetic tests and this incremental pass cannot activate the binding or
   complete the task.
3. **Spec synchronization remains with the main session.**
   The account-login spec describes the earlier negative readiness check, but
   should also capture the bounded timeout reconciliation and enabled positive
   account-control requirement. No spec edits were made by this reviewer.

## Verification

Fresh commands ran from `backend`, with no dependency installation:

| Command | Result |
| --- | --- |
| `uv run --offline ruff check --no-fix app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed |
| `uv run --offline ruff format --check app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed; three files already formatted |
| `uv run --offline basedpyright app/modules/cnc/login/providers.py tests/cnc/login/test_providers.py tests/cnc/login/test_xometry_readiness.py` | Passed; zero errors, warnings or notes |

Reused unchanged test evidence from
`login-timeout-verification-2026-10-26.md`: **73 login tests** and **9 Xometry
owner tests** passed with zero skips. Source review found meaningful assertions
for late success, identity mismatch, no second submission/navigation, empty and
loading shells, retained challenges/callbacks, navigation-context loss,
post-identity UI regression and disabled controls. No product/test changes or
new unresolved test concern justified repeating those suites. Unrelated
frontend/browser suites were not rerun.

Reviewed SHA-256 fingerprints:

| File | SHA-256 |
| --- | --- |
| `login/providers.py` | `7cc049c1222df61d916c63c1c6be441cd80094936955cabe4323e742077aef04` |
| `login/test_providers.py` | `5acad4346adbefe01a12b5f5e714a131a32de4592447d4e6dd78f3a1107008f8` |
| `login/test_xometry_readiness.py` | `b48c209162433a53cb141dcca7f0d4b42c365545bd2e5842b34e528881762eaa` |

This is an incremental code check, not the final full-task quality or live
acceptance gate. No commit, task completion or archive action was performed.
