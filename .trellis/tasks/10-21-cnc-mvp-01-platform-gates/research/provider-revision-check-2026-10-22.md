# D-17 provider revision: independent scoped review

Date: 2026-10-22. Active task: `10-21-cnc-mvp-01-platform-gates`.
This reviews the current D-17 planning/configuration/input-probe revision and
the archived JLC/Xometry controls/lead-time evidence. It is not a browser,
account, provider permission, runtime adapter or full-product acceptance run.
No browser/network/account interaction, CAD mutation, commit or archive was
performed by this reviewer. Other agents' existing changes were preserved.

## Findings (fixed)

### PR-01: reconcile JLC archives without replacing the historical snapshot

- Files: parent `research/platform-configs/jlc_cnc_cn.json` and its `README.md`.
- Issue: the initial config accurately said the two evidence archives were pending
  **at draft creation**, but did not reconcile their subsequent completion or
  the later unknown quantity-change receipt and official order-guide evidence.
  After adding current evidence, the README's “current only” initial-observation
  description also needed reconciliation.
- Fix: incremented JLC `config_version` from `2026-10-22.1` to `2026-10-22.2`;
  appended `JLC-ARCHIVE-RECONCILIATION-20261022` with both existing archive refs,
  last-confirmed read/quantity, unknown post-attempt quantity, no replay and the
  old-guide/current-button distinction. Added the unknown-receipt readiness
  limitation. Preserved the original timestamp and initial archive-status string
  as history, and updated README wording/links to distinguish both scopes.
- No new live observation is claimed. Tool failures are time-scoped evidence,
  not proof of a permanent transport blocker. A subsequent successful read must
  be recorded by its operator before changing the current-state conclusion.
- Verification: all three full schemas and all 30 executed static checks passed
  again after the JSON fix; README/config refs and spec links resolve.

## Findings (not fixed)

### PR-02: supplemental research typing remains failed

The backend-configured research check was actually rerun:

```powershell
& 'backend/.venv/Scripts/basedpyright.exe' --project backend/pyrightconfig.json .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/validate_inputs.py .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_validate_inputs.py
```

It returned exit 1, **1 error and 2 warnings**:

- `test_validate_inputs.py:8`: sibling `validate_inputs` import unresolved under
  the backend project (`reportMissingImports`).
- `validate_inputs.py:107–108`: optional `jsonschema` and
  `jsonschema.exceptions` source unresolved (`reportMissingModuleSource`).

This reproduces the already-recorded research/environment scope limitation;
unittest and the system-Python full Schema checks run successfully. No new
type diagnostic attributable to the JLC registry change appeared. A dedicated
research typing environment/configuration is a broader tooling decision; no
backend configuration, import path, diagnostic level or dependency was changed
to hide this result. There is no universal type-check pass.

### PR-03: existing duration-only component cannot represent arrival labels

The Xometry lead-time research correctly separates arrival estimates, production
durations and shipping. Existing `backend/app/modules/cnc/browser/contracts.py`
`LeadTime` and `workflow.py` quote validation remain duration-based; current
Xometry arrival-only observations cannot simply be filled into that contract.
Task 02's design/implementation plans now explicitly own the typed contract,
API/persistence/snapshot alignment and regression work before adapter enablement.
This is a public/shared contract change outside the present research revision;
the reviewer did not modify production types or weaken validation. Raw private
component `leadTimeDays=7`, generic service minima and assumed transit days are
insufficient evidence for a production-duration conversion.

### Remaining live/product gates (not defects repaired by this static review)

- **Xometry first-provider handoff:** retain complete source-to-remote-item/
  receipt/geometry association, actual authorized identity/session evidence,
  requested/effective parameter and save/readback verification, same-offer
  amount/currency/scope/freshness, and interpretable lead-time/commercial
  context. A/B controlled numeric prices and same-quote UI reloads are partial
  evidence, not full E2/E3. Product automatic authentication, encrypted session
  reuse/rebuild and persistence are owned by 02/03; their unfinished
  implementation must not become an impossible task-01 prerequisite. Remote
  byte hashes are not required where unavailable; a verifiable association is.
- **JLC:** existing `292.1301C` is not a newly witnessed original-B upload;
  matching name/dimensions do not prove byte identity. The explicit reference
  disclaimer requires `REFERENCE_ESTIMATE`, not `QUOTED`/G-05/E2. ISO currency,
  complete parameters/temper/equivalence, valid definitive pricing, quantity
  2/5, freshness, commercial and lead-time context remain incomplete. Last
  archived confirmed quantity is 1; the one failed 1→2 request has unknown
  delivery/effect. Read back before another mutation, never replay to discover
  whether it ran.
