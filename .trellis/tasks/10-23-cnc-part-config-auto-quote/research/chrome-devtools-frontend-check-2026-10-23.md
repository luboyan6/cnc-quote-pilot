# Frontend automatic quote review — 2026-10-23

Reused task: `10-23-cnc-part-config-auto-quote`. Review began from the existing dirty `dev` worktree at `93dff6ec`; existing changes were preserved. This sub-agent reviewed the frontend only and did not operate a browser. The parent session owns Chrome DevTools and live provider evidence.

## Fixed findings

1. **Pre-run rejection reason was lost.** The backend emits a fixed `CustomException.msg` (`backend/app/modules/cnc/quote/routes.py:35`), and the shared HTTP interceptor rejects failures as `HttpError.message` or a business response. `useAutoQuote` previously converted all account/start failures to a generic notice, hiding actionable upload authorization, file and platform errors. `useAutoQuote.ts:185` and `:227` now use the same allowlisted mapping as the dialog (`quoteMessages.ts:73`, `:80`; `AutoQuoteDialog.vue:234`). Failed business envelopes retain their `msg` for that mapping. Unknown messages and transport failures retain the existing generic notice; no request is replayed. Added the actual `PLATFORM_CONFIGURATION_INVALID` and `ACCOUNT_UNAVAILABLE` reasons while preserving existing reasons, including `PROVIDER_AUTOMATION_UNVERIFIED`.
2. **Inherited object keys could bypass the unknown-reason fallback.** The former plain `reasons[reason]` lookup accepted `constructor`/`__proto__` via the object prototype. The shared mapper requires an own key and returns fixed strings only. Regressions cover these names without exposing arbitrary server content (`cnc-part-config-auto-quote.spec.ts:518`).
3. **Formatting check failed in the existing shared-browser consumer.** Applied Prettier only to `cnc_account/AccountLoginDialog.vue`. This changed ternary formatting, preserving its existing behavior and all uncommitted content.

Change boundary: one local fixed-message helper, its two existing consumers, necessary regressions, and the formatter-only account-dialog edit. Public API paths, global HTTP handling, provider operations and existing configuration CRUD were retained.

## Verified behavior and limits

| Requirement | Source and automated evidence | Scope of conclusion |
| --- | --- | --- |
| Per-row action, permission gates and disabled configuration | `index.vue:190`, `:750`; options suite exercises the actual row action and absent account-update permission | Frontend action verified; server authorization requires backend evidence |
| Zero/one/multiple eligible accounts; arbitrary platform record ID | `useAutoQuote.ts:194`, `:237`; lifecycle fixtures use platform ID 205; reject non-eligible accounts and display the actual recovered existing account | Synthetic API data, not an assertion about the business DB |
| Stage/status/result rendering | `AutoQuoteDialog.vue:66`, `:70`, `:82`, `:258`; preserves decimal strings, currency, unit/line branch, original lead-time wording and nullable tax/shipping; separates QUOTED, REFERENCE_ESTIMATE, PENDING_REVIEW and FAILED | Mocked result/UI correctness; no real provider quote was produced by these tests |
| Human handling and serial polling | `useAutoQuote.ts:123`, `:249`; WAITING_HUMAN requires can_input, no frame fetch when false, stale reads cannot overwrite a command response | Input/continue target the same mocked run; real login/session reuse is separate |
| Close, row change, late responses and no blind replay | `useAutoQuote.ts:69`, `:82`, `:159`, `:281`; waits prior creates/cancels across configurations, cancels late-created runs, releases object URLs, stops terminal polls and pending input | Vitest lifecycle coverage; cancellation transport failure remains governed by server ownership/lease checks |
| Pre-run error propagation | `cnc-part-config-auto-quote.spec.ts:129`, `:160`; accounts/start each cover Error/HttpError.message, rejected data.msg and failed-business-code envelopes; unknown transport contents remain hidden and no polling/replay follows | Dialog text verified; existing global interceptor still owns its separate toast behavior |
| Existing account and upload behavior | Account login/API/platform options and part upload suites included below | Regression coverage, not real platform upload acceptance |

No new frontend blocker remains after the local fixes. The shared global interceptor may still show the backend machine reason in its toast; changing that shared behavior was outside this approved repair. Actual received STEP bytes, effective provider parameters, geometry, quote freshness and current price need the parent session's backend/live evidence. These checks cannot satisfy AC-03 or AC-08 by themselves.

Follow-up accessibility limitation: the parent session's Chrome DOM/screenshot inspection confirmed all four row-operation icons exist; an empty accessibility snapshot was not evidence of missing actions or denied permissions. Static inspection confirms the existing `renderTableOperationCell` (`src/utils/table/index.ts:525`) wraps `FaButtonTable` in tooltips. That component's root (`src/components/forms/fa-button-table/index.vue:3`) is a clickable icon-only DIV without role, aria-label or tabindex; labels exist only as tooltip content. The current options test substitutes text buttons, so it cannot establish accessibility of this real component. No table or permission change was made during this follow-up; this existing shared-component limitation remains recorded for the coordinator.

