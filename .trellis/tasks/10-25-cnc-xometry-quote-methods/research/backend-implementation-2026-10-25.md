# Xometry backend methods: implementation and validation

## Scope and acceptance boundary

Implemented the Xometry methods and existing quote/login integration. This is application code with real local Chromium/SDK and isolated durable-owner tests; it is not a successful managed Xometry upload or quote. No provider upload, declaration choice, configuration save, or quote request was performed by this implementation worker.

`quote/providers.py` now has an explicit Xometry registration path. Its private `_REVIEWED_XOMETRY_BINDING` remains absent because current managed-route receipt/readback/price evidence is unavailable. Xometry requests therefore stop before upload with `XOMETRY_BINDING_UNVERIFIED`; other provider registration remains unchanged. The code does not activate a synthetic binding, load historical platform JSON, or manufacture a remote receipt/geometry/currency.

## Implemented methods

`backend/app/modules/cnc/quote/xometry.py` supplies:

- Trusted, source-only `XometryDOMBinding`, `DOMValue`, and `ParameterControl` contracts for reviewed native controls and value representations. There are no invented production selectors or user-supplied script/locator readers.
- Current managed-route inspection rejecting testdrive and the historical `vercel_part_config` variant.
- One official `set_input_files` operation with frozen, hash-verified bytes and current actor/input revalidation immediately before mutation.
- A uniquely new parsed part/file receipt, exact SDK file name and byte length, and positive finite geometry. Existing staged/history parts cannot become this run's upload.
- Exact option-title matching, complete supported-key validation, dependency-order controls, separate Save Configuration, and saved-value equality. No implicit material/temper/form substitution.
- Save-triggered recalculation adoption without clicking Save a second time in submit, remote quote/part/revision/time correlation, explicit ISO currency/price scope, and original typed lead-time context.
- A final parameter/revision/quote-ID recheck to reject values read across a changing page generation.
- Explicit provisional estimate/review outcomes and read-only reconciliation of upload, declaration, saved configuration, and submission receipts.

The binding is intentionally unpopulated until its fields have current normal-managed-route evidence. Providing a binding is trusted engineering registration, not an administration flag or arbitrary JSON capability.

## Declaration and owner contract

`QuoteRunView.export_declaration` is optional and contains `declaration_id`, plain-text `statement`, and two `{value, label}` options with values `not_controlled` and `controlled`. No option is preselected by the server.

New endpoint: `POST /cnc/cnc_part_config/{id}/quote/runs/{run_id}/declaration`, strict body `{declaration_id, choice}`. Existing seven quote endpoints remain compatible. The current statement/options/file hash determine the declaration version; stale content is rejected/refreshed.

`QuoteRepository.record_declaration` commits actor/run/config/account/file SHA-256, exact displayed statement/options, choice, quote-only scope, and decision time privately before Continue. A compatible `DeclarationReceipt` and `Operation.DECLARATION` use the existing durable intent store and shared mutation guard. An unknown Continue is not repeated.

The existing login owner receives the typed command; HTTP never touches Page. While declaration choice is required, public generic input/resume is blocked. On identity expiry, coordinates may be enabled only on the recognized hosted `login.xometry.com` surface in the same owned Page. A pending declaration is retained privately, and every subsequent input rechecks whether authentication has returned to the quote: a stale login-frame click is ignored and the current declaration is restored before any further user action. Identity failure while the declaration itself is visible leaves coordinate input blocked.

Delayed Save Configuration enters bounded, read-only configuration reconciliation. Unchanged/pending revision returns no receipt; it does not cause another Save. A cancelled unresolved Save cannot be bypassed by a new run for the same file.

## Cross-run uncertainty and the latest user corrections

Admission checks preserve all earlier claimed/uncertain operations for the same account/platform/owner. An authoritative equal file hash, or missing/invalid legacy frozen hash, blocks a new same-file mutation. A valid known different frozen SHA-256 may identify a distinct file and proceed without removing the old claim. No historic run ID or filename is hardcoded in this policy.

The main session reported the user's explicit correction that `part.upload_authorized` is a test column unrelated to Xometry website authorization. Accordingly:

- `source_file(..., require_upload_authorization=True)` keeps existing direct/other-provider behavior by default.
- Resolved Xometry snapshots pass `False`; their revision fingerprint also excludes this test column.
- No database value is changed. Actor/RBAC/account/root/framing/size/hash/current-input/intent guards remain intact.
- Actual SQLite tests prove that changing the column does not block or invalidate Xometry snapshots, file tampering still stops, and JLC retains its former column/revision behavior.

The selected L072 live test's quantity/default-configuration instruction belongs to that test only. Ordinary product material/extras handling remains strict; this worker did not replace stored material values or alter default product semantics.

## Changes owned by this worker

- New `quote/xometry.py` and `tests/cnc/quote/test_xometry_adapter.py`, `test_xometry_runner.py`.
- `quote/{contracts,providers,repository,runner,service,routes}.py`.
- Minimal `browser/contracts.py`, `browser/workflow.py`, and `login/runtime.py` integration.
- `tests/cnc/quote/test_quote_repository.py`: provider-scoped test-column regression.
- `tests/cnc/quote/test_quote_runner.py`: separate independent mismatch and cached-price cases, because an unresolved first Save now correctly fences a second same-file run.

`ProvisionalQuote` moved to shared browser contracts and is re-exported from its original quote-contract import path; old imports and serialized upload/configure/submit receipts remain compatible. Terminal-view equality normalizes newly optional fields when reading older persisted views. No database schema, settings, credentials, existing uncertain intent, or unrelated JLC/MCP/agent implementation was changed.

## Validation observed

- Focused app Ruff: passed for all ten owned app files. New/updated owned tests also pass narrow Ruff.
- Focused app basedpyright: `0 errors, 0 warnings, 0 notes` on the final source, including provider-policy/hash-fence adjustments.
- Targeted formatting: 14 owned app/test files passed; no all-repository `--fix` operation was used.
- Concrete real local headless Chromium adapter suite: 11 cases passed in independent review, including exact file bytes, exact title matching, declaration immutability/one Continue, delayed Save, input revocation before Save, wrong quote ID, `$` rejection, mixed-revision reads, and provisional results. All browser routes were fulfilled in process; none were live Xometry traffic.
- Real durable-owner runner suite: 9 tests passed after hash-aware fence refinement, including decision-before-Continue, stale/uncertain declarations, safe reauthentication, delayed Save, same-file replay denial, distinct-file admission, and absent legacy hash denial.
- Latest provider test-column regressions: 2 actual SQLite tests passed.
- Existing login suite: 62 tests passed after the owner changes.
- Existing browser suite: 98 tests passed with 13 existing opt-in/platform skips after shared receipt/workflow changes.
- The earlier full quote run had 73 cases with one old chained-negative-case error, now corrected by separating those independent cases. The final full quote suite (expected 77 cases after the new regressions) is assigned to independent review; do not describe the earlier failed run as green.

Initial redirected test attempts were denied access to uv's cache and did not execute tests. Retrying through the approved escalated `uv run --offline --no-sync` capability ran the suites above without dependency changes.

## Remaining live work

Normal managed authentication, reviewed field bindings and provider limit, actual frozen-file receipt/geometry, full saved-parameter readback, and same-run explicit monetary/lead-time evidence still need live verification before registration. A public uploader or historical numeric quote does not meet those gates. The earlier uncertain upload remains unresolved and preserved.
