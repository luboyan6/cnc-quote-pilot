> 历史记录（2026-10-27 已覆盖）：用户已决定直接复用官方 DeerFlowClient Harness，并确认本轮先修改计划、清理自建实现。本文保留原调研/评审事实，其中“SDK 可选”“优先自建 create_agent”及旧授权/状态不再是当前执行要求。现行依据见 [最新方案与范围](harness-client-replan-2026-10-27.md)、父子任务 design/implement 和 [共享契约](local-contracts.md)。

# 调研：DeerFlow API 与 CNC Lead 智能体集成分析

- 调研目标：明确最小化的 HTTP 集成方案、以扩展优先（Extension-first）方式构建的 CNC 工具/中间件/技能，并精准定位在不引入长期记忆与沙箱执行的前提下构建 Lead Agent 的技术差距。
- 调研范围：内部源码及本地文档；只读审查 `E:/AIWorkspace/agent-platform`。
- 日期：2026-10-24。
- 路径约定：`AP/` 表示 `E:/AIWorkspace/agent-platform/`；其余路径均相对于 CNC 仓库根目录。

## 当前范围调整（取代下文关于独立 Gateway 的建议）

父任务转达了用户的进一步明确：**仅运行 CNC 项目，不运行 `agent-platform`；本轮次仅提供简要设计，无需进行产品代码实施。** 将 `agent-platform` 视为本地参考资料。下文关于 HTTP 的调研结论属于对参考设计的技术证据，不再作为部署要求，亦非修改该参考仓库的授权。

推荐的简要设计：在 CNC 的 FastAPI 应用内部构建 Lead Agent，完整保留现有的用户认证体系、加密的个人模型配置、平台账号/会话持久化、可靠的报价执行器以及 APScheduler 调度器。复用 DeerFlow 的成熟架构模式：单 Lead 运行循环、强类型的提交/查询/取消/结果工具、显式的技能目录与激活机制、精选的用于鉴权/错误处理/循环限制/进度反馈的中间件，以及带有持久化 Run/事件/存据 ID 的 SSE 传输协议。显式禁用长期记忆与沙箱执行。现有的业务 API 依然保持唯一权威；智能体仅作为业务流程的编排者。在单项目内运行能够无缝保留现有的个人模型配置，避免了复杂的服务端模型目录迁移。

**直接内嵌 DeerFlow SDK 是技术可行的（无需 Gateway 独立进程），但这属于依赖项层面的选择，并非硬性要求：**

- 公共导出 `from deerflow.agents import create_deerflow_agent, RuntimeFeatures` 位于 `AP/backend/packages/harness/deerflow/agents/__init__.py:8`，并在第 34 行懒加载。
- 该 Factory 接收现有的 LangChain `BaseChatModel`、`BaseTool` 列表、字面量提示词、可选的 Checkpointer、State Schema 以及调用方注入的中间件（`AP/backend/packages/harness/deerflow/agents/factory.py:67`）。可设置 `features=RuntimeFeatures(sandbox=False, memory=False, subagent=False, vision=False, auto_title=False)` 及可选的 `extra_middleware`；沙箱标志会同步跳过 ThreadData、Uploads 和 Sandbox 中间件（`:248`）。该 Factory 本身不负责启动 Gateway、RunManager 或任何常驻服务。
- 此外，直接传入 `middleware=[...]` 会完全接管中间件调用链；它不能与 `features` 或 `extra_middleware` 同时混用（`factory.py:140`）。传入的对象与工具最终交由 LangChain 的 `create_agent` 处理（`:161`, `:189`）。若提供 Checkpointer，需保留 `checkpoint_channel_mode="full"`；该 Factory 显式拒绝持久化的 Delta 增量模式（`:142`）。无论采用哪种方式，CNC 都必须自行实现运行注册表、取消控制、SSE 通道及 Checkpoint 的生命周期管理。
- 通用 Factory **不会**自动启用技能系统。现有的 `SkillActivationMiddleware` 可以在无沙箱环境下显式挂载；但其构造函数强制要求传入运维生成的 `slash_source_owner_token` 以及可选的所有者/AppConfig/技能授权（`.../skill_activation_middleware.py:121`）。其内部的 `_storage` 强绑定于 DeerFlow 自身的技能存储与配置，无法直接接入 CNC 的存储接口（`:274`）。而显式技能加载逻辑本身使用的是宿主机安全读取（`:282`）。因此，需要开发完整的 CNC 自定义技能服务或轻量适配器；单纯引入该中间件并不能达成技能系统的完整集成。
- 完整的 `deerflow-harness` 引入了一整套不可选的依赖项，包括 `agent-sandbox`、Kubernetes、MCP 以及多个模型 Provider SDK，即使运行时特性被完全关闭也是如此（`AP/backend/packages/harness/pyproject.toml:6`）。CNC 目前使用 Python >=3.12，在语言层面完全兼容，但工程内尚无 LangChain/LangGraph 依赖，且锁定了 Agno 2.5.8 技术栈（`backend/pyproject.toml:6`）。依赖冲突消解与运行时测试仍不可或缺；本次调研未安装任何外部依赖。
- **简要设计的首选推荐：** 基于 `langchain.agents.create_agent` / LangGraph 构建一个轻量级的 CNC 本地 Lead 实现，有针对性地引入精简中间件与本地技能端点，充分吸纳 DeerFlow 的架构模式。这能够避免强依赖同级仓库的本地物理路径或全盘引入其沉重的运行时。应将其准确描述为“适配 DeerFlow 的 Lead Agent 架构设计”，而非“连接至 DeerFlow Gateway API”。若后续确实决定直接复用 SDK，应在 CNC 分发体系内将其封装为可重现的固定 Harness 依赖包或 Wheel 文件，切勿硬编码指向 `E:/AIWorkspace/agent-platform` 的绝对路径，亦不要求运行外部独立进程。局部代码吸纳需遵循开源许可证声明与维护边界，避免无节制地复制代码库。

