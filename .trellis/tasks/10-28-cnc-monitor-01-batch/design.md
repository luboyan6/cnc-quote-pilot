# T1 技术设计

继承父 [共享契约](../10-21-cnc-mvp-04-monitoring/research/implementation-contract.md) 第 1～5、8～9 节；此处只定义 T1 落点。

## 责任文件

- 新增 backend/app/modules/cnc/batch/：contracts、service、repository、dispatcher。
- 新增 backend/app/plugin/module_cnc/cnc_quote_batch/、cnc_quote_batch_item/：模型和项目风格 API/CRUD/Schema。
- 扩展 modules/cnc/quote/ 的内部快照、统一执行入口和结果终结；扩展 cnc_quote/model.py 的 item/attempt 关联。
- 接入 app/__init__.py lifespan，统一启动、停止并 await 消费者。
- 必要的 JLC/Xometry 快捷路径账号/租约/Intent 接入，以及 QuoteResult 幂等落库基础；不重写完整 DOM 流程。
- 相关 Alembic 迁移、tests/cnc/batch/ 与既有 login/quote 定向回归。后续 T2/T4 会继续修改共享文件，按顺序交接。

## 准入事务与快照

preview 与 create 使用同一个规范化器。全目标校验通过后计算稳定请求指纹，锁定容量记录/执行等价原子容量仲裁；同事务创建 batch/items。唯一冲突回读同请求，比较指纹后返回原记录或冲突。

明确数量覆盖在内部快照工厂应用，保存原 source revision 与实际 requested；执行时按当前权限、账号 revision 和源配置/文件复验，不从新配置重建请求。请求 UUID 按 item_id/attempt_no 派生。

## 消费与共享执行

QuoteDispatcher 在应用同一事件循环按有界周期扫描。短事务用 SKIP LOCKED 领取，写 owner/token/期限，再释放事务执行浏览器。消费者不靠用户轮询推进。

QuoteService 增加接受已校验批次快照的内部入口，并保留原单次方法/响应契约。同账号进入现有 fenced lease，同配置仍只有一个 active Run。活动 Run 与 item/数量不匹配时返回资源等待，而不是采用其结果。

所有真实路径都需要复用账号隔离与 durable intent；不能以快捷路径绕过。JLC 显式接收 AccountSnapshot，私有加密会话按账号绑定，读取当前 provider registry。Xometry 保留当前文件/声明语义。

## 终结与取消

Run 关联 item_id、attempt_no；run_id 唯一结果写入和子项完成使用同事务。原始错误可私有记录，公开只保留固定安全错误。修复现有结果保存吞异常路径，失败事务回滚并保留可恢复记录。

取消先持久化标志，未领取项直接结算，活动项由所有者有界取消/清理再确认。每次写入校验 owner/token/version，终态不可被迟到回调撤回；详细异常核对策略由 T2 扩充。

## 兼容与回滚

Run 新列可空，不改变旧单次响应结构或 active_config 唯一性。先检查历史重复 run_id，冲突时停止而不删除；迁移以实际 head 为父。禁用新批次入口与消费循环后保留记录，旧单次报价仍可工作。

