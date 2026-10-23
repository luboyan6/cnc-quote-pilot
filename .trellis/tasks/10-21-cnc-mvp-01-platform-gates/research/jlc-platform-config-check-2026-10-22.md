# JLC-CNC draft configuration and fixed input checks

Date: 2026-10-22. Scope: task-01 research only. This is an implementation-side
configuration check, not independent live-provider acceptance or a product test.
The implementer did not operate a browser, upload CAD, change provider parameters,
request manual review, add to cart, place an order or pay.

## Decision and change boundary

The user's D-17 order is Xometry US first, JLC-CNC China second, RapidDirect third.
RapidDirect development is deferred until the first two providers and all existing
planned functionality are complete. Historical RapidDirect evidence remains;
no real-quote, two-provider or product acceptance gate is waived.

Files owned and changed by this implementation:

- Parent `research/platform-configs/jlc_cnc_cn.json`: new independent draft;
  `platform_code=jlc_cnc_cn`, `provider_group=jlc`, automation disabled.
- Parent `research/platform-configs/README.md`: current order, JLC observations
  and limitations, three-file static validation contract.
- This task's `research/validate_inputs.py`: extend the fixed registry to all
  three research configs; no paths/platforms accepted from CLI input.
- This task's `research/test_validate_inputs.py`: one added regression test,
  accepting the correct JLC identity and rejecting both other provider groups.
- This report.

The existing `platform.schema.json` already permits an independent provider code.
No schema, other provider JSON, dependency, application, task metadata, planning
artifact or context manifest was modified by this implementer.

## Evidence interpretation

The coordinator supplied an initial controlled UI observation at
`2026-10-22T05:57:18.282Z`. The new config preserves that observation as evidence,
separate from runtime bindings and catalog mappings:

- Clean entry is `https://www.jlc-cnc.com/cncOrder/#/placeOrder`; only observed
  `www.jlc-cnc.com` is allowed. Supplied tracking parameters are omitted. No auth
  or CDN host was inferred.
- Existing item label `292.1301C`, dimensions 28 × 25 × 9.5 mm, volume
  1967.6 mm³ and area 2135.64 mm² are recorded. It was not uploaded in this
  observation; neither local A/B identity nor remote bytes are verified.
- Current labels Al6061, blasting/anodizing in natural matte finish,
  GB/T1804-2000 m class, ordinary appearance and no threads are evidence only.
  No T6 temper, cross-platform equivalence, option IDs or required-field rules
  were inferred. All parameter bindings remain null, options empty, canonical
  mappings empty and observed unsaved selection null.
- Quantity 1 unit/line estimate 212.51, tax 27.63, total including tax 240.14;
  standard/rush/economy amounts 212.51/366.36/191.99 and observed workday counts
  6/3/11 are decimal-string amount snapshots. Workday counts do not establish
  start point, production or delivery semantics. Approximate coupon price 190.14
  was not applied and is not recorded as a discount amount or effective price.
- The page says `系统预估价` and limits the automatic amount to reference pending
  final manual-review pricing. It stays `REFERENCE_ESTIMATE`, never `QUOTED`
  or E2. The currency glyph is ¥; currency ISO code and UI locale code remain
  null, with no assumed CNY.
- STEP/STP required 3D, DWG/DXF/PDF supplementary, up to 20 files and `<100M`
  are UI declarations only. No byte conversion or upload boundary is inferred.
- `修改参数`, a quantity text input, `uploadFileBut`, `addCarCNC` and `提交询价`
  are recorded only as observed control evidence. No action binding is enabled.
  Cart/manual inquiry actions are forbidden; the submit-inquiry boundary remains
  unresolved and must be checked before a click.

At draft creation the coordinator's `jlc-live-validation-2026-10-22.md` and
`jlc-live-validation-2026-10-22.json` archives were pending. Their names in the
config are explicitly pending evidence references, not claims that those files
already existed or were independently verified by this implementer. The
coordinator owns their completion and evidence reconciliation.

## Executed verification

All commands ran from the repository root using existing interpreters/packages.
No dependencies were installed.

```powershell
python -B .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/validate_inputs.py
python -B -m unittest discover -s .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research -p test_validate_inputs.py -v
& 'backend/.venv/Scripts/python.exe' -m ruff check --no-fix --config backend/pyproject.toml .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/validate_inputs.py .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_validate_inputs.py
& 'backend/.venv/Scripts/python.exe' -m ruff format --check --config backend/pyproject.toml .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/validate_inputs.py .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_validate_inputs.py
```

| Check | Actual result |
| --- | --- |
| Read-only A/B size, SHA-256 and mm declarations | 6 PASS; no source writes |
| Fixed identity, versions, draft/automation and safety checks | 21 PASS across three configs |
| Full Draft 2020-12 Schema checks | xometry_us, jlc_cnc_cn, rapiddirect: 0 errors each |
| Live readiness | 3 NOT_ASSESSED, deliberately unchanged |
| Existing five negative tests plus JLC provider-group regression | 6 tests passed; exit 0 |
| Ruff lint with backend configuration, no fixes | All checks passed; exit 0 |
| Ruff format check | 2 files already formatted; exit 0 |

After the locale-null and coupon-field wording clarification, the full
input/Schema probe was rerun: all 30 executed checks passed, three live readiness
checks stayed NOT_ASSESSED, no check was NOT_EXECUTED, and exit status was 0.
No Python behavior changed after its successful test/lint run.

## Remaining work and risks

No runtime adapter/loader, quote extractor, managed authentication, complete
catalog, legal/terms conclusion, parameter equivalence, monitor, persistence or
live E2/E3 gate is delivered by these research files. JLC still requires source
identity reconciliation, valid quote semantics, currency evidence, full requested
and effective parameters, safe submission boundary and lead-time/commercial
context. The main session must reconcile the coordinator's later live evidence
with this timestamped initial snapshot before any readiness promotion. Historical
two-file probe/spec descriptions may require a small main-session documentation
update; they were outside this implementer's assigned ownership.
