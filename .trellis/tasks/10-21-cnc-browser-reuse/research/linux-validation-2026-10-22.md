# Existing Ubuntu runner validation — 2026-10-22

## Result and scope

- The unchanged `test_policy_files_state.FileTests.test_symlink_escape_rejected` executed successfully: **1 test, 0 skips, exit 0**, 0.024 seconds.
- The existing cross-platform modules (`test_egress`, `test_policy_files_state`, `test_session`, `test_workflow`) executed successfully: **46 tests, 0 errors, 0 failures, 0 skips, exit 0**, 3.385 seconds. The symlink test passed here too.
- The broader diagnostic run including the Windows-only listener adapter was **not green**: **62 tests, 58 passed, 2 errors, 2 existing Windows-specific skips, exit 1**, 7.300 seconds. Its errors and kernel observations are retained below. Do not summarize this as 62/62 or Linux deployment validation.
- No production code or test was edited. No OS settings/account privileges were changed, and no runner/WSL distribution was installed. The existing Ubuntu WSL2 was already running. No remote runner, fake module, Windows native extension, application startup, database connection or real provider workflow was used.

The required test file's SHA-256 before and after execution was identical:

```text
backend/tests/cnc/browser/test_policy_files_state.py
17209160855a9ea821bb103e74dd36a7cd9c1d5535839c02f65e9f314dd71a61
```

## Runner and dependencies

```text
RUNNER Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39
Python 3.12.3 (main, Jul 15 2026, 23:46:41) [GCC 13.3.0]
Existing distribution: Ubuntu (WSL2), uid=0(root), gid=0(root)
Interpreter: /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-venv/bin/python
Repository: /mnt/e/AIWorkspace/cnc-quote-pilot
Test temporary files: Linux tempfile default /tmp (real symlink creation)
```

The new test-only environment and wheel directory are under the already ignored `.trellis/.runtime/`. `git check-ignore .trellis/.runtime/br-linux-venv` returned that path. The venv uses `--system-site-packages`; the required dependency set was subsequently installed locally at the exact existing `backend/uv.lock` versions. Actual imported package versions:

| Package | Version |
| --- | --- |
| cryptography | 50.0.0 |
| fastapi | 0.138.2 |
| loguru | 0.7.3 |
| sqlalchemy | 2.0.51 |
| rich | 15.0.0 |
| pydantic-settings | 2.14.1 |
| pydantic | 2.12.5 |
| pydantic-core | 2.41.5 |
| cffi | 2.1.1 |
| greenlet | 3.5.2 |

The 22-package offline installation also installed annotated-doc 0.0.4, annotated-types 0.7.0, anyio 4.12.1, idna 3.11, markdown-it-py 4.0.0, mdurl 0.1.2, pycparser 3.0, pygments 2.19.2, python-dotenv 1.2.1, starlette 0.52.1, typing-extensions 4.15.0 and typing-inspection 0.4.2. No lockfile or dependency manifest was modified. Playwright is absent in this Linux venv; these scoped tests use the existing SDK doubles and explicitly test the missing optional SDK branch. This is not Chromium E2E evidence.

Read-only `importlib.util.find_spec` on the existing system Ubuntu Python found no `OCP`, `OCC` or `cadquery`; that observation does not assess STEP geometry or authorize changing task-01 live gates.

## Setup history and successful commands

The initial sandboxed WSL execution returned `Wsl/Service/E_ACCESSDENIED`; the authorized same-command retry outside the sandbox succeeded. Windows `whoami /priv` showed only `SeChangeNotifyPrivilege`, so another identical Windows symlink skip was not used as progress.

The existing system Ubuntu Python could not load the unchanged suite because `backend/app/__init__.py` eagerly imports FastAPI. Discovery reported `ModuleNotFoundError: No module named 'fastapi'`. An initial test-selection wrapper also encountered a `_FailedTest` iteration error; **zero actual tests ran and no pass was claimed**. Dependencies were then provided in the isolated venv without bypassing package initialization.

Commands were issued from `E:/AIWorkspace/cnc-quote-pilot` in PowerShell. Venv creation:

```powershell
wsl -d Ubuntu --exec /root/.local/bin/uv venv --system-site-packages --python /usr/bin/python3 /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-venv
```

Constraint generation used the actual lock, without editing it:

```python
import pathlib, tomllib
root = pathlib.Path('/mnt/e/AIWorkspace/cnc-quote-pilot')
packages = tomllib.loads((root / 'backend/uv.lock').read_text())['package']
constraints = root / '.trellis/.runtime/br-linux-constraints.txt'
constraints.write_text('\n'.join(p['name'] + '==' + p['version'] for p in packages if p['name'] != 'backend') + '\n')
```

WSL networking failed against both package indexes: PyPI `/simple/cryptography/` and the repository-configured Tsinghua mirror `/simple/rich/` returned connection timeouts after three retries (46.5s and 45.1s). An offline Windows uv cache attempt also failed because cached FastAPI metadata was unavailable. These setup failures did not execute the test.

