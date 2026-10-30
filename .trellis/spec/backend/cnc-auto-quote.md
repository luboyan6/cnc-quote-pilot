# CNC configuration auto quote

## 1. Scope / trigger

Read when changing configuration-row quote APIs, quote persistence, provider activation or the login owner's quote hook. Implementation owners are `app/modules/cnc/quote/`, `app/modules/cnc/cnc_quote/model.py`, the quote registration in `cnc_part_config/controller.py`, and the existing login runtime. This feature consumes [browser-executor.md](browser-executor.md) and [cnc-account-login.md](cnc-account-login.md); it does not establish full MVP/provider acceptance merely by exposing a button.

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
| POST `.../{run_id}/declaration` | Strict `{declaration_id: lowercase SHA-256, choice: not_controlled \| controlled}` -> QuoteRunView |
| DELETE `.../{run_id}` | Stop/settle; never delete mutation intent to retry |

`QuoteService.start/status/command` orchestrates references only. `QuoteActivity.check_inputs/login_state/advance/resume/declare/finish` is called in the existing LoginManager owner task. `ActorAuthorizer.load(actor_id, for_run=True)` re-reads active user/roles/menus in an independent DB session. `DurableIntentStore` implements the shared IntentStore port.

`xometry.py::XometryQuoteAdapter(snapshot, run_id, binding)` implements `authenticate/upload/configure/read_effective/submit/extract_quote/reconcile`; its concrete methods include current-page inspection, exact-file parsing, declaration read/continue and saved-revision validation. `XometryDOMBinding` is source-reviewed internal input, not platform/request JSON. Its `part_config_variant: Literal["legacy", "v2"] = "legacy"` names the reviewed editor variant; an unknown variant fails binding construction. `providers.py` only registers its private reviewed binding; absent current managed-route evidence raises `XOMETRY_BINDING_UNVERIFIED`. Implemented methods and synthetic tests do not establish production activation.

Migration `c9e3a6b72f14` follows `0ce906be2d99`, adding `cnc_quote_run` and `cnc_quote_intent`. Run uniqueness is `(actor_id, config_id, request_id)` plus nullable unique `active_config_id`; intent uniqueness is `(run_id, generation, operation)`. Terminal persistence clears active_config_id. Migration SQL must be reviewed against the actual current revision; do not apply unrelated pending revisions automatically.

## 3. Contracts

