# JLC CNC China observed DOM and evidence

Observations below are scoped to their dates and sessions; they are not stable runtime bindings. Reinspect current controls before acting. This skill uses JLC evidence independently and does not import another site's controls, classifications or material mappings.

## Sources and evidence scope

Repository sources:

- `.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/jlc-live-validation-2026-10-22.md`: historical existing-item observation and unresolved quantity click.
- `.trellis/tasks/10-21-cnc-mvp-01-platform-gates/research/jlc-platform-config-check-2026-10-22.md`: independent research draft, exact unknown fields and automation-disabled status.
- `.trellis/tasks/10-23-cnc-part-config-auto-quote/research/provider-live-evidence-2026-10-23.md`: public upload-entry DOM, managed access attempts and account inventory. Its early DNS diagnosis was superseded by the later user-approved filtered-address contract; it is not permission to change network policy.
- `.trellis/tasks/10-23-cnc-part-config-auto-quote/research/site-skill-live-observations-2026-10-23.md` and `research/site-skill-browser-evidence.jsonl` under that same task: fresh public observation at `2026-10-23T15:55:59.836Z` (23:55:59 Asia/Shanghai), canonical landing, file-input projection and tutorial controls. These are the coordinator's live observations; the skill implementer read the saved evidence.

| Evidence level | Established | Not established |
| --- | --- | --- |
| Historical existing part, 2026-10-22 | Visible geometry, parameters and expressly qualified system estimate | Who uploaded it, exact remote bytes, saved parameter changes, current-run quote |
| Current public entry, 2026-10-23 | Upload button/native input and declared formats/limits | Authenticated upload, parameter editor, saved readback, final inquiry side effects |
| Managed project inventory, 2026-10-23 | No enabled JLC account at that observation | Whether an account is available in a later run |
| Skill validation | Reusable instructions and valid skill structure | Provider adapter activation, real upload/quote success or two-platform acceptance |

Production provider automation remains unverified/disabled. Do not load a historical draft JSON as an activated adapter.

## Public upload entry

Configured/requested clean entry: `https://www.jlc-cnc.com/cncOrder/#/placeOrder`. The fresh anonymous observation at `2026-10-23T15:55:59.836Z` landed at canonical `https://www.jlc-cnc.com/cncOrder/` with an empty hash; title was **嘉立创CNC-在线报价-深圳嘉立创科技集团股份有限公司**. Use the actual platform configuration plus trusted provider resolver; do not infer authorization for arbitrary JLC subdomains or tracking URLs.

| Purpose | Observed DOM / text | Use boundary |
| --- | --- | --- |
| Primary upload trigger | `button#uploadFileBut`, **拖拽或上传图纸文件** | Reconfirm current uniqueness/visibility before action |
| Part-list import | `button#exportModelBut`, **导入零件清单** | Not the CAD-upload control |
| Native file input | Exactly one `input[type=file]`, no ID, `multiple=true` | Official helper only; send the one authorized payload |
| Native `accept` | `.stp,.STP,.step,.STEP,.zip,.ZIP,.rar,.RAR,.pdf,.PDF,.dwg,.DWG,.dxf,.DXF` | Supplementary/archive acceptance does not make those valid primary 3D CAD |
| Main CAD statement | STEP/STP; supplementary DWG/DXF/PDF | Verify STEP bytes against frozen hash; never infer validity from suffix alone |
| Limits | Single batch ≤20, individual `<100M` | UI declarations only; exact byte convention and boundaries not tested |
| Public access | Login/Skip controls visible | Their presence establishes neither a verified account nor permission to upload anonymously |
| First-visit walkthrough | **上传图纸文件(1/2)** with **跳过/下一步** | Tutorial only; not parameter Save, quote or inquiry actions |
| Existing data | History **暂无数据**; no quantity inputs/material editor | Do not assume historical item-edit controls exist on this anonymous page |

No file was selected, uploaded or configured, and no account was logged in during the fresh public research. The UI says the same part's 3D/2D filenames should match; this observation does not authorize adding supplementary files to a one-file request. The broad `accept` list does not override the application's trusted STEP verifier. Where the existing application accepts historical `.setp`, it still validates framing/hash/root/size and sends verified bytes as private `part.step`; that compatibility does not prove JLC accepts `.setp` filenames directly.