Windows successfully downloaded standard target-platform wheels, including native Linux cp312/abi3 wheels rather than Windows site-packages:

```powershell
python -m pip download --dest .trellis/.runtime/br-linux-wheels --python-version 3.12 --platform manylinux_2_34_x86_64 --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --only-binary=:all: --constraint .trellis/.runtime/br-linux-constraints.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple --timeout 15 --retries 1 fastapi==0.138.2 loguru==0.7.3 sqlalchemy==2.0.51 rich==15.0.0 pydantic-settings==2.14.1 cryptography==50.0.0
```

This downloaded 24 wheels; two Windows-marker pure-Python optional wheels were not installed by the Linux resolver. Linux then installed 22 matching packages entirely offline:

```powershell
wsl -d Ubuntu --exec /root/.local/bin/uv pip install --offline --no-index --find-links /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-wheels --python /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-venv/bin/python --constraint /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-constraints.txt fastapi==0.138.2 loguru==0.7.3 sqlalchemy==2.0.51 rich==15.0.0 pydantic-settings==2.14.1 cryptography==50.0.0
```

Output: `Resolved 22 packages in 45ms`, `Prepared 22 packages in 780ms`, `Installed 22 packages in 5.48s`; a cross-filesystem hardlink warning caused a normal full-copy fallback.

An initial `ENVIRONMENT=test` process failed before test execution because this application's enum accepts only `dev`/`prod`. The successful commands below explicitly use its existing default `dev`. They import existing modules but do not call `create_app` or run the application lifespan; backend logger initialization may write its already ignored local logs.

## Required unchanged symlink test

Exact successful command (the wrapper verifies the executed count, skips and unchanged file hash; it does not alter the test):

```powershell
wsl -d Ubuntu --exec /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-venv/bin/python -B -c 'import hashlib,os,pathlib,sys,unittest; os.environ["ENVIRONMENT"]="dev"; os.chdir("/mnt/e/AIWorkspace/cnc-quote-pilot/backend"); sys.path.insert(0,"tests/cnc/browser"); before=hashlib.sha256(pathlib.Path("tests/cnc/browser/test_policy_files_state.py").read_bytes()).hexdigest(); suite=unittest.defaultTestLoader.loadTestsFromName("test_policy_files_state.FileTests.test_symlink_escape_rejected"); result=unittest.TextTestRunner(verbosity=2).run(suite); after=hashlib.sha256(pathlib.Path("tests/cnc/browser/test_policy_files_state.py").read_bytes()).hexdigest(); print("ACTUAL_EXECUTION",result.testsRun,"SKIPS",len(result.skipped),"TEST_SHA256_UNCHANGED",before==after,before,flush=True); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==1 and not result.skipped and before==after else 1)'
```

Actual output, exit 0:

```text
test_symlink_escape_rejected (test_policy_files_state.FileTests.test_symlink_escape_rejected) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.024s

OK
ACTUAL_EXECUTION 1 SKIPS 0 TEST_SHA256_UNCHANGED True 17209160855a9ea821bb103e74dd36a7cd9c1d5535839c02f65e9f314dd71a61
```

## Cross-platform existing suite

Exact successful command:

```powershell
wsl -d Ubuntu --exec /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-venv/bin/python -B -c 'import hashlib,os,pathlib,sys,unittest; os.environ["ENVIRONMENT"]="dev"; os.chdir("/mnt/e/AIWorkspace/cnc-quote-pilot/backend"); sys.path.insert(0,"tests/cnc/browser"); modules=("test_egress","test_policy_files_state","test_session","test_workflow"); suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules); result=unittest.TextTestRunner(verbosity=2).run(suite); print("SUMMARY",{"run":result.testsRun,"errors":len(result.errors),"failures":len(result.failures),"skips":len(result.skipped)},flush=True); print("TEST_SHA256",hashlib.sha256(pathlib.Path("tests/cnc/browser/test_policy_files_state.py").read_bytes()).hexdigest(),flush=True); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==46 and not result.skipped else 1)'
```

Actual result excerpt, exit 0:

```text
test_symlink_escape_rejected (test_policy_files_state.FileTests.test_symlink_escape_rejected) ... ok
...
----------------------------------------------------------------------
Ran 46 tests in 3.385s

OK
SUMMARY {'run': 46, 'errors': 0, 'failures': 0, 'skips': 0}
TEST_SHA256 17209160855a9ea821bb103e74dd36a7cd9c1d5535839c02f65e9f314dd71a61
```

Logs contained expected fixed `browser egress policy_blocked` warnings and some asyncio slow-task warnings. There was no traceback or skipped test in this 46-test run.

## Broader Linux diagnostic: retain failures

Exact executed command:

