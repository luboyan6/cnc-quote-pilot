# 03 嘉立创 CNC 中国站 配置与适配器：设计

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

本子项继承 [父设计](../10-21-cnc-pricing-mvp/design.md)、[稳定契约](../10-21-cnc-pricing-mvp/research/mvp-contract.md)及[平台 JSON 契约](../10-21-cnc-pricing-mvp/research/platform-configs/README.md)；它们是本子任务的实际设计输入，不复制状态/金额/安全规则形成第二套定义。

继承[Deep Agents 设计](../10-21-cnc-pricing-mvp/agent-design.md)；当前核验基线 `0.7.29`，与 02 共用 Agent 工厂/工具权限/checkpoint 规则，只增加嘉立创 CNC 平台 JSON/adapter/Skills。

## 范围与依赖

责任：jlc_cnc_cn.json、第二 adapter、嘉立创 CNC 平台只读 Skills、映射/定位/提取与契约测试；必要核心兼容调整须带首家 Agent 回归。

进入条件：02 首家产品闭环通过，01 嘉立创 CNC 账号/实际样件与参数可行性有 E2 依据。

追溯：MVP-R03/04/07/08/10/11/13/14/15；S-01～07；DV-06/07；父 AC-12/13。

## 本阶段实现行为

1. 读取并完善独立嘉立创 CNC JSON，核对中国站导航域/账号、材料牌号/状态/标准、处理/颜色/粗糙度与价格交期语义。
2. 复用 Deep Agents 工厂/受控工具、loader/runner/DTO/checkpoint/证据策略，真实 UI 差异放 adapter 与只读 jlc-cnc-cn-quote Skills；不复制 Xometry US 或 RD IDs/选择器/数量上限，也不让模型拼接选择器或修改 JSON。
3. 当前请求按嘉立创 CNC 选项目录独立解析与参数回读，配置未知或无等价规格时明确失败/不可严格比较。
4. 同图同数量两家真价与改参验证，保留不同币种/税运/交期档，不做混币排名。
5. 验证两家流程/SDK/模型/技能版本与 incident/thread 隔离、允许恢复策略及其守卫/复验、共享预算；改共用工具/状态时回归首家正常与异常分支，不新增平台专属自主规划循环。

## 验证与风险

第二 adapter/参数隔离契约测试；TC-05～08/12/20/24、TC-CFG-03/04/06、TC-DA-02/04/08；两家实际 S-01～07 和首家 Agent 定向回归。

风险/降级：嘉立创 CNC 账号地区/认证挑战、材料标准不一致、默认推荐非 CNC、人工审核；不伪造账号可用、真价或目录，必要候补按变更记录。

现有规划文件和静态检查不代表产品实现、真实报价或性能已经通过。保护账号/STEP/证据、有限重试与禁止交易保持父契约。

## BR-2026-10-21 共用归属与选型

[源码依据](../../../docs/browser-reference-analysis.md)和[统一接口](../../../docs/browser-implementation-design.md)为本轮设计输入；[BR](../10-21-cnc-browser-reuse/prd.md) 一处交付 Playwright 官方 SDK 薄封装和独立 MIT 出站代理。只增嘉立创 CNC adapter/已验证配置与提取器；消费同一执行层，不复制启动、会话、上传、代理或 Ref 引擎。

禁止另建 CDP/DOM 上传协议、Ref 引擎或 BrowserSkill gateway。接入条件：秘密加密/私有证据及 Trace、owner/platform/account 绑定、允许域、挑战转人工和禁止交易。保留 02 真闭环及 01 嘉立创 CNC E2 依赖；回归平台域/会话/参数隔离，不复用 Xometry US 或 RD 定位器。
