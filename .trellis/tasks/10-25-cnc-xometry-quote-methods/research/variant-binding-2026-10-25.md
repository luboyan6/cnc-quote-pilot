# Explicit deployed-editor variant binding — 2026-10-25

## Change boundary

The current official source and native links identify `vercel_part_config=test` as the deployed V2 editor experiment; see [source evidence](site-auth-source-2026-10-25.md) and the design amendment. The unconditional rejection lived in `XometryQuoteAdapter.inspect_page`. This change only makes that internal route distinction expressible; it neither registers a production binding nor supplies missing live receipt/readback evidence.

## Implementation

- `backend/app/modules/cnc/quote/xometry.py`: added internal `XometryDOMBinding.part_config_variant`, defaulting to `legacy`, with only `legacy` and `v2` accepted at binding construction. The page inspector preserves blank query values. A present variant key is accepted only for an explicit V2 binding and exactly one decoded `test` value. The ordinary no-query upload home remains usable. Default bindings reject all variant-key forms, including the previously ignored blank form.
- `backend/tests/cnc/quote/test_xometry_adapter.py`: two local Chromium regressions cover explicit/default binding behavior, unrelated query keys, empty/unknown/case-changed/duplicate variant values, public test-drive and untrusted-host rejection, unchanged production-factory rejection, and the same saved receipt/parameter/current-currency validation through the V2 route.

The existing file, identity, part, geometry, save revision, current-result, explicit currency, and no-replay contracts remain in force. No registry, login, settings, frontend, database, or unrelated source was changed by this worker. Other agents' changes were preserved.

## Verification

Executed from `backend`, against the existing installed environment:

| Command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/quote -p test_xometry_adapter.py -v` | 13 passed, zero skips, 56.325 s |
| `.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/quote/xometry.py tests/cnc/quote/test_xometry_adapter.py` | Passed |
| `.venv/Scripts/ruff.exe format --check app/modules/cnc/quote/xometry.py tests/cnc/quote/test_xometry_adapter.py` | Both files already formatted |
| `.venv/Scripts/basedpyright.exe app/modules/cnc/quote/xometry.py` | 0 errors, 0 warnings, 0 notes |

All Chromium traffic in these tests was fulfilled locally. No live browser/network, upload, declaration, configuration save, or quotation was performed. The focused tests do not establish current same-file managed acceptance. Production activation and actual V2 reader representations remain with the main session.
