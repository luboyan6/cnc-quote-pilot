# 四模块实施与集成计划

> 本轮仅创建规划。所有复选框为后续工作；未执行产品代码修改、迁移、真实询价或产品测试。父任务不调用 task.py start，未来按审核后的子项顺序启动。

## 启动前检查

- [ ] 复核父 PRD、design、共享契约和四个子项；确认最新规划之后收到实施授权。
- [ ] 检查 git status，保留现有用户修改；加载目标层规范，核对当前账号与单次报价真实调用路径。
- [ ] 确认 CNC 执行首期拓扑为单进程；核验实际数据库为受支持版本，记录实际 Alembic head，禁止自动套用未知 pending revisions。
- [ ] 为即将执行的子任务运行 task.py validate；启动该子项而不是父项，按 Trellis implement/check 流程执行。
- [ ] 若后续修改共享接口/状态/指标，先更新共享契约与受影响子项，再实施；其他任务的 Agent 前置不自动继承。

## 交付顺序与评审门

- [ ] T1：批次/子项迁移、快照覆盖、统一执行入口、账号隔离、持久消费、取消请求、Run/Result 原子落库和 API。门槛：12 子项/幂等/互斥/权限/旧单次兼容通过。
- [ ] T2：错误分类、有限预算、持久冷却、人工状态、Intent 核对、取消栅栏与重启恢复。门槛：崩溃、丢回执和晚到回调无重复副作用。
- [ ] T3：计划/轮次迁移与 API、同步 builtin 扫描、时点去重、暂停/恢复、重叠/漏跑、失权处理。门槛：并发扫描和事务故障检查通过。
- [ ] T4：批次/计划页面、结果/指标/比较契约、私有证据、类型/交互和菜单权限。门槛：全链路筛选、金额精度、正式/参考分类、跨用户访问检查通过。
- [ ] 集成：对照父 AC-01～14 逐项记录命令、环境、结果和证据；真实两轮监测单列，不用模拟结果代替。

## 后续检查命令

以下测试目录/文件为子任务拟创建位置，必须在实现后才运行；本轮的计划验证不代表这些检查通过。

backend 工作目录：

~~~powershell
uv run pytest tests/cnc/batch tests/cnc/recovery tests/cnc/monitor tests/cnc/results tests/cnc/login tests/cnc/quote tests/test_scheduler_schedulability.py
uv run ruff check --no-fix app/modules/cnc app/plugin/module_cnc app/modules/task/cronjob/node/handlers/cnc_monitor.py
~~~

类型检查按仓库当前 basedpyright 配置执行，并区分既有基线与本次新增问题。对新增文件运行格式检查；对动态插件路由运行 OpenAPI/HTTP 测试。真实 PostgreSQL 的锁/唯一键/迁移检查必须单独执行并记录，不能用 SQLite 结果替代。

frontend/web 工作目录：

~~~powershell
pnpm exec vitest run src/__tests__/cnc-quote-batch.spec.ts src/__tests__/cnc-quote-schedule.spec.ts src/__tests__/cnc-quote-result.spec.ts src/__tests__/cnc-part-config-auto-quote.spec.ts src/__tests__/cnc-account-login.spec.ts
pnpm run type-check
pnpm run build
~~~

新文件另跑定向 ESLint/Prettier/Stylelint 的检查模式，不对整个用户工作区执行自动修复。

## 真实平台集成验收

- [ ] 对当前用户可访问的两份图纸/双平台配置执行数量 1/2/5，逐项核对实际账号、文件与生效参数。
- [ ] 配置合法周期并执行至少两轮，检查新轮次/新 Run/新观测、同价保留和证据关联。
- [ ] 将 QUOTED 与 REFERENCE_ESTIMATE/PENDING_REVIEW 分开报告；实际平台只给参考价时记录平台能力边界。
- [ ] 验证停止/重启恢复的安全边界，不为了测试主动重放不明上传或提交；优先故障注入验证危险窗口。
- [ ] 保留原账号登录、配置 CRUD、原单次报价和受控人工处理回归证据。

## 回滚点与交接

每个子项自带兼容迁移与功能开关。出现失败时先停止新准入/调度和领取，再协作停止活动项；有远端副作用时只读核对。保留批次、Run、Intent、结果和私有证据，不删除历史。

父项最终检查只覆盖本任务变更与跨子项验收。完成质量门后更新对应 spec、记录真实结果并按工作流交接；不将当前规划落盘描述为功能实现完成。
