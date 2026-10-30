# Lead 源码融合实施清单（待评审）

前置为最新源码融合规划获准；本轮不激活或执行以下步骤。共享契约见 [local-contracts](../10-24-deerflow-cnc-agent/research/local-contracts.md)。

- [ ] 1. 从固定上游提交建立逐文件来源/哈希/MIT 清单，分析选定 graph/skills/middleware/state 的依赖闭包；与当前 modules 路径和工程规范对齐，确认历史清理与其他未提交改动。
- [ ] 2. 解析最小 LangChain/LangGraph/model/saver 依赖版本，更新可选安装、锁文件和生产说明；不引入完整 harness/extension-api 平台依赖。
- [ ] 3. 在 agent/ 下适配图组装、必要状态与中间件；先用原生 async model 的受控慢响应样本验证首 token 前取消、流关闭及唯一终态。不满足 LA-04 时先记录实际原因，不继续启用。
- [ ] 4. 适配技能解析/只读存储/显式激活/允许工具集合与提示词，记录保留/裁剪项；覆盖目录一致性、未知技能、根目录越界、重复激活与技能上下文保持。
- [ ] 5. 注入现有 AuthSchema/个人模型读取，接本人图纸/配置/账号脱敏视图/报价状态等只读工具；逐调用重验权限，覆盖两用户并发与凭据脱敏。
- [ ] 6. 接标准 async checkpointer、应用 lifespan/AsyncExitStack 和设置开关，验证 PostgreSQL 持久化/重启、shutdown、启动失败清理及非 ORM 表保护；不操作用户数据库。
- [ ] 7. 验证稳定领域请求与取消/准入交界，不重建通用运行台账；冻结给聊天消费的内部事件/状态/停止边界。
- [ ] 8. 局部质量检查及来源静态扫描通过后，单独用真实模型完成“技能 → 只读工具 → 本人记录”与实际 stop 验收，离线样本不冒充真实通过；更新规范/报告后进入聊天任务。

## 验证计划

拟新增测试为 `backend/tests/ai/agent/`，覆盖实际适配后的项目边界与来源行为；不是恢复此前已删除的测试。实施时测试名与真实文件同步。
在 backend/ 执行：
```powershell
.venv/Scripts/python.exe -m pytest tests/ai/agent -q
.venv/Scripts/ruff.exe check --no-fix app/modules/ai/agent tests/ai/agent
.venv/Scripts/basedpyright.exe app/modules/ai/agent
uv lock --check
```
修改 settings/lifespan/路由/安装文件时补入局部检查；保留当前 Agno/模型与 CNC 查询回归。零收集、跳过或失败不计通过。
依赖扫描确认无运行时 deerflow import、同级路径、Gateway/全局配置/通用工具或未解释的源码依赖。对来源行为增加断言，不能仅断言导入成功。
数据库 setup/迁移/重启只用一次性库，记录 checkpoint 与应用表管理的不同职责。真实模型、真实平台验收分开；本任务不做真实平台写入。