先前关于将个人模型设置迁移至独立 Gateway 目录的所有顾虑，均是建立在已被取代的跨进程部署方案之上的。对于同一项目内的内嵌方案，只需完整保留现有的个人设置，并在 Lead Factory 背后对模型对象进行适配即可。

## 调研发现

### 发现的文件

| 文件 | 用途说明 |
| --- | --- |
| `AP/AGENTS.md` | 服务拓扑架构、扩展优先原则、部署约定规范。 |
| `AP/backend/AGENTS.md` | Harness 与 App 的边界、内部上下文信任机制、后端强制测试要求。 |
| `AP/backend/docs/API.md` | 权威的本地 HTTP 请求/响应、鉴权、SSE、技能、上传及调度器参考文档。 |
| `AP/backend/docs/AUTH_DESIGN.md` | 平台级信任身份与所有者隔离设计，特别是第 312 至 373 行。 |
| `AP/backend/docs/AGENT_HARNESS_BACKEND_SOURCE_ANALYSIS.md` | 用户提供的 Harness 源码分析报告；基准版本标注为 2026-09-03（第 4 行）。具备参考价值，存在源码漂移时以当前最新源码为准。 |
| `AP/backend/app/gateway/services.py` | 运行准入控制、鉴权上下文构建、助手选择及定时任务拉起逻辑。 |
| `AP/backend/app/gateway/routers/{threads,thread_runs,skills,models,managed_models}.py` | 具体的 HTTP 接口生命周期与目录服务契约。 |
| `AP/backend/packages/harness/deerflow/agents/lead_agent/{agent,prompt}.py` | Lead Agent 组装、自定义 Agent 策略、模型/工具/技能选择机制。 |
| `AP/backend/packages/harness/deerflow/agents/middlewares/skill_activation_middleware.py` | 宿主机侧安全的显式技能加载与激活审计中间件。 |
| `AP/backend/packages/extension-api/deerflow_extension_api/{contracts,plugins,placement}.py` | 公共扩展机制能力与鉴权工具调用上下文。 |
| `AP/backend/packages/harness/deerflow/extensions/{plugin_tools,isolation,stack}.py` | 工具调用约束、扩展故障隔离及语义化中间件挂载堆栈。 |
| `AP/examples/deerflow-extension-bookmarks/deerflow_extension_bookmarks/__init__.py` | 基于公共 API 构建的、具备所有者过滤的插件工具/Action 极简范例。 |
| `AP/backend/docs/extension-agent-runs.md` | 面向扩展的可选完整 Agent 控制接口；对 Internal / PAT 主体明确不可用。 |
| `AP/examples/deerflow-extension-workflows/AGENTS.md` | 复杂的 Workflow 异常恢复不变式及 POSIX/QuickJS 运行约束；CNC MVP 无需这些。 |
| `AP/frontend/src/content/en/harness/integration-guide.mdx` | 主要介绍内嵌式 `DeerFlowClient`，并非主流的 HTTP 集成指南。 |

### 1. 早期的 HTTP 方案（范围调整后仅作参考）

在最初的“独立 API 微服务”设想下，CNC 应用现有的鉴权后端作为 BFF 及业务权威中心（负责管理平台账号、STEP 文件、持久化报价执行、结果与存证），通过 HTTP 调用独立的 DeerFlow Gateway 进行对话管理与流程编排。封装后的 CNC 扩展插件通过受限工具调用上述业务 API。**上述最新明确的单项目范围已取代该部署方案。**

