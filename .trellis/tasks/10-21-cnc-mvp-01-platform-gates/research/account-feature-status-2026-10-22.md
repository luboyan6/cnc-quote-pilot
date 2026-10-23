# Research: Account management implementation and user testing

- Query: Assess per-platform credentials, automatic login, session management, secure persistence, and repeatable user tests.
- Scope: internal; read-only source audit and coordinator-reported test execution
- Date: 2026-10-22

## Findings

The complete account-management product feature is **not delivered**. A reusable browser/session safety component exists and has isolated test evidence. No production CNC account CRUD/model/API/UI, platform credential resolver, real Xometry/JLC login adapter, durable session repository, or integrated expiry/reauthentication/human-resume flow was found. Existing application administrator authentication is a separate feature.

### Files found and code patterns

| File | Source-backed finding |
| --- | --- |
| `backend/app/modules/cnc/browser/contracts.py:25` | `SessionScope` binds owner/platform/account identifiers; it does not configure or persist usernames/passwords. |
| `backend/app/modules/cnc/browser/contracts.py:149` | Production `IntentStore` is an injected durable-store protocol; no default production in-memory implementation. |
| `backend/app/modules/cnc/browser/contracts.py:243` | `PlatformAdapter` is a protocol; `authenticate` at line 254 has no real provider implementation. |
| `backend/app/modules/cnc/browser/session.py:71` | `confirm_authentication` rejects challenge, expired/unknown status and wrong scope. It consumes adapter assertions rather than logging in itself. |
| `backend/app/modules/cnc/browser/session.py:93` | Export requires confirmed authentication and encrypts official Playwright cookies/origins/IndexedDB state in memory. |
| `backend/app/modules/cnc/browser/session.py:129` | `BrowserExecutor` admission/account exclusivity is process-local; distributed durable leases remain production work. |
| `backend/app/modules/cnc/browser/session.py:153` | A fresh context can receive encrypted state; all owned resources are cleaned on success/error/cancellation. No durable repository or automatic saving is performed. |
| `backend/app/modules/cnc/browser/state.py:17` | `SessionCodec(crypto)` requires injected crypto; validates full owner/platform/account envelope, ciphertext, cookie/origin host policy. It is not a persistent storage service. |
| `backend/app/utils/crypto_util.py:28` | Existing shared Fernet/HKDF encryption utility, separate encryption-key setting with fallback and old-key ring, can be reused. Its existence does not establish CNC credentials have been securely saved. |
| `backend/app/modules/cnc/browser/workflow.py:180` | Workflow calls injected adapter authentication, then checks scope/status before upload. No automatic credentials login implementation is present. |
| `backend/tests/cnc/browser/_support.py:50` | Tests use fresh real Fernet keys through `TestCrypto`; not configured production key/storage. |
| `backend/tests/cnc/browser/test_browser_e2e.py:1` | Real Chromium against intercepted synthetic pages, no provider credentials or live CNC platforms. |
| `backend/tests/cnc/browser/test_browser_e2e.py:288` | Synthetic encryption/restore/account-isolation test. Line 334 covers expiry/challenge stop, not genuine provider reauthentication. |
| `.trellis/tasks/10-21-cnc-mvp-02-first-quote/prd.md:20` | Planned minimum account and evidence persistence/API; F-03 at line 32 is unchecked session reuse/expiry acceptance. |
| `.trellis/tasks/10-21-cnc-mvp-02-first-quote/implement.md:9` | Task 02 remains planning; product implementation has not started. Lines 21/40 assign real auth, durable intent, ACL and encrypted-session integration. |
| `.trellis/tasks/10-21-cnc-mvp-03-second-platform/prd.md:38` | JLC integration depends on first-platform closure and separate provider evidence. |
| `docs/browser-test-report.md` | Component-only verification history, Windows/Linux scopes, and explicitly pending production stores/provider login. |

Search covered `backend/app/modules/cnc` (only browser component files) and `frontend/web/src` with CNC/provider/account identifiers. No CNC-specific account screen, API service, controller, schema/model, or production call constructing `BrowserExecutor` / `SessionCodec` was found. No credential values, environment files or browser/session material were inspected.

### Tests users can run now

In PowerShell from any directory (existing backend virtualenv/dependencies assumed):

```powershell
Set-Location E:\AIWorkspace\cnc-quote-pilot\backend
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/cnc/browser -p test_session.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -v
```

Coordinator reran both on 2026-10-22 for this answer: session 15/15 PASS (0.257 s); policy/files/state 10 executed, 9 PASS and 1 Windows symlink-privilege skip (0.078 s). These cover isolation, identity, encryption integrity/scope, and lifecycle behavior using SDK test doubles; they do not verify a real account password or provider login. Symlink skip is unrelated to account login and does not count as passed file-safety coverage.

Optional existing real Chromium **synthetic** test suite (browser already installed):

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = 'E:/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/playwright-browsers'
$env:CNC_BROWSER_E2E = '1'
$env:CNC_BROWSER_CHANNEL = ''
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/cnc/browser -p test_browser_e2e.py -v
```

Expected historical report: 11/11 PASS, zero skips, managed Headless Shell 145; system Chrome 155 also 11/11 PASS historically. Not rerun for this audit. Without `CNC_BROWSER_E2E=1`, skipped tests are not proof of browser behavior. This suite needs no real platform password and must not be described as real auto-login acceptance.

### Future product acceptance, currently unavailable

1. Configure separate authorized Xometry and JLC credentials in the application's future account screen/API; response must mask secrets and persistence must contain ciphertext, with another owner denied access.
2. Start in a clean managed context, log in with the configured account, verify identity, close context, rebuild and reuse persisted state after application restart.
3. Invalidate the state; observe bounded relogin or explicit human handoff. CAPTCHA/OTP/email verification must pause; the user can complete it in the browser without sending codes to chat.
4. Concurrent different accounts/platforms must stay isolated; the same account must not execute concurrently across workers. Disable/delete/update credentials must invalidate/reconcile associated sessions.
5. Inspect the future API, logs, checkpoint, database and evidence exports for plaintext secrets/tokens and wrong-owner access. Existing component cipher tests alone do not establish this product-wide result.

## Related specs

- `.trellis/spec/backend/browser-executor.md`: component boundary, injected encryption, account isolation, durable production stores/provider validation still required.
- `.trellis/spec/backend/index.md` and frontend index: checked; most general layer pages remain placeholders.
- `.trellis/workflow.md`: read for task/research boundaries.

## External references

None consulted; conclusions concern repository state. Installed SDK version and historical browser results are reported from `docs/browser-test-report.md`, not independently remeasured here.

## Caveats / Not Found

- Existing manual/controlled provider quote visits and page reload persistence are feasibility evidence, not product-managed authentication/session restoration.
- Encryption codec has no session lifetime policy or persistent store; provider state outside cookies/origins/IndexedDB still needs validation.
- Percentage completion would be misleading: component evidence and missing product behaviors are listed separately.
- No production code or tests changed; only this research file was written.
