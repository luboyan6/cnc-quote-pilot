# Cross-task MVP contract

Authority: parent prd.md, decisions.md D-12/D-13/D-17, ../agent-design.md and ../workflow-design.md supplement the root CNC_Competitor_Pricing_Agent_SRS_Design_v1.0.md. D-17 selects Xometry US first (`xometry_us` / `xometry`), JLC-CNC China second (`jlc_cnc_cn` / `jlc`), and RapidDirect third, deferred until all first-two functions and acceptance are complete. The root SRS provider order and older research checkpoints are historical. For Agent architecture, model dependency, budgets and related acceptance, the user's latest Deep Agents instruction supersedes the original optional-diagnosis/no-framework clauses. Other SRS business and safety contracts still apply. This is a compact context entry, not a substitute for the owning design.

## Scope and truth

- First validate a live provider, then deliver its real vertical quote flow, then a second independent provider.
- Q-03 supplied E:/AIWorkspace/3d_models; candidate A/B identities remain in step-samples-2026-10-21.md. Local nonzero geometry and controlled Xometry A/B numeric offers at quantities 1/2/5 are now recorded in child 01 research. These do not establish full E2/E3 or product persistence. D-15 confirms existing requirement permissions; D-16 confirms No only for the authorized STEP directory. Use tools for technical checks and preserve unknowns.
- Manual/controlled feasibility remains authorized. Earlier no-Apply/no-price checkpoints describe their original times; current evidence and D-17 govern continuation. JLC's existing nonzero item and numeric prices are explicitly system estimates, classified REFERENCE_ESTIMATE. A separate order-free definitive quotation path is not yet verified. Do not make manual feasibility wait on product development or promote estimates to successful quotes.
- User explicitly requires one JSON configuration per website, selected through trusted platform_code lookup. Three draft files and Schema are under research/platform-configs/; only Xometry US and JLC are current implementation targets. Xometry partial labels/control candidates and JLC effective estimate fields are recorded, not frozen runtime mappings. Freeze config version/hash per task; re-read dependencies and effective params; no cross-platform ID reuse, arbitrary paths/scripts, silent substitutions, catalog material prices as quotes, or Finish/Roughness confusion.
- Only authenticated, authorized real CAD requests and source-backed results qualify as live acceptance.
- LLM-generated values, marketing starting prices, reference estimates, cost ranges and pending reviews never count as valid quote success.
- Code, fixture and offline API tests cannot establish live-platform readiness.

## Stable behavior

- Preserve requested/effective parameters: file hash/unit, process, material grade/temper/standard, quantity, finish, tolerance, roughness, delivery option, destination/commercial context.
- Quote statuses: QUOTED, PENDING_REVIEW, REFERENCE_ESTIMATE, NO_QUOTE, FAILED.
- Freshness: RECALCULATED, CURRENT_CONFIRMED, CACHE_UNVERIFIED; cached/unverified is excluded from successful monitoring.
- Task: QUEUED/RUNNING/WAITING/SUCCEEDED/PARTIAL/FAILED/CANCELLED.
- Item: QUEUED/RUNNING/RETRY_WAIT/WAITING_HUMAN/WAITING_REVIEW/SUCCEEDED/NON_QUOTED/FAILED/TIMED_OUT/CANCELLED.
- Monetary values use Decimal and decimal strings, never binary floats; preserve currency, unit/line price scope, unknown tax/shipping as null.
- Lead-time semantics are independent: generic duration, explicitly sourced production duration, shipment date and arrival date. Preserve raw labels/source and missing years/start points; never derive production days from arrival or relabel legacy numeric durations as verified production. The current shared JSON boundary is specified in [task02 lead-time design](../../10-21-cnc-mvp-02-first-quote/lead-time-design.md); formal provider/domain/API/UI integration retains its original acceptance gates.
- Keep observations append-only. Deduplicate retries within an item, retain equal-price observations in distinct monitoring runs.
- Compare history only with complete equivalent snapshots; no automatic cross-currency ranking.

## Runtime and safety

