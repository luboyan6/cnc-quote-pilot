# 浏览器复用实现与验收报告（2026-10-21～22）

本报告属于 `cnc-browser-reuse` 共用组件交付。真实平台登录/STEP 解析/报价/交期、正式 Agent 恢复、持久调度、人工接管 UI 尚须原 01–05 逐项验证；本报告不将它们标为完成。

当前续接已补齐原先未验证的 OS 符号链接逃逸用例：在本机现有 Ubuntu 中原样执行，1 项通过、0 跳过，测试 SHA-256 前后一致。Windows 本轮单元/Mock/TCP 仍为 62 项、61 通过/1 权限跳过；两者分列，不把 Windows 跳过算作通过。既有配套 Headless Shell 与系统 Chrome 的合成 E2E 各 11/11 结果保留。本轮未改生产代码/测试或操作系统权限。

## 环境与已执行准备检查

- 业务分支 `dev`，起始 Commit `60d5519b30caec112431e1722becf246120be8a4`。
- Windows，backend Python 3.12.13；Playwright 1.58.0、pyee 13.0.1、greenlet 3.5.2、cryptography 50.0.0。
- 验证工具为 backend 虚拟环境 Ruff 0.14.13、basedpyright 1.40.2。后者只装在环境用于本轮检查，没有变更项目开发依赖。
- 2026-10-21 首轮实际启动全新 headless Chrome channel `155.0.8059.85`；2026-10-22 已通过官方安装器在被 gitignore 的 `.trellis/.runtime/playwright-browsers` 下载 Playwright 配套 Headless Shell `145.0.7632.6`（build 1208），另含 FFmpeg 1011、Winldd 1007。没有连接个人已登录 Chrome 或导入其会话。系统 Chrome 和配套 Headless Shell 分别报告结果。
- `uv lock`：PASS，解析 109 包，只新增 playwright/pyee，旧依赖版本未改。首次 `uv lock --offline` 先遇沙箱缓存权限限制，提权读取后因离线缓存不足失败；联网解析成功。之后 backend 目录 `uv lock --check --offline`：PASS。
- `uv pip install --python backend/.venv/Scripts/python.exe playwright==1.58.0`：PASS，实际安装至本项目虚拟环境。
- `review_task_tree.py`：PASS，旧 7 项任务元数据保留（仅父 children 增 BR），38 个允许的原文件修订、29 个基线文件未改，8 项 ID 唯一，明确依赖无环。
- 父任务、01–05 和 BR 的 `task.py validate`：PASS；这只代表上下文路径有效。
- `git diff --check`：PASS；初始用户修改不在本轮更改范围。

## 代码交付与复用来源

| 路径 | 实际变更 |
| --- | --- |
| `backend/app/modules/cnc/browser/contracts.py`、`errors.py` | 账号/参数/回执/几何/精确报价契约，受信 PlatformAdapter、强制注入 IntentStore，固定脱敏停止原因 |
| 同目录 `files.py`、`policy.py`、`state.py` | STEP 根/大小/哈希/格式校验及官方字节/文件框上传；精确域、公网 IP/IPv6 site-local 拒绝；注入已有 CryptoUtil 的作用域加密状态 |
| 同目录 `session.py`、`workflow.py` | 惰性可选 SDK、同 loop/task 账号隔离、完整生命周期；Context 路由/逐请求观察；固定步骤、三类 mutation intent、只读有限重试、全字段/Decimal/交期/新鲜度校验 |
| 同目录 `third_party/egress.py`、`DEERFLOW-LICENSE`、`README.md` | 独立复用 DeerFlow MIT 代理与完整许可；固定 Commit/路径/源哈希和最小适配差异 |
| 同目录 `windows_streams.py` | 本组件自有 Windows 接受连接的公开 Socket/Streams Adapter；不改 SDK、解释器或原 SOCKS/出站协议；释放效果以最终独立回归为准 |
| `backend/tests/cnc/browser/` | 独立 unittest、测试专用 SDK/存储替身及真实 Chromium 合成站点/适配器；不加入生产假平台或默认内存仓储 |
| `backend/pyproject.toml`、`uv.lock` | optional `browser` extra 和实际锁定的 Playwright/pyee；未升级旧依赖 |
| 相关 `docs/`、`.trellis/tasks/`、backend specs | 本轮源码/设计/任务审计/安装/验收记录与可执行契约；原任务元数据/历史保持 |

