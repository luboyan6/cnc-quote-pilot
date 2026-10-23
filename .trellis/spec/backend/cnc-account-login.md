# CNC account login and controlled browser

## 1. Scope / trigger

Read when changing account credentials/CRUD, login APIs, visible browser control, provider authentication or leases. D-18 is an approved login-only slice within task 02; it does not enable draft quote automation or satisfy the original quote/provider acceptance gates. Source design: [account-login-design.md](../../tasks/10-21-cnc-mvp-02-first-quote/account-login-design.md).

## 2. Signatures

Owners: `app/modules/cnc/login/{contracts,credentials,providers,repository,runtime,routes}.py`, existing `app/plugin/module_cnc/cnc_account/`, and the account Vue page/dialog/composable.

Base path: `/cnc/cnc_account`.

| Method / suffix | Result |
| --- | --- |
| POST `/login/{id}` | Start/reuse, ordinary response envelope containing LoginView |
| GET `/login/{id}/sessions/{session_id}` | LoginView |
| GET `.../frame` | Binary JPEG, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` |
| POST `.../input` | Strict LoginInput; LoginView |
| POST `.../verify` | Recheck identity and persist verified encrypted state; LoginView |
| DELETE `/login/{id}/sessions/{session_id}` | Close and release; LoginView |

Runtime: `LoginManager.start(AccountSnapshot)`, `command(snapshot, session_id, kind, payload=None)`, `revoke(account_id)`, `close_all()`. Persistent repository: `load(auth, id)`, `claim(snapshot, owner) -> token`, `renew(snapshot, owner, token, state=None)`, `release(snapshot, owner, token)`. Application shutdown closes login sessions before disposing the DB engine.

## 3. Contracts

- Input is account ID; address/credentials come from the server-side account and related platform. The platform model currently has name/login_url/quote_entry_url, not a trusted code/enabled registry. Resolve only Xometry US/JLC CNC by exact configured entry hosts, then validate HTTPS/443/no userinfo. Static asset hosts cannot be configured as platform entries.
- LoginInput forbids extras: click requires integer x in [0,1279], y in [0,719]; scroll requires integer delta_y in [-1500,1500], optional delta_x same bounds; key is a fixed enum; text is 1–256 characters. No arbitrary JS, URL, locator, file or clipboard API. Screen input is human-directed, not an Agent tool.
- LoginView contains session_id, account_id, platform_name, masked username, status, fixed reason, reused, viewport and expires_at. States: STARTING/AUTHENTICATING/READY/WAITING_HUMAN/FAILED/CLOSED. READY requires an exact match from the provider's authenticated identity endpoint and another check on the quote page. Cookie existence, URL, logout label, customer initials or typed username never suffice.
- Every operation uses update permission, reloads account owner/enabled/config/revision, and binds the activity to its actor. Ordinary account CRUD is creator-scoped with superuser access; an actor cannot inspect or revoke another actor's active session. Random session IDs do not grant access.
- The single owner task holds the existing BrowserExecutor session and Page. HTTP requests enqueue bounded commands; cancellation settles the active and queued futures. Closed-but-still-cleaning tasks must finish lease release before a new start. Default capacity 4, queue 16, input rate at most 10/s, idle 5 minutes, total lifetime 30 minutes; frame polling does not extend user activity.
- Claim/renew/state/release run in independent committed transactions. Claim is conditional and increments fencing token; renew checks owner/token/expiry/revision under lock and requires the final conditional UPDATE RETURNING id to return a row. Expiry during a lock wait cannot silently report renewal. Old release cannot clear a new owner's lease.
- Encrypt write credentials with existing CryptoUtil; legacy password is migrated to credential_ciphertext and cleared on controlled load/update. Empty password update preserves the old password. Username/platform/method/password changes revoke the prior state. OutSchema is independent from write DTOs; public query/export has no password, state, key or lease secrets. Terminal runtime snapshots clear plaintext password and encrypted state references.
- PrivateAccountRoute audits metadata only and sanitizes rejected input/storage failures before global development handlers. Account CRUD overrides the protected `_log_error` hook to omit traceback locals; other CRUD subclasses keep their prior exception logging. Engine constructors use `hide_parameters=True` and `echo=bool(settings.DATABASE_ECHO)`: an explicit debug setting must not log fetched credential/state rows. Keep aiosqlite at WARNING because driver DEBUG can print bound values despite engine hiding. Do not reintroduce `logger.exception` on account write failures.
- Provider identity fetch runs through the guarded Page/context, not an unguarded APIRequestContext. Xometry uses its hosted identifier/password form; JLC uses the native `#jlc-cas-login-window` iframe, preserving the CNC app's CAS callback. Unknown controls/timeouts stay manual without repeated submission. RapidDirect remains deferred.
- Optional tracking/QR resource hosts are a separate exact deny set in BrowserPolicy. They remain outside allowed_hosts and cannot resolve/connect through the proxy. Only their subresources/subframes are aborted without tainting the main page; top-level navigation, unknown domains, userinfo/non-HTTPS URLs and mixed/private/reserved DNS still stop. Defaults preserve the original strict behavior.
- Production requires the configured encryption key ring, matching Playwright binary and real public DNS. Multi-process deployments need account-affine routing or a single login worker; another worker returns unavailable rather than duplicating a browser. No personal browser profile, state file, screenshot log or token-bearing URL handoff is used.
- On Windows, `main.py` passes the importable `app.core.server_loop:subprocess_event_loop` to Uvicorn. Its Proactor loop supports Playwright subprocesses under reload/workers; the installed Uvicorn auto loop selects an unsupported Windows Selector in those modes. Other platforms retain auto. Test the actual configured factory with a subprocess, without starting the business app or database.

