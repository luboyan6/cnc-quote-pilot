# DeerFlow Source Integration with FastAPI

## 1. Scope / trigger

The user changed the integration design on 2026-10-29: adapt selected DeerFlow
Agent source into this FastAPI project, following its architecture. This replaces
the Client-only design and its prohibition on source adaptation. The local
source-agent and chat components now have offline coverage, but the integration
gate remains closed until the task's history, cancellation and deployment
acceptance criteria are satisfied.

Agno remains the default chat implementation. The old custom runtime was removed;
do not restore it and label it a source integration. The authoritative component
map and user decision are in
`.trellis/tasks/10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md`.

## 2. Signatures and ownership

- Existing `ai/chat/controller.py → ChatService → AgentService` is the target
  in-process call chain. AgentService, graph assembly, selected state/middleware,
  model construction and checkpoint resources belong in `app/modules/ai/agent/`.
- `ai/skills/` exposes authenticated catalog/detail routes using the same
  SkillCatalog as execution. Register through
  `app/api/v1/routers.py:DOMAIN_CONTROLLERS`.
- Follow Controller / Service / CRUD or Repository / Schema / Model boundaries.
  Use current AuthSchema, MappedBase, async_db_session, settings, exceptions and
  logger. Do not introduce a second app, configuration singleton, authz stack,
  ORM, scheduler or Gateway RunManager.
- Tools in `ai/agent/tools/` call existing CNC Services directly, without
  HTTP/MCP loopback or duplicating browser/credential/CRUD operations.
- The graph builder accepts explicit model, tool, skill, state and checkpointer
  dependencies and returns a framework-compiled graph. Adapt selected upstream
  assembly and middleware semantics; use LangChain/LangGraph execution rather
  than a handwritten model/tool loop.
- Existing domain entry points include QuoteService, BatchService,
  MonitorService and CncQuoteResultService under `app/modules/cnc/`. Old
  `app/plugin/module_cnc/` research paths are not the current built-in layout.

## 3. Contracts

### Source and dependency provenance

Record the selected immutable upstream commit, per-file hashes, target files,
preserved/changed/omitted behavior and boundary tests. The planning reference is
`f6fe1e9c9e029bf22b8e2eb8e2e23e1258cf0814`. Preserve the MIT license and
Bytedance/DeerFlow copyright notices for derived portions.
Do not copy the whole deerflow tree, merely rename imports, import an upstream
factory at runtime or add a sibling-workspace dependency. Resolve only selected
LangChain/LangGraph/model/saver/parser dependencies, not the whole harness extra
closure. Keep pyproject, lock and production installation instructions consistent.

### Identity, models and skills

Trust the authenticated numeric user and authorized application session.
Recheck current domain permissions for every tool. Client/model/skill text cannot
override actor, permissions, engine or checkpoint namespace.
Read private model settings through the existing Redis/decryption path and build
a separate async model per turn. Preserve model_id/base_url/api_key/temperature
and existing default semantics. Secrets never enter graph state, RunnableConfig,
events or visible history; do not rotate process globals across users.
Use one read-only runtime skill catalog under
`ai/agent/resources/skills/`, with adapted upstream parsing/activation behavior,
allowed-tool constraints and bounded content/reference reads. Do not scan
development-assistant skills or expose general filesystem/browser/Shell tools.

### Execution, persistence and transport

Proposed `AI_CHAT_ENGINE=agno|deerflow_source` defaults to agno and belongs in
the existing settings class. Missing dependencies, unsupported databases or
topologies fail explicitly when the new engine is selected; no silent fallback.
Use compiled-graph native async streaming and async model/tool paths. Lifespan
owns service/saver resources and single-turn tasks. Stop, disconnect, timeout and
shutdown cancel and await cleanup. A stopped event is not evidence of cleanup.
Full LangGraph checkpoints are the inference-state source; project session
metadata and idempotent visible Human/Assistant projections serve ownership,
history and rollback. They are not a parallel inference engine.
Verify PostgreSQL persistence first. SQLite fixtures do not prove deployment
concurrency. Preserve legacy Agno database support; do not silently switch MySQL
deployments to a different database to enable the new executor.

The planned structured event envelope is
`{session_id, turn_id, seq, type, payload}`; the shared contract owns the type
union and one sequencer/terminal producer. Legacy unversioned WS keeps text and
[DONE]/[STOPPED]; protocol_version=2 opts into typed events.
Business quote_run_id/batch_id/schedule_id/evidence_id remain distinct; keep
the existing domain schedule_id naming for monitor plans.
Stopping chat stops generation/observation. Domain tasks already admitted in
their own transactions continue until an explicit authorized business cancel.

Application mappings follow the actual Alembic head. Standard checkpoint tables
have explicit deployment/setup ownership and reflection protection. Preserve
revision a7d30f26b8e1 and its descendants and all unresolved domain intentions.

## 4. Validation and error matrix

