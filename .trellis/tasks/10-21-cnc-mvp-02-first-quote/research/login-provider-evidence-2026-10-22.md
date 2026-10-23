# D-18 平台登录依据（2026-10-22；2026-10-23 复核）

本记录只覆盖匿名公开页面、官方前端代码和合成浏览器验证。未读取用户浏览器、未读取保存账号、未向真实平台提交用户名/密码，未上传模型或提交报价。站点会变化，后续真实认证仍须单独验收。

## 观察方式与来源

- [Xometry 官方登录入口](https://www.xometry.com/account/login/)、[官方询价入口](https://www.xometry.com/quoting/home/)。一次性独立 Playwright context 观察页面、可见控件和跳转域；不读取 input value、Cookie 或 storage。
- [嘉立创 CNC 询价入口](https://www.jlc-cnc.com/cncOrder/#/placeOrder)、[嘉立创账号入口](https://passport.jlc.com/)。观察原生账号登录窗口，并检查询价应用公开加载的 CAS SDK/前端模块。
- 本目录 `public_login_probe.py` 为匿名页面观察器，`public_source_probe.py` 仅下载公开脚本；下载结果保存在被忽略的 `.trellis/.runtime/login-public-source/`。脚本含完整第三方实现和公开配置，不作为产品源码或证据全文入库，不摘录其密钥样式配置。
- `guarded_login_probe.py` 另用生产 BrowserExecutor 执行匿名只读检查；它的连通性结果与普通匿名浏览器观察分开报告。

## Xometry US

1. 官方登录入口跳转到 `login.xometry.com/u/login/identifier`。观察到唯一 `input#username[name=username]` 及 Continue 按钮。密码阶段采用 Auth0 托管表单的 `input#password[name=password]`，仅合成场景覆盖；本轮未用真实账号推进该阶段。因此站方页面变化时须保留人工接管，不能把密码阶段记为现场已验证。
2. 公开询价应用脚本快照为 `1bf2160b1162.js`。webpack 模块 14712 的当前用户方法调用模块 46757 的请求封装，请求 `/v2/users/me`。后者 GET 分支使用默认 fetch、设置 `credentials=include`，该调用不添加 Authorization/Bearer。这支持在同一受控 Page 发起携带 Cookie 的只读身份请求；不是另建无出站保护的请求客户端。
3. 页面使用当前用户返回的 `email_address`，适配器只接受明确身份字段与配置用户名完全匹配。接口地址为 `https://api.xometry.com/v2/users/me`。字段候选、跨域 Cookie/CORS、真实账号返回形状和认证状态恢复仍须实际登录补验；接口路径或 HTTP 200 本身不构成登录成功。
4. 合成 Chromium 验证了分步表单、询价页身份复验、JPEG 画面、关闭 context 后从加密状态恢复，以及再次打开不重复提交密码。合成响应由测试提供，不能证明真实账号已登录。

## 嘉立创 CNC 中国站

1. 独立 passport 页面默认展示扫码入口，可切换“账号登录”；观察到“请输入手机号码 / 客户编号 / 邮箱”和“请输入登录密码”控件。适配器通过 CNC 原生“登录”按钮打开 `iframe#jlc-cas-login-window`，再切账号登录。不要导航到独立 passport 根页面后期待其自动建立 CNC 业务态。
2. 公开 CNC 应用脚本快照为 `7ae736367b30.js`。SDK 的默认 iframe ID 与上述选择器一致；CNC 的 CAS appId 为 `CNC_BIZ_GATEWAY`，开启回调认证码及第三方 Cookie 检查。使用原生窗口保留 appId、redirect/callback 和业务态交换，不自行拼接带认证码的 URL。
3. 公开应用在登录及挂载路径调用 `/cncPortal/login/queryLoginUser`，成功后更新用户信息，并另调用业务当前用户接口。适配器在同一业务页 GET `https://www.jlc-cnc.com/cncPortal/login/queryLoginUser`，只检查明确账号/客户编号/邮箱/手机号等候选字段；真实返回形状、字段可见性和输入账号等价关系仍待真实认证核验。无明确匹配保持人工状态，不以成功包装码推断身份。
4. 合成 Chromium 覆盖原生 iframe、账号表单、SDK 风格回调、身份复验、关闭恢复；未绕过真实验证码，未验证真实平台授权。

## 出站边界及当前阻断

平台业务/认证/必要静态主机为精确 allowlist。已观察的分析、广告、扫码等可选资源为单独的精确 deny 集合，仅其子资源/子 frame 被阻断且不污染页面；不因此允许这些主机连接或进行顶层导航。未知主机、非 HTTPS、带 userinfo 的地址以及私有/保留/混合 DNS 答案继续拒绝。

2026-10-22 的系统解析结果如下；这是本环境观测值，并非平台公网部署地址：

| 主机 | 观察到的答案 |
| --- | --- |
| www.xometry.com | `2001:2::128`、`28.0.1.44` |
| www.jlc-cnc.com | `2001:2::18a`、`28.0.1.145` |

生产出站探针因保留 IPv6 的混合答案拒绝连接，未完成受控真实登录页加载。没有过滤掉问题答案、修改本机 DNS、放宽策略或复用个人浏览器绕过。需在具有真实公网解析的部署环境补验首次登录、有效态复用、失效/挑战、关闭恢复和最终询价页身份。平台完整报价与 D-17 原 gates 不受本轮合成通过影响。

最终自动化命令与结果见 [D-18 验证记录](login-validation-2026-10-22.md)。
