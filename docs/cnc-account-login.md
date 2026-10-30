# CNC 账号自动登录

账号列表的“自动登录”会打开受控浏览器窗口。已有有效会话时先核对目标账号，再进入关联平台的询价页；会话失效时执行一次平台登录。有验证码或页面无法识别时停在人工处理状态，用户可在窗口中操作并点击“验证登录”。浏览器画面与登录使用同一会话，不会转交 Cookie 给本机普通新标签页。

## 使用与配置

1. 在竞价平台中填写当前登录地址和询价地址，再给账号关联该平台。Xometry 的已观察登录入口为 `https://www.xometry.com/account/login/`，询价页为 `https://www.xometry.com/quoting/home/`；嘉立创 CNC 询价入口为 `https://www.jlc-cnc.com/cncOrder/#/placeOrder`，登录通过该页原生 CAS 窗口完成。服务端只支持这两个平台的受信入口，RapidDirect 仍延期。
2. 账号须启用，当前用户须具有账号修改权限及对象访问权。普通用户只访问自己创建的账号，管理员可管理账号；活动窗口仍绑定发起人。
3. 点击“自动登录”。窗口可点击、输入文本、发送按键和滚动；需要人工处理时，完成后点击“验证登录”。身份不一致不会显示成功。当前画面交互不是完整远程桌面，不支持文件上传、拖拽或系统剪贴板。
4. 关闭窗口或离开页面会请求释放浏览器；服务端在空闲 5 分钟或最长 30 分钟后兜底释放。已验证的认证状态加密保存，下次打开仍实际复验。修改账号/平台/密码或停用账号会撤销旧活动。
5. 编辑密码留空表示保留原密码。查询/导出不返回密码或凭据/会话密文；新增、修改和 Excel 导入使用项目已有 `CryptoUtil`（Fernet）将账号、密码加密存入 `credential_ciphertext`，旧 `password` 字段清空。平台登录时仅在后端解密并交给登录流程，前端无需读取或解密已保存密码。

## 历史密码迁移

后台用户登录使用不可逆的 PBKDF2 密码哈希；第三方平台自动登录需要还原密码，因此使用可逆的 `CryptoUtil` 加密。密钥优先使用 `DATA_ENCRYPTION_KEY`，未配置时由 `SECRET_KEY` 派生，旧密钥由 `DATA_ENCRYPTION_OLD_KEYS` 保留供轮换使用。

历史账号在编辑或登录时会迁移并清空遗留明文；对于尚未使用、已停用或已软删除的账号，可在 `backend/` 目录执行一次性迁移：

```powershell
# 仅检查，不修改数据库；输出记录数量，不显示账号或密码
.venv/Scripts/python.exe scripts/encrypt_cnc_account_passwords.py

# 使用当前后端数据库及密钥配置，将历史密码加密并清空明文字段
.venv/Scripts/python.exe scripts/encrypt_cnc_account_passwords.py --apply
```

迁移可重复执行，所有写入在同一事务中完成。已有密文会先验证且保持原样，再清理残留明文；密文无法解密时整次迁移回滚，不使用旧明文覆盖密文。执行时应暂停账号编辑和登录，避免活动登录引用的凭据版本发生变化。妥善保留加密密钥，丢失密钥后无法恢复已保存密码。

## 运行要求

- 使用项目已有 Playwright browser extra 和匹配浏览器，安装方式见 [浏览器运行说明](browser-runtime-setup.md)。本次合成验证使用工作区 managed Headless Shell，通过 `PLAYWRIGHT_BROWSERS_PATH` 指定，不连接个人 Chrome。
- Windows 请用项目 `main.py run` 启动，它已为 Uvicorn 配置支持 Playwright 子进程的 Proactor 循环；使用其他 Uvicorn 入口时需显式加 `--loop app.core.server_loop:subprocess_event_loop`。当前版本的 Windows 默认 reload/多 worker 循环不能启动该子进程。非 Windows 启动方式保持不变。
- 保持现有 CryptoUtil 加密密钥及轮换配置，勿丢失旧密钥。数据库沿用账号表已有 credential/session/lease 字段，不新增表结构迁移；历史密码的数据迁移命令见上文。
- 数据库语句日志隐藏绑定值；`DATABASE_ECHO=debug` 只保留语句级输出，不回显查询结果行。不要启用数据库驱动 DEBUG，避免在驱动层记录账号内容。
- 当前受控浏览器由创建它的 worker 持有。使用单个登录 worker，或按账号配置固定路由；跨 worker 请求会明确失败，不创建重复窗口。
- 浏览器必须能够获得并连接平台的真实公网 DNS 地址。未知地址、非 HTTPS、私网依然被严格拒绝（混合 DNS 中的合规公网地址安全保留，详见 [登录故障排查与修复说明](troubleshooting-account-login-browser-failed.md)）；不要通过关闭安全校验修复连通性。

