# Independent Query-only Check Result

Date: 2026-10-24. Role: `trellis-check`. This fresh review replaces the earlier write-capable review. The current approved scope is an embedded MCP Server exposing exactly four account/drawing queries, with no outbound MCP-client application feature.

## Findings

No task-scoped correctness, authorization, privacy, or compatibility defect was found. No product-code fixes were required. Existing unrelated account/part/Agent changes and shared dependency work were preserved.

No unresolved task-scoped finding remains. Product documentation, task design, and the seven-section backend spec agree with the query-only implementation.

## Current Boundary Verified

- Exactly `cnc_account_list`, `cnc_account_detail`, `cnc_part_list`, and `cnc_part_detail` exist. Every annotation is read-only, nondestructive, idempotent, and closed-world.
- The MCP package contains only query/search argument models. Static AST inspection found only `service.page` and `service.detail` calls; there are no mutation adapters, DTOs, or create/update/delete/status execution branches.
- The exact MCP settings are `MCP_ENABLED`, `MCP_ALLOWED_HOSTS`, and `MCP_ALLOWED_ORIGINS`. No write-enable field or dormant flag remains. Tests prove stale write-enable input cannot widen the catalog.
- Header-only Bearer authentication reuses `_authenticate` for each HTTP request, including actual JWT/session expiry, revocation, refresh-token rejection, and current user lookup.
- Discovery and invocation independently apply existing query/detail `AuthPermission` checks. Unknown, hidden, and mutation names cannot execute by direct invocation, including for superusers with write permissions.
- Existing account creator restrictions and role data scopes remain owned by the existing services and CRUD query builder. Real SQLite tests prove SELF restrictions and ALL-scope drawing expansion while account owner isolation remains enforced.
- Direct mutation attempts by ordinary users and superusers leave complete account/drawing row snapshots unchanged. Fixtures are seeded directly, not through mutation-capable MCP code.
- Account output uses the independent safe response schema, including every page item. Rejected arguments, malformed protocol envelopes/params, business errors, and storage failures are covered for safe responses/logs.
- Native stateless HTTP, request-local identity, private zero-TTL discovery, Host/Origin validation, the 64 KiB body limit, disabled registration, and host manager lifecycle are retained. Both `/mcp/` and `/api/v1/mcp/` work; unregistered subpaths are rejected.
- Application MCP code imports no outbound MCP client. Official SDK clients remain solely protocol test harnesses; no external-service registration, OAuth client, client UI, or Agent MCP-client integration is added.

## Fresh Independent Verification

Commands were executed from the repository root.

| Command | Current result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/mcp -p 'test_*.py'` | PASS: 20 tests in 12.157 seconds |
| `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/login -p 'test_storage_privacy.py'` | PASS: 3 tests in 0.125 seconds |
| `backend/.venv/Scripts/ruff.exe check backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/__init__.py backend/app/config/setting.py` | PASS |
| `backend/.venv/Scripts/basedpyright.exe -p backend/pyrightconfig.json backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/__init__.py backend/app/config/setting.py` | PASS: 0 errors, 0 warnings, 0 notes |
| AST inspection of the MCP package and MCP settings | PASS: service calls are exactly `detail`, `page`; no outbound client imports; exactly three MCP settings |
| `git diff --check -- <task-scoped paths>` | PASS: no whitespace errors |
| Local Markdown target verification for the two current guides | PASS: 17 local links, 0 missing |

The 20 MCP tests include 17 protocol/auth/privacy/denial tests and 3 actual in-memory SQLite query/data-scope/unchanged-row tests. Both official legacy `ClientSession` and modern `Client(mode='2026-07-28')` HTTP transports are exercised; the modern test calls all four queries. Total freshly rerun tests: 23; none skipped. Dependency manifests and the lockfile were unchanged by this scope correction, so dependency resolution was not redundantly rerun.

## Acceptance Mapping

| Criterion | Current evidence |
| --- | --- |
| AC1: source-backed Server analysis, separate unimplemented client role | Updated source-analysis and usage guides, verified local links |
| AC2: initialization/discovery and all four queries | Official legacy/modern SDK HTTP tests |
| AC3: exact four-tool boundary and query/detail permissions | Catalog annotation checks, permission changes, hidden/direct-call denial |
| AC4: authentication and data access | Actual JWT/fakeredis checks and existing services against SQLite |
| AC5: permanent mutation denial and no runtime client | Ordinary/superuser/stale-setting denial, unchanged row snapshots, static source inspection |
| AC6: credential/session privacy | Safe output models, invalid/malformed input, fixed errors, log checks, storage-privacy regressions |
| AC7: focused checks and accurate configuration/docs | Fresh commands above, three-setting/four-query documentation/spec review |

## Verification Limits

No full business application startup, production database/Redis access, browser activity, vendor upload, quote execution, or deployed-proxy test was performed. SQLite/fakeredis and ASGI evidence do not claim PostgreSQL, production Redis, or live deployment acceptance. Enabling `MCP_ENABLED` and configuring the deployed Host/Origin remain documented operator configuration steps.

## Session Continuation Verification

Rechecked on 2026-10-24 at approximately 20:50 Asia/Shanghai after restoring the prior conversation's final query-only requirements. The existing implementation already satisfies the requested scope; no product-code change was necessary. Preserved all unrelated uncommitted account, drawing, login, and Agent work.

| Command | Fresh continuation result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/mcp -p 'test_*.py'` | PASS: 20 tests in 6.852 seconds; none skipped |
| `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/login -p 'test_storage_privacy.py'` | PASS: 3 tests in 0.210 seconds; none skipped |
| `backend/.venv/Scripts/ruff.exe check backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/__init__.py backend/app/config/setting.py` | PASS: all checks passed |
| `backend/.venv/Scripts/basedpyright.exe -p backend/pyrightconfig.json backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/__init__.py backend/app/config/setting.py` | PASS: 0 errors, 0 warnings, 0 notes |
| `git diff --check -- backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/__init__.py backend/app/config/setting.py backend/pyproject.toml backend/requirements/base.txt backend/uv.lock backend/README.md docs/cnc-mcp-server.md docs/weknora-mcp-analysis.md .trellis/spec/backend/cnc-mcp.md .trellis/tasks/10-24-cnc-management-mcp` | PASS: no whitespace errors; Git emitted only its existing LF-to-CRLF lockfile notice |

