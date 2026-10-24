# Research: Current provider access and automation evidence

- Query: Establish current managed-runtime access, exact upload/configuration/readback/quote controls, safe no-order triggers and evidence gaps for the approved auto-quote feature.
- Scope: mixed (repository evidence, live controlled browser, desktop research)
- Date: 2026-10-23

## Findings

### Current controlled runtime, actually executed

The existing read-only `10-21-cnc-mvp-02-first-quote/research/guarded_login_probe.py` was run using `backend/.venv/Scripts/python.exe` and the installed `.trellis/.runtime/playwright-browsers` binary directory. It uses production `BrowserExecutor`, `SessionCodec`, exact provider policies and fresh anonymous contexts. It does not read saved accounts, submit credentials, upload or request a quote.

- Sandbox run at local 13:10:51–52: Xometry US and JLC CNC each returned fixed `browser_failed`; proxy independently logged `browser egress policy_blocked`; unknown host collection empty.
- Per network-failure requirements the identical command was repeated with explicit escalation, approved by user. Run at local 13:31:30–31 had the same result for each platform. This is a fresh current failure, not merely historical evidence.
- No authentication, file upload, parameter mutation or quote took place. Quote adapters cannot be promoted on these results.

Current `socket.getaddrinfo(..., 443, SOCK_STREAM)` answers were then read without connections:

| Host | IPv4 | IPv6 | IPv6 is_global |
| --- | --- | --- | --- |
| www.xometry.com | 28.0.1.46 | 2001:2::120 | false |
| login.xometry.com | 28.0.0.159 | 2001:2::9b | false |
| api.xometry.com | 28.0.1.49 | 2001:2::123 | false |
| www.jlc-cnc.com | 28.0.0.161 | 2001:2::9c | false |
| passport.jlc.com | 28.0.1.50 | 2001:2::124 | false |

`backend/app/modules/cnc/browser/policy.py:90` requires every resolved address to be global and rejects mixed answers. Its refusal is expected. IPv4 classification alone cannot authorize discarding the IPv6 answer. Do not hardcode IPs, monkeypatch DNS, disable IPv6 or relax guard logic to make a probe green.

The concrete external prerequisite is real public DNS resolution for these provider and approved dependency hosts in the execution environment. The machine has a running `clash-verge` desktop app, but this research has not inspected or changed its settings; the exact responsible resolver/proxy configuration is unverified.

### Repository controls, exact observed candidates and limits

- `backend/app/modules/cnc/browser/files.py`: official helpers `upload_step(locator,payload)` and `upload_step_with_chooser(page,trigger,payload)` accept verified STEP buffer; no path re-read by browser.
- `backend/app/modules/cnc/login/providers.py`: fixed identity queries and account matching already exist. Xometry `https://api.xometry.com/v2/users/me` reads explicit email fields; JLC `https://www.jlc-cnc.com/cncPortal/login/queryLoginUser` reads explicit account/email/phone fields. Login iframe/form is documented in spec. Neither endpoint is a quotation API.
- Historical Xometry exact DOM candidates from `xometry-controls-2026-10-22.json`: `#option-select-process`, `#option-select-cnc-subprocess-select`, `#material-select-material-select`, `#finish-select-finish-multiselect`, `#option-select-tolerances-radio-metal`, `#option-select-surface-roughness-select`; switch IDs for threads/inserts; inspection and certification IDs. The JSON explicitly sets `bindings_runtime_verified=false`. Generated `_r_*` option IDs are transient. No save/readback mutation was verified there.
- Xometry historical safe quote-only flow is native file input, `Start Instant Quote`, export declaration `confirmed-not-itar` and `Continue`; subsequent quote remained separate from checkout. It used the specifically approved sample directory and D-16 declaration. This evidence does not authorize defaulting arbitrary linked files to No or reusing personal session as managed acceptance.
- Xometry 150MB is Supporting Files text, not a verified CAD upload limit. Complete current upload and price locators absent. Historical 6061-T6x/Standard/tolerance choice must not be mapped approximately to AL6061/ISO2768M.
- JLC historical observed candidates `#uploadFileBut`, `#material-box .change-info`, unique visible `input[role=spinbutton]`. No actual controlled parameter-save/readback implementation verified. Upload UI declares STEP/STP, <=20 files, individual <100M; bytes unit not independently verified.
- JLC `addCarCNC` is add-to-cart and forbidden. `提交询价` was not clicked; no-order semantics are unverified. Historical official guide couples audit quotation to a subsequent order/details workflow; stop before that trigger until current safe semantics are established.

