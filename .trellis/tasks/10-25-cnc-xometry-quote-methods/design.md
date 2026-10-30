# Xometry 报价方法接入设计

## 目标、缺口与变更边界

目标是从现有图纸参数配置页面执行技能的完整单配置流程。页面已经通过 `handleAutoQuote` 调用 `useAutoQuote.open`；真正缺少行为的位置是后端 `quote/providers.py` 的空适配器工厂，不能通过重复添加按钮或调用账号登录 HTTP 接口来替代。

沿用现有受控浏览器、运行/intent 表、账号选择规则和结果校验器。前端在目标 `cnc_part_config` 目录保留方法入口与阶段交互；站点 DOM 操作只在后端同一个登录 owner 中执行，浏览器 Page、账号密码和文件路径不进入前端。

本次只接入 Xometry US；不扩展其他平台、批量/定时任务、下单或支付，不重写登录/浏览器底层。除确有新增契约所需，不修改共享文件。不执行无关重构。

## 已有能力与方法复用

| 职责 | 既有实现 | 本次处理 |
| --- | --- | --- |
| 页面行入口 | `cnc_part_config/index.vue::handleAutoQuote` | 保留并接入明确的模块方法，避免重复入口 |
| 账号选择、运行轮询、关闭 | `useAutoQuote` | 继续复用；仅补所需的声明/阶段交互 |
| 登录 | `login/runtime.py::LoginManager`、`login/providers.py::LoginProvider` | 沿用同一 owner/session 与只读身份复验 |
| 文件冻结与授权 | `quote/repository.py::snapshot/source_file/validate` | 继续校验 root、size、SHA-256、授权和修订 |
| 一次变更约束 | `DurableIntentStore`、`QuoteWorkflow._mutation` | 上传、保存、报价触发分别使用既有 intent；新增声明动作也须有独立记录 |
| 报价有效性 | `validate_quote`、`QuoteActivity` | 保留金额/币种/口径/参数/几何/新鲜度校验与结果落库顺序 |

直接从页面先调用账号登录 API 再启动报价可能造成账号浏览器争用。页面因此继续发起报价运行，由该运行复用已存在的登录 owner 或恢复加密会话。用户在账号管理中已完成的有效登录应免重复提交密码。

恢复实施时发现实际登录复用缺口：当前 Xometry `/v2/users/me` 身份匹配，但报价首页仍展示明确的登录要求且原生新报价按钮禁用。补充 `login/providers.py::LoginProvider.verify` 的只读负向就绪检查：身份匹配仍为必要条件；有明确当前登录阻断时不能返回已就绪，交由既有 LoginManager 登录流程处理。允许有界只读等待初始页面加载，正常已登录页面继续复用；不在 verify 中导航、提交凭据或另开会话。该项只修复当前 Xometry 信号，保留并行 JLC 逻辑和生产 binding 门槛。

本次接续的受控新上下文又确认：真实账号/密码各提交一次后，网站成功回跳报价页，但最后一个按钮的 8 秒等待先超时，`submit` 返回 false，既有 owner 因此没有核对迟到的成功结果。最小修复位于 Xometry `LoginProvider.submit` 的超时分支：最多三次有界、同一 Page 的只读核对，仅在报价路径已完成加载、当前可见原生 My Account 控件明确就绪且无显式登录/验证阻断后，再要求原有身份接口精确匹配；成功才返回 true。不得导航、重复提交账号密码、修改 cookies 或把空壳/回调/密码页当成成功。`runtime.py` 与 JLC 超时行为不改，原本有效的登录复用不经过该分支。对应测试限于 provider 与实际本地 Chromium 的就绪/迟到结果回归。

2026-10-26 实测与独立复核还确认了正常提交分支的相同缺口：`_submit` 返回 true 时，首页仍是无控件的加载空壳，identity-only 检查通过后 owner 再次导航，稍后页面仍显示 guest。将上述 Xometry 只读完成核对同时用于正常成功提交，原始 false 仍返回 false；一个真实提交最多调用一次，不能为了等界面而重发密码。复用同一核对方法和原有有界预算，保留身份必需、启用的唯一原生账号控件、挑战/登录阻断检查及身份核对后的 UI 重读。只改 provider 和针对性回归，不扩大到 runtime、既有恢复会话判断或 JLC；这个修复阻止空壳误报，不声称已修好当前官网的新旧登录衔接。

## 预期文件边界

