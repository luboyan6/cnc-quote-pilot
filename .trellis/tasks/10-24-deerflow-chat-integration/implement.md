# 本地源码 Agent 聊天集成实施清单（待评审）

前置：Lead 的源码/依赖、模型隔离、技能/工具、checkpoint 和真实异步停止门禁通过；最新规划获准。本轮仅修订，不运行以下产品步骤。

- [ ] 1. 复核当前 Chat Controller/Service/CRUD/Schema、显式路由总表及前端；建立旧 WS/REST/个人模型/Uni-app 的基线回归，不使用旧 plugin 路径。
- [ ] 2. 将 ChatService 接到本地 AgentService 与现有设置开关，保留 Agno 分支；与 Lead 共享强类型事件/模型/停止契约，不增加 DeerFlow 代理层。
- [ ] 3. 实现项目会话元数据/数字所有者与可见投影，接标准 checkpoint；覆盖新会话分页/续聊/重命名/删除/重启/回滚，避免双写推理历史。用户已明确无需迁移旧 Agno 聊天，保留原记录。
- [ ] 4. 接 WS 独立接收、原生异步图消费与唯一发送器，覆盖首 token 前停止、慢流/消费者、有界队列、断线/切会话、late event 和唯一终态，测 stop 到资源收敛时间。
- [ ] 5. skills 路由通过同一只读目录及当前权限返回真实能力；注册到 DOMAIN_CONTROLLERS。复用 CNC 上传字节/hash/业务引用，保留第三方授权。
- [ ] 6. 实现 Vue 共享事件类型/composable、技能选择/工具卡片/结果引用、代次栅栏、失败草稿与 Blob 释放；兼容无版本客户端。
- [ ] 7. 回归旧 Web/Uni-app/REST 和历史管理，证明聊天停止/关闭与后台报价/批次生命周期独立。
- [ ] 8. 用真实融合 Agent/模型验证“移植技能 → 领域工具 → 真实记录 → UI → 刷新续聊”，另测跨用户与真实停止；离线样本、真实模型及平台结果单独记录。
- [ ] 9. 后端/Vue 局部质量门禁、Trellis check、规范与安装/迁移说明完成后再进入报价工具任务。

## 验证计划

拟新增 `backend/tests/ai/chat/` 和 Lead 的 `tests/ai/agent/`；覆盖源代码适配后的服务与真实 LangGraph 交界，而非 mock 一个不存在的 DeerFlowClient 异步接口。
在 backend/ 执行对应 pytest、Ruff --no-fix 和 basedpyright，纳入实际修改的 chat/skills/agent/settings/lifespan/routers 及测试文件。迁移/重启/双用户验证只用一次性数据库。
前端在 frontend/web/，以下 ai-chat 测试是拟新增名称，实施时与真实文件同步：
```powershell
pnpm exec vitest run src/__tests__/ai-chat-events.spec.ts src/__tests__/ai-chat-history.spec.ts src/__tests__/ai-chat-upload.spec.ts src/__tests__/cnc-part-upload.spec.ts
pnpm run type-check
pnpm exec eslint src/api/module_ai/chat.ts src/views/module_ai/chat
pnpm exec prettier --check src/api/module_ai/chat.ts src/views/module_ai/chat
pnpm exec stylelint "src/views/module_ai/chat/**/*.vue"
pnpm run build
```
新增 skills API/测试文件补入局部 lint/type；Uni-app 按实际 package.json 验证。零收集、跳过或未执行不算通过。
检查运行时没有 deerflow import/Client/上游服务依赖，没有新建第二个 App/ORM/鉴权系统；真实模型和平台调用仅在相应实施授权与证据条件具备时执行。
