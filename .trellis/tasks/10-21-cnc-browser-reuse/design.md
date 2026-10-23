# BR 设计

权威设计：[docs/browser-implementation-design.md](../../../docs/browser-implementation-design.md)。证据：[源码分析](../../../docs/browser-reference-analysis.md)。本项只交付共用组件，01–05 的平台业务/调度/Agent/UI 依赖不变。

变更边界：新增 backend/app/modules/cnc/browser、对应独立测试、optional browser 依赖与锁文件、文档和相关 Trellis 要求。直接 SDK 优先，单独复用 DeerFlow MIT 出站组件；不重写 Ref/CDP/上传协议，不移植两个框架，不开启 draft 平台。

使用服务端 scope、加密内存会话、精确域/连接固定、官方上传及确定性适配器；注入业务 IntentStore，未知副作用不重发。平台接入需要真实持久仓储/ACL/参数/几何/真价/证据及全部原 gates。具体 contracts、故障矩阵、生命周期、数据流、兼容/回滚与验收映射见权威设计。

用户已明确授权本轮创建并推进实现；规划已按原始范围收敛，无额外产品选择。保留原任务状态和历史；依赖 DAG 无环，审计基线在 research/task-baseline.json。
