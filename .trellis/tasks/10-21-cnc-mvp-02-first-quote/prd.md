# CNC MVP 02：首平台真实报价闭环

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

## Goal

以固定 Workflow 完成首平台认证上传、参数核验、真实报价与证据入库，以 Deep Agents 处理未知页面和受控异常恢复，支持改参重算

## Source and Scope

父任务：[CNC MVP](../10-21-cnc-pricing-mvp/prd.md)。追溯 MVP-R02/03/07/08/10/11/13/14、FR-01/02/05、DV-04/05。第一交付点为一条真实报价纵向链路。

## Requirements

### D-18：账号列表自动登录

- 点击账号行登录，读取所属平台当前登录/询价地址，核验已有会话及目标身份；有效则免重复登录并进入询价页，失效则最多重登一次，验证成功后进入。
- 禁用、越权、缺少平台/地址、不支持、登录失败均有明确反馈；验证码/MFA 转人工，身份不符不成功。查询、导出、日志和登录响应不得暴露密码、凭据/会话密文或 Cookie/Token，编辑密码留空保留原值。
- 用户已选择受控浏览器，见父 [D-18](../10-21-cnc-pricing-mvp/decisions.md)：用户可见的平台页与登录使用同一隔离会话，支持人工处理挑战后复验；关闭/超时释放，再次点击恢复加密状态并复验。登录切片拟先行交付，原完整报价 gates 保持，不自动上传/提交报价。
- F-LOGIN-01：首次登录并进入询价页，再次点击实际核验身份且不重复提交凭据；F-LOGIN-02：失效、挑战、身份不符、禁用、越权、缺地址分支正确反馈；F-LOGIN-03：用户可见的平台页使用已验证的目标账号；F-LOGIN-04：响应/导出/日志无秘密。登录切片及自动化证据见 [D-18 验证记录](research/login-validation-2026-10-22.md)，真实平台认证/部署仍未验收，不替代原 F-01～08/live gates。

- 通过既有应用发起首平台询价；当前目标为 Xometry US；Q-01/02 的 RapidDirect 账号事实保留历史，Q-03 已提供模型目录并筛出 D14 转接件首选及 M12-TO-CS 候选，见[样件记录](../10-21-cnc-pricing-mvp/research/step-samples-2026-10-21.md)。使用 CNC Machining；剩余 G-02/G-05、几何/DFM 与报价能力由工具核验，不把页面可达或本地实体计数视为真实报价完成。
- 实现最小账号/文件/任务/结果/证据持久化及必要 API，复用现有 RBAC、响应和加密能力；不先铺完 30 个接口。
- 复用 BR 共用执行层，接入平台认证/会话复验、上传解析、精确加工参数和数量回读、报价/交期解析和证据保存。
- 改数量或材料后重新计算，保留新快照及新结果，证明不是读取缓存旧价。
- 正常链路按固定 Workflow 调用适配器；未知页面/原因/页面变化进入 Deep Agents 观察与策略选择，由代码守卫执行、复验后回到指定步骤。模型不改参数/价格/业务顺序，异常 Agent 不可用明确报告并转人工；正常步骤无需模型调用。
- 按用户新增要求实现受信 platform_code → 独立 JSON 的严格 loader/参数接口、配置版本/哈希固定与 requested/effective 快照；复用[配置契约](../10-21-cnc-pricing-mvp/research/platform-configs/README.md)。只从真实报价提取金额/交期，字段依赖重读，不能把材料目录 price、粗糙度或截图默认值冒充有效报价参数。
- 首条链路同时具有凭据保护、对象权限、交易禁止、总预算、提交 intent 与安全人工接管；不能把安全拖到最后验收。
- 使用核验的最新稳定 Deep Agents（当前 `0.7.29`）实现正式恢复能力；固定模型/技能/工具版本，观察工具只读，恢复策略白名单、守卫/复验、incident/checkpoint/累计预算与人工恢复随首价交付。默认不开放子代理或跨业务自主规划。

