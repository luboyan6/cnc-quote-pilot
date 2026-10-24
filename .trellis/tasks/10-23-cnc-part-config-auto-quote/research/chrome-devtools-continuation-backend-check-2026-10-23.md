# Backend continuation review — historical strict DNS candidate — 2026-10-23

## Scope and result

Reused the existing task and dirty `dev` worktree based on `93dff6ec`. Loaded the native check context, saved full hook output, task PRD/design/implementation plan, applicable specs, previous frontend/backend reports, handoff, and the two focused repair reports. This reviewer changed no production code, tests, assertions or timeout budgets. This report is the only deliverable in tracked/task scope.

The complete independent Windows suites on the reviewed candidate sources discovered **201 test methods: 188 passed, 13 skipped, zero failures/errors**. All four processes exited **0**. The unchanged symlink method additionally executed successfully on the already installed Linux runner: **1 passed, zero skips, exit 0**. Scoped production and this session's file-boundary test type checks passed. Wider pre-existing test-fixture typing and a generated controller lint baseline remain reported below.

**These strict-DNS semantics are superseded by an explicit user decision.** The results below describe the historical strict candidate `BrowserPolicy.resolve` at SHA-256 `5EA9F6BA61C121D7C9D01E685426CE7B6C492237651128D3D188B11B4046BAAF`, which rejects the complete answer set if any address is unsafe. During this review, the coordinator found an earlier Antigravity session explicitly describing safe-answer filtering as a login fix, followed by a user message requesting testing after a manual restart. The user then explicitly selected: “保留 Antigravity 的地址过滤方案；同步调整契约和验证”. The implementation worker is updating the resolver and DNS tests to that approved contract while preserving `.setp` additions; the coordinator owns spec/design updates. This record does not verify or approve the later filtering sources. This reviewer made no policy/test change and will wait for the worker to settle before the coordinator's requested final browser/login/static verification. The `.setp` repair and quote/upload results are independent of that DNS choice.

The production `resolve_quote_adapter` still returns `None`. Both platforms remain unaccepted for real linked-file upload, effective parameter readback and same-run price. Generic fixtures, including their `12.30` value, are synthetic and cannot satisfy AC-03/04/08. No provider request, Chrome operation, service restart, DNS/proxy change, migration, dependency installation, business-database edit, commit or task archive was performed by this reviewer.

## Findings verified

### STEP alias crosses the actual upload/freeze/revalidation boundary

Reviewed `browser/files.py`, `quote/repository.py`, the existing upload service/utility and the new `test_step_file_boundary.py` together. `STEP_SUFFIXES` is immutable and consumed by the metadata, resolved-path and shared verifier checks. `.step`, `.stp` and historical `.setp` are accepted case-insensitively, including dotted metadata, without renaming the stored display file. `StepPayload.sdk_payload` continues using private `part.step` and the already verified byte buffer.

The four new quote methods use the actual upload service/utility and independent temporary SQLite storage. They cover lower/uppercase aliases, frozen size/hash/bytes, same-size disk tampering, unchanged SDK buffer after disk changes, and empty/PDF/unframed/truncated or unsupported-suffix rejection. Upload authorization, rejected status, trusted root, actual size, resource/provider limits and SHA-256 checks remain in place. The added shared-file method covers both alias cases and SDK payload identity. The Part 21 fixture is framing-valid and contains a point; these tests do not prove valid solid geometry or provider parsing.

### Strict candidate DNS and optional-resource denial

Reviewed the historical candidate's complete deduplicated answer-set validation, exact hostname gate, fixed proxy error conversion, request observation and route guards. In this candidate any unsafe answer rejects the connection, including mixed public/private/special answers and explicit IPv6 site-local addresses. Public addresses are returned only after the complete set passes. This candidate is content-equivalent to the committed policy, but the user has now expressly chosen safe-answer filtering instead. The strict behavior described in this paragraph is historical, not the approved final contract.

