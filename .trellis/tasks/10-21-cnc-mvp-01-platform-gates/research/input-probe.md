# Read-only input probe

Run from the repository root with an existing Python 3.12+ interpreter:

```powershell
python -B .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/validate_inputs.py
python -B -m unittest discover -s .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research -p test_validate_inputs.py
python -m ruff check --no-fix --config backend/pyproject.toml .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/validate_inputs.py .trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/test_validate_inputs.py
```

The probe only reads the fixed A/B files in the authorized `E:/AIWorkspace/3d_models` directory and fixed parent research resources derived from its repository location. It compares size, SHA-256 and millimetre declarations against `step-samples-2026-10-21.md`; it does not validate CAD geometry, dimensions, part count or DFM. No source CAD contents, sessions or credentials are printed or written. There are no browser actions or configurable input paths.

For the three fixed platform JSON files (`xometry_us`, `jlc_cnc_cn`, `rapiddirect`) it checks platform/provider identity, the current local Schema version, a nonempty configuration version, draft/disabled automation and safety policies. D-17 prioritizes the first two; static validation of the deferred RapidDirect draft does not resume that provider. If the selected interpreter already has `jsonschema`, it additionally uses the existing `platform.schema.json` with `Draft202012Validator`. Otherwise that check is explicitly `NOT_EXECUTED`; no package is installed. SDK availability is outside this probe.

Exit code 1 means an input check failed; 0 means the executed static checks passed, with any `NOT_EXECUTED` checks still unverified. Live readiness is always `NOT_ASSESSED`, even if JSON readiness text claims a verified quote. Real account, geometry, configured-parameter, currency, price and lead-time evidence remains a separate platform gate. These checks do not deliver the runtime configuration loader or adapter.

The backend guideline pages are currently templates. These research scripts follow the repository's actual `backend/pyproject.toml` Python requirement and Ruff configuration; the isolated negative tests use standard-library `unittest` without importing the application or changing its dependency/test configuration.

Verified on 2026-10-21: system Python 3.13.0 passed the sample/config checks and both full Schema validations; backend `.venv` Python 3.12.13 passed the implemented input checks and reported Schema validation `NOT_EXECUTED` because that interpreter lacks `jsonschema`. All five negative tests passed on both interpreters; backend Ruff lint and format checks passed. An in-memory missing-sample simulation returned exit code 1 without changing any source file. None of these results verifies platform live readiness.

Current 2026-10-22 revision: three complete Schemas, 30 static checks and six negative tests passed; live checks remain NOT_ASSESSED. See [JLC config check](jlc-platform-config-check-2026-10-22.md). The 2026-10-21 results above retain their original two-platform/five-test scope.
