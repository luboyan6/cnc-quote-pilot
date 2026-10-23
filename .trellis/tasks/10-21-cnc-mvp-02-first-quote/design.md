# 02 首平台真实闭环与 JSON 加载：设计

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

本子项继承 [父设计](../10-21-cnc-pricing-mvp/design.md)、[稳定契约](../10-21-cnc-pricing-mvp/research/mvp-contract.md)及[平台 JSON 契约](../10-21-cnc-pricing-mvp/research/platform-configs/README.md)；它们是本子任务的实际设计输入，不复制状态/金额/安全规则形成第二套定义。

按[Deep Agents 设计](../10-21-cnc-pricing-mvp/agent-design.md)实现固定 Workflow + 异常恢复 Agent，API 基线 `0.7.29` 见[版本研究](../10-21-cnc-pricing-mvp/research/deepagents-2026-10-21.md)。本任务交付共用转移表、只读观察、策略执行器/守卫/复验、Skills/checkpoint。

## 范围与依赖

责任：backend/app/modules/cnc/ 最小配置/数据/账号/Agent/执行/首 adapter、Skills/checkpoint/预算/事件、API/迁移和 backend/tests/cnc/，必要 backend/pyproject.toml/uv.lock 依赖接入；谨慎接入既有路由/生命周期。

进入条件：01 的首平台实际报价可行性与安全停止点通过；复杂规划经最新评审后开始。

追溯：MVP-R02/03/07/08/10/11/13/14/15；F-01～08；DV-04/05；父 AC-12/13。

## 本阶段实现行为

### D-18 登录命令与受控浏览器

用户已选择受控浏览器。集中技术设计以 [account-login-design.md](account-login-design.md) 为准：复用现有 plugin CRUD 与 BrowserExecutor，POST 登录命令、脱敏状态、私有画面、受限人工输入/验证/关闭 API；一个 owner task 串行操作官方 Page，持久租约及 scope 隔离，空闲/最长时限释放。先修复读模型/导出/日志的秘密暴露并兼容加密凭据。登录切片拟先行交付，不自动上传或提交报价，原完整报价链路前置和验收保持。此处不再维护另一套待定页面交接方案。

1. 将评审后的配置文件迁入 CNC 模块；实现严格 config_schema/受信 registry/loader 和版本哈希固定，返回脱敏参数定义。
2. 复用现有模型/RBAC/CryptoUtil，最少 account/part/task/item/result/event/evidence 与私有存储、迁移/幂等建立。
3. 在 backend/pyproject.toml 与 uv.lock 解析锁定最新稳定 SDK、直接导入的 LangChain/provider/checkpoint 和 Playwright；不迁移现有 Agno 聊天模块。使用显式模型实例做 tool calling/protocol 检查，不复用短期聊天激活缓存作为定时任务唯一模型来源。
4. 实现 execution/workflow.py 的 S01～S11、E01～E13、StepResult/版本更新与安全恢复位置；由代码执行正常报价、已知异常和结果校验。
5. 实现 create_deep_agent 恢复工厂、受信 incident context、只读观察/页面契约工具、RecoveryDecision、当前 allowed_strategies、策略守卫/执行/复验、固定 Skills、StateBackend()/只读 backend 与共享预算；默认关闭委派。
6. 配置私有持久 saver 与 owner/item/incident/thread 绑定；业务 WAITING_HUMAN 按持久步骤恢复，只有实际 SDK interrupt 才用 Command；重启先协调 intent/远端对象，不靠 checkpoint 恢复浏览器。
7. 接入 BR 的 Playwright 账号隔离和上传；本任务的身份复验、持久 upload/submit intent 和唯一键先于首价上线。正常首价/改参与 Agent 异常恢复分别验收；缺模型不阻断已知正常链路，需要模型而不可用时接管，不伪称自动恢复。

## 验证与风险

backend: uv run --offline pytest tests/cnc/ -q；uv run --offline ruff check app/modules/cnc tests/cnc；相应迁移/安全回归。TC-DA-01～08 对应离线故障/守卫检查；真实 F-01～08、模型工具调用与 TC-CFG-01～08 不可由 fixtures 替代。

风险/降级：目录价误用、跨字段重置、旧缓存、0 尺寸、同名控件和模型/恢复故障。Agent 只能选择满足前置的允许策略，无可靠恢复即人工；延期优先砍丰富 UI，不删除固定流程、正式异常恢复或安全验证。

现有规划文件和静态检查不代表产品实现、真实报价或性能已经通过。保护账号/STEP/证据、有限重试与禁止交易保持父契约。

## BR-2026-10-21 共用归属与选型

[源码依据](../../../docs/browser-reference-analysis.md)和[统一接口](../../../docs/browser-implementation-design.md)为本轮设计输入；[BR](../10-21-cnc-browser-reuse/prd.md) 一处交付 Playwright 官方 SDK 薄封装和独立 MIT 出站代理。消费 BR 的 Playwright 层与账号隔离；负责 Xometry US 可信 locator/JSON、回执/几何、完整回读和真实 Decimal 报价，接入前完成持久 intent、账号 ACL/加密会话与异常 Agent。

禁止另建 CDP/DOM 上传协议、Ref 引擎或 BrowserSkill gateway。接入条件：秘密加密/私有证据及 Trace、owner/platform/account 绑定、允许域、挑战转人工和禁止交易。先 BR 组件通过，再按原 01 gates 启用真实 adapter；回执不明只读协调，挑战暂停，禁止盲重发。


## 02 上线前交期类型契约对齐（2026-10-22）

依据 [交期语义研究](../10-21-cnc-mvp-01-platform-gates/research/xometry-lead-time-semantics-2026-10-22.md)，原 SRS 允许生产天数、发货日、到货日等独立类型；现有 BR LeadTime/validate_quote 仅接受数值 duration/day_basis，不能承载 Xometry 的 Arrives by 原文。02 必须在启用 Xometry runtime 前演进共享类型、校验与 API/持久化/证据快照：生产 duration、ship date、arrival date/label 分别建模，保留 raw/type/source，未给年份/起算点/工作日规则则 unknown/null，不能从观察日倒算生产天数或把运输假设扣掉。未知日期字段不得填造；到货标签不改名为生产交期。该调整对齐 SRS，不自动通过 G-05/E2；真实报价仍须同次参数、价格性质、币种/范围、可解释交期和新鲜度依据。

2026-10-23 独立切片以 [lead-time-design.md](lead-time-design.md) 为具体契约：共享值对象采用 version2 的 duration / production_duration / ship_date / arrival_date，旧四字段快照保留通用 duration 语义，不能自动升级为已证实生产周期。现存正式报价 API/领域持久化/前端页尚未实现；本轮先交付可共用的严格编解码与组件验证，正式贯通仍随原报价 gates 另行实施。

- [ ] 回归组件构造/序列化/validate_quote、领域 DTO/API 与快照：明确 duration 的合法 min/max/day_basis；arrival/ship 类型拒绝混入推算 duration，原文无年份可保留。
- [ ] 验证缺失/无解释交期、无效区间/日期、未知 day_basis/起算点、旧版本快照兼容与前端显示；不得把未知字段当成功证据，不降低原 duration 类型检查。
- [ ] 对 Xometry A/B arrival-only 记录与嘉立创工作日说明分别验证，不跨报价/档位/平台借值；真实 live 与离线契约检查分开报告。
