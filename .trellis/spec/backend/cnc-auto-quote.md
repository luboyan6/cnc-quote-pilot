# CNC configuration auto quote

## 1. Scope / trigger

Read when changing configuration-row quote APIs, quote persistence, provider activation or the login owner's quote hook. Implementation owners are `app/modules/cnc/quote/`, `app/plugin/module_cnc/cnc_quote/model.py`, the quote registration in `cnc_part_config/controller.py`, and the existing login runtime. This feature consumes [browser-executor.md](browser-executor.md) and [cnc-account-login.md](cnc-account-login.md); it does not establish full MVP/provider acceptance merely by exposing a button.

## 2. Signatures

Prefix `/cnc/cnc_part_config`:

| Method / suffix | Contract |
| --- | --- |
| GET `/{id}/quote/accounts` | Eligible `{id, alias, masked_username}[]` |
| POST `/{id}/quote/runs` | `StartQuote(account_id?: positive strict int, request_id: UUID)` -> QuoteRunView |
| GET `/{id}/quote/runs/{run_id}` | Actor-private progress/result |
| GET `.../{run_id}/frame` | Private JPEG/no-store |
| POST `.../{run_id}/input` | Existing strict LoginInput, human stage only |
| POST `.../{run_id}/resume` | Verify same activity then continue; no replacement parameters |
| DELETE `.../{run_id}` | Stop/settle; never delete mutation intent to retry |

`QuoteService.start/status/command` orchestrates references only. `QuoteActivity.check_inputs/login_state/advance/resume/finish` is called in the existing LoginManager owner task. `ActorAuthorizer.load(actor_id, for_run=True)` re-reads active user/roles/menus in an independent DB session. `DurableIntentStore` implements the shared IntentStore port.

Migration `c9e3a6b72f14` follows `0ce906be2d99`, adding `cnc_quote_run` and `cnc_quote_intent`. Run uniqueness is `(actor_id, config_id, request_id)` plus nullable unique `active_config_id`; intent uniqueness is `(run_id, generation, operation)`. Terminal persistence clears active_config_id. Migration SQL must be reviewed against the actual current revision; do not apply unrelated pending revisions automatically.

## 3. Contracts

- Configuration `site_type` is the actual platform row ID selected by the current Web page. Old 1=Xometry/2=JLC comments do not authorize hardcoded provider routing. Resolve the row then the trusted exact entry-host registry.
- Account selection: zero eligible accounts -> NO_AVAILABLE_ACCOUNT; one auto-selects; multiple require a choice. Account must match this platform and actor/object permissions. A duplicate active configuration returns its existing actor-private run, potentially with its previously chosen account.
- QuoteRunView includes run/config/account IDs, platform_name, masked_username, file_name, status/stage/reason/can_input, requested, viewport, expires_at and optional result. No credentials, remote references/URLs, storage paths or raw DOM.
- States are STARTING/AUTHENTICATING/RUNNING/WAITING_HUMAN/QUOTED/REFERENCE_ESTIMATE/PENDING_REVIEW/FAILED/CANCELLED. Result money is a Decimal string, scope unit/line, taxes/shipping unknown=null. Preserve LeadTime.text/type; never derive production days from an arrival date.
- QUOTED requires existing validate_quote plus committed result storage. ProvisionalQuote carries explicit current_verified/evidence_code and the same run/file/parameters/geometry; it enters the separate REFERENCE_ESTIMATE/PENDING_REVIEW branch, never ValidatedQuote. Missing price alone does not imply review.
- Source bytes are frozen and SHA-256 checked under the configured upload root; upload_authorized must be true. Upload, quote freezing and shared revalidation accept the same case-insensitive `.step`/`.stp`/historical `.setp` suffixes through `browser.files.STEP_SUFFIXES`, retaining framing/root/size/hash guards and stored filenames. The official SDK receives only the frozen bytes with its private generic `part.step` name. Optional finish stays omitted, not invented. Scalar JSON extras use explicit canonical values; unsupported/ambiguous mappings stop rather than silently choosing an alloy, temper or finish.
- Account and configuration ownership/enabled/revision, file identity, and current user/RBAC are rechecked before automatic operations. HTTP session permissions alone are insufficient for a long-running activity. Current active-role/menu collection reuses LoginService._collect_permissions. Existing AuthSchema does not carry a login-session identity, so do not claim per-session logout revocation is checked from it.
- Same owner retains Page; HTTP handlers never manipulate it. Quote activity excludes ordinary account-page input. Bounded phases renew the fenced account lease; slow upload parsing observes the claimed upload through read-only reconciliation, without re-upload. Human resume verifies identity without navigating away from an uploaded item.
- A run with no local owner may belong to another worker or a restart. Return an explicit unavailable/manual status. Only a safe expired-lease settlement may release its active configuration; do not cancel a live other-worker lease or leave expired runs impossible to stop forever.
- Register quote routes through a local child router in `register_quote_routes(parent)`. DynamicRouterRegistry scans every top-level APIRouter attribute; exporting an already included router can duplicate paths. With nested FastAPI routers, verify materialized OpenAPI/HTTP rather than only a flat app.routes loop.
- Keep site procedures independent in `.agents/skills/cnc-xometry-quote/` and `.agents/skills/cnc-jlc-quote/`. Xometry's material search and Save Configuration are separate from JLC's per-part 修改参数 and submission controls. A completed skill is operator guidance, not an `AdapterBinding` registration. DOM evidence from a public demo, a `vercel_part_config=test` historical route or an anonymous upload entry cannot satisfy normal managed-route acceptance. Re-observe the current site and preserve exact alloy/temper/product-form/finish semantics before setting parameters.
- The HTTP action boundary converts both `LoginError` and `BrowserStop` to a `CustomException` carrying only their fixed reason. File revalidation can raise `BrowserStop(file_invalid)` during start/status/resume; it must remain an actionable business failure, not an uncaught HTTP 500 or raw exception traceback. HTTP regressions cover those three entry points.

