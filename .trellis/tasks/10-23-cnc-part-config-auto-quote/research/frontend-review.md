# Frontend independent review — 2026-10-23

## Reviewed boundary

Reviewed the quote API, configuration list entry and permissions, `useAutoQuote`,
`AutoQuoteDialog`, shared `ControlledBrowser`, extracted account login dialog,
and their regression suites. Read backend DTO/routes/service/runner/repository
to check the API contract. Backend edits remain owned by the backend implementer.
Preserved the pre-existing configuration CRUD/options changes.

## Findings fixed

1. **Cross-configuration account race** (`useAutoQuote.ts`). The reopen barrier
   waited only for cancellation under the next configuration's ID. Switching A
   to B could start B while A still held the same account. The barrier now waits
   for all preceding quote closes, consistent with this UI's single-run model.
2. **Unfinished create race** (`useAutoQuote.ts`). When A's create POST had not
   returned yet, no cancellation promise existed. Switching to B could race A's
   active server run. Track outstanding creates and await cancellation of any
   late-created run before admitting B. Added meaningful delayed-response
   regressions for both races.
3. **Lead-time DTO mismatch** (`AutoQuoteDialog.vue`). `LeadTime.as_dict()` emits
   the original string as `text`, but the dialog only read `raw_text`/`raw`.
   Canonical `text` now takes priority, retaining the existing legacy fallbacks.
   The result rendering test now uses the actual backend shape.
4. **Actual reason-code mismatch** (`AutoQuoteDialog.vue`). Browser errors are
   lowercase enum values, but several dialog mappings used uppercase aliases.
   Added actual parameter/file/mutation/identity/evidence reasons and concrete
   quote phase reasons. Unknown content still uses fixed safe Chinese text.
   Added a regression for actual codes and unknown private content.
5. Declared optional nullable `freshness` in the result type to match backend
   `QuoteResult`, without calculating or inventing a freshness claim in the UI.
6. **Existing run under another selected account** (`useAutoQuote.ts`, dialog
   and list wiring). Following the main session's approved interpretation of
   same-config deduplication, adopt the actor-private active run returned by the
   server if its account belonged to the frozen eligible candidates. Update the
   selected account and display an explicit informational recovery notice. The
   notice clears on terminal state/close. New tests verify displayed original
   account, no second start/no auto-cancel, and rejection of ineligible accounts.

## Findings referred to main/backend

- `QuoteActivity` retains the start-time `AuthSchema`; `repository.validate`
  rereads configuration/part/account but uses cached actor superuser/permissions.
  Automatic steps can outlive a user/role/menu revocation. Main/backend was
  provided exact authentication-model evidence and a quote-local current-actor
  permission refresh recommendation. The backend owner has since added the
  quote-local `ActorAuthorizer` and independent refresh at validation, snapshot,
  lookup, candidate and creation boundaries. Full backend verification remains
  outside this frontend review. No global auth redesign was made here.
- Terminal quote results can precede owned browser cleanup: `LoginManager.start`
  waits for cleanup only when the owned login status is `CLOSED`/`FAILED`, while
  an already-terminal quote can still have login status `READY`. Immediate new
  quotation can therefore receive `ACCOUNT_BUSY` until cleanup finishes. Main
  was given the exact branch and a delayed-cleanup regression recommendation;
  this shared-runtime edit remains with the backend owner.

## Verification

- Six focused frontend suites passed before fixes: **39 tests**.
- After race, result-contract and existing-account regressions: **44 tests passed** across the same
  six suites (quote lifecycle/API/config options and account login/API/options).
- ESLint and Stylelint passed for all nine changed/new frontend files; Prettier
  caught one long alert element in the final correction, which was formatted
  with the project's Prettier command and rechecked successfully.
- Full `pnpm run type-check` passed, including the create/cancel barrier changes;
  the final source-frozen production command also passed its `vue-tsc --noEmit`
  step before entering Vite compilation.
- Production `pnpm run build` passed: **3987 modules, 3m 58s** before the final
  reason-map/lead-time/recovered-account edits. A final build including those edits is running;
  exact output is in `frontend-final-build.log` and will be recorded below.

These checks are synthetic/code-level evidence. They do not establish actual
Xometry/JLC authentication, uploaded file identity, parameter fidelity, or live
price semantics. No live quote acceptance is claimed in this report.
