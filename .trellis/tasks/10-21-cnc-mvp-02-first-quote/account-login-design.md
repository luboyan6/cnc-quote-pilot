# D-18：账号列表受控浏览器登录

## Goal and confirmed choice

2026-10-22 用户答复“听你的推荐即可”，选择受控浏览器方案：用户看到的平台页面与服务端登录使用同一隔离会话，不转移登录态到本机普通新标签页。沿用已有 02/03/05 任务，不创建重复任务。本文件是本增补的集中技术设计；原完整报价、两平台真价和延期 RapidDirect 的验收要求保持。

本次交付边界为账号列表 → 登录/复用 → 可视平台页，不自动上传 STEP、配置或提交报价，不包含异常 Agent、批量、定时或完整报价 runner。建议将此登录切片先行交付；它的登录/权限/安全/平台实测单独验收，不宣称通过原报价 E2/E3。原报价研发顺序和 live gates 继续用于完整报价链路。

## Evidence and reuse

- `frontend/web/src/views/module_cnc/cnc_account/index.vue` 的 handleAutoLogin 是占位；复用现有表格操作及 Element Plus 对话框。
- `backend/app/plugin/module_cnc/cnc_account/` 与 `cnc_platform/` 已有 CRUD。平台当前模型仅有 name/login_url/quote_entry_url，不能假设已有 code/enabled/受信注册字段；平台识别须由服务端固定注册表与精确入口域匹配，不凭显示名称授权。
- 共用 BrowserExecutor 固定 headless，BrowserSession 强制当前 asyncio task 所有权；不能在各 HTTP handler 中直接操作或退出其他 task 创建的会话。复用其官方 SDK、出站策略、scope、加密状态和释放逻辑。
- OutSchema 当前继承写模型，包含 password 和密文；导出映射同样有秘密字段。读写模型拆分和导出脱敏属于本切片前置。OperationLogRoute 会采集 JSON 请求/响应；画面及用户输入不能进入通用操作日志正文。
- 官方依据：[Page screenshot](https://playwright.dev/python/docs/api/class-page#page-screenshot)、[身份状态复用](https://playwright.dev/python/docs/auth#reusing-signed-in-state)。采用已锁定 SDK 的 public screenshot/mouse/keyboard/storage_state 方法，不依赖新版 screencast 或自建 CDP/Ref/上传协议。

## UX and state contract

点击行按钮后打开“平台登录”对话框，展示所属平台、脱敏账号和准备/登录/验证/已登录/需人工处理/失败状态。行按钮 loading 防止同一账号重复请求；已有活动窗口优先重用并重新核验身份，不重复创建或提交凭据。

页面使用固定 1280×720 viewport 的 JPEG 画面，串行轮询约每 1.5 秒一次；缩放画面按实际尺寸换算点击坐标。提供键盘/文本输入和滚动，让已授权账号持有人处理平台挑战及浏览业务页。页面内容是私有业务画面，不发送模型、不记录截图/输入正文、不公开静态文件；自动化只执行登录及导航，不自动操作下单/支付。

状态为 STARTING、AUTHENTICATING、READY、WAITING_HUMAN、FAILED、CLOSED。READY 仅在业务页及目标身份核验成功后设置。WAITING_HUMAN 明确显示处理要求，人工处理后点击“验证登录”执行身份复验，不能凭用户关闭弹窗、存在 Cookie 或数据库 VALID 变 READY。未知页面/身份不符明确失败或待人工，不试猜定位器。

## API and permission boundary

在现有账号 router/service 下接入，固定前缀 `/cnc/cnc_account`：

| Method/path | Contract |
| --- | --- |
| POST `/login/{id}` | 输入仅账号 ID；校验对象权限、启用、平台入口和支持范围，创建或复用会话；返回会话 ID、平台/账号显示值、状态、固定原因及是否复用，不返回凭据/状态密文 |
| GET `/login/{id}/sessions/{session_id}` | 返回脱敏状态、viewport、过期时间；不透传 token-bearing URL |
| GET `/login/{id}/sessions/{session_id}/frame` | 当前 JPEG 二进制，Cache-Control: no-store；无画面时返回类型化状态，不能缓存旧账号画面 |
| POST `/login/{id}/sessions/{session_id}/input` | 严格枚举 click/scroll/key/text；坐标、长度、频率和队列有界，不接受 JS、locator、文件路径或任意 URL；输入仅发往当前会话 |
| POST `/login/{id}/sessions/{session_id}/verify` | 人工处理后复验目标身份，成功才加密保存会话并进入询价页 |
| DELETE `/login/{id}/sessions/{session_id}` | owner 关闭；幂等清理，不删除持久认证状态 |

使用既有账号 detail/update 权限约束，登录/输入/验证/关闭需要 update，状态/画面也要求同一 owner 与相同权限；每次访问重新查对象授权及 enabled，停用/删除/凭据变更撤销活动会话。随机会话 ID 只是引用，不能代替后台认证。画面/输入采用不采集正文的路由，仅审计 actor/account/action/status 元信息；创建/编辑及导出路径同样禁止秘密回显。

## Ownership, persistence and lifecycle

一个后台 owner task 独占 BrowserExecutor session，串行执行受限命令队列。HTTP handler 校验权限后提交命令，不跨 task 访问 Page；超时、取消、排队失败不自动重发登录或输入。命令完成/取消/关闭都必须结算 future，不能留挂起请求。

账号持久租约采用条件更新和 fencing token，启动前取得并独立提交；周期续期失败停止会话。owner_id/platform_code/account_id 绑定加密状态。多进程会话由创建它的进程持有，其他进程返回明确会话不可达/忙碌，绝不另建同账号窗口；部署文档明确需要登录会话粘性路由，跨进程失效仍受持久租约保护。

默认空闲 5 分钟、最长 30 分钟；画面轮询不延长用户空闲，仅人工输入/验证计活动。关闭弹窗/离开页面尽力关闭，服务器超时是兜底；停服取消 owner task 并完整释放 SDK context/browser/proxy、队列和租约。持久有效会话按现有 CryptoUtil/SessionCodec 保存，下一次创建 context 后仍须验证身份。屏幕内存仅保留最新画面并在关闭时清除。

## Credentials, providers and failure handling

写入凭据使用 CryptoUtil 加密到 credential_ciphertext；现有 NOT NULL password 列迁移期间只存空占位，读旧明文仅作受控兼容并在更新/登录时迁入密文。密码留空更新保留原值，用户名/平台/密码变化清空旧会话；外部请求不能写 session/lease/fingerprint 等内部字段。查询、导出及日志均不包含 password/密文，导入仍走相同加密写入服务。

服务端以关联平台 login_url/quote_entry_url 为地址源，以受信注册表验证 HTTPS/443、精确主机和平台归属，使用现有 BrowserPolicy/代理做实际出站校验。缺地址、未知平台、非信任域在启动/提交凭据前拒绝。不能把账号旧 login_url 覆盖平台配置。

顺序为 Xometry US、嘉立创 CNC，RapidDirect 保持延期。每站先只读核对真实登录页/跳转域/业务页身份标记，记录可信 locator 与身份判定；未核验的站点明确“不支持/待验证”，不使用通用猜测自动提交。draft 报价配置保持禁用；只启用已验证的登录路径，不连带启用上传/报价适配器。现有已登录页面只能用于观察，不能替代从凭据首次登录、恢复及挑战分支的产品验收。

依赖缺失、浏览器不可用、出站拒绝、租约冲突、配置错误、登录失败和挑战均返回固定脱敏原因；不透传 SDK 异常、DOM、完整 URL 或截图到日志。自动重登最多一次，挑战不绕过，输入回执不明不重发。

## Validation and rollback

- 后端：离线单元/合成 Chromium 验证 owner/账号隔离、权限撤销、入口拒绝、实际身份复验、有效状态免提交、失效重登、挑战、命令取消/超时、租约丢失、关闭/过期释放，以及响应/导出/日志无秘密。
- 前端：实际按钮调用、行级 loading、重复点击、失败/挑战、画面坐标与键盘输入、关闭/卸载清理，明确 HTTP 失败不显示已登录；定向 Vitest、type-check 和 build。
- 真实平台：各自单列首次登录、再次点击复用、关闭重建后恢复及询价页目标身份结果，挑战未完成则记待人工，不声称成功。不会为了验登录上传或提交报价。
- 回滚：关闭新增登录入口及会话服务，停止并释放活动会话；保留加密凭据/状态、租约历史及既有 CRUD 数据，不恢复秘密回显。凭据迁移需保留可读取密文的兼容能力，不能回滚为依赖旧明文。

当前状态（2026-10-23）：用户已确定受控浏览器，并在最终规划摘要后明确答复“是”。本次登录切片已按确认实施，沿用 02 激活执行，03/05 按本切片分工协作。自动化检查和合成 Chromium 通过，见 [验证记录](research/login-validation-2026-10-22.md)；真实平台认证因本机混合保留 DNS 仍未验收。完整报价、Agent 和监测的原前置仍未通过，不启用 draft 报价配置，不归档整个 02。
