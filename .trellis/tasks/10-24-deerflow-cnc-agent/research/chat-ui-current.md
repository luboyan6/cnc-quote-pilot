# 调研：当前 AI 聊天现状及 Vue 对 DeerFlow 的适配分析

- 调研目标：明确当前聊天、历史记录、模型配置、附件、流式/取消契约，并找出在 Vue 中承载 DeerFlow 工具/技能及可追溯 CNC 结果的最小适配方案。
- 调研范围：内部；CNC Quote Pilot 实际代码加上本地 `E:/AIWorkspace/agent-platform` 参考代码/文档。仅规划分析，不修改产品代码。
- 日期：2026-10-24
- 路径约定：无前缀路径均相对于 `E:/AIWorkspace/cnc-quote-pilot`；`AP/` 表示 `E:/AIWorkspace/agent-platform`。

## 最新范围调整

- 主会话在本次调研后转达了用户的进一步明确：**仅运行 CNC 项目**，在本地吸收适配 DeerFlow 的思路与代码，不运行或部署独立的 agent-platform Gateway 服务。保留 CNC 身份认证、Vue 前端和现行有效的个人模型配置。当前要求的交付物为简要设计；暂未授权任何产品代码实施。
- 因此，下文提及的外部 Gateway/BFF、内部 Token 权属映射以及远程历史导入等内容，均属于**早期范围的参考调研结论**，已被选定的单项目本地运行方向所替代。它们绝不能变成实施要求或额外服务。
- 适用的后续设计是在 CNC 的 API 背后实现本地 Lead Agent、必要中间件、工具集与技能，为 Vue/工具/技能进度提供强类型的本地事件适配器，保留现有历史记录与协议兼容，接入真实附件上传并实现可独立取消的执行流程。DeerFlow 的前端交互协议依然极具参考价值，无需引入其 React 应用或可选的记忆/沙箱系统。

## 调研发现

### 1. 发现的文件与适用指南

| 文件 | 用途 / 证据说明 |
| --- | --- |
| `AGENTS.md`, `.trellis/workflow.md` | 任务规划/评审门禁；调研结果归档于本任务下。CNC 后端、Web 前端或 App 端除三方依赖外未发现额外的 AGENTS 文件。 |
| `.trellis/spec/frontend/index.md`, `backend/index.md`, `guides/index.md` | 规范索引。通用的前端类型/状态/组件/质量与后端错误/数据库/质量规范当前为占位符，并非已落地的约定。 |
| `.trellis/spec/frontend/cnc-auto-quote.md` | 真实前端契约：权限、串行轮询、生成栅栏、创建/取消屏障、准确的报价状态、精确金额/工期展示、针对性检查项。 |
| `.trellis/spec/backend/cnc-auto-quote.md` | 真实报价 Run / 隐私 / 文件 / 所有者 / 意图契约；严禁捏造虚假成功报价或盲目重放写操作。 |
| `backend/app/modules/ai/chat/{controller,service,crud,schema}.py` | 实际现存的聊天 API、Agno 执行器、历史记录/Redis 模型存储；**并非** `plugin/module_ai` 包。 |
| `backend/app/utils/ai_factory.py` | Agno Team，包含一个通用的成员 Agent，且 `tools=[]`。 |
| `frontend/web/src/api/module_ai/chat.ts` | 共享的 Web 聊天/历史/模型 REST 客户端及历史遗留类型定义。 |
| `frontend/web/src/views/module_ai/chat/index.vue`, `types.ts`, `components/*.vue` | Vue/Element Plus 聊天视图、侧边栏、输入区、文本消息渲染器、模型配置抽屉。 |
| `frontend/web/src/views/module_ai/memory/index.vue` | 现有的历史记录管理页；这是聊天记录的消费端，不同于为智能体添加长期记忆。 |
| `frontend/app/src/api/module_ai/chat.ts`, `composables/useAiChat.ts`, `subPages/module_ai/chat/index.vue` | Uni-app 移动端第二聊天客户端，共用后端路由。 |
| `docs/ai_agent_langgraph_migration_analysis.md` | 先前的架构提案；包含有价值的历史 Schema 清单，但**不是** LangGraph 迁移已实现的证据。 |
| `AP/AGENTS.md`, `AP/frontend/AGENTS.md`, `AP/frontend/src/AGENTS.md` | 参考前端基于 React/Next；应在 Vue 中重新适配其交互契约，而非照搬其组件框架。 |
| `AP/API.md`, `AP/AUTH_DESIGN.md` | 权威的 HTTP 集成/鉴权参考；MDX 集成指南主要描述内嵌 Python 的 `DeerFlowClient`。Gateway 细节已由同级调研核验。 |
| `AP/frontend/src/core/{threads,skills,uploads,messages,artifacts,api}/` | 供参考适配的传输层逻辑与纯领域/UI 行为实现。 |

