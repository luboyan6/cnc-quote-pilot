# Independent site quote skills — completion and handoff

## Delivered

Completed the user's requested documentation work in order: updated the existing Xometry US skill, validated it, then created and validated the independent JLC CNC China skill. Both are installed in the project's discoverable shared skill directory:

- `.agents/skills/cnc-xometry-quote/SKILL.md` with its `references/observed-dom-and-evidence.md`.
- `.agents/skills/cnc-jlc-quote/SKILL.md` with its own `references/observed-dom-and-evidence.md`.

They support Playwright, official Chrome DevTools MCP and CDP bridge workflows. Xometry documents exact searchable material titles and separate Save Configuration; JLC documents its primary uploader and per-part 修改参数 candidate, tutorial/import distinctions, unverified editor details and reference-estimate/inquiry boundaries. Shared authorization, identity, file, intent and result invariants remain intact, but site controls and material mappings are independent.

The user authorized commands needed for this task without repeated confirmation and requested self-verification. That preference is scoped to this task; it does not classify a CAD file or reconcile an uncertain external operation.

## Verification completed

- Implementer validated Xometry before creating JLC; both passed final staged `quick_validate.py` using `python -X utf8`.
- Independent Trellis reviewer forward-tested three realistic requests against source artifacts: Xometry exact material/quantity with an uncertain upload, JLC formal-price comparison with no enabled account, and JLC tutorial/import/upload routing. Review PASS after fixing positive-money/lead-time wording, the conservative-upload-cap precondition and a provenance pointer. See `site-skills-independent-check-2026-10-24.md`.
- Installed exactly four reviewed Markdown documents. SHA-256 comparison matched every installed file to its reviewed staged source.
- Re-ran official `quick_validate.py` on both **installed** directories: `Skill is valid!`, exit 0 for each.
- Installed-copy link/identity check: 4 Markdown files, 2 relative links, 0 broken links, 0 reviewed-copy mismatches. Reviewer also checked 6 repository evidence pointers, all present.
- `node --check research/site_skill_browser_probe.mjs`: exit 0. The bounded live public-entry capture used the existing isolated official Chrome DevTools daemon; no new file upload or quote was submitted.

These are documentation/evidence checks. Frontend/backend suites and provider live quote acceptance were not rerun or counted as passed for this documentation-only change. No production application code or adapter registration was modified in this continuation. Existing unrelated working-tree edits were preserved. No task archive or commit was performed; the parent feature remains unfinished.

## Current application and browser findings

The existing local page still shows the earlier `PROVIDER_AUTOMATION_UNVERIFIED` failure with no price, idle row controls and no console errors/warnings. Ports 10006 and 5180 were listening. The adapter factory still returns None; the product cannot reach its third-party upload/configure/result operations.

Current Xometry material-picker observations belong to historical quote Q59-6980-1120 with `vercel_part_config=test`. Its quantity remains 5, versus requested quantity 1. The picker was opened and dismissed without selecting, saving or requesting a quote. These are scoped control observations, not normal-route acceptance.

Fresh JLC public entry evidence confirms `uploadFileBut`, mandatory primary STEP/STP, supplementary 2D formats, declared ≤20 files/<100M, the separate part-list import and first-visit tutorial. It is anonymous with empty history and no material editor. This continuation did not authenticate a JLC account or upload a file. Its public research page was created in the task-owned isolated DevTools session; existing user tabs were left intact.

Raw/concise sources: `site-skill-live-observations-2026-10-23.md`, `site-skill-browser-evidence.jsonl`, and the existing Chrome evidence log. Observations occurred before midnight on 2026-10-23 Asia/Shanghai; review/installation completed on 2026-10-24.

## Resume from here

Do not repeat skill creation or known fail-closed UI starts. First load the applicable installed site skill and its reference. Preserve research run `e8dea2c1-3430-4279-832e-1e655ced79b8` and its upload/uncertain intent; no reset or blind replay. Reconcile exact remote file identity/receipt before continuing that file's mutation workflow. Apply any already recorded exact-file declaration decision; if none exists, a command authorization is not a classification decision.

Xometry still needs normal managed-route controls, complete effective-parameter save/readback, positive exact-file geometry, same-run recalculation and money/currency/basis/lead-time evidence. JLC needs a currently enabled authorized account, authenticated upload/remote binding, actual material/finish/dependency/editor/save/readback evidence, current result context and a verified quote-only boundary for final pricing. Its system estimates stay REFERENCE_ESTIMATE.

Only after the respective platform evidence is sufficient should production adapters be implemented/registered and the original feature's live acceptance resumed. The existing task stays **in_progress**; neither provider has passed complete real quote acceptance.