该方案遵循了 `AP/AGENTS.md:90` 中的扩展优先原则及 `AP/backend/packages/harness/deerflow/extensions/AGENTS.md:171` 中的公共贡献契约。在 CNC 内部无需从零编写底层的 LangChain/Deep Agents 框架。所有的 HTTP 助手最终均路由至 `assemble_lead_agent`；`assistant_id` 仅用于选择自定义 Agent 的配置策略，而非调用任意的 Python 图对象（`AP/backend/app/gateway/services.py:1146`）。

可为每个映射的所有者配置自定义 Agent（如 `cnc-quote`），设置 `memory_enabled: false`、受限的 CNC 工具组、`mcp_plugins: []`、`allowed_subagents: []` 以及核准的 CNC 技能名称。这些策略字段均已现成支持（`AP/backend/packages/harness/deerflow/config/agents_config.py:207`）。Agent 定义绑定用户作用域；尝试加载未配置的 Agent 会直接抛出 `FileNotFoundError`，而非静默回退（`.../config/agents_config.py:332`）。在独立部署方案中也可以关闭全局记忆，无需编写记忆组件。短期 Checkpoint 与会话持久化必须保留，以支持重新接入与链路追溯。

### 2. 认证、所有权与 BFF 信任

- Gateway 原生路由使用 `/api/threads/...`、`/api/models`、`/api/skills` 等。`/api/langgraph/...` 仅为 Nginx 重写路径，并非第二套原生运行时（`AP/backend/docs/API.md:592`）。配置统一的 Base URL 并在系统内统一规范化路径。
- 服务间调用的**每个**请求都必须携带两个 Header：`X-DeerFlow-Internal-Token` 与 `X-DeerFlow-Owner-User-Id`。在 Gateway 与 CNC 后端中配置相同的高强度 `DEER_FLOW_INTERNAL_AUTH_TOKEN`；若未配置，系统会自动生成进程级的随机 Token（`AP/backend/app/gateway/internal_auth.py:14`, `:20`）。严禁查看或在日志中打印真实的凭证值。
- 从已认证的 CNC 用户 ID 中推导稳定的、带命名空间的所有者标识，例如 `cnc_user_<uuid>`。绝不允许从浏览器 Header、模型参数或任意透传的 `context` 中接收所有者或 Token。Gateway 验证平台 Token，不强制要求在 `users` 表中存在对应记录，完全信任业务平台自身的鉴权结果（`AP/backend/docs/API.md:1907`；`AP/backend/docs/AUTH_DESIGN.md:349`）。缺失所有者会降级为 `default`，BFF 必须对常规用户请求拦截该情况。
- 虚拟的内部主体 ID 会由 `make_safe_user_id` 进行安全转换（`AP/backend/app/gateway/internal_auth.py:43`）。推荐直接使用本身即合规的稳定 ID；上线后严禁更改映射规则。若存在对应记录，DeerFlow 会检查相同 ID 的封禁状态（`AP/backend/app/gateway/auth_middleware.py:110`）。CNC 仍需自行负责账号禁用与注销校验。
- 内部认证比普通浏览器请求具备更高的信任权限：可以保留内部上下文以及系统/开发者角色的运行消息。必须从白名单前端字段构建强类型的运行请求；绝不能将其做成无限制的反向代理。参见 `AP/backend/AGENTS.md:197`、`AP/backend/app/gateway/services.py:2161`、`:2205` 及 `:1066`。
- 元数据与客户端提示信息不具备资源鉴权效力。无 DeerFlow `users` 记录的内部调用通常使用配置的默认授权角色。全局 `authorization.enabled` 默认为 false；启用时默认采用安全闭环（Fail-closed）（`AP/backend/packages/harness/deerflow/config/authorization_config.py:21`）。业务工具必须独立强制执行 CNC RBAC、同所有者资源检查以及“仅报价”的安全边界。
- PAT **不适合全功能集成**：PAT 路由白名单无论 Token Scope 如何，都会一律拦截技能、模型、上传、智能体、调度器及其他配置路由（`AP/backend/docs/API.md:139`）。内部角色不属于管理员会话，因此不能将技能安装/编辑/启停作为普通聊天功能对外暴露（`AP/backend/app/gateway/deps.py:1423`；`AP/backend/docs/API.md:1030`）。应通过受控的运维途径部署审查通过的技能包。

### 3. 最小化 HTTP 生命周期与重放契约

