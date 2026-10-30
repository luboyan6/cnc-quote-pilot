# T3 实施计划与交付报告

## 实施状态

- [x] 核对 T1/T2 实际接口、恢复检查和质量记录，加载 backend/scheduler 规范。
- [x] 增加 Schedule/Round 模型、唯一键 `(schedule_id, scheduled_for)`、时点索引和兼容迁移（`2026_10_28_1830_e5a2c3d81028.py`）。
- [x] 实现计划 CRUD/版本校验/暂停/恢复/轮次查询及 RBAC，输出 UTC 时间。
- [x] 从 T1 提炼可复用的规范化与准入构造器，提供同步短事务入口；在执行器独立事件循环推进短事务，避免跨线程异步 Session 冲突。
- [x] 实现锁计划、判定 slot、round/batch/items/next_run_at 原子提交，覆盖唯一冲突/容量不足/中途故障。
- [x] 实现重叠（SKIPPED_OVERLAP）、漏跑（MISSED）、宽限（grace_period_seconds）、长停机有界推进（compute_next_slot anchor 运算）。
- [x] 注册固定 builtin:cnc_monitor.scan_due，通过现有 SchedulerUtil/Node 生命周期对账，不影响其他 job。
- [x] 完成定向测试集（13 项全通过），联合回归通过（68 passed, 28 skipped），静态检查全绿。

## 验证结果

1. **定向测试**:
   - `tests/cnc/monitor/test_schedule_handler.py`: 内置处理函数绑定与调用通过。
   - `tests/cnc/monitor/test_schedule_http.py`: 动态路由发现、权限检查与 CRUD 接口验证通过。
   - `tests/cnc/monitor/test_schedule_scan.py`: 轮次准入、并发重叠跳过、长停机漏跑标记、队列容量等待验证通过。
   - `tests/cnc/monitor/test_schedule_service.py`: slot 对齐算法、时区规范化、计划暂停/恢复/目标版本修订验证通过。
   - 结果：**13 passed**。

2. **联合回归**:
   - `pytest tests/cnc/batch tests/cnc/recovery tests/cnc/monitor -q`
   - 结果：**68 passed, 28 skipped**。

3. **静态类型与格式检查**:
   - `basedpyright app/modules/cnc/monitor app/plugin/module_cnc/cnc_quote_schedule app/plugin/module_cnc/cnc_quote_schedule_round`: **0 errors, 0 warnings, 0 notes**。
   - `ruff check --no-fix`: **All checks passed!**
   - `ruff format --check`: **All checks passed!**
