# Existing flow evidence — 2026-10-23

Repository inspection only. No live provider requests, product edits, browser run or tests have been performed for this task.

## UI and platform identity

- `frontend/web/src/views/module_cnc/cnc_part_config/index.vue:190`: option values are actual `cnc_platform.id` values. `site_type` therefore refers to the selected platform record despite outdated backend comments describing a 1/2 enumeration. Never hardcode 1=Xometry/2=JLC during quote dispatch. Resolve the platform row, then use the existing trusted entry-host provider resolver.
- `index.vue:440` defines the fixed operation column, and `index.vue:712` builds row actions. Preserve the existing CRUD actions and local uncommitted changes when adding the quote action and increasing available operation width.
- `frontend/web/src/api/module_cnc/cnc_part_config.ts`: only CRUD currently exists. There is no quote API to call yet.
- User confirmed: one eligible account auto-selects; multiple eligible accounts require a selection dialog. No permanent account binding.

## Login ownership and lifecycle

- `backend/app/modules/cnc/login/runtime.py:84`: start reuses an activity owned by the same actor; READY reuse triggers identity verification.
- `runtime.py:120`: commands enqueue work for the owner task, rather than operating on Playwright from the HTTP handler; callers currently wait up to 30 seconds.
- `runtime.py:150`: login verification also navigates to the configured quote entry. Do not call this entire method in the middle of a configured quote; navigation may discard its page. Add a separate read-only identity verification boundary for active quote steps.
- `runtime.py:167`: the owner task creates and retains the SDK context/page; command processing is bounded to 25 seconds. A quote must advance in bounded stages in this task, rather than placing a long quote workflow inside one HTTP command or moving the page to a new asyncio task.
- `backend/app/modules/cnc/login/repository.py:76`: persisted account leases have a 60-second lifetime. Renew and revalidate between bounded stages, including analysis polling. A separate heartbeat may renew storage only; it must never use the browser page from another task.
- `frontend/web/src/views/module_cnc/cnc_account/AccountLoginDialog.vue` and `useAccountLogin.ts`: existing UI provides private JPEGs, bounded input, serial polling, late-response protection and teardown. Reuse these mechanics; READY alone must not cause a second quote submission after each poll.
- `backend/app/plugin/module_cnc/cnc_account/controller.py`: login operations require account update permission; `PrivateAccountRoute` omits request/response bodies from audit logs. Quote UI must not bypass those privileges.

## Files and parameters

- `backend/app/plugin/module_cnc/cnc_part_config/model.py:18` and `:22`: configuration stores platform, material, quantity, surface finish and JSON extra parameters; there is no account column or parameter catalog validation.
- `backend/app/plugin/module_cnc/cnc_part/model.py:16`, `:19`, `:20`: file metadata contains size, third-party upload authorization and a stored path, but no persisted SHA-256. Establish a server-owned file snapshot and hash before a remote mutation; verify the exact uploaded bytes against it.
- `backend/app/modules/cnc/browser/files.py:23`: TrustedStep validates storage-root confinement, suffix, size, hash and STEP header/footer; official upload helpers use a verified buffer.
- `backend/app/modules/cnc/browser/contracts.py:153`, `:229`: durable mutation intent store and concrete provider adapters are application integration ports, not existing implementations.
- `backend/app/modules/cnc/browser/workflow.py:175`, `:210`: existing workflow and quote validator enforce identity, file/geometry, complete effective parameters, current quote freshness and Decimal money. A current timestamp alone does not prove a current quote.

## Provider readiness and historical boundaries

- Read `.trellis/spec/backend/cnc-account-login.md` and `browser-executor.md` before implementation. D-18 shipped login only; it does not authorize treating upload/quote as already implemented.
- Parent decisions D-17/D-18 and `.trellis/tasks/10-21-cnc-mvp-02-first-quote/prd.md`: Xometry first, JLC second, RapidDirect deferred. Original full-MVP workflow, Agent and integrated acceptance remain separate; this feature must not mark those tasks complete.
- `.trellis/tasks/10-21-cnc-pricing-mvp/research/platform-configs/README.md`: historical JSON files are draft/automation-disabled. Xometry parameter equivalence/fresh extraction and JLC exact currency/quote semantics still need provider evidence. JLC historical system estimate is REFERENCE_ESTIMATE; the no-order side effects of its final inquiry action require verification before enabling that action.
- Historical login checks reported reserved/mixed DNS rejection. Recheck through the existing guarded executor during implementation; do not weaken its policy, use a personal browser profile, invent selectors or silently enable draft JSON to get a green result.

## Deferred technical investigation

Implementation begins with controlled provider evidence gathering under the approved plan: exact upload controls, file limits, parse identity/geometry, parameter mappings/dependencies, no-order quote trigger and current result extraction. Research is part of implementation; each provider remains unavailable for automated mutations until its corresponding evidence gate passes. Failure to obtain live access is an incomplete integration, not successful feature acceptance.
