# DeerFlow Agent 源码融合设计

## 1. 目标架构与源码边界

Vue/Uni-app → 现有 FastAPI Chat Controller → ChatService → 本地 AgentService → 适配的图/技能/中间件 → CNC Service → 既有 DB/Redis/调度器/受控浏览器。
源码基线、移植取舍与来源记录要求见 [映射表](research/source-integration-replan-2026-10-29.md)，不以安装 DeerFlowClient 或调用上游工厂完成接入。

| 职责 | 本项目落点 |
| --- | --- |
| 图组装、状态、技能激活、中间件、提示词 | 新 `app/modules/ai/agent/`，选择上游相关源码重组，保留可验证行为 |
| 单轮异步执行、限额、停止、事件 | 同模块 AgentService；使用编译图原生异步流，框架执行循环不另写 |
| 个人模型、身份、业务权限 | 现有 Redis/解密、AuthSchema 与 CNC Service；不移植上游全局配置和鉴权 |
| 会话元数据、旧 Agno 兼容、可见消息 | 现有 `ai/chat/` 按 CRUD/Service/Schema/Model 分层扩展 |
| 技能目录/详情 HTTP | 新 `ai/skills/`，与运行时注入同一 SkillCatalog，通过现有路由总表注册 |
| 报价/批量/计划/结果/凭证 | 已有 `app/modules/cnc/` 服务；Agent 工具直接调用服务，不绕回本机 HTTP/MCP |
| 资源启停 | 现有 `app/__init__.py:lifespan` 与 AsyncExitStack |

对来源组件逐项记录“保留、适配、裁剪”，不直接搬 `deerflow/` 目录、改包名或恢复旧自建实现充数。选用 LangChain/LangGraph 公共框架编译/执行能力属于底层依赖，不是调用 DeerFlow 接口。

## 2. 与当前工程融合

Controller 只处理传输、认证和 schema；Service 做编排；CRUD/Repository 管数据；持久模型沿 MappedBase 和 Alembic。
`app/api/v1/routers.py:DOMAIN_CONTROLLERS` 是当前内置路由入口，不能同时按旧 plugin 路径重复发现。
服务依赖使用当前 `AuthSchema`、`async_db_session`、logger、CustomException 和设置类；不引入上游全局 YAML 单例、第二个 FastAPI app 或独立启动器。
个人模型每轮读取后构造独立 async model，不全局切换密钥、地址或温度；图/工具不跨用户共享可变上下文。私密模型配置不进入 checkpoint。
按移植闭包锁定最少框架及 saver 依赖，不安装完整 harness 的可选平台依赖；同步维护 pyproject、uv.lock、生产 requirements 和启动说明。

## 3. 异步执行与停止

从适配后的组装代码取得编译图，AgentService 直接消费原生 `astream`；不消费同步 Client，不用 to_thread 包裹推理。
应用 lifespan 持有服务和 checkpoint/model 资源，单轮 Task 有明确所有者。停止、断线、切会话、服务退出都要取消并 await 流/模型清理；保留 CancelledError，禁止 middleware 吞掉取消。
WS 接收、生成与唯一发送器独立运行，有界队列与轮次栅栏丢弃晚到事件。终态只由单轮收敛出口发布一次。
首 token 前、慢模型、慢消费者、工具等待和 shutdown 是 Lead 的先行验证；“已发 STOPPED”不能替代本地生成/HTTP 流已关闭。远端服务是否继续计费不由本地取消作保证。
报价/批次在领域事务完成准入后归领域生命周期；取消聊天只停本轮生成/观察。取消与领域准入并发时以持久请求键查询实际准入，不重复提交或误报已取消业务。

## 4. 技能、工具与状态

适配上游元数据解析、显式激活、允许工具集合及活跃技能上下文；只读根目录来自后端发布资源，不扫描开发助手 .agents 目录。
目录/详情/执行共同读取一份 SkillCatalog。技能和工具权限取发布允许范围与当前项目权限交集，业务工具再次校验本人对象/账号。
只提供受限技能内容读取，不开放上游通用 read_file、Shell、浏览器或任意 Python 路径。暂停/报价等领域工具不暴露凭据、原始 DOM 或秘密 URL。
图状态使用标准 full checkpoint，选择消息/技能/必要摘要字段与 reducer，剔除上游沙箱、委派和平台状态。长期记忆、delta checkpoint 和自改技能本期不启用。

## 5. 会话、文件与兼容

LangGraph checkpointer 是新执行器推理状态唯一来源；项目保存会话所有者、执行器/旧会话关联、标题/删除状态及可重建的可见 Human/Assistant 投影。
旧历史先验证归属，再按稳定来源标识幂等导入；不重放工具、不每轮重复全量注入 checkpoint。旧 Agno 用户名映射到数字用户时必须基于已验证归属。
列表/分页/排序/重命名/删除统一；删除屏障阻止旧来源复现。显式回滚至 Agno 后仍能读取新可见历史，执行器切换不自动重跑工具。
保留 REST/个人模型和旧 WS 文本/[DONE]/[STOPPED]；新 Web 显式 protocol_version=2。事件以项目判别类型映射图事件，界面不从自然语言猜 JSON。
STEP 仍走真实字节/hash/part/config 上传和第三方授权；凭证走现有受鉴权业务读取，无上游 uploads/artifacts 旁路。

## 6. 数据库、现有业务与发布

首期在当前 PostgreSQL 部署验证 async checkpoint 持久化、独立连接资源和重启；SQLite 用作相应隔离回归。MySQL 的新 checkpoint 兼容是后续技术门禁，旧 Agno 支持不因本任务移除；无受支持 saver 时明确拒绝启用新执行器，不静默切库或回退。
应用业务模型与 checkpoint 自有表的迁移职责分离，标准 saver setup 作为显式部署步骤，不能在普通请求中建表。Alembic 反射保护要保留 checkpoint 非 ORM 表。
历史 `a7d30f26b8e1` 与后续链不改写、不清表。新增映射迁移跟随实施时实际 head，先在一次性库验证。
批量/恢复/监测/结果以现有代码及其任务契约为事实来源，Agent 任务只做工具/事件集成和缺口补足，不重复造表/调度/指标。
发布顺序为 Lead 源码/停止门禁 → 聊天兼容 → 报价工具/凭证 → 批量监测结果工具。新执行器通过独立开关启用；回滚停新入口，保留历史/checkpoint/领域意图。