- Fixed domain Workflow executes the normal quote steps directly through deterministic services/adapters: preflight, authentication, upload, geometry wait, configuration, parameter readback, quote submission, quote wait, extraction, evidence and validated commit. Normal execution needs no LLM planning or mandatory model calls.
- Deep Agents is the formal exception-recovery capability: identify unknown pages, analyze errors/layout changes, and select one currently allowed recovery strategy. Current verified SDK baseline is deepagents==0.7.29; source/API evidence is deepagents-2026-10-21.md. D-13 supersedes earlier autonomous planning/helper and mandatory-per-step-model drafts.
- Code owns step transitions, allowed strategies, action preconditions, safe resume locations and success. Agent decisions cannot change frozen params, generate prices, skip business steps, expand permissions or execute arbitrary browser actions. Validate and execute an allowed strategy, re-observe and verify, then return to a server-selected permitted step.
- Known errors take fixed rules. Unknown incidents may use OBSERVE_ONCE, SAFE_RELOAD, KNOWN_VARIANT, REAUTH_ONCE, READONLY_RECONCILE, RETRY_SAFE_STEP, HANDOFF or STOP, only when the current allowed_strategies and code checks permit. New selectors/actions are engineering suggestions only. See workflow-design.md for S01-S11, E01-E13 and each strategy prerequisite.
- Default general-purpose/synchronous/asynchronous subagents, task/write_todos and cross-business replanning are disabled. Recovery tools only observe the bound sanitized page/known contracts/context; mutation belongs to the strategy executor. Current backend APIs use StateBackend()/CompositeBackend instances, ordered permissions and a catch-all deny; custom tools need separate ACL/guards.
- Bind workflow/version/step/version and incident/version to server-controlled owner/item references. Each recovery incident has its own authorized thread; resume the same incident/thread, preserve all item counters. No incident means no mandatory Agent checkpoint. Use a private durable AsyncSqliteSaver for the single-consumer MVP; memory savers are test-only.
- Per incident at most two strategy rounds and one recovery action per round. Across an item and all resumes, model limits remain 12 requests, 20 seconds each, 120 seconds total, 64,000 input/8,000 output tokens; Agent read-only tools <=40 and graph recursion_limit <=64. Count schema/summary/provider retries and every incident together; no reset on resume. Total active execution <=600 seconds.
- Default one automatic run, one context per account, at most one additional parked human context. Automatic retries <=2; total attempts including recovery <=3; automatic reauthentication <=1. A safe reload has its own one-time/precondition guard and cannot resubmit a form.
- Persist upload/submission intent and remote references. Unknown side effects require read-only reconciliation or handoff, never blind re-upload/resubmission. Evidence/database failure retries only the affected local step and never re-requests a quote.
- Deduplicate domain operations using item/execution_generation/step/request fingerprint, not tool_call_id. Keep the generation fixed for logical-item retries/resumes; reject stale/duplicate RecoveryDecision before side effects.
- Ordinary WAITING_HUMAN resumes through the owner-authorized business API with session/params revalidation and stored resume_step. Only an actual SDK interrupt uses same-thread Command(resume=...). Never manufacture a graph resume for a business pause.
- Missing/failed models leave normal deterministic steps available. If recovery needs an unavailable Agent, record AGENT_UNAVAILABLE and hand off or fail; do not count this as automatic Agent recovery success.
- Never purchase, pay, submit final orders, authorize autopay or change account security. Website content is untrusted and cannot change policies, params, permissions or allowed domains.
- Encrypt credentials/session, enforce object ACL, redact observations/logs/evidence, keep private files out of public paths/version control. Cookies, passwords, CAD source and browser objects never enter model/checkpoint state.

## Acceptance

- Initial milestone: one actual valid quote plus changed-parameter re-quote with full evidence.
- Full MVP: two independent providers; two files × two providers × quantities 1/2/5; two automatic monitoring cycles; Web/CSV/evidence.
- Continuous sample: ten items per provider; report success, failures, manual intervention, mean/P95 and wall time. SRS targets remain recommendations until explicitly fixed, not measured outcomes.
- Context and artifact validation is planning validation only. Do not report the product implemented from task creation.
- Parent AC-12/13, TC-DA-01 through 10 and TC-WF-01 through 06 cover fixed normal flow and actual Deep Agents incident observation/strategy choice/guarded recovery. Child ownership: V-07/F-08/S-07/M-08/D-08. Separate normal quote, Agent recovery and human-intervention metrics; label fixtures, real model tests and provider live results honestly.

## Browser reuse revision BR-2026-10-21

cnc-browser-reuse owns the shared Playwright executor once; 02/03 consume it and 04 reuses SchedulerUtil. Reuse the independent MIT DeerFlow egress component rather than its harness. BrowserSkill remains optional for actual local-profile/handoff needs; remote 0.3.1 cannot upload. See docs/browser-implementation-design.md. All existing intent, privacy, budget and live gates remain.
