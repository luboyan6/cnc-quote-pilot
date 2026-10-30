# T1 实施计划

> 2026-10-28 用户明确要求根据本计划开始任务，已激活为 in_progress。实施代码正在执行最终 check；隔离 PostgreSQL 并发和迁移测试已运行，双平台 live 验收仍未执行。

## 顺序

- [x] 核对 git status 与当前 app/登录/报价修改，加载 backend 实际规范；明确责任文件和数据库 head。
- [x] 建立 Batch/Item、Run 尝试关联、结果唯一约束与兼容迁移；历史重复检查无损失败。
- [x] 实现共享 preview/create 规范化与原子幂等/容量准入，冻结完整输入及稳定请求 UUID。
- [x] 增加数量覆盖的内部快照接口，保留原单次行为；配置更改明确失效。
- [x] 将 JLC/Xometry 快捷路径接入账号选择、隔离、lease 与 Intent；未验证有效参数回读的 JLC 执行在上传前停止，不伪造报价。
- [x] 实现同事件循环 QuoteDispatcher、配置/账号互斥、持久推进及 lifespan 有界启停。
- [x] 实现列表/明细/items/attempts/cancel API 与菜单/按钮权限，检查实际动态路由注册。
- [x] 将 Run/Item/Result 原子终结，取消与回调条件更新；实现不依赖前端轮询的完成聚合。
- [x] 增加测试并执行定向回归；记录与 T2 交接的状态/取消/尝试接口。部署和真实平台验收单列，不视为已通过。

## 验证

拟新增 tests/cnc/batch/test_batch_service.py、test_batch_repository.py、test_batch_http.py、test_batch_dispatcher.py、test_batch_migration.py。数据库并发测试需在真实 PostgreSQL 上覆盖同键创建、容量争抢、领取、同配置竞争和结果唯一性；SQLite 不替代锁验收。

实现后从 backend 执行：

~~~powershell
uv run pytest tests/cnc/batch tests/cnc/quote tests/cnc/login
uv run ruff check --no-fix app/modules/cnc/batch app/modules/cnc/quote app/plugin/module_cnc/cnc_quote_batch app/plugin/module_cnc/cnc_quote_batch_item
~~~

对新增/修改代码定向 basedpyright 与格式检查；通过 HTTP/OpenAPI 检查路由和数据权限。实际文件落点改变时同步命令，不执行尚不存在的路径。

## 评审门与回滚

B-AC01～08 有结果后交接 T2。隔离测试通过与真实平台成功分开报告；旧平台验证缺口不自行勾选。

回滚先禁 batch create 和消费者领取，结算活动项，保留 Run/Intent/结果及用户数据；代码可关闭新增能力，新关联列保持兼容，已有数据不破坏性 downgrade。



## 2026-10-28 实施与验证记录（最终 check 前）

### 实施落点

- 新增领域编排：backend/app/modules/cnc/batch/{contracts,repository,service,dispatcher}.py。
- 新增 plugin Batch/Capacity、Item 模型及 Batch controller/schema/crud；API 为 preview/create/list/detail/items/cancel/attempts。复杂重试端点由 T2 承接。
- QuoteRepository 支持受限 quantity override 和 from_frozen，源 configuration revision、account revision、源文件 SHA-256 变化停止，不修改共享 config.quantity。
- Batch admission 通过单例容量行的事务 UPDATE 统一串行化容量与请求仲裁，PG 领取采用 SKIP LOCKED；SQLite 使用条件 UPDATE 补充防双领。Batch actor/request 唯一、Item input 唯一、Run item/attempt 唯一、Result run 唯一。
- QuoteService.start_snapshot 是批次/instant 的共享入口。批次建立 Run 前先领取账号 fenced lease；资源忙只排队，不创建尝试。LoginManager.start 新增可选内部 preclaimed lease，原单次调用形态保留。
- Run 保存、Item 状态、Result 写入在同一事务提交，落库异常不吞掉。快捷路径远端返回先保存私有 pending_result_view/evidence，再在终结事务确认 Intent；失败仅重试本地保存，不重新上传/报价。
- stage/claim/save/Intent 路径检查 Item owner/token/claim_until；取消锁顺序与完成一致为 Item→Batch，迟到写入不得回退终态。
- lifespan 引入可控 QuoteDispatcher，默认 CNC_BATCH_ENABLED=false；开关关闭时 preview/create 拒绝，读取/取消仍可用。开启要求 WORKERS=1。app finally 的故障清理由 check agent 进一步覆盖。
- JLC/Xometry 快捷执行基础接入选定账号、account-bound encrypted browser state、冻结 SDK 文件 bytes、input/mutation guards 和持久 Intent。JLC 已移除固定 platform_id=2 账号和共享明文 session 文件，但现有页面证据不足以验证同一零件的保存后有效参数；单次及批量 JLC 路径现在均在浏览器上传前返回 `JLC_EFFECTIVE_PARAMETERS_UNVERIFIED`。
- InstantQuote.export_controlled 缺省为 None；快捷 Xometry 遇当前声明统一停止，完整声明/当前文件/actor/版本持久授权仅由原 managed typed declaration API 执行。批次 Xometry 使用该 managed owner 路径；当前 reviewed binding 未获真实平台证据，因此保留明确未激活失败，不假造可用性。
- 保留 JLC REFERENCE_ESTIMATE、Xometry PENDING_REVIEW 及未知金额/税运/交期语义。平台 code 从 frozen provider registry 来源读取，不依赖行 ID 1/2。
- backend/sql/sys_menu.json 增加隐藏 CNC 批次权限种子（create/query/detail/cancel）；不新增前端页面。现有部署仍需按项目菜单初始化/授权机制登记权限。