2026-10-26 本次接续的原生入口修订：当前官方 header chunk `c5ab5fec30a829d4.js` 的 `navigateToAuthHostLogin` 使用 `https://xometry.com/login`；历史受控证据表明产品固定 `/account/login/` 兜底可落在无登录控件的错误页面。仅将 `LoginProvider._submit` 中该固定兜底替换为官方原生固定入口；已经位于 `login.xometry.com` 的 hosted form 继续原样复用。不猜测 callback/token API，不写入或转移 cookies，不扩展 runtime、信任主机或报价 binding。新增入口回归须验证一次导航、hosted identifier/password 各提交一次以及正常 false、timeout、最终就绪核对行为兼容。这修正过时入口，但真实新旧身份桥接仍以实测为准。

- `frontend/web/src/views/module_cnc/cnc_part_config/index.vue`：目标模块的发起、继续、停止方法及弹窗事件连接。保留现有权限和 CRUD。
- 同目录 `useAutoQuote.ts`、`AutoQuoteDialog.vue`、`quoteMessages.ts`：按需补充 Xometry 声明确认、阶段说明与固定原因，不复制账号登录 composable。
- `frontend/web/src/api/module_cnc/cnc_part_config.ts`：只有新增固定类型声明确认契约时扩展；现有七个报价接口保持兼容。
- 新增 `backend/app/modules/cnc/quote/xometry.py`：实现可信的 Xometry adapter 及站点方法，不读取历史平台 JSON 作为可执行 locator 配置。
- `backend/app/modules/cnc/quote/providers.py`：按 `snapshot.provider_code` 和可信入口选择 Xometry binding，保留其他平台行为。
- `backend/app/modules/cnc/quote/{runner,contracts,repository,service,routes}.py`：仅扩展声明记录、人工继续与未确认回执核对所必需的状态/命令。
- `backend/app/modules/cnc/login/runtime.py`、`browser/contracts.py`：仅在固定声明命令或 receipt 需要时做最小兼容扩展，回归既有登录/浏览器契约。
- `backend/app/modules/cnc/login/providers.py` 与对应 login 测试：按上述当前页面证据修复 Xometry 显式登录阻断下的错误就绪判断，不重写现有登录。
- `backend/tests/cnc/quote/`、相关前端现有测试：覆盖真实方法的关键边界及回归。
- `.trellis/spec/backend/cnc-auto-quote.md` 与 frontend 对应文档：记录最终生效的方法和契约。

优先复用现有 JSON 字段持久保存最小声明证据和远端回执，不新建表或修改数据库结构。若实施发现必须迁移，先说明原因并修订设计。

## 数据流

1. `handleAutoQuote(row)` → composable 读取可用账号 → `startQuote(config_id, account_id, request_id)`。
2. 服务端重读并冻结配置/图纸/账号，保留当前权限、版本、完整参数和文件字节；复用已有持久 run，不自动重试 POST。
3. `LoginManager` 在受控会话中验证账号；有效会话直接进入报价，挑战显示同一页面并等待用户。
4. `QuoteActivity` 取得 Xometry adapter，依次调用上传、解析核对、参数设置、保存回读、当前报价读取方法。
5. 每次上传、保存和报价触发先提交 durable intent；仅持有当前账号租约和输入版本的 owner 可执行。超时只进入有界只读核对。
6. 验证同次文件、零件、参数、geometry 和价格证据，提交结果记录后返回完成；前端轮询并显示其实际性质。

## Xometry 站点方法

接口沿用 `PlatformAdapter` 的 `authenticate/upload/configure/read_effective/submit/extract_quote/reconcile`。内部按下列职责拆分，具体私有方法名可随实现调整：

- `inspect_page`：核对可信主机和页面变体、当前可见控件唯一性；公开 testdrive 和历史 `vercel_part_config=test` 不能代替正式报价页面。
- `upload_verified_step`：在当前正式主 CAD input 使用官方 helper 发送冻结缓冲，最多一次；不能用附加文件或 Update CAD 控件替代。保留本次请求到远端零件的可核对关联。
- `read_parsed_part`：有界只读等待分类/解析，建立正数几何和 remote part receipt；只有文件名或 ready 数量不够。
- `read_export_declaration/continue_declaration`：发现声明则暂停；只接受与本次文件和当前声明内容绑定的明确选择。执行 Continue 前持久记录决策和独立变更意图。
- `apply_parameters/save_configuration`：先校验全部参数可支持，再按依赖顺序设置工艺、精确材料标题、表面处理、数量及适用 extras；重新观察依赖选项，不持久化生成式 option ID。
- `read_saved_parameters`：保存完成后重读平台有效值，与完整 requested 比较；保留 alloy/temper/product-form 差异，不把 AL6061 自动映射到任意 6061 选项。
- `read_current_quote`：确认保存/重算回执，读取该零件、参数 generation 下的新鲜结果和原始交期。若保存已自动重算，不能为了凑 submit 阶段再点击一次保存。
- `reconcile_operation`：只读核对已声明操作对应的真实 receipt；无法核对即保持明确阻断，不清除 claim 或换 run 重发。

