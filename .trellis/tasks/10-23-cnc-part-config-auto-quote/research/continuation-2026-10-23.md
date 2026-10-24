# Continuation evidence — 2026-10-23

## Recovered state

- Resumed the approved `10-23-cnc-part-config-auto-quote` task; no new task was created. The configured sample remains owned and enabled, linked STEP upload authorization is true, and its frozen specification is `Aluminum 6061-T6x (Best Available)`, quantity 1, `Standard`.
- The registered Xometry account's encrypted session was reused and current identity was verified. JLC still has no enabled account. The production quote adapter registry remains intentionally disabled until the provider contract is verified.
- The browser reached the Xometry upload flow and the authorized sample bytes were uploaded once to a quote draft. Xometry then displayed its export-classification declaration. Prior project history records the user's instruction that STEP files from `E:\AIWorkspace\3d_models` use the page's “No” option. The continuation probe stopped before selecting an option or continuing; it did not configure machining parameters or request pricing. The upload receipt is persisted as uncertain, so this run was not retried and no price is claimed.
- Do not start another quote run for this same sample until the existing uncertain upload intent/draft is reconciled. The research run identifier and redacted allowlisted DOM projection are in `xometry-upload-evidence.json`.
- The temporary DNS override was restored in the running proxy controller. Its research helper's restore body was corrected to reload the original config as a payload; the first restore attempt returned HTTP 400 and did not mutate disk config. The corrected restore returned success.

## Permission revalidation fix

`QuoteActivity.advance` now revalidates current authorization and frozen inputs after the awaited provider identity/read steps and immediately before each upload/configure/submit mutation claim. Added `test_role_revoked_during_identity_read_stops_before_upload_claim`; it revokes the role during identity verification and proves the run fails with `QUOTE_PERMISSION_REVOKED`, with zero upload and no intent row.

## STEP upload behavior

See `step-upload-continuation.md`: product upload recognizes `.step`, `.stp`, and the previously requested `.setp` alias, validates basic Part 21 framing and actual byte bounds, and fills file name/path/size/status metadata. This is format/framing recognition only. There is no integrated extraction of geometry, dimensions, volume, units, or manufacturability. Third-party upload authorization for a replaced file resets to false.

## Verification

- Final combined backend run after the permission-race regression and STEP upload tests: 182 passed, 13 skipped, 319 subtests passed; one pre-existing warning about helper-class collection. The corrected focused permission-race test also passed independently (`1 passed`).
- Ruff passed for quote, upload, and related backend paths. `basedpyright` passed for production quote modules plus STEP upload/config files (0 errors, warnings, notes). Including synthetic test modules in basedpyright reports existing fixture/test typing issues; this is not a production-module failure.
- STEP upload worker reports 12 backend tests and 20 frontend tests passed, plus scoped Ruff/basedpyright/ESLint/Stylelint/Prettier and frontend type-check.
- Frontend quote reviewer reports 44 tests passed across six suites, type-check/lint/format/style checks and production build passed. The open UI's “无法读取可用账号” message remains unexplained because the local backend HTTP listener is not running; do not infer an RBAC or route defect from that generic message.
- No provider returned a price. Xometry parameter fidelity/price semantics and JLC live integration remain unverified; quote adapter activation is blocked on those gates.
