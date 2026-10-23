# CNC input and live validation

## 1. Scope / trigger

Read this before CNC configuration, adapter, runner, or acceptance work. The task-01 research probe remains separate from the shared [Browser Executor](browser-executor.md) component. Provider adapters, product APIs and real-platform quote integration are still pending. Source evidence is in [task-01 live validation](../../tasks/10-21-cnc-mvp-01-platform-gates/research/live-validation-2026-10-21.md) and the parent [configuration contract](../../tasks/10-21-cnc-pricing-mvp/research/platform-configs/README.md).

## 2. Signatures

From the repository root, Python 3.12+:

```powershell
python -B .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/validate_inputs.py
python -B -m unittest discover -s .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research -p test_validate_inputs.py
```

The separate isolated SDK fixture is run with its task-local interpreter:

```powershell
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.sdk-venv/Scripts/python.exe' -B .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/sdk_probe.py
```

Its exact environment pins and setup are documented in [SDK probe](../../tasks/10-21-cnc-mvp-01-platform-gates/research/sdk-probe.md). Do not install those pins into the application as an implicit side effect of running a research check.

The probe accepts no input paths, platform names, credentials, or environment settings. Source CAD paths and three platform research resources are fixed by the authorized task. The fixed registry is `xometry_us: xometry`, `jlc_cnc_cn: jlc`, and `rapiddirect: rapiddirect`; checking the deferred RapidDirect draft does not resume its live work. It does not open application settings or connect to the application database/browser.

## 3. Contracts

`Check(name: str, status: str, detail: str)` is the probe's local result. Status is `PASS`, `FAIL`, `NOT_EXECUTED`, or `NOT_ASSESSED`. Exit 1 means at least one executed input check failed; exit 0 does not clear an unexecuted Schema check or any live gate. If installed, `jsonschema.Draft202012Validator` validates the existing local Schema; no dependency is installed implicitly.

A/B expected byte size, SHA-256 and millimetre declaration come from the recorded sample identity. Platform identity must match the fixed platform/provider registry. Research configurations remain `lifecycle=draft`, `automation_enabled=false`. Their readiness strings never establish account, geometry, price or lead time. This probe is separate from the future runtime loader.

## 4. Validation and error matrix

| Condition | Required result |
| --- | --- |
| Same-length CAD bytes change | SHA-256 failure, exit 1 |
| Identity matches but length declaration is not millimetres | Unit failure, exit 1 |
| Platform/provider mismatch or enabled research automation | Input failure, exit 1 |
| Local `jsonschema` unavailable | Schema `NOT_EXECUTED`; never report full Schema validation as passed |
| JSON claims a successful live quote | Probe still returns live readiness `NOT_ASSESSED` |
| Upload row exists but dimensions/volume are zero | Geometry remains unverified; do not advance successful product workflow |
| Apply exposes further required parameters | Re-read all effective fields before any success or comparison |
| Quantity panel changes but edit/saved snapshot differs | Do not claim saved effective parameters or a recalculated quote |
| Missing amount/lead time, including a currency placeholder | Preserve unknowns; never convert to zero or `QUOTED` |

## 5. Good / base / bad cases

SDK boundary: the installed 0.7.29 filesystem surface includes `delete` in addition to `ls/read_file/write_file/edit_file/glob/grep/execute`. Verify the actual bound tools, not a remembered list; visibility exclusions do not replace permissions or custom-tool authorization. The fixture verifies a real DeltaChannel and typed decision with strict file-backed serialization across processes; it does not implement domain recovery or prove provider tool calling. On Windows, create the asyncio event loop before the fixture's socket block, since loop initialization itself requires an internal socketpair.

- Good: report local input checks independently from a time-stamped, same-configuration real quote with verified geometry, complete effective fields and evidence.
- Base: local checks pass while a platform still shows zero geometry and no price. Keep the live gate unmet and retain the no-price observation.
- Bad: mark E2/E3 or monitoring successful from the catalog's `is_auto_price`, a successful upload, a Schema check, or quantity text alone.

## 6. Tests required

The six current negative tests assert same-size tampering, wrong units, cross-platform identity, JLC's independent provider group, automation/payment guard changes, and a false readiness claim. Run both the probe and these tests after changing its code or research input contracts. Use the backend Ruff configuration for the scripts.

Future adapter tests must exercise the post-Apply effective-field readback, conflicting quantity displays, zero geometry and no-price branches. Live evidence is still required for E2/E3; a fixture cannot pass that acceptance gate.

## 7. Wrong vs correct

```python
# Wrong: source material metadata or a changed widget is not a quotation.
succeeded = catalog_option["is_auto_price"] and quantity_widget == requested_quantity

# Correct contract for the future product validator, not an existing API:
# require geometry + complete requested/effective parameter agreement + actual
# amount/currency/scope/lead time + freshness + same-run evidence before success.
```

Observed 2026-10-21: RapidDirect's initial Apply form showed process/material/Finish/Roughness/quantity. The next view also exposed cosmetic, tolerance, threads, inserts, marking and inspection. Its quote-panel quantity could differ from the still-visible edit form. Keep these as versioned observations with scope, not universal selectors or frozen business defaults.

### D-17 provider and price-nature revision (2026-10-22)

