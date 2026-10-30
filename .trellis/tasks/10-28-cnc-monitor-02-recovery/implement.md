# T2 实施计划

> 2026-10-28 已激活为 in_progress。已完成核心异常分类决策器、有限重试与退避抖动、一次会话重新认证、未决副作用 RECONCILING 隔离、本地存储恢复、恢复扫描器（RecoveryScanner）、安全手动重试接口（POST /cnc_quote_batch/items/{id}/retry）及 RBAC 登记。

## 顺序

- [x] 核对 T1 实际模型、dispatcher、claim token、取消与终结接口，更新本项上下文为最终落地路径。
- [x] 建立结构化错误/阶段/副作用状态和恢复决策，覆盖已有 LoginError/BrowserStop/平台错误的兼容映射。
- [x] 接入快捷报价 mutation 前 claim、确认回执与 uncertain；证明异常路径不能绕过保护。
- [x] 实现有限重试、一次重认证、持久平台/账号冷却及可注入时钟/抖动。
- [x] 实现 RECONCILING 只读核对、本地存储恢复与人工等待/超时；每一步核验当前权限。
- [x] 增加恢复扫描与 lifespan 有界停止，验证在没有前端轮询时仍运行。
- [x] 完成取消/租约失效/晚到回调条件写入，保留真实已发生副作用和原始结果证据。
- [x] 接入安全手动 retry/人工能力投影，不允许重试未确认远端 mutation 或重置预算。
- [x] 执行故障注入与定向回归，交接给 T3/T4。

## 验证

已新增：
- `tests/cnc/recovery/test_error_policy.py`：覆盖 9 种错误分类、时钟注入退避、重试预算耗尽、会话重认证上限、限流冷却与敏感日志脱敏（9 passed）。
- `tests/cnc/recovery/test_recovery_service.py`：覆盖网络超时转 RETRY_WAIT、未决操作转 RECONCILING、手动重试预算控制、终态与未决项重试拦截及权限隔离（7 passed）。
- `tests/cnc/recovery/test_recovery_scanner.py`：覆盖 WAITING_HUMAN 超时转 MANUAL_TIMEOUT、RECONCILING 暂存结果恢复转 COMPLETED 及扫描器启停（4 passed）。
- `tests/cnc/recovery/test_recovery_http.py`：覆盖动态路由发现暴露 retry 接口、RBAC 鉴权及异常响应（2 passed）。

执行记录：
~~~powershell
pytest tests/cnc/batch tests/cnc/recovery -q
# 55 passed, 28 skipped (PostgreSQL opt-in) in 93.32s

basedpyright app/modules/cnc/recovery app/modules/cnc/batch/repository.py app/plugin/module_cnc/cnc_quote_batch/controller.py
# 0 errors, 0 warnings, 0 notes

ruff check --no-fix app/modules/cnc/recovery app/modules/cnc/batch/repository.py app/plugin/module_cnc/cnc_quote_batch/controller.py tests/cnc/recovery
ruff format --check app/modules/cnc/recovery app/modules/cnc/batch/repository.py app/plugin/module_cnc/cnc_quote_batch/controller.py tests/cnc/recovery
# All checks passed! 11 files already formatted
~~~

## 评审门与回滚

E-AC01～08 核心功能与隔离回归已通过。未决变动保护已生效：
- 远端 mutation 未决状态坚决禁止盲目重试；
- 达到最大执行次数（默认 3 次）禁止普通用户重复触发；
- 代码回滚可通过配置或停用扫描器实现，已有 Intent 与数据保持无损。