### 2. 后端与 API 当前实际行为

- 根路由直接导入 `ChatRouter` 并挂载于 `/ai` 路径下：`backend/app/api/v1/routers.py:5,61`。控制器前缀为 `/chat`（`controller.py:29`）；实际部署路径为 `/api/v1/ai/chat/*`。
- REST 接口：GET `/list`、POST `/create`、GET `/detail/{session_id}`、PUT `/update/{session_id}`、DELETE `/delete`；现有权限标识为 `module_ai:chat:query/create/detail/update/delete`（`controller.py:44-98`）。POST `/ai-chat` 接收 `{message,session_id?}` 并以标准 CNC 响应外壳返回 `{response,session_id,function_calls,action}`（`controller.py:101-123`, `schema.py:68-89`）。
- WebSocket 接收 JSON `{message,session_id?,files?,action?}`（`schema.py:8-14`）。它输出**纯文本**数据块以及哨兵字符串 `[DONE]` / `[STOPPED]`，并不包含结构化的工具或状态事件（`controller.py:251-291`）。
- 握手鉴权验证当前 CNC 用户及 `module_ai:chat:query` 权限；Web 端使用 `Sec-WebSocket-Protocol: access_token,access_token.<jwt>`，Uni-app 使用受支持的 Query Token 兜底（`controller.py:194-222`；`backend/app/core/dependencies.py:55-87`）。应避免将 Query Token 扩散到新服务中。
- `ChatService.chat_query` 创建 Agno Agent，仅流式返回 `chunk.content` 且完全忽略了 `query.files`；执行错误会被转换为形似助手回复的文本（`service.py:157-205`）。非流式路径同样调用 Agno 且恒定返回 `function_calls=None`（`service.py:209-247`）。现存的 action 解析产出的是页面跳转或 JSON 建议，而非可调用的 CNC 业务工具（`service.py:249-274`）。
- 工厂类使用 `agno==2.5.8`（`backend/pyproject.toml:8`）、`OpenAILike`、包含一个 `tools=[]` 的通用成员、共享 Team ID 以及保留 3 轮历史（`ai_factory.py:14-20,57-89`）。当前聊天链路中不存在任何技能（Skills）运行时或 API。

**基于源码证实的取消缺陷：** 控制器中的同一个协程先调用 `receive_text()`，然后在返回继续接收前消费完整的模型流（`controller.py:236-291`）。因此，在生成过程中发送的停止指令帧，必须等待流完全结束才能设置 `stop_event`。现存的 Event 检查无法做到并发接收停止指令。迁移文档中关于“已实现即时取消”的断言（`docs/ai_agent_langgraph_migration_analysis.md:104`）与实际代码不符。本地 DeerFlow 风格的适配层必须将接收控制命令与正在运行的生成任务解耦（或提供独立的鉴权取消接口），并进行并发停止测试。

### 3. 历史记录与数据库契约保留

