# Final bounded evidence review — 2026-10-22

Reviewer: dispatched `trellis-check`; no further agents dispatched.
Deliverable: this new record only. Shared documents, task metadata, parent status,
production code, tests and dependency manifests were not edited. No browser,
external service, dependency installation, privilege change, commit or archive
was used during this review. Local loopback TCP tests were run as part of the
existing isolated component suite, not against an external service.

## Conclusion and BR-04 meaning

**PASS for the assigned component-evidence review. Not a full Linux 62-test
success or Linux deployment certification.**

Read `check.jsonl` and all six referenced specification/design/source-analysis
files, task PRD/design/implementation plan, the Linux validation record,
independent continuation review and shared test report. The task design delegates
the interface/safety contract to `docs/browser-implementation-design.md`.

BR-04 requires scope-bound encrypted state, authentication/challenge stops,
rejection of disallowed/public-network violations and invalid file boundaries
before side effects. The symlink case is one part of that criterion, not all of
it. `.trellis/spec/backend/browser-executor.md`, section 6, explicitly rejects a
Windows privilege skip as proof and permits the unchanged original symlink test
on a permitted local Linux runner, with one executed test, zero skips and
unchanged hash. It does not require the Windows-only adapter's entire diagnostic
suite to pass on Linux. Prior Windows security/lifecycle and synthetic-browser
evidence plus the actually executed Ubuntu file-boundary case therefore support
the current component BR-04 checkbox. A Windows skip stays a skip.

This accepts the recorded execution evidence; this reviewer did not rerun Linux
or the synthetic browser tests. SHA-256 verifies the currently available test
file against the recorded value, not independent provenance of every prior
process or an archived hash of the whole source tree.

## Verified evidence

| Evidence | Recorded result | Interpretation |
| --- | --- | --- |
| Ubuntu original `test_policy_files_state.FileTests.test_symlink_escape_rejected` | 1 executed / 0.024 s / 0 skips / exit 0 | Actual OS-symlink negative test, not a substituted Mock or Windows skip |
| Ubuntu original four cross-platform modules | 46/46 / 3.385 s / 0 errors / 0 failures / 0 skips / exit 0 | Scoped cross-platform unit/Mock coverage, including symlink and Unix proxy path |
| Broader Ubuntu diagnostic with direct Windows adapter tests | 62 total / 7.300 s / 58 passed / 2 errors / 2 existing Windows-specific skips / exit 1 | Failed diagnostic, retained as failed; not Linux 62/62 |
| Prior independent Windows unit/Mock/TCP run | 62 total / 1.365 s / 61 passed / 1 privilege skip / exit 0 | Supported Windows component evidence, not a passed Windows symlink test |
| Prior managed Headless Shell 145 and Chrome 155 synthetic E2E | Each 11/11, respectively 23.707 s and 37.981 s | Existing synthetic-browser evidence only; not repeated here |

The Linux record documents Python 3.12.3 on the existing Ubuntu/WSL2 runner,
real temporary files under Linux `/tmp`, and an isolated environment with
standard Linux wheels constrained by the existing lock. Its initial import,
environment-selection and network setup failures are retained and do not count
as successful tests. The ten reported core imported dependency versions agree
with current `backend/uv.lock`; this check does not freshly inspect Linux imports.
Playwright is absent in that Linux environment, so no Chromium conclusion follows.

Current SHA-256 of `backend/tests/cnc/browser/test_policy_files_state.py`:

```text
17209160855a9ea821bb103e74dd36a7cd9c1d5535839c02f65e9f314dd71a61
```

It matches the Linux before/after record, independent continuation review and
shared report. Source inspection confirms the test creates a real symlink under
the trusted root to another temporary directory's STEP file and expects
`BrowserStop` from `read_verified()`. `fixture_step()` supplies the same valid
bytes/hash/size as the external file. `TrustedStep.read_verified()` resolves the
actual root/path strictly and rejects an out-of-root resolved target before
opening it. The negative test has not been replaced by mocked path resolution.

Static AST counts match the documented selections: `test_egress` 3,
`test_policy_files_state` 10, `test_session` 15, `test_workflow` 18 = 46;
`test_windows_streams` adds 16 = 62. These static counts corroborate selection,
not execution. A fresh Windows execution below independently confirms the
62-test selection and sole privilege skip.