| Condition | Required result |
| --- | --- |
| Forged actor/session or revoked domain permission | Reject before tool side effects |
| Unknown, unpublished or unauthorized skill/tool | Reject; catalog must not advertise executable capability |
| Missing selected model or unsupported configuration | Safe explicit error; never substitute another personal model |
| Stop before first token or during slow streaming | Cancel and await local graph/model stream cleanup; unique terminal |
| Stop races with domain admission | Inspect stable domain request result; do not resubmit or claim business cancellation |
| Duplicate/new tool call after unknown write receipt | Existing Run/Intent barrier and read-only reconciliation |
| Legacy Agno history or stale callback | Preserve the old rows without importing them; do not apply state from a superseded turn |
| Missing async saver/dependency | Refuse new engine enablement; preserve existing data |
| Unknown quote/price/evidence scope | Preserve truthful domain status; do not infer a successful quote |

## 5. Good / base / bad cases

- Good: a selected runtime skill activates its adapted middleware, calls an
  authorized local CNC Service, and produces safe typed events and a durable
  checkpoint tied to the correct owner/model.
- Base: agno is selected and existing REST/WS/model/history remain usable without
  importing optional new dependencies.
- Bad: a renamed copy of the full upstream package reads global AppConfig,
  exposes bash/read_file, or wraps a synchronous Client in to_thread and emits
  STOPPED while its worker still runs.

## 6. Tests required

Tests under `tests/ai/agent/` must exercise the actual adapted assembly,
skill parsing/activation/context, middleware behavior, model isolation,
permissions and async checkpoint integration. Do not merely mock an imagined
Client API or reproduce upstream internals.
Assert stop before first token, slow consumer, tool wait, disconnect, shutdown,
exception cleanup, elapsed one-second controlled stop target, closed local HTTP
stream and one terminal event. Local cancellation is not a promise about provider
billing.
Chat tests cover preservation of legacy rows, new-session CRUD/deletion barriers/rollback,
cross-user access and v1/v2 transport. UI tests cover generation fences, safe tool
cards, upload drafts and authenticated evidence blobs.
Use existing domain tests/contracts for Quote Run/Intent, batches, recovery,
schedules, metrics and private evidence; do not build duplicate foundations.
Keep source/static, offline integration, real-model and real-platform evidence
separate; an offline pass does not enable the gated source engine.

## 7. Wrong vs correct

Wrong:
```python
# Whole-package/client coupling and cancellation that leaves inference running.
client = DeerFlowClient(config_path=user_config_file)
async for event in wrap_in_thread(client.stream(message)):
    ...
```

Correct target shape (illustrative, not an existing API):
```python
# Project dependencies are explicit; selected upstream semantics live in
# adapted project modules. The framework owns graph execution.
graph = build_graph(model=model, tools=authorized_tools,
                    skills=skill_catalog, checkpointer=checkpointer)
async for event in graph.astream(input_state, config=trusted_config):
    ...
```

The surrounding AgentService must own cancellation and await async cleanup;
the snippet alone does not satisfy the cancellation or source-provenance gates.

## Scenario: source-chat drawing references and read-only reporting

### 1. Scope / trigger

This applies when changing source-chat STEP attachments or the Agent's existing
quote, batch and monitoring read tools. It does not authorize a platform upload,
quote submission or the release of the gated source engine.

### 2. Signatures

- `POST /cnc/drawing-upload/step`: multipart `request_id: UUID` and `file`;
  returns `{request_id, state, part_id, sha256, size_bytes}` without a path.
- `GET /cnc/cnc_quote_result/screenshot/{id}?private_only=true` reads only an
  available private evidence ID after the existing result authorization check.
- Migration `a816e3b61030` follows `9c4f72e61029` and adds the nullable JSON
  `evidence_result_ids` projection to `ai_source_chat_message`. Downgrade is
  refused while any row retains references.
- Source WebSocket protocol 2 accepts `drawing_uploads: UUID[]`, at most eight
  unique IDs, with a message or at least one drawing. The UI enables this
  attachment contract only for protocol 2; the source protocol-1 path rejects it.
- Read-only runtime tools: `cnc_quote_result_detail(result_id)`,
  `cnc_quote_statistics(part_id?)`, `cnc_quote_history(part_id, limit<=50)`,
  `cnc_batch_status(batch_id)`, `cnc_batch_items(batch_id, offset, limit<=50)`,
  and `cnc_monitor_status(schedule_id, limit<=20)`.

### 3. Contracts

The browser keeps one stable upload UUID per selected file across retries. It
does not clear the draft until a matching `turn.started` event. A stopped or
superseded upload may finish locally, but its late result cannot start a turn.
Before starting the graph, source chat rechecks the current numeric actor,
`module_cnc:cnc_part:detail`, upload ownership, READY state, size and SHA-256
against private storage. The generated human message contains only verified
part IDs, sizes and hashes; attaching does not grant third-party transfer.

