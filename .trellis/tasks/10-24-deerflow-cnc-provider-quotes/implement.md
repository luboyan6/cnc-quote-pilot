# 双平台报价实施清单（源码融合方案，待评审）

> 2026-10-29 修订：DeerFlow 必要 Agent 源码按当前 FastAPI 架构适配，本轮只改计划。领域工具从本地 Agent 直接调用现有 CNC Service，不调用 DeerFlowClient/Gateway 或本机 HTTP/MCP。复用当前 app/modules/cnc 的实现，仅补实际缺口；前置为本地图、身份/模型、技能/checkpoint 与真实异步停止验证，见 [源码融合依据](../10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md)。


前置：Lead/聊天契约落地并检查；本子任务经用户批准进入实施。线上操作沿用已有报价授权，实际缺失的账号、文件声明等信息单独处理。

- [ ] 1. 核对现有 QuoteService/平台执行、恢复、结果/证据与两家站点最新观测，列出实际缺口；清点历史未结清意图，只读对账后决定准入。不得重建已存在能力或对未知副作用重新上传。
- [ ] 2. 验证现有 Run/Intent 的跨新 Run 未结清范围屏障及恢复契约，仅在实际缺失时补足并发保护；保持冻结文件/参数、账号租约和已有重试语义。
- [ ] 3. 复用现有结果/证据存储与认证读取，补足尚缺的私有发布、关联及必要迁移；覆盖脱敏、文件暂存、存储失败、撤权及跨用户读取。
- [ ] 4. 复核 Xometry 既有执行路径及证据，补真实上传/几何体/保存回读/价格工期与只读对账缺口；离线验证后受控线上验收，未通过不启用新增能力。
- [ ] 5. 独立复核嘉立创当前服务和观测，补相应端口缺口，严格保留参考估价/审核分支；正式路径未验证时 PA-03 保持未通过，不为完成任务改枚举。
- [ ] 6. 在 ai/agent/tools/ 以原生异步工具直接调用现有 CNC Service，接技能与聊天凭证引用；通过当前权限/白名单、稳定请求键与固定错误验证，不新增上游 Client/HTTP/MCP 调用层。
- [ ] 7. 覆盖登录失效、首写后超时、回执丢失、未知页面、取消、撤权、重启、存证/结果事务失败；确认只读恢复和零重复写入。
- [ ] 8. 分别记录真实平台结果、凭证和剩余阻塞；完整 Trellis check、规范更新、提交评审后再进入批量监测。

## 验证

在 `backend/` 下，复用现有 quote/login/recovery/results 测试，缺失的 evidence 边界样本实施时补齐：

```powershell
.venv/Scripts/python.exe -m pytest tests/cnc/login tests/cnc/browser tests/cnc/quote tests/cnc/upload tests/cnc/results tests/cnc/recovery tests/ai/agent -q
.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/quote app/modules/cnc/browser app/modules/cnc/cnc_quote_result tests/cnc
.venv/Scripts/basedpyright.exe app/modules/cnc/quote app/modules/cnc/cnc_quote_result
```

新增文件/模块模型/路由等补入实际局部检查范围。验证 OpenAPI 无重复挂载，迁移仅在一次性库升级/降级。若修改 Vue 凭证卡片，运行聊天/报价相关 Vitest、type-check、局部 lint 和 build。真实平台使用各自技能规定的当前证据链；本清单不等于已执行线上验收。

## 门禁与回滚

Xometry、嘉立创分别启用，单项未验证保持禁用。无安全正式路径时记阻塞；仍可交付真实估算显示，但不能勾选正式验收。停用适配器即回滚，保留私有证据/Run/Intent，不迁移会话到普通浏览器、不发起下单/外联。
