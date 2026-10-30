# T1 final quality review — 2026-10-28

## Gate

The combined regression passed after the Windows SQLite fixture and owner cleanup repairs. That run started before the final release-wait and permission-revoked cancellation changes; affected local paths subsequently passed targeted regression and static checks. The final isolated PostgreSQL rerun passed. A shutdown-timeout resource-lifecycle boundary remains unresolved as described below.

Isolated PostgreSQL concurrency and migration checks passed. Live provider and deployment acceptance remain **not run**, so this is not full B-AC01–08 production acceptance.

## Fixed findings

- Restored exact Xometry server identity verification; an account header cannot replace missing/mismatched identity or override explicit guest/upload sign-in signals. Submission reconciliation follows the existing three-attempt/eight-second contract without repeating credentials.
- Input locator resolution rejects ambiguity. Provider field writes recheck current input/cancellation guards, SDK uploads use frozen bytes, selected accounts use scoped encrypted sessions, and shortcut declarations stop for the existing typed exact-file/version decision.
- Disabled batches reject preview/create while preserving inspection/cancellation. Cancellation uses Item→Batch lock ordering, matching completion.
- Run/Result/Item commit together; shortcut observations stage private candidate/evidence before local persistence retries. Stale staging and mutation claims check owner/token/expiry, and no retry replays remote work.
- Lifespan cleanup uses AsyncExitStack so dispatcher start/stop, MCP, serving, or login cleanup errors still run remaining cleanup callbacks. Unsupported worker topology fails before initializing resources.
- Line-scoped amounts now populate total_amount when the provider does not also set it explicitly. Nullable unknown currency passes the existing result output schema instead of failing result list/detail validation or becoming CNY.
- Mechanical scoped lint/type issues were fixed in result declarations and isolated test model/module mappings.
- Every dispatcher tick scans expired claims before heartbeat, including claims still live at startup that expire later. Renewals, release-wait and failure settlement cannot revive or alter an expired owner; a lost Run remains RECONCILING without re-execution.
- LoginManager keeps an owner discoverable until quote finalization finishes. Concurrent close/shutdown calls share cleanup, including pre-start cancellation, so shutdown and a new start wait for final persistence and lease cleanup.
- A persisted batch cancellation can stop only the matching local Item/Run/claim owner and token, even after the actor loses execution permission. A missing local owner is retained as RECONCILING; mismatched claims never stop another owner. Staged observations are persisted before cancellation where possible, and claimed Intents are preserved.
- Dispatcher shutdown no longer requires the actor's execution permissions to join its own local activities. It also waits for terminal activities whose task is still releasing resources, without cancelling their cleanup. It waits at most 35 seconds plus a bounded reconciliation write; timeout records `BATCH_SHUTDOWN_UNSETTLED` when possible and raises a fixed failure. The unresolved cleanup task may outlive the timeout; resource-order implications are explicitly listed below.
- JLC shortcut execution now stops before starting a browser or uploading because existing evidence does not establish reliable same-part post-save parameter readback. The result projection separately refuses missing, incomplete or mismatched effective values instead of copying requested values. This affects both single and batch JLC shortcuts until a source-reviewed readback is implemented and verified; an actionable Chinese notice is shown.
- Windows teardown diagnostics found a cancelled aiosqlite SELECT cursor still referenced by `_execute` frames after its connection and worker thread had closed. `sqlite3_close_v2` retains the database file while that cursor's statement remains active. The isolated fixture tracks only its own connection's cursors and closes them before the connection; a regression keeps an unconsumed cursor alive and verifies the file can actually be deleted. The existing pool-return timeout remains; no cleanup failure is ignored and no file-deletion retry masks it.
- Actual DynamicRouterRegistry discovery/OpenAPI is exercised; batch routes appear once. Current menu seed contains create/query/detail/cancel permissions in backend/sql/sys_menu.json.

## Verification commands and evidence

All Python commands below ran from backend using the existing .venv; no dependency install, configured database migration, or live remote mutation was performed.

