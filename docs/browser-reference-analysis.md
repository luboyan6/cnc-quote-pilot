# 浏览器自动化源码核验与复用决策

首次核验：2026-10-21；续作复核：2026-10-22。方法：先检查业务仓库及任务树，再读取本地参考源码、确定复用方案、修订任务，最后设计、实现、验收。参考仓库仅执行读取和 git 查询，没有修改、重置、安装依赖或克隆。本文描述源码能力，不把参考项目测试或既有研究当成本项目的实测结果。

## 1. 仓库身份与业务现状

| 仓库 | 实际目录 | 分支 / Commit | 工作区与许可证 |
| --- | --- | --- | --- |
| 当前业务 | `E:/AIWorkspace/cnc-quote-pilot` | `dev` / `60d5519b30caec112431e1722becf246120be8a4` | 已有未提交的 backend/README.md、frontend/app/.env.development 等修改；保留。根 LICENSE：MIT，2025 fastapiadmin |
| DeerFlow | `E:/AIWorkspace/deer-flow` | `main` / `f6fe1e9c9e029bf22b8e2eb8e2e23e1258cf0814` | 有未跟踪的项目管理/文档文件；核查的浏览器源码无已跟踪改动。根 LICENSE：MIT，Bytedance / DeerFlow Authors |
| WeKnora | `E:/AIWorkspace/rag-platform` | `main` / `a6cc635ab91f81c105b0f38b8e6b0b4c9ede1c1a` | 查询时 git status 为空。根 LICENSE 为含第三方例外的 MIT，所评估实现归 Tencent；不能据此给整个依赖树统一授予 MIT |

2026-10-22 只读复核：两仓分支/Commit 与上表一致，DeerFlow 仍只有原未跟踪管理/文档文件，WeKnora 工作区干净；DeerFlow 源 LICENSE 与本项目许可副本 SHA-256 均为 `b23dff4d4bac8d17b6efaaa7e88c2b730149c4dda45699ce676b719cfdffe7e1`。业务中用户已有 README 与前端环境文件哈希保持。

业务栈依据 `backend/pyproject.toml`：Python >=3.12、FastAPI、SQLAlchemy、APScheduler、Agno、cryptography；Web 为既有 Vue 管理端。递归搜索 `backend/app`、`backend/tests` 和依赖清单后，尚无 CNC 运行模块、浏览器执行器或 Playwright 依赖；`browser` 命中主要是登录日志的 UA 字段。`.trellis/tasks` 现有 7 个 task.json，含 bootstrap、MVP 父任务与 01–05；无归档/已完成任务。研究目录已有输入探针与 Deep Agents SDK 探针，不能算产品 RPA。

已知业务限制来自子 01 的 `research/live-validation-2026-10-21.md`：RapidDirect A/B 保存过配置但几何为零且无真价；Xometry US 账号和报价未验证；研究 JSON 为 draft、automation_enabled=false。不得为了执行器测试启用它们。

## 2. DeerFlow 调用链与证据

以下路径均相对 DeerFlow 根；固定 Commit 见上表。

