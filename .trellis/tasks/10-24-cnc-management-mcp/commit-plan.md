# Proposed Commit Plan

Status: four-query Server-only implementation and independent review complete; 23 tests and focused quality checks passed. The prior eleven-tool commit question is superseded; no commit approval has been received.

## Work Commit

Proposed subject: `feat(cnc): 增加账号与图纸查询 MCP Server`

Include only this task's changes:

- `backend/app/modules/cnc/mcp/{__init__,server,tools}.py`
- `backend/tests/cnc/mcp/{test_http,test_database}.py`
- `backend/app/__init__.py`: additive MCP route/lifespan integration.
- `backend/app/config/setting.py`: only `MCP_ENABLED`, `MCP_ALLOWED_HOSTS`, and `MCP_ALLOWED_ORIGINS`; no write-enable option.
- `backend/pyproject.toml`: only the new `mcp` core dependency.
- `backend/requirements/base.txt`: matching MCP dependency.
- `backend/uv.lock`: MCP dependency closure and required shared-version changes only; retain unrelated Agent changes in the working tree.
- `backend/README.md`: two documentation links.
- `docs/cnc-mcp-server.md` and `docs/weknora-mcp-analysis.md`.
- `.trellis/spec/backend/cnc-mcp.md` and only its new row in the backend spec index.

Shared files require selected hunks or a task-only staged version. Do not stage the whole settings, project manifest, lockfile, or spec index if that would include prior Agent work. The task must be reviewed as a coherent commit, with no amend or remote push.

## Existing Work Excluded

The workspace already contained account credential/browser changes, drawing annotations/changes, optional local-Agent dependencies, Agent modules/tests/scripts, an account migration, JLC skill edits, previous task research, and frontend account changes before this task began. Leave those edits intact and outside this commit, including:

- `.agents/skills/cnc-jlc-quote/` edits.
- `.trellis/spec/backend/ai-agent.md` and its existing index row.
- `.trellis/tasks/10-23-cnc-part-config-auto-quote/` edits and the five `10-24-deerflow-*` task directories.
- `backend/app/modules/cnc/login/{providers,repository}.py` edits.
- Existing modifications under `backend/app/plugin/module_cnc/cnc_account/` and `cnc_part/`.
- Existing `AI_AGENT_*` settings, the `agent` optional dependency group, and its lockfile entries.
- `backend/app/modules/ai/agent/`, `backend/tests/ai/`, `backend/scripts/`, and `backend/requirements/agent.txt`.
- The existing account Alembic migration and password-migration test.
- Existing account login/provider/repository tests and account frontend files.
- Existing `docs/cnc-account-login.md` and `docs/ai_agent_langgraph_migration_analysis.md` changes.

## Bookkeeping After Work Commit

After the user approves the work commit and it succeeds, the normal Trellis finish flow may archive this task and record its journal in separate bookkeeping commits. No other active task is included. If the user prefers manual commits, leave the validated changes and this task ready for that handoff.
