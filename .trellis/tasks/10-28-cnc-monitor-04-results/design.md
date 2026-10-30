# T4 技术设计

继承父 [共享契约](../10-21-cnc-mvp-04-monitoring/research/implementation-contract.md) 第 7～9 节，使用 T1～T3 实际接口；不建立另一套状态或指标来源。

## 文件责任

后端扩展 plugin/module_cnc/cnc_quote_result/ 的 model/schema/crud/service/controller、必要的 quote/repository 结果投影与私有证据服务。新增比较/商业口径/证据字段迁移，衔接 T3 实际 head。

前端新增 views/module_cnc/cnc_quote_batch/、cnc_quote_schedule/ 和对应 api/module_cnc 客户端；扩展现有 cnc_quote_result/index.vue、API 类型、必要的配置列表批量选择入口和菜单/按钮权限。复用 Element Plus、FaTable、现有请求封装和 ECharts，不更换技术栈。只在本项需要的范围内复用 ControlledBrowser 和人工声明 UI。

## 查询与指标

把当前列表可见范围提取到共享结果查询边界，使 stats/history/detail/screenshot 与 list 一致应用 RBAC、actor/数据权限和软删除。不能仅过滤 is_deleted 或靠前端隐藏按钮。

主指标从 item 终态与 quote_kind 计算，attempt 作为独立维度；单次旧数据另列来源，历史 success 不能被推断为正式报价。基于持久时间区间统计排队/执行/人工/核对/总耗时。

后端用 Decimal 输出十进制字符串；可比键包含有效技术与商业快照以及规则版本。相同筛选复用于 stats/list/history，先取最近 N 条再按观测时点升序；前值为零/未知口径时变化率为 null。

## 页面结构与交互

- 配置列表的批量入口：显式选择目标账号、数量，显示展开数/参数摘要，再提交稳定 request_id。
- 任务页：批次列表、计数、详情子项、尝试/错误、明确取消和可安全 retry；权限和允许动作由后端投影约束。
- 计划页：固定周期、目标/账号、下次触发、启停与轮次；编辑有 revision 条件，暂停和取消分开。
- 原结果页：增加 batch/round/quote_kind/时间/比较组筛选，详细快照、金额口径和证据；按币种与可比组分系列，保留未知/无价格状态。

轮询串行并检查 generation，离开页面中止读请求/释放图表和 Blob；页面关闭不发批次 cancel。现有单次报价对话框关闭协议保持原行为。人工操作沿用原 Run API，不开放任意 DOM/脚本操作。

## 私有证据

截图服务先授权结果记录，再通过证据 ID 解析受控私有根目录；路径解析后校验 containment，返回 no-store。新证据写私有目录，前端带认证取 Blob 后创建 object URL，不直接拼公共静态路径。

旧 static/upload 历史证据先建立可审阅迁移清单：验证归属与文件哈希，迁入私有目录并更新引用，确认后移除原公共副本；不得直接删除未核对证据。迁移和清理需单独记录。本轮当前只规划，不移动任何截图。

## 兼容与回滚

新增查询字段可选，旧 Run/result 保持可读；缺失比较字段为 unknown。运行同一个后端接口时尽量采用兼容字段扩展；旧 API 消费方在实施前检索并同步。

回滚关闭新菜单/筛选和私有新入口前先验证已有数据仍可读；不得重新开放公共证据访问作为降级方式。保留历史记录与迁移清单。

