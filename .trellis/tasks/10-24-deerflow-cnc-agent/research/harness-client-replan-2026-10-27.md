# 官方 DeerFlowClient 复用与旧实现清理（2026-10-27）

> 历史方案（2026-10-29 已取代）：本文保留 10-27 的授权、源码核验和清理事实，不再规定当前接入架构。现行用户决定与源码融合边界见 [最新规划依据](source-integration-replan-2026-10-29.md)。

## 最新用户决定与本轮边界

用户要求：“修改计划，删除之前的代码，直接复用官方DeerFlowClient Harness，减少重复实现”。
经范围澄清，用户选择“先修改计划并清理旧实现”，随后要求继续任务。

本轮授权：修订现有父子任务、删除自建 Agent 代码及专属配置/测试、验证原有业务仍可用。
本轮不安装或实现新 Client，不改聊天 UI/历史，不运行真实模型/报价，不操作用户数据库，不提交/推送。
不创建新任务。此前自建 Lead 的实施授权和验收不适用于未来官方 Client 接入。

## 官方证据

- 快速上手：https://deerflow.tech/zh/docs/harness/quick-start
- 嵌入指南：https://deerflow.tech/zh/docs/harness/integration-guide
- 安装状态：https://deerflow.tech/zh/docs/harness
- 只读核验官方仓库 bytedance/deer-flow，2026-10-27 获取 main SHA：
  `24f15cc4790f5b0a50f55332f77f4a2eeb35fdf1`（提交时间 2026-10-27T07:26:16Z）。
- 源码：
  https://github.com/bytedance/deer-flow/blob/24f15cc4790f5b0a50f55332f77f4a2eeb35fdf1/backend/packages/harness/deerflow/client.py
  SHA256 `a89b5da4bf65f0ac43f5b8d7bea62261c1661f49bb92568d5b6eccb48d2d5fb6`。
- 包元数据：
  https://github.com/bytedance/deer-flow/blob/24f15cc4790f5b0a50f55332f77f4a2eeb35fdf1/backend/packages/harness/pyproject.toml
  SHA256 `c5b90e86ae4a9aab4e255f6b4bc1c4481a710c775aaf3c8391695f2c1029e477`。

源码通过 Python urllib 完整读取，以 AST/tomllib 检查公开方法及元数据，未安装依赖、未修改同级参考仓库。

## 关键事实与技术门禁

1. 官方入口为 `from deerflow.client import DeerFlowClient`，可嵌入现有 Python/FastAPI 进程，无需启动 Gateway。
2. 文档示例使用 `astream`/`ainvoke`；本次核验的源码只有同步 `stream(message, *, thread_id=None, **kwargs)` 和 `chat(...)`，没有这两个异步方法，也没有公开 cancel 方法。实施必须以固定版本真实签名为准，不能照抄文档伪造调用。
3. 公开方法包括 `list_threads`、`get_thread`、`list_models`、`list_skills`、`get_skill`、`upload_files`、`list_uploads`、`delete_upload`、`get_artifact`。是否支持旧聊天 CRUD 必须逐项检查，不能假设所有 CRUD 都有。
4. 多轮状态需要 checkpointer；只有 thread_id 不会自动保存历史。聊天列表/重命名/删除/旧 Agno 导入由项目做必要的兼容映射，不能建立另一套 Agent checkpoint/记忆引擎。
5. 当前源码 distribution 名为 `deerflow-harness==2.1.0`，import 名为 `deerflow`；安装页的未来 `pip install deerflow` 尚未正式发布。后续核验发布渠道，使用官方固定 commit 构建的 wheel 或可复现的官方源码依赖，并同步其 workspace 依赖；禁止随便安装同名 PyPI 包或指向 E:/AIWorkspace/agent-platform。
6. 当前官方约束为 LangChain >=1.3、langchain-openai >=1.2.1、LangGraph >=1.2.9,<1.3，且依赖 deerflow-extension-api==0.2.9 等。原自建版本 1.0.x 不兼容，清理原 extra/锁项；未来官方依赖解析作为实施第一道门禁，本轮不宣称解析通过。
7. 技能发现/加载、Agent 组装、图执行、状态检查点优先交给官方；项目仅保留身份/会话映射、个人模型接入、业务工具/权限与传输适配。
8. 官方 Client 构造函数没有直接 model/tools/features 参数。个人模型隔离、CNC 工具注入、禁用长期记忆/沙箱/通用工具，必须先验证官方配置/扩展入口；禁止覆写 _ensure_agent/_get_tools、monkeypatch 或拷贝上游源码绕过。
9. 同步流的非阻塞消费、首 token 前停止和慢消费者收敛是明确的实施前验证项。线程适配可作为最小传输方案，但取消 asyncio Task/to_thread 不等于终止底层生成；未证实官方可用取消机制前不承诺验收达成，也不恢复自建运行循环。
10. 官方 uploads/artifacts 与 CNC STEP 业务上传不同。业务文件沿用现有 hash/所有者/第三方上传授权；报价凭证仍由业务 ACL 管理，不能把官方文件能力当权限旁路。

## 清理清单与数据保护

删除 `backend/app/modules/ai/agent/` 的自建 factory、adapter、contracts、skills、tools、privacy、repository、model、资源、README 和包文件；
删除 `backend/tests/ai/agent/` 的专属测试；
删除仍依赖旧运行层的 `backend/scripts/cnc_agent_smoke.py` 冒烟脚本；
删除 `backend/requirements/agent.txt`、pyproject 的旧 agent extra、旧 AI_AGENT 配置；重算 uv.lock，不整体升级无关依赖。
删除代码前核验实际导入者，保留现有 Agno 聊天、CNC 服务、MCP、受控浏览器及用户其他未提交改动。

保留历史迁移 `a7d30f26b8e1`：后续 CNC 迁移 `23f445d964cc` 已引用它，当前 head 为 `b76d50ea5d8f`。不删除/改写这条迁移链，不降级/删除用户表或意图。
`backend/app/alembic/env.py` 的 include_name 只比较现存 MappedBase 表，已移除模型对应的遗留表会被反射过滤，不自动生成 DROP；复用现有迁移安全回归验证。
遗留表不再作为新方案运行状态源；未来若迁移/归档其数据，必须单独设计并检查未结清操作，不能自动重放写入。

## 计划覆盖关系

本记录与更新后的 design/local-contracts 优先于 2026-10-24 调研中“SDK 可选”“自建 create_agent 为首选”的建议。
旧研究/授权作为历史证据保留并标记已被取代；implement/check manifests 不再注入旧方案为当前要求。
本轮清理验证通过不代表官方 Client、聊天集成或生产报价已验收。