- `ChatSessionCRUD` 使用 Agno 自带的异步 SQLAlchemy 适配器作为单例：MySQL/Postgres/SQLite 均受支持（`crud.py:29-49`）；类型为 TEAM（`crud.py:82`），Team ID 为 `default`（`crud.py:21-22`），所有者为**用户名**（`crud.py:90-102`），会话 ID 为 UUID（`crud.py:163-174`）。已安装的 Agno 代码 `backend/.venv/Lib/site-packages/agno/db/base.py:57` 默认表名为 `agno_sessions`。
- 历史数据包含 `session_data.session_name`、`runs[*].messages`、总结摘要以及 Unix 秒级时间戳。服务对 JSON 字符串格式的 runs/session_data 进行反序列化归一化，仅提取用户和助手的消息，同时透出原始字段以及兼容字段 `id,title,created_time,updated_time,message_count,messages`（`service.py:43-140`）。`ChatSessionOutSchema(extra="allow")` 保留了原始的 Agno 字段（`schema.py:46-59`）。
- 列表接口中的 `message_count` 目前统计的是轮次数（Runs），而详情接口统计的是提取出的消息数（`service.py:129`）；不能盲目假设两处计数相等。提取逻辑并未对跨轮次的重复消息 ID 进行去重（`service.py:73-91`）。
- 现有的 Web 侧边栏依赖 `session_id`、`session_data.session_name`、Unix 秒，并映射至 `id`（`FaSidebar.vue:291-324`）。Web 聊天视图忽略规整后的 `messages`，直接遍历原始的 `runs`（`chat/index.vue:302-312`）；记忆/历史页则渲染规整后的 `messages`（`memory/index.vue:98-117,424-430`）。如果数据结构发生变动，必须两端兼顾。
- 先前的迁移分析文档提议将 Checkpoint 写入 `session_data.langgraph_state` 并将新引擎运行记录写回 `agno_sessions`（`docs/...migration_analysis.md:264-283,370`），并声称对前端零影响（`:781-782`）。这仅仅是**提案**，不适合直接作为 DeerFlow HTTP 设计，更不是修改历史数据的用户授权。

**针对评审设计的稳健本地建议：** 保持现存 Agno 数据库记录可读且不因迁移被篡改；保留列表/详情/历史视图投影。在首次继续旧会话时，将可见的历史用户/助手前缀规整为本地标准的 Lead Agent 状态，保留并去重稳定 ID，不回放旧工具、系统提示词、凭据或虚构的凭据。在现有 CNC 边界执行权限归属校验。无需进行后台批量数据迁移或重写历史运行记录；评审通过的设计必须明确定义后续本地引擎的运行状态保存在何处，以及其历史投影如何保持向前兼容。

**已被取代的远程部署参考：** 同级 API 调研确认了 Gateway 的能力支持：POST `/api/threads` 接收 `thread_id`（`AP/backend/app/gateway/routers/threads.py:490-495`）并返回同所有者的既有线程（`:950-978`）；跨所有者冲突则返回 404（`:995-1008`）。UUID 字符串满足线程 ID 规范（`AP/backend/packages/harness/deerflow/utils/thread_id.py:11-30`）。POST `/api/threads/{id}/state` 可导入 `{values:{messages:[...],title:...}}` 而不启动大模型运行，但会**覆盖** Reducer 字段（`threads.py:1629-1637,1689-1711`）且拒绝处于活动中的运行。若后续重新考虑该方案，必须使用独立的所有者/导入台账，仅向已确认为空的线程写入，对不确定写入进行对账，绝不覆盖已有进展的线程，且旧版前缀仅展示一次。这在用户当前的纯本地单项目方向下并非必需。

### 4. Web UI 行为、可复用部分及相关缺陷

