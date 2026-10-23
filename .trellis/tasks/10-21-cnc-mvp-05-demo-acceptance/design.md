# 05 Web、配置参数展示与演示验收：设计

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

本子项继承 [父设计](../10-21-cnc-pricing-mvp/design.md)、[稳定契约](../10-21-cnc-pricing-mvp/research/mvp-contract.md)及[平台 JSON 契约](../10-21-cnc-pricing-mvp/research/platform-configs/README.md)；它们是本子任务的实际设计输入，不复制状态/金额/安全规则形成第二套定义。

Deep Agents 的真实异常观察/决策/恢复验收按[Agent 设计](../10-21-cnc-pricing-mvp/agent-design.md)，SDK 核验基线 `0.7.29`；正常路径可零模型调用，正式异常恢复能力仍须实际验证。

## 范围与依赖

责任：frontend/web CNC API/views、权限菜单种子、CSV 与真实验收/运行文档；后端必要查询变更保持归属清楚。

进入条件：02～04 接口稳定和两家真实报价；首价前不让完整 UI 成为关键路径。

追溯：MVP-R08/09/10/12/13/14/15；D-01～08；DV-10/12～15；父 AC-12/13。

## 本阶段实现行为

### D-18 现有按钮接入

修改 `frontend/web/src/views/module_cnc/cnc_account/index.vue` 与 `frontend/web/src/api/module_cnc/cnc_account.ts`，消费 02/03 的登录契约。按账号 ID 发起命令，校验权限/启用，行级 loading/重复点击保护，错误与挑战明确反馈；组件卸载停止相关轮询。前端不读取密码/会话密文，不自行判定 VALID，不拼接 Token。

用户已选择受控模式，使用 owner 授权的对话框画面与人工输入入口，契约以 02 的 [集中设计](../10-21-cnc-mvp-02-first-quote/account-login-design.md) 为准。串行轮询 JPEG、坐标换算/键盘文本/滚动及“验证登录”操作有明确状态；不打开普通外部新标签页，不向浏览器交付 Cookie/Token。关闭/卸载停止轮询并请求释放，服务器到期兜底；失败不能保留其他账号或旧会话画面。最终可见账号身份端到端验证，原完整 demo 依赖保持。

1. Web 按平台参数接口展示材料/处理/数量等和配置版本、未验证/不支持状态；依赖变化清空失效子项并明确提示。
2. 任务进度、Deep Agents 步骤/工具摘要/待办、两家报价、完整有效参数、币种/口径、历史/截图/CSV 和实际耗时/介入率展示。后端把框架流转换为脱敏业务 DTO，Web 轮询现有接口，不暴露目录定位器、会话、原始消息/推理或 checkpoint。
3. 完成各 10 项连续实测、12 基准和两轮历史证据，恢复/重启/提示注入/越权/CSV 等 P0 检查。
4. 交付部署/模型/SDK/Skills/流程与恢复策略版本、会话接管/checkpoint 持久卷/备份恢复说明；演示两家 Workflow 报价、改参、实际 Agent 异常策略选择与人工恢复。普通业务暂停不伪造 SDK resume，真实模型/受控 fixture/平台 live 分别记录。

## 验证与风险

frontend/web: pnpm run type-check，pnpm test -- <实现的测试文件>，pnpm run build；TC-08/16～19/23/25～28、TC-CFG-07/08、TC-DA-01～10；TC-17 的旧模型预算按增补设计覆盖。真实报告记录全部失败/人工介入和模型用量，离线 scripted model 不计作 live 成功。

风险/降级：把 null 展示为 0、不同币种排名、配置不可用仍让提交、fixture 冒充实测；界面/报表明确状态与口径。

现有规划文件和静态检查不代表产品实现、真实报价或性能已经通过。保护账号/STEP/证据、有限重试与禁止交易保持父契约。

## BR-2026-10-21 共用归属与选型

[源码依据](../../../docs/browser-reference-analysis.md)和[统一接口](../../../docs/browser-implementation-design.md)为本轮设计输入；[BR](../10-21-cnc-browser-reuse/prd.md) 一处交付 Playwright 官方 SDK 薄封装和独立 MIT 出站代理。展示脱敏步骤与人工待办；恢复经 owner 授权并复验身份/参数/远端 intent。BrowserSkill 仅实际本机复用需求时评估，remote 0.3.1 上传不支持。

禁止另建 CDP/DOM 上传协议、Ref 引擎或 BrowserSkill gateway。接入条件：秘密加密/私有证据及 Trace、owner/platform/account 绑定、允许域、挑战转人工和禁止交易。保留 02/03/04 依赖；分别报告单元/Mock、Chromium 合成 E2E、真实模型/平台，未执行标未验证。

## D-17 前两平台交付边界

本阶段目标固定为 Xometry US 与嘉立创 CNC 中国站；12 基准、每平台 10 项、两轮监测、Web/CSV/证据及全部原验收保持。RapidDirect 为第三家延期 backlog，不出现在当前批次、监测模板或成功率分母中；前两家完整功能与验收完成后才考虑实施。