- `.venv/Scripts/python.exe -m pytest tests/cnc/login -q`: **88 passed, 75 subtests passed** (18.07s), after the identity fixes.
- `.venv/Scripts/python.exe -m pytest tests/cnc/batch/test_batch_lifespan.py -q`: **7 passed** (0.51s).
- `.venv/Scripts/python.exe -m pytest tests/cnc/batch/test_batch_http.py -q`: **2 passed** (1.18s), including dynamic discovery.
- First combined `.venv/Scripts/python.exe -m pytest tests/cnc/batch tests/cnc/quote tests/cnc/login -q`: **234 passed, 167 subtests passed** (208.76s).
- After line amount / null currency / stale staging additions: `.venv/Scripts/python.exe -m pytest tests/cnc/batch/test_batch_service.py tests/cnc/batch/test_batch_http.py -q`: **14 passed** (17.99s).
- Final combined rerun in the preceding session: **234 passed, 167 subtests passed, 1 failed** (223.15s). The sole failure was teardown of XometryOwnerTests.test_known_different_frozen_file_can_start_without_erasing_prior_claim: Windows WinError32 deleting the temporary SQLite file. Business assertions passed; this failed rerun was not treated as green.
- Continuation rerun before the cursor and owner fixes: **234 passed, 167 subtests passed, 1 failed** (316.03s), repeating the same Windows SQLite teardown failure. Subsequent targeted fixture and affected owner tests: **2 passed**; targeted batch business tests including expiry recovery: **15 passed**; provider isolation/readback tests: **31 passed**.
- Combined `.venv/Scripts/python.exe -m pytest tests/cnc/batch tests/cnc/quote tests/cnc/login -q` after the SQLite/owner and JLC fixes: **247 passed, 19 skipped, 167 subtests passed** (350.29s). The 19 opt-in PostgreSQL cases skipped without a DSN; three SQLAlchemy warnings report fixture table re-registration during test collection. This run began before the later release-wait/cancellation changes.
- Against an isolated temporary PostgreSQL 16.8 instance, with `CNC_BATCH_PG_TEST_DSN` explicitly set to its test database: `.venv/Scripts/python.exe -m pytest tests/cnc/batch/test_batch_postgres.py -q --tb=short` **19 passed** (49.76s). Cases cover admission/capacity, `SKIP LOCKED`, same-config contention, cancellation and duplicate completion, expiry recovery, and real migration/history uniqueness. The normal suite skips these tests without that explicit DSN; no configured business database was used.
- Subsequent isolated PostgreSQL checks: the lock-wait expiry test passed; a later whole-file run passed **24 tests** (27.43s); two later owner-finish/shutdown cases passed (**2 passed**, 2.51s), followed by the bounded shutdown timeout case (**1 passed**, 1.35s). A whole-file rerun then passed **27 tests** (30.66s); after the terminal-owner cleanup correction the final whole-file rerun passed **28 tests** (38.53s).
- After the final cancellation, staged-result and shutdown changes, targeted batch cancellation/owner/shutdown cases passed **9 tests** (13 deselected, 12.35s). The quote owner, Xometry owner, provider isolation, login runtime and batch lifespan selection passed **84 tests, 4 subtests** (97.41s). Relevant scoped Ruff, format and basedpyright checks passed after those changes.
- A subsequent terminal-owner cleanup correction passed the shutdown-focused tests: **3 passed, 20 deselected** (3.71s), plus scoped Ruff, format and basedpyright checks. Its isolated PostgreSQL case passed separately (**1 passed**, 1.48s) and in the final whole-file run.
- Frontend `pnpm exec vitest run src/__tests__/cnc-part-config-auto-quote.spec.ts`: **37 passed**. Changed-file ESLint/Prettier and `pnpm run type-check` pass; `pnpm exec vite build --mode production --outDir ../../scratch/t1-frontend-verification-01a18149 --emptyOutDir false` passed after the JLC notice was added.
- Scoped `ruff check --no-fix`: pass.
- Scoped `ruff format --check`: **40 files already formatted**.
- Scoped `basedpyright`: **0 errors, 0 warnings, 0 notes**.
- Wider `.venv/Scripts/ruff.exe check --no-fix --output-format json app/modules/cnc/quote` still reports **74 pre-existing issues**, restricted to untouched jlc_cnc_params_loader.py (36) and xometry_cnc_params_loader.py (38). These are outside this task's changes; no blanket formatting or cleanup was applied.
- Whole-workspace `git diff --check` fails on pre-existing whitespace in `backend/app/plugin/module_cnc/cnc_account/model.py` (lines 112/122/132/142) and `backend/app/plugin/module_cnc/cnc_part_config/service.py` (lines 112/119 and an EOF blank line). These unrelated existing edits were preserved.