## Acceptance Criteria

- [ ] F-01：从本站受控入口完成授权 STEP → 参数 → 真实明确报价，证据和结构化结果入库，对应父 AC-01。
- [ ] F-02：改参重报价成功，关键参数/金额/币种/交期与同次页面 100% 一致，对应 AC-02。
- [ ] F-03：会话复用与失效分支可演示；有挑战就停在人工待办，不继续上传/报价。
- [ ] F-04：成功记录证据可读取且绑定同次参数；缺证据/币种或参数不符不能 SUCCEEDED。
- [ ] F-05：自动重试≤2、attempt≤3、自动重登≤1；提交不明先核对，不重复盲发。
- [ ] F-06：凭据/会话不泄漏，无正式订单/支付；第二家可复用核心 DTO 与 runner。测试 TC-01～07/11/13/18/19/21。
- [ ] F-07：独立 JSON 及版本加载有效，未知平台/路径/参数在动作前拒绝，配置变化不污染在途重试；实际 UI 变体唯一定位、保存后完整回读，TC-CFG-01～08 对应检查有结果。父 AC-11。
- [ ] F-08：首价/改参按 S01～S11 固定执行，未知异常有真实 create_deep_agent 观察/分析/策略选择记录，经代码守卫/复验恢复或明确接管；正常链路允许零模型调用。TC-DA-01～08、TC-WF-01～05 和适用 E01～E13 有结论，重启/预算/幂等有效；父 AC-12/13、MVP-R14/15。

## Dependencies

必须先有 [01 的首平台验证交付](../10-21-cnc-mvp-01-platform-gates/prd.md)及父任务关键问答结果。首平台链路未通过不得开启第二适配器全面开发。

## Ownership and Boundaries

拟负责 backend/app/modules/cnc/ 的最小 account/file/quote/agent/execution、首平台 adapter、Skills/checkpoint/预算/事件、必要 API/迁移、既有路由/生命周期接入和 backend/tests/cnc/，以及必要 backend/pyproject.toml/uv.lock 依赖接入。实际文件清单在 design.md/implement.md 固化。

复用现有后台和数据库，包含固定 Workflow 与首价异常所需 Deep Agents 恢复工厂/只读观察/策略守卫/Skills/checkpoint；不先开发完整 Web 页面、批量/定时或动态多 Agent。ModelMixin 整型主键与 SRS UUID 的差异按父设计兼容。

## Planning Artifacts

复杂任务；[design.md](design.md)、[implement.md](implement.md)、JSON 与真实上下文已齐备，既有实施授权有效，完成当前规划复核及 01 Xometry US 首平台验证后启动研发。目标约 Day 2；本 PRD 不代表已实现。

## 浏览器复用修订 BR-2026-10-21（当前增补）

用户已批准本轮创建修订任务并推进实现；原停止指令/记录保留历史范围。[BR](../10-21-cnc-browser-reuse/prd.md) 统一交付共用组件，契约见 [设计](../../../docs/browser-implementation-design.md)。

- 消费 BR 的 Playwright 层与账号隔离；负责 Xometry US 可信 locator/JSON、回执/几何、完整回读和真实 Decimal 报价，接入前完成持久 intent、账号 ACL/加密会话与异常 Agent。
- 先 BR 组件通过，再按原 01 gates 启用真实 adapter；回执不明只读协调，挑战暂停，禁止盲重发。
- 验收 F-BR-01：按 BR 契约检查域名/SSRF、秘密脱敏、官方上传及状态核验、有限重试、异常/取消释放和人工停止，提供用例结果。原验收 ID/live 欠项保持。
- 验收 F-BR-02：同次文件哈希/完整有效参数/币种/金额/交期与证据一致；零几何/无真价/挑战/未知回执不得成功，组件测试与 E2/E3 分开。
