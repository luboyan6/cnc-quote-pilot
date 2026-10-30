# CNC Monitoring Schedules and Periodic Execution Policy

## 1. Scope / Trigger

T3 implements scheduled quote monitoring, execution plan lifecycle, round management,
and automatic periodic scanning integrated with the system scheduler. Domain logic
resides in `app/modules/cnc/monitor/`; database models and HTTP endpoints are in
`app/modules/cnc/cnc_quote_schedule/` and `app/modules/cnc/cnc_quote_schedule_round/`;
the scheduler handler is integrated in `app/modules/task/cronjob/node/handlers/cnc_monitor.py`.

## 2. Signatures

### 2.1 HTTP Endpoints
- `POST /cnc_quote_schedule/create`
  - Permission: `module_cnc:cnc_quote_schedule:create`.
  - Accepts `ScheduleCreate`: name, interval_minutes, timezone, targets (list of config_id, account_id, quantities).
  - Normalizes and validates configuration ownership and account accessibility, snapshots frozen parameters.
- `PUT /cnc_quote_schedule/update/{id}`
  - Permission: `module_cnc:cnc_quote_schedule:update`.
  - Accepts `ScheduleUpdate`: partial update of name, interval_minutes, timezone, targets.
  - Updates target snapshot and increments `revision` when targets change; re-computes `next_run_at`.
- `GET /cnc_quote_schedule/list`
  - Permission: `module_cnc:cnc_quote_schedule:query`.
  - Paged list of schedules filtered to the caller's tenant/actor.
- `GET /cnc_quote_schedule/detail/{id}`
  - Permission: `module_cnc:cnc_quote_schedule:detail`.
  - Full schedule details, status, target snapshot, timestamps.
- `POST /cnc_quote_schedule/{id}/pause`
  - Permission: `module_cnc:cnc_quote_schedule:update`.
  - Transitions status to `PAUSED` with reason.
- `POST /cnc_quote_schedule/{id}/resume`
  - Permission: `module_cnc:cnc_quote_schedule:update`.
  - Re-validates configuration/account snapshot; re-aligns `next_run_at` to the next future slot and sets `ENABLED`.
- `GET /cnc_quote_schedule/{id}/rounds`
  - Permission: `module_cnc:cnc_quote_schedule:detail`.
  - Paged list of executed/skipped rounds for the schedule, ordered by round_no desc.

### 2.2 Scheduler Job Handler
- Builtin handler: `builtin:cnc_monitor.scan_due`
  - Resolves to `app.modules.task.cronjob.node.handlers.cnc_monitor.scan_due`.
  - Called periodically (e.g. every 60s) by APScheduler worker thread.
  - Executes short database transaction to admit due schedules without holding long locks.

## 3. Contracts

### 3.1 Slot Alignment and Interval Math
- Schedule runs are anchored to `anchor_time` (UTC).
- Next slots are computed via `compute_next_slot(anchor_time, interval_minutes, now)`:
  - If `now <= anchor_time`, next slot is `anchor_time`.
  - Otherwise, next slot is `anchor_time + k * interval_minutes` where `k = floor(delta / interval) + 1`.
  - Prevents drift across repeated executions.
- `ensure_utc` guarantees timezone-safe comparisons across SQLite naive timestamps and UTC-aware datetimes.

### 3.2 Round Admission Invariants
When `scan_due` encounters a schedule where `next_run_at <= now`:
1. **Overlap Guard**: If a previous round of the schedule is still `RUNNING`:
   - Records a round with status `SKIPPED_OVERLAP` and `skip_reason="PREVIOUS_ROUND_RUNNING"`.
   - Advances `next_run_at` to the next slot without creating a batch.
2. **Downtime Catch-up / Grace Period**: If the scheduled slot has passed beyond `grace_period_seconds` (default 60s):
   - Records a round with status `MISSED` and `skip_reason="MISSED_SLOT_DOWNTIME"`.
   - Advances `next_run_at` without blasting overdue queue items.
3. **Queue Capacity Guard**: If system active items + schedule items exceed `capacity_limit`:
   - Records a round with status `CAPACITY_WAIT` and `skip_reason="BATCH_CAPACITY_EXCEEDED"`.
   - Retains the same slot until capacity becomes available, then admits it once.
   - Serializes this capacity check with manual admission using the batch capacity row.
4. **Valid Admittance**:
   - Creates `CncQuoteBatchModel` (`source="schedule"`, `request_id="sched-{id}-r{round_no}"`).
   - Creates frozen `CncQuoteBatchItemModel` entries for each target and quantity.
   - Creates `CncQuoteScheduleRoundModel` (`status="RUNNING"`, `batch_id=batch.id`, `schedule_revision=sched.revision`).
   - Committed in a single atomic transaction. Browser quotes are executed asynchronously by `QuoteDispatcher`.
   - The round is settled when its batch reaches a terminal status. The scanner also repairs stale RUNNING rounds from the batch status.

The scheduler leader registers the 60-second scan when batch execution is enabled.
Before admission, revalidate the creator's current permissions and frozen inputs;
pause the unchanged schedule if either is no longer valid.

## 4. Verification

~~~powershell
cd backend
$env:PYTHONUTF8=1
.venv/Scripts/python.exe -m pytest tests/cnc/monitor -v
.venv/Scripts/basedpyright.exe app/modules/cnc/monitor app/modules/cnc/cnc_quote_schedule app/modules/cnc/cnc_quote_schedule_round
.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/monitor app/modules/cnc/cnc_quote_schedule app/modules/cnc/cnc_quote_schedule_round tests/cnc/monitor
.venv/Scripts/ruff.exe format --check app/modules/cnc/monitor app/modules/cnc/cnc_quote_schedule app/modules/cnc/cnc_quote_schedule_round tests/cnc/monitor
~~~