- 保留 Vue3/Element Plus 的分栏骨架、侧边栏 CRUD/搜索/日期分组、Markdown/复制/折叠渲染器、欢迎页状态以及现行鉴权权限约定。`index.vue:1-51` 已实现了侧边栏、消息区与输入区的解耦。`FaMarkdownRenderer` 使用 MarkdownIt 并默认启用了 DOMPurify 和安全的外链新窗口属性（`components/display/fa-markdown-renderer/index.vue:40-58,77-96`）。
- 当前 WebSocket 状态维护在页面组件内部而非独立的传输 Composable；它简单地将每个收到的数据块追加到最后一个加载中的助手消息上（`chat/index.vue:85-185`）。`types.ts:2-19` 中没有 Run ID、Tool Call ID、产物/状态联合类型、人工输入请求或经过校验的技能使用标识。
- 当前附件组件仅为一个限制 10 MiB 的本地 File 列表，`auto-upload=false`，且允许的扩展名中不包含 STEP/STP（`FaChatInput.vue:79-85,210-239`）。发送时仅序列化了 `{name,type,size}`（`chat/index.vue:240-247`）。必须建立真实的上传与引用绑定；仅仅在 `accept` 中追加 `.step` 无法满足上传验收要求。
- 输入组件在触发 `emit("send")` 后立即清空了文本与文件（`FaChatInput.vue:249-256`），而此时新会话尚未创建，网络请求也未确认成功。应改造为在实际分发或上传确认成功后再清空，在可恢复的失败场景下必须保留用户草稿。
- 当前的会话切换、新开聊天、清空聊天等操作未对迟到的历史响应或正在活跃的流式回调进行拦截防护（`chat/index.vue:292-334`），且加载已有的助手消息会走 `addMessage` 导致误设 `loading=true`（`:187-196,305-310`）。新的传输层/Store 必须将每个异步更新限定在特定的所有者/会话/运行范围内，并将已持久化的历史数据标记为已就绪。
- 网络断开时虽然会重置助手的 loading，但未将 `sending` 置为 `false`（`index.vue:114-145,199-206`），导致断网后发送按钮可能永久卡死。KeepAlive 清理逻辑完备应予以保留（`:344-353`）。新的传输层必须将“观测断开”与“取消持久化业务执行”彻底分离。
- “清空聊天”当前仅仅清空了本地数组，却弹出了“不可逆操作”的警告（`:326-334`）。设计必须说明这究竟保留为视图级重置还是改为真正的远端删除/重置；切勿在未说明的情况下暗中修改行为。

### 5. 需在 Vue 中适配的 DeerFlow 前端契约

