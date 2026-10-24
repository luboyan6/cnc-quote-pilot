# Independent site-skill review — 2026-10-24

## Scope and disposition

**PASS for the two staged documentation skills after the local fixes below.** This is an independent local-artifact review and forward-test, not a live provider test. It permits installation of the reviewed skill documents; it does not establish production adapter readiness, a successful upload, a current final quote, or completion of the parent auto-quote task.

Reviewed staging folders:

- `research/skill-staging/cnc-xometry-quote/`
- `research/skill-staging/cnc-jlc-quote/`

Paths above are relative to this task. Only these staged documents and this report were changed. No browser, upload, account, external request, application code, production skill directory, intent store or adapter registration was mutated. No commits were made. The skill-creator guidance and task check context were loaded before review.

## Findings fixed

1. `cnc-xometry-quote/SKILL.md`: the short QUOTED definition omitted the shared contract's positive finite money and known lead-time requirements. It now explicitly requires positive geometry, positive finite decimal-string amount and known lead-time context in addition to exact effective parameters, currency, basis and freshness. This is a documentation contract correction, not evidence that extraction works.
2. `cnc-jlc-quote/SKILL.md`: step 1's instruction to stop on an unverified upload limit could contradict step 4's allowance for a reviewed conservative local cap below the declared `<100M`. Step 1 now stops when that reviewed cap is unavailable. The provider's byte convention and numerical boundary remain unverified; no conversion or concrete cap was invented.
3. `cnc-xometry-quote/references/observed-dom-and-evidence.md`: added the existing reconciliation report as a direct provenance pointer for the historical quote/quantity mismatch. The handoff facts were already supported by it.

## Forward-test 1: Xometry, exact material title, quantity 1, unresolved upload

Applied **cnc-xometry-quote** only. The requested `Aluminum 6061-T6x (Best Available)` is an exact option title; a long description, popularity marker or price glyph is not part of that title. `Aluminum 6061-T651, Plate` and `Aluminum 6061-T6/T6511, Bar/Rod` remain distinct choices.

The next permissible continuation is read-only: inspect the authorized current page with fresh references, verify intended account/ownership, reread the frozen configuration/file authorization and hash, and reconcile the earlier claimed/uncertain upload against an authoritative remote receipt. In this evaluation those are described future actions only; no page was operated. The existing quantity-5 historical page does not satisfy quantity 1, and its filename does not prove remote byte identity. Its amount cannot be reused or divided by five.

Because that upload has no confirmed receipt, this request cannot yet proceed to another upload, parameter save or new quote as an evasion of reconciliation. If reconciliation fails, stop and report the unresolved operation. If it later succeeds, honor any exact-file declaration decision already recorded; obtain the actual decision if missing, without inferring it from a default radio selection. Then freshly inspect the correct page variant, exact material-title field, dependencies, finish and quantity; record the appropriate mutation intent, save once, and read back the complete effective values and current result. The historical `vercel_part_config=test` DOM does not establish normal managed-route bindings. No QUOTED result is supported now.

## Forward-test 2: JLC formal quote and comparison, no enabled account

Applied **cnc-jlc-quote** for JLC, with Xometry guidance used only to interpret any separately established Xometry evidence. The request's lack of an enabled authorized JLC account is a concrete automation blocker. The recorded project inventory supports that condition as of its observation; it does not imply that no future account can be configured. Recheck authorized current configuration when work resumes; do not borrow a personal browser identity or another actor's account.

The displayed `系统预估价 ¥212.51` and manual-audit disclaimer permit only a qualified observation of **REFERENCE_ESTIMATE**. In the supplied historical evidence its exact current-file/current-run identity is unproved. The symbol alone does not establish CNY. `提交询价` remains untouched until current no-order side effects are established; neither its name nor lack of payment settles that boundary. The historical uncertain quantity-plus action also requires read-only reconciliation before another change.

“6061、自然色哑光” does not establish a T6 temper or fully choose blasting/anodizing and its subchoices. Preserve the user's words, discover the actual supported editor options and resolve any missing or ambiguous finish requirement before changing parameters. Do not adopt the historical `喷砂+普通阳极氧化 / 本色 / 哑光` as an implicit requested default. No final JLC quote is available for a like-for-like comparison with Xometry; differences in alloy/temper, finish, quantities, price scope, currency and result nature must remain explicit. Formal-price ranking is unsupported.

## Forward-test 3: JLC tutorial, import list and primary uploader