| 能力 | 源码 / 类或方法 / 行号 | 核验结果及复用边界 |
| --- | --- | --- |
| 工具注册 | `config.example.yaml:1165`，`backend/packages/harness/deerflow/community/browser_automation/tools.py:126` `_resolve_session` | 配置引用工具 → 读取固定 browser_navigate 配置 → 按 runtime.context.thread_id 申请 session lease → session 方法 → ToolMessage/Command；依赖 DeerFlow config/runtime/output 服务和 LangChain/LangGraph，不能当无依赖 SDK 搬入 |
| 浏览器启动 | 同目录 `session.py:408` `BrowserSession._ensure_page` | 惰性导入 async_playwright；启动 Chromium、新建 Context，设置超时，绑定路由和新页监听；CDP 分支复用默认 Context/现有页，不等价于账号隔离 |
| 会话与并发 | `session.py:228` `_PlaywrightLoopThread`；`:933` `BrowserSessionManager`；`:967` `get_session`；`:1015` `acquire_session` | 专用事件循环、thread key、pin/release、容量/空闲/LRU；进程本地，不支持任意多 worker。业务项目用单消费者同一 asyncio loop，采用 owner/platform/account key，避免搬入跨 loop 线程框架及默认共享 key |
| Snapshot/Ref | `session.py:42` `_SNAPSHOT_JS`；`:544` `_snapshot_impl`；`:553` `_click` | DOM 内注入 data-df-ref，清除旧标记；点击后更新 snapshot。编号属于当前页面观察，不能持久用作平台定位器或恢复权限。正常链路采用官方 Locator；异常仅向 Agent 提供脱敏、有限观察 |
| DOM 与自动等待 | `session.py:539` `_navigate`、`:553` `_click`、`:590` `_type` | 调用 Playwright goto/locator.click/fill；使用 domcontentloaded 和有界超时。自定义 Ref 框架对确定流程非必要 |
| STEP/认证持久化 | 搜索整个 browser_automation 目录 | 该目录无 set_input_files、filechooser、storage_state 或正式登录工作流；不能声称直接覆盖 STEP/跨重启登录态。使用官方上传及 storage_state API，由平台适配器验证身份/上传解析 |
| 人工接管 | `session.py:765` `_start_screencast`、`:792` `_dispatch_input`；`backend/app/gateway/routers/browser.py` | 存在 Live/CDP 输入和视图链路；带 Gateway 权限及流媒体生命周期，不能只复制一个方法就宣称已具备接管 UI |
| 出站安全 | `session.py:455` `_egress_proxy_settings`、`:497` `_install_request_guard`；`egress.py:58` `BrowserEgressProxy` | Context 路由检查请求；SOCKS 代理在实际连接处解析并固定已核验 IP。注释中的“覆盖每一重定向”不能替代 SDK/实测核验，见下文补证。CDP 明确跳过路由守卫，需 allow_unguarded_cdp，本项目不默认连接个人浏览器 |
| 清理/恢复 | `session.py:728` `_close`、`:927` `close`、`:1086` `close_session`、`:1096` `close_all_sessions` | 取消时 shield 清理、容量回收；浏览器存活/重建不等价于业务提交恢复，没有 CNC intent/远端回执协调 |

依赖证据：`backend/packages/harness/pyproject.toml:5,24,31,109` 为 Python >=3.12、LangChain >=1.3、LangGraph >=1.2.9,<1.3、可选 `browser=[playwright>=1.40]`。其中 `egress.py` 只依赖 Python 标准库，是可独立复用的最小组件；保留 MIT 全文及固定来源，必要本地改动须列出。

安全取舍同样依据源码：`_SNAPSHOT_JS` 的名称回退包含 `el.value`，不能直接把该结果作为已脱敏观察发给报价 Agent；本轮不复制这套 DOM/Ref 实现。CDP 分支的 request guard 被明确跳过，也不能用“已连接浏览器”替代出站安全验收。