| 业务诉求 | 原生 Gateway 契约 / 代码依据 |
| --- | --- |
| 创建 / 恢复会话线程 | `POST /api/threads`，请求体 `{thread_id?, assistant_id?, metadata?}`；显式指定 ID 具备幂等性，跨所有者冲突返回 404。`routers/threads.py:490`, `:950`。 |
| 当前状态 / 初始历史消息 | `GET /api/threads/{thread_id}/state`；状态中包含标准消息列表。`routers/threads.py:1580`。 |
| 提交并建立流式连接 | `POST /api/threads/{thread_id}/runs/stream`；请求模型与创建一致。`routers/thread_runs.py:1000`。 |
| 提交异步运行（不挂接流） | `POST /api/threads/{thread_id}/runs`；随后通过 Join 或 Read 获取结果。`routers/thread_runs.py:982`。 |
| 接入正在活跃的流 | `GET /api/threads/{thread_id}/runs/{run_id}/join` 或使用已有 Run 发起 GET/POST `/stream`；需传递 `Last-Event-ID`。`routers/thread_runs.py:1337`, `:1447`；`API.md:1978`。 |
| 显式停止取消 | `POST /api/threads/{thread_id}/runs/{run_id}/cancel?action=interrupt&wait=false`；202 代表取消请求已受理；需持续轮询直至终态。`wait=true` 可在取消完成后直接返回 204。`routers/thread_runs.py:1276`。 |
| 持久化恢复追溯 | `GET /api/threads/{thread_id}/runs/{run_id}`、GET `/runs/{run_id}/events`、GET `/runs/{run_id}/messages`；线程级接口还包含 `/messages/page`。`routers/thread_runs.py:1264`, `:1834`, `:1645`, `:1617`。 |
| 上传真实文件字节 | `POST /api/threads/{thread_id}/uploads`，multipart 格式传输 `files`；返回文件名、虚拟路径及产物 URL。`API.md:1297`。此处不包含任何 STEP 解析能力。 |

BFF 构造的 Run 请求体示例（包含示例技能名称）：

```json
{
  "assistant_id": "cnc-quote",
  "input": {
    "messages": [{
      "role": "user",
      "content": "对所选零件在数量 1、2、5 下发起报价。",
      "additional_kwargs": {"skill_references": ["cnc-quote-orchestration"]}
    }]
  },
  "context": {"model_name": "<configured-model-name>", "thinking_enabled": false},
  "stream_mode": ["values", "messages-tuple", "custom"],
  "on_disconnect": "continue",
  "multitask_strategy": "reject"
}
```

- 保留响应头中的 `Content-Location: /api/threads/{thread_id}/runs/{run_id}` 与 `X-Trace-Id`，以及 SSE 的 `event`/`data`/`id` 及控制事件。支持的流模式包括 `values`、`messages-tuple`、`custom`、`updates`、`debug`、`tasks`、`checkpoints`；传入不支持的模式（包括 input `messages`）会返回 422（`AP/backend/docs/API.md:330`）。输出的消息事件名称与请求中的 `messages-tuple` 模式名有所区别；应使用真实的协议/SDK 适配器，切勿使用简单的纯文本 Token 模拟。
- `on_disconnect` 默认值为 `cancel`（`AP/backend/app/gateway/run_models.py:53`）；针对后台业务任务应主动指定为 `continue`，并提供独立的停止接口。通过 Join 接入的观察者连接恒定设置 `apply_on_disconnect=False`（`AP/backend/app/gateway/routers/thread_runs.py:1350`）。关闭浏览器 Fetch 连接并不等于取消业务。
- `Idempotency-Key` 绑定单次明确的用户操作意图。在遇到不确定的网络传输故障时可带 Key 重试，但严禁为新操作复用旧 Key。线程维度的创建、流式和等待接口共享该操作标识；若变更了输入内容、助手或引用，则返回 409。无状态运行无法提供等价的按 Key 重试能力（`AP/backend/docs/API.md:257`）。CNC 工具侧的报价提交需要其自身完备的幂等性/意图标识；仅仅是 HTTP 层的智能体准入无法消除底层的业务重复写操作。
- 重放缓冲区存在容量上限（默认 256）。当遇到 `gap` 或 `stream_replay_gap` 时连接关闭且不输出 `end`；此时应重新拉取持久化的 Run/事件/线程状态，随后再尝试重连。重放缺口决不代表任务失败，也不会导致运行被取消（`AP/backend/docs/API.md:1978`）。必须保持 `Cache-Control: no-cache, no-transform` 与 `X-Accel-Buffering: no`，禁用 SSE 压缩与代理层缓冲（`API.md:1963`）。
- 取消操作本质是中断图的执行（Interrupt the graph）；它无法撤回已经向第三方平台提交的报价请求。系统必须清晰界定“智能体已中断”、“已请求业务取消”、“对账确认的终态报价”以及“未知的外部状态”。切勿将回滚宣传为可以撤销外部网站已发生的行为。

### 4. 技能：目录、加载与执行相互分离

