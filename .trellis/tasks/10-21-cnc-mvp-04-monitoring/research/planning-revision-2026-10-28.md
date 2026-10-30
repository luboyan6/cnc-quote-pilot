# 2026-10-28 规划修订与源码依据

## 授权与当前范围

- 用户先提供 `F:/downloads/CNC竞品报价监测系统技术设计方案_v1.0.md`，说明账号管理和自动报价已经完成，要求基于本项目规划批量执行、定时检测、异常处理和结果展示。
- 本轮用户明确回复“请将上述功能 创建trellis 任务”。本次授权为创建/修订规划任务，不是启动产品实现。
- 复用 `10-21-cnc-mvp-04-monitoring`，新增四个子任务，全部保持 `planning`，不调用 `task.py start`。
- 本次修订在该任务子树内采用确定性业务流程、现有报价入口、APScheduler 和 Vue/ECharts。旧父任务的 Deep Agents / DeerFlow 前置不属于本轮执行依赖；其他任务保持其原有范围。
- 旧任务的 `prd.md`、`design.md`、`implement.md`、`task.json`、两个上下文清单已原样复制到 [legacy-planning-2026-10-28](legacy-planning-2026-10-28/)。历史验收证据保留，不因规划修订标记为通过。

## 需求来源

原附件已复制为 [source-technical-design-v1.0.md](source-technical-design-v1.0.md)，SHA-256：

`8291ce3193b7766c419d2afa0da42b2812e4750e1a936031fc13a611f0e6e2aa`

附件中的分层、任务快照、历史追加、分类异常规则作为需求输入；工程落点采用仓库现有结构。附件的 Celery/Beat 与 Jinja2 建议由现有 APScheduler 与 Vue/ECharts 承接，本轮不新增相同职责的运行栈。附件的原始五天工期是历史目标，本次不据此承诺交付日期。

## 已核对事实与接入约束

| 依据（仓库相对路径与行号） | 当前事实 | 规划影响 |
| --- | --- | --- |
| `backend/pyproject.toml:11` | APScheduler 固定为 3.11.0，SQLAlchemy/Redis 已存在 | 复用当前版本和封装，不升级框架 |
| `backend/app/core/ap_scheduler.py:62`、`:96` | Redis 选主、Job Store、builtin 白名单和生命周期已存在 | 一个活跃调度器，新增短时 CNC 扫描 handler |
| `backend/app/core/ap_scheduler.py:726` | `_task_wrapper` 为同步调用，直接返回 builtin handler 的结果 | builtin 使用同步数据库短事务，禁止返回未等待的 coroutine |
| `backend/app/core/database.py:93` | 已有同步 engine 和异步 Session 工厂 | 同步扫描与异步消费者分别使用各自 Session，禁止跨线程传递 Session/Page |
| `backend/app/modules/cnc/quote/service.py:15`、`:50`、`:55` | 单次服务保留进程内 activity，并通过 create_task 运行两家报价 | 首期同一进程/事件循环消费队列；持久化记录不等于可恢复 Page |
| `backend/app/modules/cnc/quote/repository.py:180`、`:201` | 快照和执行复验读取当前账号、权限、配置和文件 | 批次增加受限数量覆盖，固定原配置版本；配置更改须显式失败或重建，不静默采用 |
| `backend/app/plugin/module_cnc/cnc_quote/model.py:11`、`:21` | 已有 Run/Intent；active_config_id 唯一 | 复用为尝试记录，同配置排队，不解除唯一约束来增加并发 |
| `backend/app/modules/cnc/login/repository.py:78`、`:104` | 账号领取与续租带 owner/token | 报价快捷路径也要经过相同账号互斥与失效栅栏 |
| `backend/app/modules/cnc/quote/jlc_quote_service.py:160`、`:185`、`:243` | JLC 快捷路径使用固定 platform_id 查询账号和共享本地会话文件 | 显式传入已授权账号，复用隔离、加密会话；按当前平台注册信息路由 |
| `backend/app/modules/cnc/quote/repository.py:314`、`:328`、`:464` | 结果保存同时标记 QUOTED/REFERENCE_ESTIMATE 为 success，保存异常被捕获记录 | 新增明确指标，结果和完成状态原子提交，存储失败不能报告完成 |
| `backend/app/plugin/module_cnc/cnc_quote_result/model.py:14` | 结果/历史模型已存在，run_id 尚非唯一 | 扩展该表，迁移前检查重复行，不创建第二套历史表 |
| `backend/app/plugin/module_cnc/cnc_quote_result/service.py:64`、`:145` | 统计/历史为直接 select，历史按创建时间升序后截断 | 应用统一可见范围，按可比条件取最近 N 条后升序呈现 |
| `backend/app/plugin/module_cnc/cnc_quote_result/controller.py:90` | 截图直接按结果 ID 与路径读取 | 先执行记录权限、软删除与路径根校验，证据存入私有目录 |
| `frontend/web/src/views/module_cnc/cnc_quote_result/index.vue:1`、`:493` | 已有统计、列表、详情、历史图与 ECharts | 增量接入批次/轮次和真实指标，保留当前单次报价交互 |
| `frontend/web/src/api/module_cnc/cnc_quote_result.ts:1` | 结果 API 客户端已存在 | 扩展共享类型和筛选，避免前端自行重算业务口径 |

## 验证级别

上述为源码/配置核对。用户将账号管理和自动报价列为已交付基础；本轮不重新实现这些模块。任务启用前只需核验当前集成契约和本任务直接依赖的能力，不以旧任务状态推翻用户说明，也不据此补勾历史 live 验收。

隔离测试可先验证编排与异常行为。真实平台验收单独记录，JLC 的 REFERENCE_ESTIMATE 保留原性质；不承诺该平台返回正式报价。

## 官方机制依据

- [APScheduler 3.x FAQ](https://apscheduler.readthedocs.io/en/3.x/faq.html#how-do-i-share-a-single-job-store-among-one-or-more-worker-processes)：共享持久 Job Store 不能被多个活跃调度器并行使用。
- [APScheduler coalescing / misfire](https://apscheduler.readthedocs.io/en/3.x/userguide.html#missed-job-executions-and-coalescing)：扫描任务可以合并触发，但业务轮次仍应在数据库去重。
- [PostgreSQL SELECT / locking](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)：SKIP LOCKED 可用于队列式并发领取；这不能证明 SQLite 测试覆盖生产锁语义。

本轮读取官方机制文档，不升级依赖版本。产品实现时以仓库锁定版本和实际部署数据库验收。