Current delivery order is Xometry US, JLC-CNC China, then deferred RapidDirect.
See [D-17](../../tasks/10-21-cnc-pricing-mvp/decisions.md) and
[JLC live evidence](../../tasks/10-21-cnc-mvp-01-platform-gates/research/jlc-live-validation-2026-10-22.md).
JLC's visible numeric prices carry an explicit system-estimate/reference disclaimer:
classify them as `REFERENCE_ESTIMATE`, never `QUOTED`. Unknown ISO currency,
material temper, source identity or shipping cost stays unknown. A displayed
coupon-after amount is neither an applied coupon nor a discount amount.

Xometry arrival labels are distinct from production durations. The current browser
component's duration-only `LeadTime` contract does not support those observations;
task 02 must reconcile it with the SRS and test the typed distinction before
enabling its adapter. This note does not claim that contract has been changed.
Never subtract assumed transit days or generic service minima to invent a duration.

If a mutation tool fails before returning a receipt, its delivery/effect is unknown.
Read back the same item before another mutation; a tab list, timeout or schema pass
does not prove whether the action ran. Do not replay a quantity change, upload or
submission to find out. Preserve last-confirmed and post-error states separately.


## 8. Fixed local CAD-kernel research contract (2026-10-22)

### Scope / trigger

Use only to investigate the recorded A/B/C zero-dimension discrepancy. This is a
task-01 research tool, not a CAD service, source converter, repair engine or
provider adapter. See [executed report](../../tasks/10-21-cnc-mvp-01-platform-gates/research/geometry-probe-2026-10-22.md).

### Signatures

From repository root, using the explicitly provisioned, ignored research venv:

```powershell
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' -B .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry_probe.py
python -B -m unittest discover -s .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research -p test_geometry_probe.py -v
```

`probe_sample(sample: Sample, path: Path, kernel_available: bool) -> dict` is a
research-internal test seam. Public normal CLI accepts no source paths, URLs,
credentials, platform selection or dependency-install flag. Hidden `--worker`
accepts only the fixed labels A/B/C and repeats recorded size/hash/unit validation
before native STEP import. Existing A/B record parsing and unit checks are reused.

### Contracts

Only fixed authorized A/B/C may be read. Confirm recorded bytes/SHA-256/mm before
CAD import and byte/hash/mtime identity after. Each native child has a 60-second
subprocess timeout; native stdout/stderr is captured, not copied into reports.
Use the isolated dependency snapshot, not backend pyproject/lock. No implicit
installation, file conversion/export, source scaling/healing or source mutation.

Each result has `local_only=true`; input checks and before/after fingerprints are
present only when those reads/checks succeeded. An unreadable source returns
`FAIL` and `identity_unchanged=false` without fabricating missing fingerprints.
`MEASURED` requires a valid BRep, 1–32 solids, finite bounds, exactly three strictly
positive dimensions, finite positive per-solid volumes with a consistent total,
and a non-boolean numeric 1.0 mm output unit. Require each bounds upper value
to exceed its lower value before tolerance-based comparison. OCP initializes the reader's output unit during
transfer: check `SystemLengthUnit()` **after** `TransferRoots()`, not before.

Report-level `platform_geometry_dfm_quote` stays `NOT_ASSESSED`. Normal CLI returns
0 only for all measured samples, 1 for a failed check/import/timeout/source-identity
change, and 2 for an unavailable kernel with no other failure. Missing dependency
is `NOT_EXECUTED`, not a successful text-parser approximation.

### Validation / error matrix

| Condition | Required behavior |
| --- | --- |
| Source hash/size/unit mismatch | Reject before native reader; no measured result |
| Kernel unavailable | `NOT_EXECUTED`, no metrics, exit 2 unless another failure exists |
| Timeout/native failure/nonfinite or inconsistent metric | `FAIL`; suppress native diagnostics; no success claim |
| Post-read source identity differs | `FAIL`; remove any measured metrics |
| Local valid BRep but provider still zero dimensions | Preserve both facts; remote geometry/DFM/price remain unpassed |
| Quote UI asks for export-control classification | Pause before Continue; page default/user scope permission is not a classification basis |

### Good / base / bad cases

Good: fixed fingerprints match, local kernel yields a valid nonzero solid, and the
report explicitly keeps remote geometry/DFM/quotation unassessed. Base: no kernel
is present; record exit 2 without inferring dimensions from STEP text. Bad: silently
convert/heal/reupload a model, infer a platform outage, or choose EAR99/No from a
filename, public origin, ready receipt or preselected radio button.

### Tests required

Run the new synthetic-byte geometry guard tests plus the five existing input
negative tests and backend-configured Ruff lint/format. Assert fixed identity
reconciliation, mismatched hash/wrong units before worker, missing-kernel handling,
nonfinite/zero/inconsistent metrics, timeout/error suppression and source-change
failure with metrics removed. A real-kernel run and before/after fingerprints are
separate from guard tests; neither passes any real platform gate.

### Wrong vs correct

Wrong: `source_has_solid = local_ok; platform_geometry_passed = source_has_solid`.
Correct: local importability is its own evidence; platform parsing needs a real
remote receipt/nonzero geometry and an actual price needs complete effective
parameters, currency/scope/lead time and freshness. Stop at new factual/compliance
declarations until the authorized user provides a basis; do not bypass the UI.


#### Guard-review lesson

The native worker is an independent entry path: validate the fixed source before
importing native code there as well as in the normal parent path. Python boolean
numeric equality and absolute comparison tolerances require explicit type and
positive-extent checks at the metric boundary. The 15-test suite includes direct
worker rejection before OCP imports, boolean units and zero/reversed tiny bounds.
Do not infer a static type pass from a successful native execution: the supplemental
research checks retain unresolved sibling/native OCP symbol diagnostics separately.
