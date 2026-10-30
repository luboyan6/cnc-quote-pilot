# Quote-tool integration baseline — 2026-10-29

The user authorized implementation of all existing DeerFlow Agent upgrade
tasks. Quote tools must use the current domain services and respect their
permission, frozen-input and unresolved-intent gates. These checks do not
authorize an unrelated file or establish fresh provider acceptance.

## Current service and external constraints

- `app/modules/cnc/quote/service.py` owns single-run admission and execution;
  the repository reloads current actor authorization and owns intents.
- The earlier Xometry upload has an unresolved intent. The 2026-10-25 quote
  task describes a hash-aware distinct-file boundary; do not erase or replay
  a same/unknown-file intent. Preserve an exact-file/current-declaration
  decision if one exists, otherwise do not infer it.
- The batch spec keeps JLC automatic uploads gated on verified effective
  parameter readback. A reference estimate cannot satisfy a formal quote.
- Inspect the current provider and result code again when implementing; these
  files were committed by another workspace operation during this session.

## Offline checks

With the existing backend virtual environment, a single pytest invocation of
`tests/cnc/quote/test_xometry_adapter.py`, `test_xometry_runner.py`, and
`test_provider_isolation.py` completed with 53 passed and 16 subtests passed.
A separate `tests/cnc/recovery` run completed with 25 passed and three
SQLAlchemy metadata warnings. These are baseline checks, not proof of Agent
tool integration, current provider behavior, or a live quote.
