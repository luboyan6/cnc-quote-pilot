# Read-only local CAD geometry research — 2026-10-22

## Result and diagnosis boundary

**Executed successfully in a local CAD kernel, not a platform acceptance.** The final bounded run was 2026-10-22T02:32:20.680536Z–02:32:26.718121Z (10:32:20–10:32:26 Asia/Shanghai), exit 0. Raw numeric results, exact package versions and before/after fingerprints are in `geometry-probe-result-2026-10-22.json`.

| Fixed sample | Transferred roots / output shapes | Solids | Local BRep valid | Axis-aligned X × Y × Z (mm, rounded) | Solid volume (mm³, rounded) |
| --- | --- | ---: | --- | --- | ---: |
| A | 1 / 1 | 1 | true | 28.000000 × 5.474000 × 25.000000 | 1860.842159 |
| B | 1 / 1 | 1 | true | 9.500000 × 28.000000 × 25.000000 | 1970.919831 |
| C | 1 / 1 | 1 | true | 9.000000 × 31.016821 × 31.016843 | 1402.385521 |

These are analytic-surface, axis-aligned bounding extents in the imported orientation, not fitted diameters, toleranced manufacturing dimensions or inferred design intent. The full precision values are in JSON; small bounding margins are numerical, not asserted dimensional tolerances. In particular, C's filename is not a measured 5 mm thickness.

All dimensions, bounds and volumes passed finite-value checks; dimensions and each solid volume were strictly positive. Output system length unit was confirmed as 1.0 mm **after** transfer. The source declarations independently passed the existing millimetre check.

Inference limited to the experiment: the authorized byte-identical A/B/C files can yield nonzero, locally valid single-solid BReps using this OCP/OCCT import. A claim that these sources necessarily contain no importable/nonzero solid is inconsistent with this result. This does **not** identify RapidDirect's zero-dimension root cause, prove the remote bytes are identical, establish compatibility with another parser, guarantee source semantics absent importer processing, or demonstrate manufacturability. No platform geometry, DFM, material suitability, price, lead time, quote or product workflow gate passed here. Existing RD zero dimensions/no-price observations remain separate coordinator evidence. No browser or Xometry export-control action/classification was performed by this worker.

## Source identity / read-only guarantee checked

Only the three explicitly authorized files were opened. A/B identities are parsed with existing `validate_inputs.recorded_samples`; C is reconciled between the parent candidate hash and task-01 live-validation record. No model directory traversal or other model read was performed.

| Sample | Bytes before = after | SHA-256 before = after |
| --- | ---: | --- |
| A | 300561 | `364dcf18796a0613f7453984faf66c510be980905b4f0991aa9fda06a58c8d6c` |
| B | 1929001 | `d3884475c50c336e3f13e5ca1665605104dc1ccc4113e962c62bff46b21e25e6` |
| C | 3609635 | `038fe7d3d464c57bfc0cb0856954f1f6bbf78b152f6db9a67ede92dbd8ea7cc7` |

Modification-time nanoseconds also matched before/after for each sample and are retained in JSON. No writer/exporter, mesh generation, scaling, explicit healing, source conversion or source overwrite was called. STEP import necessarily constructs an in-memory BRep using kernel translator behavior; this experiment does not claim the translator never performs internal normalization. No CAD bytes, mesh, kernel diagnostics, source path or model fragment was sent to an external service/model. Only package/documentation requests used the network. Reports contain controlled sample labels, fingerprints and numerical summaries.

## Discovery and environment

Read-only discovery checked PATH for `FreeCADCmd`, `FreeCAD`, `gmsh` and Python modules `OCP`, `cadquery`, `FreeCAD`, `OCC`, `gmsh` in:

- System Python 3.13.0, MSC v.1941 AMD64: none of the five modules.
- Existing backend Python 3.12.13, MSC v.1944 AMD64: none.
- Existing task research SDK Python 3.12.13: none.
- `C:/Program Files/*FreeCAD*`: no matching installation directory; no named CAD executable on PATH. This is bounded discovery, not an exhaustive disk scan.

Created `research/.geometry-venv/` using the existing backend Python executable, without modifying that environment. Windows platform reported `Windows-11-10.0.26100-SP0`. Python is `3.12.13 (main, Mar 10 2026, 18:15:39) [MSC v.1944 64 bit (AMD64)]`; uv `0.12.1 (329541a50 2026-07-31 x86_64-pc-windows-msvc)`; Ruff `0.15.20`.

Installed `cadquery-ocp==7.8.1.1` (OCP reports 7.8.1.1; bindings target OCCT 7.8.1) into that environment only. Its resolver pulled 13 transitive packages, including VTK 9.3.1; no full CadQuery dependency was requested. Exact 14-package snapshot: `geometry-probe-requirements.txt`. The binary-only installation resolved in 2.64 seconds, prepared in 38.23 seconds and installed in 4.71 seconds. No prolonged build or additional install attempt was needed. The environment's generated `.gitignore` contains `*`; `git check-ignore` confirmed its interpreter is ignored. No backend manifest/lock or shared ignore file was edited.

An optional `uv python list --only-installed` failed on access to uv's pre-existing user cache. It was not needed for kernel discovery or the task; subsequent required setup explicitly used `--no-cache` and the already-known interpreter. No cache permissions were changed.

## Reproduce from repository root (PowerShell)

Actual setup commands:

```powershell
uv venv --no-cache --python 'E:/AIWorkspace/cnc-quote-pilot/backend/.venv/Scripts/python.exe' '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv'
uv pip install --no-cache --python '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' --only-binary :all: 'cadquery-ocp==7.8.1.1'
uv pip freeze --no-cache --python '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe'
```

For a fresh environment with the exact executed dependency set, replace the single-package install with:

```powershell
uv pip install --no-cache --python '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' --only-binary :all: -r '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry-probe-requirements.txt'
```

Executed final run (PowerShell redirection writes only the report, never a model):

```powershell
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' -B '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry_probe.py' | Set-Content '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry-probe-result-2026-10-22.json' -Encoding utf8
# Inspect $LASTEXITCODE immediately: executed result was 0.
```

The public CLI accepts no input path, directory or platform. An internal `--worker A|B|C` selects only fixed sample identities. Each worker repeats fixed size/hash/unit checks before the CAD reader sees the source path. The parent fingerprints before/after and discards measurements on identity changes. Workers have a 60-second subprocess timeout each (three fixed sequential samples; at most 180 seconds of kernel waits), a 32-solid cap and no shell invocation. Native stdout/stderr is captured, not forwarded; only validated JSON is retained. The internal worker entry is not the standalone fingerprint-report interface; reviewers should use the no-argument CLI for the complete experiment.

A missing OCP returns `NOT_EXECUTED` with **no geometry metrics** and exit 2. An executed check/import/timeout/identity failure returns exit 1. Exit 0 means only local measurements succeeded, never a live readiness pass. The normal system Python was additionally executed through a captured subprocess: exit 2, all A/B/C `NOT_EXECUTED`, no metrics, all fingerprints unchanged.

## API evidence and implementation correction

Primary upstream references were fetched read-only as documentation (HTTP 200), not by browser, with no sample data in requests:

```text
https://raw.githubusercontent.com/CadQuery/OCP/7.8.1.1/README.md
https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_1/src/BRepBndLib/BRepBndLib.hxx
https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_1/src/BRepGProp/BRepGProp.hxx
https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_8_1/src/STEPControl/STEPControl_Reader.cxx
```

Installed binding docstrings were also inspected for signatures. `AddOptimal_s(shape, box, False, False)` does not request triangulation or shape-tolerance enlargement. `VolumeProperties_s(solid, props, True, True, False)` uses closed shells, skips shared faces and does not use triangulations. `BRepCheck_Analyzer(shape).IsValid()` supplies the limited local BRep check; it is not a DFM or full self-intersection guarantee.

The first probe conservatively failed because it checked `SystemLengthUnit()` immediately after `ReadFile`, which returned 0.0 before transfer. A bounded diagnostic on fixed A found `xstep.cascade.unit=MM`, 1 transferred root and `SystemLengthUnit()=1.0` after `TransferRoots`. The check was moved after transfer; no unit override, scale or source change was used. The successful final JSON supersedes that development-run failure. No fabricated metrics were substituted.

## Tests / checks executed

```powershell
python -B -m unittest discover -s '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research' -p 'test_geometry_probe.py' -v
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' -B -m unittest discover -s '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research' -p 'test_geometry_probe.py' -v
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' -B -m unittest discover -s '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research' -p 'test_*inputs.py' -v
ruff check --no-fix --config backend/pyproject.toml '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry_probe.py' '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_geometry_probe.py'
ruff format --check --config backend/pyproject.toml '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry_probe.py' '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_geometry_probe.py'
```

Results: 13 new tests passed under both Python versions; 5 pre-existing input negative tests passed in the geometry environment; Ruff lint and formatting passed after formatting only the two new files. New tests cover same-size hash mismatch (no kernel call), wrong units despite matched hash, missing kernel, changed synthetic bytes during import (discard metrics), timeout, safe exception reporting, finite/positive and internally consistent metrics, fixed-label bounded subprocess and rejection of nonfinite worker JSON/native failure. Fixtures mutate only temporary synthetic declarations, never the authorized models. The real local run is separate from mocked guard tests. No product/backend full suite or platform acceptance was run.

## Changed paths / follow-ups

All deliverables are new files under `.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/`:

- `geometry_probe.py`
- `test_geometry_probe.py`
- `geometry-probe-result-2026-10-22.json`
- `geometry-probe-requirements.txt`
- `geometry-probe-2026-10-22.md` (this report)

Local ignored runtime: `.geometry-venv/`. Shared records, task metadata, product sources, backend dependencies, other environments and source models were not edited by this worker. Existing edits from collaborators were preserved. Code/results were announced reviewer-ready before writing this narrative report; independent review remains the coordinator's responsibility.

Remaining: platform-specific existing-record/geometry diagnosis and real quote/DFM acceptance still require their own authorized evidence. The local result does not justify another upload, model conversion, automatic export-control declaration, RFQ, transaction, or advancing task 02 past unmet entry gates.


## Coordinator integration after independent review

The initial 13-test result above is preserved as history. Final
[independent review](geometry-check-2026-10-22.md) fixed three guard edge cases,
increased the suite to 15 passing tests and reran the real kernel with identical
metrics and source fingerprints. Ruff/format and five original input tests pass.
Supplemental static typing is not green; research import roots/native OCP symbols
are documented without suppressions or product dependency changes. Spec section 8
now qualifies fingerprints/checks for unreadable-source failure output. Live gates
and the pending Xometry export-classification declaration remain unchanged.