The original browser suite now passes its unchanged mixed-DNS and local SOCKS denial tests; the former 12 assertion failures and associated egress cleanup error did not recur. Optional analytics/QR hosts remain separate exact denies: no DNS/connection permission is granted, subresources/subframes are aborted, and top-level navigation or unknown destinations still stop. Added provider business-file hosts are exact allowed hosts rather than platform entry aliases. This verifies policy/fixture behavior, not real public DNS or provider connectivity.

### Fixed HTTP file stop remains a safe business response

`quote/routes.py::_action` catches both `LoginError` and `BrowserStop`, converting only their fixed reason to the private business exception. The full quote run includes the existing regression covering start/status/resume and HTTP 400 `file_invalid`, without global exception-stack/error logging. Strict input, privacy, both update permissions, private JPEG headers and materialized OpenAPI route uniqueness also pass. Expected synthetic HTTP 400/403/500 responses in these tests are assertions, not failed suite results.

### Owner, permission, intent and result invariants

Reviewed `authorization.py`, quote repository/service/runner, persistent models/migration, the login owner integration and their complete isolated tests:

- Current user/role/menu permission reload, cached-superuser demotion, creator/platform/enabled checks and actor-private run lookup remain enforced. Ordinary account-page activity cannot operate a quote-owned browser.
- The owner task retains the Page, performs bounded stages and renews the existing fenced account lease. Human resume during an active quote verifies identity without navigating away from the uploaded item.
- Frozen buffers and input revisions are rechecked before mutation. Run/request and intent uniqueness use independent real transactions; an intent commits before granting a mutation.
- Slow parsing reconciles read-only. Cancellation, confirmation/storage failure, restart/orphan handling and repeated requests do not authorize blind re-upload; claimed/uncertain evidence is retained.
- Exact shared quote validation precedes committed result publication. Reference estimates and pending review use distinct branches; result-store failure cannot publish `QUOTED`.
- The isolated quote migration round trip compares table columns and uniqueness to the actual production models. It does not exercise the business database or prove a deployed PostgreSQL migration/lease integration.

These are code and isolated/synthetic integration conclusions. They do not establish real account authentication/state reuse, current provider controls, geometry, parameter equivalence or price freshness.

## Complete isolated verification

Commands ran from `E:/AIWorkspace/cnc-quote-pilot/backend`, using the installed environment and independent unittest discovery. They do not import the full application's pytest DB/Redis fixture workflow. Separate processes use temporary files/SQLite transactions and local test sockets.

| Exact test command | Discovered | Passed | Skipped | Duration | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p 'test_*.py' -q` | 95 | 82 | 13 | 1.972 s | 0 |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/login -p 'test_*.py' -q` | 50 | 50 | 0 | 3.537 s | 0 |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/quote -p 'test_*.py' -q` | 44 | 44 | 0 | 150.713 s | 0 |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/upload -p 'test_*.py' -q` | 12 | 12 | 0 | 0.516 s | 0 |
| **Windows total** | **201** | **188** | **13** | — | **all 0** |

This includes all original tests plus four new quote methods and one shared browser-file method. The existing slow-parser method retains its previously approved 30 s fixture wait; other defaults and all production deadlines remain unchanged. Logs contain expected policy-denial, permission, invalid-upload and asyncio slow-task messages. No assertion, fixture budget or production timeout was changed to obtain these results.

Captured outputs are under the ignored runtime directory: `.trellis/.runtime/continuation-backend-{browser,login,quote,upload}-20261023.log`. The PowerShell wrappers redirect output, retain `$LASTEXITCODE`, print the log tail, and exit with that same code.

### Skips and permitted Linux execution

The Windows browser suite's 13 skips are **12 opt-in managed Chromium synthetic E2E methods** (`CNC_BROWSER_E2E` is not `1`) and the existing symlink-privilege skip. They are not passed checks. The login-specific `browser_e2e.py` is likewise opt-in and is not selected by `test_*.py`; no new login Chromium E2E run is claimed here.