1. `GET /api/skills` 与 `GET /api/skills/{name}` 返回经过可见性过滤的**元数据**，并不包含技能的具体正文，亦不负责执行技能（`AP/backend/docs/API.md:965`）。读取自定义技能内容需调用 `GET /api/skills/custom/{name}`；管理类变更必须具备管理员权限。当前路由中不存在通用的 `/skills/{name}/execute` 端点。
2. `describe_skill` 属于元数据发现工具；默认提示词随后会指导智能体对容器内的物理路径调用 `read_file`（`AP/backend/packages/harness/deerflow/skills/describe.py:213`）。这同样不属于技能执行。
3. 显式激活采用 `/skill-name ...` 指令，或在当前 HumanMessage 的 `additional_kwargs.skill_references` 中声明（支持 1 至 16 个技能名称）。批处理会综合用户存储、启用状态、Agent 白名单及 `skill:activate` 权限对所有技能名称进行统一校验；若批次中存在非法项，则整批均不予部分激活（`AP/backend/packages/harness/deerflow/agents/middlewares/skill_activation_middleware.py:317`, `:490`）。
4. 激活逻辑直接从经过校验的**宿主机**技能存储中读取 `SKILL.md`（`.../skill_activation_middleware.py:282`），安全注入转义后的 HumanMessage 上下文，并对 `skill_name`、分类、路径和 SHA-256 哈希进行审计（`:369`, `:519`）。显式激活本身既不需要沙箱环境，也不需要调用 `read_file`。真实的业务动作依然通过调用具体工具完成。`AP/backend/tests/test_inline_skill_references.py:47` 展示了确切的消息体结构。
5. 当前的 `allowed-tools` 纯粹是互操作性元数据；它**不会**自动授权或禁用任何工具。实际的执行权限完全由 Agent 本身的工具选择、鉴权配置和运行时防护栏决定（`AP/backend/packages/harness/deerflow/skills/AGENTS.md:17`, `:21`；`.../config/agents_config.py:215`）。9 月份的源码分析报告中关于 SkillToolPolicy 的描述不得凌驾于当前这一契约之上。
6. 应围绕强类型工具及不透明的文件/账号/Run ID 来组织 CNC 的工作流指导规范。避免在自称无沙箱的技能中硬编码敏感凭据、任意操作系统命令、本机开发机路径或必须依赖沙箱执行的脚本。若需要配套的辅助资源，应设计通用的、受权限管控的技能资源加载器，实施严格的包名/所有者/启用状态/白名单检查并限制内容大小，绝不能暴露通用的宿主机 `read_file` 能力。

### 5. 确切的无沙箱技术差距与通用核心扩展缝隙

用户的诉求是字面意义上的：绝不能用 `LocalSandboxProvider` 来充当所谓的“无沙箱”实现。

- Gateway 自定义 Agent 始终统一采用标准的 Lead 组装流程（`AP/backend/app/gateway/services.py:1146`）。`AgentConfig` 具备记忆/工具/技能策略配置，但并未提供沙箱开关（`.../config/agents_config.py:207`）。
- Lead 共享的基础架构中无条件挂载了 `SandboxMiddleware`（`AP/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py:395`）。只要配置了非空的显式技能白名单，系统就会为线程构建物理的技能投影，甚至在任何模型或工具调用之前就会提前申请 Provider（`AP/backend/packages/harness/deerflow/sandbox/middleware.py:91`, `:231`）。因此，仅仅在工具列表中剔除沙箱工具是远远不够的。
- `RuntimeFeatures(sandbox=False, memory=False)` 仅存在于直接调用 `create_deerflow_agent` 的 SDK Factory 中；HTTP Lead 路径根本没有消费该特性对象（`AP/backend/packages/harness/deerflow/agents/features.py:18`；`.../agents/factory.py:67`）。若为了绕过沙箱而用该 Factory 整体替换 Gateway，会丢失现有的完整 Lead 组装与管理能力，完全没有必要。
- 文件上传接入模块在 `AP/backend/app/gateway/upload_ingestion.py:200` 中无条件尝试获取沙箱 Provider；未挂载的 Provider 可能会在 `:201-216` 发生申请与同步动作。一个真正的无沙箱能力必须同步支持纯宿主机的上传、列表和产物处理。即使是因角色权限被拒绝的上传路径，当前依然会去解析 Provider。
- 建议的**通用且向前兼容的切入点**：引入一套面向运维或自定义 Agent 的运行时能力策略，默认保持现有的完整 Lead 行为不变。在服务端统一解析该策略；若沙箱被禁用，则跳过沙箱中间件、技能投影、实例预热以及 Provider 获取动作，彻底剔除所有依赖沙箱的工具，并生成感知当前能力的受限文件/技能提示词。同时完整保留宿主机侧的显式技能激活、Checkpoint、输入/结果脱敏、权限校验、工具错误/回执/死循环防护以及调用链追踪。绝不允许普通的运行输入动态放宽该策略，亦不可重新激活 Checkpoint 中残留的沙箱状态。
- 将 CNC 的业务逻辑完整保留在扩展中。仅向核心层贡献通用的能力开关策略，以及按需增加安全的技能内容/资源钩子。现有的 `PluginContribution.ModelTool` 足以承载受限的 CNC 工具集；无需在核心层新增专属于 CNC 业务的工具注册表。
- 必备的验收测试：无沙箱 API 运行 + 显式技能激活 + 文件上传 + 工具调用 + 取消/重连全链路正常工作，且在测试中将 Provider 工厂/获取方法打桩为一旦调用即报错；确保无记忆提取/工具/刷盘动作；现有的默认 Lead 回归测试全部通过。补充缺失/禁用/外部技能及非法调用沙箱工具的负向用例。