Applied **cnc-jlc-quote** only. `下一步` and `跳过` under `上传图纸文件(1/2)` are first-visit walkthrough controls. `#exportModelBut` / `导入零件清单` imports a part list. The primary CAD upload candidate is `button#uploadFileBut` / `拖拽或上传图纸文件`, with one observed native file input. A fresh current snapshot is needed before using any control; dismissing the tutorial, if necessary and freshly confirmed, does not authorize uploading a file.

Explain or prepare that path without pretending a material editor is already visible. Before actual upload, require the authorized account, exact linked STEP bytes/hash, third-party permission, reviewed cap and durable intent, then use the official file-input/chooser helper once. The current anonymous page has no material or quantity editor. After a confirmed/reconciled upload and parsing, inspect the existing-part `#material-box .change-info` / `修改参数` candidate and discover its real controls, material/finish options, dependencies and save semantics. Their selectors and saved-value extraction are not verified. Do not invent radio IDs or select a presumed alloy/finish; stop at an unknown committing control until its semantics are established.

## Evidence and operational consistency

- Compared JLC historical values, quantity-click uncertainty, material/editor gaps and order boundary with task-01 `jlc-live-validation-2026-10-22.md` and `jlc-platform-config-check-2026-10-22.md`. Both staged references preserve historical versus current scope and reject cross-site material/finish equivalence.
- Checked the 2026-10-23 current-observation report and raw `site-skill-browser-evidence.jsonl`: JLC's UTC timestamp `2026-10-23T15:55:59.836Z` is 23:55:59 on the same date in Asia/Shanghai. The canonical no-hash landing, uploader, native accept list, empty history and tutorial distinction match the raw projection. The 2026-10-24 review date does not redate those observations.
- Checked `xometry-upload-evidence.json`, the reconciliation report and `provider-live-evidence-2026-10-23.md`: the single prior buffer upload, declaration stop, unresolved receipt, quantity-5 mismatch, public demo/shadow-root controls and normal-route limitations are kept separate. The Xometry historical material popup remains explicitly unselected/unsaved.
- The documented identity endpoints agree with existing provider evidence. Auth is verified from explicit identity, not initials/cookies or dashboard presence. Raw identity responses, auth state, signed URLs and credential-bearing logs are excluded from retained evidence.
- Both skills require fresh current tool references and official file helpers. Generated option IDs and this machine's daemon paths/session IDs are not reusable bindings. Playwright, official Chrome DevTools MCP and CDP-bridge guidance preserve page ownership and stop on unknown/stale controls.
- The earlier provider research's strict mixed-DNS diagnosis is identified as superseded in the JLC reference. Neither skill authorizes a policy bypass. Existing `backend/app/modules/cnc/quote/providers.py::resolve_quote_adapter()` still returns `None`; documentation validation does not change that boundary.
- The skills are independently discoverable by their names/descriptions and contain one linked site-specific reference each. Neither requires loading the other to perform its own site workflow. No placeholders, duplicated generic manual, account secrets or private token URLs were found in the staged package.

## Verification

- Skill format: `python -X utf8 C:/Users/admin/.codex/skills/.system/skill-creator/scripts/quick_validate.py <staged folder>` passed separately for both folders after fixes (`Skill is valid!`, exit 0).
- Local Markdown links: 2 checked, 0 missing. Repository source pointers: 6 checked, 0 missing. External URLs were reviewed as previously recorded evidence sources; no live fetch was made in this local-only review.
- Behavioral forward-test: all three cases above preserve the permitted next action and stop conditions; no missing evidence was replaced with a fabricated selector, account, price, classification or parameter mapping.
- Lint: not applicable to Markdown-only staging changes; no application code changed.
- TypeCheck: not applicable to Markdown-only staging changes.
- Tests: the two validators, link/source checks and local-artifact behavioral review passed. No frontend/backend suite or live test was run or counted as passed.

## Findings not fixed / remaining acceptance limits

No unresolved material defect remains in the reviewed staged documents. Installation and validation of the installed copies belong to the coordinating session.

Live acceptance remains incomplete: Xometry needs authoritative reconciliation of the uncertain upload, exact-file declaration authorization if not already recorded, normal managed-route verification, full parameter save/readback, linked positive geometry and current-run money/currency/basis/lead-time evidence. JLC needs an enabled authorized account, exact-file upload/remote binding, resolution of any applicable uncertain quantity action, actual editor/material/finish/dependency/save/readback verification, current estimate evidence, explicit currency/price/lead-time context and a proven quote-only path to any final price. Neither provider adapter should be enabled on the strength of this documentation review. The parent task remains in progress.
