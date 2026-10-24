# STEP alias boundary repair — 2026-10-23

## Change boundary recorded before implementation

- Smallest behavior gap: `.setp` is an explicitly supported legacy STEP spelling in the configuration UI, `settings.ALLOWED_EXTENSIONS` and the existing `UploadUtil` Part 21 validation, but a successfully stored `.setp` file is rejected by both quote snapshot freezing and shared browser-file revalidation.
- The behavior lives in `quote.repository.source_file` (stored extension metadata and resolved-path suffix checks) and `browser.files.TrustedStep.read_verified` (resolved-path suffix check). The upload utility already checks the actual bounded bytes and Part 21 framing and needs no modification.
- Intended production files: `backend/app/modules/cnc/browser/files.py` for the immutable STEP suffix allowlist and its consumer, and `backend/app/modules/cnc/quote/repository.py` to consume the same allowlist for metadata and path checks.
- Intended verification files: a quote boundary regression using the actual upload service/utility, isolated SQLite snapshot freezing, shared revalidation and official-SDK buffer helper; shared-file alias regressions where needed. Verify the new regression fails before the production fix.
- Preserve the stored `.setp` filename and exact byte buffer. Keep upload authorization, rejection status, root/path, Part 21 framing, actual size/limit and SHA-256 checks. The SDK's existing private generic `part.step` filename remains unchanged.
- This repair does not enable adapters, change provider limits/selectors, change DNS, touch runtime/routes/frontend/specs/task main artifacts, run migrations, restart servers, upload to a provider or change the business database. Existing user and other-agent edits remain intact.

## Results

The fix adds `STEP_SUFFIXES = frozenset({".step", ".stp", ".setp"})` in the shared browser-file module. `TrustedStep.read_verified` and the quote source metadata/resolved-path checks consume it. Case-insensitive handling and optional metadata leading dots retain the existing behavior. No storage rename, upload-utility change or provider activation was needed.

`backend/tests/cnc/quote/test_step_file_boundary.py` exercises the actual `FileService.upload_service` -> `UploadUtil.upload_file` validation/persistence -> isolated SQLite part metadata -> `QuoteRepository.snapshot`/`source_file` -> repository/shared file revalidation -> `upload_step` SDK buffer helper. It covers `.step`, `.STP`, `.setp` and `.SETP`, including dotted metadata. The framing-valid Part 21 fixture has a point entity; this is not a solid-geometry or platform-parsing acceptance claim.

The regression verifies the original display/stored suffix remains intact, the SHA-256 and frozen buffer equal the uploaded bytes, and same-size disk changes are rejected while the helper still sends only the previously frozen bytes. Negative checks cover empty/PDF/unframed/truncated `.setp` data before storage, unsupported metadata or physical suffixes despite valid Part 21 bytes, denied third-party upload, rejected status, root, size, limit and hash guards. The shared `FileTests` adds direct lower/uppercase alias coverage without touching its DNS tests or existing symlink test.

## Before-fix evidence

The new tests were written and run before changing production files:

- `test_step_file_boundary.py`: 4 methods in 4.504 s, exit 1, `FAILED (errors=3)`. Both successful-upload alias subtests (`setp`, `SETP`) stopped in `source_file` with fixed `FILE_INVALID`; the valid `.setp` safety baseline was also rejected. Existing `.step/.STP` positive cases reached revalidation and SDK buffer assertions.
- Shared `FileTests.test_setp_alias_preserves_verified_bytes_and_sdk_name`: 1 method in 0.056 s, exit 1, `BrowserStop(file_invalid)` from `TrustedStep.read_verified` on `.setp`.

## Final focused verification

Commands were run from `backend`, using the existing environment without installation. Independent unittest discovery avoids application-wide pytest DB fixtures. Test files/SQLite transactions use temporary directories; no business DB or external provider request is involved.

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p test_step_file_boundary.py -q` | 4 methods, OK, zero skips; 6.224 s; exit 0. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p test_quote_repository.py -q` | 15 methods, OK, zero skips; 24.964 s; exit 0. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/upload -p test_*.py -q` | 12 methods, OK, zero skips; 0.608 s; exit 0. |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k FileTests -q` | 5 methods, OK with 1 existing Windows symlink-privilege skip; 0.128 s; exit 0. The skipped case is unverified, not passed. |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/browser/files.py app/modules/cnc/quote/repository.py tests/cnc/quote/test_step_file_boundary.py tests/cnc/browser/test_policy_files_state.py` | All checks passed; exit 0. |
| `.venv/Scripts/basedpyright.exe app/modules/cnc/browser/files.py app/modules/cnc/quote/repository.py tests/cnc/quote/test_step_file_boundary.py tests/cnc/browser/test_policy_files_state.py` | 0 errors, 0 warnings, 0 notes; exit 0. |

The focused runs total 36 discovered methods: 35 passed, 1 skipped. Existing asynchronous test-loop slow-task warnings did not affect assertions. `git diff --check` for the tracked production/shared-test changes passed; Git emitted only the repository's LF-to-CRLF worktree notices.

## Changed files and remaining boundaries

- Production: `backend/app/modules/cnc/browser/files.py`, `backend/app/modules/cnc/quote/repository.py`.
- Regressions: `backend/tests/cnc/browser/test_policy_files_state.py`, new `backend/tests/cnc/quote/test_step_file_boundary.py`.
- This report is the only task artifact changed by this sub-agent. Main-task artifacts, specs, existing user changes and other-agent work remain owned by the coordinating session.
- Suggested spec sync for the coordinator: `.setp` is the supported historical STEP suffix alias at upload, quote freeze and shared revalidation boundaries; it carries exactly the same authorization/root/framing/size/hash rules. The SDK still uses the private generic filename `part.step`.
- Live provider parsing/upload/quotes remain separate and unverified by these tests. The production factory was not changed; no fake amount or guessed selector was introduced. The shared mixed-DNS issue is outside this repair.
- Windows symlink behavior still needs its separately required permitted Linux verification before the file-boundary criterion can be treated as fully accepted. No source in the existing symlink test was changed.
- No commit, archive, migration, installation, real upload, server restart or business-data edit was performed.
