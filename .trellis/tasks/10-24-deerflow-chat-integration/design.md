# 聊天与当前 FastAPI 架构融合设计

## 服务与路由边界

现有 `ai/chat/controller.py → ChatService → AgentService` 直接进程内调用。AgentService 由 Lead 在 `ai/agent/` 适配实现，不经 DeerFlowClient、上游 HTTP 或本机 MCP。
Controller 只处理传输/认证/参数，Service 选择执行器及编排，CRUD/Model 管会话数据，Schema 管 HTTP/WS 及历史响应。
沿 `app/api/v1/routers.py:DOMAIN_CONTROLLERS` 注册技能路由，不复制上游 Router/DI/异常栈，也不按旧 plugin 路径双注册。
保留 Agno 分支、REST 外壳、握手/RBAC 与个人模型。新开关 AI_CHAT_ENGINE 由现有 settings 控制，不在模型失败时自动换执行器。

## 历史和持久化

新增必要会话元数据/关联模型，沿 MappedBase、数字 actor、CRUD/async_db_session 和项目软删除/时间约定。LangGraph saver 由 Lead 管理，不强行用业务 AsyncSession 代替原生 saver 连接。
用户于 2026-10-30 明确无需迁移旧 Agno 聊天，旧记录保持原样并由旧执行器读取；源码引擎只创建和续聊其自己的新会话，不从当前用户名推断历史所有者，不导入或重放旧工具。
新可见消息是 checkpoint 的展示投影，使用来源消息/轮次标识去重，可修复投影缺失；推理只读 checkpoint。不要另建 Agent Run/ToolOperation 引擎。
源码会话列表/分页/排序/搜索、重命名与删除使用数字用户所有者和删除屏障；保留旧来源数据，不依赖客户端值或当前同名猜测历史归属。
显式回滚 Agno 时通过统一可见历史适配继续读取；切换执行器不静默重跑旧工具。验证刷新、重启、导入失败恢复和并发删除/生成的一致性。

## 事件与停止

Lead 以编译图原生 async stream 提供共享判别事件，单一事件边界分配 seq；Web 显式 protocol_version=2，旧 WS 投影为文本和哨兵。
接收、生成与唯一发送器独立 Task；发送队列有界，连接/session/turn generation 丢弃晚到事件。工具错误和业务结果用真实字段，不从自然语言解析状态。
停止命令取消并 await 本轮图流/model 清理，首次 token 尚未到达也能接收；收敛后发布唯一终态。控制 UI 结束不等于真实生成停止，CA-02 需资源证据。
断线/关闭/切会话同样停止本轮生成观察。CNC 持久准入后的后台任务独立继续，业务取消走其原 Service 命令；停止与准入交界按稳定请求键读实际结果。

## 模型、技能与附件

每轮通过既有 Redis/解密入口构造个人模型快照，交给 Lead 的 model_provider；保留 id/地址/密钥/温度和默认配置语义，不全局切换密钥。
`ai/skills/{controller,service,schema}.py` 读取同一 SkillCatalog，按当前权限/发布能力筛选目录和详情。技能列表、前端选择与实际加载不能各写一份注册表。
STEP 使用现有 CNC 字节上传及 part/config 引用、hash/所有者和第三方授权，不能借用上游 uploads 跳过校验。发送/上传失败保留草稿与可重试状态。
工具进度只携带安全业务引用，报价/批次成功以领域提交状态为准。

## Vue 和兼容

扩展现有 `src/api/module_ai/chat.ts` 和 `views/module_ai/chat/`，建立共享事件类型与连接/session/turn 栅栏，串行查询可取消。
复用 Vue/Element Plus 技能选择、工具卡片和已有 CNC 结果/计划页面的引用；不引入 DeerFlow React UI。
证据经认证请求取 Blob，并在关闭/切换时释放 URL。新写工具未通过验收时目录不可执行；Uni-app 继续旧协议。
模型设置、REST 非流式与旧 Web 无版本 WS 使用同一应用服务边界，避免只修新 Web 而破坏旧客户端。

## 迁移、测试和回滚

会话映射/投影迁移接实施时真实 Alembic head，保留历史 a7d30f26b8e1/后续链；checkpoint 自有表独立保护，先在一次性库演练。
默认保留 Agno，灰度启用 deerflow_source；回滚停新轮并保留历史/投影/checkpoint/领域记录。不会自动清库、重放工具或取消业务任务。
停止门禁由 Lead 先验证，聊天再覆盖端到端传输；源码融合尚未实现，本设计不宣称停止问题已解决。
