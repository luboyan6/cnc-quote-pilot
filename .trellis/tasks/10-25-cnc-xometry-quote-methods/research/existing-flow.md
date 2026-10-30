# Existing Xometry integration evidence

Inspected on 2026-10-25. This document describes local source and historical research, not a newly verified provider session. No browser upload, declaration, configuration save, quote request, order, or payment was performed during planning.

## Request and authorization

The user requested methods implementing `.agents/skills/cnc-xometry-quote/` under the part-configuration module, referring to the account module for login reuse. After inspection exposed the empty backend adapter, the user agreed to create a task and plan frontend calls plus backend Xometry integration. The user subsequently approved the final planning summary, and implementation started on 2026-10-25.

## Current call chain

1. `frontend/web/src/views/module_cnc/cnc_part_config/index.vue:189` creates `useAutoQuote()`. `handleAutoQuote` at line 201 calls `quote.open(row)` behind existing permissions. The action is already present near line 758.
2. `useAutoQuote.ts` handles zero/one/many eligible accounts, one create request UUID, serial status/frame polling, generation guards, all-prior-create/cancel barriers, and cleanup. Its current POST body permits only account ID and request ID.
3. `backend/app/modules/cnc/quote/service.py` freezes server-side inputs, creates/reuses durable runs, and attaches `QuoteActivity` to the existing `LoginManager`. It does not control a Page from HTTP.
4. `quote/runner.py` runs upload, configuration, submission, and extraction inside the login owner. It uses `DurableIntentStore`, same-file receipts, complete parameter equality, `validate_quote`, and persistence before public success.
5. `quote/providers.py::resolve_quote_adapter` currently returns `None`, so the real pipeline stops at `PROVIDER_AUTOMATION_UNVERIFIED`. A new frontend wrapper alone cannot close that gap.

## Login ownership and reuse

`frontend/web/src/views/module_cnc/cnc_account/index.vue` uses `useAccountLogin`. The shared server implementation is `backend/app/modules/cnc/login/`, rather than a frontend function that can be imported to transfer a browser session.

`LoginManager.start(..., quote_activity=...)` can adopt the actor's existing owner. Its owner loop retains the `BrowserSession`, fenced lease, verified encrypted state, and Page. `LoginProvider.verify` checks explicit provider identity fields in the guarded Page/context. During an uploaded quote, `QuoteActivity.resume` uses read-only provider verification without navigating away.

Do not start a competing account login request from the quote UI, pass plaintext credentials to it, or use a separate personal CDP context as proof of managed-session reuse.

## File and persistence boundaries

`quote/repository.py::source_file` enforces upload authorization, trusted root, allowed STEP suffixes, size, STEP framing, and frozen SHA-256. `snapshot` freezes requested material, quantity, optional surface finish, scalar extras, and account/config revisions. `validate` rechecks current authorization and inputs before operations.

`CncQuoteRunModel` already has `frozen` and `public_view` JSON. `CncQuoteIntentModel` has scoped operation/fingerprint/state/receipt JSON with unique run/generation/operation identity. Prefer compatible extension over new tables. Existing public views intentionally omit remote IDs, paths, browser state, and credentials.

Current `Operation` values are upload/configure/submit. Explicit export declaration is not yet a typed quote command or receipt. Generic human coordinates alone are insufficient to represent an exact-file declaration decision for later automatic continuation; any new declaration command must preserve owner and durable-decision semantics.

## Evidence limits inherited from the skill

Read `.agents/skills/cnc-xometry-quote/SKILL.md` and its `references/observed-dom-and-evidence.md` for the full workflow. The skill is operator guidance and does not itself register an application adapter.

Historical evidence establishes candidate upload/declaration/configuration controls. The material popup observation belongs to a historical `vercel_part_config=test` quote route. Generated option IDs and combined option descriptions are not stable exact material titles. Public testdrive controls do not prove managed-route support.

The earlier research upload run `e8dea2c1-3430-4279-832e-1e655ced79b8` retains an uncertain upload intent without an authoritative remote receipt. It must not be reset, deleted, or bypassed with a new run. The historical quote `Q59-6980-1120` has quantity 5 versus the recorded target quantity 1 and does not reconcile frozen byte identity.

Current managed-route parameter mappings, saved-value parsing, remote geometry/receipt correlation, and current quote extraction still require implementation-time verification. Do not mark synthetic tests or historical amounts as live acceptance.

## Relevant specifications and tests

- `.trellis/spec/backend/cnc-auto-quote.md`
- `.trellis/spec/backend/cnc-account-login.md`
- `.trellis/spec/backend/browser-executor.md`
- `.trellis/spec/frontend/cnc-auto-quote.md`
- `backend/tests/cnc/quote/test_quote_runner.py`, `test_quote_repository.py`, and `test_quote_http.py`
- Original CNC login/browser test directories
- Frontend part-config quote API, auto-quote, and options suites; account API, login, and platform-options suites

The working tree already contains unrelated/uncommitted account, login, MCP, and agent changes. No task worker may revert them. Task-local findings and targeted diffs should distinguish the new work from that baseline.
