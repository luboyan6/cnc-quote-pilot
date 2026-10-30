# Implementation Plan

## Authorization and Planning

- [x] User requested implementation limited to `cnc_account` and `cnc_part` and explicitly approved task creation and continued implementation.
- [x] Inspect WeKnora's renamed feature document and current embedded Go server.
- [x] Persist requirements, adaptation design, and ordered implementation plan.
- [x] Curate implementation/check context and activate task after artifact review.
- [x] User narrowed this same task to four account/drawing queries and explicitly excluded MCP-client functionality; implementation is authorized by that correction.

## Ordered Work

1. Reduce `backend/app/modules/cnc/mcp/` to the fixed four query tools and existing query/output schema adapters. Delete mutation argument classes, imports, execution branches and write-related instructions.
2. Remove `MCP_ALLOW_WRITES` and all write-gating logic, retaining current authentication, query/detail permissions, data scopes, transport security, lifecycle and private errors.
3. Preserve working exact-route and root-path integration, dependency manifests/lock, and unrelated dirty workspace work. No outbound MCP client or Agent integration is added.
4. Update isolated protocol and real SQLite tests for all four queries and unconditional mutation denial, keeping meaningful auth/permission/privacy/lifecycle/path coverage.
5. Rewrite the source analysis adaptation, usage guide, backend spec and commit plan to reflect permanent query-only Server functionality.
6. Run focused checks, dispatch an independent Trellis check agent, fix verified findings, and record the final validation evidence.
7. Capture the MCP contract in `.trellis/spec/backend/` and finish only this task without committing unrelated workspace work.

## Ownership

- Main session: planning, WeKnora analysis, operator guide, spec update, coordination, and final integration review.
- Trellis implement sub-agent: new MCP code/tests, minimal backend integration/settings, SDK dependency manifests and lockfile.
- Trellis check sub-agent: independent review against artifacts; fix verified task-scoped issues and run focused verification.

All participants share the dirty workspace. Never revert unrelated edits. Do not implement or review by spawning nested agents.

## Validation Commands

Resolve/install the current `mcp>=2,<3` dependency with `uv` using the backend environment, preserving other locked dependency versions as far as possible. Run focused checks with the actual installed SDK, for example:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/mcp -p 'test_*.py'
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/login -p 'test_account_service.py'
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/cnc/login -p 'test_http.py'
backend/.venv/Scripts/ruff.exe check backend/app/modules/cnc/mcp backend/tests/cnc/mcp backend/app/__init__.py backend/app/config/setting.py
```

Use a targeted type checker when available. Record commands, counts, skips, and limitations in a task check result. Run broader tests only when findings justify them.

## Rollback and Review Gates

- Disable MCP by configuration before removing its integration if rollback is required.
- Keep service behavior and schemas authoritative; no speculative account/part refactor.
- Exactly four query tools; no dormant or configurable mutation surface.
- Direct mutation calls must fail for superusers and ordinary users without changing business rows.
- SDK clients may appear in tests only; no outbound MCP-client application feature.
- Review changes relative to the starting dirty workspace; no automatic broad commit.

## Completion Evidence

The query-only implementation and independent review are complete. Fresh evidence in `check-result.md` and `research/implementation-check.md` covers 23 passing tests (20 MCP and 3 storage privacy), clean Ruff/basedpyright, four fixed query adapters, exactly three MCP settings, no outbound MCP-client feature, 17 valid documentation links, and clean whitespace checks. No product-code issue remains.

The earlier eleven-tool commit question is superseded by the scope correction; the revised `commit-plan.md` reflects the four queries. No Git commit is authorized or performed. Preserve unrelated work; commit/archive bookkeeping remains separate from the completed feature and verification.

## Connection Handoff Follow-up

The user subsequently requested enabling MCP and detailed instructions for other projects. Set only the local ignored `backend/env/.env.dev` flag to `MCP_ENABLED=true`; keep code/template defaults disabled and retain the current `localhost:10006` listener and loopback transport allowlists. Add an environment-template section, a placeholder-only connection JSON, and a walkthrough covering startup, the application's access token, remote Streamable HTTP setup, discovery, LAN/HTTPS reachability, and token lifecycle. Configuration parsing, example syntax, local links, and scoped whitespace checks are sufficient for this configuration/documentation follow-up. Running processes apply the flag after startup/restart; no production rollout, network exposure change, or long-lived machine-token feature is included.
