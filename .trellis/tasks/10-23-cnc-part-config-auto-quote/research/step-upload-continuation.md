# STEP upload continuation — 2026-10-23

## Scope and recovered intent

Used `trellis-start`, `trellis-before-dev`, and a focused local `trellis mem search "setp" --limit 5`. Prior sessions `01a166ba-013` / `01a166c3-355` explicitly requested upload buttons in create/edit, original filename and local storage path autofill, and accepted `.step`, `.stp`, `.setp`. Preserve that compatibility spelling; do not silently extend recognition into geometry parsing. Reused the existing shared request/auth conventions. No live browser, provider, quote runtime, quote UI, business DB, specs, or unrelated edits were changed or exercised. Managed quote research's uncertain receipt remains untouched.

## Changes and audit

- `backend/app/utils/upload_util.py`: STEP/STP/SETP now require basic Part 21 start/end markers. Empty, disguised and truncated CAD uploads are rejected before storage. Read at most configured maximum + 1 bytes even if UploadFile.size is absent/inaccurate; save the exact checked buffer. Existing non-CAD MIME warning behavior, allowed types, directory routing, and confinement remain intact. Retained prior POSIX URL conversion.
- `frontend/web/src/views/module_cnc/cnc_part/index.vue`: upload/download controls and handlers honor `module_common:file:upload` / `module_common:file:download`. Successful replacement/removal resets third-party authorization and file-specific form metadata. Explicit empty declared_unit clears the previous persisted declaration: shared BaseCRUD ignores null and omitted fields. Failed replacement preserves existing metadata/consent. Retained prior 50 MB boundary, request aborts, duplicate-submit guard, filename/path autofill and Windows slash normalization.
- `frontend/web/src/__tests__/cnc-part-upload.spec.ts`: 12 tests cover extensions/fallback names, metadata + save payload, edit/download, consent/unit reset, removal, permission denial, invalid size/type, server/network failure preservation, close/unmount cancellation, duplicate upload/save prevention.
- `backend/tests/cnc/upload/test_step_upload.py`: 12 isolated unittest cases cover actual routes/dependencies and service/storage. STEP extensions/case/alias, framing rejection, size metadata bypass, exact size boundary, all existing non-CAD suffixes, all upload directory types, traversal/sibling confinement, authenticated round trip, permission 403 and unauthenticated 401.
- Pre-existing owned changes preserved: `backend/app/modules/common/file/service.py` POSIX file_path response; `backend/app/config/setting.py` CAD extension allowlist and global MAX_FILE_SIZE=50 MiB. No additional edits to these two files in this continuation.

## Verification

From `backend`:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests/cnc/upload -p test_step_upload.py -q
.venv/Scripts/ruff.exe check --no-fix app/utils/upload_util.py app/modules/common/file/service.py app/config/setting.py tests/cnc/upload/test_step_upload.py
.venv/Scripts/basedpyright.exe app/utils/upload_util.py app/modules/common/file/service.py app/config/setting.py tests/cnc/upload/test_step_upload.py
```

All pass: 12 tests; Ruff clean; basedpyright 0 errors/warnings. HTTP cases retain real AuthPermission dependencies but substitute a synthetic actor rather than accessing business users/tokens. Tests use temporary storage and do not run application startup/migrations.

From `frontend/web`:

```powershell
pnpm exec vitest run src/__tests__/cnc-part-upload.spec.ts src/__tests__/cnc-part-config-options.spec.ts
pnpm exec eslint src/views/module_cnc/cnc_part/index.vue src/__tests__/cnc-part-upload.spec.ts
pnpm exec stylelint src/views/module_cnc/cnc_part/index.vue
pnpm exec prettier --check src/views/module_cnc/cnc_part/index.vue src/__tests__/cnc-part-upload.spec.ts
pnpm run type-check
```

Vitest: 20 tests pass (12 upload + 8 existing options). Scoped ESLint, Stylelint and Prettier pass. Full vue-tsc passed again after the explicit empty-unit adjustment (exit 0).

## Limits and follow-ups for the coordinator

- This product path performs extension/framing recognition plus filename/path/byte-size autofill. It does **not** extract real geometry, dimensions, volume, units, or manufacturability. Frontend validation_status stays PENDING. Separate task-local OCP research is not integrated here.
- `.setp` remains an explicitly requested upload compatibility alias. `app/modules/cnc/browser/files.py::TrustedStep` accepts only `.step` / `.stp`; such an alias file will be rejected by the quote reader. Changing that contract/canonicalizing old records requires a separately coordinated decision beyond this ownership boundary.
- New/replaced files remain upload_authorized=false. The current part form still hides the third-party consent field; enabling an explicit consent workflow is not part of upload autofill and cannot be assumed from local upload.
- Shared BaseCRUD.update excludes null/omitted values. Empty declared_unit and explicit authorization=false persist correctly; clearing optional numeric file_type only clears the local form, not an existing DB value. Do not invent a numeric sentinel without a defined file_type contract. Removal is form unlinking, not server file deletion; storage cleanup and manual-path metadata consistency remain existing concerns.
- Global 50 MiB default applies to all existing upload consumers, as in the inherited change; no per-CAD settings split was introduced. Deployment overrides and reverse-proxy multipart limits were not exercised.
- Common upload/download remain authenticated permission-scoped, with storage-root confinement rather than per-part object ownership. No new ACL model or static-file exposure policy was introduced in this slice.
