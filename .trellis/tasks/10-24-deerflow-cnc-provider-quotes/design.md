# 双平台报价技术设计（源码融合方案）

> 2026-10-29 修订：DeerFlow 必要 Agent 源码按当前 FastAPI 架构适配，本轮只改计划。领域工具从本地 Agent 直接调用现有 CNC Service，不调用 DeerFlowClient/Gateway 或本机 HTTP/MCP。复用当前 app/modules/cnc 的实现，仅补实际缺口；前置为本地图、身份/模型、技能/checkpoint 与真实异步停止验证，见 [源码融合依据](../10-24-deerflow-cnc-agent/research/source-integration-replan-2026-10-29.md)。


## 边界与端口

实现 [共享契约](../10-24-deerflow-cnc-agent/research/local-contracts.md) 的报价、凭证与恢复部分。首先复核 app/modules/cnc/quote、login、recovery、browser 及 cnc_quote_result 的当前实现与各平台任务交付，保留 QuoteService/QuoteActivity、现有平台执行路径、登录所有者/租约和 Run/Intent。平台端口只补未满足的验收缺口，不重复实现或注册已存在适配器；数据库 JSON、技能文本不作为可执行配置。

Agent 工具放在 ai/agent/tools/，用当前 AuthSchema 与业务 ID 直接调用 QuoteService 的准入/查询/命令服务。每次重查领域权限，工具不获取 Page、凭据或任意脚本权限；原生异步工具受生成取消与领域准入的边界约束。技能资源与目录来自 Lead 的单一只读 SkillCatalog。

适配器只接收冻结快照、当前 Run 与受控 Page 端口。依次完成身份验证、文件回执、几何体关联、参数保存/回读、当次价格/工期提取。文件使用原始不可变 Buffer 和本地哈希，远端不提供的标识不能假造。平台上限、域名/上传出口、材料/表面处理映射来自本次线上观测；不沿用未验证选择器或匿名演示入口。

## 启用与分类

Xometry US 先通过单项门禁后启用，嘉立创随后独立验证。验证包括普通已认证路径、已授权 STEP、文件特定声明、精确参数回读、价格来源及仅报价终点。会产生询价外联/订单的动作不属于本适配范围；没有安全的正式路径时保持阻塞。

正式报价仍经 validate_quote，并保留 Decimal 金额、币种/计价范围及 LeadTime 原始语义。嘉立创 REFERENCE_ESTIMATE 与 PENDING_REVIEW 经独立 ProvisionalQuote 分支，不转成 QUOTED；缺价格不能推断待审核。未知映射、模糊热处理或工期含义停止自动化，不让模型猜测。

## 恢复与重放防护

复用 CNC 领域 Run/Intent 中先持久化 claim 再执行一次的 mutation 包装。读取超时有界重试，写操作丢响应只能核验当前回执/页面关联，不再次上传或保存。补充跨新 Run 的未结清范围检查：相同操作者、平台账号、源文件/目标配置范围内的未结清副作用在准入前阻止新写入，不能以新 request UUID 或工具调用 ID 绕过。已存在历史不确定样本先通过权威记录只读对账。

凭证失效可走现有登录/人工流程；恢复时保持原 Run/页面关联。未知 DOM、所有者丢失、权限撤销、超时或进程重启输出固定可操作原因。只能做已验证的只读恢复；没有活动所有者时不承诺自动接管。模型诊断仅得到脱敏摘要/允许动作，不能扩大浏览器权限。

## 私有凭证

优先复核 cnc_quote_result 的现有 evidence 字段、受权 screenshot 路由和 evidence.py；复用可用部分，只补私有存储/完整性/原子发布的实际缺口，不另建重复凭证体系。凭证绑定 actor、quote_run、文件哈希、参数代次、捕获时间和适配器版本。捕获报价区域并在入库前遮盖账户/秘密，无法可靠脱敏则不保存该图并标记存证失败；不采集登录密码表单。原始敏感图不进入公共目录或普通业务日志。

文件写入与元数据提交之间采用 staged/available 状态：只有可用图和已提交关联才发 evidence.available。结果先验证、再保存凭证/结果关联、最后发布交付成功；若价格已核验但存证失败，保留核验信息及失败原因，不重试远端报价。读取时重新校验对象/RBAC，仅返回图像流，不返回服务器路径、Cookie 或秘密远端 URL。实现阶段确定清理孤立 staged 文件的有界策略，不删除运行意图。

## 迁移与回滚

凭证元数据/必要的未结清范围索引接到实际 Alembic head，验证旧 Run/Intent 无损。每个平台独立开关；异常时停用绑定、保留登录及所有持久记录。回滚不开新 Run 补偿写入，不清空不确定 claim。真实线上验收报告关联代码版本和允许文件范围，独立于 Fixture。