## Findings (fixed)

No mechanical in-scope implementation or test defect was demonstrated; no code,
test or shared-document correction was made. The new record supplies the
requested final evidence review only. No specification change is needed to
permit this Linux symlink supplement: the existing executor spec already states
the applicable runner/hash/no-skip contract.

## Findings (not fixed)

1. **Broader Linux diagnostic remains failed.**
   `test_active_callback_cancelled_and_real_stream_writer_closed` and
   `test_real_streams_handoff_cancellation_closes_via_public_api` directly call
   `start_windows_server` on Linux and fail the bare immediate rebind at
   `test_windows_streams.py:107` with errno 98. The production proxy selects that
   adapter only for `sys.platform == "win32"`; other hosts use
   `asyncio.start_server`. Changing test portability/host support is outside this
   bounded evidence assignment and potentially changes supported interfaces or
   assertions. Neither add skips nor relax Windows cleanup assertions to present
   a green Linux 62. If full-suite Linux support is required, define that support
   and its OS-appropriate cleanup assertions in a separate scoped change.
2. **TCP diagnosis is suggestive, not a replacement result.** The first kernel
   snapshot included LISTEN (`0A`) and FIN_WAIT1 (`04`). The later bounded
   reproduction, after closing both ends and yielding 100 ms, showed TIME_WAIT
   (`06`), no LISTEN, connect errno 111, listener descriptor -1 and empty owned
   sets. This supports a kernel-state explanation; it does not prove the exact
   state of every earlier failing connection, prove a leak, or turn either
   original error into a pass. No TCP-policy change is warranted by this record.
3. **Windows OS symlink permission remains unavailable.** The fresh Windows run
   still skips the original test. Ubuntu's actual execution supplements this
   missing case, not the Windows test count. No account/OS permission change is
   required or recommended for this completed evidence step.
4. **Metadata is stale; coordinator must integrate.** `task.json` still says
   BR-04 remains open and records
   `component_state=implemented_component_tests_passed_with_unverified_symlink`
   and `filesystem_symlink_validation=unverified_os_privilege`. Those strings
   no longer describe current component evidence. They were read only. See
   recommendations below; status transitions remain coordinator-owned.

## Remaining integration boundaries

- Real RapidDirect/Xometry authorized authentication, session recovery, verified
  STEP geometry, effective parameters, actual money/lead time and recalculation
  remain original task-01/02/03 live gates. Draft platform automation remains off.
- Production durable IntentStore, encrypted session repository/ACL, distributed
  account leases and private evidence remain task-02/04 integration work. Test
  stores and process-local exclusivity do not satisfy these requirements.
- Formal model/Agent recovery, owner-authorized handoff/resume UI, persistent
  scheduling, two monitoring rounds, history and full Web acceptance remain
  original task-02–05 work. Synthetic pages do not establish those outcomes.
- Linux Chromium, container/managed deployment, production egress isolation,
  secrets/backup/Trace-retention controls and any BrowserSkill pairing remain
  separately unverified. The Linux unit result cannot satisfy those gates.
- This review does not recertify the complete task-tree baseline audit or
  original BR-01/02/03/05/06 evidence; their existing recorded component findings
  remain referenced, not new live executions.

## Coordinator-only metadata recommendations

Replace the *current* notes assertion that BR-04 is open with a dated summary:
Ubuntu original symlink 1/1, zero skips, unchanged hash; Ubuntu cross-platform
46/46; Windows 61 passes plus one explicit privilege skip; broader Linux 62
failed with two errors and two existing skips; prior managed145/chrome155
synthetic E2E each 11/11 retained, not repeated. Link the Linux, continuation
review and this final record, and retain earlier failure/skip history.

Recommended semantic updates (exact enum/string choice belongs to coordinator):

- `meta.component_state`: component acceptance passed with the separate Ubuntu
  symlink supplement, rather than an unverified-symlink state.
- `meta.filesystem_symlink_validation`: original Ubuntu test passed with zero
  skips and unchanged SHA-256; Windows privilege skip retained separately.
- Preserve `meta.windows_runtime_validation` as the existing synthetic result;
  preserve `meta.live_platform_validation=unverified`.
- If metadata tracks Linux coverage, describe the 46-test scope and failed
  broader diagnostic separately; do not introduce a `linux_full_suite_passed`
  or deployment-passed assertion.
