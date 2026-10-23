# CNC MVP 技术设计与仓库兼容方案

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

状态：规划产物，尚未启动产品研发。来源为父 PRD、SRS v1.0、decisions.md 及 research/；当前按 D-17 为 Xometry US → 嘉立创 CNC，RapidDirect 延期、5 工作日、先真实闭环、逐平台 JSON，并最新指定采用 Deep Agents。网站真实性以 [实际配置调研](research/rapiddirect-configuration-2026-10-21.md) 为准。Agent 选型/API/预算/恢复以 [Deep Agents 增补设计](agent-design.md) 为当前权威；原 SRS 的被替代条款见其第 1 节。

## 1. 范围与核心决策

- 复用现有 FastAPI/SQLAlchemy/Alembic/RBAC/Redis/APScheduler 与 frontend/web；不新建独立应用、第二个调度器、Celery 或通用浏览器 Agent。
- `deepagents==0.7.29` 负责未知页面/异常原因/页面变化分析与恢复策略选择；runner 按[固定 workflow](workflow-design.md)执行正常步骤、管理转移/租约/锁/预算。Agent 在当前异常的 allowed_strategies 内选择，代码守卫执行并复验，模型不生成价格、替代参数、跳业务步骤或交易。
- 两个平台独立 JSON：材料/处理/颜色/粗糙度/数量约束、可选附加项、UI 变体、定位和报价提取元数据。完整字段、加载契约、来源与待验证项以 [配置 README](research/platform-configs/README.md) 为准；旧两份 JSON 的静态校验保留原历史范围；当前前两家各自维护 draft，嘉立创配置必须独立建证据，不是已运行适配器。
- 先验证首份真实价格，首个研发交付点只实现一条上传→配置→报价→证据的纵向链路，后加第二家与批量/定时/Web。

## 2. 拟落地目录和职责

    backend/app/modules/cnc/
      controller.py / schema.py / model.py / service.py
      platform_configs/xometry_us.json / jlc_cnc_cn.json / platform.schema.json
      config_schema.py / config_loader.py
      execution/runner.py / workflow.py / state.py / browser_session.py / policy.py
      agent/factory.py / model_factory.py / context.py / tools.py
      agent/middleware.py / checkpoints.py / skills_backend.py / events.py
      agent/skills/xometry-us-quote/SKILL.md / jlc-cnc-cn-quote/SKILL.md
      adapters/base.py / xometry_us.py / jlc_cnc_cn.py
      parsers.py / snapshots.py / evidence.py
      scheduler.py
    backend/tests/cnc/
    frontend/web/src/api/module_cnc/
    frontend/web/src/views/module_cnc/

具体文件按现有模块控制器/服务约定组织；上述是责任边界，不要求 Day 1 一次建立所有空文件。Deep Agents 为 CNC 必需依赖，与直接导入的 LangChain/provider/checkpoint 包在同一 uv.lock 中解析固定；Playwright 锁定与浏览器匹配的版本。不迁移已有 Agno 通用聊天模块，不新增 AgentSeek/Bub 服务。实施前读现有 Trellis 层规范并按[版本研究](research/deepagents-2026-10-21.md)复核最新发行版。

## 3. 配置、适配器与请求的关系

- 受信注册表 platform_code → 固定 JSON → 固定适配器类；用户和页面都不能指定文件路径、模块名或脚本。配置不含凭据，不接受网页返回内容写回受信 JSON。
- config_loader 用 Pydantic 严格校验消费字段、Schema 版本、依赖图、已使用映射上下文和 locator 唯一性；JSON Schema 用于静态审阅。配置开启标志不足以证明已验证：待用动作/参数/价格提取必须有同版 live 依据。
- 任务请求给统一意图和明确平台差异参数。按该平台实际支持情况精确映射；不支持/未知返回可读错误，不能复制另一平台 ID 或用最相似材料。
- catalog 是当前上下文已加载目录；可包含不可自动报价的 Other/Custom/禁用记录。实际执行重新确认当前可选值及依赖，网站改版触发配置过期/人工待办，不能把 catalog 当无限期正确事实。
- 参数 UI 经后端返回脱敏字段定义/可选子集。Web 不读原始定位器/全部目录，不解析网站页面，也不持有账号会话。
- 任务固定 config_version、原文件字节 SHA-256、adapter_version 与私有归档引用；只存一份不可变配置归档，item 保存所用映射和 requested/effective 快照。修改 JSON 不影响在途/重试任务。
- 金额和交期由实际报价 DOM 经固定解析器取得；配置只保存提取位置/语义，不保存预设报价。网站材料目录 price 与 is_auto_price 不是零件报价证据。