### 迁移与开关

新增 backend/app/alembic/versions/2026_10_28_1400_d4b9a2f61028.py，父 revision 为实际源码 head b76d50ea5d8f。重复非空历史 Result.run_id 会输出冲突列表并停止，不自动删行；批次已有数据时拒绝破坏性 downgrade。结果 currency 允许 null，避免失败/未知观测隐式变成 CNY。

本会话未执行用户业务数据库 upgrade/downgrade。部署须先审阅并应用此迁移，再显式启用 CNC_BATCH_ENABLED；默认保持关闭。

### 已执行的定向验证

- 新增 Batch 业务测试首轮 8 passed；增加 12 项展开、自主调度与远端结果保存重试后 11 passed（15.32s）。
- Batch + 历史 quote migration 在增加后续三个业务用例之前为 18 passed（11.94s）；包含 7 个 lifespan 故障清理用例。
- Quote repository + runner：35 passed（80.21s）。
- 隔离 migration 测试验证新表/Run 列与唯一约束、容量种子、重复历史 run_id 无损停止、空数据 downgrade。
- HTTP 测试验证 RBAC、409 同键冲突、私有输入 400 拒绝和 OpenAPI controller 路径；实际 DynamicRouterRegistry 的最终 OpenAPI 检查交 check agent 补齐。
- 我负责的 batch/quote service/repository/runner/models 定向 basedpyright：0 errors、0 warnings、0 notes；定向 Ruff clean。provider worker 的独立结果另由最终 check 汇总。
- QuoteDatabase 隔离 fixture 现包含真正 Result 表映射，原测试不再靠生产代码吞掉 Result 写入异常通过。历史 migration 用例只比较其自身 revision 引入的列；最新 Run 完整模型由 batch migration 用例覆盖。

### 仍未验收 / T2 交接

- 本机隔离 PostgreSQL 16.8 已验证幂等/容量争抢、SKIP LOCKED、同配置 Run 冲突、取消与完成竞争、领取锁等待过期，以及迁移的历史重复保护和结果唯一约束。各测试使用新建临时 schema，未连接或迁移用户业务数据库；部署环境仍需单独验证。
- 未运行双平台真实登录、上传、报价；未发送人工声明、未产生真实远端 mutation。
- Xometry reviewed managed binding 仍需真实同文件/参数/当前结果证据，不能以测试 fixture 激活。快捷声明暂停是明确产品限制，不能写成真实批量平台成功。
- JLC 仍需真实同零件、保存后的材料、数量、表面处理和公差回读证据；在此之前，单次与批量 JLC 自动报价均明确不可用。
- dispatcher 关闭超过 35 秒时会尝试将运行标记为 `RECONCILING` 并返回固定失败，但现有 lifespan 仍继续关闭资源，超时清理任务可能尚未结束；此极端场景的资源收敛尚需单独设计验证。
- T2 继承 Item 的 attempt_count/max_attempts/next_attempt_at、claim owner/token/expiry/row_version、Run item/attempt 关联及 cancel_requested_at。到期失主无 Run 可释放；有 Run 保持 RECONCILING/BATCH_OWNER_LOST_NO_RETRY，绝不盲重放 Intent。复杂 retry 分类/退避/跨重启核对仍属 T2。
- 本机后端综合回归及后续定向检查通过，隔离 PostgreSQL 最终全文件回归 28 项通过；真实平台、部署以及上述超时资源收敛仍未通过验收。提交/归档未执行。
