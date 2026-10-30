> 历史记录（2026-10-27 已覆盖）：用户已决定直接复用官方 DeerFlowClient Harness，并确认本轮先修改计划、清理自建实现。本文保留原调研/评审事实，其中“SDK 可选”“优先自建 create_agent”及旧授权/状态不再是当前执行要求。现行依据见 [最新方案与范围](harness-client-replan-2026-10-27.md)、父子任务 design/implement 和 [共享契约](local-contracts.md)。

# 规划约束与外部契约核验

调研日期：2026-10-24。仅用于规划分析；无线上平台实测操作或产品代码修改。

## 用户明确后的实际生效范围

用户澄清：“我只运行本项目，不运行agent-platform，只要适配deer-flow即可，简要设计即可”。该声明取代了最初的独立微服务集成方案。当时交付物为自包含 CNC 单项目简要设计，已交付；本轮按用户“根据 trellis 10-24 任务规划开始计划”及后续“继续未完成的任务”扩展为实施规划，仍未授权产品实施。部署边界继续适用；`agent-platform` 仅作为代码参考。保留 CNC 原有的用户身份认证、个人模型配置、Vue 前端以及本地领域服务。不需要独立的 Gateway、Next.js 前端应用、跨服务凭据桥接或修改 agent-platform 仓库。本轮次无需进行产品代码实施。

## 代码版本与工作区状态

- CNC Quote Pilot 仓库版本：`e00019d8a8f36a3884eb8a921db1c731c7d1e941`，分支 `dev`。
- Agent platform 仓库版本：`a041af542f126e96e859497392f8959f24af5c18`。
- 保留 CNC 当前已被修改的 `backend/app/plugin/module_cnc/cnc_part/model.py` 以及未跟踪的 `docs/ai_agent_langgraph_migration_analysis.md`。
- 保留 agent-platform 中未跟踪的 `backend/docs/AGENT_HARNESS_BACKEND_SOURCE_ANALYSIS.md`。

## 依然生效的历史既定决策

来源：`.trellis/tasks/10-21-cnc-pricing-mvp/decisions.md:163` (D-17) 与 `:181` (D-18)，以及 `.trellis/tasks/10-23-cnc-part-config-auto-quote/task.json:24`。

1. 首批接入的两个平台为 Xometry US（`xometry_us`）和嘉立创 CNC 中国站（`jlc_cnc_cn`）。RapidDirect 延期至前两个平台的全部功能与验收通过之后再进行。
2. 严格维持“仅报价”范围：严禁加入购物车、结算、采购、支付、正式下单，或绕过身份认证/人工验证挑战。
3. 嘉立创的系统/参考估价属于 `REFERENCE_ESTIMATE`；无法满足 `QUOTED` 状态，亦无法替代双平台正式报价的验收。其是否提供正式报价属于交付风险，不能借此悄悄降低验收标准。
4. 复用隔离的受控浏览器、所有者/账号级租约、加密会话状态、身份验证与人工挑战处理流程。严禁将 Cookie 直接转移到用户的常规浏览器中。
5. 当且仅当存在一个符合条件且启用的账号时自动选择；存在多个时弹窗供用户选择。由大语言模型或前端直接传入的运行时身份不被视为可信凭据。
6. 历史任务继续保留既往的验收凭证。创建本次集成父任务不会变更历史任务的归属、标记完成、归档或作废它们。

在现有项目内适配所需的 DeerFlow Lead Agent、中间件、工具、技能及前端交互契约。早期的完整 Gateway/API 方案以及基于旧版 Agno 的 LangGraph Checkpointer 提案仅作参考。CNC 业务流程必须保持确定性；智能体不得凭空捏造价格，亦不得绕过平台的参数/意图防护网。

## 当前本地约束

- `E:/AIWorkspace/agent-platform` 仅作为本设计的只读参考资料。规划相关文档统一存放在 CNC 任务目录下。
- 智能体的长期记忆与沙箱基础设施明确排除在本次范围之外。会话连续性、执行记录、加密浏览器会话及价格历史记录依然是必不可少的应用业务数据。
- 技能管理 API 的成功响应并不代表运行时已真正执行。验收必须串联技能发现/激活、实际工具执行、领域记录生成以及界面的最终呈现。
- 本地实现与测试集是已安装 API 行为的唯一权威标准。除非实施证明存在必须解决的兼容性冲突，否则必须保持现有固定的依赖版本。

## 已核验的官方框架文档

以下核验仅确认通用框架能力，并不替代 DeerFlow 实际的 Gateway/扩展契约。

- [LangChain 运行时](https://docs.langchain.com/oss/python/langchain/runtime)：调用上下文（Invocation Context）可以将用户身份和依赖项注入工具与中间件。身份必须起源于经过认证的应用边界。Context API 与可选的长期记忆完全解耦。
- [自定义中间件](https://docs.langchain.com/oss/python/langchain/middleware/custom)：节点钩子与包装器（Wrappers）支持对模型与工具进行拦截。包装器的重试机制可能会导致操作被重复执行，因此领域业务的幂等性与不确定写入对账必须独立于通用的重试建议。
- [流式传输](https://docs.langchain.com/oss/python/langchain/streaming)：消息流、更新流与自定义进度流是彼此分离的。本地适配器应为 Vue 前端封装统一规范的事件协议，而不是强行引入 DeerFlow Gateway 或盲目全盘采纳上游全新的流协议。

官方文档目前也描述了更新的事件流投影机制。但这不能作为在本次任务中升级或重构已安装 DeerFlow 协议的理由。
