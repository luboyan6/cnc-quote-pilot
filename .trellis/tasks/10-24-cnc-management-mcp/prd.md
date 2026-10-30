# CNC account and part MCP server

## Goal

Analyze WeKnora's embedded MCP Server and expose only the existing account and drawing query interfaces through this project's MCP Server.

## Background and Evidence

- The requested WeKnora document is now `E:/AIWorkspace/rag-platform/website-docs/03-features/08-mcp.md`. Its current server reference starts at line 416; the old independent Python server is deprecated.
- WeKnora embeds a stateless Streamable HTTP server, authenticates each request, filters discovery and execution by an allowlist, and reuses existing business tools and permission checks.
- The target controllers and services already exist under `backend/app/plugin/module_cnc/cnc_account/` and `cnc_part/`.
- The workspace contains unrelated uncommitted account, drawing, and agent changes. Preserve and accommodate them.
- The user explicitly authorized task creation and continued implementation on 2026-10-24.
- The user's subsequent correction limits this feature to query interfaces only and explicitly excludes WeKnora's MCP client functionality. This supersedes the previous eleven-tool design and pending commit plan.

## Requirements

- R1: Document the source-backed WeKnora server request flow and its adaptation to this FastAPI application.
- R2: Provide an MCP Streamable HTTP endpoint inside the existing backend process, with client connection examples.
- R3: Expose exactly four query tools: `cnc_account_list`, `cnc_account_detail`, `cnc_part_list`, and `cnc_part_detail`. Retain existing pagination and search filters.
- R4: Reuse existing user authentication, action permissions, data access rules, business schemas, and transaction handling. Account responses must remain free of passwords, credential ciphertext, session ciphertext, and browser state.
- R5: Check authorization on every request and tool invocation. Hidden or unknown tools must not be executable by supplying their names directly.
- R6: Validate MCP arguments and return structured results plus readable errors without leaking submitted credentials or internal exception details.
- R7: Ship no mutation adapters, mutation argument models, or write-enable setting. No user, including a superuser, can enable create/update/delete/status operations through this MCP Server. Implement no outbound MCP client, external-service registration, OAuth client, client UI, or Agent MCP-client integration.
- R8: Add isolated protocol and authorization regression coverage and verify the existing affected CNC behavior.

## Acceptance Criteria

- [x] AC1 / R1: Source analysis maps WeKnora's Server to concrete code, distinguishes its unimplemented MCP client feature, and accurately describes this query-only adaptation.
- [x] AC2 / R2: A standard external MCP client can initialize/discover, list tools, and execute account and drawing queries through the embedded endpoint.
- [x] AC3 / R3, R5: Only the four query tools exist; discovery and invocation enforce the exact existing query/detail permissions.
- [x] AC4 / R4: Invalid/revoked authentication fails closed; account owner and drawing role-data restrictions remain effective through the existing services.
- [x] AC5 / R3, R7: Direct mutation calls fail for all users without changing rows. No write-enable option or runtime MCP-client implementation remains.
- [x] AC6 / R4, R6: Query results and rejected-input/error responses exclude credentials and session material.
- [x] AC7 / R8: Focused protocol/data-access tests, Ruff, and type checks pass; configuration, schemas, examples, specs, and final evidence reflect the four-tool scope.

Current evidence: `check-result.md` and `research/implementation-check.md` were replaced for the four-query scope. Independent review passed 20 MCP tests, 3 storage-privacy tests, targeted Ruff/basedpyright, static query-only/client-absence checks, whitespace validation, and 17 documentation links. No live production or vendor-platform validation is claimed.

## Out of Scope

- MCP client support or integration with the local AI agent.
- All create/update/delete/status tools, credential writes, drawing authorization changes, and write-enable configuration.
- Platform management, part configuration, quote execution, monitoring, or arbitrary REST/SQL/filesystem tools.
- Browser login interaction and spreadsheet import/export tools.
- Uploading drawing bytes, downloading arbitrary paths, or uploading to third parties.
- A new endpoint-management UI, a second account system, or replication of WeKnora knowledge-base features.