Context、Locator、上传、自动等待及 storage_state 都直接使用官方 Playwright 1.58.0；未复制 DeerFlow harness/Ref/跨 loop 框架、WeKnora gateway、BrowserSkill runtime 或新 Agent 工厂。仅代理为第三方代码，源为 DeerFlow `f6fe1e9c9e029bf22b8e2eb8e2e23e1258cf0814` 的 `backend/packages/harness/deerflow/community/browser_automation/egress.py`。许可证副本哈希与参考 LICENSE 一致，适配差异随代码说明。

## 组件测试与独立审查

独立 `trellis-check` 已完成任务/文档和核心/测试代码审查，结果与历次命令在 [check-review.md](../.trellis/tasks/10-21-cnc-browser-reuse/research/check-review.md)、[实现交接](../.trellis/tasks/10-21-cnc-browser-reuse/research/implementation-notes.md) 和 [E2E 原始记录](../.trellis/tasks/10-21-cnc-browser-reuse/research/e2e-notes.md)。最终 E2E 结果以本报告下方分层结论为准，不能引用早期功能断言通过代替整体清理验收。

backend 目录中的验证命令：

```powershell
.venv/Scripts/ruff.exe check --no-fix app/modules/cnc/browser tests/cnc/browser
.venv/Scripts/ruff.exe format --check app/modules/cnc/browser tests/cnc/browser
.venv/Scripts/python.exe -m basedpyright app/modules/cnc/browser tests/cnc/browser --project pyrightconfig.json
.venv/Scripts/python.exe -m unittest discover -s tests/cnc/browser -p 'test_[epsw]*.py' -v
# 单独显式启用真实 Chromium 合成 E2E；默认跳过不代表通过
$env:PLAYWRIGHT_BROWSERS_PATH = 'E:/AIWorkspace/cnc-quote-pilot/.trellis/.runtime/playwright-browsers'
$env:CNC_BROWSER_E2E = '1'
$env:CNC_BROWSER_CHANNEL = '' # 配套 managed；'chrome' 为系统版本复现
.venv/Scripts/python.exe -m unittest discover -s tests/cnc/browser -p 'test_browser_e2e.py' -v
```

验收与测试证据入口如下；各入口的通过、失败与未验证仍以本报告最新运行结果为准。

| Trellis 验收 | 可重复核查的证据入口 |
| --- | --- |
| BR-01 / BR-02 | 源码/设计/任务复核三份指定文档、第三方许可与 `research/review_task_tree.py` |
| BR-03 账号、并发、生命周期 | `test_session.py`；`test_windows_streams.py` 的真实 TCP/所有权/取消/清理回归；合成 E2E 的 state/isolation、rebuild、cancel、redirect 释放用例 |
| BR-04 会话、域名、文件安全 | `test_policy_files_state.py` 的真实加密和公网/路径/哈希校验；`test_egress.py` 的实际出口约束；合成 E2E 的挑战、重定向、子资源和弹窗用例；OS 符号链接情形单独报告 |
| BR-05 上传、完整字段、价格、重试 | `test_workflow.py` 的参数/Decimal/交期/缓存/intent/三次读取上限；合成 E2E 的原生文件框/动态 chooser/完整字段和未知提交重建用例 |
| BR-06 证据分层 | 本报告的单元/Mock、真实浏览器合成站点与真实平台表；原平台 JSON/Schema 基线哈希不变，draft/禁用状态不变 |

审查中已修正并增加回归覆盖：未经核实缓存价/错误枚举类型、IPv6 `fec0::/10` 识别、初始化失败后占位泄漏、取消与清理同时完成的竞态、配置保存/读回超时和取消、重定向后续跳的策略停止标记，以及代理清理超时被继承实现静默忽略的问题。测试替身的 13 个类型注解错误和一处格式差异也已修正，没有降低检查配置。