- Configuration `site_type` is the actual platform row ID selected by the current Web page. Old 1=Xometry/2=JLC comments do not authorize hardcoded provider routing. Resolve the row then the trusted exact entry-host registry.
- Account selection: zero eligible accounts -> NO_AVAILABLE_ACCOUNT; one auto-selects; multiple require a choice. Account must match this platform and actor/object permissions. A duplicate active configuration returns its existing actor-private run, potentially with its previously chosen account.
- QuoteRunView includes run/config/account IDs, platform_name, masked_username, file_name, status/stage/reason/can_input, requested, viewport, expires_at and optional result. Optional `export_declaration` is null or `{declaration_id, statement, options: [{value, label}]}` with the two explicit choices; the text is the current full plain-text declaration, not arbitrary DOM/HTML. No credentials, remote references/URLs or storage paths.
- States are STARTING/AUTHENTICATING/RUNNING/WAITING_HUMAN/QUOTED/REFERENCE_ESTIMATE/PENDING_REVIEW/FAILED/CANCELLED. Result money is a Decimal string, scope unit/line, taxes/shipping unknown=null. Preserve LeadTime.text/type; never derive production days from an arrival date.
- QUOTED requires existing validate_quote plus committed result storage. ProvisionalQuote carries explicit current_verified/evidence_code and the same run/file/parameters/geometry; it enters the separate REFERENCE_ESTIMATE/PENDING_REVIEW branch, never ValidatedQuote. Missing price alone does not imply review.
- JLC shortcut execution, including single and batch entry points, stops before opening the browser or uploading with `JLC_EFFECTIVE_PARAMETERS_UNVERIFIED`. Existing site observations describe the editor but do not prove same-part, post-save readback of material, quantity, finish and tolerance. Do not activate this path or label requested/default values as effective until a reviewed binding verifies the saved values and current estimate together.
- Source bytes are frozen and SHA-256 checked under the configured upload root. On 2026-10-25 the user explicitly clarified that `cnc_part.upload_authorized` is a test column unrelated to Xometry: it neither blocks nor invalidates Xometry runs, and quote execution must not silently flip it. Xometry authorization still comes from the current actor's explicit quote action, current RBAC/account/file access and frozen run scope. `source_file(..., require_upload_authorization=True)` preserves the existing direct/other-provider gate; only resolved Xometry snapshots opt out of that test-column check and omit it from the configuration fingerprint. Upload, quote freezing and shared revalidation accept the same case-insensitive `.step`/`.stp`/historical `.setp` suffixes through `browser.files.STEP_SUFFIXES`, retaining framing/root/size/hash guards and stored filenames. The official SDK receives only the frozen bytes with its private generic `part.step` name. Optional finish stays omitted, not invented. Scalar JSON extras use explicit canonical values; unsupported/ambiguous mappings stop rather than silently choosing an alloy, temper or finish.
- Account and configuration ownership/enabled/revision, file identity, and current user/RBAC are rechecked before automatic operations. HTTP session permissions alone are insufficient for a long-running activity. Current active-role/menu collection reuses LoginService._collect_permissions. Existing AuthSchema does not carry a login-session identity, so do not claim per-session logout revocation is checked from it.
- Same owner retains Page; HTTP handlers never manipulate it. Quote activity excludes ordinary account-page input. Bounded phases renew the fenced account lease; slow upload parsing observes the claimed upload through read-only reconciliation, without re-upload. Human resume verifies identity without navigating away from an uploaded item.
- Export declaration is an explicit fixed owner command. Re-observe its complete statement/options, verify identity, and commit the actor/run/frozen file SHA-256/declaration version/choice/decision-time record before any selection/Continue. It has its own durable `declaration` operation and `DeclarationReceipt`; it is never inferred from coordinates, filenames, cookies or defaults. Generic frame/input/resume cannot bypass a declaration (`can_input=false`), while the typed declaration command is allowed in its WAITING_HUMAN stage. Stale declaration or unconfirmed Continue stops/reconciles without another click.
- `QuoteRepository.assert_upload_available` also fences new runs against every prior claimed/uncertain upload, configuration save, submission or declaration for the same account/platform/owner, including cancelled runs. The same frozen file hash remains blocked; a prior missing/invalid hash conservatively fences the account. A known different frozen hash may proceed as a separately authorized file without settling or deleting the old claim. A filename match/difference or a new request_id/run cannot authorize replay of an unresolved file.
- Xometry uploads an exact frozen SDK payload only into an empty reviewed primary CAD target, then binds the uniquely new remote part/file, byte length and positive geometry. Parameter titles are exact and dependent controls re-observed. Save Configuration must yield a new reviewed remote revision with complete saved readback. Because that Save already recalculates, `submit` adopts its correlated receipt read-only rather than clicking Save again. A current timestamp without that correlation is insufficient.
- A run with no local owner may belong to another worker or a restart. Return an explicit unavailable/manual status. Only a safe expired-lease settlement may release its active configuration; do not cancel a live other-worker lease or leave expired runs impossible to stop forever.
- Register quote routes through a local child router in `register_quote_routes(parent)`. DynamicRouterRegistry scans every top-level APIRouter attribute; exporting an already included router can duplicate paths. With nested FastAPI routers, verify materialized OpenAPI/HTTP rather than only a flat app.routes loop.
- Keep site procedures independent in `.agents/skills/cnc-xometry-quote/` and `.agents/skills/cnc-jlc-quote/`. Xometry's material search and Save Configuration are separate from JLC's per-part 修改参数 and submission controls. A completed skill is operator guidance, not an `AdapterBinding` registration. DOM evidence from a public demo, an unrelated historical quote or an anonymous upload entry cannot satisfy same-file managed-route acceptance. Current official source identifies `vercel_part_config` as part of the deployed `bx_part_config_v2` editor experiment, so the key alone does not classify a page as the public demo. Default legacy bindings reject the key. An explicitly reviewed V2 binding permits only a single exact `vercel_part_config=test`; blank, duplicate and other values reject. A query-free reviewed home uploader remains valid before navigation to the V2 editor. Public testdrive, host, identity, file, parameter and current-result gates still apply. Source evidence: [current deployed source](../../tasks/10-25-cnc-xometry-quote-methods/research/site-auth-source-2026-10-25.md). Re-observe the current site and preserve exact alloy/temper/product-form/finish semantics before setting parameters.
- Managed-route activation evidence must distinguish explicit provider identity from usable quoting controls. On 2026-10-25 the same owned Xometry Page returned a matching `/v2/users/me` identity while its native uploader displayed `Sign in to start a new quote.` with `Start Instant Quote` disabled. A successful identity fetch alone therefore does not establish live upload readiness. Record both observations; resolve the visible login state through the normal owned UI before treating that route as accepted. An existing configuration link that carries `vercel_part_config` remains evidence for that actual variant, even when obtained from the current dashboard.
- The HTTP action boundary converts both `LoginError` and `BrowserStop` to a `CustomException` carrying only their fixed reason. File revalidation can raise `BrowserStop(file_invalid)` during start/status/resume; it must remain an actionable business failure, not an uncaught HTTP 500 or raw exception traceback. HTTP regressions cover those three entry points.

## 4. Validation & error matrix

