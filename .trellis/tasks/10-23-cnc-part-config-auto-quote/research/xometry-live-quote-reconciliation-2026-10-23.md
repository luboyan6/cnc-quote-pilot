# Xometry live quote reconciliation — 2026-10-23

## Scope and method

Used the already-open Xometry CDP-bridge browser session. The session was already authenticated: it could read the account's Quotes history and open existing quote-detail pages. Actions in this reconciliation were navigation and DOM reads only. No upload, parameter edit, new quote, checkout, order, or payment action was performed.

## Observed DOM operation evidence

### Earlier controlled upload attempt (existing research evidence)

`xometry-upload-evidence.json` records the previous run `e8dea2c1-3430-4279-832e-1e655ced79b8`:

1. Authenticated dashboard exposed `#dashboard-get-instant-quote-primary`; the observed quote dialog had one `input[type=file]`.
2. The controlled Playwright executor claimed a durable `upload` intent and passed the frozen STEP byte payload once through `upload_step(locator, payload)`; it did not simulate clicking a hidden file input or use a guessed coordinate.
3. The UI changed from `Classifying…` to `1 part ready`. The staged test id included the size `300561` bytes and a generated run-specific timestamp; evidence shortened the filename to `part.step`.
4. Starting Instant Quote presented the export-control declaration. The script intentionally stopped before selecting a radio or continuing.

Database read-only inspection found that this run still has one `operation=upload`, `state=uncertain` intent with scope keys only `owner_id`, `platform_code`, and `account_id`; it has no receipt. The intent does not bind to a filename/hash in its scope, so this record cannot independently prove which remote CAD object was created. It must not be deleted or blindly replayed.

### Current attached session read-only inspection

The Quotes history showed two `Auto-Quoted` rows last updated 10/22/2026. Opening their detail pages showed:

- `Q78-4652-8737` contains a different visible CAD filename (`292.1301C …-CS-ADAPTER).step`; not the linked STEP file.
- `Q59-6980-1120` contains the exact linked source filename `D14-TO-CS-ADAPTER_LP0335_P2002B.STEP`. Its visible configuration is CNC Machining, Aluminum 6061-T6x (Best Available), Standard finish, and quantity **5**. The page shows `$48.74 ea.` and `$243.70` for the least-expensive option; the history row marks it Auto-Quoted with 8 Business Days. The linked product configuration currently requests quantity **1**.

This existing quote proves that an account quote with the same displayed filename and matching material/finish exists. It does not prove byte-for-byte identity with the uncertain run, and it is not a quote for the current quantity 1. No mutation was made to alter this historical quote.

## Outcome / stop reason

- Login/session and quote pages are usable in the attached browser.
- A previous controlled upload reached the ready-to-quote stage, but stopped at the export-control declaration. The durable upload intent remains uncertain and has no remote receipt.
- A historical auto-quote exists for the same displayed filename, but its quantity is 5 rather than the current target quantity 1.
- Therefore this session did **not** create or verify a quote matching the current configuration, and did **not** re-upload. Reconciliation is insufficient to safely claim completion; repeating the upload could duplicate an unresolved remote side effect. The next safe step is a user-confirmed decision on whether to reuse/modify the existing quote or authorize a distinct new quote after the uncertain upload has been reconciled. Any follow-up must stop before checkout/order/payment.

## Production-flow status

`backend/app/modules/cnc/quote/providers.py::resolve_quote_adapter()` remains deliberately fail-closed and returns `None`. The prior product-UI test terminates before provider upload. Browser evidence is not a verified production adapter; no selector or quote result should be inferred from these observations.