### 6. 扩展工具、中间件与长耗时任务

- 通过公共的 `PluginContribution(tools=...)` 与 `ModelTool(group="cnc", ...)` 注册工具。它们由自定义 Agent 配置的工具组进行过滤（`AP/backend/packages/extension-api/deerflow_extension_api/plugins.py:54`；`AP/backend/packages/harness/deerflow/extensions/plugin_tools.py:124`）。运行时工具名称由宿主带有命名空间或哈希生成，不等同于声明时的原始名称（`.../plugin_tools.py:58`）。切勿在技能文档中硬编码推测的运行时工具名。
- `ToolContext` 提供经过认证的 `principal.user_id` 与线程 ID；对资源的归属校验依然是插件 Provider 的责任（`AP/backend/packages/extension-api/deerflow_extension_api/plugins.py:35`）。输入 Schema 校验限制单次入参不超过 256 KiB；每个 Handler 具备固定的 30 秒超时阈值，且返回结果严格限制在 64 KiB 以内（`AP/backend/packages/harness/deerflow/extensions/plugin_tools.py:78`）。应采用精简的提交/状态/取消/结果响应结构，并通过凭据 URL 或 ID 传递存证，严禁在一个工具调用中执行完整的浏览器自动化操作或直接回传 Base64 截图大图。
- 公共工具上下文中没有显式暴露运行时的 Run ID 或 Tool Call ID。需使用 CNC 自行签发的持久化操作/意图 ID 以及幂等协议。若后续需要严格的宿主 Run/工具链路追溯，应在公共上下文中新增通用的标准字段；切勿直接导入宿主私有运行时或轻信大模型自作主张传入的 Run ID。
- 所有者过滤范例：`AP/examples/deerflow-extension-bookmarks/deerflow_extension_bookmarks/__init__.py:49` 始终基于所有者进行数据库操作；`:130` 将 Handler 与 `context.principal.user_id` 绑定；`:139` 注册公共工具。
- 扩展中间件的作用域可限定为 LEAD，并可检查 Agent 名称与模型（`AP/backend/packages/extension-api/deerflow_extension_api/placement.py:43`）。它可以通过语义化挂载补充操作提示词、进度反馈和审计功能。**所有由扩展贡献的中间件均具备故障隔离且默认故障放行（Fail-open）**，包括前置处理阶段的异常（`AP/backend/packages/harness/deerflow/extensions/isolation.py:1`）。绝不能将其作为唯一的所有权、权限或意图拦截屏障；这些安全门禁必须在强类型的 CNC 工具和底层业务 API 中严格实施。核心的关键运行时与认证控制必须保留在 Core 中。
- `AgentRuns` 是可选的完整 Agent 控制能力，对于 CNC 的提交/状态工具并非必要。其持有的句柄刻意对 Internal / Channel / PAT 认证主体禁用（`AP/backend/docs/extension-agent-runs.md:32`）。不要把建议的 BFF 集成建立在一个必须依赖此类能力的 Workflow 扩展之上。引入 Workflow/QuickJS 扩展会平添不必要的 POSIX 环境、进程管理与异常恢复约束。

### 7. 调度器复用与结果语义

