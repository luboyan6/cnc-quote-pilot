# 账号管理平台登录失败故障排查与修复说明

## 1. 问题背景与现象

在前端页面 `E:/AIWorkspace/cnc-quote-pilot/frontend/web/src/views/module_cnc/cnc_account/index.vue`（账号管理）中：
- 用户点击操作列中的【登录】按钮后，弹出平台登录弹窗。
- 弹窗顶部状态显示红色 **【登录失败】** 标签，提示信息为：“登录服务浏览器启动失败，请检查服务器浏览器依赖或联系管理员。”，下方浏览器画面显示“暂无可用画面”。
- 打开浏览器控制台查看网络请求（Network）：
  - `POST /api/v1/cnc/cnc_account/login/1` 返回 HTTP 200，`code: 0`，`data.status: "STARTING"`（初始会话创建成功）。
  - 后续轮询 `GET /api/v1/cnc/cnc_account/login/1/sessions/{sessionId}` 同样返回 HTTP 200，`code: 0, msg: "成功"`，但 `data.status: "FAILED"`, `data.reason: "browser_failed"`。
- 用户疑惑点：接口网络状态和业务 code 返回 0 且打印成功，但页面界面却显示登录失败。

---

## 2. 根本原因排查

### 2.1 为什么接口返回 `code: 0` 但页面显示失败？
- `code: 0` 是 FastApiAdmin 框架规范中 HTTP 接口层级执行成功的标志（表示请求正常投递并成功获取到了会话当前状态）。
- 真正的业务状态存储在 `data.status` 中。会话启动后，后台异步任务驱动无头浏览器初始化，当浏览器或网络异常时，后台将该 session 的 `status` 置为 `"FAILED"`，`reason` 置为 `"browser_failed"`。
- 前端 `AccountLoginDialog.vue` 正确捕获并响应了 `session.status === "FAILED"`，呈现了红色的“登录失败”警告。

### 2.2 为什么无头浏览器会报 `browser_failed`？
查看后端日志 `backend/logs/fastapiadmin.log`，发现每次点击登录后约 1 秒均会出现以下告警：
```text
WARNING | app.modules.cnc.browser.third_party.egress:_handle:133 - browser egress policy_blocked
```

深入分析链路发现：
1. **受控代理拦截**：系统为了防御 DNS 重绑定攻击（DNS Rebinding）和 SSRF 探测，通过 `BrowserEgressProxy`（SOCKS5 代理）强行接管了 Playwright Chromium 的所有外发出站流量。
2. **域名解析校验**：所有出站流量必须通过 `BrowserPolicy.resolve(host)` 进行 DNS 安全审查。
3. **DNS 混合解析问题**：
   - 目标平台域名（例如 `www.xometry.com`）在本机代理环境中同时返回了 `ipaddress` 分类允许的 IPv4（`28.0.1.46`）和一条 Benchmarking 测试保留段 IPv6（`2001:2::120`）。此前环境核对确认这些是本机代理的 Fake-IP 回答；不能仅凭 `is_global=True` 将 IPv4 称为真实平台公网地址。
   - 在 Python `ipaddress` 库中，该 IPv6 地址的 `ip.is_global` 判定为 `False`。
4. **原契约与本机环境的冲突**：
   原 `BrowserPolicy.resolve` 按当时规范采用了“一票否决”校验：
   ```python
   # 原严格契约：只要包含任意一个非全球/保留 IP，直接抛出异常拒绝整个连接
   for address in addresses:
       ip = ipaddress.ip_address(address)
       if not ip.is_global or ...:
           raise ValueError
   ```
   导致整组回答被拒绝，出站代理终止握手，触发 `BrowserStop(Reason.BROWSER_FAILED)`。2026-10-23 用户明确选择保留地址过滤方案，并要求同步契约和验证；这属于已确认的行为变更。

---

## 3. 解决方案与代码修改

修改文件：[`backend/app/modules/cnc/browser/policy.py`](../backend/app/modules/cnc/browser/policy.py)

将“一票否决”策略优化为“**安全过滤合规候选 IP**”：
- 对所有 DNS 解析结果进行逐一安全审查，过滤掉私网（private）、环回（loopback）、组播（multicast）、未指定（unspecified）、保留地址及特殊本地地址。
- 收集符合合规条件的公网地址列表返回给上层连接池优先连接。
- 过滤后列表为空，或回答为空/畸形、解析出错时，拒绝请求并返回固定原因。
- 上层连接器只接收通过检查的固定 IP，不再次解析域名，也不尝试被过滤掉的地址。精确域名、HTTPS/443 和可选资源拒绝规则保持。

### 核心变更对比：

```python
<<<<
            addresses = list(dict.fromkeys(str(record[4][0]) for record in records))
            if not addresses:
                raise ValueError
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified or ip.is_loopback or ip.is_link_local or (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):
                    raise ValueError
            return addresses
====
            candidates = list(dict.fromkeys(str(record[4][0]) for record in records))
            if not candidates:
                raise ValueError
            addresses = []
            for address in candidates:
                ip = ipaddress.ip_address(address)
                if ip.is_global and not ip.is_multicast and not ip.is_reserved and not ip.is_unspecified and not ip.is_loopback and not ip.is_link_local and not (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local):
                    addresses.append(address)
            if not addresses:
                raise ValueError
            return addresses
>>>>
```

---

## 4. 验证结果

1. **Python 本地模拟测试**：
   - 编写独立脚本运行 `BrowserExecutor` 全流程会话建立，成功启动 Playwright 并导航至目标登录页，正常输出 `SUCCESS! Page title: Xometry`。
2. **Chrome DevTools 端到端全链路操作验证**：
   - 重启后端服务后，在真实的 Chrome 前端页面（`http://localhost:5180/web/#/module_cnc/cnc_account`）中执行操作：
     - 点击表格中第一条 Xometry 账号的【登录】按钮。
     - 弹窗正常开启，状态经过短暂的“准备浏览器”后，顺利转换为 **【已核验登录】**（绿色成功状态）。
     - 显示账号身份 `an***@gmail.com`，受控浏览器实时交互画面顺利加载展示（包含 Xometry 控制台完整的 Quotes 订单与报价组件）。
     - 交互控制按钮（Tab、回车、退格、Esc、滚动以及文本发送输入框）均恢复可用。
