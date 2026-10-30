# DeerFlow Agent 源码融入 FastAPI 的规划依据（2026-10-29）

## 用户决定与覆盖关系

用户要求修改聊天等 Agent 计划：不再调用 DeerFlow 接口，将 Agent 代码与当前 FastAPI 架构融合，不能直接整目录移入。
本轮只修订现有父任务及四个子任务、共享契约和上下文，不实现产品、不安装依赖、不操作用户数据库。

运行方案改为“选择 DeerFlow 的必要 Agent 源码，按本项目职责重组并适配”，不使用 DeerFlowClient、远程 DeerFlow HTTP/Gateway 或官方工厂作为运行时入口。
本项目现有 FastAPI API 与用户选择的模型服务仍保留；“不用 DeerFlow 接口”不意味着取消正常模型请求。
2026-10-27 的 Client-only、禁止适配其运行代码等架构限制被本决定取代；此前清理事实、数据保护、权限和业务验收要求继续有效。
2026-10-29 Client 停止门禁记录只解释旧方案为何中止，不再要求等待 Client 新增接口才能推进新方案。
首 token 前停止、1 秒内确认并收敛本地生成仍是必须验证的目标，源码融合本身不等于已通过。

## 本次只读核对

- 来源参考：本机官方 DeerFlow 仓库，提交 `f6fe1e9c9e029bf22b8e2eb8e2e23e1258cf0814`；本次已读的源码映射以此固定提交为基线。实施前按该提交及文件哈希建立来源清单，不使用浮动 main。此前 `24f15cc...` 属于 Client 专项核验，不能冒充本次已完整审查的移植依赖闭包。
- 上游 `backend/packages/harness/deerflow/agents/factory.py` 最终以 LangChain `create_agent` 编译 LangGraph；`lead_agent/agent.py` 负责模型、工具、提示词、技能和中间件组装。后者高度依赖上游 AppConfig、鉴权、存储和可选平台功能，不能只改 import 后复制。
- `agents/middlewares/skill_activation_middleware.py` 有显式技能激活及异步钩子；`skills/parser.py`、`frontmatter.py`、`validation.py`、`storage/` 是技能解析/存储参考。运行时不能用一份临时手写 Markdown 解析器替代这些行为。
- `agents/thread_state.py` 同时包含消息、技能、摘要和沙箱/委派字段。只选择本期所需字段及 reducer，不搬入完整平台状态。
- 当前路由总表为 `backend/app/api/v1/routers.py:DOMAIN_CONTROLLERS`，AI 聊天和 CNC 均显式注册；CNC 代码已在 `app/modules/cnc/`，不再按旧调研路径另建 `app/plugin/module_cnc/`。
- 当前身份为 `AuthSchema.user.id`；请求鉴权沿用 `core/dependencies.py`。数据库资源在 `core/database.py` 的 `async_db_session`，生命周期在 `app/__init__.py:lifespan`，已有 AsyncExitStack 管理清理。
- 聊天在 `ai/chat/{controller,service,crud,schema}.py`，Agno 历史按用户名隔离，个人模型来自现有 Redis 加密配置；不能把用户名或客户端传入 actor 当作新运行时权限源。
- 已有 `cnc/quote/service.py:QuoteService`、`cnc/batch/service.py:BatchService`、`cnc/monitor/service.py:MonitorService` 及 `cnc/cnc_quote_result/service.py:CncQuoteResultService`。批量/恢复/调度相关任务已有完成记录，结果任务仍在进行；源码存在不等于真实平台验收通过。
- 当前开发数据库配置为 PostgreSQL；未读取或记录凭据到本规划。源码适配不授权切库。其他数据库原有聊天兼容继续保留，新 checkpoint 支持范围须单独验证。
- 上游 LICENSE 为 MIT，含 Bytedance 与 DeerFlow Authors 版权声明；实施时保留许可证与来源说明，来源跟踪不能只写“参考 DeerFlow”。

## 源码取舍与目标模块

所有目标均是拟新增或拟修改，不代表当前已有实现。表中上游路径相对 `backend/packages/harness/deerflow/`。