- Do not infer new implementation from `browser_revision=2026-10-21`; if this is
  a code-baseline field it can remain, while validation date is 2026-10-22.
- No automatic `status`, `completedAt`, parent/01–05, commit or archive change.
  The remaining finish/integration decisions belong to the coordinator.

The implementation plan labels earlier pending-symlink statements as historical;
they should remain history, not be erased or used to reopen today's completed
component evidence. Shared report/PRD/spec already preserve the failed broader
Linux diagnostic and the separate live gates.

## Verification executed by this reviewer

All commands used existing local tools; no install, external service or browser.
From `backend/`:

```powershell
.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/browser tests/cnc/browser
.venv/Scripts/ruff.exe format --check app/modules/cnc/browser tests/cnc/browser
.venv/Scripts/python.exe -m basedpyright app/modules/cnc/browser tests/cnc/browser --project pyrightconfig.json
.venv/Scripts/python.exe -B -m unittest discover -s tests/cnc/browser -p 'test_[epsw]*.py' -v
uv lock --check --offline
```

- Lint: PASS (`All checks passed!`), exit 0.
- Format: PASS, 18 files already formatted, exit 0.
- TypeCheck: PASS, 0 errors / 0 warnings / 0 notes, exit 0.
- Tests: PASS with explicit limitation, 62 run / 1.626 s / 61 passes /
  1 unchanged Windows symlink privilege skip / exit 0. All 16 Windows adapter
  tests pass. Expected fixed `policy_blocked` and asyncio slow-task warnings
  appeared; no test errors/failures or reported resource-cleanup warnings.
- Lock: PASS, resolved 109 packages in 1 ms, exit 0, offline.

From repository root:

```powershell
Get-FileHash backend/tests/cnc/browser/test_policy_files_state.py -Algorithm SHA256
git diff --check
git status --short
```

Hash matched as above; tracked diff whitespace check passed, with Git's existing
LF-to-CRLF warning for `backend/uv.lock`. Git diff does not check untracked
content; this new record is checked separately after writing. Initial worktree
contains unrelated user/other-agent changes, which were preserved.

A read-only inline Python check was executed via
`@' ... '@ | backend/.venv/Scripts/python.exe -B -` from repository root. Its
exact assertions/checks were:

1. Parse nonblank `check.jsonl` lines with `json.loads`; assert 6 entries and all
   referenced paths are files.
2. Compute `hashlib.sha256(test_file.read_bytes()).hexdigest()` and assert the
   exact hash above; assert that string occurs in both assigned research records
   and `docs/browser-test-report.md`.
3. Parse each of the five named test modules with `ast.parse`; count
   `FunctionDef`/`AsyncFunctionDef` names beginning `test_`; assert first four
   total 46 and all five total 62, outputting per-module counts.
4. Parse `backend/uv.lock` with `tomllib`; assert recorded versions for
   cryptography 50.0.0, fastapi 0.138.2, loguru 0.7.3, sqlalchemy 2.0.51,
   rich 15.0.0, pydantic-settings 2.14.1, pydantic 2.12.5,
   pydantic-core 2.41.5, cffi 2.1.1 and greenlet 3.5.2 all match the lock.
5. Resolve every relative Markdown link matching `\]\(([^)]+)\)` in both
   assigned research records and task `prd.md`, `design.md`, `implement.md`;
   assert each target exists (ignore URLs/fragment-only links).
6. Parse/read current task `status`, `meta.component_state` and
   `meta.filesystem_symlink_validation` without writing them.

All assertions passed, exit 0. Source-path reads additionally verified the
symlink fixture/validator and Windows-versus-Unix listener dispatch described
above. No Linux rerun was necessary for this bounded evidence check.

Post-write verification: a second read-only inline Python command checked this
record is UTF-8 without BOM, ends with a newline, has no trailing whitespace or
merge-conflict markers, and contains all required findings/boundary/verification
headings; it also recomputed the unchanged symlink test hash. All passed.
`git diff --check` and `git status --short` were then repeated successfully.
SHA-256 snapshots immediately before/after report creation confirmed no changes
to browser Python source/tests, dependency manifests, this task and parent
metadata, assigned task artifacts, both prior research records or shared report
during that write. Only this new Markdown record was authored by this reviewer.