真实重定向初测确实失败过：非法目标已被 SOCKS 拒绝，但会话返回 BROWSER_FAILED；添加 Context 逐请求观察后针对该用例真实 Chrome 复测通过（1 项 / 4.039 秒）。这不是放开允许域，也没有把无关 Chrome 后台拒绝标记成当前页面事件。SDK 的[重定向路由限制](https://playwright.dev/python/docs/api/class-page#page-route)已同步设计和规范。

2026-10-22 续作时复核的历史结果：

| 检查 | 实际结果（后续修复前的基线） |
| --- | --- |
| 单元/Mock | 46 项，45 通过，1 项 Windows 符号链接权限不足，明确“未验证” |
| Ruff lint / format | 通过，16 个 Python 文件格式检查通过 |
| basedpyright 核心与全部测试 | 0 errors / 0 warnings / 0 notes |
| 系统 Chrome 155 E2E | 11 方法 / 60.903 秒 / exit 1；FAILED(errors=11)，错误数含 subtest；取消用例随后加严以拒绝清理失败 note，不能将原取消结果当作完整释放通过 |
| managed Chromium 145 E2E | 11 项 / 27.634 秒 / exit 1，10 通过、1 错误、0 跳过；禁止域重定向退出时 `browser_cleanup_failed` |
| managed 运行的功能覆盖 | 官方文件上传/动态文件框、字段/Decimal/交期回读、会话隔离/加密恢复、失效/挑战、只读三次上限、回执不明不重发、缓存拒绝、子资源/弹窗阻断、严格取消均通过；这不替代失败的重定向释放用例 |

这些结果已促成下文记录的最小 Windows 接受连接 Adapter 修复，最终复验结果另列，保留失败历史。

2026-10-22 修复后的独立完整回归（本次 Ubuntu 补验之前）：

| 检查 | 最新实际结果 |
| --- | --- |
| 单元 / Mock / 本机 TCP | 62 项，61 通过、1 跳过；仅 OS 符号链接权限不足，仍为“未验证” |
| 新 Windows 专项 | 上述包含 16/16 专项通过；涵盖真实 TCP RST、SOCKS 拒绝后 RST、端口释放、任务启动前取消、实际 Streams 初始化取消、交接/关闭/其他错误传播 |
| Ruff lint / format | 全部核心与测试通过；18 个 Python 文件格式检查通过 |
| basedpyright | 全部核心与测试 0 errors / 0 warnings / 0 notes |
| 配套 Headless Shell 145 E2E | 11/11 通过，23.707 秒，0 跳过；无 Proactor / ResourceWarning / cleanup failure，仅预期固定 policy_blocked 日志 |
| 系统 Chrome 155 E2E | 11/11 通过，37.981 秒，0 跳过；全新 headless profile，最初失败的重定向/释放路径通过 |
| 完整 E2E 日志复核 | 两份完整日志均无 ResourceWarning / Proactor transport / WinError / cleanup failure / traceback；Chrome 背景请求只有预期固定 policy_blocked 警告 |
| 符号链接用例独立重试 | 获准在沙箱外执行原用例：1 项 / 0.023 秒，仍因 Windows symlink privilege 不足跳过；未改系统权限，不能接受为通过 |

完整 E2E 原始输出临时保存在 `C:/Users/admin/AppData/Local/Temp/cnc-br-managed-e2e-fixed-2026-10-22.log` 与 `cnc-br-chrome-e2e-fixed-2026-10-22.log`。审查者在 Chrome 完成后一次新建命令进程遇到 Windows 1909；主会话随后以普通执行工具成功读取两份完整日志并完成上述扫描，没有修改账号/权限。可追溯的命令、数量和审查记录保存于任务 research，临时文件不是长期证据仓储。

最终任务检查时普通沙箱进程也返回 1909，未开始执行；获准在沙箱外重跑后，任务树审计、父/01–05/BR 的七组 manifest 校验及 `git diff --check` 全部通过，原用户文件哈希不变。进度已用 `add_session.py --no-commit` 记入 Session 3，未提交/归档。该工具账户问题与已完成的浏览器运行结果分开记录，没有重置账号或更改操作系统权限。

## Windows 资源释放：原因、最小修复与边界

在 Windows Python 3.12.13 + Chrome 155 的实际 E2E 中出现 `ConnectionResetError: [WinError 10054]` 和 `ResourceWarning: unclosed transport`。本地 `asyncio/proactor_events.py:165` 的 shutdown 抛错发生在随后 socket.close/server detach 之前；[CPython 对应实现](https://github.com/python/cpython/blob/3.13/Lib/asyncio/proactor_events.py)也可核对该顺序。不能据此假定换到另一 Python 小版本就已修复。

首先让清理 handler/server 超时或失败明确上报 `browser_cleanup_failed`，继续尝试其他资源释放并归还账号名额，避免原继承实现隐藏真实泄漏。随后只为组件自有 Windows 接受连接增加 `windows_streams.py`：公开 `sock_accept` / `detach` / `asyncio.open_connection(sock=...)` 管理所有权，单独处理自建 socket 已 reset 的精确 shutdown 10054，使标准 transport 继续关闭。Unix 仍走原 `asyncio.start_server`，SOCKS/端口443/域名/DNS固定和出站连接没有改写。

真实 TCP RST 又验证了 Streams 会把终止读取的 WinError64 交给 reader 和关闭 waiter；只接受公开 `reader.exception()` 的同一异常对象，关闭中未知错误仍失败。独立 shutdown 结果记录防止该读取结果掩盖后续关闭异常。负向回归实际覆盖“已知 reader64 + 未知 shutdown10053/OSError”仍报告清理失败，实际取消测试确认对端 EOF/端口释放。没有修改解释器/已有 transport 的私有 socket，也没有设置全局异常过滤器。

既有 managed 与系统 Chrome E2E 均已验证本机 Windows 正常、重定向和取消后的资源释放。`docker version` / `docker images` 当时返回找不到 `dockerDesktopLinuxEngine` named pipe，Linux 容器与生产托管部署仍为“未验证”；本地配套浏览器通过不代表生产环境通过。当时未验证的 OS 符号链接逃逸用例现已由下述 Ubuntu 原样执行补齐，Windows 的权限跳过记录保留。

## 2026-10-22 本次续接：Ubuntu 符号链接补验

使用已经运行的本机 Ubuntu/WSL2，Python 3.12.3，隔离环境 `.trellis/.runtime/br-linux-venv`。WSL 在线访问 PyPI 与项目清华镜像均超时，随后由 Windows 下载依据既有 `backend/uv.lock` 约束的标准 Linux wheels，在 Ubuntu 中离线安装最小导入依赖。未复用 Windows 原生 site-packages，未启动应用/DB/Redis 或访问平台。准备过程、具体命令和版本见[原始补验记录](../.trellis/tasks/10-21-cnc-browser-reuse/research/linux-validation-2026-10-22.md)。

原用例 `test_policy_files_state.FileTests.test_symlink_escape_rejected`：**1 项 / 0.024 秒 / 0 跳过 / exit 0**。原测试文件 SHA-256 执行前后均为 `17209160855a9ea821bb103e74dd36a7cd9c1d5535839c02f65e9f314dd71a61`。该结果证明实际 OS 符号链接指向受信根外时，被现有文件校验拒绝。没有替换断言、Mock 路径解析或修改系统权限。

另一次扩大范围的 Linux 诊断运行实际为 **62 项 / 7.300 秒 / 58 通过、2 errors、2 原有 Windows 专属跳过**，不能称为完整 Linux suite 通过。两项错误来自直接调用 Windows-only Adapter 的 `test_windows_streams`：流关闭后，新 socket 的 `assert_port_released` 裸 bind 返回 Linux `EADDRINUSE`。这与平台的端口/TIME_WAIT 语义有关的解释仍须依据原始记录，不据此断言泄漏或完整 Linux 支持。没有修改生产代码、原测试或新增 skip 来消除错误。原符号链接用例在该扩大运行中也实际通过；Windows 专项的受支持环境结论仍为本轮 Windows 16/16。

适用的 Linux 跨平台单元/Mock 回归（原 `test_egress`、`test_policy_files_state`、`test_session`、`test_workflow`）实际 **46/46 通过 / 3.385 秒 / 0 errors / 0 failures / 0 skips**，包含原符号链接用例及 Unix 实际代理路径。这是明确模块范围的独立通过结果，不覆盖或改写上述 62 项诊断运行中的错误。

独立本轮 Windows 检查：Ruff lint、18 文件格式、basedpyright（0 errors / warnings / notes）、109 包锁文件校验全部通过；单元/Mock/TCP 62 项 / 1.365 秒，61 通过、1 明确权限跳过。生产代码和 E2E 测试未变更，既有 managed145/chrome155 各 11/11 的实测不重复执行。Linux 单元验证不代表 Linux Chromium、容器部署或真实平台通过。

## Trellis 验收状态

BR-01/02/03/05/06 的既有组件结论保持；BR-04 原加密/挑战/域名/SSRF/重定向/文件检查与本次实际 OS 符号链接结果合并，组件安全验收已补齐。独立续接审查见[审查记录](../.trellis/tasks/10-21-cnc-browser-reuse/research/check-review-2026-10-22.md)。提交/归档仍按既有本项“不提交 git”的边界单独保留，不能据组件通过推进未满足前置条件的原 01–05。

原 Windows 沙箱外重试的 `.venv/Scripts/python.exe -m unittest discover -s tests/cnc/browser -p test_policy_files_state.py -k symlink -v` 曾返回 `OK (skipped=1)`；该历史仍只表示跳过，不作为本次 Ubuntu 通过的证据。生产平台与部署接入继续按下表原任务处理。

## 真实平台与待接入项

| 项目 | 本轮结论 | 前置 / 所属任务 |
| --- | --- | --- |
| RapidDirect 真实认证/会话复用/失效恢复 | 未验证 | 授权托管会话、身份与认证机制；01/02 |
| RapidDirect STEP 非零几何、完整参数、真价/交期及改参重算 | 未验证 | 既有研究 A/B 零几何/无即时报价；需可报价样件/提取依据；01/02 |
| Xometry US 真实认证/上传/报价 | 未验证 | 账号身份、独立映射/提取与 E2，且 02 真闭环；01/03 |
| 生产 IntentStore、会话仓储/ACL、跨进程账号租约 | 未验证 | 本组件强制注入端口；02/04 提供真实持久实现后集成验收 |
| 正式 Deep Agents 模型异常分析/受控恢复 | 未验证 | 沿用既有选型；本轮无模型调用、不把旧 SDK 探针算成产品；02/03/05 |
| 两轮自动监测与历史/完整 Web 演示 | 未验证 | 两家真链路及既有 SchedulerUtil/业务服务接入；04/05 |
| BrowserSkill 本机/远程配对及接管 | 未验证，未引入 | 只有实际本机登录复用需求才另评估；remote 0.3.1 不支持上传 |
| 生产托管 Chromium/隔离网络/密钥备份/私有 Trace 保留 | 未验证 | 部署环境和 02/05 运行验收；不由本机合成 E2E 推断 |

研究 JSON/Schema/历史平台证据未改，仍 draft 且 automation_enabled=false。禁止通过补造定位器、Cookie、价格、手工结果或放开权限来使表中项目“通过”。

## 2026-10-22 最终独立复核

[最终证据复核](../.trellis/tasks/10-21-cnc-browser-reuse/research/check-final-2026-10-22.md)已完成：Ruff/18 文件格式、类型、Windows 62 项（61 通过/1 权限跳过）、离线 lock 检查通过；原 Ubuntu 符号链接及跨平台结果独立核对，组件验收成立。Linux 扩大诊断仍记录为 58 通过/2 errors/2 skips；未重新执行合成浏览器，不代表 Linux 部署或真实平台通过。任务元数据已同步；不提交或归档。
