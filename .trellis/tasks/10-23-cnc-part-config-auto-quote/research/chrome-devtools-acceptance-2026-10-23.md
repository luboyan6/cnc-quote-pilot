# Chrome DevTools real-page continuation acceptance - 2026-10-23

## Scope and environment

Continued the approved `10-23-cnc-part-config-auto-quote` task using its isolated official Chrome DevTools session (`pageId=2`) at `http://localhost:5180/web#/module_cnc/cnc_part_config`. The test used the enabled Xometry configuration (`config_id=1`, linked STEP, `Aluminum 6061-T6x (Best Available)`, quantity 1, `Standard`) and the one enabled same-platform account. Credential-bearing headers and values remain redacted in the evidence log.

This is a real local application/API browser test, but it is not a successful provider quote. The production adapter factory still returns no verified adapter, so the run is expected to stop before provider login, upload, parameter mutation, or price retrieval.

## Observed UI and API behavior

- The real row action was identified by its money icon and clicked. The eligible-account request returned HTTP 200 with exactly one Xometry account (`id=1`); the UI selected it without opening a chooser.
- The first quote start returned HTTP 200 with the same configuration/account, requested material/quantity/finish, and a new run in `STARTING / prepare`. Polling reached HTTP 200 terminal state `FAILED`, reason `PROVIDER_AUTOMATION_UNVERIFIED`, and `result=null`. The UI showed the fixed Chinese failure notice and no price.
- A second explicit start also stopped at the same provider-verification gate. Neither production run reached an upload/configure/quote intent.
- Closing a separately reopened active run used the visible “Stop and close” control. DELETE returned HTTP 200 and the run ended `CANCELLED / QUOTE_CANCELLED`. The final request list contained no later poll or mutation for that run; the dialog was gone and every row action was idle/enabled.
- The final page had no visible dialogs and no browser console errors or warnings.

## Persistence and side-effect boundary

The read-only quote inventory confirms the UI runs above created no upload or quote intents and left no active run or account lease. There is one distinct pre-existing research run (`e8dea2c1-3430-4279-832e-1e655ced79b8`) with an `upload/uncertain` intent (`RESEARCH_UPLOAD_UNCONFIRMED_NO_RETRY`). That record is not evidence from these UI starts and must not be deleted or blindly retried. The earlier controlled research upload reached Xometry's export-classification declaration and stopped before choosing an option or requesting a price.

## Acceptance boundary

Verified in this real browser session: row action availability, one-account automatic selection, correct configuration context, safe fail-closed provider gate, no fake/stale price, explicit cancellation, cleanup of polling/dialog/loading state, and clean console.

Not verified: zero/multiple live account cases; provider identity/session reuse through a quote adapter; a new or reconciled Xometry upload; effective parameter save/readback; a same-run Xometry price; JLC CNC; or real QUOTED/REFERENCE_ESTIMATE/PENDING_REVIEW semantics. Those criteria remain open. The production adapter must remain disabled until the exact provider controls, mutation semantics, and result evidence are verified; no public demo price or historical DOM selector may be substituted.

## Evidence

- `chrome-devtools-evidence-2026-10-23.jsonl`: redacted DevTools actions, request/response records, final lifecycle state, and console check. Relevant local request IDs: accounts `15777`, first start/status `15778-15783`, second start/status `15784-15790`, cancellation start/delete `15792-15793`.
- `chrome-quote-first-click.png` and `chrome-quote-first-run.png`: screenshots from the real local configuration page and first run.
- `quote-runtime-inventory-2026-10-23.json`: read-only database/run/intent inventory.

