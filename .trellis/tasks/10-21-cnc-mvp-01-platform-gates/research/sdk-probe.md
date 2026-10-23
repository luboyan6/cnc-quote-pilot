# Isolated Deep Agents feasibility probe

This completes the local SDK/checkpoint slice of task 01. It does not complete task 01's live gates or task 02's production recovery implementation. The user subsequently requested stopping at this phase boundary and recording progress before reviewing AI Agent, RPA and browser-automation requirements.

## Reproduce

From the repository root, using the existing project Python 3.12 interpreter:

```powershell
uv venv --python backend/.venv/Scripts/python.exe .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.sdk-venv
uv pip install --python .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.sdk-venv/Scripts/python.exe --index-url https://pypi.org/simple -r .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/sdk-probe-requirements.txt
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.sdk-venv/Scripts/python.exe' -B .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/sdk_probe.py
```

The environment's own `.gitignore` excludes its installed files. No backend dependency declaration, lockfile or application configuration was changed. The exact 82-package snapshot is [sdk-probe-requirements.txt](sdk-probe-requirements.txt). Its successful resolution includes the existing Agno 2.5.8, OpenAI 2.46.0 and Pydantic 2.12.5 pins; this is not a full backend dependency/regression validation.

## Executed result

The actual `deepagents==0.7.29` graph used `StateBackend()`, a matched harness profile, a read-only synthetic observation tool and `ToolStrategy(ProbeDecision, handle_errors=False)`. `ProbeDecision` is deliberately a fixture-only Pydantic schema, not the production domain contract. No provider/model secret or CAD/browser data enters the fixture.

Two separate child processes write and read a private temporary SQLite checkpoint using `AsyncSqliteSaver` 3.1.2 and checkpoint package 4.3.0. The strict `JsonPlusSerializer` explicitly permits the fixture decision type and disables pickle fallback. The compiled message channel is checked to be `DeltaChannel`.

Result: 52 settled synthetic turns, checkpoint step 260, 158 retained messages. The fresh process recovered the identical message digest/count, read the typed decision, verified an empty independent thread, appended a new turn without changing preceding history and retained exactly one synthetic observation. Actual output is in [sdk-probe-result-2026-10-21.json](sdk-probe-result-2026-10-21.json). Per-message IDs make the digest run-specific.

The model is a local scripted fixture. External socket connections are blocked during SDK execution; tracing is disabled locally. The 52 turns stress serialization and are not a production incident or evidence that business budget limits have been implemented. Thread-ID separation is not owner authorization, and the no-repeat fixture check is not production side-effect idempotency.

## Findings carried forward

- `subagents=[]` plus `GeneralPurposeSubagentProfile(enabled=False)` was applied to the pre-initialized fixture model's actual provider/model profile. A final `bind_tools` guard observed exactly `inspect_fixture` and `ProbeDecision`.
- The first guard run caught an additional installed built-in named **`delete`**. Excluding only older lists of filesystem tools is insufficient. The corrected profile excludes the actual eight filesystem tools plus planning/delegation, and a catch-all read/write deny remains present. Profiles only control visibility; production custom-tool ACL and strategy guards still belong in task 02.
- On Windows, blocking socket connections before constructing the asyncio event loop also blocks its internal socketpair. The fixture now creates the loop first and blocks connections inside the running coroutine. No warning suppression or production event-loop change was introduced.
- Backend system model settings were loaded only to emit presence booleans: API key, model identifier and base URL are nonempty. Their values were not output, persisted, sent to a model or used for a request. Actual provider authentication, protocol and tool calling remain **NOT_TESTED** because the user requested stopping at this boundary.

## Remaining work

Actual provider tool calling/typed decisions, domain budgets and guards, Skills isolation, business restart/idempotency, authorized browser contexts, platform permission, geometry and real quotations remain pending. No result here counts toward live quote success, Agent live recovery, monitoring or performance acceptance. Review the Agent/RPA/browser boundary before resuming product implementation.