| 关注领域 | 参考实现依据 | 适配实施建议 |
| --- | --- | --- |
| 线程/运行身份标识 | `AP/frontend/src/core/threads/hooks.ts:1967-1969,2166-2181`；默认助手 `lead_agent`、`useStream`、已创建线程/运行的元数据 | 独立追踪线程（Thread）与运行（Run）。构建框架中立的 TypeScript 适配器/Composable；React 的 `useStream` 无法直接粘贴进 Vue。 |
| 消息提交结构 | `hooks.ts:234-268,2791-2816` | 人类消息格式为 `{type:"human",id,content:[{type:"text",text}],additional_kwargs}`；上下文单独存放。保留标准 ID 用于乐观更新与服务端对账。 |
| 流式传输模式 | `AP/frontend/src/core/api/stream-mode.ts:1-15,83-111`；`AP/frontend/src/AGENTS.md:196-208` | 使用 `messages-tuple`、`updates`、`custom`。支持的模式还包括 values/debug/tasks/checkpoints；`messages` 与 `events` 是不受支持的。`streamResumable` 是 SDK 内部记录，发往 HTTP 前会被移除。 |
| 实时与历史组装 | `AP/frontend/src/core/threads/types.ts:67-75,104-113`；`hooks.ts:660-700`；`AP/frontend/src/AGENTS.md:44` | 保留消息类型、文本块、ID、工具调用与结果、additional_kwargs、产物；将分页的持久化消息（`seq/run_id`）与实时增量流平滑合并，不将所有内容压平为一个文本气泡，也不盲信压缩后的 Checkpoint 作为完整历史。 |
| 运行状态管理 | `AP/frontend/src/core/threads/stream-state.ts`；`types.ts:67-75` | State 包含 title/messages/artifacts/todos/tool_artifacts；渲染轻量级的任务/进度/凭证面板。Lead Agent MVP 阶段无需记忆、子智能体、目标规划及沙箱 UI。 |
| 工具执行步骤 | `AP/frontend/src/core/messages/utils.ts:17-57,1055-1119`；`components/workspace/messages/message-group.tsx:1219-1310` | 将 AI 消息中的 `tool_calls[].id` 与 ToolMessage 的 `tool_call_id` 进行关联；展示名称、执行中/成功/错误状态及有界详情。发起调用的 AI 文本应保持可见。严禁将空结果或缺失结果臆测为成功。 |
| 交互澄清确认 | `AP/frontend/src/AGENTS.md:160`；`core/messages/utils.ts:1068-1088` | `ask_clarification` ToolMessage 的 `artifact.human_input` 携带表单/选项/自由文本。渲染交互卡片或安全的纯文本兜底；作为普通人类消息回复，并携带服务端约定的响应元数据。默认情况下这并非 LangGraph 的中断恢复式 UI。 |
| 文件真实上传 | `AP/frontend/src/core/uploads/api.ts:126-159,165-176`；`threads/hooks.ts:2720-2790` | 在运行分发前通过 multipart 上传二进制字节，在 `additional_kwargs.files` 中使用服务端确认返回的文件元数据与虚拟路径，拒绝 `success:false`，上传失败时保留草稿。CNC STEP 文件的授权/哈希/冻结文件契约保持为独立的业务边界。 |
| 停止与重连机制 | `AP/frontend/src/core/api/api-client.ts:44-75`；`threads/hooks.ts:2346-2365,2434-2443`；`AP/frontend/src/AGENTS.md:196-208` | 优先读取终态；不再尝试重新接入成功/错误/超时/已中断的运行。显式取消后端运行；停止后将持久化状态作废并重新拉取。重连 GET 请求可带 `Last-Event-ID` 重试；绝不盲目重试初始创建运行的 POST 请求。出现重放缺口（Gap）时重新加载持久化状态，而非假定成功。 |
| 凭据与存证展现 | `AP/frontend/src/core/threads/types.ts:54-75`；`core/artifacts/utils.ts:72-98` | 使用与线程/运行绑定的产物引用以及鉴权的 BFF 下载端点；保留强类型的 CNC 结果/状态/凭据 ID。助手在 Markdown 文本中口头宣称的报价或截图不能作为真实结果记录的证明。 |

参考前端中的浏览器 REST fetch 使用 Cookie 凭据与 CSRF 保护（`AP/frontend/src/core/api/fetcher.ts:49-103`）；而 CNC 使用 Bearer Token 鉴权以及通过 Axios 封装的 `ApiResponse`（`frontend/web/src/utils/http/index.ts:245-249,292-318`）。原始的 DeerFlow 响应无法原样通过现有的 Axios 成功状态码拦截器。应使用经过 CNC BFF 规整的 REST 包装以及专用的鉴权流式通道，在准入前刷新 Token；认证或传输错误后切勿重放带有不确定副作用的运行变更。

同级 API 调研确认：Gateway 原生路由为 `/api/threads...`；`/api/langgraph/*` 仅为 Nginx 重写路径（`AP/API.md:592`）。CNC BFF 应从已认证的 CNC 用户 ID 推导稳定的所有者身份，并在服务端注入 `X-DeerFlow-Internal-Token` 与 `X-DeerFlow-Owner-User-Id`（`AP/API.md:1907-1922`, `AUTH_DESIGN.md:312-373`）；切勿将浏览器传入的这两个 Header 直接转发。PAT 鉴权因排除了技能、模型和上传等接口，无法支持全功能集成（`API.md:139-155`）。针对持久化业务任务应显式指定 `on_disconnect=continue`；默认行为为取消，而观察者接入不会触发取消（`AP/backend/app/gateway/routers/run_models.py:53`）。在审查显式停止/取消的前端交互时必须清晰界定该差异。

