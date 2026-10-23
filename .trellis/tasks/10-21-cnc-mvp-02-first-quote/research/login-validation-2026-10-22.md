# D-18 账号自动登录验证（2026-10-22 至 2026-10-23）

范围：现有账号列表登录入口、服务端受控浏览器会话、Xometry US/嘉立创 CNC 登录适配、账号凭据/响应/日志保护。用户已确认受控浏览器方案及实施；沿用任务 02，未创建新任务。任务 02 整体报价闭环仍未完成，03/05 整体 gates 不变。

## 最终检查结果

| 检查 | 结果 | 边界 |
| --- | --- | --- |
| 登录后端 `test_*.py` | 47/47 通过 | 独立 HTTP、服务、runtime、provider、实际 SQLite 事务、日志保护及 Windows 启动循环 |
| 真实 Chromium 合成 `browser_e2e.py` | 3/3 通过 | 实际生产适配器/BrowserExecutor；精确 HTTPS 测试响应，无真实平台凭据 |
| 共用浏览器回归 | 发现 73 项，61 通过、12 跳过 | 11 项原 opt-in 浏览器场景及 Windows symlink 条件跳过，不计为 live 通过 |
| 前端 CNC 账号定向测试 | 15/15 通过 | API 写字段白名单、按钮/form、状态/画面、取消/晚到、清理、坐标和输入节流 |
| 后端定向 Ruff / basedpyright | 通过，0 类型错误 | 覆盖登录、账号及本次必要共用修改 |
| 前端定向 ESLint / Prettier / Stylelint | 通过 | 未对全仓执行自动格式化 |
| 前端 vue-tsc | 通过 | 包含最终输入节流和提示修复 |
| 前端生产构建 | 通过 | 最终源代码执行 vue-tsc + Vite，3973 modules，Vite 3m52s |
| 受控浏览器真实平台认证 | 未通过验收 | 公网 DNS 前置阻断；没有真实凭据提交，不能用合成结果替代 |
| 全报价 / Agent / 监测 / 双平台验收 | 未执行 | 不在 D-18 登录切片完成范围内 |

## 可复现命令

在 `backend` 下，使用当前已安装依赖的 Python（不自动改锁文件或用户数据库）：

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests/cnc/login -p test_*.py -q
.venv/Scripts/python.exe -m unittest discover -s tests/cnc/browser -p test_*.py -q
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Resolve-Path ..).Path '.trellis/.runtime/playwright-browsers'
.venv/Scripts/python.exe tests/cnc/login/browser_e2e.py -v
.venv/Scripts/ruff.exe check app/modules/cnc/login app/plugin/module_cnc/cnc_account app/modules/cnc/browser/policy.py app/modules/cnc/browser/session.py app/core/base_crud.py app/core/database.py app/core/logger.py app/core/server_loop.py app/__init__.py main.py tests/cnc/login
.venv/Scripts/basedpyright.exe app/modules/cnc/login app/plugin/module_cnc/cnc_account app/modules/cnc/browser/policy.py app/modules/cnc/browser/session.py app/core/base_crud.py app/core/database.py app/core/logger.py app/core/server_loop.py app/__init__.py main.py tests/cnc/login
```

在 `frontend/web` 下：

```powershell
pnpm exec vitest run src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-platform-options.spec.ts
pnpm run type-check
pnpm exec eslint src/api/module_cnc/cnc_account.ts src/views/module_cnc/cnc_account/index.vue src/views/module_cnc/cnc_account/AccountLoginDialog.vue src/views/module_cnc/cnc_account/useAccountLogin.ts src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-platform-options.spec.ts
pnpm exec prettier --check src/api/module_cnc/cnc_account.ts src/views/module_cnc/cnc_account/index.vue src/views/module_cnc/cnc_account/AccountLoginDialog.vue src/views/module_cnc/cnc_account/useAccountLogin.ts src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-platform-options.spec.ts
pnpm exec stylelint src/views/module_cnc/cnc_account/index.vue src/views/module_cnc/cnc_account/AccountLoginDialog.vue
pnpm run build
```

## 关键证明和修复

- HTTP 使用真实账号 router/权限依赖，隔离仓库及会话对象；每条登录/画面/输入/验证/关闭路径都检查权限和 owner。错误/审计不会回显人工密码、密文或 SQL 绑定值。普通 CRUD 查询/导出也只保留公开字段，密码留空编辑不会清空原密码。
- 临时 SQLite 使用真实独立提交事务，覆盖并发 claim、过期接管、旧 fencing token 不能释放新租约、旧明文加密迁移，以及续期读后在最终写前过期。最终 UPDATE RETURNING 无行必须失败。这不等同 PostgreSQL 部署或多机验证。
- runtime 实现单 owner task 和有界队列；测试覆盖有效态免提交、身份不符、挑战、超时/取消、关闭立即重开、租约释放和终态清除秘密引用，尚无独立队列满回归。活动命令取消须结算 future，私有会话包装保留固定 LoginError 原因而不放宽共享异常脱敏。
- 前端按行阻止重复创建，拒收旧请求/Blob，关闭/卸载释放同一会话。发送输入后预留 110ms 间隔，避免快速滚动/按键命中服务端 10/s 限制导致断连；无自动重发不确定输入。
- 数据库引擎隐藏参数，`DATABASE_ECHO=debug` 收敛为只输出语句级日志；aiosqlite 保持 WARNING，禁止驱动 DEBUG 和结果行输出账号内容。实际同步/异步 `SELECT :secret` 的参数与查询结果均未进入捕获日志；非账号 CRUD 原异常日志行为保留。
- 安装的 Uvicorn 0.49 Windows 默认 reload/多 worker 循环为 Selector，无法启动 Playwright 子进程。`main.py` Windows 路径改用可导入 Proactor factory，其他平台保留 auto；回归从真实 CLI 参数构造 UvicornConfig，在普通/reload/双 worker 配置下实际启动无副作用子进程。未启动业务 app/数据库，也未据此宣称已验证真实部署负载。

## F-LOGIN / D-LOGIN 验收归属

| 验收 | 本轮证据 | 仍需补齐 |
| --- | --- | --- |
| F-LOGIN-01 首次登录/免重复提交/关闭恢复 | 单元及真实 Chromium 合成通过 | 两站真实授权账号的相同链路 |
| F-LOGIN-02 失效/挑战/错误/禁用/权限 | 离线、接口及合成挑战通过 | 真实平台失效与挑战场景 |
| F-LOGIN-03 同一画面及目标身份 | 私有 JPEG、同 context、明确身份匹配/不符合成通过 | 真实询价页目标账号核验 |
| F-LOGIN-04 无秘密响应/导出/日志 | 接口/实际服务及日志保护回归通过 | 部署日志、代理与运维配置复核 |
| D-LOGIN-01 列表入口/反馈/交互/清理 | 15 项前端回归及类型/样式检查通过 | 连通环境下真实用户全流程联调 |

公开依据、身份接口传输机制及 DNS 观测详见 [平台登录依据](login-provider-evidence-2026-10-22.md)。本机对两个平台返回含 `2001:2::/48` 的保留 IPv6 混合答案，生产出站策略拒绝连接；没有修改 DNS/安全规则。密钥和 Playwright 安装继续沿用 [运行说明](../../../../docs/cnc-account-login.md)。尚未登录不显示 READY；没有明确身份响应就保留人工处理或固定失败状态。

工作区还包含本轮开始前的 CNC、迁移、生成器和环境修改；本轮未自动提交、归档或修改用户网络环境。后续先在真实公网解析环境补齐授权账号登录验收，再按原 01/02 的前置继续完整报价链路。