### Historical same-file/parameter/freshness evidence is limited

- `xometry-b-live-quote-2026-10-22.md`: B uploaded once, local SHA-256 and size recorded; resulting quote had positive 28 ×25 ×9.50mm/1970.97mm³ geometry. Quantities 1/2/5 changed and cards recomputed; qty5 persisted after reload. It establishes controlled manual feasibility and a no-checkout example, not exact remote byte checksum or current managed runtime binding.
- `jlc-live-validation-2026-10-22.md`: pre-existing B-like item only, remote byte identity unknown. Positive geometry and amount but expressly “系统预估价” and final manual audit disclaimer. Only `REFERENCE_ESTIMATE`, never `QUOTED`. ¥ alone did not independently establish ISO currency.
- Research JSON in `10-21-cnc-pricing-mvp/research/platform-configs/` remains draft with automation disabled and null extraction locators. It cannot be loaded as production trusted adapter.

## External references

- JLC official order/quotation guide: https://www.jlc.com/portal/server_guide_37967.html (historically read 2026-10-22; current page recheck pending).
- Xometry official process: https://www.xometry.com/how-xometry-works/ (historical source only at this point).
- No private URLs, account IDs, credentials, tokens or raw authenticated DOM retained here.

## Related specs

- `.trellis/spec/backend/browser-executor.md`: exact egress, owner task, durable intents, file buffer, positive geometry, complete effective parameters and explicit current quote freshness.
- `.trellis/spec/backend/cnc-account-login.md`: same controlled browser identity checks, exact hosts and lease/privacy requirements; live deployment separate from synthetic acceptance.

## Caveats / Not Found

Production upload/configure/extract capability is not implemented by historical evidence or this probe. Returning `PROVIDER_AUTOMATION_UNVERIFIED` is honest but does not satisfy the requested working auto-quote feature.

Desktop research follow-up: `computer-use` and `orca-cli` skills read; installed Orca guide read from `orca skills get`. Sandbox could not read Orca runtime metadata; approved `orca open --json` outside sandbox found runtime ready. Read-only desktop list succeeded with escalation. Chrome's current window was local DevTools; Firefox/Opera window titles unrelated to CNC. Embedded Orca tab list was empty. No existing account quote session was found by this window inventory; inactive tabs were not enumerated or read.

### Current public Xometry demo DOM (2026-10-23, local 13:35–13:40)

An approved new Orca tab to `https://www.xometry.com/testdrive/` rendered successfully. Its public CNC sample `Fly Wheel.step` was selected once using the observed semantic button. No private drawing, account or order was involved. Subsequent snapshot confirmed `You are test-driving the Instant Quoting Engine`, sample name and 95×95×9mm dimensions. These sample-only prices are not real linked-file quote results.

New current primary-upload evidence: both sample-picker and sample configuration display `Max Size of 150MB per file` beside supported CAD formats. This establishes a current public primary uploader's declared limit, superseding the narrower historical observation that 150MB had only been seen for supporting files. Exact byte convention/boundary not tested; 150,000,000 is a conservative engineering limit only, not a verified binary boundary.

Top-level DOM has exactly one `input[type=file]` with accept including `.step,.stp`; no ID or name. The current public demo parameter form lives inside `HTML-LOFT` open shadow DOM and nested open component shadow roots. Plain `document.querySelectorAll` misses most controls; official Playwright Locators pierce open shadow roots. This demo differs from the historical authenticated quote's React DOM candidates and cannot automatically replace them.

Current demo control values (read via recursive, read-only DOM attribute projection):

| ID | Type / role | Readback |
| --- | --- | --- |
| quantity-input | number | 1 |
| process-combobox | text / combobox | CNC |
| cnc-subprocess-select-combobox | text / combobox | No Preference |
| FilterableSelectSub1-combobox | text / combobox | Aluminum 6061-T6x (Best Available) |
| finish-multiselect-combobox | text / combobox | Standard |
| threads-and-tapped-holes-checkbox | checkbox | false |
| inserts-checkbox | checkbox | false |
| tolerances-looser-metal | radio | false |
| tolerances-false-metal | radio | true (±.005in / ±0.13mm, with reamed-hole exception) |
| tolerances-true-metal | radio | false |
| surface-roughness-select-combobox | text / combobox | 125uin/3.2um Ra |
| standard-inspection | radio | true |

