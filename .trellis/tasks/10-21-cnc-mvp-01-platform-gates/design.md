# 01 平台、样件与参数目录验证：设计

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

执行状态（2026-10-21）：现有设计已按用户顺序执行指令启动；当前结果与剩余 G-01/几何/真报价条件见[实测记录](research/live-validation-2026-10-21.md)。原文中的规划/探针批准条件由本次执行授权满足，不代表 live 进入条件已通过。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

本子项继承 [父设计](../10-21-cnc-pricing-mvp/design.md)、[稳定契约](../10-21-cnc-pricing-mvp/research/mvp-contract.md)及[平台 JSON 契约](../10-21-cnc-pricing-mvp/research/platform-configs/README.md)；它们是本子任务的实际设计输入，不复制状态/金额/安全规则形成第二套定义。

Agent 接入以[Deep Agents 设计](../10-21-cnc-pricing-mvp/agent-design.md)及[版本核验](../10-21-cnc-pricing-mvp/research/deepagents-2026-10-21.md)为准；当前 SDK 基线 `0.7.29`，本阶段为 02 提供兼容性与停止点依据。

## 范围与依赖

责任：自身 research/ 的实测记录、平台/样件 gates 和受控探针（批准后）；不修改其他模块。

进入条件：用户已给账号状态/样件引用并选择 Xometry US；人工验证现在可继续；产品探针遵守最终评审。

追溯：MVP-R01/13/14/15；V-01～07；SRS G-01～07、DV-01～03；父 AC-12/13。

## 本阶段实现行为

1. 核对 A 文件哈希/单位、0 尺寸及真实预览；限时排查后备用 B，不把上传条目当解析通过。
2. 在 Xometry US 实际配置/报价变体验证选项点击、字段依赖、完整回读及明确价格/币种/口径/交期，补齐首平台 E2。RD 旧试验只保留历史。
3. 检查嘉立创 CNC 中国站客户报价路径、同件关联、材料/处理规格及报价性质；系统预估/待审核不算 QUOTED，未知值不填假 ID。
4. 完善当前前两平台各自 JSON 的证据与范围，分别交接首平台 E2 与第二平台 E2；最终冻结两份两家可报价基准；记录通过/失败/待验证，不用人工审核充成功。
5. 复核最新 SDK 与 Python 范围，登记实际 provider/tool calling 和持久 saver 检查结果或待验证项；形成领域工具需要的允许步骤、认证挑战和提交不明停止点。最小探针遵守原规划门槛，正式 Agent 工厂在 02 实现。

## 验证与风险

人工核对首份真实价、哈希/参数/截图；TC-01/03/07/20/24、TC-CFG-03/04/07/08；V-07 区分资料核验与 SDK 实测；JSON Schema + 任务上下文。

风险/降级：反自动化/人工认证、解析 0 尺寸、审核或地区不可达；按 SRS 时间盒换候选，记录阻塞，不绕过验证。

现有规划文件和静态检查不代表产品实现、真实报价或性能已经通过。保护账号/STEP/证据、有限重试与禁止交易保持父契约。

## BR-2026-10-21 共用归属与选型

[源码依据](../../../docs/browser-reference-analysis.md)和[统一接口](../../../docs/browser-implementation-design.md)为本轮设计输入；[BR](../10-21-cnc-browser-reuse/prd.md) 一处交付 Playwright 官方 SDK 薄封装和独立 MIT 出站代理。核验真实身份/认证机制、上传回执、非零几何、参数与真价提取证据；feasibility 不重写浏览器/session/Ref 框架。

禁止另建 CDP/DOM 上传协议、Ref 引擎或 BrowserSkill gateway。接入条件：秘密加密/私有证据及 Trace、owner/platform/account 绑定、允许域、挑战转人工和禁止交易。保留本地探针成果；平台许可/身份/样件/真价仍须实际通过。