所有方法只操作报价范围。Checkout、Order、Forward to Purchaser、支付等不属于 adapter 行为。金额缺失不能推断成待审核，`$` 不能独立确定 USD。

## 人工声明与继续的最小契约

现有通用坐标输入不能单独表达可持久审查的出口声明决策。如正式页面需要该声明，增加 run 绑定的固定类型声明确认命令，包含当前声明版本和用户选项；文件 SHA-256、actor、run 和决策时间由服务端填写。前端展示当前完整声明及绑定文件，不预选、不据文件名推断。

声明文本或绑定文件变化使旧决策失效。决策先写入既有 run 私有记录，再由同一 owner 执行对应页面操作；不能将页面的选择结果反推为用户授权。用户已经给过且经核对仍适用的精确范围决定可复用，无需重复询问。

普通登录验证继续使用现有 resume；声明确认只在对应 WAITING_HUMAN 阶段接受。新增字段保持可选，其他平台及现有消费者无需提供。人工等待时显示阶段原因，自动阶段禁止并发人工改参。

## 正式页面证据与激活

实施首先核对当前正常托管报价页面的主 CAD 控件/限制、完整参数语义、保存回执、几何来源、同次当前价格/币种/口径。历史研究是候选信息，不是激活凭证；当前技能也不单独授权生产注册。

2026-10-25 当前官网部署源码进一步确认：`vercel_part_config` 属于 `bx_part_config_v2` 的参数编辑器实验路由，原生 dashboard 链接会携带该键；不能仅凭查询键判定为公共 testdrive。将原先对该键的一律拒绝收窄为 binding 显式声明的页面变体门槛：默认 binding 继续拒绝；只有由当前官方来源明确核对的 V2 binding 可以接受唯一、精确的 `vercel_part_config=test`，其他值或重复值仍拒绝。公共 `/testdrive/`、错误主机和无同次文件/参数/回执依据的历史结果继续拒绝。该修订只使真实部署变体可被准确描述，不启用生产 binding，也不降低完整上传、回读及结果验收要求。证据见 `research/site-auth-source-2026-10-25.md`。

方法实现与隔离测试可推进，但生产 binding 的启用必须建立在上述核验结果上。未核实则保留固定、可说明的阻断，并在交付中明确实际缺口；不能继续以工厂永远返回 None 却宣称功能已接通。真实条件受阻时不把合成结果计入真实验收。

此前 `e8dea2c1-3430-4279-832e-1e655ced79b8` 的 uncertain upload 保留，不能用于自动重新上传。历史 quote `Q59-6980-1120` 数量为 5，不是当前数量 1 的目标结果；不自动复用/修改该历史 quote 来绕过不确定上传。

## 兼容、测试与回滚

保留现有七个报价接口和状态、金额字符串、账号权限与同 owner 生命周期。新增原因走 allowlist 中文映射，不显示原始异常、敏感 DOM、URL 或凭据。新 receipt/命令扩展必须可读取既有运行与 intent。

验证顺序：实际 adapter 的隔离 DOM/receipt 测试 → 持久 run/intent 和登录 owner 集成回归 → 页面交互/类型/构建 → 已获授权且可核对的正式站点验证。测试成功与真实报价成功分别记录。

回滚停止新 Xometry 运行并关闭新增 binding，保留 durable run、声明决策、回执和 uncertain intent；保留原有登录和配置管理。无本机网络改动或数据清理。

## 规划状态

需求和用户范围已由原请求及本轮同意覆盖。用户在最终摘要后明确批准实施，任务于 2026-10-25 进入 in_progress。正式 DOM、回执和当前价格提取属于实施期技术核验项；具体测试配置与文件声明决定属于该次报价运行，不预先代用户作答。目前方法实现及独立检查正在进行，生产绑定与真实站点验收尚未完成。
