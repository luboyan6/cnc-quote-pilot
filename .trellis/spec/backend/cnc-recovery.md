# CNC Error Recovery and Retry Policy

## 1. Scope / Trigger

T2 implements structured error classification, retry budgets, safe state recovery, and
manual retry capabilities around batch quote items and quote execution. Domain logic
resides in `app/modules/cnc/recovery/`; HTTP endpoints are integrated into
`app/modules/cnc/cnc_quote_batch/`.

## 2. Signatures

- `POST /cnc_quote_batch/items/{id}/retry`
  - Requires permission `module_cnc:cnc_quote_batch:retry`.
  - Item must belong to the caller's tenant/actor (unless superuser).
  - Permitted only when `exec_status in ("FAILED", "RETRY_WAIT")`.
  - Forbidden on `COMPLETED`, `CANCELLED`, or active items (`RUNNING`, `CANCELLING`).
  - **Strictly forbidden** on `RECONCILING` with uncertain remote side-effects (`BATCH_UNCERTAIN_MUTATION_RETRY_FORBIDDEN`).
  - Checks attempt budget: if `attempt_count >= max_attempts`, non-superusers receive `MAX_ATTEMPTS_EXCEEDED` (HTTP 400).

## 3. Contracts

### 3.1 Error Classification & Sanitization
Every failure maps into one of 9 structured categories (`ErrorCategory`):
1. `TEMPORARY_NETWORK`: Retries with backoff (30s / 120s base).
2. `SESSION_EXPIRED`: At most 1 automatic re-auth attempt; then fails terminally.
3. `HUMAN_ACTION_REQUIRED`: Transitions to `WAITING_HUMAN`, pauses lease.
4. `PERMANENT_REJECTED`: Fails terminally without retry.
5. `RATE_LIMITED`: Enforces cooldown delay (min 60s) before retry.
6. `DOM_CONTRACT_CHANGED`: Fails terminally, preserves evidence.
7. `UNCERTAIN_MUTATION`: Transitions to `RECONCILING`, never auto-retried.
8. `LOCAL_PERSISTENCE_FAILED`: Retries local storage only, no remote re-upload.
9. `OWNER_LOST_EXPIRED`: Moves to `RECONCILING` for safe inspection.

All error messages and codes returned by API or logged must be sanitized:
- No file system paths (`C:\...`, `/home/...`).
- No bearer tokens or passwords.
- No raw Python stack traces.

### 3.2 Uncertain Mutation Invariant
When a remote write (upload / parameter save / quote submission) is initiated:
- If its outcome is unknown (e.g. timeout / connection reset / process crash):
  - Intent state is `UNCERTAIN`.
  - Item state becomes `RECONCILING`.
  - **Never** replay remote mutations automatically or via standard retry.

### 3.3 Recovery Scanner
`RecoveryScanner` runs periodically during application lifespan:
- Items in `WAITING_HUMAN` exceeding deadline (default 900s) become `FAILED` with `MANUAL_TIMEOUT`.
- Items in `RECONCILING` whose remote quote results are found in memory/pending storage are settled to `COMPLETED`.

## 4. Verification

~~~powershell
pytest tests/cnc/recovery -v
basedpyright app/modules/cnc/recovery
ruff check --no-fix app/modules/cnc/recovery
ruff format --check app/modules/cnc/recovery
~~~
