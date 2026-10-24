# CNC 账号自动登录

账号列表的“自动登录”会打开受控浏览器窗口。已有有效会话时先核对目标账号，再进入关联平台的询价页；会话失效时执行一次平台登录。有验证码或页面无法识别时停在人工处理状态，用户可在窗口中操作并点击“验证登录”。浏览器画面与登录使用同一会话，不会转交 Cookie 给本机普通新标签页。

## 使用与配置

1. 在竞价平台中填写当前登录地址和询价地址，再给账号关联该平台。Xometry 的已观察登录入口为 `https://www.xometry.com/account/login/`，询价页为 `https://www.xometry.com/quoting/home/`；嘉立创 CNC 询价入口为 `https://www.jlc-cnc.com/cncOrder/#/placeOrder`，登录通过该页原生 CAS 窗口完成。服务端只支持这两个平台的受信入口，RapidDirect 仍延期。
2. 账号须启用，当前用户须具有账号修改权限及对象访问权。普通用户只访问自己创建的账号，管理员可管理账号；活动窗口仍绑定发起人。
3. 点击“自动登录”。窗口可点击、输入文本、发送按键和滚动；需要人工处理时，完成后点击“验证登录”。身份不一致不会显示成功。当前画面交互不是完整远程桌面，不支持文件上传、拖拽或系统剪贴板。
4. 关闭窗口或离开页面会请求释放浏览器；服务端在空闲 5 分钟或最长 30 分钟后兜底释放。已验证的认证状态加密保存，下次打开仍实际复验。修改账号/平台/密码或停用账号会撤销旧活动。
5. 编辑密码留空表示保留原密码。查询/导出不再返回密码或凭据/会话密文；新写入及受控读取的旧明文使用现有加密组件收敛到密文。

## 运行要求

- 使用项目已有 Playwright browser extra 和匹配浏览器，安装方式见 [浏览器运行说明](browser-runtime-setup.md)。本次合成验证使用工作区 managed Headless Shell，通过 `PLAYWRIGHT_BROWSERS_PATH` 指定，不连接个人 Chrome。
- Windows 请用项目 `main.py run` 启动，它已为 Uvicorn 配置支持 Playwright 子进程的 Proactor 循环；使用其他 Uvicorn 入口时需显式加 `--loop app.core.server_loop:subprocess_event_loop`。当前版本的 Windows 默认 reload/多 worker 循环不能启动该子进程。非 Windows 启动方式保持不变。
- 保持现有 CryptoUtil 加密密钥及轮换配置，勿丢失旧密钥。数据库沿用账号表已有 credential/session/lease 字段，本次没有新增迁移。
- 数据库语句日志隐藏绑定值；`DATABASE_ECHO=debug` 只保留语句级输出，不回显查询结果行。不要启用数据库驱动 DEBUG，避免在驱动层记录账号内容。
- 当前受控浏览器由创建它的 worker 持有。使用单个登录 worker，或按账号配置固定路由；跨 worker 请求会明确失败，不创建重复窗口。
- 浏览器必须能够获得并连接平台的真实公网 DNS 地址。未知地址、非 HTTPS、私网依然被严格拒绝（混合 DNS 中的合规公网地址安全保留，详见 [登录故障排查与修复说明](troubleshooting-account-login-browser-failed.md)）；不要通过关闭安全校验修复连通性。

## 本次验证边界

已实现接口、受控画面、人工输入、凭据保护、租约及平台登录适配。单元/接口/实际 SQLite 事务、真实 Chromium 合成场景、前端检查和构建的最终结果见 [D-18 验证报告](../.trellis/tasks/10-21-cnc-mvp-02-first-quote/research/login-validation-2026-10-22.md)。

2026-10-22 的验证记录只确认了公开登录表单、嘉立创原生 iframe/SDK 回调和只读身份接口；当时未用真实账号密码完成平台登录。本机 DNS 对两站返回保留 IPv6，按当时的整组拒绝契约停止。2026-10-23 用户确认保留混合地址过滤方案，当前契约和回归见 [browser spec](../.trellis/spec/backend/browser-executor.md)；上述旧记录不代表当前契约仍拒绝全部混合回答。自动报价页面本轮真实操作已单独保存 accounts/start/status/取消证据；真实上传、参数回读和报价仍未验收，不能从登录或接口调用成功推断报价成功。完整上传/报价、Agent、批量和监测的原任务门槛保持。
