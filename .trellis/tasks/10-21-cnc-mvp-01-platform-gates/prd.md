# CNC MVP 01：平台、账号与样件验证

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前续接（2026-10-22）：用户要求继续现有 CNC 任务；在确认已有许可后进一步明确现有六项需求范围均允许，按父 D-15 恢复两家候选的受控验证。许可依据为用户确认，不冒称已独立审阅站方协议。BR 符号链接测试已补齐，真实几何/报价仍须验证后才能进入 02。最新整体记录见[执行状态](../10-21-cnc-pricing-mvp/execution-status.md)。

历史阶段状态：本地输入与 SDK/checkpoint 验证已完成检查，用户曾要求就此停止并复核 Agent/RPA/浏览器需求。整项 live 验收未完成，不标记 completed。见[阶段检查](research/verification-2026-10-21.md)及[需求复核交接](../10-21-cnc-pricing-mvp/requirements-review-handoff.md)。

历史执行更新（2026-10-21；以本页 2026-10-22 当前检查点及后续 B 增补为准）：用户已授权并启动本任务，当前 in_progress。A/B 已进行 Apply/保存配置但无即时报价；C 已上传未配置，Xometry 已观察官方入口。G-01 适用许可及真实价格仍未通过；[本轮实测](research/live-validation-2026-10-21.md)记录该时点执行事实，下文前期调研描述保留其历史范围。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

## Goal

核实授权账号、统一 STEP、加工参数、报价性质与安全停止点，形成真实平台 E2 依据

## Source and Scope

父任务：[CNC MVP](../10-21-cnc-pricing-mvp/prd.md)。追溯 MVP-R01/13/14、SRS 第 2 章 G-01～07、DV-01～03。此阶段产生技术验证依据，不代替两个平台的自动化交付。

## Requirements

- 用户已确认 RapidDirect 注册及可进入报价页（Q-01/02）；接下来由工具核验控件、会话与业务流程，不要求用户口述元素。Q-04 用户已选择择幂美国 Xometry US，中国入口在其当前环境不可达；美国账号可用性及 E2 尚待验证，不再要求采用中国入口。
- 用户要求立即试价；按[首轮步骤与记录](../10-21-cnc-pricing-mvp/research/live-quote-validation-2026-10-21.md)继续 A 文件数量 1→2→5 的人工/受控验证，不等待完整产品研发。早期历史检查点（Apply 前）：CDP 曾失败，随后临时恢复并打开单件 Configure 读取目录，当时尚未点击 Apply/取价，详见[实际配置调研](../10-21-cnc-pricing-mvp/research/rapiddirect-configuration-2026-10-21.md)。
- 用户要求每平台独立 JSON；补充各平台真实选项/ID、字段依赖、数量约束、界面变体和报价提取证据到[配置文件](../10-21-cnc-pricing-mvp/research/platform-configs/README.md)，未实测值保持未知，不将目录标记/材料基础 price 当零件报价。
- 用户已在 Q-03 提供 E:/AIWorkspace/3d_models；[只读筛选记录](../10-21-cnc-pricing-mvp/research/step-samples-2026-10-21.md)登记 A 为 D14 转接件、B 候选为 M12-TO-CS 转接件及哈希/mm 单位声明。入口选择 CNC Machining；实体有效性、平台解析/DFM 与最终统一 A/B 冻结由本任务核验，不把候选当作已报价样件，不使用未授权图纸。
- 在真实环境手工/受控验证登录、会话复用、上传、几何解析、数量 1/2/5、材料/表面处理/公差、价格和交期语义。
- 区分明确报价、仅参考/区间、人工审核与无价；明确安全停止点，无购买/支付/正式订单副作用。
- 第二家嘉立创 CNC 中国站做 E2 核验以降低后续风险，但不在首平台自动闭环前全面开发第二适配器。
- 技术上可探索的问题直接核验；用户所有的输入或选择使用父 decisions.md 的单问题流程记录。
- 按父 [Agent 设计](../10-21-cnc-pricing-mvp/agent-design.md)核验最新 Deep Agents、Python、模型 tool calling 与持久 checkpoint 接入条件；当前稳定基线为 `0.7.29`，受控浏览器停止点交给 02 的领域工具。实际未测试项保留待验证，不把框架资料或人工试价记为 Agent 已接通。

## Acceptance Criteria