## 4. Validation and error matrix

| Event | Required behavior |
| --- | --- |
| Missing permission / different owner | Deny before pixels/input; no cross-actor revoke |
| Disabled/deleted/config/credentials changed | Revoke affected activity; no further command |
| Verified restored identity | No password resubmission; enter the quote page in the same context |
| Wrong identity | Fixed IDENTITY_MISMATCH; never overwrite with another login |
| Challenge / changed form | WAITING_HUMAN, visible same session; no bypass or blind retry |
| Expiry between lease read/write | Renewal fails; no following browser action |
| Active command cancellation / immediate close | Settle futures, finish browser/proxy cleanup and fenced release |
| Invalid input / SQL failure | Fixed safe response/audit, no raw body/parameters/ciphertext |
| Reviewed optional tracking resource | Abort; zero egress; page may continue |
| Optional host used for main navigation / unknown host | Policy stop |
| Reserved/mixed DNS | Refuse connection; report live integration unverified |

## 5. Good / base / bad cases

- Good: verified account identity, encrypted restoration after context closure, no credential POST on reuse, same browser pixels and fenced release.
- Base: real Chromium on synthetic HTTPS verifies selectors/lifecycle while real platform login remains unverified. State both results separately.
- Bad: treat a successful API response, generic dashboard, localStorage token or synthetic fixture as a real authenticated account; or return an external URL and claim it inherited the server context.

## 6. Tests required

`backend/tests/cnc/login/test_*.py` covers HTTP permission/body privacy, real service writes/export, actual independent SQLite lease transactions, owner-task failure/cancellation, provider identity and optional-resource denial. `browser_e2e.py` is an explicit managed Chromium run for the split form, native iframe, challenge, JPEG and closed-context restoration. SQLite transaction coverage does not prove PostgreSQL deployment. Frontend CNC account tests cover the API allowlist, button/form regression, serial polling/late responses, coordinate input, teardown and status display. Run narrow Ruff/basedpyright, frontend type-check/lint and production build. Do not count unavailable live checks as passed.

## 7. Wrong vs correct

```python
# Wrong: a selected row can expire while waiting for its lock.
await db.execute(update(Account).where(*fence).values(lease_until=deadline))
return  # Zero updated rows would incorrectly grant another browser action.

# Correct: the final write itself must confirm the current fencing predicate.
result = await db.execute(update(Account).where(*current_fence).values(lease_until=deadline).returning(Account.id))
if result.scalar_one_or_none() is None:
    raise LoginError("ACCOUNT_CHANGED_OR_LEASE_LOST")
```
