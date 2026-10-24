# 产品配置自动报价 — 技术设计

## 目标与边界

从现有配置列表发起单行报价，按配置关联平台选择账号，在同一个受控会话中登录、上传、填参和读取报价，弹窗反馈结果。实施顺序为 Xometry US → 嘉立创 CNC。两站都在本次目标内；一个平台未通过真实链路时必须单独报告未完成。

这是既有浏览器与登录能力的业务集成，不另建浏览器引擎。既有完整 MVP 的异常 Agent、跨平台对比、监测及整体 E2/E3 验收继续由原任务负责；本次遇到未知页面转人工，不用通用猜测或自动模型操作替代缺失的可信平台适配。不会据此宣称原 MVP 完成。

此设计等待最终摘要确认；当前没有开始产品实现。

## 证据与复用

代码依据、文件定位、已知限制集中记录在 [existing-flow.md](research/existing-flow.md)。关键事实：site_type 在当前页面存的是平台记录 ID；配置没有账号绑定；登录浏览器必须由单一 asyncio owner task 操作；真实报价适配器与持久 intent 尚未实现。

## 用户流程

1. 在行末新增“自动报价”，保留现有操作。只对正在执行的行展示 loading，禁止同一配置重复创建活动执行。
2. 服务端按该配置的平台筛选当前用户有权操作且启用的账号。零个提示先配置；一个直接选用；多个弹窗列出别名及脱敏账号，用户选择后继续。
3. 打开报价弹窗，展示配置、平台、关联文件与阶段：准备、登录、上传、解析、设置参数、获取报价。
4. 有效登录态复验通过后继续；无效时沿用账号模块登录。验证码/MFA 等显示原受控页面并允许人工处理。点击“验证并继续”只做登录/状态复验，通过后恢复已冻结的报价执行。
5. 同一浏览器上传文件、等待模型解析、设置并回读参数，再读取或触发经核实的报价。自动阶段只读展示画面，人工输入只在 WAITING_HUMAN 开放，以免用户与自动化同时改参。
6. 成功展示平台、脱敏账号、文件名、材料、数量、表面处理、金额、币种、单价/行总价性质、交期原文、报价时间与关键差异化参数。平台返回参考估价、待审核、不可报价时显示对应性质及原因。
7. 关闭或离开页面停止自动运行，释放由该执行持有的浏览器和租约；已发送但未确认的操作保留 UNCERTAIN，不能因重开窗口而盲目重复。结果记录在服务端保留；再次点击是明确的新报价，已有活动执行则返回该执行。

## 服务端模块与所有权

- `app/modules/cnc/quote/`：新增 contracts、repository、service/runner 与 providers（xometry_us、jlc_cnc_cn）。负责配置/图纸快照、对象权限、参数映射、持久变更 intent、结果与执行状态。
- `app/modules/cnc/login/runtime.py`：保留登录入口行为，扩展受控 owner 的报价活动和有界推进能力。HTTP 只提交固定类型命令，Page 不跨 task 共享。报价独占账号，账号页在报价占用时返回明确 busy 状态，不能另开同账号活动或允许两个界面并行操作。
- `app/plugin/module_cnc/cnc_part_config/controller.py`：挂载报价子路由；只有新增私有报价路由使用脱敏审计，既有 CRUD 路由约定保留。
- `app/plugin/module_cnc/cnc_quote/` 或现有 CNC 模型发现机制支持的等效位置：注册执行/intent 持久模型；实施时核对插件模型发现机制后固定位置，不额外生成无用途的 CRUD 页面。
- `frontend/web/src/views/module_cnc/cnc_part_config/`：新增 `useAutoQuote.ts`、`AutoQuoteDialog.vue`，入口调用现有操作渲染器。受控画面/输入机制尽量从账号对话框抽取共用组件，账号页回归测试必须通过。
- `frontend/web/src/api/module_cnc/cnc_part_config.ts`：增加严格类型的报价接口，保留既有 CRUD API。

## API 契约

前缀 `/cnc/cnc_part_config`，均使用当前项目标准响应 envelope；文件/画面不放入 JSON。

