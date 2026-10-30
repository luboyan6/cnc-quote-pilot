# CNC 批量、监测、恢复与结果共享契约（2026-10-28）

适用于本任务及四个子任务。需求与验收归各任务 PRD；本文件拥有跨子项接口、状态与数据口径。当前是规划契约，所列新接口/字段/测试尚未实现。

## 1. 运行边界

- Router → 领域 Service → Repository；浏览器仍由 QuoteService/执行所有者持有，HTTP/扫描器不操作 Page。
- 模型、CRUD、Schema、Controller 沿用 `backend/app/plugin/module_cnc/`；编排放在 `backend/app/modules/cnc/`。
- 首期 `WORKERS=1`，同一 FastAPI lifespan 启停一个异步 QuoteDispatcher，初始全局自动执行容量 1、同账号 1、同配置 1；人工等待占用的浏览器有独立容量和超时上限。
- 批次入库是可靠入口；唤醒可丢失，消费者周期扫描补偿。Redis 不作为业务任务唯一事实来源。
- 单次报价保留现有 API 和关闭行为；新批次页面关闭只停止读取，明确取消命令才停止任务。
- 单次与批量报价共享账号租约/配置互斥。进程内 semaphore 仅限制资源，不能代替持久租约。
- 多 API worker、多机浏览器调度及跨进程 frame/input 路由为后续工作；首期配置校验应明确拒绝不支持的 CNC 执行拓扑。

## 2. 模型与不变量

| 记录 | 核心字段/约束 | 所有者 |
| --- | --- | --- |
| cnc_quote_batch | id、actor_id、source(manual/schedule)、request_id、request_fingerprint、status、created_at；UNIQUE(actor_id, request_id) | T1 |
| cnc_quote_batch_item | id、batch_id、config_id、account_id、input_snapshot、input_fingerprint、exec_status、attempt_count/max_attempts、next_attempt_at、cancel_requested_at、claim_owner/token/until、row_version、时间累计；UNIQUE(batch_id, input_fingerprint) | T1；恢复策略由 T2 扩展 |
| cnc_quote_schedule | id、actor_id、name、enabled、interval_minutes、timezone、target_snapshot、revision、next_run_at、deferred_slot/reason/since、row_version | T3 |
| cnc_quote_schedule_round | id、schedule_id、scheduled_for、schedule_revision、status、batch_id、reason、created_at；UNIQUE(schedule_id, scheduled_for) | T3 |
| cnc_quote_run（已有） | 可空 item_id、attempt_no；UNIQUE(item_id, attempt_no)，手动旧行保持可空；保留现有 request 唯一键与 active_config_id 唯一键 | T1 |
| cnc_quote_intent（已有） | upload/configure/submit/declaration 的持久 claim、回执与不明状态 | T2 接入；不得绕过现有保护 |
| cnc_quote_result（已有） | UNIQUE(run_id) 对非空 Run 生效；batch/item/round 引用、file_sha256、comparison_key/version、effective_snapshot、tax/shipping/discount/lead-time 商业口径、evidence_state | T1 落库一致性，T4 展示扩展 |

批次计数从子项聚合为权威；如缓存计数，必须可重算并防重复增量。配置表启停/用户可见范围继续使用既有机制；不能把配置表 status/batch 当报价批量执行。

一次尝试的 Run、完成状态、结果引用在一个事务中提交。重试保存新 Run；历史观测按真实 Run 追加。同 Run 重放只返回原记录，不重复添加观测。迁移前只检查重复 run_id 并输出清单；存在冲突时停止迁移，待可审阅修复方案确认，不自动删除历史行。

新表时间用 UTC aware datetime；界面默认 Asia/Shanghai，数据库的旧账号租约时间通过既有适配转换，不在本轮全局改列类型。

## 3. 批次准入与快照

请求示意：

