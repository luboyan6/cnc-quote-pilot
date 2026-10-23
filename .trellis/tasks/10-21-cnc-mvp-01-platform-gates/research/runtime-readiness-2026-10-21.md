# Research: SDK, Python, provider, and checkpoint readiness

Later execution supplement: the backend environment/lockfile snapshot below remains unchanged. A separate task-local SDK environment was subsequently installed and the actual factory, restricted fixture tools, typed decision and cross-process SQLite/DeltaChannel checks passed; see [SDK probe](sdk-probe.md) and [actual result](sdk-probe-result-2026-10-21.json). System model-setting presence was checked without emitting values; real provider calls were not run before the user's phase-boundary stop. This does not establish product integration or live acceptance.

- Query: Recheck the Deep Agents baseline and establish the actual local prerequisites and blockers for V-07, without installing dependencies or accessing credentials.
- Scope: mixed (official release metadata/documentation, repository source, and read-only local runtime probes).
- Date: 2026-10-21; local snapshot timestamp: 2026-10-21T17:16:53+08:00.
- Active task: `.trellis/tasks/10-21-cnc-mvp-01-platform-gates`.
- Responsibility: the runtime portion of V-07; platform page/quote observations are collected separately by the main session.

## Findings

### 1. Result and evidence levels

The published baseline remains `deepagents==0.7.29`. The existing project interpreter satisfies its Python requirement. The backend virtual environment and lockfile do not contain Deep Agents, LangChain, LangGraph, their model integration, or a checkpoint saver. Consequently, live tool calling, actual `create_deep_agent` construction, and persistent Agent recovery remain unverified and cannot currently run in that environment.

| Check | Evidence level | Result |
| --- | --- | --- |
| Latest stable Deep Agents / Python requirement | Official online metadata plus tagged source | `0.7.29`, released 2026-10-20; Python `>=3.11,<4.0` |
| Project Python | Actual local process | Backend `.venv`: Python `3.12.13`; compatible |
| System Python / package manager | Actual local process | System `python`: `3.13.0`; `uv`: `0.12.1` |
| SDK / LangChain provider availability | Installed metadata, import discovery, parsed lockfile | Missing; not a completed SDK integration |
| Existing OpenAI SDK / PostgreSQL driver import | Actual local imports | `openai` and `psycopg` import successfully; no API/database connection attempted |
| Existing asynchronous SQLite driver | Actual local read-only query in memory | `SELECT sqlite_version()` returns `3.50.4`; not a file persistence or saver test |
| Actual provider tool calling / structured recovery decision | Not executed | Integration package missing; runtime model credentials/configuration deliberately not inspected |
| File-backed checkpoint / restart / interrupt-resume | Not executed | Saver/runtime missing; no checkpoint database created |
| Browser / platform live quotation | Outside this research slice | No browser operation or quotation claim from this investigation |