Reporting tools use the current authenticated actor and reload domain
permissions on every invocation. Result detail additionally requires query and
detail permissions; statistics/history require result query permission; batch
and monitoring status require their respective detail permission. Even a
superuser's Agent tools are scoped to that actor's own records. Return safe
business fields and evidence IDs, never private screenshot paths or frozen
monitor target snapshots. Result statistics and comparisons use the existing
domain service; platform statistics are capped at 30 and report truncation.
When an authorized result tool verifies an available private evidence file,
the stream can emit `evidence.available` with only its numeric `result_id`.
The Vue viewer uses `private_only=true`, aborts stale requests and revokes Blob
URLs on close, session change and teardown. Checkpoint repair associates each
validated tool reference with the next visible assistant message and stores
only numeric result IDs in the idempotent projection. A restored card performs
the same current authorization check when opened; it does not store image data.

### 4. Validation and error matrix

| Condition | Behavior |
| --- | --- |
| Duplicate, malformed or over-limit drawing IDs | protocol-2 `request.error: INVALID_REQUEST`; no admitted turn |
| Missing, foreign, pending or modified upload | `turn.failed: CHAT_DRAWING_UNAVAILABLE` before `turn.started` |
| Revoked drawing or domain permission | deny before the graph/tool accesses the record |
| Foreign batch, schedule or result, including superuser | domain read is denied |
| Private evidence is missing, unpublished or replaced by a legacy path | private-only screenshot returns 404; no public-path fallback |
| Unknown comparison terms | return original observation with null comparison/difference |

### 5. Good / base / bad cases

- Good: retry a failed upload with the same UUID, verify the stored bytes and
  attach its owned part ID once; preserve draft until the turn is accepted.
- Base: a message without attachments uses the existing chat flow.
- Bad: trust a client-provided part ID or screenshot path, treat an estimate as
  a formal quote, or aggregate another actor's records in Agent reporting.

### 6. Tests required

Use isolated storage and database to test upload retry, byte tampering, owner
and role revocation, and the actual source graph; test protocol-2 rejection
before `turn.started`, stable retry IDs, stop/switch while uploading and draft
preservation. Exercise reporting against domain rows including another actor,
superuser, formal/estimate outcomes, incomparable observations and missed
rounds. Verify private-only image authorization, missing-file fallback denial,
stale-request cancellation and Blob revocation. Offline checks do not prove
real provider, evidence capture/redaction or migration acceptance.

### 7. Wrong vs correct

```python
# Wrong: model/client values decide which local file or actor is read.
message = f"Use file {client_path} for user {client_actor}"

# Correct: server-owned status resolution checks numeric actor and file hash.
reference = await DrawingUploadService(current_auth, sessions).status(request_id)
```

## Scenario: preserving source history during an Agno rollback

### 1. Scope / trigger

Use when the legacy engine is selected after source-engine sessions have been
created. The user chose on 2026-10-30 to keep old Agno rows without importing
them into the source engine.

### 2. Signatures

The existing `/ai/chat/list`, `/detail/{session_id}`, `/update/{session_id}`
and `/delete` endpoints expose owned source projections in Agno mode using
`source:<source-session-id>` and `read_only: true`. Normal Agno IDs remain
unchanged. Creation in Agno mode still creates an Agno session.

### 3. Contracts

`RollbackSessionService` combines independently owner-scoped Agno sessions and
numeric-owner source projections, then sorts and paginates the combined view.
It handles equal-timestamp page boundaries before applying the stable ID tie
break. The Vue chat displays source projections as read-only during rollback;
it must not send a new Agno turn with a source session ID. Rename and deletion
of a source projection target its own metadata; a mixed-source deletion request
is rejected before any deletion because the stores have no shared transaction.

When neither source table exists, legacy listing continues unchanged. A partial
source schema fails explicitly instead of silently hiding source data. Rollback
reads the last materialized projection and does not reconstruct a missing one
without the source checkpointer. Never import, delete, or rewrite old Agno rows
as part of the source-engine switch.

### 4. Validation and error matrix

| Condition | Behavior |
| --- | --- |
| Source projection belongs to another actor or is deleted | Session unavailable |
| Both stores appear in one delete request | Reject before either store changes |
| Only one source table exists | `AI_SOURCE_CHAT_SCHEMA_INCOMPLETE` |
| Legacy installation has no source tables | Existing Agno history remains available |

### 5. Good / base / bad cases

- Good: switch to Agno, read a source projection under its namespaced ID, then
  create a separate Agno conversation for new messages.
- Base: an installation with no source tables uses its existing Agno session
  behavior.
- Bad: replay source history into Agno or guess which numeric owner held an
  old username.

### 6. Tests required

Use isolated real Agno and source tables to test merged sorting, equal timestamp
pagination, title filtering, cross-user access, tombstones, mixed deletion,
missing/partial schema, and unchanged legacy rows. Vue tests must verify that
read-only source history cannot send and that a new chat re-enables input.

### 7. Wrong vs correct

```python
# Wrong: treat a source ID as an Agno generation session after rollback.
await agno_chat.chat_non_stream(message, source_session_id)

# Correct: present the owned projection as a read-only namespaced session.
result = await rollback_sessions.get_session("source:" + source_session_id)
```
