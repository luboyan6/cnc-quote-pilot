# CNC automatic quote dialog

## 1. Scope / trigger

Read when changing the configuration row action, quote API/composable/dialog, or the shared ControlledBrowser used by quote and account login. Backend contract: [cnc-auto-quote.md](../backend/cnc-auto-quote.md).

## 2. Signatures

`useAutoQuote()` exposes visible/run/selectedRow/accounts/selectedAccount/choosingAccount/loadingIds/frameUrl/error/info/busy/interactive and open/close/chooseAccount/command. The API module uses seven fixed quote endpoints and strict response types; start body allows only request_id and optional account_id. QuoteRun carries requested parameters and optional result; monetary values remain strings. `info` is the non-error notice for recovered existing-account activity.

`ControlledBrowser.vue` is shared with AccountLoginDialog. Inputs remain the existing fixed click/scroll/key/text union; no JavaScript, arbitrary URL, locator, file path or clipboard interface.

## 3. Contracts

- Render the row action using existing table operations and Element Plus style. Require config query OR detail plus config update and account query/update. Disabled configurations cannot start; preserve existing uncommitted CRUD/option logic.
- No eligible account shows an actionable message; one starts automatically, multiple require selection. Server may recover an existing same-config run with another previously selected account: only adopt an eligible returned account, display its actual masked identity and explicitly explain recovery rather than claiming a new selected-account run started.
- Poll serially around1.5s, with generation checks after every await. Never allow a late account/frame/start response to replace another row's state. Do not automatically repeat start/input/resume after transport failure.
- Closing first invalidates generation, stops/aborts read polls, releases object URLs and schedules cancellation. Before another config starts, wait ALL prior creates and cancellations, not just the same config ID: different configs may share an account. A start resolving after closure must release its returned nonterminal run.
- Human input requires WAITING_HUMAN AND can_input AND no local error/busy. WAITING_HUMAN with can_input=false must retain the reason without trying to fetch an inaccessible frame. Automatic phases cannot accept concurrent human parameter changes.
- Terminal statuses are QUOTED/REFERENCE_ESTIMATE/PENDING_REVIEW/FAILED/CANCELLED. Display them distinctly; only QUOTED is a successful final quote. Preserve exact Decimal amount/currency/unit-vs-line and nullable tax/shipping.
- LeadTime's canonical raw display field is `text`; preserve platform wording. Unknown lead time uses a human label, not JSON or invented production days. Actual lowercase BrowserStop reasons and uppercase quote-local reasons need actionable Chinese mappings; unknown reasons get a safe generic fallback.
- `quoteMessages.ts` owns the allowlisted reason mapping for both run notices and pre-run account/start failures. Recognize known `Error.message`, rejected response `data.msg`, and unsuccessful response envelopes; unknown messages, including inherited object keys, retain the generic notice. Never display arbitrary exception text or retry a mutation because its error was translated.
- Use crypto.randomUUID with secure getRandomValues UUIDv4 fallback for non-secure/LAN environments; generate inside error handling so unavailable crypto cannot strand busy/loading flags. Do not use Math.random for request IDs.

## 4. Validation & error matrix

| Event | Expected UI behavior |
| --- | --- |
| Zero/one/multiple accounts | Message / direct start / picker |
| Missing any required permission | No action/network start |
| Close A then open B while create or cancel is pending | B waits; late A is cancelled first |
| Returned same-config eligible existing account differs | Recover it with explicit notice and actual account |
| Returned wrong config/ineligible account | Reject; no silent adoption |
| Late read/frame after row switch | Ignore; revoke obsolete URLs |
| WAITING_HUMAN, can_input=false | Explain block, no unavailable frame request |
| Mutation response not confirmed | Stop sending, no automatic replay |
| Result is reference estimate or pending audit | Warning status, no success label |

## 5. Good / base / bad cases

- Good: one account auto-starts, challenge resumes same run, accurate result displays, close cleans up before the next config starts.
- Base: mocked API/synthetic provider result demonstrates UI behavior only; actual platform remains separately verified.
- Bad: open an ordinary provider tab and assume server auth transfers, treat a current timestamp as fresh-price evidence, or let a late response restore a closed dialog.

## 6. Tests required

`cnc-part-config-options.spec.ts` covers actual row click/permissions and existing configuration options. `cnc-part-config-auto-quote.spec.ts` covers zero/one/many account handling, serial reads, human control, cross-config pending-create/cancel barriers, late cleanup, existing-account recovery and exact result/status/lead-time rendering. `cnc-part-config-quote-api.spec.ts` checks fixed API paths, POST body allowlist and JPEG Blob boundary. Regress original account login/API/platform-option suites when extracting the shared browser UI.

Run focused Vitest, type-check, changed-file ESLint/Prettier/Stylelint and production build. State which code revision the build covers; do not claim a pre-edit build verifies later behavior.

The existing shared `FaButtonTable` renders tooltip-wrapped icon DIVs without button role, accessible name or keyboard focus. A text-button test substitute does not verify that component's accessibility. An empty Chrome accessibility snapshot alone does not prove row actions are absent: inspect the actual DOM and screenshot before diagnosing a permission/rendering failure.

## 7. Wrong vs correct

```ts
// Wrong: another config may use the same account as an unfinished create.
await closing.get(nextConfigId);

// Correct: serialize prior create settlement and all cleanup before admission.
await Promise.all([...starting, ...closing.values()]);
if (generation !== epoch) return;
```

Both tracked promise types handle failures before settling; do not replace them with raw rejecting network promises and lose the cleanup barrier.
