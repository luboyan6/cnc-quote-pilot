# T3 技术设计

继承父 [共享契约](../10-21-cnc-mvp-04-monitoring/research/implementation-contract.md) 第 2、6、8～9 节。

## 文件责任

新增 modules/cnc/monitor/ 的计划服务、同步扫描编排、Repository 与契约；新增 plugin/module_cnc/cnc_quote_schedule/ 和 cnc_quote_schedule_round/ 的模型/API/CRUD/Schema；新增 modules/task/cronjob/node/handlers/cnc_monitor.py。必要的 batch 事务接口调整和 Alembic 迁移以 T1/T2 最终实现为输入。tests/cnc/monitor/ 与既有 scheduler schedulability 回归由本项拥有。

## 计划与唯一轮次

计划固定 target_snapshot、revision、interval_minutes、timezone、next_run_at；轮次记录 scheduled_for_utc 和计划版本。唯一约束 (schedule_id, scheduled_for) 作为去重边界。

扫描锁定到期计划行；再次校验 enabled/当前权限/目标，判定是否重叠/漏跑。可执行时在同一事务内用 T1 准入规则写 round、batch/items 并更新 next_run_at。容量不足抛可恢复错误整体回滚，再以短事务记录当前 revision/slot 的容量等待，不留下空轮次；唯一冲突返回已存在轮次，禁止再次创建批次。等待记录和漏跑宽限的优先关系、崩溃窗口及清理由父共享契约第 6 节定义。

T1 使用异步业务 API；本项增加共享规范化/领域构造器加同步 Repository 的事务入口。同步/异步入口使用同一目标校验与指纹规则，数据库权限查询通过明确接口实现，不能复制两套不同业务规则或共享跨线程 Session。

## 调度入口与时间

builtin:cnc_monitor.scan_due 是同步可调用，只执行短数据库扫描事务。沿用 SchedulerUtil/Node 的注册、选主、启停与重新对账，不变更共享执行器默认行为、不调用 asyncio.run 去运行全流程报价。

固定扫描 60s，显式 max_instances=1/coalesce=True，原定时点用 UTC 且按 anchor+interval 推进。允许一个扫描间隔的迟到宽限，超期按共享契约记录 MISSED；大量错过时点按有界分段/计数处理并保留缺口，恢复后不采集假历史。

scan 与 pause/update 锁同一计划行；暂停后不生成新批次。resume 计算下一未来 slot 并重新校验执行权限。存在任何未终结前轮时跳过新 slot 并保存 SKIPPED_OVERLAP。

## 安全与兼容

计划不持久化 JWT、密码或 Cookie；扫描准入与执行前重读 actor/RBAC/账号/配置。失权时暂停计划并保留原因，不无限制造失败批次。CNC 扫描只注册自身命名 job，禁止清空或重建其他业务的计划。

迁移线性跟随实际 T1/T2 head，历史 QuoteResult 可空 round 关联；停止扫描器/禁新计划即可降级，已有批次和观测保留。

