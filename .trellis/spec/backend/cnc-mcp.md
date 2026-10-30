# CNC MCP Server

## 1. Scope / Trigger

Read when modifying the embedded MCP transport, CNC tool catalog, authentication, business adapters, application lifespan integration, or MCP deployment configuration. Sources: `app/modules/cnc/mcp/`, `docs/cnc-mcp-server.md`, and `docs/weknora-mcp-analysis.md`.

This feature provides an MCP Server for external callers. It exposes account/drawing queries, controlled account login and explicit password decryption. It adds no outbound MCP client, external-service manager, OAuth client, Agent integration, quote, arbitrary browser input or file-transfer operations.

## 2. Signatures

- `register_mcp(app: FastAPI) -> None`: optional route registration; one independent server per host app.
- `mcp_lifespan(app: FastAPI)`: async context manager for the SDK session manager; called by the host application's lifespan.
- Canonical backend `/mcp/`, deployment prefix `/api/v1/mcp/` with default `ROOT_PATH`.
- `CncMCPServer.list_tools(ctx, params) -> ListToolsResult`.
- `CncMCPServer.call_tool(ctx, params) -> CallToolResult`.
- `ToolSpec.execute(auth, db, arguments) -> dict`: delegates to existing account/part services.
- Official SDK dependency: `mcp>=2.3,<3`, locked by `backend/uv.lock`; protocol handling belongs to the SDK.

## 3. Contracts

### Configuration and identity

`MCP_ENABLED=false` removes the endpoint. `MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` are JSON-array settings with loopback defaults; deployments explicitly add their public host and browser origin. Transport security stays enabled independently of development CORS. There is no write-enable configuration; the former `MCP_ALLOW_WRITES` option is removed.

Accept existing access tokens only in `Authorization: Bearer ...`. Reuse `_authenticate`, including Redis session existence/revocation, refresh-token rejection, configured sliding expiry, and current DB user lookup. Signature-only JWT validation is forbidden. Do not create a shared superuser fallback or treat query-string tokens as credentials. Authentication storage failures fail closed.

Carry the authenticated `AuthSchema` in the current request, not mutable server-global identity. Create the catalog/transport per app. Private, zero-TTL discovery prevents one user's catalog from being cached for another user.

### Catalog and argument ownership

| Tools | Existing action permission suffix | Argument shape |
| --- | --- | --- |
| `cnc_account_list`, `cnc_part_list` | `query` | `{page_no, page_size, order_by, search}` |
| `cnc_account_detail`, `cnc_part_detail` | `detail` | `{id}` |
| `cnc_account_login` | `update` | `{id, action="start", session_id?}` |
| `cnc_account_decrypt_password` | `update` | `{username}` (exact unique permitted match) |

Permissions are `module_cnc:<module>:query`, `module_cnc:<module>:detail` and `module_cnc:cnc_account:update` for login/decryption. Both discovery and invocation apply `AuthPermission`; never rely on hiding alone. Exactly six tools exist. Generic CRUD/status mutations remain unavailable, including to superusers.

Reuse existing query/output schemas with strict outer and nested search models. Positive IDs exclude booleans. Pagination uses existing defaults and maximum 100. The complete HTTP request body is bounded to 64 KiB. Queries/decryption are annotated read-only, nondestructive, idempotent and closed-world. Login is nondestructive but not read-only or idempotent, and is open-world because it contacts a vendor and persists session/lease state.

No create/update/delete/status argument model, mutation DTO import, or mutation execution branch belongs in the MCP package. Drawing queries may return or filter `upload_authorized`; this interface cannot alter that field or transfer bytes.

### Business behavior and privacy

The current CRUD query builder applies `Permission._permission_condition`; account service additionally requires creator ownership for ordinary users. Preserve these executable data checks. Stale class comments must not override observed code behavior.

Query adapters call `page` and `detail` on existing account/drawing services. No arbitrary method/URL/SQL dispatch is allowed. A query and its safe result validation share the existing request transaction boundary. Authentication session renewal follows shared authentication behavior; query/decryption calls leave business rows unchanged.

Login uses shared `login.actions.login_action`, also used by the HTTP controller. `start` rejects a session ID; `status`, `verify`, and `close` require the returned bounded session ID. Every action reloads account ownership/configuration/credentials through the existing manager repository; decryption stays internal to `read_credentials`. Preserve actor-bound revocation and independent fenced transactions. Return only `LoginView`; READY alone means verified identity. WAITING_HUMAN requires the existing human login window, without MCP screen-input tools.

