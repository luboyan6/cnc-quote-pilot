# 浏览器组件安装与验证

此组件尚未接通真实平台/API/调度。按 [设计](browser-implementation-design.md) 在 02 接入业务仓储、ACL、可信平台适配器和 live gates 后才能启用自动化。

Windows 首轮验收发现 Python 3.12.13 Proactor 的连接重置回调可在关闭 socket 前抛出 WinError 10054，出现未关闭 transport。当前实现为组件自有接受连接增加了公开 Socket/Streams Adapter，保留其他清理错误的 `browser_cleanup_failed`；此前失败和修复后的独立回归分列于 [测试报告](browser-test-report.md)。需按部署版本复验，不能只据功能断言推断资源释放。本机 Docker Desktop Linux 引擎尚不可用，Linux 部署仍未验证。本轮没有修补系统 Python、访问已有 transport 的私有 socket 或设置全局异常过滤。

## 依赖

Python >=3.12；可选 extra 采用 Playwright==1.58.0（Apache-2.0），锁文件已实际解析新增 Playwright 和 pyee，未升级现有依赖。由项目 backend 目录安装：

```powershell
uv sync --locked --extra browser
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Resolve-Path ..).Path '.trellis/.runtime/playwright-browsers'
.venv/Scripts/python.exe -m playwright install chromium --only-shell
```

已有项目使用某数据库 extra 时一并保留，例如 `--extra browser --extra sqlite`。pip 部署可使用现有 requirements 入口后另装 `playwright==1.58.0`；基础 requirements 不强制所有后台实例携带浏览器。

以上安装与当前默认 headless 执行方式相匹配，运行服务和测试时须保留相同 `PLAYWRIGHT_BROWSERS_PATH`。该工作区目录已被 `.trellis/.gitignore` 排除；无浏览器二进制进入源码。需要完整 Chromium 的环境可去掉 `--only-shell`。浏览器安装会下载 Playwright 对应的二进制；受限环境需要管理员提供相同版本镜像/缓存，不能把系统 Chrome 自动更新版当作锁定的生产浏览器。Linux 镜像需要匹配的系统依赖；是否安装/构建应由部署流程安排，本轮没有部署。

## 会话与存储

配置由服务端提供精确允许域；默认只允许 HTTPS/443 和全公网 IP。托管浏览器进程经独立出站代理，浏览器 Context 禁止 Service Worker/下载及未经核验的 WebSocket。不得添加生产“允许私网”开关来方便测试。

将既有 `CryptoUtil.encrypt/decrypt` 作为 codec 注入；加密包内绑定 owner/platform/account，恢复时比对，明文 state 只在内存中交给 SDK。适配器验证实际身份成功后才导出/保存；平台使用 sessionStorage、设备绑定或挑战时仍须单独验证，不能把 storage_state 当万能登录。

IntentStore 由 02 的应用 DB 实现，上传/提交前原子写入，重启/重复调用只读协调。进程内账号忙检查和测试替身不替代持久账号租约/ACL/副作用日志。人工暂停需业务恢复入口和 owner 复验；本组件没有可直接使用的接管 UI。

真实 Trace/截图可能含秘密、身份、CAD 与请求体；默认不收集，确需诊断时存入授权私有位置并设置保留期限，禁止发给模型/提交仓库/公开目录。合成 E2E 的临时 Trace 也不作为真实报价证据。

## 验证

本轮实际使用 backend Python 3.12.13、Playwright 1.58.0、配套 Headless Shell 145.0.7632.6/build1208，以及独立启动的系统 headless Chrome 155.0.8059.85；未连接个人浏览器或导入其会话。默认合成 E2E 使用配套 Headless Shell，设置 `CNC_BROWSER_CHANNEL=chrome` 才使用系统版本。测试的 HTTPS 页面、STEP、身份和报价均为合成数据。系统 Chrome 的本地测试结果不能代替部署版本验证。最终命令/数量及环境差异见 [测试报告](browser-test-report.md)。

参考原项目源码只读；第三方组件许可/差异随 browser 模块保存。BrowserSkill 尚未安装或接通，0.3.1 remote 不支持上传，不能用作远程 STEP 通道。

## Windows 权限不足时的 Linux 文件边界补验

本机现有 Ubuntu/WSL2 已能执行原符号链接负向用例，无需开启 Windows Developer Mode 或修改账号权限。测试环境位于 gitignored `.trellis/.runtime/br-linux-venv`，Python 3.12.3；因 WSL 外网连接超时，使用按既有 backend lock 约束下载的标准 Linux wheels 离线安装最小导入依赖。该环境只用于组件测试，不是 Linux 浏览器部署。

从仓库根目录、使用该 Linux 环境运行：

```sh
cd backend
../.trellis/.runtime/br-linux-venv/bin/python -B -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k symlink -v
```

必须核对实际执行 1 项、0 跳过、退出码 0；不能接受 discovery 导入失败、过滤到 0 项或 `OK (skipped=1)`。完整准备/执行命令、环境版本及原测试 SHA-256 见[Linux 补验记录](../.trellis/tasks/10-21-cnc-browser-reuse/research/linux-validation-2026-10-22.md)。本次补验不代表 RapidDirect/Xometry、Linux Chromium、Docker 或生产托管已验证。