## 4. 执行流程和浏览器边界

持久 task/item → 领取租约/冻结版本 → 固定顺序：认证 → 上传 → 等几何解析 → 配置 → 参数核对 → 提交询价 → 等报价 → 读取报价 → 截图 → 校验入库。正常链路直接使用确定性服务/adapter；已知错误走规则，未知异常进入 Deep Agents 观察/分析/策略选择 → 守卫执行 → 复验 → 返回规定步骤，或人工/停止。

恢复 Agent、只读观察工具、禁用开放规划/子代理、固定 Skills 和当前 StateBackend() API 见[Agent 设计](agent-design.md)；S01～S11、E01～E13、策略条件和恢复位置见[workflow-design.md](workflow-design.md)。正常链路可零推理；需要 Agent 而模型不可用时明确 AGENT_UNAVAILABLE 并转人工/失败，不伪报自动恢复。

- 正式运行每账号独立 Playwright BrowserContext；storage_state 使用现有 CryptoUtil 加密保存，运行时在内存解密。会话复用先验证业务页身份，不以 Cookie 未过期代表登录成功。
- 允许账号持有人在受控可见浏览器处理 CAPTCHA/MFA；程序等待并复验身份，秘密不进入聊天/日志。自动重登至多一次，挑战不做绕过。
- CDP bridge 仅用于当前开发调研及受控核验；临时修复不是生产组件。正式执行不依赖用户日常浏览器的随机页签或 Vue 私有写入。
- 下拉先确认页面/样件范围与可见唯一控件；固定等待可解释状态和文本，不堆固定 sleep。数量回显、材料变动后的处理/粗糙度、处理后的颜色和新增必填项必须复验。
- RapidDirect 当前 live 为 Finish/Apply，截图为 Surface Finish/Save。UI 变体按实测配置；当前仅记录了单样件输入绑定，未实测选项点击、保存或报价结果。
- 0×0×0 mm 不能作为解析成功证据。尺寸或预览异常时限时等待/排查，不因出现 Configure 就跳过几何关卡。

## 5. 状态、恢复和资源预算

使用 research/mvp-contract.md 的 task/item/quote_status/freshness 枚举，不为单平台另造状态。中间字段和浏览器当前步骤持久化为可解释事件。

- 默认一个自动运行，同账号一个自动 context，最多一个额外人工暂停 context；平台访问率配置化且不超过站方限制。
- 自动重试≤2，恢复/回查计入总 attempt≤3，累计活跃执行≤600秒；重试不重置总预算。人工/审核等待独立统计并设置有限到期处理。
- 保存 submit intent、远端引用及配置摘要。保存/提交回执不明先只读协调，不能盲目点击 Apply 或重新上传；关联不明转人工。
- 重启不从任意浏览器内存续跑：回收过期租约，按远端引用回查可确认状态；不能确认的副作用保留待办。取消后不再发新动作。
- Agent checkpoint 与领域记录分别保存；同一 incident 沿用受权 thread，先协调租约/intent/远端引用再重建 context，重放不绕过领域唯一键。业务人工暂停按 resume API/记录位置恢复；只有实际 SDK interrupt 使用 Command，随后仍复验身份/参数。
- 所有 incident/Agent 观察/策略选择、SDK 隐藏调用和重试共享持久预算；每异常≤2轮选择、每轮≤1恢复动作，策略前置由代码校验。具体限额见[Agent 设计第 6 节](agent-design.md)；原活跃≤600秒、attempt≤3和重登≤1不变，恢复不清零。
- SUCCEEDED 要求明确 QUOTED、核实新鲜度、请求/有效参数匹配及同次证据齐全；审核/参考估价/无价和缓存未确认均不能补成功率。