### 6. 技能：发现、请求与实际调用凭证

- 参考接口 GET `/api/skills` 返回元数据（`name,description,category,license,enabled,editable`）：`AP/frontend/src/core/skills/{type.ts:1-8,api.ts:151-158}`。PUT `/api/skills/{name}` 修改启用状态（`api.ts:161-179`）；安装/导入/重新加载为管理类写操作，普通调用端 MVP 无需这些。API 调研已证实 GET 详情既不暴露 `SKILL.md` 内容，也不执行技能。
- 参考前端输入区使用 **@ 呼出技能选择器**，并在 `HumanMessage.additional_kwargs.skill_references` 中提交去重后的技能名称列表（`AP/frontend/src/components/workspace/input-box.tsx:1487-1526`）。旧版的 `/skill-name task` 形式仍受支持；保留的 `/goal` 和 `/compact` 属于控制指令（`core/skills/slash.ts:1-76`）。不要受限于旧版的斜杠指令交互。在向用户展示并允许发送前，必须先解析已启用且 Agent 允许调用的技能目录（`input-box.tsx:894-910`）。
- 技能在目录中存在或被用户选中，仅代表技能被**请求**，并不代表已被**使用**。运行经过验证的依据是服务端返回的 `additional_kwargs.skill_usage`，或终态 AI 汇总的 `skill_usages`，包含路径、内容、哈希、激活状态与局部调用标记（`AP/frontend/src/core/skills/usage.ts:6-43,88-119`；`AP/docs/skill-usage-ui.md:3-31`）。读取失败或模型口头宣称均不算数。这些 kwargs 应完整穿透 BFF 并写入历史，不得由浏览器前端自行伪造。
- 验收必须完整涵盖列表展示/发现、显式引用准入、Lead Agent 真实的加载与使用、工具实际执行以及页面刷新后依然存在的服务端使用凭证。单靠一个 Mock 的 GET 列表无法证明“技能接口调用成功”。技能文本本身不具备授予凭证、文件上传、浏览器操作或报价的权限。

### 7. 保留有效的个人 AI 模型配置

- 当前用户可以创建/更新/删除/激活私有的 `{name,base_url,api_key,model_id,temperature}` 记录（`controller.py:126-178`）。Redis Key 绑定用户 ID，TTL 为 7 天，受分布式读-改-写锁保护（`service.py:332-355,405-411,424-442`）。密钥在静态存储时进行加密，在执行模型调用**以及列表响应输出**时进行解密（`:358-386,414-416,506-510`）。配置抽屉支持显示/复制/编辑 Key，输入框支持切换当前生效配置（`FaAiModelConfigPanel.vue:215-222,305-312,389`；`FaChatInput.vue:156-205`）。切勿将 Redis 中的加密误判为向浏览器返回了脱敏数据。
- 运行调用采用当前用户已激活的配置，或回退至全局 `OPENAI_*` 环境变量（`controller.py:108-114,266-272`；`ai_factory.py:43-54`）。新的 Web/API 行为绝不能在 DeerFlow 忽略该配置的情况下，静默造成“界面选了但实际未生效”的假象。
- 本地 DeerFlow 仅接收运行时 `context.model_name` 并匹配配置好的目录。同级调研未发现公共的个人 BYOK API：模型存储由部署统一管理，管理类 CRUD 仅限管理员（`AP/backend/packages/harness/deerflow/config/managed_models.py:150-153`；`AP/backend/app/gateway/routers/managed_models.py:68-117`）。在运行上下文直接传递明文 `api_key/base_url` 并不是已有能力。
- 最新的指导意见明确了方向：保留现有的个人模型设置，通过本地模型适配器将选定的 Provider/Base URL/Model/Temperature/Key 转换为本地 Lead Agent 所需的实例。无需引入远程凭据桥接或管理员目录重构。**不得替换/废除个人配置，不得将密钥复制到全局目录，也不得仅在 UI 上做表面切换。** 绝不能在对话/工具/凭据载荷中泄露模型密钥。上述关于远程目录的兼容性问题，充分说明了为何全盘替换 Gateway 会破坏既有行为。