The exact static-check path arguments were:

~~~text
app/modules/cnc/batch
app/modules/cnc/quote/contracts.py
app/modules/cnc/quote/repository.py
app/modules/cnc/quote/service.py
app/modules/cnc/quote/runner.py
app/modules/cnc/quote/jlc_quote_service.py
app/modules/cnc/quote/xometry_quote_service.py
app/modules/cnc/quote/instant.py
app/modules/cnc/login/providers.py
app/modules/cnc/login/runtime.py
app/plugin/module_cnc/cnc_quote
app/plugin/module_cnc/cnc_quote_batch
app/plugin/module_cnc/cnc_quote_batch_item
app/plugin/module_cnc/cnc_quote_result/model.py
app/plugin/module_cnc/cnc_quote_result/schema.py
app/__init__.py
app/config/setting.py
tests/cnc/batch
tests/cnc/quote/_quote_support.py
tests/cnc/quote/test_quote_migration.py
tests/cnc/quote/test_provider_isolation.py
tests/cnc/login/test_providers.py
tests/cnc/login/test_xometry_readiness.py
tests/cnc/login/test_runtime.py
tests/cnc/quote/test_quote_support.py
~~~

Ruff checks additionally include `app/alembic/versions/2026_10_28_1400_d4b9a2f61028.py`; basedpyright excludes migration scripts per the repository configuration.

Reproduce scoped commands by passing the path list above to:
~~~powershell
.venv/Scripts/ruff.exe check --no-fix <paths> app/alembic/versions/2026_10_28_1400_d4b9a2f61028.py
.venv/Scripts/ruff.exe format --check <paths> app/alembic/versions/2026_10_28_1400_d4b9a2f61028.py
.venv/Scripts/basedpyright.exe <paths>
~~~

## Acceptance assessment

| Criterion | Local evidence | Outstanding boundary |
| --- | --- | --- |
| B-AC01 | Four configs over two parts/platforms × 1/2/5 produce exactly twelve matching preview/create items | No live browser matrix |
| B-AC02 | SQLite and isolated PostgreSQL concurrent admission, replay/conflict and capacity cases leave no partial batch | Deployment-environment acceptance |
| B-AC03 | Source revision/file/account revalidation, frozen quantities, original quantity unchanged | Deployment file/permission behavior still needs integration acceptance |
| B-AC04 | Account fenced lease and config active-run protection; PostgreSQL `SKIP LOCKED` and same-config contention; failed item does not stop subsequent dispatcher work | Real browser resources and deployment concurrency |
| B-AC05 | Persistent cancellation, no Run/browser for pending cancellation; dispatcher advances independently of status reads; lifespan cleanup regressions | Live active-owner cancellation/refresh acceptance |
| B-AC06 | Attempt uniqueness, stale write fencing, duplicate completion, failed Result insert rollback, staged local-only persistence retry; PostgreSQL duplicate completion and migration uniqueness | Deployment integration |
| B-AC07 | HTTP/current RBAC, actor ownership, selected account/registry source, scoped encrypted state, no fixed platform 1/2 routing | Both real selected-account provider executions |
| B-AC08 | Local regressions and dynamic route registration; estimate/review nature retained | JLC shortcut is stopped pending effective readback; Xometry managed binding remains unverified/inactive; live acceptance incomplete |