## 4. Validation & error matrix

| Condition | Required result |
| --- | --- |
| Missing current permission, actor disabled/deleted, revoked role/menu or superuser demotion | Stop before next automatic mutation; QUOTE_PERMISSION_REVOKED/QUOTE_ACTOR_UNAVAILABLE |
| Cross-platform/other-owner/disabled account | Reject, no browser action |
| Explicit upload_authorized=false | THIRD_PARTY_UPLOAD_NOT_AUTHORIZED; never silently enable it |
| Changed input/file or invalid STEP/path/hash/limit | Fixed stop before upload/next mutation |
| Active same config / replayed request | Return existing run, no duplicate upload |
| Slow model parsing / unknown upload receipt | Bounded read-only reconcile or human; preserve committed claim |
| Phase timeout / process restart / failed confirmation | No blind repeat; preserve uncertain record and accurate fixed reason |
| Quote store fails | No public QUOTED; retain recoverable durable activity/intent |
| Provider unverified / unknown mapping | Explicit unavailable/manual reason; never return fixture/demo price |
| Estimate / pending audit | Separate status; never final quote acceptance |

Private quote routes reuse metadata-only audit handling; malformed input and SQL failures must not leak parameters or private snapshots. Browser reason values are often lowercase; UI mappings must use actual enum strings.

## 5. Good / base / bad cases

- Good: current authorized actor, exact linked STEP, verified account reuse, durable one-time upload, exact provider parameter readback, same-run fresh quote and committed result.
- Base: isolated repository/owner/synthetic tests pass while provider authentication or exact quote is blocked. Report these separately and leave live acceptance incomplete.
- Bad: make factory unconditionally return None yet claim the feature works; promote historical draft JSON or public test-drive prices; re-upload after losing a response; approximate “铝合金” to an arbitrary alloy.

## 6. Tests required

`backend/tests/cnc/quote/` covers actual independent SQLite transactions, current user/role/menu revocation, file/root/hash/authorization checks, non-enum platform IDs, concurrent run/intent claims, stale-lease cancellation, HTTP permissions/privacy, owner lifecycle, exact quote/provisional validation, slow parse and failed persistence. `test_step_file_boundary.py` traverses actual upload validation/storage, isolated quote snapshot, shared revalidation and SDK buffer handling for `.step/.stp/.setp` (including uppercase), rejecting invalid content/metadata and preserving authorization/root/size/hash checks. `test_quote_migration.py` compares isolated upgraded table columns/unique constraints against models and checks the revision parent and isolated downgrade.

Run original CNC login/browser regressions for runtime/provider policy changes, narrow Ruff/basedpyright, and OpenAPI or HTTP registration checks. Live provider results must separately identify real login/state reuse, exact linked-file upload, parameter save/readback and current result nature. Synthetic/draft evidence cannot satisfy those steps.

## 7. Wrong vs correct

```python
# Wrong: cached start-time auth may still grant superuser after demotion.
await provider.upload(session, payload)

# Correct: current actor/object/lease and committed intent guard the mutation.
await activity.check_inputs()
await repository.renew(snapshot.account, owner, token)
receipt = await workflow._mutation(key, session, adapter, action, sha256, params)
```

Do not call the navigating login `_verify` midway through a quote; use the provider's read-only identity check in the same owner instead.
