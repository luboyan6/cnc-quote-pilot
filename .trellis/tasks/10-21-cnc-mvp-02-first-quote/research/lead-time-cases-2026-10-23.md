# Research: 交期类型契约的四个真实记录样例

- Query: 从已有 Xometry A/B 与嘉立创记录中提取可用于类型契约测试的准确交期原文、日期字段、天数依据和未知项。
- Scope: internal；只读既有脱敏证据，不访问网页/浏览器、账号、地址、原始平台标识或数据库，不检查/修改产品代码。
- Date: 2026-10-23

## Findings

以下 `raw` 是既有证据文件中保存的字面值，不声称重新读取原始 DOM 或 PDF。A/B 卡片只保存日期片段，不能把未保存的 `Arrives by` 前缀拼成逐字 UI 引文。样件 A/B 和本地证据编号仅用于关联，不复制原始报价/部件/账号 ID。字段名是研究投影，不规定产品 API。

### 文件与关联

| 文件 | 用途 |
| --- | --- |
| [A Markdown](../../10-21-cnc-mvp-01-platform-gates/research/xometry-live-quote-2026-10-22.md):76–86,105–121 | A 数量 2 的卡片日期及同状态二级投影 |
| [A JSON](../../10-21-cnc-mvp-01-platform-gates/research/xometry-live-quote-result-2026-10-22.json):134–173 | `observations.XU-E08`、`observations.XU-E09` 的原始字段 |
| [B Markdown](../../10-21-cnc-mvp-01-platform-gates/research/xometry-b-live-quote-2026-10-22.md):48–76 | B 数量 5 的 Least Expensive/economy 卡片日期 |
| [B JSON](../../10-21-cnc-mvp-01-platform-gates/research/xometry-b-live-quote-result-2026-10-22.json):149–157 | `quotes[quantity=5].tiers.economy` |
| [B PDF Markdown](../../10-21-cnc-mvp-01-platform-gates/research/xometry-b-pdf-evidence-2026-10-22.md):49–77,87–97 | B 数量 5/Economy 的明确工作日数、发货日和订单截止条件 |
| [B PDF JSON](../../10-21-cnc-mvp-01-platform-gates/research/xometry-b-pdf-evidence-2026-10-22.json):101–127 | `lead_time` 精确原文、独立字段及未验证的生产语义 |
| [嘉立创 Markdown](../../10-21-cnc-mvp-01-platform-gates/research/jlc-live-validation-2026-10-22.md):9–23 | 当前已有条目数量 1、各档位工作日数及参考价性质 |
| [嘉立创 JSON](../../10-21-cnc-mvp-01-platform-gates/research/jlc-live-validation-2026-10-22.json):38–70 | 当前选中 `标准交期`、6/BUSINESS、`ship_by_text` |

### 四例对照

所有时间均为既有记录的 UTC 观察/截图时间，不是生产起算事件。以下四例的 **已验证生产 duration min/max/day_basis 全部为 null**：没有一例原文明确证实其天数是生产周期；可明确的“平台交期天数”另列，不能静默改名为生产天数。

| 样例及限定范围 | 精确保存的 raw / 字段 | 可明确的日期 | 同记录平台交期天数 | 证据与未知项 |
| --- | --- | --- | --- | --- |
| LT-A：Xometry 样件 A，数量 2，economy；卡片与其同状态二级投影 | 卡片 `arrival_label_as_reported="Nov5"`；投影 `arrivalDate="2026-11-05"`、`leadTimeDays=7` | 卡片只含 month=11/day=5/year=null；投影明确 year=2026/month=11/day=5，作为独立来源保存 | raw 数值 7 可留作未解释来源字段；已验证 duration min/max/day_basis=null | XU-E08：`2026-10-22T03:07:12.179Z`；XU-E09：`2026-10-22T03:08Z`，仅分钟精度。投影不是受信公共 API；7 的业务语义、工作日/自然日和起算事件未知 |
| LT-B-UI：Xometry 样件 B，数量 5，卡片 Least Expensive（记录 key=economy） | `arrival_label="Nov 9"` | arrival month=11/day=9/year=null；没有完整 ISO 日期 | min/max/day_basis=null | `2026-10-22T04:35:10.438Z` 的 B 卡片，后续刷新仅确认保留。不能复制 A 的年份或 7；不能把后续 PDF 的8天塞回这条早期卡片记录 |
| LT-B-PDF：仅 Xometry 样件 B，数量 5，Economy，PDF 同次证据 | `raw="8 business days"`；其他字段见下表 | 发货 month=11/day=3/year=null；到货日=null；订单截止 month=10/day=22/year=null，时区原文 EDT | **generic provider duration min=8/max=8/day_basis=business_days**；`explicit_production_label_verified=false`，start_event=null | XU-BPDF-E01，截图 `2026-10-22T07:05:33.819Z`。不能标为已验证生产8天；不扩展至 A、B其他数量/档位。发货日、工作日数、截止条件独立保存 |
| LT-JLC：嘉立创中国站已有条目，数量 1，当前选中 `标准交期`；本地源件关联未知，不称样件 B | 档位 label=`标准交期`；叙述记录为 `6 个工作日`（并非已保存的单个完整 DOM 字符串）；完整 `ship_by_text` 见下表 | ship month=10/day=29/year=null，clock=23:00；支付截止 raw 是“今日19点前”，不推算绝对日期 | **generic provider duration min=6/max=6/day_basis=BUSINESS**（记录值）；生产/支付后的起算点未知 | `2026-10-22T05:59:55.850Z`；价格性质 **REFERENCE_ESTIMATE，不可作为真实 QUOTED**。工作日日历、时区和发货条件是否适用于其他档位未核验；不借用其他档位3/11天 |