## Explicit remaining limitations

- PostgreSQL evidence comes from a disposable local 16.8 cluster and isolated test schemas. It does not establish live provider or deployment-environment acceptance.
- No real provider login, STEP upload, parameter save, declaration, or quote was executed. Xometry's reviewed managed adapter remains deliberately unavailable until exact-file/current-result activation evidence exists.
- JLC single and batch shortcut execution intentionally stops before upload with `JLC_EFFECTIVE_PARAMETERS_UNVERIFIED`: recovery requires reviewed same-file, same-part, post-save material, quantity, finish and tolerance readback plus current price correlation, followed by separate live acceptance.
- If a local cleanup task does not settle within the 35-second shutdown budget, shutdown reports failure and attempts to fence its Run, but the task may still be running when the existing AsyncExitStack continues disposing independent resources, including the DB engine. This extreme path is not claimed to guarantee complete resource convergence; it requires a separately verified lifecycle design.
- Complex retry/backoff and lost-owner reconciliation belong to T2. T1 releases expired claims without a Run and preserves owned remote runs as RECONCILING without replaying side effects.
- Existing results stats/history still contain old currency grouping/fallback and comparison semantics; provider screenshots still use the historical public static location. These pre-existing T4 concerns are not claimed as fixed by T1. The nullable list/detail projection was fixed solely to keep this task's persisted failure records readable.
- New feature remains disabled by default. Deployment must review/apply migration d4b9a2f61028 (parent b76d50ea5d8f), register/grant menu permissions using existing deployment mechanisms, and explicitly enable CNC_BATCH_ENABLED with WORKERS=1.
- No commit or archive was performed. Existing unrelated dirty work was preserved.

## Session scope

Implementation owners changed the batch modules and plugin models/routes, migration, quote shared execution/repository/result integration, provider isolation, login lease handoff, feature settings/environment example, menu seed, and the related regression fixtures/tests. The static path list above identifies every Python module reviewed for this task; backend/env/.env.example and backend/sql/sys_menu.json were also read. Specs/task documents are coordinated by the main session.

Reviewer edits in this session:
- backend/app/modules/cnc/login/providers.py
- backend/tests/cnc/login/test_providers.py
- backend/tests/cnc/login/test_xometry_readiness.py
- backend/app/__init__.py
- backend/tests/cnc/batch/test_batch_lifespan.py
- backend/tests/cnc/batch/test_batch_http.py
- backend/tests/cnc/batch/test_batch_service.py
- backend/tests/cnc/batch/test_batch_migration.py
- backend/tests/cnc/quote/_quote_support.py
- backend/tests/cnc/quote/test_quote_migration.py
- backend/app/modules/cnc/quote/repository.py (line amount projection only; other changes belong to implementer)
- backend/app/plugin/module_cnc/cnc_quote_result/model.py (mechanical lint/format)
- backend/app/plugin/module_cnc/cnc_quote_result/schema.py (unknown currency/scope compatibility and mechanical format)
- backend/app/config/setting.py (single trailing comma required by formatter)
- .trellis/tasks/10-28-cnc-monitor-01-batch/check-report.md

Continuation reviewer edits:
- backend/app/modules/cnc/batch/repository.py
- backend/app/modules/cnc/batch/dispatcher.py
- backend/app/modules/cnc/login/runtime.py
- backend/app/modules/cnc/quote/jlc_quote_service.py
- backend/app/modules/cnc/quote/service.py
- backend/app/modules/cnc/quote/runner.py
- backend/tests/cnc/batch/test_batch_service.py
- backend/tests/cnc/login/test_runtime.py
- backend/tests/cnc/quote/_quote_support.py
- backend/tests/cnc/quote/test_quote_support.py
- backend/tests/cnc/quote/test_provider_isolation.py
- frontend/web/src/views/module_cnc/cnc_part_config/quoteMessages.ts
- frontend/web/src/__tests__/cnc-part-config-auto-quote.spec.ts
- .trellis/tasks/10-28-cnc-monitor-01-batch/check-report.md