```json
{
  "request_id": "UUID",
  "targets": [
    {"config_id": 101, "account_id": 20, "quantities": [1, 2, 5]},
    {"config_id": 102, "account_id": 30, "quantities": [1, 2, 5]}
  ]
}
```

- 服务端按当前 RBAC、数据范围、平台关联、配置可用性、账号及文件校验；不接受任意路径、平台 URL、Python handler 或密码。
- 先规范化并去重数量/目标，再计算请求指纹与展开数；有界队列容量与准入在事务中仲裁，失败时整体回滚。
- 同键同指纹返回原批次；同键异指纹 409。运行请求 UUID 从 item_id + attempt_no 稳定派生，不随网络重试变化。
- 快照固定文件哈希、源配置 revision、平台 code、账号引用、完整参数与数量；不修改共享 config.quantity，不存明文密码/Cookie。
- QuoteRepository 增加受限数量覆盖/从已存快照构建执行的内部入口。重新读取权限和资源状态；源配置 revision 或文件变更时停止为 INPUT_CHANGED，不采用新值。
- 排队子项的冻结文件在原文件仍可验证时执行。文件更改/删除由既有文件守卫拒绝；本期不引入文件版本仓库。
- 单配置 active Run 冲突时保持排队；若找到其他 item、数量或 fingerprint 的 Run，不将其认领为本 item 的成功结果。
- 账号默认选择沿用零/一/多账号规则；提交时必须已确定每个 target 的账号。执行中不静默切换账号。

## 4. 执行与报价状态

执行状态：`PENDING → RUNNING → COMPLETED | FAILED | CANCELLED`；旁路为 `RETRY_WAIT`、`WAITING_HUMAN`、`RECONCILING`、`CANCELLING`。

- PENDING/RETRY_WAIT 均为数据库可领取队列，next_attempt_at 控制时机。资源占用导致的等待不增加 attempt_count。
- COMPLETED 保存 quote_kind：QUOTED / REFERENCE_ESTIMATE / PENDING_REVIEW；FAILED/CANCELLED 不伪造价格。
- WAITING_HUMAN 表示需要当前用户动作；PENDING_REVIEW 表示本次采集完成但平台仍审核。两者分别展示。
- cancel_requested_at 一经设置，禁止新自动 mutation；活跃项先 CANCELLING，所有者确认停止/资源释放后结算。取消与提交确认并发时保留实际发生的证据，取消不抹掉已确认结果或不明 Intent。
- 每次领取递增 claim_token；写入状态、续租、结果和清理必须匹配当前 owner/token/version。旧 callback 不得覆盖新状态。
- 批次聚合：PENDING / RUNNING / WAITING_HUMAN / CANCELLING / COMPLETED / PARTIAL_FAILED / FAILED / CANCELLED；等待核对计入活跃，并单独给出 reconciling_count。
- 全部成功采集（含估价/待审）为 COMPLETED；成功采集与失败混合为 PARTIAL_FAILED；全部失败为 FAILED；用户取消存在的终结批次为 CANCELLED，已完成数和正式报价数保留。

## 5. 异常、预算与重启

错误投影至少包括 `error_code`、`category`、`stage`、`retryable`、`next_attempt_at`、安全用户消息、私有 evidence_id；原始异常和凭据不进入 API。

自动重试最大执行次数默认 3（含首次），退避基准 30s / 120s 加抖动；测试使用可注入时钟，平台限流可延长至不早于 Retry-After/冷却期限。

| 阶段/异常 | 行为 |
| --- | --- |
| 远端写入前网络/页面临时错误 | 受预算控制的 RETRY_WAIT |
| 会话失效 | 同账号一次重新认证；认证失败按明确错误停止或人工 |
| 验证码/MFA/声明缺失 | WAITING_HUMAN；声明沿用当前文件/声明版本/显式选择契约 |
| 无效文件/不支持参数/权限撤销 | 固定错误失败，不自动重试 |
| 429/可识别限流 | 持久冷却，其他不受限资源可继续 |
| 选择器/页面契约变化 | 证据留存并停止，不用任意页面脚本猜测恢复 |
| claim 已写入，远端回执丢失 | RECONCILING，只读核对，不能再次上传/保存/提交 |
| 远端成功、本地保存失败 | 重试本地持久化或只读核对，不重新报价 |
| 进程退出、租约过期 | 未发生副作用的排队/尝试可安全重领；不明 Intent 保持核对/人工 |

