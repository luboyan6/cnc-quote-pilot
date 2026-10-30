# 最新范围授权：计划修订与旧实现清理

> 历史授权：本文仅记录 2026-10-27 的计划/清理范围。本次 2026-10-29 用户要求修订为源码融合计划；现行范围见 [最新决定](../../10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md)。本轮仍不实施产品。

2026-10-27 用户在获知旧实现直接使用 LangChain create_agent、没有调用官方 Client 后要求：
“修改计划，删除之前的代码，直接复用官方DeerFlowClient Harness，减少重复实现”。

范围澄清时用户明确选择“先修改计划并清理旧实现”，之后要求继续。
因此本轮授权仅为：修改现有任务计划、删除旧自建运行层/专属测试/依赖/配置、验证保留原应用。
新官方 Client 的依赖安装、接入实现、聊天/UI/历史改造仍为后续 planning。
此前“可以”对自建 Lead 的授权属于已被取代的方案，不能继续用来实施旧架构或自动扩展到新接入。

清理范围、官方 API 核验及迁移保护见父任务 research/harness-client-replan-2026-10-27.md。
保留所有不相关的未提交 CNC/MCP/前端/技能/文档改动。不运行 agent-platform，不操作用户数据库。
不删除或重写 a7d30f26b8e1 迁移；后续 CNC 迁移已引用它。无 commit/push/archive 授权。

主会话修订计划和规范；implement agent 仅清理 product 范围；check agent 核查并修复范围内缺陷。