- 绑定所有者范围的 `/api/scheduled-tasks` 已经具备完善的 CRUD、暂停、恢复、手动触发、运行历史及 Cron 预览能力。字段包含一次性/Cron/间隔、时区、`assistant_id`、全新或复用线程上下文以及可选的运行上限（`AP/backend/docs/API.md:1643`）。读取需要 `threads:read` 权限；修改需要 `threads:write`；创建/更新/恢复/手动触发还需要 `runs:create`。
- 调度器运行时默认处于关闭状态；`scheduler.enabled` 用于启动轮询器，`scheduler.tool_enabled` 用于独立暴露对话式调度工具（`AP/backend/packages/harness/deerflow/config/scheduler_config.py:6`）。调度服务依赖持久化仓库，并在常规运行时初始化完成后方才装配（`AP/backend/app/gateway/app.py:782`）。如果当前进程的轮询器未启动，创建任务接口会报错（`API.md:1735`）。
- 定时任务触发的运行属于非交互式；无法自动应答登录二次验证、验证码或出口合规声明。必须使用预先记录的、已授权的报价配置与意图，并在前置依赖失效时输出可恢复的阻塞状态。对话式调度工具是由宿主能力单独授予的，单纯在 YAML 中声明其路径并不代表获得了该工具（`AP/backend/packages/harness/deerflow/tools/tools.py:145`, `:182`）。
- 处于繁忙状态的触发实例会进入带超时上限的有界队列，并受单用户/全局并发上限约束；需保持单调度任务的独占所有权。DeerFlow 调度器触发的是提示词执行，并非内置的 CNC 价格监控时序序列。既可以复用它拉起有界的 CNC 提交/巡检工作流，**也可以**完整保留 CNC 原有的持久化监控调度器作为唯一权威。切勿针对同一个监控方案创建两个独立的定时器。结构化的报价快照、历史曲线、成功率与耗时统计必须归 CNC 所有；智能体运行成功绝不能作为浏览器真实报价成功的证据。

### 8. 模型兼容性与旧会话继续对话

- Gateway 模型选择使用配置好的 `AppConfig.models` 命名；`context.model_name` 会对照该目录进行严格校验（`AP/backend/app/gateway/services.py:2110`）。`/api/models` 接口返回的是经角色过滤的元数据，不包含 API 密钥（`AP/backend/app/gateway/routers/models.py:141`）。针对单个 Agent 的覆盖项仅限于有界采样参数及思考/推理开关，并不包含凭证或 Base URL（`.../config/agents_config.py:175`）。
- 受管模型的 CRUD **仅限管理员操作**，统一加密保存在全局的 `managed-models/catalog.enc` 中，并不支持单用户的 BYOK 模式（`AP/backend/app/gateway/routers/managed_models.py:68`, `:114`；`.../config/managed_models.py:150`）。未发现现成的面向普通用户的模型 Provider/凭据 HTTP 接口。在决定是全盘迁移至全局目录还是搭建新的通用凭证桥接之前，必须完整保留 CNC 的个人配置；绝不可静默将其废弃，亦不能在消息或配置元数据中透传密钥。这一影响用户体验的兼容性决策，在前序主会话中已被明确提出。
- 历史上的旧版 Agno 会话可以采用懒加载的方式无缝继续对话，无需修改原始数据行。Gateway 支持外部传入 UUID（不透明 ID 正则匹配 `[A-Za-z0-9_-]{1,64}`，`AP/backend/packages/harness/deerflow/utils/thread_id.py:11`），并支持同所有者下的幂等创建（`routers/threads.py:950`）。
- `POST /api/threads/{id}/state`，请求体为 `{values:{messages:[...],title:...}}`，通过 Checkpoint 变更直接覆盖 Reducer 字段，而不触发模型运行（`AP/backend/app/gateway/routers/threads.py:1629`, `:1689`）。支持标准可见的 Human/AI 消息格式；外部传入的 system/developer 角色会被状态归一化逻辑拒绝。如果当前线程有活动中的运行，则返回 409（`:1710`）。
- 需使用独立的所有者/会话/线程/导入状态台账、稳定的消息 ID 以及幂等迁移屏障。仅对已确认属于自己的空白远程线程进行初始填充；在局部迁移失败或重试后，绝不覆盖已有后续进展的远程会话。导入的状态不会自动追溯生成历史 DeerFlow 运行事件；需保留旧版历史数据来源与前端回退展示逻辑。CNC 标准格式的提取与分页展示细节见前端专项调研。

### 9. 版本、测试与部署约束