Other inspection radio IDs: formal-inspection, cmm-inspection, fair-inspection, source-inspection, build-hold-inspection, custom-inspection, all false. Part marking checkbox IDs: silkscreen-checkbox, ink-stamp-checkbox, bag-and-tag-checkbox, engraving-checkbox, laser-mark-checkbox, all false. Certificate IDs: itar-ear, cmmc-cert, as9100, iso9001, hardware-cert, c-of-c-cert, material-traceability, jcp-certified, material-cert, all false. These sample defaults are observations, never business defaults for arbitrary files.

Semantic locator candidates observed in current accessibility snapshot: `get_by_role('spinbutton', name='Quantity', exact=True)`, combobox names `Process`, `Search Preferred Subprocess`, `Search Material`, `Search Finish`, `Smallest Roughness`; named checkboxes Threads and Tapped Holes/Inserts. No production SDK mutation or save/reload readback verified on this demo.

Demo price group shows three offers: Made in USA 4 Business days / $672.81, Made in USA 5 Business days / $662.52, Made Internationally 8 Business days / $225.84; quantity1 unit and line same. All are sample display only. Observed `.leadTime` with `span.blurrable`; monetary span classes are generated `css-*`, unsuitable as trusted stable production selectors. Do not return these as results or derive original live quote extraction from them.

### Current official no-order semantics (re-read via web, 2026-10-23)

`https://www.xometry.com/how-xometry-works/` (How to Use the Xometry Instant Quoting Engine), current web extraction lines 259–290: upload, Edit Configuration, change material/finish/quantity/etc, live prices update and Save Configuration; checkout and Place Order are separate later steps. This supports quote-only semantics, but not current authenticated DOM bindings or application acceptance.

`https://www.jlc.com/portal/server_guide_37967.html` (updated 2024-12-12, re-read today), current extraction lines 31–52 and 100–104: default parameters yield online quote after upload; modify parameters; then Submit Order enters details; completed order details enable manual audit quote. This reinforces the current need to classify system estimates independently and stop before unverified order-coupled inquiry trigger. It does not prove all independent inquiry channels are impossible.

Root independently diagnosed Clash/Mihomo TUN fake-IP DNS matching the observed ranges, and owns any external network adjustment/approval. This researcher did not modify network settings. Further managed probes after that change are pending separately.

### Managed recheck after root's approved temporary runtime DNS change

Root applied exact-host runtime fake-IP exceptions through the existing Mihomo named pipe, with user approval, leaving production BrowserPolicy unchanged. With that override active, the same escalated anonymous guarded probe was actually re-run:

- Xometry: `PUBLIC_LOGIN_PAGE_VISIBLE`, origin `www.xometry.com`, unknown hosts empty. This is anonymous page access, not authentication.
- JLC: `browser_failed`, unknown hosts empty. No credentials sent. This later error did not have the earlier proxy policy warning; underlying network failure still needs diagnosis.

`managed_provider_inspect.py` in this research directory then exercised actual enabled platform-account data using existing `LoginRepository` and `LoginManager`, production `BrowserExecutor`, encrypted credential reader, independent persistent account lease transactions, single browser owner and bounded lifetime. It does not upload or place an order. It allows only metadata/control projection, and suppresses exception strings and logger output so secrets cannot be printed. All started owner tasks were awaited/closed with repository release in the official cleanup path. No manual DB permission or authorization fields changed.

Current safe inventory (aggregate only):

- One enabled account, for Xometry; credentials available; no saved encrypted browser state. No enabled JLC account.
- One enabled configuration, with an existing nondeleted linked part and matching part/config owner; exactly one enabled account matches its platform and owner.
- That linked part's `upload_authorized` is explicitly **false**. Consequently there are zero currently authorized linked-file quote inputs. It must not be silently changed to true; this is a concrete user-data prerequisite distinct from network/code readiness.
- Material present, surface finish absent, extra parameter keys empty. No assumptions about desired finish or additional machining requirements are authorized by this data.

The real account's official managed login reached quote entry but was refused by strict request observation before verified login completion. The observed current unknown dependency hosts are:

1. `d2d1457e431c55589cd6869389fcdc7da348eb3d.appgw.conviva.com`
2. `sentry.mgmt.global.xmtr.io`

No failures were observed for allowed-host requests in that run. Both managed attempts ended fixed `policy_blocked`. These appear related to telemetry by naming but that classification is inference; reviewer must confirm exact resource types/source before adding exact optional-resource denial, never automatically allow egress or extend policy from untrusted page text. The inspection script now records host/resource type/navigation on future runs to support that review.

### Current real entry DOM using ordinary Orca research only

