# Deep Agents 版本与用法核验

核验日期：2026-10-21。本文件记录外部资料及仓库事实；具体工程选择见 [Agent 设计](../agent-design.md)。本轮仅修订规划，未安装依赖、调用付费模型或运行真实报价。

## 1. 最新版本与兼容要求

已实时读取 [PyPI JSON 元数据](https://pypi.org/pypi/deepagents/json)并核对[版本页](https://pypi.org/project/deepagents/0.7.29/)：

| 项目 | 核验结果 |
|---|---|
| 最新稳定版本 | `deepagents==0.7.29`；该发行文件未 yanked |
| Wheel 发布时间 | `2026-10-20T16:17:42.442313Z` |
| Python | `>=3.11,<4.0`；仓库 `backend/pyproject.toml` 为 `>=3.12`，声明范围兼容 |
| 核心依赖下限 | `langchain>=1.4.6,<2.0.0`；`langchain-core>=1.6.12,<2.0.0`；`langsmith>=0.14.11` |
| 其他声明依赖 | `langchain-anthropic>=1.7.6,<2.0.0`、`langchain-google-genai>=4.4.2,<5.0.0`、`packaging>=23.2`、`wcmatch>=11.0` |

这些是已发布元数据，不是本仓库已安装/解析通过的版本。首次实施时再次查 PyPI 的最新非预发布、非撤回版本；有更新则记录新版本、核对 API 后统一更新本任务基线。生产使用精确版本和 `uv.lock`，不使用运行时浮动 `latest`；其余直接导入的包、模型 provider 包、checkpoint 包及 Playwright 由同一次解析确定兼容版本。实际安装/回归前不宣称兼容已通过。

拟在 backend 中执行的依赖入口：`uv add "deepagents==0.7.29" langchain langchain-core langgraph langchain-openai langgraph-checkpoint-sqlite`。LangGraph 在此提供 Deep Agents 底层的类型/恢复/checkpoint API，不新增一套手写编排。若采用其他 provider 或 PostgreSQL checkpoint，相应替换/补充集成包；不凭记忆手写伴随包的“最新版本”。

## 2. 官方 API 核对

| 官方资料 | 已核实事实 | 对本项目的意义 |
|---|---|---|
| [Quickstart](https://docs.langchain.com/oss/python/deepagents/quickstart) | Python 入口是 `from deepagents import create_deep_agent`，模型需支持 tool calling | D-13 在未知页面/异常恢复阶段实际调用；正常确定性步骤不强制模型 |
| [Customization](https://docs.langchain.com/oss/python/deepagents/customization) | 支持 `model/tools/subagents/skills/backend/permissions/context_schema/checkpointer/interrupt_on/response_format` | 用参数配置 harness，复用现有应用生命周期 |
| [Backends](https://docs.langchain.com/oss/python/deepagents/backends) | 当前写法传 `StateBackend()` / `CompositeBackend(...)` 实例；旧 `lambda rt: StateBackend(rt)` 已弃用；StateBackend 的文件在同 thread checkpoint 中保存 | 新方案使用当前实例 API；工作文件与真实业务记录分工明确 |
| [Permissions](https://docs.langchain.com/oss/python/deepagents/permissions) | 首条匹配生效，无匹配默认允许；只管内置文件工具，不管自定义/MCP 工具或 shell | 必须有兜底 deny；浏览器动作另加服务端守卫 |
| [Subagents](https://docs.langchain.com/oss/python/deepagents/subagents) | 默认存在 general-purpose；活动 profile 可设置 GeneralPurposeSubagentProfile(enabled=False)，仅空 subagents 不足以关闭默认项 | D-13 默认关闭委派，仅保留当前异常内的观察/恢复策略选择 |
| [Skills](https://docs.langchain.com/oss/python/deepagents/skills) | 技能目录含带 `name/description` frontmatter 的 `SKILL.md`，按需加载正文 | 平台流程知识与机器可校验的 JSON 配置分别版本化 |
| [Human-in-the-loop](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop) | `interrupt_on` 需要 checkpointer；通过同 thread 的 `Command(resume=...)` 恢复，批量决策与待处理动作对应 | 人工接管与现有 owner/状态/预算检查接合 |
| [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | checkpointer 保存 thread 状态；Store 保存跨 thread 数据；内存 saver 重启会丢失 | 持久 checkpoint 不替代报价数据库；MVP 不引入共享可写长期记忆 |
| [Models](https://docs.langchain.com/oss/python/deepagents/models) | 可传 provider:model 或预初始化模型；OpenAI 字符串路径当前默认启用 Responses API | 兼容网关不能仅换 base_url；显式模型实例及工具调用兼容性需测试 |
| [Streaming](https://docs.langchain.com/oss/python/deepagents/streaming) | 可通过 updates 和子图流获得进度 | 转换为项目事件 DTO；Web 不直接消费框架状态或未脱敏消息 |

本地技能中若有较旧 backend 工厂或最低版本示例，以本次官方资料和实施时锁定发行包的接口为准，不照搬旧 API。

## 3. AgentSeek 模板借鉴范围

用户提供的[模板目录](https://github.com/ob-labs/agentseek/tree/main/templates/deepagents)有 default、research、content-builder、sandbox 等分支。已查看 default 的 README 和 [`demo_binding.py`](https://github.com/ob-labs/agentseek/blob/main/templates/deepagents/default/%7B%7Bcookiecutter.project_slug%7D%7D/src/%7B%7Bcookiecutter.project_slug%7D%7D/demo_binding.py)：其 `build_agent()` 在读取配置后创建本地 Deep Agents runnable；`build_spec()` 用 `agentseek_langchain.messages_spec` 暴露给 AgentSeek。这个工厂与绑定分离的方式适合借鉴。

另查看 [research README](https://github.com/ob-labs/agentseek/tree/main/templates/deepagents/research)：展示 Deep Agents 主代理、子任务、todo 和流式结果的组织方式。CNC 借鉴任务分解与进度映射，不复制搜索工具、模板模型默认值或 React 前端。

本项目采用 SDK 嵌入现有 FastAPI consumer：固定 Workflow + `build_recovery_agent()` + 只读观察/RecoveryDecision/策略守卫/复验 + 现有 API/事件。AgentSeek 的 lifecycle、Bub gateway、AG-UI binding 不是调用 SDK 的必要依赖；不增加第二服务，也不把开发用 AGENTS.md 带入生产 CNC 上下文。

## 4. 仓库约束与未完成核验

- `backend/pyproject.toml` 已有 `agno==2.5.8`；`backend/app/modules/ai/chat/service.py` 调用 `AgnoFactory`。CNC 新方案独立使用 Deep Agents；已有通用聊天模块不是本次迁移目标。
- AI 聊天模型配置目前以 Redis 缓存保存且有 7 天 TTL（同文件 `_AI_MODEL_TTL`）。定时 CNC 任务不能依赖用户当前激活项或这份会过期的缓存；需固定服务端模型配置引用与非敏感版本，密钥运行时解析。
- `backend/app/config/setting.py` 声明支持 mysql/postgres/sqlite，默认 mysql；这不证明当前实际运行库类型或连通性。官方 PostgreSQL saver 不能直接当作 MySQL saver 使用。
- 依赖解析、provider 的 tool calling/结构化输出、checkpoint 驱动/序列化及恢复、技能只读 backend、平台 live 报价均待后续实施验证。页面目录和框架示例均不能代替上述证据。

## 5. 固定 Workflow 与异常 Agent 的 API 依据

- 官方 [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents)区分代码预定义流程与模型动态决策。本项目按用户 D-13 选择混合分工：正常流程固定，未知网页问题由 Deep Agents 有限观察和选择恢复策略；具体业务规则是本项目设计，不是 SDK 自动保证。
- 官方 [Custom middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom)提供模型/工具调用钩子，可用于观察工具权限、用量和协议约束；恢复动作仍由领域策略执行器校验，不能只依赖 Prompt 或置信度。
- 官方 [Profiles](https://docs.langchain.com/oss/python/deepagents/profiles)提供 register_harness_profile、GeneralPurposeSubagentProfile、excluded_tools 等配置；注册按匹配模型/provider 生效，须验证预初始化实例命中。不要传不存在的 create_deep_agent(harness_profile=...)，也不要排除受保护的 SubAgentMiddleware。
- D-13 的 S01～S11、E01～E13、allowed_strategies、守卫/复验和安全恢复位置见 [workflow-design.md](../workflow-design.md)。正常零模型调用有效；Agent 实际异常恢复、业务暂停与 SDK interrupt 的区分均需单独验证。
