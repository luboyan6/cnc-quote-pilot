# Source Findings

## WeKnora

The requested `website-docs/03-features/mcp.md` is named `08-mcp.md` in the local checkout. Lines 416-493 document the current embedded server; lines 494 onward mark the independent Python server as deprecated.

- `internal/router/routes_mcp_endpoint.go`: management routes and public POST/GET/DELETE `/mcp/:endpoint_id`, outside global REST auth but with its own endpoint auth.
- `internal/middleware/mcp_endpoint_auth.go`: header-only Bearer extraction, active endpoint/workspace checks, synthetic endpoint principal, and scoped API-key capabilities.
- `internal/mcpserver/server.go`: one catalog, request-specific discovery filter and invocation guard, stateless HTTP, per-endpoint rate limits, structured result adapter, existing business tool reuse.
- `internal/types/mcp_endpoint.go`, `internal/types/mcp_endpoint_tools.go`: endpoint model, capability mapping, and tool allowlist.
- `internal/application/service/mcp_endpoint.go`: endpoint CRUD, token generation/hash storage/rotation, authorization checks and configuration validation.
- `internal/mcpserver/tools_retrieve.go`, `tools_ingest.go`: adapters delegate to existing tools/services instead of duplicating data access.

## This Application

- `backend/app/__init__.py` owns the sole app factory, host lifecycle, and routes. It uses `ROOT_PATH=/api/v1`; Vite and Nginx already proxy that prefix unchanged.
- `app/core/dependencies.py` provides `_authenticate` (JWT + Redis session + DB user) and `AuthPermission` (current action checks); `db_getter` wraps sessions in transactions. CRUD methods only flush.
- Account service enforces creator isolation and lifecycle revocation; its output schema has no password/ciphertext fields. Account schema errors must not disclose raw write DTO values.
- `CRUDBase._build_conditions` at line 339 applies `Permission._permission_condition`; its introductory docstring is stale. Both modules retain existing role-based self/department/all data ranges. Account service adds an explicit creator restriction for ordinary users.
- The final user instruction limits this integration to exactly four list/detail query tools. Exclude all create/update/delete/status adapters and their DTOs/settings. Drawing `upload_authorized` is query metadata only. WeKnora's outbound MCP-client feature is explicitly unimplemented; official SDK client usage belongs to protocol tests only.
- Existing focused tests use isolated `unittest` runners to avoid `backend/tests/conftest.py`'s unrelated full-app startup.

## SDK Sources Verified

- https://github.com/modelcontextprotocol/python-sdk: current stable public API is v2, `MCPServer` and low-level `Server`.
- https://py.sdk.modelcontextprotocol.io/advanced/low-level-server/: constructor callbacks accept `(ServerRequestContext, params)`; low-level schemas/results remain application-owned.
- https://py.sdk.modelcontextprotocol.io/run/asgi/: mounted MCP app requires explicit host lifecycle for `session_manager.run()`, host/origin security and root-path-aware mounting.
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports: authenticated Streamable HTTP, Origin checks and standard JSON-RPC responses.

The backend currently has no installed `mcp` package; pin a supported major and inspect the resolved API rather than copying obsolete FastMCP v1 signatures.