Source and integration review confirmed the fixed four-query catalog, `page`/`detail` service adapters, exactly three MCP settings, request-local authentication and permission checks, deferred SDK loading, host lifecycle, direct/prefixed paths, safe account serialization, and absence of an application MCP-client integration. Mutation denial remains covered for ordinary users, superusers, and stale write-enable configuration. The documentation and backend spec continue to describe that same boundary.

No task-scoped finding remains. This continuation performed no dependency installation or resolution, commit, archive, production startup, external platform operation, or live deployment test. The verification limits above still apply.

## Development Enablement and Connection Handoff Review

Reviewed the authorized follow-up limited to `backend/env/.env.dev`, `backend/env/.env.example`, `docs/cnc-mcp-server.md`, and `docs/cnc-mcp-connection.example.json`. Corrected one documentation claim: successful refresh rotation does not itself invalidate an existing access token in the shared `_authenticate` path; expiration follows the configured sliding-session policy. The guide now describes current authentication expiry/revocation and updating stored tokens after refresh without claiming immediate old-access-token invalidation.

- Read-only Settings inspection (`ENVIRONMENT=dev`, importing `app.config.setting.settings`) printed only `ENVIRONMENT`, `SERVER_HOST`, `SERVER_PORT`, `ROOT_PATH`, and the three MCP settings: dev, localhost, 10006, `/api/v1`, enabled, and unchanged loopback-only Host/Origin lists.
- PowerShell line checks confirmed exactly one active `MCP_ENABLED=true` in the local development file and no active MCP Host/Origin overrides. The checked-in template keeps `MCP_ENABLED=false`; deployment overrides remain comments.
- `ConvertFrom-Json -ErrorAction Stop` validated the connection sample and asserted the local URL and exact placeholder Authorization value. No application token was read or added.
- PowerShell 7 `[System.Management.Automation.Language.Parser]::ParseInput` accepted all four PowerShell code blocks. Local Markdown target checks resolved both links in the connection guide.
- Frontend `utils/auth/index.ts`, `store/modules/user.store.ts`, and `api/module_system/auth.ts`, plus backend authentication controller/service, confirm the documented token storage, login endpoint, and response field.
- `git diff --check -- backend/env/.env.example docs/cnc-mcp-server.md docs/cnc-mcp-connection.example.json` passed. No new behavior tests were necessary or run for these configuration/documentation changes. No backend restart, database/Redis connection, dependency change, commit, or archive was performed.

No unresolved finding remains for this follow-up. Enabling the ignored local environment file takes effect on the next backend start/restart; a live authenticated client connection was not claimed.

## Chinese Interview Artifact Review

Reviewed only `docs/cnc-mcp-interview-guide.md` against the existing MCP adapters, shared authentication, CRUD data-scope path, and prior verification record. Made three narrow wording fixes: the sequence diagram now distinguishes `Service(auth, db)` construction from `page` arguments; action-permission revocation guidance no longer implies ordinary token refresh recomputes the Redis permission set; Q15 now clearly scopes future revocation/rotation work to new machine credentials and acknowledges existing user-session revocation and refresh-token rotation.

Artifact checks passed: 12 relative code links resolve, all three fenced blocks are balanced, and both JSON snippets parse with `ConvertFrom-Json -ErrorAction Stop`. Source-reference attribution checks found no named reference project or adaptation claim. `git diff --check -- docs/cnc-mcp-interview-guide.md` passed. The document distinguishes stateless MCP transport from Redis login sessions, describes four query tools and no outbound client, separates Redis action permissions from database role data scopes, qualifies sliding expiry, and presents the 23 passing tests as prior evidence. No production, performance, or vendor acceptance is claimed. No behavior tests, dependencies, restarts, database access, commits, or archiving were performed for this documentation review.
