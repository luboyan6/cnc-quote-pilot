# Agent integration baseline — 2026-10-29

The user authorized implementation of the existing DeerFlow Agent task tree.
The monitor/result integration remains dependent on the Lead and chat contracts.
These observations are not evidence of real provider acceptance.

## Existing service boundary

- `BatchService` freezes quantities per target and calls the existing quote
  repository; `MonitorService` owns schedule admission and current permissions.
- `CncQuoteResultService` is the existing source for statistics and history.
  Agent tools must call domain services directly, reload current permissions,
  and return safe references rather than browser state or private paths.
- The result task `10-28-cnc-monitor-04-results` is still in progress; its
  user-owned changes must be preserved.

## Gap to resolve before publishing history tools

`cnc_quote_result/service.py:get_history_prices` falls back to a series keyed
by platform, currency, quantity and quote status when `comparison_key` is
missing. This can compare unrelated files or processing specifications. In
addition `comparison.py:build_comparison_key` currently accepts missing file,
material and price scope, despite its description and V-04 requiring unknown
critical conditions to remain incomparable. Check current domain code and
contracts at implementation time; repair the owning result layer with
meaningful regression cases before exposing the history through an Agent tool.
Do not synthesize missing commercial terms or delete historical records.
An isolated call with missing `file_sha256`, `material` and `price_scope`
returned a nonempty comparison key; this is a verified current behavior, not
an inference from the source alone.
The same result service also supplies platform/currency fallbacks based on
numeric platform IDs in statistics/history. Check whether these can fabricate
unknown values before exposing results; preserve the actual domain facts.

## Baseline checks

Using the existing backend virtual environment, three independent pytest runs
completed: `tests/cnc/results` 12 passed; `tests/cnc/monitor` 20 passed with
5 SQLAlchemy metadata warnings; `tests/cnc/batch` 36 passed, 32 skipped with
3 metadata warnings. These are baseline results before Agent integration;
PostgreSQL-dependent tests and live platform acceptance were not established by
these results. The missing-comparison regression was not covered by this suite.
