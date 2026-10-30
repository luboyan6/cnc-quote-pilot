# CNC Batch Execution

## 1. Scope / Trigger

T1 adds durable manual batches around the existing single quote executor. Domain
code lives in `app/modules/cnc/batch`; plugin models and HTTP routes live in
`app/modules/cnc/cnc_quote_batch` and `cnc_quote_batch_item`. This does not
implement schedules, automatic retry policy, or the historical results UI.

## 2. Signatures

After the normal CNC API prefix, expose:

- `POST /cnc_quote_batch/preview`, `/create`.
- `GET /cnc_quote_batch/list`, `/detail/{id}`, `/{id}/items`.
- `GET /cnc_quote_batch/items/{id}/attempts`.
- `POST /cnc_quote_batch/{id}/cancel`.

Batch requests contain `request_id: UUID` and `targets: [{config_id,
account_id?, quantities: int[]}]`. Quantities must be strict integers in
1..100000; normalize duplicate targets/quantities before admission.

Migration `d4b9a2f61028` follows `b76d50ea5d8f`. It creates Batch/Item plus a
capacity arbitration row, adds nullable Run attempt links and Result batch/item
links, and enforces unique `(actor_id, request_id)`, `(batch_id,
input_fingerprint)`, `(item_id, attempt_no)` and non-null `Result.run_id`.

## 3. Contracts

`CNC_BATCH_ENABLED` defaults to false. Enable dispatch only after applying the
reviewed migration; execution supports one API worker. Never apply migrations
to the user's configured database as a side effect of tests.
Disabled batches reject preview/create; existing records remain readable and
cancellable. Application cleanup must release all independent resources even
if dispatcher shutdown or MCP lifecycle raises.

Use existing authentication and private audit routing. Permissions use
`module_cnc:cnc_quote_batch:{create,query,detail,cancel}` plus current resource
execution permissions. Batch ownership scopes reads/cancellation. Reload current
permissions for execution; do not retain HTTP JWTs in queue records.

Freeze the selected account, source revision, file digest, provider and complete
requested parameters. Quantity overrides apply to an internal snapshot, never
to the shared configuration row. Use a stable UUID derived from item/attempt
for Run creation. An unrelated active configuration Run is a resource wait,
never the result of the waiting item.

Admission serializes on the capacity row in the transaction that creates every
item. A failed target or capacity check leaves no partial batch. A same-key
replay returns the original batch; changed normalized targets conflict.

Dispatcher progress belongs to application lifespan, independent of HTTP reads.
Browser operations never hold admission/claim database transactions open. Persist
Run, Result and successful Item completion atomically; persistence failure must
not expose COMPLETED. Cancellation preserves completed observations and uncertain
Intent records. Quote nature remains QUOTED / REFERENCE_ESTIMATE / PENDING_REVIEW.

Scan expired claims on every dispatcher tick, not just at startup: a claim held
by a previous process can still be valid at startup and expire later. An expired
owner cannot renew, release, or settle that claim. Release an expired claim only
when it has no Run; a claim with a Run becomes `RECONCILING` with
`BATCH_OWNER_LOST_NO_RETRY`, preserving the Run and any uncertain remote Intent.

For a persisted batch cancellation, the dispatcher may stop only its matching
live local activity after rechecking Item, Run, actor and current owner/token.
This internal stop must still work if execution permissions were revoked after
the cancellation request; it does not authorize an external command or another
browser mutation. If the owner is unavailable, retain the Run and Intent for
reconciliation. A staged result is persisted before cancellation settlement.

Dispatcher shutdown waits up to 35 seconds, then makes a bounded attempt to
fence remaining Runs as `RECONCILING` with `BATCH_SHUTDOWN_UNSETTLED` and
returns a fixed failure. If cleanup outlives that timeout, the current lifespan
still closes its other resources; complete resource convergence in that extreme
case remains unverified and must not be reported as a successful shutdown.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Invalid targets or quantity | Reject before admission |
| Same request ID, different normalized targets | BATCH_REQUEST_CONFLICT, HTTP 409 |
| Capacity exceeded | BATCH_QUEUE_FULL, HTTP 409; no partial records |
| Foreign actor reads/cancels | BATCH_UNAVAILABLE, HTTP 404 |
| Current permission revoked | BATCH_PERMISSION_REVOKED, HTTP 403 |
| Config/account/file changed | Stop using frozen input; never silently refresh it |
| Claim expires after dispatcher startup | Rescan; release only an unstarted claim, otherwise retain the Run for reconciliation |
| Execution permission revoked after batch cancel | Stop only the matching live local owner; preserve staged results and uncertain Intent |
| JLC effective-parameter readback not reviewed | `JLC_EFFECTIVE_PARAMETERS_UNVERIFIED` before browser upload |
| Historical duplicate Result.run_id | Abort migration with duplicate IDs; delete nothing |
| Nonempty batch downgrade | Refuse destructive downgrade |

## 5. Good / Base / Bad Cases

- Good: four configurations with quantities 1/2/5 expand to twelve frozen items.
- Base: three identical submissions produce one batch and the same twelve items.
- Bad: attaching a quantity-5 item to an existing quantity-1 Run, or marking an
  item complete after its Result insert failed, violates the execution contract.

## 6. Tests Required

Test normalization, replay/conflict, capacity rollback, snapshot revision/file
changes, selected accounts, cancellation before/after claim, stale completion,
duplicate completion, result storage failure, dispatcher progress without polling,
HTTP permission/ownership boundaries, route registration and migration safety.
Run the existing quote/login regression suites. SQLite verifies portable business
logic only; PostgreSQL tests must establish row-lock and concurrent admission
behavior. `tests/cnc/batch/test_batch_postgres.py` requires an explicit
`CNC_BATCH_PG_TEST_DSN` pointing to an isolated PostgreSQL test database; it
creates a uniquely named disposable schema per test and is skipped when the DSN
is absent. It covers serialized admission, `SKIP LOCKED`, competing Runs,
cancel/completion contention, and the migration's duplicate-result protection.
Live provider acceptance is a separate gate.

## 7. Wrong vs Correct

Wrong: update `config.quantity`, execute a shared JLC session, then swallow a
Result insert error while returning success.

Correct: freeze `requested.quantity` per Item, execute through the selected
account's fenced owner and durable Intent guards, then commit Run/Result/Item
completion together. Preserve unresolved remote actions for reconciliation.
Shortcut paths stop on export declarations; they must not infer a decision
from a missing legacy boolean or bypass the managed declaration flow. Missing
prices and lead times stay unknown rather than becoming zero or fabricated days.
JLC single and batch execution remain stopped until same-part, post-save
effective parameter readback has been reviewed; requested values are not evidence
of the values used by the platform.
