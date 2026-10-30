# 批量、监测及结果技术设计（源码融合方案）

> 2026-10-29 修订：DeerFlow 必要 Agent 源码按当前 FastAPI 架构适配，本轮只改计划。领域工具从本地 Agent 直接调用现有 CNC Service，不调用 DeerFlowClient/Gateway 或本机 HTTP/MCP。复用当前 app/modules/cnc 的实现，仅补实际缺口；前置为本地图、身份/模型、技能/checkpoint 与真实异步停止验证，见 [源码融合依据](../10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md)。


## 领域数据与准入

依 [Agent 共享契约](../10-24-deerflow-cnc-agent/research/local-contracts.md) 第 6–7 节直接复用现有 batch/monitor/cnc_quote_result 服务、模型和路由，领域状态及数据结构以 [监测任务契约](../10-21-cnc-mvp-04-monitoring/research/implementation-contract.md) 和当前源码为准。实际使用现有批次/子项、计划/轮次和按 Run 留存的结果/观测关联，不另外新建 PriceObservation 或重复批次表。数字 actor、冻结参数、状态/时间、真实 quote_run/evidence 引用继续由领域层维护。

本任务新增的是 ai/agent/tools/ 中受限 batch/monitor/report 工具、运行时技能与聊天结果引用。CncQuoteResultService 的统计/历史/权限逻辑直接复用，UI 优先复用已存在批次、计划和结果页面。服务内部缺口仍先回到对应领域责任任务处理。

Batch 输入为显式 part/config/platform 映射、账号选择及数量集合；事务内规范化并建立请求指纹，同键同内容返回原批次、异内容冲突。2×2×3 精确生成 12 个子项，独立保存冻结参数/文件引用和确定的领域请求 UUID。snapshot 工厂接受受限数量覆盖后走相同授权/验证，不修改共享 config.quantity。

子项由持久化队列交给现有单浏览器消费者，沿用 fenced lease/资源上限；同配置仍只有一个 active Run，其余排队。同账号不并发执行；有界队列满时明确拒绝准入，不能创建部分成功的批次。取消阻止待执行子项并逐项请求当前活动任务取消，保留已完成结果、未结清意图及真实中间状态。单项失败不会取消无依赖的其他子项。

## 调度与恢复

复用 APScheduler Leader/生命周期及现有 handler，模型不得指定 Python 路径或处理器代码。计划/轮次沿当前 ScheduleRepository 与模型的 schedule_id + scheduled_for 唯一约束，保存触发时区及原计划时间；不重新定义 Agent 专属 MonitorRound。

暂停阻止新轮次，已有轮次继续，可另行取消；恢复从下一未来时点开始。重叠、漏跑及容量等待按领域任务的 SKIPPED_OVERLAP / MISSED / deferred_slot 契约处理，不批量补报过去价格；已记录容量等待的迟到准入保持真实 observed_at。并发暂停/触发复用同一计划行事务仲裁。

重启恢复复用现有 RecoveryScanner/Dispatcher 的副作用阶段、租约和 Intent 检查；可安全重领项按原规则继续，不明 Intent 只能只读对账或等待人工。不能仅凭内存活动为空接管/重新上传，也不将所有 claimed 项一概视作不明副作用。首期仍遵循现有单 worker/单账号资源约束，不构建分布式执行平台。

## 观测与比较

实际观测沿现有按 Run 留存的结果记录追加，即使同价也保留独立观测，不新建 PriceObservation 表。MISSED/SKIPPED_OVERLAP 只保留轮次信息，不捏造价格。比较沿现有 comparison_key/version 和技术/商务范围；未知关键范围、跨币种或报价性质不同则不可直接比较，不自动换汇。

结果 API 直接消费现有领域 Service 计算的终态计数、正式报价率分子/分母、排队/执行耗时及趋势，不从助手文本聚合数据或重定公式。零分母显示暂无结果，取消及未终态单列，历史只连可比点；证据复用当前受权读取，不增加公共图片地址。

## API、Agent 与 Vue

复用经过当前 RBAC/所有者校验的批次、计划、轮次及结果路由与权限项，工具直接调用同一 Service；若存在缺口才按当前 DOMAIN_CONTROLLERS/菜单机制补充，不再在旧 plugin 路径新增第二份。导出/列表使用同样范围，聊天权限不能代替业务写权限。

工具只接收记录 ID、核验参数和稳定请求键；对应服务未启用前技能保持不可执行。Vue 复用现有批次进度、监测计划、历史/趋势及私有结果页面，补聊天卡片引用和必要显示缺口；串行查询与 epoch 栅栏防晚到更新。关闭页面仅停观察，暂停计划与取消批次为明确操作。

## 迁移与回滚

先复核已有模型/索引/唯一约束，仅对确认缺口新增线性迁移；应用迁移跟随实际 head，不重复执行或重写已交付批次/计划/结果迁移。LangGraph checkpoint 和聊天映射各按其职责管理；SQLite/当前部署数据库按实际范围验证，不对用户数据库自动 upgrade。关闭新批次/计划准入后保留结果和轮次；暂停调度 handler，结算未执行项，活动/不确定写入只读处理。回滚不删除价格历史或意图。
