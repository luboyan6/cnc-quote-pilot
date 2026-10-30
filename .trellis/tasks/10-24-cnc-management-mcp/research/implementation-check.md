# Query-only Implementation Check Record

Date: 2026-10-24. Role: Trellis implementer. Independent check remains a main-session gate. This record replaces all earlier write-capable implementation evidence after the user's explicit scope correction.

## Current Boundary

- Exactly four tools remain: `cnc_account_list`, `cnc_account_detail`, `cnc_part_list`, and `cnc_part_detail`.
- Every tool is read-only, nondestructive, idempotent and closed-world. The only service calls are the existing `page` and `detail` methods.
- Deleted all MCP mutation DTOs, mutation argument models/imports, mutation execution branches, write instructions and write-availability checks. Removed `MCP_ALLOW_WRITES` and `self.allow_writes`; stale environment/config input cannot widen the catalog.
- No outbound MCP client, external-service registration, OAuth client or Agent integration was added. Official SDK clients remain strictly test harnesses.
- Preserved native stateless SDK transport, exact ASGI `/mcp/` route, `/api/v1` root-path support, host lifecycle, Bearer authentication, permission filters and direct-call guards.
- Preserved Host/Origin and 64 KiB body controls, safe envelope/argument/error handling, per-request identity, safe output schemas, account ownership and actual role data scopes.
- `MCP_ENABLED=false` remains the default; transport Host/Origin defaults remain loopback-only.
- No REST CNC service/schema/CRUD, Agent code, dependency manifest or lockfile was changed in this correction.

## Files Updated in This Scope Correction

- `backend/app/modules/cnc/mcp/tools.py`: four query adapters and query-only schemas/catalog.
- `backend/app/modules/cnc/mcp/server.py`: removed write state/gating and updated instructions.
- `backend/app/config/setting.py`: deleted the write-enable field and corrected its adjacent MCP comment.
- `backend/tests/cnc/mcp/test_http.py`: permanent mutation denial, stale-setting coverage, preserved protocol/auth/privacy/lifecycle checks and explicit direct/prefixed path success.
- `backend/tests/cnc/mcp/test_database.py`: real queries, role/ownership checks and unchanged-row mutation-denial assertions.

## Validation

Commands run from the repository root:

| Command | Current result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/mcp -p 'test_*.py'` | 20 passed in 11.065 seconds: 17 protocol/auth/privacy tests and 3 real SQLite query/data-scope/denial tests |
| `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/login -p 'test_storage_privacy.py'` | 3 passed |
| `backend/.venv/Scripts/ruff.exe check --fix backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/config/setting.py` | All checks passed |
| `backend/.venv/Scripts/basedpyright.exe --project backend/pyrightconfig.json backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/config/setting.py` | 0 errors, 0 warnings |

The protocol suite uses actual official SDK `ClientSession` and `Client(mode='2026-07-28')` HTTP transports. It covers initialize/discovery/query results, read-only annotations, exact query/detail permissions, revocation/expiry/refresh-token rejection, concurrent identities, fixed query/storage errors, secret-bearing rejected inputs and malformed envelopes/params, Host/Origin/body controls, disabled lifecycle and direct/prefixed URLs.

Mutation names are rejected for ordinary users with mutation permissions, superusers, and stale `MCP_ALLOW_WRITES=true` input. Real in-memory SQLite tests compare every account/drawing row before and after attempts. Existing services exercise all four outputs, account-owner isolation, role SELF filtering, and role ALL expansion for drawings while account ownership remains restricted.

## Limits

No full backend startup, production database/Redis access, browser activity, vendor transfer, quotation or live deployment was performed. SQLite/fakeredis and ASGI protocol evidence do not constitute PostgreSQL or deployed-proxy acceptance. Enable `MCP_ENABLED` and restart to expose the endpoint; deployment Host/Origin configuration remains explicit.
