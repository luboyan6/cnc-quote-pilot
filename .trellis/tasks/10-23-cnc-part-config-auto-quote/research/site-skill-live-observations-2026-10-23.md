# Site-specific quote skills: current observations

## Scope and continuation

Recovered session `01a168cb-d9d5-7f33-9165-052f3077d6ad` and resumed the existing approved task; no new task was created. User then requested separate site skills, Xometry US first and JLC CNC China second, because upload/quote controls and material selection differ. User authorized commands required for this task and requested self-verification without repeated confirmation. This does not decide an export classification or settle an uncertain remote upload.

Local services were listening on ports 10006/5180. The existing isolated official Chrome DevTools session still displays the earlier product failure `PROVIDER_AUTOMATION_UNVERIFIED`, no price, idle row actions and no console warnings/errors. No new quote run was started in this continuation. The native Chrome MCP entry remains blocked by a profile already in use; the existing isolated daemon was reused without stopping another browser.

## Xometry current configuration observation

Observed through the existing CDP-bridge tab on 2026-10-23 around 23:50–23:54 Asia/Shanghai. This is the historical quote `Q59-6980-1120` with query `initialTab=Configure&vercel_part_config=test`; normal-route and managed-account applicability are unverified.

| Field | Observed control | Current value |
| --- | --- | --- |
| Process | `#option-select-process`, DIV role=button | CNC |
| Preferred subprocess | `#option-select-cnc-subprocess-select` | No Preference |
| Material | `#material-select-material-select`, DIV role=button | Aluminum 6061-T6x (Best Available) |
| Finish | `#finish-select-finish-multiselect`, DIV role=button | Standard |
| Quantity | visible input aria-label=Quantity, role=spinbutton | 5 |
| Save | `#configure-part-header-save-and-view-quote` | Save Configuration |

Opening the material picker exposed `#search-material-select`, role=combobox, aria-label=Search materials; its listbox/options have generated IDs. Distinct option titles include Aluminum 6061-T6x (Best Available), Aluminum 6061-T651, Plate, and Aluminum 6061-T6/T6511, Bar/Rod. Their descriptive text and price glyphs are not part of the exact material title. No option was selected and no configuration was saved; Escape dismissed the picker. Material and quantity stayed unchanged. Current selectors are observed candidates, not enabled production bindings.

The CAD Update button and supporting-files browse area are separate from a primary new-CAD upload. The historical quantity 5 and displayed dollar amounts cannot satisfy the linked configuration's quantity 1. No new amount/currency/geometry acceptance was established. The original research upload intent remains uncertain and untouched.

## JLC current public entry observation

Official Chrome DevTools observation at `2026-10-23T15:55:59.836Z`. The first public navigation timed out without leaving a tab; a second bounded navigation opened owned page 4. Requested `https://www.jlc-cnc.com/cncOrder/#/placeOrder` landed at `https://www.jlc-cnc.com/cncOrder/` with an empty hash.

- `button#uploadFileBut`: 拖拽或上传图纸文件.
- One native file input, no ID, multiple=true. Accept lists STEP/STP plus archives and supplementary 2D formats; this does not replace actual STEP byte validation.
- Primary 3D STEP/STP is required. DWG/DXF/PDF are supplementary; the UI recommends matching 3D/2D filenames for the same part.
- UI limit: one batch ≤20 files, each file <100M. Numeric byte semantics and boundary behavior were not tested.
- `#exportModelBut` imports a part list and must not be mistaken for CAD upload.
- Login/register visible; history is empty. No material editor or quantity field is present without a part. The initial tutorial has 跳过/下一步 under 上传图纸文件(1/2); these are walkthrough controls, not quote submission.

No login, file selection/upload, material change, inquiry/cart/order or payment action was performed. Current authenticated JLC parameter controls remain unverified. Historical `#material-box .change-info` and estimate semantics stay separately dated in the JLC reference. Raw public-entry evidence: `site-skill-browser-evidence.jsonl`.

## Completion boundary

The deliverable here is two discoverable, independent site skills with accurate operational guidance and evidence levels. Production `resolve_quote_adapter()` still returns None; writing skills does not register a runtime adapter or complete either provider's real quote acceptance. The parent auto-quote task remains in_progress.