- 源码依赖版本：Gateway `2.2.0-dev`，Python `>=3.12`（`AP/backend/pyproject.toml:1`）；harness `2.1.0`，Extension API 严格限定为 `0.2.9`（`AP/backend/packages/harness/pyproject.toml:1`, `:16`）。Lockfile 解析锁定 LangChain 1.3.14、langchain-core 1.4.9、LangGraph 1.2.9、langgraph-sdk 0.4.4、langchain-openai 1.2.1、FastAPI 0.136.1、httpx 0.28.1、Pydantic 2.13.3、SSE-Starlette 3.3.4、pytest 9.0.3、Ruff 0.15.12。这些是本地已锁定的事实，而非建议升级的版本。
- 后端 TDD 原则：每项特性与修复均需具备单元测试覆盖；在修改前后运行离线的 `make test` 与 `make test-blocking-io`，并执行 `make lint`（`AP/backend/AGENTS.md:208`；`AP/backend/Makefile:33`, `:60`）。在 Windows 上使用等价的环境变量与 uv pytest 命令；POSIX 专有测试需进行条件跳过，避免在用例收集阶段报错。在未明确指定前切勿触发依赖外网环境的测试集。
- 重点扩展测试集：`test_inline_skill_references.py`、`test_slash_skills.py`、`test_lead_agent_skills.py`、`test_extension_api_contracts.py`、`test_extension_api_surface.py`、`test_extension_isolation.py`、`test_extension_placement_guarantees.py`、`test_skills_router_authz.py`、`test_gateway_services.py`、`test_threads_router.py`、`test_run_event_stream_contract.py`，以及调度器用例与防阻塞 I/O 对应测试。CNC 侧应补充 MockTransport 契约测试，覆盖所有者隔离、超时/不确定准入、流式控制/重放/取消以及显式技能激活，并基于受控 Fixture 补充真实浏览器测试。
- 扩展包检查工具：在 AP 根目录下执行 `uv run --project backend --no-sync python scripts/check_extension.py <package>`（`AP/scripts/check_extension.py:4`）。通过文档记载的扩展管理器安装受信任的扩展；本地目录会被固化为快照，而非软链接。任何修改都会更新扩展依赖组与 Lockfile；在安装/升级/配置修改后需重启 Gateway，并在受管依赖集发生变更时重新构建镜像（`AP/backend/packages/harness/deerflow/extensions/AGENTS.md:95`, `:138`, `:162`）。
- Core/Harness 模块严禁导入 `app.*`；扩展应使用公共契约，并在必要时显式声明框架导入（`AP/backend/AGENTS.md:176`；`.../extensions/AGENTS.md:171`）。切勿将外部 CNC 业务逻辑或依赖强行塞入 Core 核心包中。
- 最小化部署拓扑：独立的 Gateway、持久化的数据库/配置主目录/技能及存据状态、固定的内部 Token、模型目录配置及 CNC 扩展连接配置；保留 SSE 代理 Header。Nginx 公开入口默认 2026，Gateway 内部端口 8001，前端 3000（`AP/AGENTS.md:18`）。纯内存存储无法满足重启后历史查看与监测验收的要求。仅在选定的多 Worker 流式拓扑需要时才引入 Redis；默认的单进程流在不同 Worker 间可能会返回 409（`API.md:290`，`routers/thread_runs.py:1347`）。初期建议优先采用单 Gateway Worker 模式，或明确设计共享流桥接与归属机制。

## 相关规范

- `.trellis/spec/backend/cnc-auto-quote.md`：持久化意图/Run 归属、仅报价安全边界及真实结果分类规范。
- `.trellis/spec/backend/cnc-account-login.md`：加密秘密/会话状态、账号隐私及登录恢复规范。
- `.trellis/spec/backend/browser-executor.md`：受控浏览器执行器、出口/意图/凭证契约规范。
- `.trellis/spec/guides/cross-layer-thinking-guide.md`：跨层设计指引，保持 HTTP/SSE、运行时、领域服务与前端 UI 契约的高度一致。
- `.trellis/spec/backend/quality-guidelines.md` 与 `error-handling.md` 目前大多为占位符；应严格遵守具体的 CNC 规范与审查过的源码，不凭空自创规范。

## 注意事项与未发现项

- 纯规划分析结论：未修改 agent-platform 或产品代码，未读取任何生产密钥，未拉起常驻服务，未发起任何外部网络请求、账号登录、STEP 上传、调度创建或外部写操作。本报告不作为线上实测验收的凭证。
- “字面意义上的无沙箱执行”确实属于通用核心层缺失的能力缝隙。现有的显式技能激活机制可以直接复用，但单纯依靠配置或工具组过滤，无法使当前的 Lead 组装与上传流程完全免除沙箱依赖。
- 用户提供的 9 月份分析文档在技能工具授权方面已经部分滞后。现存的最新源码与模块说明已经明确将 `allowed-tools` 定义为兼容性元数据。
- 未发现原生的技能执行 REST 端点、单用户 BYOK 模型管理 API，或公共插件 ToolContext 中的 Run/工具调用追溯字段。切勿宣称这些功能已经存在。
- 真实的报价平台访问、凭据配置、MFA/合规声明及价格有效性，必须通过专门的 CNC 业务调研和后续授权的实测验收来确认。智能体的对话文本本身不构成有效的报价依据。
- 面向用户的模型目录与 BYOK 兼容性是早期独立 Gateway 方案中的重大未决决策。当前采用的同项目内适配方案应完整保留现有的个人配置；不需要进行服务端模型目录迁移。

## 外部引用

无需查阅外部公网资料。本文档引用的核心素材均来自本地已校验的 API/模块文档及已安装源码的 Lockfile。后续具体实施应严格基于当前本地检出的 API 体系，切勿混用外部不相关的 DeerFlow 上游新版本。
