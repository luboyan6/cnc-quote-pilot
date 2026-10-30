# Incremental independent check — deployed editor variant

## Scope

Reviewed the new internal `XometryDOMBinding.part_config_variant` and its page-inspection branch in `backend/app/modules/cnc/quote/xometry.py`, plus the two focused regressions in `backend/tests/cnc/quote/test_xometry_adapter.py`. Loaded the saved native check context, current task design amendment, backend contract, deployed-source research, and implementation report. This is an incremental gate while the main session continues managed login and same-file live acceptance; it is not the task's final full-scope check.

## Findings (fixed)

None. No product or test edits were needed. This report is the reviewer's only edit.

The route inspector preserves blank query values. Legacy bindings reject every present editor-variant key; explicitly reviewed V2 bindings accept only one exact decoded `test` value. The query-free home uploader remains usable. Duplicate, empty, unknown and case-changed values reject, as do public test-drive and untrusted-host routes. The existing factory still raises `XOMETRY_BINDING_UNVERIFIED`; the change does not activate a provider. File, saved parameters, receipt revision and explicit-currency checks remain in the exercised path.

## Findings (not fixed)

No new concrete code defect was found. Production registration and the selected file's managed login/upload/parse/save/readback/current-result evidence remain separate unfinished task acceptance work owned by the main session. The current official source explains the deployed editor experiment, but neither that source nor locally fulfilled Chromium pages supplies a real quote.

## Verification

Commands ran independently from `backend` using the existing environment:

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/quote -p test_xometry_adapter.py -v` | **13 passed**, zero skips, 55.439 s |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/quote/xometry.py tests/cnc/quote/test_xometry_adapter.py` | Passed |
| `.venv/Scripts/ruff.exe format --check app/modules/cnc/quote/xometry.py tests/cnc/quote/test_xometry_adapter.py` | Both files already formatted |
| `.venv/Scripts/basedpyright.exe app/modules/cnc/quote/xometry.py` | 0 errors, 0 warnings, 0 notes |

All adapter-test requests were fulfilled locally. No live provider, credential, upload, declaration, configuration-save or quotation operation was performed by this reviewer. Unrelated login, frontend, browser, JLC and registry files were untouched. Their broad checks were not repeated for this incremental change.
