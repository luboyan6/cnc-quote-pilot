# Lead source integration progress — 2026-10-29

The user authorized implementation of the existing Agent upgrade task tree.
This is an interim implementation record, not overall task acceptance.

## Offline implementation reported by the implementer

- Added locally adapted graph, bounded skill catalog and middleware, model
  construction, safe event envelope, native asynchronous turn service, and
  direct read-only CNC tools under `backend/app/modules/ai/agent/`.
- Recorded the fixed upstream source hashes and MIT license in that module.
- Preserved the Windows Playwright Proactor main loop by putting the standard
  PostgreSQL saver on an owned Selector loop in a separate thread. Setup is an
  explicit deployment command, not a request-time or startup migration.
- Added a fail-closed gate for `AI_CHAT_ENGINE=deerflow_source` until chat
  ownership/history/transport integration is implemented and reviewed.

## Reported checks

The implementer reported 20 Agent tests passed and one Windows symlink test
skipped, with a separate non-skipped path-containment test. Two lifecycle
tests passed; Ruff, basedpyright and `uv lock --check` passed. A disposable
PostgreSQL instance on port 55447 demonstrated compiled-graph checkpoint
write, close, reopen and continuation under a Proactor main loop. A loopback
HTTP/SSE test observed TCP EOF following cancellation before the first token.
The temporary database was stopped and port 55447 was no longer listening.
An independent Trellis check found and fixed repeated cancellation interrupting
resource cleanup and a false successful stop after a turn had finished. Its
current suite reported 26 passed and 2 skipped (Windows symlink permission and
an unconfigured disposable PostgreSQL DSN); Ruff, basedpyright and lock checks
passed. A non-cooperative cleanup can still exceed the one-second stop goal.

## Isolated configured-model probe

`synthetic_model_probe.py` used the configured system model and an in-memory
SQLite database containing only a synthetic user, role and drawing. The model
connected, activated `cnc-part`, invoked the real permission-checked
`cnc_part_detail` tool, and completed the turn. The event sequence contained
`skill.activated`, `tool.started`, `tool.completed` and `turn.completed`.
It did not use the user database. This does not establish real-user chat,
provider quoting, restart integration or the one-second real-model stop gate.

## Not yet accepted

Real-model and live-provider acceptance, chat/history/UI integration, quote
write tools, batch/monitor/report tools, and the parent integration criteria
remain outstanding. The skipped symlink test is not counted as passed. No
user database was changed by these tests. Do not enable the source engine
until its chat and permission contracts are independently verified.