Following the existing [Linux validation record](../../10-21-cnc-browser-reuse/research/linux-validation-2026-10-22.md), the already installed Ubuntu runner executed the original symlink method without changing it, installing anything, or altering WSL/services. Exact command from the workspace root:

```powershell
wsl -d Ubuntu --exec /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-venv/bin/python -B -c 'import hashlib,os,pathlib,sys,unittest; os.environ["ENVIRONMENT"]="dev"; os.chdir("/mnt/e/AIWorkspace/cnc-quote-pilot/backend"); sys.path.insert(0,"tests/cnc/browser"); before=hashlib.sha256(pathlib.Path("tests/cnc/browser/test_policy_files_state.py").read_bytes()).hexdigest(); suite=unittest.defaultTestLoader.loadTestsFromName("test_policy_files_state.FileTests.test_symlink_escape_rejected"); result=unittest.TextTestRunner(verbosity=2).run(suite); after=hashlib.sha256(pathlib.Path("tests/cnc/browser/test_policy_files_state.py").read_bytes()).hexdigest(); print("ACTUAL_EXECUTION",result.testsRun,"SKIPS",len(result.skipped),"TEST_SHA256_UNCHANGED",before==after,before,flush=True); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==1 and not result.skipped and before==after else 1)'
```

Actual result: **Ran 1 test in 0.062 s; OK; exit 0**. Wrapper output:

```text
ACTUAL_EXECUTION 1 SKIPS 0 TEST_SHA256_UNCHANGED True ea8f0dff35a3436bd18b50b4a9468d3e5878632b95920c9ba7955001639c29e4
```

An AST-source comparison also confirmed the symlink method itself is identical to `HEAD`; its source SHA-256 is `f3aad640e96c3f343ffeb50b856f7d816209a3cb2387fda44ac3e9524d8e501e`. The module's whole-file hash differs from the October 22 report because this session added the separate alias method. Windows's skipped execution remains recorded; Linux supplies the separate successful file-boundary evidence. This is not Linux Chromium/deployment acceptance, and the old broader Linux diagnostic failures were not rerun or reclassified.

## Lint and type checks

Commands below ran from `backend`, with no automatic fix flag.

