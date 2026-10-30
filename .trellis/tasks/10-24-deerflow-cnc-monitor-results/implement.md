# 批量监测结果实施清单（源码融合方案，待评审）

> 2026-10-29 修订：DeerFlow 必要 Agent 源码按当前 FastAPI 架构适配，本轮只改计划。领域工具从本地 Agent 直接调用现有 CNC Service，不调用 DeerFlowClient/Gateway 或本机 HTTP/MCP。复用当前 app/modules/cnc 的实现，仅补实际缺口；前置为本地图、身份/模型、技能/checkpoint 与真实异步停止验证，见 [源码融合依据](../10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md)。


前置：Lead/聊天契约及报价 snapshot/结果/私有凭证接口已检查；用户批准本子任务。生产运行只使用已验证平台。若正式报价阻塞，继续离线工程须明确评审，不改变前置/整体验收状态。

- [ ] 1. 复核 10-28 领域任务的当前交付、snapshot/Run/Intent/active_config 和模块路径，列出 Agent 接入缺口；复用现有数量覆盖，不更新共享配置数量。
- [ ] 2. 复核现有 Batch/Item、Schedule/Round、结果观测与权限/迁移；验证请求指纹、唯一键与读取范围，仅补实际缺口，不另建 Observation 或重复模型。
- [ ] 3. 通过现有 BatchService/Dispatcher/Recovery 测试证明原子展开、有界队列、单账号执行、并发重放、部分失败及取消符合领域契约，不重写已交付消费者。
- [ ] 4. 复用 MonitorService 和既有调度 handler，覆盖时区、唯一计划时点、容量等待、暂停/恢复、重叠、漏跑及重启只读恢复，保留当前领域规则。
- [ ] 5. 直接消费现有结果/观测/统计/可比历史及私有凭证服务，校验 Decimal、分子分母与时间口径；未知或未交付项明确保留，不另定指标公式。
- [ ] 6. 在 ai/agent/tools/ 将受限 batch/monitor/report 工具直接绑定到现有服务；覆盖当前权限、稳定请求键、生成停止/业务取消边界，只有实际交付能力进入单一技能目录。
- [ ] 7. 复用既有 Vue 批次/计划/结果界面，补聊天卡片引用/安全跳转及必要缺口；保留串行观察、代次栅栏和独立业务取消。
- [ ] 8. 离线验证 12 子项及两轮调度，随后单独进行真实双平台 12 项及两轮观测验收，保留估算/失败与阻塞，不把数量对齐等同于正式成功。
- [ ] 9. 完整跨层 Trellis check、规范更新及提交评审，回父任务做 R-01–R-08 与 AC-01–AC-09 集成核对。

## 验证

在 `backend/` 下复用现有领域测试，并补 Agent 工具接入样本；新增目录必须实际存在后再纳入命令：

```powershell
.venv/Scripts/python.exe -m pytest tests/cnc/batch tests/cnc/monitor tests/cnc/results tests/cnc/quote tests/cnc/login tests/cnc/browser tests/cnc/upload tests/ai -q
.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/batch app/modules/cnc/monitor app/modules/cnc/cnc_quote_result tests/cnc
.venv/Scripts/basedpyright.exe app/modules/cnc/batch app/modules/cnc/monitor app/modules/cnc/cnc_quote_result
```

前端 `frontend/web/`，拟新增测试名需与实际实现同步：

```powershell
pnpm exec vitest run src/__tests__/cnc-quote-batch.spec.ts src/__tests__/cnc-quote-schedule.spec.ts src/__tests__/cnc-quote-result.spec.ts src/__tests__/cnc-part-config-auto-quote.spec.ts
pnpm run type-check
pnpm run build
```

对所有修改的 API/视图/样式/测试文件执行局部 ESLint、Prettier --check、Stylelint；不跑全仓自动修复。模型/权限/调度集成模块纳入后端局部 lint/type 范围。迁移升级/降级及唯一约束使用一次性数据库；真实模型、真实平台和离线测试单独记录。跳过或失败不能判通过。

## 风险与回滚

重点验证数量覆盖不影响共享配置、计划并发及未知副作用重启。关闭批次/计划准入并暂停新调度回滚；保留历史/结果/意图，活动轮次显式结算，不重放远端请求。正式报价外部阻塞保持可见。