```powershell
wsl -d Ubuntu --exec /mnt/e/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/br-linux-venv/bin/python -B -c 'import hashlib,importlib.metadata,os,pathlib,platform,sys,unittest; os.environ["ENVIRONMENT"]="dev"; os.chdir("/mnt/e/AIWorkspace/cnc-quote-pilot/backend"); print("RUNNER",platform.platform(),sys.version,flush=True); print("DEPENDENCIES",{n:importlib.metadata.version(n) for n in ("cryptography","fastapi","loguru","sqlalchemy","rich","pydantic-settings","pydantic","pydantic-core","cffi","greenlet")},flush=True); print("TEST_SHA256",hashlib.sha256(pathlib.Path("tests/cnc/browser/test_policy_files_state.py").read_bytes()).hexdigest(),flush=True); suite=unittest.defaultTestLoader.discover("tests/cnc/browser",pattern="test_[epsw]*.py"); result=unittest.TextTestRunner(verbosity=2).run(suite); print("SUMMARY",{"run":result.testsRun,"errors":len(result.errors),"failures":len(result.failures),"skips":len(result.skipped)},flush=True); print("SKIPPED",[(case.id(),reason) for case,reason in result.skipped],flush=True); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==62 and all("symlink" not in case.id() for case,reason in result.skipped) else 1)'
```

Actual failure summary, exit 1:

```text
SUMMARY {'run': 62, 'errors': 2, 'failures': 0, 'skips': 2}
SKIPPED [('test_windows_streams.WindowsListenerTests.test_real_rejected_socks_request_followed_by_tcp_reset_releases_proxy', 'Windows accepted-proxy integration'), ('test_windows_streams.WindowsListenerTests.test_real_tcp_peer_reset_closes_transport_and_releases_listener', 'Windows RST transport regression')]

ERROR: test_active_callback_cancelled_and_real_stream_writer_closed (test_windows_streams.WindowsListenerTests.test_active_callback_cancelled_and_real_stream_writer_closed)
  File "backend/tests/cnc/browser/test_windows_streams.py", line 160, in test_active_callback_cancelled_and_real_stream_writer_closed
    self.assert_port_released(address)
  File "backend/tests/cnc/browser/test_windows_streams.py", line 107, in assert_port_released
    probe.bind(address)
OSError: [Errno 98] Address already in use

ERROR: test_real_streams_handoff_cancellation_closes_via_public_api (test_windows_streams.WindowsListenerTests.test_real_streams_handoff_cancellation_closes_via_public_api)
  File "backend/tests/cnc/browser/test_windows_streams.py", line 304, in test_real_streams_handoff_cancellation_closes_via_public_api
    self.assert_port_released(address)
  File "backend/tests/cnc/browser/test_windows_streams.py", line 107, in assert_port_released
    probe.bind(address)
OSError: [Errno 98] Address already in use

----------------------------------------------------------------------
Ran 62 tests in 7.300s

FAILED (errors=2, skipped=2)
```

The unchanged symlink test passed in this broader run. The two errors call the explicitly Windows-only `start_windows_server` directly on Linux and require immediate rebinding using a new socket without reuse options. Production Unix proxy execution uses `asyncio.start_server`; this diagnostic does not claim that the Windows adapter is supported on Unix. Neither production logic nor the Windows test's strict rebind assertions were changed to obtain a green result. The Windows-specific suite's supported-host results remain separate evidence.

## Bounded TCP diagnostic observations

An independent temporary process reproduced the close sequence with a real local TCP client, `start_windows_server`, peer EOF, public `StreamWriter.close()/wait_closed()`, and a read-only `/proc/net/tcp` lookup of the owned local port. It did not modify or rerun the required test with extra waits.

The first immediate snapshot observed:

```text
PEER_EOF b''
KERNEL_SERVER_PORT_STATES ['0A', '04'] LISTEN_0A_ABSENT False
REBIND_ERRNO 98
CONNECT_ERRNO 111
OWNED_HANDLES_AND_TASKS_EMPTY True
```

This snapshot alone did not establish absent kernel LISTEN state or TIME_WAIT, so no such conclusion was drawn from it. One final bounded diagnostic closed the client too and yielded the loop for 100ms. Actual output:

```text
PEER_EOF b''
AFTER_CLIENT_CLOSE_AND_100MS_KERNEL_STATES ['06'] LISTEN_0A_ABSENT True
CONNECT_ERRNO 111
LISTENER_FD -1 OWNED_HANDLES_AND_TASKS_EMPTY True
```

Linux state `06` is TIME_WAIT; `0A` is LISTEN and `04` is FIN_WAIT1. Errno 111 is ECONNREFUSED and 98 is EADDRINUSE. These observations support a platform/kernel TCP-state explanation for the diagnostic rebind errors. They are not a replacement pass for either failed original test or proof about every earlier failed connection's exact kernel state. Full Linux deployment/browser acceptance remains unverified.

## Handoff

This file is the only tracked-scope deliverable from this validation sub-agent. Main session owns report/PRD/spec/status updates and independent review. Production repositories, task metadata, existing evidence and original tests were preserved. The component can use the supported Windows listener evidence together with the genuinely executed Linux symlink/cross-platform evidence; real provider E2/E3, production storage/leases and managed deployment retain their own gates.
