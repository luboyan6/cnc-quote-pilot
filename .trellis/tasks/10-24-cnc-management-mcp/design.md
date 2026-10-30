# Embedded CNC Management MCP Design

## Boundary and Architecture

The behavior gap is a standards-based MCP Server transport and a query-only adapter for existing account/drawing services. Embed the official Python MCP SDK (`mcp>=2.3,<3`, locked at 2.3.0) in FastAPI. The latest user instruction supersedes the previous write-capable design. Do not hand-write JSON-RPC or implement outbound MCP-client functionality.

Request flow: MCP client -> existing deployment API prefix -> embedded MCP ASGI endpoint -> existing Bearer authentication -> filtered tool catalog / guarded invocation -> existing CNC service and schemas -> existing CRUD in a committed request transaction -> structured MCP result.

Use canonical backend `/mcp/` and proxy `/api/v1/mcp/`. An exact Starlette ASGI route delegates to the native SDK session manager, avoiding nested-router path resolution under the application's `ROOT_PATH`; direct and prefixed paths are tested. Initialize and close the SDK session manager through the host lifespan; mounted ASGI app lifespans do not run automatically. Use stateless Streamable HTTP and JSON responses. No separate port, subprocess, server-side client session, or schema migration is needed.

## Authentication and Authorization

- Accept only `Authorization: Bearer <existing access_token>`. Use the project's current authentication implementation, including Redis revocation, refresh-token rejection, session expiry, and current user lookup; signature-only JWT decoding is insufficient.
- Do not introduce a shared superuser, a static machine token, a fallback identity, or a new endpoint token management system. This is an intentional adaptation from WeKnora's workspace endpoint principal to this project's existing user model.
- List only tools whose exact existing `module_cnc:<module>:<action>` permission the actor has; superusers follow the current `AuthPermission` behavior. Recheck the same permission before invocation, independent of discovery.
- Keep identity and settings request-local. Concurrent users and independent app factories must not share mutable identity or tool allowlists.
- The account service additionally enforces creator ownership for ordinary users. Both modules inherit role-based self/department/all data ranges through `CRUDBase._build_conditions` and `Permission._permission_condition`. Reuse those actual checks; do not rely on the stale CRUDBase class docstring that says filtering is entirely service-owned.
- Preserve existing query-session and error handling. No MCP adapter calls a business mutation method. Existing authentication session renewal remains owned by the shared authentication implementation.
- Validate Origin/Host with the SDK transport-security controls and existing configured origins/hosts. Document explicit production configuration; no globally disabled transport security.

## Tool Contract

| Tools | Permission suffix | Service call |
| --- | --- | --- |
| `cnc_account_list`, `cnc_part_list` | `query` | `page` with validated pagination/filter models |
| `cnc_account_detail`, `cnc_part_detail` | `detail` | `detail` |

Reuse existing Pydantic query/output schemas with strict argument wrappers, positive IDs and existing pagination limits (maximum 100). Remove mutation DTOs, batch/status argument models, and all create/update/delete/status execution branches from the MCP package. All four tools are read-only, nondestructive, idempotent, and closed-world. A remembered or guessed mutation tool name is always unavailable, even for a superuser.

Keep `MCP_ENABLED` and the existing MCP Host/Origin allowlists. Delete `MCP_ALLOW_WRITES`; no configuration can widen the four-tool catalog. The endpoint is registered only when enabled, with deferred SDK imports. Use native MCP response objects rather than the REST envelope.

## Privacy and Error Contracts

Return existing output schema data as both readable text and structured content. Account output must be serialized through the independent safe `CncAccountOutSchema`, never an ORM `__dict__` or write DTO. Validate output if the service boundary changes.

Never log tool arguments or raw exceptions containing arguments, SQL parameters, credentials, session/browser state, or tokens. Validation errors omit inputs and context; unknown/disabled tool errors do not reflect arbitrary tool names. Expected business failures use a bounded safe message/code. Unexpected failures return a fixed message and only safe metadata may be logged. Authentication infrastructure failures return a fixed unavailable response, never a permissive fallback. Make sure the chosen SDK's own schema validation does not echo password inputs before the application handler runs.

## Compatibility and Rollback

No change to current REST contracts or account/part CRUD is planned. Add a small integration point to the application factory/lifespan and additive configuration/dependencies. Existing Nginx and Vite `/api/v1` proxy rules should carry `/api/v1/mcp/`; verify this and document direct vs proxy URLs. Extend proxy settings only if required by evidence. Disabling `MCP_ENABLED` removes the new surface. Do not remove or overwrite unrelated dirty workspace changes.

## Verification

Use isolated `unittest`/ASGI tests consistent with `backend/tests/cnc/login/test_http.py`. Keep official SDK clients strictly as test harnesses for initialize/discovery and all four queries. Retain authentication/revocation, permission hiding/direct-call denial, concurrency, output/input privacy, safe errors, disabled registration, manager lifecycle, Host/Origin/body limits, and direct/root-path routing coverage. Real in-memory SQLite tests must exercise the existing account/part query services and data scopes. Replace mutation-success tests with permanent mutation-denial tests for superusers and ordinary users, including stale write-enable environment/config inputs. Seed fixtures directly; do not preserve mutation-capable MCP code just to test it.

Run targeted Ruff and focused CNC account regression suites. Do not count isolated tests as live deployment or vendor-platform verification.
