# Agent 源码融合共享契约（2026-10-29，待实施）

本文件是四个子任务的现行技术边界，依据 [用户决定与源码映射](source-integration-replan-2026-10-29.md)。
原 Client-only 契约被取代。以下内部服务、事件和配置是实施目标，不代表已有接口或已验收能力。

## 1. 工程职责与依赖

- Lead：将必要源码适配到 `app/modules/ai/agent/`，包含图、提示词、状态、技能目录/激活、中间件、模型构建、checkpoint 及异步执行服务；不导入运行时 deerflow 包。
- 聊天：扩展现有 `ai/chat/` 的 Controller/Service/CRUD/Schema/Model，做会话归属、旧历史/可见投影、WS/REST、附件引用；`ai/skills/` 暴露目录/详情。
- 业务工具：放在 `ai/agent/tools/`，直接调用 `app/modules/cnc/` 对应 Service；不调用本机 HTTP/MCP，也不复制 CRUD/浏览器自动化。
- 路由：统一 `app/api/v1/routers.py:DOMAIN_CONTROLLERS`，避免旧 plugin 发现与显式挂载双注册。
- 资源：现有 FastAPI lifespan/AsyncExitStack 管理 AgentService、模型 HTTP 资源与异步 saver；使用当前设置、logger、AuthSchema 和数据库资源入口。
- 依赖：仅锁所选 LangChain/LangGraph/model/saver/解析组件及必要闭包；不安装完整 harness、extension-api、Gateway/沙箱/搜索依赖。保留来源提交/哈希/MIT 声明，禁止只换包名整目录搬运。

## 2. 本地执行、模型与身份

拟定内部调用为 ChatService → AgentService.stream(可信身份、已授权会话、消息、技能标识、私密模型快照) → 编译图原生异步流。
该入口不是新 HTTP 协议。AgentService 持有本轮 Task 和资源清理职责；Graph builder 只接显式依赖并返回框架编译图，不实现模型/工具的手写循环。

身份从 `AuthSchema.user.id` 构造；会话/线程关联由服务端验证。客户端、模型参数和技能文本不得覆盖 actor、权限、执行器或 checkpoint namespace。
个人模型沿现有 Redis/解密读取 model_id/base_url/api_key/temperature，每轮独立构建，不修改全局环境/YAML，不回退其他模型掩盖失败。
模型密钥/地址等私密配置只用于构造模型客户端，不放入图状态、RunnableConfig、可见历史、事件或普通日志。
每次领域工具再次验证当前权限、对象/账号有效性和来源文件；不能只依靠握手时的权限快照。

拟新增设置 `AI_CHAT_ENGINE=agno|deerflow_source`，默认 agno，启用前验证依赖/资源/数据库能力。缺依赖或不支持的 saver 明确失败，不能静默切执行器。
沿用项目现有模型默认值语义；已选择个人模型时不静默替换。新设置由现有 settings 统一管理，具体资源限额同步 schema/示例/测试。

## 3. 事件与停止

保留现有 /ai/chat 路由和 REST/WS 握手、权限、响应外壳。无 protocol_version 的 WS 仍输出文本及 [DONE]/[STOPPED]；新 Web 显式 protocol_version=2。
项目定义一次共享判别类型：`turn.started`、`text.delta`、`skill.activated`、`tool.started`、`tool.completed`、`tool.failed`、`domain.progress`、`evidence.available`、`turn.completed`、`turn.stopped`、`turn.failed`。
事件包含 session_id、turn_id、单轮递增 seq；业务 quote_run_id/batch_id/schedule_id/evidence_id 独立引用，监测沿用当前领域 schedule_id 命名。turn_id 为本地传输关联，不是持久 AgentRun 或业务幂等凭据。
映射/seq 由 `ai/agent/events.py` 的单轮发布边界统一负责；WS 单一发送器只投影传输，前端不自行从自然语言提取工具状态。
同一轮只允许一个 completed/stopped/failed 终态。payload 只含白名单安全字段，不发送原始工具参数/异常、凭据、用户名、路径、DOM、秘密 URL 或推理内容。
LangGraph 的消息增量与状态/工具更新分别处理，不能用全量快照再次输出旧文本。

接收停止、执行图流与发送并发运行；队列有界。连接/session/轮次 generation 栅栏丢弃晚到回调，切会话后不能被旧轮覆盖。
stop 进入后 1 秒内确认并收敛本地生成是保留的受控验收目标：必须 await 图/model async stream 的关闭，证明 Task 结束和 HTTP 流释放，不能仅更改 UI 标记。
middleware 不吞 CancelledError，禁止将同步推理包装进 to_thread 当作可取消实现。超时/断线/shutdown 走同一清理出口；不承诺取消远端服务计费或服务商内部推理。
聊天停止/关闭只停止生成与观察，已完成事务准入的领域任务继续。业务取消通过独立受权命令，保留当前行级自动报价弹窗的独立行为。
停止与准入并发时用稳定领域请求键查询实际结果；不得因任务取消/丢回执重复提交。重连只读历史/领域状态，不自动重放中断工具或做 token 级重放。

## 4. 技能与工具