- [ ] V-01：G-01～G-07 有逐项通过/失败/待验证记录及时间、样件哈希、参数、证据引用。
- [ ] V-02：首家至少一份统一样件取得真实明确报价和可解释交期；两份最终基准样件通过或明确尚未通过。
- [ ] V-03：首家材料/数量/表面处理/公差和报价性质可确认，不以参考价达标。
- [ ] V-04：第二家嘉立创 CNC（jlc）与首家 Xometry US（xometry）属于不同 provider_group；入口、账号与报价可行性有真实 E2 依据后才冻结。
- [ ] V-05：关键未知限时排查，失败按 SRS 候补规则处理；不伪造选择器、报价或性能。
- [ ] V-06：验证说明、样件/账号引用、各平台 JSON 选项目录与证据可交给 02/03，秘密不入库；明确已加载目录与已报价的区别。关联 TC-01/03/07/20/24、TC-CFG-03/04/07/08。
- [ ] V-07：SDK/Python/provider/checkpoint 依据与实际结果或阻塞有记录；补齐 S01～S11、E01～E13 的已验证/未知页面、停止点和可用恢复变体依据，按 Workflow 正常步骤 + Deep Agents 异常协同交接 02。追溯 MVP-R14/15、父 AC-12/13。

## Dependencies and Open Inputs

Q-01/02 的账号/业务页状态已由用户确认，Q-03 已提供目录且完成只读候选筛选，Q-04 已选择择幂美国。立即进行首份真实人工/受控试价；研发实施前完成本任务规划。用户确认、本地检查和浏览器连接探测不替代真实报价证据，不宣称已跑通。

## Ownership and Boundaries

本任务负责自身 research/ 中的可行性/验证记录、Deep Agents 接入条件与受控验证方案；必要最小探针也须在计划确认后实现。正式 Agent 工厂/工具/checkpoint 由 02 交付，不为 feasibility 重构业务后台。不把包含凭据的截图、storage_state 或 STEP 内容提交到任务目录。

## Planning Artifacts

PRD、[design.md](design.md)、[implement.md](implement.md) 与真实上下文已齐备，用户已批准顺序执行并启动本任务。当前实际阻塞为未通过的外部平台条件，非开发授权。阶段目标约 Day 1，不承诺外部账号或许可取得时长；未完成的 live 验收保持未勾选。

## 浏览器复用修订 BR-2026-10-21（当前增补）

用户已批准本轮创建修订任务并推进实现；原停止指令/记录保留历史范围。[BR](../10-21-cnc-browser-reuse/prd.md) 统一交付共用组件，契约见 [设计](../../../docs/browser-implementation-design.md)。

- 核验真实身份/认证机制、上传回执、非零几何、参数与真价提取证据；feasibility 不重写浏览器/session/Ref 框架。
- 保留本地探针成果；平台许可/身份/样件/真价仍须实际通过。
- 验收 V-BR-01：按 BR 契约检查域名/SSRF、秘密脱敏、官方上传及状态核验、有限重试、异常/取消释放和人工停止，提供用例结果。原验收 ID/live 欠项保持。
- 验收 V-BR-02：同次文件哈希/完整有效参数/币种/金额/交期与证据一致；零几何/无真价/挑战/未知回执不得成功，组件测试与 E2/E3 分开。


## 当前受控验证检查点（2026-10-22）

[本轮真实 UI 记录](research/live-validation-2026-10-22.md)：RapidDirect 旧 A/B/C
仍零几何，A/B 无真价，C 未配置；2026-10-22T03:24:36.109Z 只读核对 C
配置页仍显示 0mm × 0mm × 0mm、0mm³，未 Apply/保存或重复上传。
父 D-16 已获用户答复：指定目录内 STEP 均适用页面 No；这是用户确认而非
助手独立分类。续接时 Xometry 已在现有报价，不能归因此前 Continue 的操作者。
[同一 A 的受控报价](research/xometry-live-quote-2026-10-22.md)已观察非零几何、
数量 1/2/5 的三档价格及到达标签；数量 5 的配置/价格于 03:23:37.878 UTC
刷新后保留。美元来自官方协议依据与页面 $，非报价卡 ISO 字段。
公差/材料/处理不宣称与 RD 等价；生产交期语义、税/目的地/落地总价、
双样件双平台和产品自动化仍未验收。无购买、人工 RFQ 或支付。

[本地 CAD 内核结果](research/geometry-probe-2026-10-22.md)：原 A/B/C 各有
1 个本地有效实体、非零尺寸/体积，前后源哈希/大小/修改时间相同；不能据此
判定 RD 根因或通过远端解析、DFM、真实报价。原 V-01～07 和 V-BR live
验收保持原有未通过状态，02 的进入条件不放宽。

补充 2026-10-22：[B 同一平台受控报价](research/xometry-b-live-quote-2026-10-22.md)
已见非零几何、8/8 DFM Passed、1/2/5 报价及数量5刷新保留。A/B 页面均有优惠/
参考金额，不能称常规价基线；双平台、生产交期语义及产品验收仍未通过。