## Commands and results

Working directory: `E:/AIWorkspace/cnc-quote-pilot/frontend/web`. Commands were non-mutating except the explicitly noted one-file formatter. The initial run passed 7 suites / 56 tests. Six newly added error-propagation regressions failed before the fix, proving the covered gap. Final focused run: **7 suites / 66 tests passed**, exit 0, duration 17.30 s (18:54:50 +08:00). Ten regressions were added; none weakened.

```powershell
pnpm exec vitest run src/__tests__/cnc-part-config-auto-quote.spec.ts src/__tests__/cnc-part-config-quote-api.spec.ts src/__tests__/cnc-part-config-options.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-platform-options.spec.ts src/__tests__/cnc-part-upload.spec.ts
pnpm exec vitest run src/__tests__/cnc-part-config-auto-quote.spec.ts -t '固定原因显示中文'
pnpm run type-check
pnpm run build
```

The `-t` command above was the intentional pre-fix regression run (6 failed, 21 skipped). Standalone type-check passed before the local fix. The final `pnpm run build` also passed, exit 0: `vue-tsc --noEmit && vite build`, 3,988 modules transformed, Vite built in 4m 25s. Its embedded type-check and production assets cover the final source hashes below; no product/test edits occurred after this build started.

Final scoped ESLint, Prettier and Stylelint: **passed**, exit 0. The initial Prettier run identified only AccountLoginDialog; the following one-file formatting command fixed it:

```powershell
pnpm exec prettier --write src/views/module_cnc/cnc_account/AccountLoginDialog.vue
pnpm exec eslint src/views/module_cnc/cnc_part_config/index.vue src/views/module_cnc/cnc_part_config/AutoQuoteDialog.vue src/views/module_cnc/cnc_part_config/useAutoQuote.ts src/views/module_cnc/cnc_part_config/quoteMessages.ts src/views/module_cnc/components/ControlledBrowser.vue src/views/module_cnc/cnc_account/AccountLoginDialog.vue src/api/module_cnc/cnc_part_config.ts src/__tests__/cnc-part-config-auto-quote.spec.ts src/__tests__/cnc-part-config-quote-api.spec.ts src/__tests__/cnc-part-config-options.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-platform-options.spec.ts src/__tests__/cnc-part-upload.spec.ts src/views/module_cnc/cnc_part/index.vue
pnpm exec prettier --check src/views/module_cnc/cnc_part_config/index.vue src/views/module_cnc/cnc_part_config/AutoQuoteDialog.vue src/views/module_cnc/cnc_part_config/useAutoQuote.ts src/views/module_cnc/cnc_part_config/quoteMessages.ts src/views/module_cnc/components/ControlledBrowser.vue src/views/module_cnc/cnc_account/AccountLoginDialog.vue src/api/module_cnc/cnc_part_config.ts src/__tests__/cnc-part-config-auto-quote.spec.ts src/__tests__/cnc-part-config-quote-api.spec.ts src/__tests__/cnc-part-config-options.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-platform-options.spec.ts src/__tests__/cnc-part-upload.spec.ts src/views/module_cnc/cnc_part/index.vue
pnpm exec stylelint src/views/module_cnc/cnc_part_config/index.vue src/views/module_cnc/cnc_part_config/AutoQuoteDialog.vue src/views/module_cnc/components/ControlledBrowser.vue src/views/module_cnc/cnc_account/AccountLoginDialog.vue src/views/module_cnc/cnc_part/index.vue
```

`git diff --check -- frontend/web/src`: passed (only Git's pre-existing LF-to-CRLF notice for configuration index.vue).

## Reviewed source identity

SHA-256 after the last product/test edit and before the final build. No later source edits are planned in this review.

| File (under frontend/web/src/) | SHA-256 |
| --- | --- |
| views/module_cnc/cnc_part_config/index.vue | A9209E3704B094557672F2A4923D310F4428A21DF0BE6FB12255806C5D18F418 |
| views/module_cnc/cnc_part_config/useAutoQuote.ts | F73D4F81CD22ABCF433D15574D71E912EF4A72742D2BE7901971E2F45AAB5994 |
| views/module_cnc/cnc_part_config/AutoQuoteDialog.vue | BE3499E980DED5D5F18DF1BA2CE67FF67167BF77F398BBD23B1E08117DDF94C0 |
| views/module_cnc/cnc_part_config/quoteMessages.ts | 27DAB91D28849A6A93DDDDB9F1C486A25A1881C76DB44836BEB5AD1888236712 |
| views/module_cnc/cnc_account/AccountLoginDialog.vue | 0A9546734320732879A572B0D5F35AA8DC529F45EE39A188634BECDB5EEAA6B4 |
| __tests__/cnc-part-config-auto-quote.spec.ts | 4B2500B938AE779E17BC8FC62A41A6539B1C08E3734F4E339053E5A2FF9176AE |

Suggested spec sync for the coordinator: document that fixed reason mapping is shared by terminal/run notices and pre-run API rejection notices; unknown messages remain generic and never trigger a mutation retry. No Trellis task was created or archived, and no commit was made.
