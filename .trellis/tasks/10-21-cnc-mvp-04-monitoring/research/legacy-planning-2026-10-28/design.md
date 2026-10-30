# 04 批量、幂等与定时历史：设计

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

本子项继承 [父设计](../10-21-cnc-pricing-mvp/design.md)、[稳定契约](../10-21-cnc-pricing-mvp/research/mvp-contract.md)及[平台 JSON 契约](../10-21-cnc-pricing-mvp/research/platform-configs/README.md)；它们是本子任务的实际设计输入，不复制状态/金额/安全规则形成第二套定义。

按[Deep Agents 设计](../10-21-cnc-pricing-mvp/agent-design.md)将同版 Agent 接入批量/监测，当前核验基线 `0.7.29`；业务任务/预算/intent 与 checkpoint 分工一致。

## 范围与依赖

责任：CNC task/schedule/history、领取/租约与既有 scheduler builtin，相关模型/测试；不重建共享调度器。

进入条件：02/03 两家适配器与配置快照/结果契约稳定且可真实报价。

追溯：MVP-R05/06/07/10/11/13/14/15；M-01～08；DV-08/09/11；父 AC-12/13。

## 本阶段实现行为

1. 展开 12 明细并固定平台配置/SDK/模型/Skills/流程与策略版本，每 item 独立步骤/intent；未知异常创建服务端 incident/thread，恢复同异常沿用原 thread，全部异常共享 item 预算。无异常不要求创建 Agent checkpoint。
2. 实现 owner 幂等键、同批去重、租约/账号锁/限流、有限重试和取消；提交不明只读协调。
3. 复用现有 leader/builtin 创建持久监测轮次，重复 tick/重启不重建同轮，错过/重叠有记录。
4. 追加保存两轮有效观测，同价不去掉；按全部有效参数和商业口径比较，未知或不同口径不强行算差额。
5. 把 02 的固定步骤、异常策略/复验、checkpoint/人工恢复/取消接入消费者；重启协调 intent/远端引用和恢复位置。所有 incident/模型/Schema 调用共享原 item 预算，重复决策/新 tool_call_id 不重发；调度器仅入队，Agent 不推进主步骤。

## 验证与风险

TC-09/10/13～15/21～25、TC-CFG-06、TC-DA-05～07/09；12 项基准、两轮真实自动监测，Agent thread/版本隔离、幂等/取消/真实 saver 重启/崩溃协调与数据库完整性测试。

风险/降级：调度重复、配置变更污染历史、静默默认附加服务、长等待占锁；固定配置、有限预算与可复算等待记录。

现有规划文件和静态检查不代表产品实现、真实报价或性能已经通过。保护账号/STEP/证据、有限重试与禁止交易保持父契约。

## BR-2026-10-21 共用归属与选型

[源码依据](../../../docs/browser-reference-analysis.md)和[统一接口](../../../docs/browser-implementation-design.md)为本轮设计输入；[BR](../10-21-cnc-browser-reuse/prd.md) 一处交付 Playwright 官方 SDK 薄封装和独立 MIT 出站代理。SchedulerUtil 只入队；消费同一执行层，同账号持久租约、operation intent 与观测由本任务/02 持有。

禁止另建 CDP/DOM 上传协议、Ref 引擎或 BrowserSkill gateway。接入条件：秘密加密/私有证据及 Trace、owner/platform/account 绑定、允许域、挑战转人工和禁止交易。保留 02/03 真闭环依赖；重复 tick/取消/租约丢失/丢回执不重复提交；两轮真实监测独立验收。

## D-17 前两平台交付边界

本阶段目标固定为 Xometry US 与嘉立创 CNC 中国站；12 基准、每平台 10 项、两轮监测、Web/CSV/证据及全部原验收保持。RapidDirect 为第三家延期 backlog，不出现在当前批次、监测模板或成功率分母中；前两家完整功能与验收完成后才考虑实施。