| 方法与路径 | 请求/响应 |
| --- | --- |
| GET `/{id}/quote/accounts` | 返回该配置对应平台的可用账号元数据，id/alias/masked_username，不返回完整凭据或状态密文 |
| POST `/{id}/quote/runs` | `{account_id?, request_id}`；request_id 是一次用户点击产生的 UUID，用于同次请求去重。省略账号仅在恰有一个可用账号时接受；多账号返回固定需选择原因；创建或返回同次 QuoteRunView |
| GET `/{id}/quote/runs/{run_id}` | 当前阶段、固定 reason、可选同次结果、是否允许人工处理 |
| GET `/{id}/quote/runs/{run_id}/frame` | 私有 JPEG/no-store，与实际报价为同一受控浏览器 |
| POST `/{id}/quote/runs/{run_id}/input` | 复用 LoginInput 严格枚举，仅 WAITING_HUMAN 接受 |
| POST `/{id}/quote/runs/{run_id}/resume` | 无自定义脚本或参数；重新验证身份/页面状态及运行所有权，继续同一运行，禁止隐式重发已声明变更 |
| DELETE `/{id}/quote/runs/{run_id}` | 停止、释放并返回最终状态；终态幂等，保留结果与 intent |

QuoteRunView：run_id、config_id、account_id、platform_name、masked_username、file_name、status、stage、reason、viewport、expires_at、result。结果金额为十进制字符串，price_scope 为 unit/line；税运未知为 null，不自行猜测总价或折扣。交期沿用已有 LeadTime 的类型/原文，不把到货日期折算成生产天数。只返回脱敏快照，不公开 token URL、原始 DOM、服务器路径或私有证据存储键。

状态：STARTING / AUTHENTICATING / RUNNING / WAITING_HUMAN / QUOTED / REFERENCE_ESTIMATE / PENDING_REVIEW / FAILED / CANCELLED。RUNNING 的 stage 分别表示 upload、parse、configure、quote、persist；只有已有 validate_quote 接受且证据/结果落库后才是 QUOTED。参考估价走独立类型与持久化分支，不能作为 ValidatedQuote。人工审核的状态只读回平台实际反馈；未知不能推断为审核中。

## 权限与输入边界

- 列出配置账号需配置 query/detail 与账号 query 权限；发起、查看私有画面、继续和停止需配置 update 及现有账号 update 权限，前端与后端同时遵守。结果查询仍验证运行 actor 和配置可访问性，随机 run_id 不授予权限。
- 服务端重读配置、平台、图纸与账号，核对 enabled、未删除、对象权限、账号平台等于配置 site_type。普通用户不能使用他人账号；超级用户也不能接管其他 actor 的活动浏览器。
- 运行前根据已有图纸上传授权字段核验第三方上传许可；缺失或未授权时明确提示修正图纸配置，不静默将 false 改成 true。文件只从服务端受信存储根解析，拒绝远端 URL、路径穿越、失效文件和格式不符。
- 冻结完整配置、文件 size/SHA-256、provider/config/adapter 版本。开始前和每个远端变更前检查对象修订与权限/租约；被禁用、删除或绑定改变则停止，不将新值混进当前运行。

## 会话、并发与持久化

复用 LoginRepository 的 actor/owner/revision 检查与 60 秒 fencing lease。登录 READY 后保留同一 Page；报价中身份复验使用只读 provider.verify，不能调用会导航回入口的整个 `_verify`。

owner task 按有界阶段推进，阶段/单次 SDK 调用通常不超过 15 秒，等待解析通过短只读观察推进；阶段间结算控制命令和 lease 续期。接口立即返回引用，前端串行轮询，不用长 HTTP 请求等待整次报价。不创建跨 task 操作同一 Page 的 quote runner；终止取消和 future 结算沿用原清理约定。报价自动推进计入有效活动，但整体仍受 30 分钟上限约束；人工等待沿用空闲上限。

新增最小持久表：

