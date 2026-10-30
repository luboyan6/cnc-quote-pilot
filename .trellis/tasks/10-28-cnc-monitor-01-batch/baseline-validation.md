# Implementation baseline — 2026-10-28

User explicitly requested starting the existing plan; task activated with `task.py start`.
Working tree initially contained 147 changed/untracked entries. Preserve prior work.

## Existing regression suite

Command from `backend`: `.venv/Scripts/python.exe -m pytest tests/cnc/quote tests/cnc/login -q`.
Result: **17 failed, 180 passed, 144 subtests passed**, 185.01 seconds.
Failures were in `login/test_providers.py` and `login/test_xometry_readiness.py`,
before this task changed login providers. Quote tests passed in this baseline.
Observed failures include accepting an unsettled quote shell or wrong identity,
and locator mocks inconsistent with `_first_visible`.
Narrow login provider review assigned because these affect B-AC07/B-AC08.

## Database acceptance environment

Default `tests/conftest.py` forces a temporary SQLite database.
No local PostgreSQL executables or port 5432 listener found.
Docker CLI exists, but Docker Desktop Linux engine pipe is absent.
Therefore SQLite checks cannot establish PostgreSQL row-lock/concurrent admission acceptance.
No existing business database was migrated or modified for this task.
