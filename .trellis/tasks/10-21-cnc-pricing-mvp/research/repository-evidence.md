# Repository evidence for CNC MVP

Inspected on 2026-10-21. This is repository research, not proof of application startup or live-platform quoting.

## Existing integration points

| Evidence | Finding | Implementation consequence |
|---|---|---|
| backend/app/api/v1/routers.py:32 | DOMAIN_CONTROLLERS aggregates business domains; no CNC controllers | Add CNC controllers to the existing registry; do not build a second app |
| backend/app/__init__.py:21 | Existing lifespan owns startup and shutdown; line 40 initializes SchedulerUtil | Register the bounded CNC consumer here after lifecycle review; no import-time browser startup |
| backend/app/core/ap_scheduler.py:65 | Existing scheduler leadership lock | Reuse scheduler ownership; CNC dispatch only enqueues durable tasks |
| backend/app/core/ap_scheduler.py:104 | Builtin handler namespace and allowlist already exist | Use a registered builtin dispatcher; do not accept arbitrary task code |
| backend/app/core/base_model.py:42 | ModelMixin has an integer primary key and separate uuid | SRS proposes UUID CNC IDs; review base-class/CRUD compatibility explicitly before adopting it |
| backend/app/modules/system/user/model.py:65 | Existing user table is sys_user | User foreign keys stay compatible with existing integer IDs |
| backend/app/core/dependencies.py:192 | AuthPermission implements existing permission checks | Reuse endpoint authorization and add object-level account/file/result checks |
| backend/app/common/response.py:47 | ResponseSchema has code/msg/data/status_code/success | Keep envelope and existing authentication semantics |
| backend/app/core/router_class.py:16 | Sensitive-key redaction exists for operation logs | Review Cookie/session/credential coverage; test new payloads rather than assuming full protection |
| backend/app/config/setting.py | DATA_ENCRYPTION_KEY and rotation settings already exist | Inspect existing encryption helpers before creating a second key-management mechanism |
| backend/tests/conftest.py | Tests use temporary SQLite and mocked Redis | Separate offline contract tests from live-platform acceptance |
| frontend/web/package.json | type-check/test/build scripts and Vue/Element Plus/ECharts are available | Extend Web admin; no new frontend framework |
| .gitignore | Existing ignored env files and backend uploads | New private CNC data must also be ignored and never served publicly |

## Search results and limits

- Searching backend/app and frontend/web/src found no CNC/rapiddirect/xometry implementation.
- Repository file discovery found no STEP/STP samples.
- backend/.venv, frontend/web/node_modules and backend/env/.env.dev exist. Existence is not a successful startup or DB connectivity test.
- Private credentials, cookies and environment secrets were not collected into task files.
- Backend/frontend spec indexes are still templates; do not fabricate completed project standards.
- Existing user changes: backend/README.md, frontend/app/.env.development, untracked project tooling and the source SRS. Preserve them.

## Deep Agents migration constraints (2026-10-21 supplement)

- backend/pyproject.toml declares Python >=3.12 and agno==2.5.8. backend/app/modules/ai/chat/service.py imports AgnoFactory for existing chat. CNC will use a separate Deep Agents factory; this planning request does not migrate the shared chat module.
- The same chat service stores encrypted user model configs in Redis with `_AI_MODEL_TTL = 604800`. CNC schedules must pin a persistent server-side model configuration reference and must not depend on the user's current active selection or this expiring cache.
- backend/app/config/setting.py:101 declares mysql/postgres/sqlite support with a mysql default. This is configuration code, not confirmation of the active runtime database. A PostgreSQL checkpoint implementation cannot be used against MySQL without a compatible storage design.
- Current SDK release/API evidence and unverified integration work are recorded in deepagents-2026-10-21.md; the actual CNC runtime contract is ../agent-design.md. No package installation, CNC source implementation or live model call is implied by these planning updates.

## Research still required before implementation

1. Confirm the actual non-sensitive runtime DB type and existing crypto helper interface, without logging secrets.
2. Inspect model discovery, migrations, permissions and existing upload conventions in the owning subtask.
3. Verify user-authorized platform account and sample references.
4. Capture real selectors and material options only in authorized live verification.

No findings above imply a real quote, browser session, migration or platform adapter already works.
