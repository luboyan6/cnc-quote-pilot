# Geometry probe independent review — 2026-10-22

## Scope and outcome

Reviewed task PRD/design/implementation boundaries, injected context, backend CNC validation spec including section 8, geometry code/tests, execution narrative, historical JSON and dependency snapshot. Only the three owned paths below were changed. No external research, network, package installation, browser use, product/shared metadata changes or source model mutation was performed.

Local behavior checks pass after three guard corrections. Supplemental static TypeCheck **fails**; do not claim universal green. No local measurement establishes platform geometry, DFM, quotation or an export-control classification.

## Findings (fixed)

File: `geometry_probe.py` (regressions in `test_geometry_probe.py`)

1. Direct hidden-worker entry imported OCP before checking recorded source identity/units. The normal parent CLI checked first, but direct worker entry did not. Moved its existing size/hash/unit check before all native imports. Added a synthetic test that fails if OCP is imported before rejecting either changed bytes or wrong units.
2. `True == 1.0` let a JSON boolean satisfy the millimetre output check. Require a non-boolean numeric type. Added `True` to existing invalid metric cases.
3. Zero/reversed bounds near zero could pass `isclose` absolute tolerance against a tiny positive dimension. Explicitly require upper > lower on each axis before dimension comparison. Added a two-case regression. Valid historical measurements are unchanged.

The original 13 tests remain; two new tests bring the suite to 15.

## Findings (not fixed)

### Supplemental type-check limitation

Backend config does not describe sibling research imports or its isolated OCP environment. The direct two-file command below returned exit 1, **13 unresolved imports**, zero warnings. A verbose single-file check using an absolute interpreter path confirmed inherited backend roots still applied (11 unresolved imports).

A temporary diagnostic config inherited backend rules, set the research directory as execution root/extra path and selected the existing `.geometry-venv`. This resolved modules but returned exit 1 with **10 unknown native OCP import symbols**, zero warnings: Bnd_Box, BRepBndLib, BRepCheck_Analyzer, BRepGProp, GProp_GProps, IFSelect_RetDone, Message, STEPControl_Reader, TopAbs_SOLID, TopExp_Explorer. Installed Python wrappers re-export the native extension without these statically exposed definitions. Actual kernel execution succeeds, but that is not a static type pass.

No diagnostic suppressions, stubs, dependencies or shared config changes were introduced. Temporary config was automatically removed. Coordinator owns any future typing/config decision; no more baseline investigation is needed here.

### Section 8 failure-shape wording

“Each result has ... input checks and before/after fingerprints” overstates failure guarantees. When the first fingerprint fails, the existing safe output is FAIL, local_only=true, identity_unchanged=false without before/after/input_checks/metrics. Confirmed using patched FileNotFoundError, no source read. Recommend qualifying these fields as conditional on successful reads; do not fabricate fingerprints. Coordinator owns spec edits, so left unchanged.

Otherwise section 8 matches the final implementation: fixed A/B/C labels, recorded bytes/hash/mm before native import, after fingerprints, 60-second subprocess bound, captured/non-forwarded native output, 1–32 solids, finite positive consistent geometry, unit after TransferRoots, local-only status, missing-kernel exit 2, failure exit 1 and local success exit 0. Export-classification stopping is a separate live-browser requirement; this local code performs no export or browser action and cannot satisfy that requirement.

## Verification: commands and results

All commands ran from repository root. Baseline original 13 geometry tests passed under system Python and isolated Python; five existing tests passed. Final commands:

```powershell
python -B -m unittest discover -s .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research -p test_geometry_probe.py -v
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' -B -m unittest discover -s .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research -p test_geometry_probe.py -v
& '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe' -B -m unittest discover -s .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research -p test_validate_inputs.py -v
ruff check --no-fix --config backend/pyproject.toml .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry_probe.py .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_geometry_probe.py
ruff format --check --config backend/pyproject.toml .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry_probe.py .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_geometry_probe.py
git check-ignore .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe
& backend/.venv/Scripts/basedpyright.exe --project backend/pyrightconfig.json --pythonpath .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/.geometry-venv/Scripts/python.exe .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/geometry_probe.py .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_geometry_probe.py
```

Results: 15/15 geometry tests system (0.046 s), 15/15 geometry environment (0.030 s), 5/5 existing input tests (0.004 s). Ruff `All checks passed!`; format `2 files already formatted`. Ignore check returned the ignored interpreter path. TypeCheck exit 1 as detailed above. No full backend suite was claimed.

Diagnostic temporary-config command was `python -B -` with the following exact stdin (PowerShell here-string piped to Python):

```python
import json
import subprocess
import tempfile
from pathlib import Path
root = Path.cwd()
research = root / '.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research'
config = {
    'extends': str(root / 'backend/pyrightconfig.json'),
    'venvPath': str(research),
    'venv': '.geometry-venv',
    'include': [str(research / 'geometry_probe.py'), str(research / 'test_geometry_probe.py')],
    'executionEnvironments': [{'root': str(research), 'extraPaths': [str(research)]}],
}
with tempfile.TemporaryDirectory(prefix='geometry-typecheck-') as directory:
    project = Path(directory) / 'pyrightconfig.json'
    project.write_text(json.dumps(config), encoding='utf-8')
    completed = subprocess.run([str(root / 'backend/.venv/Scripts/basedpyright.exe'), '--project', str(project)], check=False)
raise SystemExit(completed.returncode)
```

### Actual fixed geometry rerun