- **JLC submission boundary:** the official 2024-12-12 guide has concrete
  order/review coupling, while the current button says “提交询价”. This does not
  prove every possible current quote path requires an order, nor establish a
  safe order-free final-price path. Keep the current stop before inquiry/cart/
  order submission until the actual path is reconciled. No provider replacement
  or new transaction permission is inferred.
- **Product 02–05:** first-provider automatic flow, second-provider E2/E3,
  monitoring/history/batch/Web/CSV, managed sessions and formal real-Agent
  recovery acceptance remain unfinished. Existing SDK fixtures do not pass
  real model/tool calling or provider live gates.

## Cross-task consistency

- Parent and 01–05 metadata agree: `xometry_us / xometry` first,
  `jlc_cnc_cn / jlc` second, RapidDirect third/deferred. Six task metadata
  checks and 18 PRD/design/implementation current-order headers passed.
- 02 requires task-01 Xometry E2 plus BR; 03 additionally requires 02 closure
  and task-01 JLC E2; 04 requires both product flows; 05 requires 02–04.
  RD zero geometry is historical/deferred and is not a predecessor. JLC's
  incomplete E2 does not itself prevent a qualified first-provider handoff.
- Parent/01 remain `in_progress`; 02–05 remain `planning`. No task completion,
  live checkbox or full product claim was introduced.
- D-17 retains FR-01–06, AC-01–13/P0, independent-provider real `QUOTED`, two
  samples × two providers × quantities 1/2/5, two monitoring rounds and ten
  items per provider. RD is excluded from current batch/success denominators
  until first-two complete functionality/acceptance. Existing P1/P2 boundaries
  and the prohibition on purchasing/payment/final orders remain intact.
- Platform JSONs stay draft/automation disabled; JLC mappings/options/bindings
  remain unknown rather than copied from Xometry/RD. Decimal price scope,
  unknown ISO/tax/shipping fields, unapplied coupon-after value and raw
  lead-time limitations are preserved.
- Xometry control IDs are scoped locator candidates, React IDs are transient,
  Supporting Files 150MB is not a primary CAD limit, and public tolerance
  descriptions do not establish ISO/GB equivalence. Cancel without a new
  save/readback is not presented as runtime binding or configuration success.
- Older unanswered D-16/permission/stop and original provider-order records
  remain explicitly historical under current D-15/D-16/D-17. The initial JLC
  snapshot's pending archives are likewise historical after PR-01. No other
  newly introduced false current/historical acceptance claim was found in
  the reviewed revision.

## Verification

Commands ran from repository root using existing interpreters/packages; no
dependency installation or product-wide test rerun was needed for this scoped
research/configuration revision.

| Check | Actual result |
| --- | --- |
| `python -B .../research/validate_inputs.py` | PASS, exit 0: 30 executed checks; three live checks NOT_ASSESSED; no NOT_EXECUTED |
| Complete Draft202012 Schema validation | PASS for xometry_us, jlc_cnc_cn and rapiddirect; zero structural errors each; repeated after config correction |
| `python -B -m unittest discover -s .../research -p test_validate_inputs.py -v` | PASS, 6 tests, exit 0 |
| Backend-configured `ruff check --no-fix` on both changed Python files | PASS, exit 0 |
| Backend-configured `ruff format --check` on those files | PASS, 2 already formatted, exit 0 |
| Supplemental backend-configured basedpyright | FAIL, exit 1: 1 error / 2 warnings, retained above |
| Strict JSON / JSONL (duplicate keys and nonfinite constants rejected) | PASS: six task JSONs, four platform/schema JSONs, JLC result and controls JSON; 12 JSONL files / 234 entries |
| Manifest target existence | PASS, all 234 entries resolve |
| Top-level planning Markdown local links | PASS, 24 files / 198 local links; no missing targets |
| Metadata/current-order planning assertions | PASS, six task metadata/statuses and 18 current-order/gate headers |
| Post-fix JLC archive/README and updated spec links | PASS |
| Product/real browser/live/model tests | NOT RUN by reviewer; this report does not promote live gates |

Ruff/unittest were run against the JLC-extended Python files before the reviewer's
JSON/Markdown-only correction; Python code was unchanged after those passes.
The existing A/B local identity probe is read-only and does not establish
remote upload, provider geometry, DFM or a real quote.