## 平台登录流程差异

登录不是「填两个框点提交」的通用动作：各平台的入口、认证域和风控各不相同。适配集中在 `backend/app/modules/cnc/login/providers.py`，由 `resolve_provider` 按账号所属平台选取，上层运行时（`runtime.py`）不感知差异。

| | Xometry（`xometry_us`） | 嘉立创中国（`jlc_cnc_cn`） | 择幂中国（`xometry_asia`） |
| --- | --- | --- | --- |
| 入口 | 报价页跳转到 `auth.xometry.com` 同源登录页 | 报价页右上 `button.login-button`，在 `iframe#jlc-cas-login-window` 内嵌 CAS | 独立页 `get.xometry.asia/sign_in`；未登录访问 `/quotes` 会被重定向回来 |
| 默认态 | 直接是账号密码表单 | 默认停在**二维码** tab，必须先点「账号登录」 | 默认停在**手机号 + 短信验证码** tab，必须先点「通过邮箱登录」 |
| 前置干扰 | 无 | driver.js 新手引导遮罩会拦截点击 | 无（新手引导只在 `/dashboard`，登录页与 `/quotes` 没有） |
| 风控 | 无 | 可选阿里云滑块，失败会重置 | 腾讯验证码 + 顶象指纹 SDK 会加载，但**拦掉不影响登录** |
| 必填同意项 | 无 | 无 | 「我已审阅并同意…条款」默认**未勾选**，不勾选提交无效 |
| 身份回显 | 接口回显登录标识，可直接比对 | `queryLoginUser` 只返回 `customerCode`，**不回显手机号/邮箱** | GraphQL `getMe` 回显 `email` 与 `phone`，可直接比对 |
| 身份接口 | REST `GET api.xometry.com/v2/users/me` | REST `GET .../queryLoginUser` | GraphQL `POST api.xometry.asia/get/graphql`（`getMe`），未登录返回 401 |

### 择幂中国登录方法

1. 打开 `https://get.xometry.asia/sign_in`，点「通过邮箱登录」tab。
   `input#password` **只在这个 tab 下存在**；手机号 tab 只有 `input[name=phone]` 和 `#phoneKey`（验证码），直接找密码框必然失败。
2. 填 `input#email` 与 `input#password`。
3. 勾选 `#accept`（条款同意）。**不勾选时提交按钮是空操作**，必须把它当作凭据提交的前置条件，否则会把「没提交」误报成「提交了但没成功」。
4. `#remember` 默认已勾选；只在未勾选时补勾，避免把它点成关闭。
5. 点「登 录」（注意文案中间有空格，与页头「登录」不同）。
6. 成功时 SPA 换掉整个文档（`/sign_in` → `/dashboard`），失败则停留原页。用「URL 路径离开 `/sign_in`」判成功，不要用 URL 等于某个具体页面。

### 择幂中国的优化点

- **身份读取走 GraphQL**：`getMe` 是 POST，共享的 `IDENTITY_FETCH` 是 JSON GET，用不了。provider 通过新增的 `identity_script` 字段提供自己的只读脚本，其余 provider 仍用共享实现。返回 `email` 与 `phone`，因此**不需要**嘉立创那套信任首次绑定。
- **跟踪域全部拦掉，而不是放行**：页面加载 41 个域名（Google/Bing/百度/360/媒体/Clarity/腾讯验证码/顶象…）。放行会让它们种下 `.doubleclick.net`、`.bing.com`、`.baidu.com` 等 cookie，而 `SessionCodec.seal` 要求**每个 cookie 域都在白名单内**，会直接报 `session_invalid`。拦掉后只剩 `xometry.asia` 一个域，登录态才存得下。白名单只保留 `get.xometry.asia`、`xometry.asia`（`xom_access`/`xom_refresh` 写在父域上）、`api.xometry.asia`、`fonts.gstatic.com`。
- **首方子域也拦**：`messenger.xometry.asia`（客服组件）与 `sentry.xometry.asia`（错误上报）对登录和打开报价页都不是必需的，放进拦截清单以缩小出网面。
- **会话复用**：`xom_access` 约 3 小时、`xom_refresh` 约 90 天；实测复用登录约 11.7 秒，直接 `CHECKING_LOGIN`，不重复提交密码。