Executed 2026-10-22T02:43:25.494547Z–02:43:31.230706Z (**5.736159 s**), exit 0. A/B/C each MEASURED, local_only=true, one solid, valid BRep. All semantic metrics (unrounded bounds, dimensions, per-solid/total volumes, transfer counts, unit), package versions and source byte/hash/mtime fingerprints matched historical JSON **exactly**. Independent outer before/after fingerprints also matched.

| Sample | Dimensions mm (rounded) | Volume mm³ (rounded) |
| --- | --- | ---: |
| A | 28.000000 × 5.474000 × 25.000000 | 1860.842159 |
| B | 9.500000 × 28.000000 × 25.000000 | 1970.919831 |
| C | 9.000000 × 31.016821 × 31.016843 | 1402.385521 |

Historical JSON SHA-256 unchanged: `625ed97df47b3c0aa64c678fed2f9b3276094f663cf159de3928c2be07cad320`. Rerun JSON captured in memory only, never written over history. System Python without OCP also executed: exit 2; all samples NOT_EXECUTED, no metrics, source identity unchanged, platform NOT_ASSESSED.

Exact verification command: `python -B -` with this stdin (PowerShell here-string piped to Python):

```python
import hashlib
import json
import subprocess
import sys
from pathlib import Path
research = Path('.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research').resolve()
sys.path.insert(0, str(research))
import geometry_probe as probe
historical_path = research / 'geometry-probe-result-2026-10-22.json'
historical_digest = hashlib.sha256(historical_path.read_bytes()).hexdigest()
historical = json.loads(historical_path.read_text(encoding='utf-8'))
samples = probe.fixed_samples()
before = {s.label: probe.fingerprint(probe.SAMPLE_DIRECTORY / s.filename) for s in samples}
completed = subprocess.run([str(research / '.geometry-venv/Scripts/python.exe'), '-B', str(research / 'geometry_probe.py')], capture_output=True, timeout=190, check=False)
assert completed.returncode == 0, f'Geometry exit {completed.returncode}; diagnostics withheld'
current = json.loads(completed.stdout)
assert current['platform_geometry_dfm_quote'] == 'NOT_ASSESSED'
assert current['packages'] == historical['packages']
for old, new in zip(historical['samples'], current['samples'], strict=True):
    assert new['sample'] == old['sample']
    assert new['status'] == 'MEASURED' and new['local_only'] is True
    assert new['identity_unchanged'] is True
    assert new['before'] == new['after'] == old['before'] == old['after'] == before[new['sample']]
    assert new['metrics'] == old['metrics'], f'Metric mismatch for {new["sample"]}'
    probe.validate_metrics(new['metrics'])
    print(json.dumps({'sample': new['sample'], 'status': new['status'], 'solid_count': new['metrics']['solid_count'], 'brep_valid': new['metrics']['brep_valid'], 'dimensions_mm': new['metrics']['dimensions_mm'], 'volume_mm3': new['metrics']['volume_mm3'], 'fingerprints_and_semantic_metrics_match_history': True}))
after = {s.label: probe.fingerprint(probe.SAMPLE_DIRECTORY / s.filename) for s in samples}
assert before == after
assert hashlib.sha256(historical_path.read_bytes()).hexdigest() == historical_digest
print(json.dumps({'exit': completed.returncode, 'started_at_utc': current['started_at_utc'], 'finished_at_utc': current['finished_at_utc'], 'historical_json_sha256': historical_digest, 'historical_result_unmodified': True, 'source_fingerprints_unmodified': True, 'package_versions_match_history': True, 'platform_geometry_dfm_quote': current['platform_geometry_dfm_quote']}))
missing = subprocess.run([sys.executable, '-B', str(research / 'geometry_probe.py')], capture_output=True, timeout=30, check=False)
assert missing.returncode == 2
missing_report = json.loads(missing.stdout)
assert all(s['status'] == 'NOT_EXECUTED' and 'metrics' not in s and s['identity_unchanged'] for s in missing_report['samples'])
assert missing_report['platform_geometry_dfm_quote'] == 'NOT_ASSESSED'
assert before == {s.label: probe.fingerprint(probe.SAMPLE_DIRECTORY / s.filename) for s in samples}
print('System Python missing-kernel CLI: exit 2; all A/B/C NOT_EXECUTED; no metrics; fingerprints unchanged; platform NOT_ASSESSED.')
```

### Section 8 missing-file shape experiment

`python -B -` with this stdin returned exit 0 (assertions passed):

```python
import sys
from pathlib import Path
from unittest.mock import patch
research = Path('.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research').resolve()
sys.path.insert(0, str(research))
import geometry_probe as probe
with patch.object(probe, 'fingerprint', side_effect=FileNotFoundError):
    result = probe.probe_sample(probe.fixed_samples()[0], Path('synthetic-unreadable.step'), True)
assert result['status'] == 'FAIL' and result['identity_unchanged'] is False
assert all(field not in result for field in ('before', 'after', 'input_checks', 'metrics'))
print('Section 8 failure-shape check: unreadable input FAIL; identity_unchanged=false; no before/after/input_checks/metrics. Spec wording needs qualification.')
```

## Changed paths (reviewer only)

Relative to `.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/`:

- `geometry_probe.py` — three guard corrections.
- `test_geometry_probe.py` — two new regression tests plus boolean-unit negative case.
- `geometry-check-2026-10-22.md` — this record.

Historical JSON, requirements, implementation narrative, task/shared metadata, backend dependencies and source CAD were not edited. Collaborator work was preserved. No implicit reupload, model healing/conversion, platform pass or task-02 entry approval follows from this review. Keep RapidDirect zero-geometry/no-price evidence and Xometry export-classification stop separate.