## 6. 存储与兼容

- 业务交付沿用现有应用配置的数据库，离线测试用临时 SQLite；不为了轻量化再建一套业务数据库。Agent checkpoint 使用私有持久存储：单机 MVP 的专用 AsyncSqliteSaver 仅单 CNC consumer 持有，已有 PostgreSQL 可按增补设计选 AsyncPostgresSaver。它不保存第二份报价事实；内存 saver 不满足重启恢复。当前实际业务 DB 连通性尚未测，环境文件和连接串不输出到调研。
- 复用 ModelMixin 整型内部主键及 uuid，对外 CNC API 用 UUID，内部 FK 与 sys_user 保持整型兼容。与 SRS 独立 UUID 主键示意的差异在此明确，不改已有基类或存量主键。
- 逻辑实体：platform、account、part、quote_task、quote_item、quote_result、schedule、execution_event、evidence。表名 cnc_ 前缀，显式命名 FK/索引，通过现有 Alembic 模型发现链接入。
- account 关联 owner 与平台、加密凭据/会话、session 有效性和人工待办；part 关联 owner、私有对象键、SHA、单位及原始名。UUID 难猜不替代 owner/RBAC 校验。
- task/item 存请求/有效参数快照、配置/适配器版本、租约、attempt/预算、远端引用/intent 与错误分类；result 以 Decimal 字符串响应，数据库 Numeric，保存金额口径、币种、原始/规范交期、新鲜度与证据关联。
- item 关联 execution_generation、workflow_version/摘要、step/step_version/resume_step/StepResult、固定模型/配置版本；incident 关联观察/策略决策/执行/复验、server thread 和用量。无异常不强制创建 checkpoint；版本不符停止协调，秘密/浏览器对象/CAD 不进入模型状态。
- API 幂等键按 owner+键唯一，同键异参 409；同批 item 去重含文件哈希/平台/参数，同一监测轮次固定唯一键。不同监测轮次不因同价被合并。
- 结果/历史追加，重试事件幂等不重复成功观测；使用结果唯一事件键和 item 的最终结果引用。中间审核状态不覆盖旧价格。索引覆盖 task+状态、租约、part+platform+时间、比较参数指纹。
- 配置版本负责复现，历史可比性依据完整有效规格与商业口径；字段 unknown 不与另一个 unknown 视为相同。税运未知为 null，生产/运输/交货语义分开，禁止跨币种直接排名。

## 7. 必要接口与调度

以现有 API v1 注册和 code/msg/data/success envelope 为准，CNC 域前缀 /cnc；所有对象按现有 AuthPermission 加 owner 范围校验。

| 方法/相对路由 | 首次交付 | 责任 |
|---|---|---|
| GET /cnc/platforms；GET /cnc/platforms/{code}/parameters | 02 | 受信平台、配置版本、可用参数子集和待验证状态 |
| POST/GET/PATCH /cnc/accounts；POST /cnc/accounts/{uuid}/session-check | 02 | 最小账号别名/凭据引用、会话状态、受控人工待办，不回显密文 |
| POST /cnc/parts | 02 | STEP/STP 大小/扩展名/内容基本检查、哈希、私有存储与 ACL |
| POST /cnc/quote-tasks；GET /cnc/quote-tasks/{uuid} | 02 | 快速持久返回 202，轮询状态，不在 HTTP 请求中跑浏览器 |
| POST /cnc/quote-tasks/{uuid}/cancel；POST /cnc/quote-items/{uuid}/resume | 02/04 | 有限取消/人工恢复，复验 owner 和状态，不任意跳步骤 |
| GET /cnc/quotes；GET /cnc/quotes/history | 02/04 | 结果、严格可比条件、历史与真实指标 |
| GET /cnc/execution-events；GET /cnc/evidence/{uuid} | 02 | 受权限保护的 Agent 步骤/待办/用量摘要和脱敏图片，不返回原始消息/checkpoint 或公开路径 |
| POST/GET/PATCH /cnc/schedules；POST /cnc/schedules/{uuid}/disable | 04 | 固定周期持久计划、禁用和幂等触发 |
| GET /cnc/quotes/export | 05 | 按权限与筛选导出 CSV，防公式注入 |