| Exact command | Result |
| --- | --- |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc app/plugin/module_cnc/cnc_quote tests/cnc/quote tests/cnc/upload tests/cnc/browser/test_policy_files_state.py` | All checks passed; exit 0. |
| `.venv/Scripts/ruff.exe check --no-fix app/config/setting.py app/utils/upload_util.py app/modules/common/file/service.py app/alembic/versions/2026_10_23_1600_c9e3a6b72f14.py` | All checks passed; exit 0. |
| The preceding extra-scope Ruff command also including `app/plugin/module_cnc/cnc_part_config/controller.py` | Exit 1: only existing first-line `UP009` UTF-8 encoding header; unchanged baseline, not fixed. |
| `.venv/Scripts/basedpyright.exe app/modules/cnc app/plugin/module_cnc/cnc_quote app/plugin/module_cnc/cnc_part_config/controller.py app/utils/upload_util.py app/modules/common/file/service.py tests/cnc/quote/test_step_file_boundary.py tests/cnc/browser/test_policy_files_state.py` | **0 errors, 0 warnings, 0 notes; exit 0.** Covers production plus this session's new/changed file-boundary tests. |
| Same type command replacing the two selected test files with `tests/cnc/quote tests/cnc/upload tests/cnc/browser/test_policy_files_state.py` | Exit 1: **36 errors, zero warnings/notes**, all in existing task quote fixtures/tests; details below. |

The wider type diagnostic found dynamic cloned SQLAlchemy model/column typing, optional synthetic adapter/callback references, inferred optional event fields, the HTTP fixture's `self.run` name shadowing `TestCase.run`, and a dynamically imported migration's patched `op`. No production or new `.setp` test diagnostic appeared. Per the coordinator's explicit scope instruction, these earlier fixture issues were recorded instead of expanding into a fixture refactor. No suppression, cast, assertion weakening or typing configuration change was introduced. Full logs: `.trellis/.runtime/continuation-backend-{ruff,ruff-extra,types,types-scoped}-20261023.log`.

The prior final frontend **7 suites / 66 tests**, scoped lint and production build are attributed to [the existing frontend report](chrome-devtools-frontend-check-2026-10-23.md) and its source hashes. No frontend source was changed in this review; those commands were not rerun by this reviewer.

## Findings left open

1. **Approved DNS contract requires final verification:** the user chose Antigravity's safe-answer filtering and corresponding contract/test synchronization. The historical strict candidate is green against the old strict assertions; its DNS pass must not be applied to the upcoming filtering sources. Await the implementation worker, then rerun browser/login and scoped lint/types on final sources as requested by the coordinator. Quote/upload need no repeat unless their reviewed inputs change.
2. **Production adapters/live acceptance:** `quote/providers.py` remains unconditionally unavailable; AC-03/04/08 are incomplete for both Xometry and JLC. Preserve existing uncertain research intent; no repeat research upload or guessed selector is authorized by these tests.
3. **Optional real Chromium checks:** 12 browser methods were skipped, and login `browser_e2e.py` was not opted in. They remain separate from the independent suites and from Chrome DevTools UI evidence owned by the coordinator.
4. **Existing quality baseline:** one generated controller `UP009` and 36 wider quote-fixture type errors are unchanged and excluded from the passing scope claims. The complete repository/task quality gate is not represented as entirely clean.
5. **Spec synchronization:** the coordinator owns `.setp` alias documentation across upload/freeze/revalidation and synchronization of the user-approved filtering contract. This reviewer did not modify specs or main task artifacts.

No new mechanical issue requiring an in-scope code fix was found after reviewing the candidate. Passing infrastructure/guard tests is not automatic-quote feature completion.

## Reviewed source identity

Byte SHA-256 captured after the checks; this reviewer made no source/test edits before or after execution. Paths are relative to `backend/`.

| File | SHA-256 |
| --- | --- |
| `app/modules/cnc/browser/policy.py` — strict candidate only | `5EA9F6BA61C121D7C9D01E685426CE7B6C492237651128D3D188B11B4046BAAF` |
| `app/modules/cnc/browser/files.py` | `0FE20085A23265296231812ADF14E7266FE1205A3AA1A480827BF57B5382E886` |
| `app/modules/cnc/quote/repository.py` | `92F7F219ACB5694F76602BFAEEAD7084063B42465E73668616CD4FF018C61740` |
| `app/modules/cnc/quote/routes.py` | `0D924B3A44B5473113DC138F2FFB67B0E2098F72CCC1C9D0EA73C6EA1E95509E` |
| `app/modules/cnc/quote/providers.py` | `0777935868B6207302299DE5153C2616DF602F2751DE20C3868C25215D2FBB0B` |
| `app/modules/cnc/login/runtime.py` | `CBE00CE7254DE4181EBCFE7ABF7E3CC03C7F3BDE391DC2FE2A04A1B3AADEBA15` |
| `app/modules/cnc/login/providers.py` | `EC46778D8973B209152FAA65FC2406D2202B918E7D78486AAADE41F6DE8928E3` |
| `tests/cnc/quote/test_step_file_boundary.py` | `1196D178290707B5588403ACCC6900DC057DA457B6250761974D83A7FC72410B` |
| `tests/cnc/browser/test_policy_files_state.py` | `EA8F0DFF35A3436BD18B50B4A9468D3E5878632B95920C9BA7955001639C29E4` |
| `tests/cnc/quote/test_quote_http.py` | `C734167B0A20333F8A2345B765AA9036CE268261B996ACC1FE7D3BFFA866B3E1` |
| `tests/cnc/quote/test_quote_runner.py` | `750CEC39A5A79FBCA1E5D1E5B0EA22801111A0810FACE20F69334205A926683D` |