| 上游职责/源码 | 本项目落点 | 保留的行为 | 适配或裁剪 |
| --- | --- | --- | --- |
| `agents/factory.py`、`agents/lead_agent/agent.py` | `ai/agent/graph.py` | 显式模型/工具/中间件/状态组装、框架编译 | 注入项目依赖；不导入上游工厂、不复制业务外的平台组装 |
| `agents/lead_agent/prompt.py` | `ai/agent/prompts.py` | 工具约束、技能目录、上下文边界 | CNC 任务提示词；移除未提供的沙箱、Shell、委派指令 |
| `agents/thread_state.py` | `ai/agent/state.py` | 消息、技能上下文及必要 reducer | 首期 full checkpoint；不移植 delta 格式、沙箱、委派/长期记忆状态 |
| `skills/{parser,frontmatter,validation}.py`、`skills/storage/` | `ai/agent/skills/` | 元数据解析、名称/根目录校验、按需读取、稳定标识 | 单一只读项目技能目录；替换上游用户目录、安装/发布/密钥注入机制 |
| `skill_activation_middleware.py`、`durable_context_middleware.py` | `ai/agent/middleware/` | 显式选择技能、去重激活、活跃技能上下文 | 统一项目权限与技能目录；不引入沙箱文件工具 |
| `dangling_tool_call_middleware.py`、`tool_error_handling_middleware.py`、`system_message_coalescing_middleware.py`、`loop_detection_middleware.py` 等 | `ai/agent/middleware/` | 断开的工具消息修复、安全错误、模型消息兼容、循环/调用预算 | 以本项目固定错误码、logger 和限制替换上游平台依赖；取消异常继续向外传播 |
| `models/factory.py` | `ai/agent/model_provider.py` | 模型构建及必要兼容 | 注入当前用户的 model_id/base_url/api_key/temperature；不搬全局配置和全供应商目录 |
| `runtime/checkpointer/` 的职责 | `ai/agent/checkpoint.py` | 多轮状态持久化 | 直接管理所选 LangGraph async saver 的资源；不移植上游数据库平台/RunManager |
| `runtime/runs/worker.py` 的异步执行/清理思路 | `ai/agent/service.py` | 原生异步图流、可等待清理、终态处理 | 项目服务持有单轮 Task；不复制 Gateway、StreamBridge 或通用运行台账 |
| 上游工具装配与鉴权边界 | `ai/agent/tools/` | 明确工具 schema、受限能力 | 直接调用本项目 CNC Service；不经 HTTP/MCP 绕回自己，不照搬上游 Authz |
| 上游事件消费概念 | `ai/agent/events.py` 与现有 `ai/chat/` | 文本/技能/工具/状态事件 | 项目判别类型及旧/新 WS 投影，不继续绑定官方 StreamEvent |

技能资源放入 `ai/agent/resources/skills/`，由后端发布；开发助手的 `.agents/skills/` 不能直接作为产品可执行目录。
未实现的工具不出现在技能可执行范围。若启用摘要压缩，必须适配上游摘要/技能保持语义并验收；首期先验证 full checkpoint，不将长期记忆混入对话状态。
新增代码需要按行为逐项记录上游提交、文件、哈希、目标文件、改动理由和边界测试；不能恢复先前已删除的代码后宣称完成源码融合。

## 核心实施门禁

1. 先在 Lead 子任务完成所选源码的依赖闭包、最小框架版本解析和来源清单；不安装整个 deerflow-harness/extension-api 及其沙箱/搜索/网关依赖来凑齐 import。
2. 用适配后的真实图组装与原生 async model 做最小对话/工具样本，先验证首 token 前取消、慢流、工具等待、shutdown、异常和资源释放；不能以取消 to_thread 证明取消。
3. 与当前认证、个人模型、只读技能、CNC Service、LangGraph checkpoint 和应用 lifespan 集成。没有真实 stop/隔离证据不得启用新执行器。
4. 聊天任务消费本地 AgentService，承担会话/历史/协议/UI；报价和监测任务仅补工具接入及现有领域实际缺口，不重建已交付服务。
5. 静态依赖扫描、项目回归和实际模型验收分别记录；本轮没有安装、移植或运行产品代码。

## 历史保留

旧清理/Client 核验记录保留原始事实并加历史说明。历史迁移 `a7d30f26b8e1` 及后续链保留；退役 Agent 表不自动复用或删除。
既有 Run/Intent、账号租约、私有凭证和后台任务生命周期继续由 CNC 领域负责。新方案不新建通用 AgentRun/ToolOperation 或第二套调度器。