实施阶段补证：本项目选择的 Playwright 1.58.0 在真实 Chromium 合成 E2E 中没有对重定向后续跳再次调用路由守卫；SOCKS 仍阻止了非法目标，但初版没有把错误归为 POLICY_BLOCKED。这与[官方 route 限制](https://playwright.dev/python/docs/api/class-page#page-route)及本地安装 SDK `_generated.py:9496` 的说明一致。[官方 Request 文档](https://playwright.dev/python/docs/api/class-request)说明重定向创建新的请求链。因此不能只复用参考注释的安全承诺：本项目采用 Context 路由 + 逐请求观察的停止标记 + SOCKS 实际连接限制，具体修复与复验见测试报告。

## 3. WeKnora 与 BrowserSkill 调用链

以下路径均相对 WeKnora 根；固定 Commit 见上表。

| 能力 | 源码 / 类或方法 | 核验结果及边界 |
| --- | --- | --- |
| Agent 工具 | `internal/application/service/agent_service.go:332`；`internal/agent/tools/browserskill.go:40,46,65` `BrowserSkillScope/NewBrowserSkillTool/Execute` | LocalBrowserEnabled → 注册 local_browser → 校验 caller tenant/user → 严格参数 schema → GetStatus/Control(select)/Call → 解释结果；不是通过 shell 让模型安装并运行 CLI |
| 连接/启动 | `internal/browserskill/daemon.go:129` `Manager.start`；`manager.go:361,532,669` `ServeHTTP/attach/rpc` | exec 启动 bsk daemon start --foreground --port 0，独立 BSK_HOME；授权 WebSocket 转发到 daemon 的官方 tool.* RPC；这个 Go gateway 不是 Python 可直接导入组件 |
| 隔离/授权 | `manager.go:35` `Scope`、`:851` `Call`；`authorization.go:35,47` `tokenHash/AuthorizeHTTP` | tenant/user + conversation task；序列化命令、epoch 防暂停前动作重放、移除调用方 session/browser id；token 哈希存储及轮换。窗口隔离不等价于 Chrome profile/Cookie 隔离 |
| 参数与 DOM | `internal/agent/tools/browserskill_schema.go:493` `ValidateArguments`；`manager.go:818` methods | 官方 observe/snapshot/ref/selector 命令，按方法检查字段、唯一定位，禁止任意方法；能力仍需应用侧限制，本项目不开放 evaluate/shell 或模型自由点击 |
| 人工接管/恢复 | `human.go:16,37` `IsHumanStep/pausedError`；`manager.go:1079` `Control` | request_help/tab_borrow 有有界人工等待；暂停后显式 resume 并先 snapshot，断连/用户关窗暂停，重选不会自动恢复。不可用任意页面谓词冒充人工完成 |
| 资源释放 | `internal/agent/tools/browserskill.go:134` `Cleanup`；`daemon.go:96` `Close` | 取消后独立 cleanup context；未完成保留供人工，完成走官方 session stop。服务清理在 container.go 注册 |
| 上传限制/版本 | `scripts/browserskill-release.json`、`scripts/build_browserskill.sh`、`manager.go:818` | 固定 extension/daemon 0.3.1，源 `da6bf4eed2dd7256567e152df8c903c87f6598c3`；从同源 cargo build --locked --release -p bsk。local_browser 方法列表无上传入口，不能推断可承担 STEP |

依赖：`go.mod` 为 Go 1.26.0、gorilla/websocket v1.5.3、jsonschema-go v0.4.3；BrowserSkill 扩展构建还需 Node/pnpm、Rust/Cargo 与 C 编译器。扩展附带的 LICENSE 与上游固定 Commit LICENSE 都是 MIT（Tencent）。不引入这些构建链和 gateway。

本地没有 BrowserSkill 上游完整源码，只有集成代码、release manifest 和构建说明，因此仅补查固定 Commit 的[官方远程协议](https://github.com/Tencent/BrowserSkill/blob/da6bf4eed2dd7256567e152df8c903c87f6598c3/docs/remote-extension-connection.md)。协议确认：local loopback；remote 由扩展向服务端发起认证连接；借用/归还标签页；断连后会话/动作不自动重放；该版 remote upload/download 返回 unsupported。本轮未运行 bsk、扩展或配对 E2E；CLI/扩展内部源码路径抓取未成功，不声称完成其内部实现审计。

## 4. 官方 SDK 优先的决策矩阵

| 需求 | 首选复用层级 | 最小本项目增量 | 舍弃或推迟的方案 |
| --- | --- | --- | --- |
| 启动/隔离/会话 | 官方 Playwright async SDK | 账号作用域、生命周期/容量约束、身份复验及加密状态边界 | 不复制 DeerFlow 线程管理器；不接个人 Chrome 默认 profile |
| DOM/上传/等待 | 官方 Locator、set_input_files / expect_file_chooser、expect | 平台可信映射、文件哈希/大小、上传远端回执/几何验证 | 不手写 DOM 等待引擎、CDP 上传协议或通用 Ref 引擎 |
| SSRF | 引入独立 MIT `BrowserEgressProxy` + 薄策略 Adapter | 精确域名、HTTPS、全地址公网检查、路由/逐请求观察及 DNS 连接固定；禁 Service Worker/WebSocket 或另经审查 | 不只检查首次 goto 或假定 route 拦截所有跳转；不复制整套 DeerFlow |
| 登录态 | 官方 storage_state（Cookie/localStorage/IndexedDB）+ 既有 CryptoUtil | 只在内存解密，存储键绑定 owner/platform/account；失效/挑战转人工，身份验证后才保存 | sessionStorage 不被默认保存；平台实际机制尚待验证 |
| 平台工作流 | 平台 Adapter + 固定 Workflow | 参数回读/几何/真实价格语义；副作用 intent 先记录，超时不盲重发 | 不让 Agent 推断价格、选择任意按钮或扩域 |
| 异常/人工 | 借鉴两项目工具/暂停契约 | 类型化异常、只读协调、WAITING_HUMAN 与复验接口 | BrowserSkill 只在本机登录态/接管需求成立且模式可用时另评估；本轮不实现 gateway/扩展/UI |
| 调度 | 既有 SchedulerUtil（04） | 调用同一执行器，持久计划/账号租约/观测 | 不移植参考项目调度/Agent 框架，不新建第二调度器 |
| 诊断 | 官方 Trace/截图 | 默认不采真实敏感 trace；开启时私有存储、授权/保留期限/脱敏 | 不把原始 DOM/trace/请求体发给模型或公开目录 |

2026-10-22 兼容性补充：本项目固定 SDK 的 Headless Shell 145 实测仍在一次非法重定向的 Windows 连接回收上失败，而正常路径已通过。选型顺序的最后一层因此限定为一个本地接受连接 Adapter：SOCKS/域名/IP 固定仍复用原组件，只有 Windows socket 所有权与已 reset 连接的 shutdown 收口需要本项目处理。采用 Python 公开的 [sock_accept](https://docs.python.org/3.12/library/asyncio-eventloop.html#asyncio.loop.sock_accept)、[detach](https://docs.python.org/3.12/library/socket.html#socket.socket.detach) 和 [open_connection(sock=...)](https://docs.python.org/3.12/library/asyncio-stream.html#asyncio.open_connection)；后者明确把 socket 所有权转给 StreamWriter。此设计不是对已有 transport 的私有 socket 做补丁；具体效果只能以修复后真实 E2E 为准。

SDK 选定可复现实测基线 `playwright==1.58.0`，不是“最新版本”声明；[该版本依赖与许可](https://github.com/microsoft/playwright-python/blob/v1.58.0/pyproject.toml)：Apache-2.0，Python >=3.9、pyee>=13,<14、greenlet>=3.1.1,<4；兼容业务 Python 3.12 与 greenlet==3.5.2。需在本项目 lock 中实际解析，浏览器二进制另装并记录。官方依据：[Context 隔离](https://playwright.dev/python/docs/browser-contexts)、[Locator](https://playwright.dev/python/docs/locators)、[上传](https://playwright.dev/python/docs/input#upload-files)、[自动等待](https://playwright.dev/python/docs/actionability)、[认证](https://playwright.dev/python/docs/auth)、[Trace](https://playwright.dev/python/docs/trace-viewer)。

## 5. 验收与可追溯边界

复用已在源码中确认，不代表本项目能力已通过。执行层交付、任务冲突检查和测试结果分别见 `browser-implementation-design.md`、`browser-trellis-task-review.md`、`browser-test-report.md`。单元/Mock、真实 Chromium 合成站点 E2E、真实平台 E2/E3 必须分别报告。没有合法会话/可报价样件/已验证提取器时，真实平台项明确为“未验证”，不编造选择器或启用 draft 配置。
