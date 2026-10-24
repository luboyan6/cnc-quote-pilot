# Frontend implementation and validation

## Implemented

- Added row-level automatic quote entry to the existing configuration list without replacing CRUD or platform/part option loading. The entry requires configuration query/detail access and update, plus account query and update; disabled configurations cannot start.
- Added typed candidate/start/status/private-frame/input/resume/cancel API functions matching the agreed backend DTO. Start sends only account ID and request UUID; file and machining inputs are resolved on the server.
- Added one/many/no-account behavior, serial status polling, epoch guards against late responses, cancellation barriers before reopening a configuration, late-created run cancellation, and object URL cleanup on close/deactivation/unmount.
- Extracted existing coordinate, key, text and wheel controls into `components/ControlledBrowser.vue`; existing account login uses the same component. Quote input and resume require `WAITING_HUMAN` with `can_input=true`. A waiting run without an available worker does not attempt to fetch a nonexistent frame.
- Added a progress/result dialog that preserves decimal strings, displays frozen requested and returned effective parameters, distinguishes verified quote/reference estimate/pending review, preserves lead-time text and marks missing tax, shipping, currency or price scope explicitly.
- Unknown backend reasons use safe Chinese fallback copy; raw server errors, provider URLs and DOM do not enter the dialog.
- Request UUID creation supports Web Crypto `getRandomValues` when `randomUUID` is absent, including LAN HTTP sessions; random-source failure clears busy/loading instead of leaving the picker stuck.

## Checks (2026-10-23)

From `frontend/web`:

```text
pnpm exec vitest run src/__tests__/cnc-part-config-auto-quote.spec.ts src/__tests__/cnc-part-config-quote-api.spec.ts src/__tests__/cnc-part-config-options.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-platform-options.spec.ts --reporter=dot
6 files passed, 39 tests passed

pnpm run type-check
PASS

pnpm exec eslint <9 changed/new frontend files>
PASS

pnpm exec prettier --check <9 changed/new frontend files>
PASS

pnpm exec stylelint <4 changed/new Vue files>
PASS

pnpm run build
PASS (exit 0; 3987 modules transformed; Vite built in 3m 40s; before the final isolated UUID fallback addition, which has focused Vitest/ESLint coverage)
```

## Scope of evidence

The frontend tests exercise the API boundary and actual list-button wiring, access gating, zero/one/many candidates, repeated clicks, delayed create/frame responses, cancellation before reopen, serial polling, terminal states, input pacing and teardown, plus original configuration CRUD/options and account login regressions. These are synthetic frontend tests. They do not establish live Xometry/JLC login, upload, parameter fidelity, price semantics or screenshot/layout acceptance; those require backend/provider and integrated live evidence.