### 8. 第二客户端兼容性：Uni-app

- App API 当前将会话/配置 ID 声明为数字类型，尽管后端使用的是 UUID/Hex 字符串（`frontend/app/src/api/module_ai/chat.ts:18-27,58-91`）。非流式 POST 发送的是 `content`，而后端要求的是 `message`（`:29-32` 对照后端 `schema.py:71`）；目前页面主要使用 WebSocket。
- 页面期望的列表数据结构为 `res.list`，而 Web 端与后端使用的是 `items`（`frontend/app/src/subPages/module_ai/chat/index.vue:59-64`）；历史记录渲染使用的是标准化后的 `messages`（`:86-97`）。应对当前的共享 HTTP 解包逻辑进行评估，而不能直接假定两种格式都合法。
- `useAiChat` 仅接收文本和哨兵字符，停止时发送 `{action:"stop"}`，Query Token 是当前的备用传输方式（`composables/useAiChat.ts:14-32,53-61,97-105`）。页面在 `await send()` 后立即清除了流式状态，而实际上 send 仅完成了 WS 帧的分发（`subPages/.../chat/index.vue:162-178`；composable `:79-95`）。在修改共享的 WebSocket 协议时必须关注该回归风险。
- 稳健方案：在新的后端中为 App 保持旧版纯文本 WebSocket 投影以确保兼容，同时 Web 端采用结构化事件传输。否则就必须在同一交付中同步更新 App 的传输层、类型和页面代码。如果直接在 `/ws` 上输出结构化事件，会导致 App 界面把 JSON 原样打印在回复中。切勿在仅修改 Web 的情况下声称完整保留了 App 的兼容性。

### 9. 建议的审查/验收矩阵与执行命令

在本次纯规划分析期间未执行任何测试或构建。在 `backend/tests` 或 `frontend/web/src/__tests__` 中未发现现存的专用聊天测试；为本次协议与集成改造补充覆盖极有必要。既有的 CNC 浏览器/报价测试集针对的是复用的既有行为，不能作为平台线上对接成功的证明。

| 验收场景 | 必须证明的事实 |
| --- | --- |
| 基础聊天 / 新建会话 | 经过认证的 CNC 用户 → 本地 CNC Lead Agent → 标准化事件输出 → Vue 端增量渲染；最终的 Run ID 和页面刷新后均只展示一份消息。 |
| 旧版列表/详情/继续对话 | 迁移前固化的 Agno 测试夹具仍能不经修改正常列出与渲染；仅由所有者触发一次继续对话的归一化，并发请求能够正确协调，状态初始化重试绝不覆盖已推进的本地状态。 |
| 模型配置生效 | 当前激活的个人配置能够真实配置本地模型适配器；公共的 Run 载荷与日志中绝无密钥泄露。 |
| 技能与工具执行 | 已启用目录/Agent 范围、显式选择、运行完成与刷新后具有真实的服务端技能使用哈希；工具调用与结果完整关联，执行错误明确展示。 |
| 附件处理 | 分发前必须确认真实的 STEP 字节与引用；上传失败保留草稿；返回的文件 ID/哈希/授权能够正确绑定 CNC 零件与配置。 |
| 停止与断网重连 | 后端正在生成或运行工具时，取消指令能够生效；用户主动停止与观察者网络断开严格区分；只读重连不会触发多余的报价/上传/运行。 |
| 线程与账号切换 | 从 A 切换到 B 时，迟到的历史/流/上传回调不能污染 B；退出登录取消读取并防止旧所有者的数据回显。 |
| 凭据与结果展示 | 价格、币种、范围均为规范的十进制字符串，保留原始工期文本；QUOTED / 参考估算 / 待审核 / 失败分类清晰；持久化的凭证仅所有者可下载；执行耗时与成功率历史真实源自记录。 |
| 其他客户端表现 | 现存的 Uni-app 文本哨兵输出保持可读，或同步更新并测试该客户端。 |