| Condition | Required result |
| --- | --- |
| Missing current permission, actor disabled/deleted, revoked role/menu or superuser demotion | Stop before next automatic mutation; QUOTE_PERMISSION_REVOKED/QUOTE_ACTOR_UNAVAILABLE |
| Cross-platform/other-owner/disabled account | Reject, no browser action |
| Xometry test column upload_authorized=false or changes | No block/revision invalidation from this column; current actor/file/byte checks still apply, no silent flag write |
| Other provider/direct helper requires upload_authorized and it is false | THIRD_PARTY_UPLOAD_NOT_AUTHORIZED; never silently enable it |
| Changed input/file or invalid STEP/path/hash/limit | Fixed stop before upload/next mutation |
| Active same config / replayed request | Return existing run, no duplicate upload |
| Prior cancelled run has claimed/uncertain upload on same account and same/unknown file hash | QUOTE_PRIOR_UPLOAD_UNCONFIRMED_NO_RETRY before a new upload |
| Current declaration requires choice / stale version / unconfirmed Continue | Explicit typed decision / QUOTE_EXPORT_DECLARATION_STALE / no repeated mutation |
| Slow model parsing / unknown upload receipt | Bounded read-only reconcile or human; preserve committed claim |
| Phase timeout / process restart / failed confirmation | No blind repeat; preserve uncertain record and accurate fixed reason |
| Quote store fails | No public QUOTED; retain recoverable durable activity/intent |
| Provider unverified / unknown mapping | Explicit unavailable/manual reason; never return fixture/demo price |
| JLC saved effective-parameter readback unverified | `JLC_EFFECTIVE_PARAMETERS_UNVERIFIED` before browser upload; no fabricated estimate |
| Legacy binding with editor experiment query; V2 binding with blank/unknown/duplicate experiment values | `XOMETRY_PAGE_UNSUPPORTED`; only explicit V2 plus one exact `test` value may proceed to the remaining evidence checks |
| Provider identity matches but native uploader requests sign-in or has disabled quote controls | Identity evidence only; live route/adapter activation remains unverified |
| Estimate / pending audit | Separate status; never final quote acceptance |

Private quote routes reuse metadata-only audit handling; malformed input and SQL failures must not leak parameters or private snapshots. Browser reason values are often lowercase; UI mappings must use actual enum strings.

## 5. Good / base / bad cases

- Good: current authorized actor, exact linked STEP, verified account reuse, durable one-time upload, exact provider parameter readback, same-run fresh quote and committed result.
- Base: isolated repository/owner/synthetic tests pass while provider authentication or exact quote is blocked. Report these separately and leave live acceptance incomplete.
- Bad: make factory unconditionally return None yet claim the feature works; promote historical draft JSON or public test-drive prices; re-upload after losing a response; approximate “铝合金” to an arbitrary alloy.

## 6. Tests required

`backend/tests/cnc/quote/` covers actual independent SQLite transactions, current user/role/menu revocation, file/root/hash/authorization checks, non-enum platform IDs, concurrent run/intent claims, stale-lease cancellation, HTTP permissions/privacy, owner lifecycle, exact quote/provisional validation, slow parse and failed persistence. Extend it for exact-file declaration persistence, stale/duplicate decisions, same-owner Continue, legacy views without the optional declaration field, and new-run fencing after a cancelled unresolved upload (same/missing/invalid hash blocked, different known hash allowed while preserving the claim). Assert the test upload flag neither blocks nor invalidates Xometry, while the direct-helper/other-provider gate and genuine file-change rejection remain intact. The concrete Xometry methods need isolated DOM/receipt cases for exact bytes, ambiguous materials, unsupported extras, saved mismatch, unconfirmed mutation, explicit currency, correlated revision and old result rejection. `test_step_file_boundary.py` traverses actual upload validation/storage, isolated quote snapshot, shared revalidation and SDK buffer handling for `.step/.stp/.setp` (including uppercase), rejecting invalid content/metadata and preserving authorization/root/size/hash checks. `test_quote_migration.py` compares isolated upgraded table columns/unique constraints against models and checks the revision parent and isolated downgrade.

On Windows, cancelling an aiosqlite read can leave an unconsumed SQLite cursor referencing a closed connection; the database file remains open even after the pool has no checked-out connections. The isolated quote fixture tracks and explicitly closes its own cursors before connection shutdown, and tests deletion with an unconsumed cursor. Do not suppress deletion errors or assume `pool.checkedout() == 0` alone proves that all statements are finalized. This fixture adaptation is not a production driver change.

Run original CNC login/browser regressions for runtime/provider policy changes, narrow Ruff/basedpyright, and OpenAPI or HTTP registration checks. `test_xometry_adapter.py` also tests legacy/V2 acceptance, a query-free uploader before V2 navigation, rejected empty/duplicate/unknown query values, and preserved public-testdrive/untrusted-host gates on local Chromium. Live provider results must separately identify real login/state reuse, exact linked-file upload, parameter save/readback and current result nature. Synthetic/draft evidence cannot satisfy those steps.

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