恢复不依赖前端 status polling。消费循环和恢复扫描负责持久推进；人工操作仅发送已有受限命令。Page 丢失后若无法恢复其对应操作，输出明确原因，不宣称自动接管。

## 6. 调度、时点与并发

- 首期支持 interval_minutes（正整数）固定周期，timezone 默认 Asia/Shanghai；Cron/复杂日历为后续范围。
- 计划显式保存目标快照；修改计划产生新 revision，已生成轮次/批次保持原输入。原配置变更需要更新计划，否则 INPUT_CHANGED。
- 新增 `app.modules.task.cronjob.node.handlers.cnc_monitor` 的同步 builtin `scan_due`，只调用同步 Service/Repository 完成短事务；调度注册使用现有 SchedulerUtil/Node 生命周期。
- 扫描任务配置 max_instances=1、coalesce=True；扫描间隔 60s。唯一键和行锁仍是业务防重边界。
- 同一计划行锁事务内：检查 enabled → 判定 slot → 创建唯一 round → 创建 batch/items → 推进 next_run_at。容量不足时整个创建事务回滚，不留下空轮次；另一个短事务重新锁计划，仅在 revision/slot/启用状态仍匹配时记录 deferred_slot/reason/since，不推进时点。重复失败只更新同一等待记录。
- 下一时点由原 scheduled_for 和 interval 推进到未来，避免每次 now + interval 导致漂移。所有比较/唯一键使用 UTC。
- 前轮未结束时记录 SKIPPED_OVERLAP；停机漏跑不补采过去报价。到期尚在一个扫描间隔宽限内可生成本轮，超宽限且没有已记录容量等待的 slots 记录 MISSED。已记录 deferred_slot 的计划在容量恢复后可准入一次迟到轮次，按真实 observed_at 采集/展示，不回填过去价格；期间其他错过时点按缺口记录。长停机采用有界分段记录/计数，不能产生无界写入或伪造价格。
- 暂停与扫描锁同一计划行，以事务先后仲裁。暂停只阻止新批次；恢复从下一个未来 slot 开始。另行取消已有批次使用批次 API。
- 计划创建者、账号或配置失权时记录不可执行原因并暂停计划，避免无限创建失败轮次。扫描器在执行准入时重查当前权限，不长期持有 HTTP JWT。
- 暂停、恢复或编辑计划应清理旧 revision 的容量等待记录，不能让旧 slot 绕过新启停/目标校验。若创建失败与记录 deferred_slot 之间发生崩溃，尚未建立的 slot 在重启时按 MISSED 处理并留下故障原因，不伪造已排队或已报价记录。

## 7. 结果、指标与比较

- 未取消终结子项数 = COMPLETED + FAILED；采集完成率 = COMPLETED / 分母；正式报价率 = quote_kind=QUOTED 的子项数 / 分母。RETRY_WAIT/运行/人工/核对单列，分母为 0 返回 null，界面显示“暂无结果”。
- 一个子项重试多次只在批次主指标中计一次；attempt_count、首次完成率作为独立字段。历史列表仍可查看尝试详情。
- queue_ms、active_execution_ms、human_wait_ms、reconcile_ms、total_wall_ms 分开记录；进程重启/重试累加持久区间，不用结果 created_at 反推全部执行时间。
- 比较键包含 provider、账号商业条件、file_sha256、完整 effective 参数、quantity、currency、price_scope、税/运/折扣口径、交期档位、quote_kind 和比较规则版本。
- 关键口径未知或缺失时不可直接比较；不同币种/数量/报价性质分系列展示，不自动换汇。同价格仍是新观测；无价格/失败/漏跑轮次不能造零值点。
- 同组有效前值为 0 或不存在时变化率为 null；否则用 Decimal 算 (current - previous) / previous。后端 JSON 金额/差额/变化率用十进制字符串，ECharts 仅在绘制时转 number。
- 历史取相同可见范围内最近 N 条，再按 observed_at、id 升序输出；保留原 quoted_at，旧记录口径未知须显示 unknown，不自动补齐。
- tax/shipping 等未知值为 null，不能默认 false/0。正式/估价/待审核必须独立计数，不直接沿用旧 success 布尔值推断正式报价。