前端 `frontend/web` 执行命令：`pnpm test -- src/__tests__/<new-chat-protocol>.spec.ts`、受影响的 CNC 测试集、`pnpm run type-check`、`pnpm exec eslint <changed-files>`、`pnpm exec prettier --check <changed-files>`、`pnpm exec stylelint <changed-vue-files>`、`pnpm run build`。现有脚本见 `package.json:12,24-30`；全局 Lint 默认带有 `--fix`，因此针对性检查可避免触碰无关文件。测试环境使用 jsdom/Vue 及 `src/**/*.{test,spec}.{ts,js}`（`vitest.config.ts:29-32`）。

后端 `backend` 执行命令：`.venv/Scripts/python.exe -m pytest tests/<new-chat-suite> -q`、相应的 `tests/cnc/quote`、`tests/cnc/login`、`tests/cnc/browser` 回归测试、`.venv/Scripts/ruff.exe check --no-fix app/modules/ai/chat <new-adapter-files>`、局部 `.venv/Scripts/basedpyright.exe <changed-files>`。后端 Ruff 配置默认启用了 `fix=true`，因此仅检查时必须加上 `--no-fix`（`pyproject.toml:91-96`）；pytest 采用 asyncio auto 模式（`:162-164`）。针对新路由验证生成的 OpenAPI 规范与真实 HTTP 行为，以及权限校验与响应外壳包装。

若涉及移动端修改：`frontend/app` → `pnpm run type-check`、变更文件 ESLint、`pnpm run build:h5`，并在支持的 App 目标平台上进行真实/Mock 的 WebSocket 冒烟测试（`package.json:31-50`）。若后续出于某种原因修改了 agent-platform 前端代码：在其目录下运行 `pnpm check`、定向 `pnpm rstest run <pattern>` 以及受影响的 Playwright 用例（`AP/frontend/AGENTS.md:25-43`）。

## 注意事项与未发现项

- 本报告仅作为实施规划证据。未对真实的 DeerFlow 服务、UI 浏览器渲染、模型凭证、真实账号、远程平台报价或附件上传进行实操调用。
- 同级调研得出的外部 API 契约，在最新的纯本地运行范围下仅作为背景参考；实现该方向绝不需要增加 Gateway、内部 Token 桥接或远程模型管理服务。
- “不引入记忆/沙箱”指排除可选的长期记忆与沙箱子系统；不能丢弃可追溯性和重连所需的持久化会话、运行、结果和存据状态。现有的历史管理应在不引入智能体记忆的前提下保持正常工作。
- 当前 Web 端的纯文本传输、未生效的元数据附件以及串行阻塞的停止接收器，证明了在不改动前端的前提下无法实现用户所需的工具/技能界面。
- 该特性由多个交付成果组成：仅完成聊天集成并不等同于交付了平台登录、自动化适配、批量调度或报表持久化。必须复用独立调研过的 CNC 领域服务，并维护报价真实性、权限隔离与写操作意图契约。
- 调研人员仅将 `E:/AIWorkspace/agent-platform` 作为代码参考，且仅编写了本调研文件。最新范围要求不在该仓库运行任何服务，亦不修改该仓库代码。
