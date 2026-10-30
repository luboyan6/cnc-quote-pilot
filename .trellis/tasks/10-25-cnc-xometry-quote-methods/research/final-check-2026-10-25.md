# Final independent check — 2026-10-25

## Scope and findings

Resumed the unfinished check from session `01a170c9-ea02-76d1-82db-dceac06fdf60`. Read the native injected task artifacts/specs and implementation evidence, then reviewed the Xometry methods, durable declaration/receipt flow, shared login-owner integration and part-configuration UI/API path against them.

**No concrete new defect was found. No product source or test was changed by this reviewer.** Unrelated working-tree changes and authentication-state files were left untouched. This report is the reviewer's only edit.

The reviewed flow commits a file-bound declaration decision and independent mutation intent before Continue; blocks coordinate/resume bypass; rejects stale declaration content; reconciles unknown uploads, declarations and delayed saves without repeating the mutation; and retains cross-run same/unknown-file uncertainty while allowing an authoritatively different frozen hash. Exact requested/effective values, file geometry, quote ID/revision, explicit currency and result nature are checked before persistence. The Xometry test upload column is excluded from admission/revision checks without modifying its value; direct/other-provider semantics remain covered.

## Fresh checks

Commands ran against the existing installed environment; no dependencies were downloaded or changed. Backend commands used `.venv/Scripts/` directly from `backend`.

| Check | Result |
| --- | --- |
| `python.exe -m unittest discover -s tests/cnc/quote -p test_*.py -q` | **77 tests passed**, 245.049 s, zero skips |
| `python.exe -m unittest discover -s tests/cnc/login -p test_*.py -q` | **62 tests passed**, zero skips |
| `python.exe -m unittest discover -s tests/cnc/browser -p test_*.py -q` | **98 tests**, OK with **13 existing opt-in/platform skips** |
| Focused `ruff.exe check --no-fix` | Passed on the ten task application files and five task test files below |
| Focused `basedpyright.exe` | **0 errors, 0 warnings, 0 notes** on the ten application files |
| Focused `ruff.exe format --check` | **15 files already formatted** |
| Six configuration/account Vitest suites | **6 files / 64 tests passed** |
| `pnpm run type-check` | Passed |
| Seven-file ESLint / Prettier | Passed |
| Two-Vue Stylelint | Passed |

Backend application scope: `quote/{contracts,providers,repository,routes,runner,service,xometry}.py`, `login/runtime.py`, `browser/{contracts,workflow}.py`. Focused test scope: `test_declaration_http.py`, `test_xometry_adapter.py`, `test_xometry_runner.py`, `test_quote_repository.py`, `test_quote_runner.py`.

Frontend suite names: `cnc-part-config-auto-quote`, `cnc-part-config-quote-api`, `cnc-part-config-options`, `cnc-account-login`, `cnc-account-api`, `cnc-account-platform-options`. Lint/format scope: the configuration `index.vue`, `useAutoQuote.ts`, `AutoQuoteDialog.vue`, `quoteMessages.ts`, configuration API module, and two quote test files. Stylelint covered `index.vue` and `AutoQuoteDialog.vue`.

The fresh frontend test count is 64; the previous implementation report recorded 61. These are the actual counts observed in each run. The prior successful production build is historical evidence from `validation-2026-10-25.md`; this reviewer did not repeat that build or change runtime frontend code.

## Remaining acceptance boundary

`providers.py` retains `_REVIEWED_XOMETRY_BINDING = None` and the explicit `XOMETRY_BINDING_UNVERIFIED` stop. This is the reviewed design's production activation gate, not a completed real quote. The local Chromium DOM tests intercept all routes in process and do not establish managed Xometry upload/save/price acceptance. The 13 browser skips do not count as executed browser/deployment acceptance.

The main session separately owns current managed-route research, exact selected-file live verification and any production binding. Its fresh identity/UI observations do not yet establish a parsed file receipt, saved effective parameters or same-run monetary result. Those live items and the corresponding full-task acceptance criteria remain open. No upload, declaration choice, save, quote request or purchase was performed by this reviewer.

## Follow-up audit: final Xometry readiness revision

Live research after the initial checkpoint identified a matching identity API response alongside explicit signed-out quote UI. The implementer's final correction is limited to the Xometry branch of `LoginProvider.verify`, its two provider-unit regressions and `test_xometry_readiness.py`. This follow-up reviewed those changes and their owner/runtime callers. Pre-existing parallel JLC edits in the same provider module were preserved. **No reviewer product or test edits were needed.**

The negative-readiness script is called only after a matching API identity. It rejects the two observed exact visible sign-in signals on `/quoting/`; it cannot supply identity by itself. An identity mismatch still raises before DOM inspection. The existing three-attempt budget and 0.5-second waits permit transient guest-shell hydration without introducing a second login, browser owner, navigation, credential submission or other verification-side mutation. Valid identity with no explicit negative signal retains the prior reuse path. Hidden guest controls, unrelated upload validation and a disabled action alone do not create false sign-in evidence.

Fresh final-revision verification:

| Check | Result |
| --- | --- |
| Full quote discovery, same command as above | **84 tests passed**, 249.418 s, zero skips |
| Full login discovery, same command as above | **65 tests passed**, 9.029 s, zero skips |
| Ruff on `login/providers.py`, `test_providers.py`, `test_xometry_readiness.py` | Passed |
| Ruff format check on those three files | **3 files already formatted** |
| basedpyright on `login/providers.py` | **0 errors, 0 warnings, 0 notes** |

The final quote discovery contains seven concurrently added `test_jlc_cnc_params.py` cases, explaining the increase from the initial 77 to 84. Those cases passed in discovery; this reviewer did not edit or conduct an independent feature audit of the unrelated JLC implementation. The final login count includes the new actual local Chromium matrix and two provider-unit regressions. The matrix covers eight DOM states plus absent/wrong identity, exact GET retry counts, and zero UI writes/navigation, with all network requests fulfilled locally.

The reviewed `login/providers.py` SHA-256 is `4d452b2102c9a6b29e44b5c042a1e848ffa8a1345766f1db13fe4abbb9a2a80a`. The main session separately reported its post-fix managed probe now stops at **WAITING_HUMAN / PROVIDER_VERIFICATION_REQUIRED**, with **zero quote mutations**, after the existing owner attempted normal login recovery. This is a correct blocked state rather than a real quote. The main session also recorded the final frontend production build: 3988 modules, exit 0, approximately 2m 52s, after all frontend runtime changes. Unchanged browser/frontend checks from the initial checkpoint remain applicable and were not repeated for this backend-only correction.

`cnc-account-login.md` and the auto-quote spec now document the readiness distinction, read-only retry contract and test boundary. Production binding, exact-file live upload/save/readback and current monetary acceptance remain incomplete; no provider activation or real quote is asserted by this follow-up.
