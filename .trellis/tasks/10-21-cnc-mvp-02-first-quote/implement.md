# 02 首平台真实闭环与 JSON 加载：实施清单

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

当前分工继承[业务 Workflow 与异常分支](../10-21-cnc-pricing-mvp/workflow-design.md)：S01～S11 固定正常步骤，E01～E13 规定出口；Deep Agents 分析未知异常并选择允许策略，代码守卫/复验后恢复，正常步骤不强制模型调用。

状态：in_progress，D-18 登录切片已按用户明确确认先行实施并完成自动化检查，真实平台认证仍未验收；完整报价、Agent 和监测尚未实施，原前置不变。见本目录 design.md/prd.md 和 [D-18 验证记录](research/login-validation-2026-10-22.md)；账号持有人手动/受控可行性测试无需等待完整报价研发。

## 顺序

### D-18 账号自动登录增补

- [x] 用户选择受控浏览器，补齐 [集中登录设计](account-login-design.md) 的 API、画面/人工输入、租约和生命周期；沿用现有任务。
- [x] 完成登录切片最终规划复核，用户明确答复“是”；在本任务内执行登录切片，原完整报价 gates 不变，不能据此启动全报价/Agent/监测。
- [x] 复用现有 plugin 账号/平台服务与权限，拆分读写 DTO，兼容密码留空保留及加密迁移，核对查询/导出/日志脱敏。
- [x] 实现登录命令、可信平台入口解析、持久租约、加密会话恢复、身份核验、最多一次重登与挑战转人工；成功后进入询价页。
- [x] 实现 owner task 有界命令队列、私有 JPEG 画面及人工输入/验证/关闭 API；不跨 task 操作 Page，不记录画面或输入正文。完成 05 登录入口与 03 嘉立创公共契约交接；自动化验证过期、并发、关闭、取消和资源释放，真实平台界面联调另列。
- [x] 完成后端 47 项、真实 Chromium 合成 3 项及前端 15 项回归，补齐日志/Windows 子进程/连续输入问题和规范；详细命令与边界见 [验证记录](research/login-validation-2026-10-22.md)。
- [ ] 完成 F-LOGIN-01～04 的真实平台与部署验收。本机保留地址混合 DNS 导致出站拒绝；离线/合成/真实分别报告，不以 Mock 或已有人工登录代替真实产品验证。当前未勾选 live。

- [ ] 读 design.md、父设计/稳定契约、当前平台 JSON/实际证据和目标层规范；核对仓库未提交修改。
- [ ] 确认进入条件：01 的首平台实际报价可行性与安全停止点通过；复杂规划经最新评审后开始。
- [ ] 将评审后的配置文件迁入 CNC 模块；实现严格 config_schema/受信 registry/loader 和版本哈希固定，返回脱敏参数定义。
- [ ] 复用现有模型/RBAC/CryptoUtil，最少 account/part/task/item/result/event/evidence 与私有存储、迁移/幂等建立。
- [ ] 按父 agent-design.md 核验并锁定最新稳定 SDK（当前 deepagents==0.7.29）、直接导入的 LangChain/provider/checkpoint 与浏览器依赖；更新 pyproject.toml/uv.lock，先验证模型工具协议，保留已有 Agno 聊天依赖。
- [ ] 实现 S01～S11 固定 Workflow、E01～E13、StepResult/step_version/resume_step、已知错误规则与幂等，不在正常步骤增加模型选择。
- [ ] 建立 create_deep_agent 恢复工厂、固定模型引用/incident context、只读观察/页面契约工具、RecoveryDecision/allowed_strategies、策略守卫/执行器/复验、平台 Skills 与 StateBackend()；默认禁用子代理和开放业务规划，全部异常共享 item 预算。
- [ ] 接入持久 checkpoint、owner/item/incident/thread、脱敏事件与业务人工恢复；仅实际 SDK interrupt 用 Command，内存 saver 仅离线测试。
- [ ] 复用 BR 的 Playwright 账号隔离/生命周期；接入登录态复验、runner 租约/预算、持久领域唯一键及 submit intent/回执不明协调，先于首价上线，SDK 重放不能重复副作用。
- [ ] 正常 Workflow 直接完成上传/解析/配置回读/Apply 或实测变体/真实报价/证据；未知页面调用 Agent 选允许策略，守卫执行并复验后恢复。提交不明只读协调，本地存储失败只补 S10/S11。
- [ ] 改参建新 item；分别验证正常零模型路径、实际 Agent 异常选择、非法/过期策略拒绝、无可靠策略接管、模型缺配/预算/权限、重启/取消/重放，覆盖 TC-DA-01～08 与 TC-WF-01～05。
- [ ] 验证 MVP-R02/03/07/08/10/11/13/14/15；F-01～08；DV-04/05、父 AC-12/13，更新实际结果与证据，不勾选未执行的 live 验收。
- [ ] 运行本阶段质量检查，交接父任务和后续子项；主会话处理最终 review/提交/归档。

