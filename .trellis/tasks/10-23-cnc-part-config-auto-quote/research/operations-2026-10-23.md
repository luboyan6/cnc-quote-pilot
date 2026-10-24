# Authorized integration operations — 2026-10-23

This record contains no credentials, tokens or authenticated page content.

## Implementation authorization

After the final planning summary the user explicitly said “开始实施”. Task activated in_progress. Backend/frontend implementation and review run through native Trellis roles. Original user changes remain in the shared working tree and must not be reverted or staged wholesale.

## Temporary DNS repair

Actual managed browser probes first failed the unchanged egress policy because Clash Verge/Mihomo TUN DNS returned fake IPv4 addresses in 28.0.0.0/8 together with benchmark IPv6 2001:2::/64. Local read-only settings inspection confirmed enhanced-mode=fake-ip and those exact ranges.

The user approved the exact command running `research/quote_dns_override.py --apply`. The reviewed script loads only the existing local runtime configuration, adds exact DNS fake-ip-filter exceptions for the already registered login/provider resource hosts, and reloads a payload through the existing Windows controller pipe. No on-disk proxy configuration was rewritten; proxy routing and BrowserPolicy were unchanged. Dry-run and controller read checks were performed first. The generated file's pipe label was stale (sidecar-release); the existing production pipe with the identical private suffix was selected before sending any request. Early controller checks failed without mutation; final application returned HTTP204.

Postflight: www.xometry.com, www.jlc-cnc.com and auth.xometry.com returned only real public addresses. Managed anonymous Xometry login page became reachable. Separate actual configured-account login later exposed exact Conviva/Sentry telemetry resources; those are being reviewed as optional DENIED subresources, not allowed egress.

**Runtime DNS override remains ACTIVE while provider integration is being tested. Before the session ends, run the script's `--restore` action to restore the original disk configuration into memory, or explicitly document any user-approved reason to retain the temporary override.** Restoring it will reintroduce Fake-IP in this machine; permanent deployment DNS compatibility remains an operational requirement.

Official sources: [Mihomo DNS exceptions](https://wiki.metacubex.one/en/config/dns/) and [reload API](https://wiki.metacubex.one/en/api/). This is an environment diagnostic, not a product safety-policy override.

## Linked drawing authorization

Actual inventory found exactly one enabled configuration with an existing same-owner linked STEP and an enabled same-platform Xometry account. The linked part had upload_authorized explicitly false, surface finish absent and extra_params empty. There is no enabled JLC account.

Root asked the user specifically whether to authorize only this drawing for live quote acceptance. User answered “允许此图纸开启授权并实测”. `research/authorize_linked_sample.py` checked unique enabled config and same-owner part in a transaction, then changed only config_id=1's linked part_id=2 from upload_authorized=false to true and set its audit updater to its existing owner. No other drawing was modified. This persisted change is explicitly requested, so it must not be silently reverted when temporary DNS is restored.

## Exact sample specification

The user also explicitly selected “采用6061-T6x＋Standard” after root explained that the current material “铝合金” was ambiguous and finish absent. `research/configure_linked_sample.py` locked the unique enabled config, checked config_id=1 / part_id=2 and original values, then persisted material=`Aluminum 6061-T6x (Best Available)` and surface_finish=`Standard`. Quantity remains1 and other configurations were untouched. This is an approved business parameter update, not an inferred provider default, and must not be reverted during diagnostic cleanup.

## Quote persistence migration

`research/quote_db_preflight.py` read actual Alembic revision0ce906be2d99 and found neither quote table. Backend's isolated migration test passed: only new tables, constraints matching declared ORM models, and isolated round-trip downgrade. Root reviewed `alembic upgrade 0ce906be2d99:c9e3a6b72f14 --sql`: CREATE cnc_quote_run/cnc_quote_intent, indexes, and Alembic version update only.

The user approved `.venv/Scripts/alembic.exe upgrade c9e3a6b72f14`. It completed exit0. Read-only postflight confirms actual revisionc9e3a6b72f14 and both tables present. Existing business tables were not changed by this revision. Do not downgrade after live results exist merely to tidy the worktree.

## Verification completed so far

- Real DynamicRouterRegistry imports and OpenAPI generation expose exactly seven quote API endpoints under /cnc/cnc_part_config. FastAPI nested routers mean a flat app.routes loop reports zero; verify materialized OpenAPI or actual HTTP routing instead.
- Frontend implementation worker passed six suites/39 tests, lint, format/style and type-check; production build passed. Reviewer added lifecycle and actual reason/lead-time fixes and is running final checks separately.
- Backend isolated migration passed; fresh RBAC repository regressions passed13 tests; initial full original login regressions passed50, final quote-wide checks ongoing. Use agents' final reports for final counts.
- No real quote has yet been obtained. Public demo prices and observed UI controls are research only. Provider adapters and live acceptance remain in progress, not complete.