The independent `cnc_account_decrypt_password` tool accepts only `username` (a nonblank string of at most 64 characters), not an ID. It intentionally returns `{id, username, password}` with plaintext only after update permission and `CncAccountService.credential_account_by_username` data/owner checks. Lookup uses exact equality, creator filtering, existing CRUD data scopes and soft-delete exclusion; require exactly one visible match. Missing/inaccessible or ambiguous matches fail without selecting a password. It uses `read_credentials`, never accepts arbitrary ciphertext, and does not start a browser or mutate records. Never log its result. Callers must keep plaintext out of user-visible displays and logs.

Account query results use independent `CncAccountMcpOutSchema`: `id`, `username`, encrypted `password`, `platform_name`, `login_url`, `quote_url`. Use account ID for login and username for decryption. The password field contains the existing Fernet-encrypted credential envelope, not plaintext or a mask; do not decrypt on query. Seal legacy plaintext in memory without mutating rows. Drawing list results use `CncPartListOutSchema` (`file_name`, `file_path`). Never serialize ORM dictionaries or credential write models directly. Use native MCP text plus structured results; do not add the REST envelope.

Do not echo or log arguments, tokens, encrypted credentials, browser state, exception strings, SQL parameters, or traceback locals. SDK envelope validation can expose input before a tool handler runs, so test malformed protocol input as well as valid tool calls. Keep JSON-RPC errors valid while returning fixed safe messages.

Mounted sub-application lifespans do not run automatically. Enter `session_manager.run()` in the host lifecycle and close it before backend resources are disposed. Disabled MCP must not require SDK import/startup.

## 4. Validation and Error Matrix

| Condition | Required behavior |
| --- | --- |
| Missing/invalid/revoked credentials or refresh token | HTTP 401, fixed message, no tool execution |
| Authentication DB/Redis unavailable | HTTP 503, fixed message, no permissive fallback |
| Invalid Host or Origin | SDK transport rejection; no business execution |
| Missing action permission | Hide from catalog and deny direct invocation |
| Generic create/update/delete/status call | Always unavailable, including for superusers; no business row changes |
| Login/decryption without update permission | Hidden and denied, without loading credentials or starting a browser |
| Login/decryption for another ordinary user's account | Denied by existing owner checks |
| Unknown tool | Fixed JSON-RPC invalid-params error; no arbitrary name reflection |
| Invalid/secret-bearing arguments | MCP error without input or raw validation exception |
| Malformed envelope | Bounded fixed JSON-RPC error, preserving required envelope fields |
| Query/data-permission failure | Safe error; no result or credential leakage |
| Unexpected execution/result failure | Fixed error and safe metadata only |
| Successful account query | Encrypted password only; no plaintext, session ciphertext, browser state or lease secrets |
| Successful explicit decryption | Plaintext only in the authorized tool result; no server logs |
| Successful login tool response | Public LoginView only; distinguish STARTING/WAITING_HUMAN from READY |
| MCP disabled | Route unregistered; ordinary backend behavior retained |

## 5. Good / Base / Bad Cases

- Good: authorized caller sees only permitted tools, queries encrypted credentials, explicitly decrypts only a permitted account, and logs in through the existing controlled manager.
- Base: official SDK transport tests with isolated storage prove protocol and adapter behavior; they do not prove production Redis/PostgreSQL deployment or vendor login/quoting.
- Bad: shared administrator identity, catalog-only authorization, raw error reflection, retaining configurable/dormant mutation adapters, or exposing a generic REST/filesystem/MCP-client tool.

## 6. Tests Required

Use isolated tests under `backend/tests/cnc/mcp/`. Assert official SDK discovery/legacy initialization, four queries plus login/decryption, accurate annotations, generic mutation denial, per-request authentication/revocation, action permissions, concurrent identities, request-size/Origin/Host checks, encrypted query output and malformed-input privacy, existing data scopes, root-path routing, manager lifecycle, and disabled registration. Real SQLite fixtures prove password decryption and owner rejection; mock browser startup to verify a plaintext internal snapshot with a secret-free login response. Verify explicit decryption returns plaintext without logging it. SDK clients belong only to test harnesses, not the application feature.

Run focused Ruff and configured type checking. Use `unittest` for isolated suites when full `backend/tests/conftest.py` startup is unrelated. Record actual commands and limitations; do not report skipped or unavailable checks as passed.

## 7. Wrong vs Correct

```python
# Wrong: an arbitrary service method turns a query interface into a write API.
return await getattr(service, client_method)(**arguments)

# Correct: a closed catalog contains only the six reviewed tools.
spec = TOOL_BY_NAME.get(requested_tool)
if spec is None:
    raise MCPError(code=INVALID_PARAMS, message="Tool unavailable")
await AuthPermission([spec.permission])(auth=auth)
return await spec.execute(auth, db, validated_arguments)
```

Hiding a query in `tools/list` must always be paired with an independent permission check in `tools/call`. Mutation tools must be absent from the implementation, not merely hidden behind a default setting.