## 检查入口

backend: uv run --offline pytest tests/cnc/ -q；uv run --offline ruff check app/modules/cnc tests/cnc；相应迁移/安全回归。TC-DA-01～08 的离线守卫/故障恢复单列，真实 F-01～08、provider 工具调用和 TC-CFG-01～08 不可由 fixtures 替代。

只运行已实现文件和适用的检查；命令/用例名称是实施计划，不能据此声称已通过。固定 JSON 用现有 Python/jsonschema 静态校验，产品测试按实现后实际命令执行。

## 变更与回滚

仅修改责任范围：backend/app/modules/cnc/ 最小配置/数据/账号/Workflow/恢复 Agent/首 adapter、API/迁移、tests/cnc 和必要 pyproject.toml/uv.lock；谨慎接入路由/生命周期。保存流程/策略/配置/SDK/模型/Skills 版本、真实历史/intent/私有 checkpoint，回滚先安全停止，不删源模型/历史，不改共享基类、Agno 聊天或用户环境。停用异常 Agent 时标记能力不可用，正常已知流程可继续，未知异常转人工，不伪称自动恢复；依赖变更同步后续子项并回归。

## BR-2026-10-21 实施增补（合并共用实现）

- [ ] 读[统一设计](../../../docs/browser-implementation-design.md)和[BR](../10-21-cnc-browser-reuse/prd.md)；复用基础组件。
- [ ] 消费 BR 的 Playwright 层与账号隔离；负责 Xometry US 可信 locator/JSON、回执/几何、完整回读和真实 Decimal 报价，接入前完成持久 intent、账号 ACL/加密会话与异常 Agent。
- [ ] 先 BR 组件通过，再按原 01 gates 启用真实 adapter；回执不明只读协调，挑战暂停，禁止盲重发。
- [ ] 执行 F-BR-01/02 与原用例，记录命令/环境/失败/未验证项；秘密/STEP 不进模型或日志，Trace 仅私有授权诊断。


## 02 上线前交期类型契约对齐（2026-10-22）

依据 [交期语义研究](../10-21-cnc-mvp-01-platform-gates/research/xometry-lead-time-semantics-2026-10-22.md)，原 SRS 允许生产天数、发货日、到货日等独立类型；现有 BR LeadTime/validate_quote 仅接受数值 duration/day_basis，不能承载 Xometry 的 Arrives by 原文。02 必须在启用 Xometry runtime 前演进共享类型、校验与 API/持久化/证据快照：生产 duration、ship date、arrival date/label 分别建模，保留 raw/type/source，未给年份/起算点/工作日规则则 unknown/null，不能从观察日倒算生产天数或把运输假设扣掉。未知日期字段不得填造；到货标签不改名为生产交期。该调整对齐 SRS，不自动通过 G-05/E2；真实报价仍须同次参数、价格性质、币种/范围、可解释交期和新鲜度依据。

- [ ] 回归组件构造/序列化/validate_quote、领域 DTO/API 与快照：明确 duration 的合法 min/max/day_basis；arrival/ship 类型拒绝混入推算 duration，原文无年份可保留。
- [ ] 验证缺失/无解释交期、无效区间/日期、未知 day_basis/起算点、旧版本快照兼容与前端显示；不得把未知字段当成功证据，不降低原 duration 类型检查。
- [ ] 对 Xometry A/B arrival-only 记录与嘉立创工作日说明分别验证，不跨报价/档位/平台借值；真实 live 与离线契约检查分开报告。