## 8. API 与前端边界

统一继承项目 API 前缀；以下列出 `/cnc` 之后的业务路径，属于待实现契约。

| 方法/路径 | 权限与用途 |
| --- | --- |
| POST /cnc_quote_batch/preview | batch:create + 对应账号/配置读权限，返回规范化组合数与参数摘要 |
| POST /cnc_quote_batch/create | batch:create + 实际配置/账号执行权限；返回稳定 batch_id |
| GET /cnc_quote_batch/list、/detail/{id}、/{id}/items | batch:query/detail + 数据范围 |
| POST /cnc_quote_batch/{id}/cancel | batch:cancel + 数据范围，幂等取消请求 |
| POST /cnc_quote_batch/items/{id}/retry | batch:retry + 当前执行权限；只允许安全且未取消项，不明 Intent 拒绝重发 |
| GET /cnc_quote_batch/items/{id}/attempts | batch:detail，查历史 Run；人工 frame/input/resume/declaration 沿用原 Run 接口 |
| POST /cnc_quote_schedule/create、PUT /cnc_quote_schedule/update/{id} | schedule:create/update + 对应资源/执行权限；版本条件更新 |
| GET /cnc_quote_schedule/list、/detail/{id}、/{id}/rounds | schedule:query/detail + 数据范围 |
| POST /cnc_quote_schedule/{id}/pause、/{id}/resume | schedule:update + 数据范围；恢复再验权限 |
| GET /cnc_quote_result/list、/stats、/history-prices、/detail/{id} | 沿用结果权限，扩展 batch/item/round/时间/比较组筛选，统一过滤 |
| GET /cnc_quote_result/screenshot/{id} | 记录读取权限 + 私有证据服务，no-store，严格证据根目录 |

上述 shorthand 权限注册为 `module_cnc:cnc_quote_batch:*`、`module_cnc:cnc_quote_schedule:*`，并复用现有 `cnc_quote_result` 权限。所有新菜单/按钮权限通过仓库当前机制显式登记。批次执行不扩大旧单次执行的 RBAC。

批次页、计划页与现有结果页使用同一有效筛选；统计/列表/趋势/截图均应用同一记录范围。轮询串行、携带 generation 并在离开时取消读取/释放 Blob URL；页面迟到响应不能覆盖新筛选。证据通过带认证请求获取 Blob，不能依赖图片 URL 自动携带 Bearer Token，也不能落入公共 static 挂载绕过授权。

## 9. 迁移、检查与回滚

- 按实施时实际 Alembic head 线性生成迁移；不预写猜测 revision，不自动操作用户数据库。
- T1 创建批次/子项与尝试关联，T3 创建计划/轮次，T4 增加比较/证据字段；后续迁移以已落地前项为父。
- 真实 PostgreSQL 验证唯一键、行锁、取消/领取/扫描并发；SQLite 仅用于可移植业务测试。部署其他数据库须明确验证后才声明支持。
- 停用顺序：禁新计划/批次 → 停扫描/领取 → 有界结算活跃项 → 保留结果、Intent 和证据。代码回滚优先于降级删表；有数据时不破坏性 downgrade。
- 新代码使用 Trellis implement/check 子代理执行时，先按工作流装载上下文；本轮只写规划，未运行任何产品测试。
