> 历史记录（2026-10-27 已覆盖）：用户已决定直接复用官方 DeerFlowClient Harness，并确认本轮先修改计划、清理自建实现。本文保留原调研/评审事实，其中“SDK 可选”“优先自建 create_agent”及旧授权/状态不再是当前执行要求。现行依据见 [最新方案与范围](harness-client-replan-2026-10-27.md)、父子任务 design/implement 和 [共享契约](local-contracts.md)。

# 10-24 规划续接与代码核验

## 本轮授权与范围

用户本轮要求：“请根据trellis 10-24任务规划开始计划”。沿用既有父任务及四个子任务，补齐可评审的实施规划；不新建任务，不激活任务，不修改产品代码。此前“简要设计”的交付已完成，本轮扩展到实施规划；部署、认证、模型配置、报价边界沿用原决策。实施授权仍为 false，等待本轮规划评审。

## 2026-10-24 源码复核

| 证据 | 当前事实 | 规划影响 |
| --- | --- | --- |
| `backend/pyproject.toml`、`backend/uv.lock` | 声明 Agno 2.5.8；未发现 LangChain/LangGraph 依赖 | 首任务需要兼容性解析及最小依赖锁定；参考仓库的 lock 不是本项目已安装环境 |
| `backend/app/utils/ai_factory.py:57` | Agno 成员 `tools=[]` | 需要本地 Factory 与实际领域工具，不能只增加技能目录 |
| `backend/app/modules/ai/chat/controller.py:235` | 接收指令和消费生成流位于同一串行循环 | 独立接收任务、生成任务及串行发送器；停止须能中断等待首 token 的请求 |
| `backend/app/modules/ai/chat/schema.py:8`、`service.py:157` | files 是通用元数据，生成时未上传字节 | 聊天侧先通过既有上传边界存储真实 STEP，工具只接收业务 ID |
| `backend/app/modules/ai/chat/crud.py:31`、`:112` | 旧会话由 Agno 存储，以用户名隔离 | 新历史采用应用存储，按数字用户 ID 映射；迁移先经旧 CRUD 核验归属，保留旧数据 |
| `backend/app/modules/ai/chat/service.py:378` | 已有按用户读取并解密模型设置的入口 | 每轮服务端读取；不重建模型设置，不把密钥加入图消息或事件 |
| `backend/app/modules/cnc/quote/providers.py:25` | resolver 恒定返回 None | 两个平台均不能宣称已具备生产自动报价；启用须分别过门禁 |
| `backend/app/modules/cnc/quote/contracts.py:22`、`service.py:24` | start 接收配置 ID、账号 ID、request UUID；优先返回历史/活动 Run | 工具层需持久化逻辑操作关联；批量不能修改共享配置来覆盖数量 |
| `backend/app/modules/cnc/quote/service.py:63` | activities/浏览器所有者仍在本进程 | 初期沿用单浏览器消费者；重启后只读对账或明确待人工处理 |
| `backend/app/alembic/env.py:21` | 通过 ImportUtil.find_models 注册模型 | 新 Agent/历史模型必须验证被发现；迁移只在一次性数据库演练 |
| `backend/tests/cnc/{login,browser,quote,upload}` | 既有隔离回归测试目录真实存在 | 新测试叠加这些回归，平台在线验收单独记录 |
| `frontend/web/package.json` | 有 Vitest、type-check、build；lint 脚本自动修复 | 使用局部无修复 ESLint/Prettier/Stylelint；不运行全仓自动修复 |

上传入口的具体复用对象以 `backend/tests/cnc/upload/test_step_upload.py` 及其引用的真实实现为准；不存在 `app/modules/cnc/upload/service.py`，不要按该推测路径新建重复服务。

参考仓库 `E:/AIWorkspace/agent-platform/backend/packages/harness/deerflow/agents/lead_agent/agent.py:33` 使用 `langchain.agents.create_agent`，但同时引用记忆、扩展及其他上游模块。参考 Factory 的组装方式，在本仓库独立实现最小子集，不能直接 import 整个参考包。

## 框架核验与选型

本轮查阅了 `ecosystem-primer` 与 `langchain-dependencies` 技能。沿用已选的 LangChain `create_agent`：运行时仅有受限领域工具与本地技能注册/加载，不需要 Deep Agents 默认的文件管理、Shell、子代理或记忆设施。LangGraph 为其底层依赖，不额外设计一套业务图，也不启用自动重放的持久化图恢复。

官方资料于本轮核验：

- [Agents](https://docs.langchain.com/oss/python/langchain/agents)：支持自行组装模型、工具和中间件。
- [Runtime](https://docs.langchain.com/oss/python/langchain/runtime)：调用上下文可注入身份及依赖；不等于给模型暴露身份参数。
- [Streaming](https://docs.langchain.com/oss/python/langchain/streaming)：模型文本、状态更新和自定义进度可分别适配。本地协议不依赖最新投影 API，实际 API 以首任务锁定版本和契约测试为准。

拟新增 `langchain`、`langchain-core`、`langchain-openai`；LangGraph 等依赖由解析器锁定，若直接使用则显式声明。精确版本在首任务兼容性解析后写入本项目 lock，不照搬参考仓库全部依赖，不承诺未运行的解析已经通过。Agno 保留用于旧协议及历史兼容。现有 Python >=3.12 与 httpx/Pydantic/OpenAI 固定约束不得为省事整体升级。无需启用外部追踪服务。

## 技术门禁与已知风险

1. 首任务先验证依赖解析、可导入性、当前 OpenAI-compatible 模型的 tool calling；失败要明确停在兼容性问题，不静默降级为无工具聊天。
2. 先由 Lead 子任务产出共享运行时契约，再由聊天任务消费，消除原来的双向前置依赖。
3. 持久化逻辑操作关联不能单独解决跨新 Run 重放：同配置/文件/账号范围内存在未结清意图时，领域层仍需拒绝新写入并先对账。
4. 嘉立创正式报价路径、平台账号可用性和历史不确定意图尚未在线重测；不影响离线规划完成，但阻止对应在线验收通过。
5. 仅规划文档检查，不运行真实模型、平台、数据库迁移或产品测试；这些检查仍是实施阶段的待执行项。