- quote_run：UUID run_id、actor/owner、config/part/platform/account ID、request_id、冻结输入与版本/hash、阶段/状态/固定原因、文件 hash、requested/effective、结果与必要私有证据引用、时间和乐观修订。`(actor_id, config_id, request_id)` 唯一，防网络重复创建。同配置的活动执行通过事务锁串行判定；同账号再由持久租约互斥。
- quote_intent：scope、run/item、generation、operation、fingerprint、CLAIMED/CONFIRMED/UNCERTAIN、已确认回执；唯一键符合 IntentStore 协议。claim 独立提交成功后才允许上传/Apply/报价触发；写回失败不释放 claim 来自动重试。

结果、有效参数和必要私有证据先持久化再向前端报完成。证据仅限授权私有读取，结果弹窗不要求展示平台整页截图。重启后非终态转待核对/人工，不重发 claimed 变更；本次不实现跨进程无人工自动恢复。服务多 worker 时遵守既有会话粘性部署限制。

## 平台适配与门槛

1. 先核对已有研究与当前真实页面，确认可信域、正式上传控件、文件限制、解析结果/远端零件身份、参数选项及依赖、保存/Apply 后完整回读。
2. provider 注册来自可信精确入口域，绝不使用 site_type=1/2 或平台显示名称决定适配器。历史 JSON 仅作研究，未验证映射不能启用；正式配置固定版本并校验，无任意 JS、动态 import 或用户提供 locator。
3. material/surface_finish 与 extra_params 必须通过该站精确映射。依赖变化重读选项，不模糊匹配或丢弃未知键；缺必要加工参数进入可说明的人工处理。保留 requested/effective 和平台原文。
4. 通过官方 set_input_files/file chooser helper 上传已核验字节；上传、Apply 与报价触发分别建立 intent。只对已审查的只读观察有限重试。
5. 报价按钮只在明确无购物车/订单/支付副作用时开放。JLC 若页面只有系统预估金额，则按 REFERENCE_ESTIMATE 返回；人工审核入口若副作用未核实，在点击前停止并显示原因，不能为了得到真价而下单。
6. 金额、币种、口径、交期、文件身份、几何、参数、报价回执与新鲜度都属于同一次执行；满足共用验证器后才可 QUOTED。历史页面存在零件或价格不能通过当前运行的真实验收。

网络、真实控件/参数与价格解析仍需实施期核验。它们是开启对应平台自动操作的内部技术门槛，不是让用户提供定位器的前置问题。无法完成时如实保留阻断记录，本次功能不能以假数据或仅按钮完成交付。

### 2026-10-23 用户确认的 DNS 契约修订

接续实测发现 Antigravity 的已验证登录修复采用地址过滤，与此前全答案拒绝规范冲突。核对同项目会话后，用户明确选择“保留 Antigravity 的地址过滤方案；同步调整契约和验证”。因此 `BrowserPolicy.resolve` 保留去重后的合格 IP，排除非 global/private/reserved/link-local/loopback/multicast/unspecified/IPv6 site-local 候选；混合回答有合格候选即可继续，无合格候选、空/畸形回答及解析故障仍用固定原因拒绝。SOCKS 连接器仅接收这些固定 IP，不重新解析域名或尝试被排除地址。精确主机、HTTPS/443、可选资源拒绝、同 owner 与文件/intent 规则保持。地址分类不能将本机 Fake-IP 直接证明为真实平台公网地址。

此前严格方案的测试结果作为历史候选记录保留；最终验收使用已确认的过滤契约和对应负向回归，不以删除出站约束或生成价格替代真实平台证据。此项明确决定允许修订 DNS 选址契约，不授权修改本机 DNS/代理设置、删除 uncertain intent 或启用未验证适配器。

## 兼容、发布与回滚

使用增量迁移，仅新增报价持久表和必要索引；不重写账号/图纸/平台既有结构，不增加永久账号绑定。生成迁移前比较当前用户未提交 Alembic 变更，避免迁移链冲突。

发布先迁移，后启用已通过证据门槛的适配器。回滚时停止新运行和活动浏览器、关闭报价入口，保留执行记录、加密认证状态与 intent；不清理未知远端回执来强行恢复，不修改出站安全策略。