核心错误约定：未知平台/不可映射参数 422；同键异参/在途冲突 409；无权限遵从现有 403/404 防对象枚举；配置未验证/不匹配不启动动作，返回 CONFIG_UNVERIFIED/PARAMETER_UNMAPPED/CONFIG_CHANGED 等业务原因。最终数值错误码按仓库统一机制登记，不硬造已有编号。

调度复用 SchedulerUtil 的 leader/内建任务注册；定时入口只创建有唯一轮次键的持久任务，runner 异步领取。错过/重叠轮次记录 skipped，默认不并发追赶站方，不另建共享 jobstore 调度器。

## 8. 安全、验证与回滚

- 复用 backend/app/utils/crypto_util.py 的 CryptoUtil，生产缺少安全密钥按现有配置约束处理；不在新 JSON 放 SECRET_KEY 或自行发明密钥存储。
- 私有 STEP/截图/会话不走公开 static；日志过滤 credential/cookie/session，截图裁剪/遮盖按既有实现选可行方式，无法脱敏则受限保存且不发给模型。
- JSON 不允许脚本/Prompt/任意请求地址。页面文本、颜色名和目录描述全部是不可信数据，不能扩大工具权限、改 allowlist 或触发交易；后台禁止购买/支付/账号安全修改。
- 首条验收需真实价格 + 改数量重算；后续 12 组合、20 连续明细、两轮自动监测及 Web/CSV，指标仍为建议目标直到实测。
- 验证覆盖 TC-CFG-01～08、SRS P0 与异常/越权/回执不明；离线测试不能代替真实平台验证。
- 增补 TC-DA-01～10、TC-WF-01～06：固定序列、E01～E13、实际异常 Agent 的策略选择、守卫/复验、有限恢复、版本/幂等/脱敏。D-13 覆盖早期开放规划/helper 和每个正常步骤强制模型调用的草案；正常零模型调用不算缺陷。
- 以 CNC 域功能开关和账号/平台 enabled 停止调度及新领取，待在途安全停止；回滚新增模块/配置版本，已采集历史保留。新增迁移先在隔离库验证，不自动回滚用户存量表。

## 9. 仍待真实验证的技术项

Xometry US 的首平台身份/可用路径、完整参数与改材/处理、真实价格/交期/优惠口径；嘉立创 CNC 的源件关联、账号/会话路径、独立参数/选项及参考估价到真实报价的可行性。RapidDirect 零几何等未解决项只保留为延期研究，不是前两家前置。新增 Deep Agents 依赖解析、provider tool calling、技能只读 backend、checkpoint/驱动和实际运行预算验证，不能把官方示例当已通过。按 01/02 限时验证，如平台不通过换授权候选样件/候补服务商并明确变更；不通过开关、模拟报价或无限重试掩盖。

## BR-2026-10-21 共用归属与选型

[源码依据](../../../docs/browser-reference-analysis.md)和[统一接口](../../../docs/browser-implementation-design.md)为本轮设计输入；[BR](../10-21-cnc-browser-reuse/prd.md) 一处交付 Playwright 官方 SDK 薄封装和独立 MIT 出站代理。所有平台/调度消费同一 Browser Executor，保留固定 Workflow 与受控异常 Agent。组件和真价分级验收，AC-01～13 不因合成测试而勾选。

禁止另建 CDP/DOM 上传协议、Ref 引擎或 BrowserSkill gateway。接入条件：秘密加密/私有证据及 Trace、owner/platform/account 绑定、允许域、挑战转人工和禁止交易。新增共用修订任务先交付组件，原 01→02→03→04→05 的真实业务进入条件不变。