### B PDF 与嘉立创的条件原文

| 范围 | 精确保存在 JSON 的字符串 | 可保存的字段和限制 |
| --- | --- | --- |
| LT-B-PDF 发货 | `Tuesday, Nov. 03` | weekday_raw=Tuesday；month=11/day=3/year=null，ship_date_iso=null。发货日原文没有时区；不能把截止条件的 EDT 自动赋给发货日 |
| LT-B-PDF 网上订单条件 | `when ordering online by 11:59 PM EDT on Thursday, October 22` | cutoff clock=23:59、timezone_raw=EDT、weekday_raw=Thursday、month=10/day=22/year=null；不推断 IANA 时区、生产起算点或订单已发生 |
| LT-B-PDF 邮件路径条件 | `Order requests emailed to support after 8 PM EDT will be processed the following business day` | 独立路径，不能用20:00替换网上23:59截止。本例未发送邮件 |
| LT-JLC 发货/支付条件 | `今日19点前支付,预计10-29 23:00前发货` | year=null、timezone=null、payment_start=null。保留“预计”及支付前提；不把观察日当作支付日期或生产开始时间 |

B PDF 另有 `quoted_on_raw="10/22/2026 3:04 AM EDT"`（字段见 PDF JSON:122）。它明确的是报价生成日期，**不补全发货日或截止日期的年份**。同理，A 的2026只属于其数量2/economy的 `arrivalDate` 投影，不能填入 A其他数量、B或嘉立创。

### 供实现/检查引用的断言

1. LT-A 保留卡片原文和二级来源的完整日期；raw `leadTimeDays=7` 的存在不允许生成 `production_minimum_days=7`、`production_maximum_days=7` 或已知 day_basis。
2. LT-B-UI 可保留 arrival month/day 标签，但 year、完整 ISO 日期、duration 和 day_basis 均为空。类型是否允许不完整日期/标签，由实现契约明确；不得用当前年份修补以通过校验。
3. LT-B-PDF 只有 generic duration 的8/8/business_days有直接依据；生产语义和起算事件仍未知。ship/cutoff/arrival 三者不得互换，也不能由到货日倒算生产天数或减去假设运输天数。
4. LT-JLC 可解析6个工作日及条件发货标签，但价格性质守卫必须仍拒绝其充当真实 QUOTED。不能因为交期解析通过，就让整笔报价通过真实金额验收。
5. 将 LT-B-PDF 的8复制到 LT-A、B其他数量/档位、或 LT-B-UI 的原始历史记录，应作为跨范围填值的负例；需要聚合时保留每条来源、时点和适用范围。

### 相关规范与代码模式

- [02 design.md](../design.md):50–56、[implement.md](../implement.md):55–61：生产 duration、ship date、arrival date/label 分开建模，保留 raw/type/source，未知年份/起算点/日历规则不补造。
- [cnc-validation.md](../../../spec/backend/cnc-validation.md):83–87：arrival 与生产时长分开；[browser-executor.md](../../../spec/backend/browser-executor.md):34,48：真实成功仍需同次参数、金额/币种/范围、交期与新鲜度。
- 仅转述已有代码审查：[交接矩阵](../../10-21-cnc-mvp-01-platform-gates/research/first-provider-handoff-gap-2026-10-22.md):126–142 记载 `LeadTime`/`validate_quote`/`ValidatedQuote.as_dict()` 的历史 duration-only 形状。本轮不检查产品实现，新增类型与行号由实施/检查代理确认。
- 外部参考：没有新增外部检索或版本判断；上述来源均是2026-10-22现存证据，未引用通用平台文档填补报价专属字段。

## Caveats / Not Found

- PDF 原始文件未成功下载/归档；本研究只使用已有协调者转录及加密截图登记，没有解密、打开或重新核验截图。
- 四例都未证实生产起算事件、节假日日历或实际运输天数。B PDF 的明确工作日数不等于明确“生产周期”；嘉立创“工作日”也不自动证明生产起算语义。
- 嘉立创数量1是该记录最后确定读回；后续一次1→2工具调用的效果曾不明，不能把该例当作当前在线数量或后续数量2/5成功证据。
- 不复制真实账号、地址、平台原始报价/部件标识或文件名；不改变任务状态、验收、配置、代码或其他研究记录。仅创建本文件。
