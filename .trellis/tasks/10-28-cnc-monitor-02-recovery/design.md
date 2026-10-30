# T2 技术设计

继承父 [共享契约](../10-21-cnc-mvp-04-monitoring/research/implementation-contract.md) 第 4～5、7～9 节，错误/状态只使用该处定义。

## 责任范围

新增 backend/app/modules/cnc/recovery/ 的错误分类、重试策略、过期任务扫描与核对服务；扩展 quote/contracts.py、runner/service/repository、当前两家快捷报价的 Intent 接入和 login 租约交互。仅修改本项直接需要的浏览器行为，不重写平台全部 DOM。

T1 已建立的 batch/item/run 与消费者是前置。必要的错误/阶段/时间累计列以 T1 实际迁移为父；相关 tests/cnc/recovery/ 与 quote/login 故障注入回归归本项。下一项会接入调度调用，按顺序交接。

## 错误边界与重试

Adapter/浏览器异常在边界转换为结构化 RecoveryDecision，携带 error_code、stage、effect_state 和允许动作。未知错误保守终结/人工；禁止依靠异常字符串包含 timeout 就重试整条浏览器流程。

决策写入数据库后更新 RETRY_WAIT、next_attempt_at、attempt budget 或 cooldown_until；时钟与随机源可注入。重新认证次数绑定 item/原账号，重复请求不清零。资源等待通过 next eligible 查询处理，不消耗尝试。

现有浏览器错误类型与固定原因映射保持兼容；public reason 采用 allowlist，日志关联 batch/item/run/attempt/account 与安全 request ID。

## Intent 与不明操作

所有远端 mutation 前提交同 Run/阶段的 Intent claim，操作后保存相关回执。重启检查 claim/confirmed/uncertain，已确认只读采用关联结果；不明先观察当前远端对象和文件/参数对应性，证据不足则人工处理。

租约过期不代表远端操作未发生。禁止通过新 request_id、新 Run 或先取消再删除 Intent 重新上传。本地结果提交失败时保留可恢复证据；无法持久化证据时保留不明状态，不虚构完成。

## 取消与恢复

RecoveryScanner 在生命周期内周期扫描到期 RETRY_WAIT 和 stale owner，不依赖用户 status。先校验当前用户/账号/文件与活跃租约，再用 CAS 领取；每次状态/续租/终结都检查 owner/token/version。

取消标志在每次自动 mutation 前检查。活动所有者有界停止、关闭资源并确认；晚到回调不能覆盖取消或新尝试，但将真实远端回执保存到受保护核对记录。已进入不明阶段仍保留追溯和只读核对入口。

WAITING_HUMAN 的 Page 存在时复用原 Run 的受控命令；页面丢失不能伪造 can_input=true。对人工等待和核对设置明确 deadline/资源上限，超时保存 MANUAL_TIMEOUT/RECONCILIATION_REQUIRED 等安全原因。

## 回滚

停止自动重试/恢复领取，保留已有等待和证据；不取消其他 worker 的有效 lease。新状态的读取须保持兼容；带不明 Intent 的记录不得因关闭功能开关变成可自动重传。