### 嘉立创登录方法

1. 打开报价页，等 `button.login-button` 可见（`domcontentloaded` 早于组件水合，不能直接点）。
2. 清除引导遮罩：先点「跳过」，失败则移除 `[id^="driver-"]`、`.driver-popover`、`.driver-overlay`、`.driver-fix-stacking`。
3. 点登录按钮并等 iframe 可见。这两步**整体重试一次**——引导可能恰好夹在「清除」与「点击」之间；但只重复指针动作，不重复提交凭据。
4. 在 iframe 内点 `.base-tabs__nav-item` 中的「账号登录」，等 `请输入手机号码 / 客户编号 / 邮箱` 出现。
5. 用 `type()` 逐字输入（保留组件校验与风控的击键信号），勾选「下次自动登录」以复用会话。
6. 点 `button.submit`；若出现 `.aliyunCaptcha-sliding-slider`，执行滑块拖动，最多两次（失败会重置）。
7. iframe 消失即回调成功。

### 优化点

- **有机滑块轨迹**：`slider_drag_steps()` 生成变步长路径，8% 概率回退、±1.4px 抖动、末步精确落点、停顿 8–90ms。两个必须踩准的细节：停在轨道边缘会被判「未完成」，需多滑约 3px；匀速扫过去会被判机器人。
- **身份绑定代替明文比对**：手机号登录无法与 `customerCode` 比对，故首次登录成功时把 `customerCode` 写入 `cnc_account.account_fingerprint` 并锁定（write-once、受租约栅栏保护），后续登录比对绑定值。绑定写入刻意不参与 `revision()`，避免把「身份登记」误判成凭据变更而撤销会话。
- **会话复用**：已验证的 `storage_state` 加密保存，再次登录直接复验，实测不重复提交密码（`submit=0`）。
- **轮询不被长提交阻塞**：提交期间 `OwnedSession.busy` 让状态查询短路返回当前视图，避免前端 1.5s 轮询排队超时。
- **WebSocket 静默拒绝**：平台会尝试 `wss://ws.jlc-cnc.com` 长连接。策略层只关该 socket，不把整个会话判为 `policy_blocked`，否则登录成功后立即失败。
- **Cookie 域白名单**：`storage_state` 中含 `jlc.com` 域（`PROD-JLC-CAS-SID`），provider `hosts` 必须覆盖，否则复验报 `session_invalid`。

### 人工兜底

验证码无法通过时进入 `WAITING_HUMAN`，前端 `ControlledBrowser` 支持点击与**拖动**（按下位移超过 4px 判定为拖动），人工拖完点「验证登录」即可继续。

## 本次验证边界

已实现接口、受控画面、人工输入、凭据保护、租约及平台登录适配。单元/接口/实际 SQLite 事务、真实 Chromium 合成场景、前端检查和构建的最终结果见 [D-18 验证报告](../.trellis/tasks/10-21-cnc-mvp-02-first-quote/research/login-validation-2026-10-22.md)。

2026-10-22 的验证记录只确认了公开登录表单、嘉立创原生 iframe/SDK 回调和只读身份接口；当时未用真实账号密码完成平台登录。本机 DNS 对两站返回保留 IPv6，按当时的整组拒绝契约停止。2026-10-23 用户确认保留混合地址过滤方案，当前契约和回归见 [browser spec](../.trellis/spec/backend/browser-executor.md)；上述旧记录不代表当前契约仍拒绝全部混合回答。自动报价页面本轮真实操作已单独保存 accounts/start/status/取消证据；真实上传、参数回读和报价仍未验收，不能从登录或接口调用成功推断报价成功。完整上传/报价、Agent、批量和监测的原任务门槛保持。
