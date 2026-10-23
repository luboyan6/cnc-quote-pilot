# 交期契约对齐切片（2026-10-23）

## 授权与缺口

用户再次要求继续 Trellis 未完成任务；沿用 D-15/D-17 顺序授权及本任务 implement.md 已列明的交期对齐项。原共享 LeadTime/validate_quote 只支持正整数天数，无法保存平台明确的发货/到货日期，也没有区分该时长是否专指生产；不得据此从 Arrives by 倒算生产天数。该独立契约修复不启用报价 adapter，不通过真实平台门槛，不推进 03～05 的整体状态。

## 变更边界

行为位于 `backend/app/modules/cnc/browser/contracts.py` 和 `workflow.py` 的报价值对象、序列化及验真边界。可以抽出同目录 `lead_time.py` 作为单一编解码/校验所有者，并从 contracts 重导出旧名字。对应单元、workflow 及现有合成浏览器 fixture 跟随变更。

当前仓库没有正式 quote DTO/持久化/API/前端报价页；本轮交付可供它们共用的版本化 JSON 契约和往返测试，不创建占位模块，不声称已完成尚未存在的数据流。现有账号登录、DNS/出站、租约、价格/新鲜度/intent/文件验证保持。无需新增依赖或修改数据库。

## 数据契约

- 保留 `LeadTime(text, minimum_days, maximum_days, basis)` 的数值时长构造兼容性；明确 kind：duration（原记录未注明用途的交期时长）、production_duration、ship_date、arrival_date。text 保存原始交期文字，不转写为另一种语义。旧契约本身没有证明其数值专指生产，不能升级时凭空标成 production_duration。
- duration/production_duration 保持原正整数 min/max、min <= max 及已知 business/calendar basis 检查，拒绝 bool/float/无效区间。显式 production_duration 还必须提供非空可信来源；起算点未给则 null，不把接单/付款/观察日作为默认起点。
- 日期类型不带生产天数/day basis/起算点。日期值显式保存 month/day/year；year 可为 null，用于只显示月份/日期的原文，不能填观察年的年份。完整日期按真实日历校验；无年份的 2 月 29 日可保留，不合法的 2 月 30 日拒绝。
- 只有原文而没有已识别日期的 unknown/TBD 观察不构成可通过验真的日期交期；不增加自然语言猜测或从页面字符串隐式推断日期的通用解析器。调用方须提供可信、明确的日期语义与月日字段。
- 新日期类型和显式 production_duration 必须提供非空 source，表示同次可信页面/文档证据来源；兼容旧通用时长快照时 source 可为 null，不能填造来源。source 只保存受信描述/证据引用，不保存带 token 的 URL。
- 日期字段与生产时长字段互斥；未知 kind、未知 schema_version、额外字段、伪造日期、无来源日期、类型错误必须固定失败。字段缺失不能被自由补全成有效报价。

## 序列化与兼容

- 单一 `as_dict` / `from_dict` 所有者提供 version=2 的交期 JSON，显式保留 kind/text/source、duration 字段、可空日期年份和起算点。canonical 字段名由实现统一，不在消费者重复转换。
- 解码兼容原来四字段 `{text, minimum_days, maximum_days, basis}` 快照，按原语义严格校验为未注明用途的 duration；缺失字段、无依据 basis 或非法区间不得因兼容路径通过。旧构造默认同样为 duration，不能把未记录的生产性质填入新类型。
- `ValidatedQuote.as_dict()` 使用同一 serializer；`validate_quote` 使用同一语义校验。错误保持 BrowserStop(QUOTE_INVALID)，不在日志打印原始快照。
- 现有价格/币种/参数/几何/身份/新鲜度验证全部保持。只修复交期表达能力，不能让 REFERENCE_ESTIMATE、旧价或身份不符成为 QUOTED。

## 验证与交付

- 单元：旧构造及旧快照往返且不自动升级为生产、明确生产来源检查、通用时长/生产/发货/到货完整和缺年份日期往返、非法天数/类型/日期/字段混合/来源/版本/额外字段拒绝、无解释交期不得成功。
- workflow：明确 arrival/ship 观察保留其类型、原文、来源和 year=null；无派生生产天数。原 duration/金额/币种/身份/几何/新鲜度负向用例保持有效。
- 合成 Chromium：更新现有 fixture 的 schema 断言，保留实际 DOM/参数/报价回读及生命周期验证；只作为组件回归，不计真实平台验收。
- 数据示例仅用已记录的 Xometry A/B 原文和嘉立创工作日说明，区分平台/报价/数量/档位；不借用 B PDF 数量 5 Economy 的天数填充 A 或其他档位。
- 先 implement agent，再 check agent；通过后主会话同步 spec、任务进度与 journal。真实平台登录/报价、正式 DB/API/前端贯通与原 gates 保持未完成。