Separate newly-created public research tabs (not managed account acceptance) were inspected read-only:

- Xometry `https://www.xometry.com/quoting/home/`: heading `Upload a 3D model to see instant pricing, lead time, and DFM feedback.`; native unique `input[type=file]`, no ID/name, accept includes `.step,.stp`; button text `Upload 3D Files`. This corroborates current real entry's native upload locator. No file selected.
- JLC `https://www.jlc-cnc.com/cncOrder/#/placeOrder`: native unique `input[type=file]`, no ID, `multiple=true`, accept `.stp,.STP,.step,.STEP,.zip,.ZIP,.rar,.RAR,.pdf,.PDF,.dwg,.DWG,.dxf,.DXF`; `button#uploadFileBut` text `拖拽或上传图纸文件`; Login and Skip controls visible. Current text declares <=20 files and individual <100M. No upload selected, no inquiry trigger.

Current Xometry normal app asset version observed (public no-query source): `/quoting/f2a0abe95eba64c6489707d33f36836523930363/resources/instant-quote-app.30062e772837939cc52f.mjs` and same version's `/env.js`. Static asset references could provide implementation research, but none of their private API payloads has been reverse-engineered or activated here.

Owned public research pages: Xometry testdrive `80e3d0f7-6343-44bb-8ba4-77e701f081c9`, Xometry real home `398d975f-ddb2-4094-9773-67da8e68a411`, JLC real entry `80656bf6-1cdf-4e46-af0e-6735176628e2`. They contain no private uploaded files or managed credentials. Their page identities/indices were freshly enumerated at final handoff; the researcher closed these three owned tabs in reverse index order after recording evidence. The actual managed account session was also closed with official lease cleanup.

### Exact public source checks for optional telemetry review

The current normal quote page's public asset URLs above were fetched through that page with `credentials:'omit'`; only fixed booleans, byte lengths and matched term names were returned, never source contents or DSN values.

- `/quoting/f2a0abe95eba64c6489707d33f36836523930363/env.js`: HTTP200, 2,438 characters; contains exact `sentry.mgmt.global.xmtr.io`, configuration term `SENTRY_DSN`, five case-insensitive Sentry mentions and three Conviva mentions. No exact account-specific Conviva hostname appears as literal.
- `/quoting/f2a0abe95eba64c6489707d33f36836523930363/resources/instant-quote-app.30062e772837939cc52f.mjs`: HTTP200, 2,470,459 characters; contains `SENTRY_DSN`, `captureException`, `Conviva`, `appgw.conviva.com` and `telemetry`; 176 Sentry mentions and268 Conviva mentions. The exact observed hashed Conviva hostname is not a literal in the minified app; its runtime request is the exact source of that hostname.
- These establish error/usage instrumentation integration by actual official source plus actual managed request, without requesting or inspecting those telemetry endpoints. Recommendation to product owner: add the **two exact observed hosts only** to reviewed optional subresource denial after confirming no navigation use. Do not add them to `allowed_hosts`, use wildcard Conviva/Sentry rules, or allow their DNS/egress. Existing optional denial excludes top navigation and retains strict policy. Fully demonstrate optionality by blocked telemetry plus successful actual login/quote in the next managed run; this researcher has not completed that test.

## Executable handoff

1. With root's temporary DNS override still active, run `backend/.venv/Scripts/python.exe -X utf8 -B .trellis/tasks/10-23-cnc-part-config-auto-quote/research/managed_provider_inspect.py --inventory-only` for safe read-only prerequisites; no account lease/browser starts in this mode.
2. Without `--inventory-only`, script uses the official manager and returns unknown resource hosts/types/navigation and safe current DOM after actual identity verification if reachable. It must not be run concurrently with another actor's account activity. Existing persistent lease enforces refusal.
3. Resolve reviewed optional telemetry denial in product owner files, rerun managed probe, inspect authenticated real form. Do not promote public demo candidates into production before this actual same-owner check.
4. Before any linked-file upload, obtain explicit applicable upload authorization through the normal part configuration flow (currently false), and sufficient exact finish/extra parameter choices. Do not auto-infer empty finish.
5. No enabled JLC credentials currently exist, so JLC actual-account acceptance additionally requires a configured authorized account. Support public DOM research and precise REFERENCE_ESTIMATE semantics meanwhile; do not fake QUOTED.

The present state is: meaningful current upload-entry evidence plus implemented generic runner capability, **no verified production provider adapter**, no current linked-file upload authorization, and no live successful quote. These are separate remaining conditions, not interchangeable tests.
