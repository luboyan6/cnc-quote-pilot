# CNC MVP 03：第二家平台与真实对比

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

## Goal

账号列表自动登录继承父 [D-18](../10-21-cnc-pricing-mvp/decisions.md) 及 02 的 F-LOGIN-01～04：嘉立创使用同一登录/会话契约，已有有效会话免重登并进入询价页，挑战转人工。用户已选择受控浏览器，沿用 02 的 [集中设计](../10-21-cnc-mvp-02-first-quote/account-login-design.md)；先核验本站真实登录定位器、跳转域和目标身份标记。登录切片拟先行交付，完整报价的 02 闭环及嘉立创 E2 前置不变，RapidDirect 保持延期。

复用首平台的核心契约接通第二家服务商，同图同参数获取真实报价与证据

D-18 协作进度（2026-10-23）：嘉立创原生 CAS iframe 登录与身份检查已接入 02 共用登录服务，真实 Chromium 合成回调/关闭恢复通过，见 [平台依据](../10-21-cnc-mvp-02-first-quote/research/login-provider-evidence-2026-10-22.md)及[验证记录](../10-21-cnc-mvp-02-first-quote/research/login-validation-2026-10-22.md)。本机混合保留 DNS 阻断生产连接，真实账号登录未验收；03 的完整报价任务仍 planning，原 E2/02 闭环前置不变。

## Source and Scope

父任务：[CNC MVP](../10-21-cnc-pricing-mvp/prd.md)。追溯 MVP-R03/04/07/08/10/11/13/14、FR-02/06、DV-06/07。D-17 已明确第二家为嘉立创 CNC 中国站（jlc_cnc_cn / jlc），首家为 Xometry US（xometry_us / xometry）。Q-04 的美国第二家选择保留历史。嘉立创登录复用、同件与完整参数/真实报价能力仍须 E2 验证；已见系统预估价不能通过。

## Requirements

- 在首平台真闭环之后，接入另一独立服务商，不以同服务商的中美入口凑两家。
- 复用 Deep Agents 工厂/受控工具、核心 runner、账号隔离、参数 DTO、结果解析规范与证据事务，站方差异放入适配器、版本化映射和只读平台 Skills，不新增第二套 Agent 循环。
- 相同 STEP、数量和完整可比规格能取得两家真实明确报价；改数量/材料均按自身可用选项回读验证。
- 币种、税运、公差或交期语义不同允许并列观察，但不得自动等同或虚假排名。
- 新增平台维持同样安全、超时、认证挑战、未知提交协调与证据要求。
- 使用独立 jlc_cnc_cn.json 并经同一 loader 按 platform_code 加载；材料/处理/颜色/粗糙度/数量及价格交期提取规则由嘉立创 CNC 真实页验证，不复用 Xometry US 或 RapidDirect ID/定位器/数量上限，未知目录不能自动启用。

## Acceptance Criteria

- [ ] S-01：第二家 E2 前提满足，自动上传→配置→真实报价达到 E3，保留人工核对证据。
- [ ] S-02：两家 provider_group 不同，同图同数量均有有效 QUOTED，父 AC-03 达成。
- [ ] S-03：数量 1/2/5 和两份样件的报价能力支撑后续基准，参数准确且不静默替代。
- [ ] S-04：第二材料/表面处理有真实映射依据；不支持项明确拒绝。
- [ ] S-05：关键状态、金额/交期/新鲜度和证据契约兼容，无核心平台特判堆积。测试 TC-05～08/12/20/24。
- [ ] S-06：嘉立创 CNC 独立 JSON 的映射、依赖和配置快照实测可用，按平台加载且不串值，TC-CFG-03/04/06 通过；父 AC-11。
- [ ] S-07：嘉立创 CNC 平台复用同一固定 Workflow 和 Deep Agents 异常恢复契约，JSON/Skills/已验证变体/incident 无串用；正常路径和允许策略守卫分别检查，TC-DA-02/04/08、TC-WF-01/02/06 及首家回归有结果。追溯 MVP-R10/14/15、父 AC-12/13。

## Dependencies

依赖 [02 首平台闭环](../10-21-cnc-mvp-02-first-quote/prd.md)实际通过，以及 [01](../10-21-cnc-mvp-01-platform-gates/prd.md)完成第二家账号/样件/独立询价验证。

## Ownership and Boundaries

拟负责第二 adapter、映射/定位版本、最少平台配置、嘉立创 CNC 平台只读 Skills 和契约测试。只有真实兼容问题才调整核心契约，并同步首家 Agent 回归。核心状态不随平台任意新增；不重写第一适配器或 UI。

## Planning Artifacts

嘉立创 CNC 平台已选定，账号/页面实测前不编造选择器和材料选项。[design.md](design.md)、[implement.md](implement.md) 与独立 JSON 结构已齐备，既有实施授权有效，完成当前规划复核及依赖实测后启动研发；账号持有人现在可先人工试价。目标约 Day 3；参考价/审核申请不充当闭环。

## 浏览器复用修订 BR-2026-10-21（当前增补）

用户已批准本轮创建修订任务并推进实现；原停止指令/记录保留历史范围。[BR](../10-21-cnc-browser-reuse/prd.md) 统一交付共用组件，契约见 [设计](../../../docs/browser-implementation-design.md)。

- 只增嘉立创 CNC adapter/已验证配置与提取器；消费同一执行层，不复制启动、会话、上传、代理或 Ref 引擎。
- 保留 02 真闭环及 01 嘉立创 CNC E2 依赖；回归平台域/会话/参数隔离，不复用 Xometry US 或 RD 定位器。
- 验收 S-BR-01：按 BR 契约检查域名/SSRF、秘密脱敏、官方上传及状态核验、有限重试、异常/取消释放和人工停止，提供用例结果。原验收 ID/live 欠项保持。
- 验收 S-BR-02：同次文件哈希/完整有效参数/币种/金额/交期与证据一致；零几何/无真价/挑战/未知回执不得成功，组件测试与 E2/E3 分开。
