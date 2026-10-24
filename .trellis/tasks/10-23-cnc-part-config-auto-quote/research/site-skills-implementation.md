# Site-specific quote skills implementation

Completed on 2026-10-24 Asia/Shanghai for the existing `cnc-part-config-auto-quote` task. Scope: staged skill documentation only, Xometry US first and JLC CNC China second. The user requested independent site skills because quote actions and material selection differ.

## Files prepared for review and installation

All skill paths below are under this task's `research/skill-staging/`:

| File | Change |
| --- | --- |
| `cnc-xometry-quote/SKILL.md` | Preserve original name/description; add authoritative identity endpoint, page-variant distinction, exact material-title matching and separate save intent/readback requirements |
| `cnc-xometry-quote/references/observed-dom-and-evidence.md` | Preserve prior uncertain-upload and quantity-5 history; add scoped current configuration/material-popup observations, dated public research sources and explicit acceptance gaps |
| `cnc-jlc-quote/SKILL.md` | New independent discoverable skill with its own upload/editor flow, identity check, mutation handling, estimate interpretation and inquiry/order boundary |
| `cnc-jlc-quote/references/observed-dom-and-evidence.md` | Separate fresh anonymous canonical-entry evidence from historical existing-item controls, uncertainty and reference estimates; retain exact unknown mappings and limits |

The existing Xometry directory was copied in full before editing. It contains only `SKILL.md` and its reference; no existing `agents/openai.yaml` was present. Its frontmatter is unchanged. JLC uses required name/description frontmatter and normal automatic discovery without an explicit-only policy. No unnecessary scripts, generic router, assets or placeholder files were added.

## Evidence and implementation choices

Current observations are grounded in `research/site-skill-live-observations-2026-10-23.md` and `research/site-skill-browser-evidence.jsonl`, supplied by the coordinating session. Earlier same-date public demo, uploader and official-guide observations come from `research/provider-live-evidence-2026-10-23.md`; the skill implementer read those saved sources and did not perform live browser actions.

Xometry configuration candidates remain scoped to the historical quote route with `initialTab=Configure&vercel_part_config=test`; normal-route and managed-account behavior are unverified. Opening/dismissing the material popup selected nothing and saved nothing. Distinct alloy/temper/product-form titles are not collapsed by substring matching. Historical quantity 5/dollar amounts cannot satisfy target quantity 1. Existing export-declaration requirements and the uncertain frozen-buffer upload remain intact.

JLC's fresh anonymous entry landed on `/cncOrder/` without a hash. The primary upload, part-list import and tutorial controls are distinguished. No current material editor/quantity control exists on that empty-history entry. Historical `修改参数` is a candidate only; modal options/save/dependencies remain unobserved. JLC material/finish/tolerance labels are not equated to Xometry labels. Its system estimate remains `REFERENCE_ESTIMATE`; `¥` alone supplies no ISO currency, and `提交询价` has unresolved order semantics. Historical uncertain quantity-change outcome is preserved.

## Checks executed

Xometry was completed and first validated before JLC was created. Final checks ran after both documents incorporated the coordinator's latest evidence:

```powershell
python -X utf8 'C:/Users/admin/.codex/skills/.system/skill-creator/scripts/quick_validate.py' '.trellis/tasks/10-23-cnc-part-config-auto-quote/research/skill-staging/cnc-xometry-quote'
python -X utf8 'C:/Users/admin/.codex/skills/.system/skill-creator/scripts/quick_validate.py' '.trellis/tasks/10-23-cnc-part-config-auto-quote/research/skill-staging/cnc-jlc-quote'
```

Both returned **Skill is valid!**, exit 0. A direct UTF-8/frontmatter/link check confirmed all four Markdown files decode, original Xometry frontmatter is preserved and both local reference links resolve. A no-index diff inspection confirmed Xometry changes are limited to its two staged documentation files. The initial JLC validator invocation without `-X utf8` failed because Windows default GBK could not decode Chinese UTF-8 text; explicit UTF-8 reruns succeeded without changing the validator or file contents.

Both skills also retain Playwright/CDP guidance and explicitly support official Chrome DevTools MCP (`list_pages`, current `pageId`, `take_snapshot`, fresh `uid`, `click`/`fill`/`upload_file`). File-path tools require an immutable protected copy matching frozen bytes/size/hash. Occupied default profiles do not authorize killing another browser; owned isolated-session reuse is described without machine-specific daemon/session defaults. The final validation rerun includes this addition.

Desk review covered the meaningful decisions: reject historical quantity-5 prices for quantity 1; stop on ambiguous `AL6061`; preserve uncertain mutations without replay; treat JLC's displayed system estimate separately from final quotes; stop before unresolved inquiry/cart/order actions. These are documentation reviews, not live provider tests or independent-agent acceptance.

## Handoff and remaining work

The implementer did not modify `.agents`, production code, task metadata, browser state or the database, and made no commit. The coordinator owns independent review and installation into project-local `.agents/skills/`; installation may require escalation because that directory is read-only in the sandbox. No new external action or file classification is implied by the user's command authorization.

Both skill packages are complete for review. Live provider acceptance remains incomplete: normal managed Xometry controls/save/result evidence, JLC account/editor/save/inquiry boundaries, exact remote file identities and current result/currency/price-basis evidence are still required. Production adapter activation is unchanged. The parent auto-quote task remains in progress.