The first row is supported by the current [PyPI project page](https://pypi.org/project/deepagents/) and the [0.7.29 tagged package manifest](https://raw.githubusercontent.com/langchain-ai/deepagents/deepagents%3D%3D0.7.29/libs/deepagents/pyproject.toml). The other runtime rows come from the probes recorded below.

### 2. Published SDK and checkpoint baseline

The tagged Deep Agents manifest declares `langchain>=1.4.6,<2.0.0`, `langchain-core>=1.6.12,<2.0.0`, `langchain-anthropic>=1.7.6,<2.0.0`, `langchain-google-genai>=4.4.2,<5.0.0`, `langsmith>=0.14.11`, `packaging>=23.2`, and `wcmatch>=11.0`. These are release requirements, not resolved additions to this repository. [Source manifest](https://raw.githubusercontent.com/langchain-ai/deepagents/deepagents%3D%3D0.7.29/libs/deepagents/pyproject.toml).

| Package checked online | Published version | Relevant declared requirements | Local status |
| --- | --- | --- | --- |
| `deepagents` | `0.7.29` | Python `>=3.11,<4.0`; core requirements above | Not installed or locked |
| `langgraph-checkpoint-sqlite` | `3.1.2`, released 2026-10-12 | Python `>=3.10`; `langgraph-checkpoint>=4.3.0,<5.0.0`; `aiosqlite>=0.20`; `sqlite-vec>=0.1.6` | Saver absent; driver alone present |
| `langgraph-checkpoint-postgres` | `3.2.0`, released 2026-10-14 | Python `>=3.10`; `langgraph-checkpoint>=4.3.0,<5.0.0`; `orjson>=3.11.5`; `psycopg-pool>=3.2.0`; `psycopg>=3.2.0` | Saver and pool absent; `psycopg` present |

Saver versions/requirements were checked against [SQLite release metadata](https://pypi.org/pypi/langgraph-checkpoint-sqlite/3.1.2/json) and [PostgreSQL release metadata](https://pypi.org/pypi/langgraph-checkpoint-postgres/3.2.0/json). Both report non-yanked releases. These are candidates for a single dependency resolution in task 02, not a claim that a compatible complete environment has already been resolved.

`backend/pyproject.toml:6` declares `>=3.12`, and `backend/.python-version:1` requests `3.12`. The actual interpreter checked is `E:\AIWorkspace\cnc-quote-pilot\backend\.venv\Scripts\python.exe`, which reports `3.12.13` on Windows AMD64. The system `python` and backend interpreter differ; execute backend probes/checks with the project interpreter or the project's `uv` entry point.

`backend/pyproject.toml:80` configures the Tsinghua package index. No resolver/download/index reachability check was run. If an implementation dependency operation fails due to index/network access, record the real failure and follow the normal approval/network procedure; published metadata does not prove mirror freshness.

### 3. Actual local dependency snapshot

Read `backend/uv.lock` with Python `tomllib` and inspect the backend interpreter with `importlib.metadata.version`. No package installation/synchronization was performed.

| Distribution | Installed version | Present in lockfile |
| --- | --- | --- |
| `agno` | `2.5.8` | Yes |
| `openai` | `2.46.0` | Yes |
| `pydantic` | `2.12.5` | Yes |
| `pydantic-settings` | `2.14.1` | Yes |
| `fastapi` | `0.138.2` | Yes |
| `sqlalchemy` | `2.0.51` | Yes |
| `aiosqlite` | `0.22.1` | Yes |
| `psycopg` | `3.3.2` | Yes |
| `deepagents`, `langchain`, `langchain-core`, `langgraph` | Absent | No |
| `langchain-openai`, `langchain-anthropic`, `langchain-google-genai` | Absent | No |
| `langgraph-checkpoint`, `langgraph-checkpoint-sqlite`, `langgraph-checkpoint-postgres` | Absent | No |
| `anthropic`, `psycopg-pool`, `playwright` | Absent | No |

`importlib.util.find_spec` independently returned `False` for `deepagents`, `langchain`, `langgraph`, and `langchain_openai` under that interpreter. The Playwright result concerns the backend virtual environment only; it does not assess the main session's connected browser tools or another Python environment.

Source fingerprint at this snapshot (SHA-256):

```text
backend/pyproject.toml  E382B887942B8FCC9323BF2443351FAF4BC553F250160E1282026A4B86F70176
backend/uv.lock         24C09C5D28B123988DF9C2CB12AE9C6E2ED3E47A76D3DBA459EB3C1D5EBCA67C
backend/.python-version 8DFDA54BA2F66AB3A8EBAB460F4338BBEEA1FB1E0F85CE06FE3530AA3C64679B
```

### 4. Existing model configuration entry points

Only source configuration declarations and field names were inspected. No `.env` content, process environment values, Redis model records, decrypted API keys, endpoint values, model IDs, Cookie, browser state, or platform account material was read.

| Entry point | Source evidence | Meaning for task 02 |
| --- | --- | --- |
| Application environment file selection | `backend/app/config/path_conf.py:16`; `backend/app/config/setting.py:18`, `:388` | Settings choose `backend/env/.env.<ENVIRONMENT>` with the application's dev fallback |
| System model settings | `backend/app/config/setting.py:243` | Names are `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`; these are application settings, not proof of a configured/live model |
| Existing runtime model factory | `backend/app/utils/ai_factory.py:22`, `:44`, `:70` | `AgnoFactory.create_agent` builds Agno `OpenAILike` from settings or an explicit runtime configuration |
| Per-user model DTO | `backend/app/modules/ai/chat/schema.py:92` | Fields: `name`, `base_url`, `api_key`, `model_id`, `temperature`; no CNC durable provider binding is established by this DTO |
| Model management endpoints | `backend/app/modules/ai/chat/controller.py:127`, `:137`, `:148`, `:160`, `:170` | Existing model list/create/update/delete/activate flow belongs to AI chat |
| Stored configuration lifetime | `backend/app/modules/ai/chat/service.py:332`, `:378`, `:410`, `:490` | Per-user Redis entries/active references have a seven-day TTL; not a stable scheduled-CNC configuration contract |
| Existing secret storage handling | `backend/app/modules/ai/chat/service.py:358`, `:363`, `:371` | Existing code encrypts the `api_key` field for Redis storage and decrypts on reads; no data reads were performed here |

The existing factory supplies `tools=[]` to its member Agent (`backend/app/utils/ai_factory.py:62`). An existing chat response or model configuration therefore would not demonstrate this project's required recovery observation tools and `RecoveryDecision` behavior.

Necessary names for the existing OpenAI-compatible configuration are listed above, plus `ENVIRONMENT` for file selection. The checkpoint package also documents `LANGGRAPH_STRICT_MSGPACK` for strict deserialization. No new CNC setting names or environment values are invented in this research.

Deep Agents requires a LangChain chat model that supports tool calling. Its `openai:...` string path enables Responses API defaults; an OpenAI-compatible gateway must instead be configured and tested with an explicit model instance/protocol as appropriate. Existing Agno `OpenAILike` behavior does not establish compatibility with the new integration. [Official model configuration](https://docs.langchain.com/oss/python/deepagents/models).

Task 02 must freeze a non-sensitive provider/model configuration reference and resolve its secret at runtime. Whether an appropriate live account/model is already configured remains unknown because this read-only investigation deliberately did not access its values. Missing packages are a proven blocker; missing credentials are not asserted.

### 5. Checkpoint feasibility and exact verification gap

The parent design chooses a private file-backed `AsyncSqliteSaver` for a single CNC consumer. Official package examples expose `langgraph.checkpoint.sqlite.aio.AsyncSqliteSaver` through an asynchronous context manager; the asynchronous saver methods are appropriate for async graph execution. SQLite is documented for local/lightweight deployments. [SQLite package](https://pypi.org/project/langgraph-checkpoint-sqlite/), [checkpointer guide](https://docs.langchain.com/oss/python/langgraph/checkpointers).

Executed local baseline:

```text
Interpreter: backend/.venv/Scripts/python.exe -B
Imports: openai -> ok; psycopg -> ok; aiosqlite -> ok
Storage: :memory:
SQL: SELECT sqlite_version()
Result: 3.50.4
Process exit: 0
```

This proves the existing async SQLite driver can run a harmless in-memory query. It does not prove file durability, Agent serialization, saver migrations, concurrent use, crash recovery, or interrupt/resume. No disk DB was opened or created, and no application DB connection was attempted.

Current `deepagents==0.7.29` source defines `DeepAgentState.messages` using `DeltaChannel` with a snapshot frequency of 50 (`deepagents/graph.py`, upstream lines 71-74). The same source accepts `checkpointer` and `response_format` (`252-272`) and forwards them to `create_agent` (`908-920`). Test the actual compiled Agent state and messages with the resolved saver/serializer, including restart after accumulated deltas; an ordinary-dictionary saver round trip alone is insufficient. [Tagged graph source](https://raw.githubusercontent.com/langchain-ai/deepagents/deepagents%3D%3D0.7.29/libs/deepagents/deepagents/graph.py).

For serialization, use the chosen package's strict MsgPack/explicit type-allowlist mechanism and verify the actual model-message/decision/delta types round-trip. Do not enable pickle fallback merely to hide serialization failures. The official checkpointer guide describes serializer behavior; the package README recommends strict type handling. [Checkpointer serialization](https://docs.langchain.com/oss/python/langgraph/checkpointers#serializer), [SQLite package guidance](https://pypi.org/project/langgraph-checkpoint-sqlite/).

PostgreSQL is an optional future/shared saver, not an established current database connection. The installed `psycopg` meets its published driver's lower bound, but `psycopg-pool` and the saver are absent. PostgreSQL saver initialization requires setup; manually supplied connections require the documented transaction/row-factory configuration. It cannot be connected directly to MySQL or inferred from the application's `DATABASE_TYPE` default. [PostgreSQL package](https://pypi.org/project/langgraph-checkpoint-postgres/); repository database selector: `backend/app/config/setting.py:101`, `:337`, `:351`.

### 6. API and workflow constraints to carry into task 02

The following are source/documentation checks, not executed Agent acceptance tests:

- Pass constructed backend instances, such as `StateBackend()` and `CompositeBackend(...)`. The old runtime factory examples in local memory skills are deprecated in the current SDK. [Official backend migration guide](https://docs.langchain.com/oss/python/deepagents/backends#migrate-from-backend-factories).
- Register the appropriate harness profile before agent creation. Disable the default general-purpose subagent explicitly and pass no other subagents; an empty list alone does not disable it. Check the profile selected for the actual configured model object. The `create_deep_agent` signature has no `harness_profile` keyword. [Profiles](https://docs.langchain.com/oss/python/deepagents/profiles), [tagged factory signature](https://raw.githubusercontent.com/langchain-ai/deepagents/deepagents%3D%3D0.7.29/libs/deepagents/deepagents/graph.py).
- File permissions are first-match, unmatched-allow, and apply to built-in filesystem tools. Keep the catch-all deny and enforce custom observation-tool ACLs separately. [Official permission guide](https://docs.langchain.com/oss/python/deepagents/permissions).
- Distinguish persisted thread state from a cross-thread Store and from the authoritative domain database. In-memory savers do not survive process restarts. [Official persistence guide](https://docs.langchain.com/oss/python/langgraph/persistence).
- Preserve the parent's S01-S11 fixed workflow and E01-E13 exits. The proven runtime gaps map to E12 `AGENT_UNAVAILABLE`; a deterministic normal workflow may continue, while an incident that actually requires the unavailable Agent must use its defined human/failure exit. Parent evidence: `workflow-design.md:40-50`, `:58-70`.
- E09 permits only read-only reconciliation for an ambiguous upload/Apply receipt; a model must not authorize resubmission. E11 restores from domain intent/version/remote references rather than letting a checkpoint decide the business step. A business `WAITING_HUMAN` is not an SDK interrupt. Parent evidence: `workflow-design.md:66-69`, `:117`.

### 7. Precise next steps and required evidence

These are implementation/validation steps for task 02, not actions executed in this research:

1. Resolve the pinned Deep Agents baseline, directly imported LangChain/LangGraph packages, chosen model integration, and SQLite saver together in `backend`; update the existing dependency/lock/production-entry conventions. Re-read current metadata if implementation starts later. Verify the combined resolution against Agno/OpenAI/Pydantic and existing tests; current requirements alone do not establish compatibility.
2. Construct the CNC recovery factory against the installed signature. Inspect the final tool list and selected harness profile with a scripted model; ensure only the approved observation/decision surface is available and no delegation, shell, or business-side-effect tools leak in.
3. Bind an authorized provider configuration through a stable server-owned reference. Run a small synthetic, non-secret tool call and a valid `RecoveryDecision` schema round trip against the actual provider. Record integration/version/protocol, configuration reference, tool-call/result correlation, structured validation, timeout/retry behavior, and provider errors without secret values or raw sensitive prompts.
4. With the private file-backed `AsyncSqliteSaver` under the consumer lifecycle, persist an actual Agent run, close the process, reopen the same store/thread, and inspect/resume it. Verify messages/deltas, ownership/thread isolation, permissions, serialization, cumulative budget, and interrupted versus ordinary business-pause behavior. This must use a persistent file; `:memory:` is not a restart test.
5. Exercise an authorized synthetic/sanitized unknown-page incident through observation -> decision -> guard -> recovery -> verification. Record fixture versus real page origin. Recheck E09/E11/E12/E13 and duplicate/restart rejection; actual live platform pricing remains a separate acceptance requirement.

For this task's runtime V-07 slice, a recorded blocker is a valid feasibility result. It must not be relabeled as task 02's SDK/provider/recovery acceptance passing. The page/stop-point portion of V-07 remains the responsibility of the separate live validation record.

### 8. Files found and related project guidance

| Path | Role |
| --- | --- |
| `.trellis/tasks/10-21-cnc-mvp-01-platform-gates/{prd,design,implement}.md` | V-07 responsibility and feasibility/product boundary |
| `.trellis/tasks/10-21-cnc-pricing-mvp/agent-design.md` | Current recovery Agent architecture and saver/model contracts |
| `.trellis/tasks/10-21-cnc-pricing-mvp/workflow-design.md` | Fixed business steps, allowed strategies, E09/E11/E12 exits |
| `.trellis/tasks/10-21-cnc-pricing-mvp/research/deepagents-2026-10-21.md` | Earlier SDK research; this record adds actual interpreter/package evidence |
| `backend/pyproject.toml`, `backend/uv.lock`, `backend/.python-version` | Dependency declarations, resolution snapshot, runtime request |
| `backend/app/utils/ai_factory.py` | Existing Agno/OpenAI-compatible construction pattern |
| `backend/app/config/setting.py`, `backend/app/config/path_conf.py` | Static environment/DB configuration entry points |
| `backend/app/modules/ai/chat/{schema,service,controller}.py` | User model DTO, encrypted Redis caching, management API |
| `.trellis/spec/backend/index.md`, `directory-structure.md`, `database-guidelines.md`, `quality-guidelines.md`, `error-handling.md`, `logging-guidelines.md` | Read before conclusions; detailed backend pages currently contain placeholders, not established executable conventions |
| `.trellis/spec/guides/{index,cross-layer-thinking-guide,code-reuse-thinking-guide}.md` | Shared-contract boundaries and inspect-before-changing guidance |

The relevant skills were read: `ecosystem-primer`, `deep-agents-core`, `langchain-dependencies`, `deep-agents-memory`, and `langgraph-persistence`. Current official/tagged APIs take precedence over their older backend snippets. The role-isolated research context was supplied by the native Trellis hook; implementation/check manifests were not loaded.

## Caveats / Not Found

- Dependency resolution, SDK construction, provider tool calling, durable checkpoint recovery, and platform quotations were not executed. Packages were not installed, no application server was started, no product/spec/task-state files were changed, and no git operations were performed.
- The local probes used only the backend interpreter, installed metadata/import discovery, source/lockfile reads, and an in-memory read-only SQLite query. Neither `.env` values nor model/Redis secrets were inspected; configured provider/model availability remains unknown.
- Backend spec detail pages remain templates. Treat source-backed observations here as research, not as a silent replacement for project specs. The main session owns any spec update.
- Guessed raw GitHub saver tag URLs returned 404. Saver dependency/version facts above instead use official versioned PyPI JSON; no nonexistent source tag is cited as evidence. The web fetcher rejected the generic saver-reference endpoint's Markdown content type, so API claims use the official package examples and checkpointer guide.
- The current published saver requirements include a checkpoint major version not present in this repository. Do not copy an older saver pin from a local skill and assume DeltaChannel recovery works; verify the combined locked environment and actual state.