技能解析、显式激活、活跃上下文与允许工具集合来自经过适配的上游代码；不只写一个 create_agent 包装就称作 DeerFlow 融合。
产品只读资源根为 `ai/agent/resources/skills/`，稳定技能名及引用路径由服务端目录解析。不得扫描开发助手 .agents/.codex、接受任意技能 URL/上传目录或执行脚本。
技能目录/详情、选择和实际加载共用注入的 SkillCatalog，发布允许范围与当前权限/真实交付能力取交集。后端提供受限的技能正文/引用读取，不暴露通用文件工具。
只读 CNC 查询/报价状态先交付；QUOTE、batch、monitor 等写工具由对应子任务完成并通过门禁后发布。技能提示词不能赋予业务权限。
`ai/skills/` 路由用现有认证/项目响应与 schema 返回目录及详情，不提供通用 skills/execute。
工具只接业务 ID、受限参数与服务端授予的请求键；模型不收密码、Cookie、验证码或浏览器 Page。人工恢复沿现有账号/报价界面。

## 5. 会话、checkpoint 与历史

新图推理状态使用所选 LangGraph async checkpointer；首期采用 full 格式，不引入上游 delta/长期记忆。
Lead 管 saver 协议/连接资源与本地图状态；聊天管最小应用会话元数据/数字所有者/legacy 关联和可见 Human/Assistant 投影，数据查询沿项目 CRUD/Repository。
可见投影仅服务历史/UI/回滚，不能成为并行推理历史。以来源消息/checkpoint 标识幂等更新，缺投影可从 checkpoint 修复，不重复每轮注入。
用户于 2026-10-30 明确无需迁移旧 Agno 聊天；保留原记录，由旧执行器读取，不猜测或建立历史用户名到数字用户的映射，不重放旧工具。
列表/排序/分页/重命名/删除采用一致来源与删除屏障。显式回滚 Agno 仍须可读新可见消息，并验证切换不重放工具。
同一会话同时只允许运行一轮，冲突明确拒绝；跨连接也不能并发覆盖 checkpoint。首期沿当前单 worker 拓扑验证，未支持的多 worker 源码执行拓扑要在启用时拒绝。
首期验证当前 PostgreSQL；SQLite 用于适配测试。MySQL 新执行器不宣称兼容，旧 Agno 支持保留。不能为新 Agent 静默切库。
应用表接实际 Alembic head；checkpoint 自有表由显式部署步骤管理并受反射保护。历史 `a7d30f26b8e1` 及后续链/退役数据不清理。

## 6. 领域副作用、文件与凭证

引用现有 Quote Run/Intent、冻结快照、请求键、当前权限及账号 fenced lease；不用 tool_call_id 作为业务幂等键，不新建通用 AgentRun/ToolOperation。
先准入持久意图再执行一次 mutation。重复工具、新会话或新 turn 不能绕过未结清范围屏障；收到不明回执仅只读对账。
准入事务与生成 Task 解耦；已准入任务归现有 QuoteService/Dispatcher。未完成准入时不能发业务成功，停止后不得继续自动发起新的写操作。
STEP 复用 CNC 原始上传字节/hash/part/config 引用和所有者校验；第三方传输须保留原有显式授权，不由聊天附件默认开启。
金额/差额/变化率保留 Decimal 字符串，税运费/工期未知项不补零；QUOTED、REFERENCE_ESTIMATE、PENDING_REVIEW 分开。
私有凭证使用现有结果/证据服务与授权读取，引用 actor/Run/文件/参数代次；当前缺口在领域任务补齐，不重建上游 artifacts 系统。

## 7. 批量、监测与结果复用

以 `10-21-cnc-mvp-04-monitoring` 及其 10-28 子任务的当前契约/源码为领域权威，本文件不另定队列、状态、调度或统计公式。
复用 BatchService、QuoteDispatcher、RecoveryScanner、MonitorService、CncQuoteResultService；工具直接调用服务并遵守已有 RBAC/所有者/启停/限额。
显式配置/平台/账号映射 × [1,2,5] 展开 12 项，不修改共享 config.quantity；当前 Run/Intent 和单账号租约规则不变。
计划/轮次唯一时点、暂停/恢复、容量等待、重叠/漏跑与同价观测按现有领域实现核验，不另起 Agent 调度器。
统计以现有领域分子/分母及时间口径为准；可比键未知、跨币种或报价性质不同，不强行连趋势或自动换汇。Agent 不从助手文本重算指标。
前端复用已有批次/计划/结果页面及私有 Blob 读取，新增聊天引用与必要缺口；实时权限、串行观察与 generation 栅栏不变。

## 8. 发布、来源和回滚

每个移植组件记录固定来源提交/文件/哈希、目标文件、保留/改写/裁剪内容及行为测试，包含原 MIT 版权和许可证。
最小依赖闭包、真实取消、模型/用户隔离、持久化和现有项目回归通过后才启用 deerflow_source。
回滚关闭新执行器或具体工具准入，保留可见历史/checkpoint、领域记录/Intent/证据；不清表、不自动重放、不静默切模型。
离线契约、真实模型和真实平台分别记录，旧 Client 的公开 API 缺口不再作为新方案必须等待上游修复的门禁。