## Existing part's editor and quantity controls

Historical candidates from 2026-10-22:

| Purpose | Observed candidate | Verification status |
| --- | --- | --- |
| Open parameters | `#material-box .change-info`, **修改参数** | Observed; editor not opened/saved |
| Quantity | Unique visible `input[role=spinbutton]`, DOM min `1`, max `9999999` | DOM attributes only; not tested business limits or accepted range |
| Inquiry | **提交询价** | Not clicked; quote-only side effects unverified |
| Cart | `addCarCNC`, **加入购物车** | Cart action, outside quote-only scope |

Do not invent material-modal radio IDs, option selectors, exact option catalogs, dependency rules, save buttons or required fields. Discover current editor structure read-only first. A local selection may commit remotely before a separate Save exists; establish its semantics and claim its mutation before changing a value.

One quantity-plus action intended to move 1→2 returned `Errno 22 Invalid argument`. Later read requests also failed and a read-only CDP batch had no acknowledgement after 15 seconds. The click's delivery/outcome is **uncertain**. It was not retried. The last confirmed quantity before that attempt was 1; later state was not established. Begin any continuation with read-only remote-state reconciliation; do not infer the item still has quantity 1, replay the plus click or claim quantities 2/5 were verified.

## Historical visible part and estimate, not a current quote

The last confirmed observation was `2026-10-22T05:59:55.850Z` on an existing item labeled `292.1301C`. It had not been uploaded by this research run. Filename similarity and near-matching dimensions do not establish local sample/file identity.

| Field | Historical display |
| --- | --- |
| Geometry | 28 × 25 × 9.5 mm; volume 1967.6 mm³ |
| Material | 铝合金-6061 |
| Finish | 喷砂+普通阳极氧化 / 本色 / 哑光 |
| Tolerance / appearance / threads | GB/T 1804-2000 m级 / 常规外观 / 无螺纹 |
| Temper / roughness | Not independently verified |
| Last confirmed quantity before uncertain click | 1 |
| Unit / line system estimate | ¥212.51 / ¥212.51 |
| Tax / total including tax | ¥27.63 / ¥240.14 |
| Approximate coupon display | 约 ¥190.14; coupon not claimed or applied |
| Rush / standard / economy | 3工作日 ¥366.36 / 6工作日 ¥212.51 / 11工作日 ¥191.99 |
| Shipping/payment text | 今日19点前支付,预计10-29 23:00前发货 |
| Price qualification | 系统预估价; 系统自动报价仅做参考, 最终以人工审核报价为准 |

All values are historical evidence, not defaults or live results. The state is **REFERENCE_ESTIMATE**. `¥` did not independently establish ISO currency. Shipping cost, final landed cost, year/timezone and payment-dependent start are unknown. Do not scale these historical amounts to another quantity or rank currencies from them.

`铝合金-6061` supplies no verified T6 temper. JLC blasting/anodizing in natural matte finish differs from another site's `Standard`; the tolerance standard is also not established as equivalent. Preserve exact site labels and requested/effective fields instead of using cross-platform approximations.

## Inquiry versus order boundary

The official [嘉立创中国站 CNC 询价下单指南](https://www.jlc.com/portal/server_guide_37967.html), updated 2024-12-12, was read on 2026-10-22 and re-read on 2026-10-23. It describes online system pricing after upload, parameter editing, then an order/details flow with logistics, invoice and contact information before manual audit pricing. Its older **提交订单** wording is not proof that today's **提交询价** has identical semantics, or that today's button is an independent quote-only trigger.

Before any current **提交询价** click, verify its actual side effects within the authorized scope. A different label, no payment yet or a subsequent cancellation option does not establish no-order behavior. Stop at order/cart/detail submission or unresolved semantics. This evidence does not prove that every possible JLC inquiry channel requires an order and does not justify changing the user's selected second provider.

## Remaining acceptance work

JLC still needs an authorized verified account, exact-file upload/remote identity, positive geometry, observed editor/material/finish/dependency semantics, complete save/readback, current recalculation evidence, explicit currency and price basis/lead-time context. Final pricing additionally needs a verified quote-only trigger and actual final result distinct from system estimates. Completing these instructions or reading the public entry does not satisfy those gates.
