# Lead 源码适配设计

## 源码落点

按 [上游到本项目映射](../10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md) 将必要职责归入 `app/modules/ai/agent/`：

| 模块 | 职责 |
| --- | --- |
| graph.py / state.py / prompts.py | 适配图组装、full 状态 reducer 和 CNC 提示词，返回 LangGraph 编译图 |
| middleware/ / skills/ / resources/skills/ | 适配断裂工具消息修复、安全工具错误、系统消息兼容、循环/预算、显式技能激活及只读目录 |
| model_provider.py | 从现有个人模型/系统默认构造 async model，私密依赖显式注入 |
| checkpoint.py | 标准 async saver 资源与类型边界，不复制上游持久化平台 |
| service.py / schema.py / events.py | 项目执行服务、单轮 Task/取消、强类型事件和资源清理 |
| tools/ | 当前认证上下文下直接调用 CNC Service 的薄工具 |

选择的组件须先分析 import/功能闭包，再替换上游配置、存储、权限、日志和文件路径。代码不是整目录复制后改名；具体来源/哈希/改动与对应行为回归一一记录。
`langchain.agents.create_agent` 仅作为框架编译入口，循环交给框架；不能只写这个调用而省掉已约定的上游技能/中间件行为。

## 显式依赖与项目分层

AgentService 由现有 FastAPI lifespan 建立，接收 checkpoint provider、模型构建器、SkillCatalog 和 CNC 服务工厂。
ChatService 调用本地服务，不新增 Agent HTTP 代理。业务依赖使用 AuthSchema、当前权限查询和 async_db_session；工具不长期持有请求 AsyncSession。
模型每轮从既有 Redis/解密入口获取，构造与用户绑定的 model 对象；不缓存跨用户可变图，不修改全局配置，不把密钥放进 state/config。
`AI_CHAT_ENGINE` 开关与资源限额由现有 settings 统一管理；选 agno 时不强制导入未安装的新依赖。旧模型配置入口和公共响应继续复用。

## 技能/中间件取舍

技能类型、frontmatter/正文解析、名称/路径校验和显式激活按所选上游行为适配，存储改为项目发布的只读根目录。
技能列表和详情同运行时用一份目录。显式选择优先、重复选择幂等、未知技能/权限不足拒绝；正文/受限引用可按需读取，不提供任意文件读写。
保留必要工具消息修复、模型消息格式、安全失败和循环/调用预算中间件；错误转为项目安全码，CancelledError 向执行服务传播。
与 summary/active skill 相关状态采用 full checkpoint；摘要压缩若启用须通过技能保持回归。裁剪沙箱/委派/长期记忆字段以及上游通用工具、扩展安装和在线改技能。
所有者来自服务端上下文，技能/工具文本不能改变身份或打开能力。领域方法仍重查权限，不将提示词作为安全边界。

## 异步执行与取消

本地服务直接消费编译图的原生异步流并统一映射项目事件，使用 native async 模型/工具。
单轮 Task 的句柄只在服务端进程持有，不创建持久 AgentRun 表；传输 turn_id 只关联 UI。同一会话的跨连接并发明确拒绝。
stop/断线/timeout/shutdown 请求取消 Task，并 await 图流关闭、model HTTP 释放及有界清理，收敛后只发布一个终态。禁止后台 to_thread 推理或吞取消异常。
先验证模型连接尚未返回首 token 的取消，以及慢消费者、工具等待、重入、例外清理；“停止消息已发送”不算 LA-04。
CNC 服务完成持久准入后由现有 QuoteService/Dispatcher 持有任务。工具等待与准入提交并发取消时读原请求键确认状态，不让取消传播为重复写入或伪报业务停止。
本地服务能关闭 HTTP 流，不据此承诺远端服务商内部停止或停止计费。

## checkpoint 与生命周期

首期对当前 PostgreSQL 验证 LangGraph async saver 及其连接池；连接配置从既有 settings 派生，SQLAlchemy 业务池与 saver 原生资源分别管理，不强行互换驱动。
应用 lifespan 注册清理顺序：拒绝新轮 → 取消/等待 Agent Task → 关闭模型及 saver 资源；保留当前 CNC dispatcher/recovery/scheduler/MCP 的清理。
checkpoint 自有表通过显式部署 setup 管理，不能借普通请求建表；应用 Alembic 不误删非 ORM checkpoint 表。
本任务验证空会话样本和重启，聊天任务负责生产会话元数据、旧历史幂等导入与可见投影。
历史退役 Agent 表和迁移不复用为新通用运行账本，不删除未结清操作。

## 依赖与回滚

只引入所选组件需要的 LangChain/LangGraph/model/saver/解析依赖并验证版本兼容；不使用整个 harness 依赖列表，也不从同级源码目录 import。
启用前检查依赖、当前数据库和单 worker 拓扑；不支持的部署明确失败。MySQL 的新 saver 路径待验证，旧 Agno 仍可用。
关闭 deerflow_source 入口即可停止新轮；保留 checkpoint、可见历史和 CNC 记录。运行错误不会静默切回其他模型/执行器。
