# 自动报价问题排查记录（2026-10-23）

## 结论

当前卡点不在登录网址、报价入口网址或 STEP 文件定位。使用 Chrome DevTools 通过本地产品配置行点击一次“自动报价”后，账号读取、报价启动及状态轮询均返回 HTTP 200；受控平台会话通过身份校验后，报价执行在 `PROVIDER_AUTOMATION_UNVERIFIED` 安全门处终止。当前生产代码没有已验证的平台报价适配器，因此不会继续点击第三方上传控件、发送图纸、配置参数或读取价格。

## 四项核对

1. **登录网址：可用。** 数据库中 Xometry 平台入口为 `https://login.xometry.com/u/login`，报价入口为 `https://www.xometry.com/quoting/home`。调用 `resolve_provider()` 的本地检查返回 `xometry_us`，两个 HTTPS 地址均通过当前受控 host 策略。运行时先打开报价入口并验证身份；需要登录时再打开配置的登录入口。当前执行抵达报价适配器检查，故不是卡在登录 URL / 身份校验。
2. **报价页面：可打开。** 当前账号与平台配置匹配；受控浏览器运行顺序包含导航到 `quote_entry_url` 并复验身份。历史受控 Xometry 研究会话也已到达报价上传草稿页。需区分：本次本地产品 UI 的报价弹窗不是外部报价页面；生产自动报价在身份验证后被适配器门禁截停。
3. **STEP 图纸：可以找到并通过上传前基础校验。** 使用生产 `source_file()` 和 `TrustedStep.read_verified()` 对配置关联文件做只读复核：找到 `.step` 文件，300,561 bytes，文件大小与数据库一致、位于配置上传根目录内，Part 21 起止标记有效，SHA-256 冻结后复核一致，且 `upload_authorized=true`。`validation_status=PENDING` 表示仍未完成几何/可加工性验证；此处只证明文件存在、基础格式和字节身份有效，不代表 CAD 几何已解析。
4. **第三方上传按钮：当前不能由产品流程自动点击/上传。** `backend/app/modules/cnc/quote/providers.py::resolve_quote_adapter()` 当前固定返回 `None`；`runner.py` 在此处抛出 `PROVIDER_AUTOMATION_UNVERIFIED`，发生在适配器 `upload()` 之前。`browser/files.py` 的通用 `upload_step()` / `upload_step_with_chooser()` 只是基础能力，没有 Xometry 适配器去绑定已验证的页面控件。

## Chrome DevTools 本次实测

- 页面：`http://localhost:5180/web#/module_cnc/cnc_part_config`，配置行显示 Xometry、6061-T6x、数量 1、Standard 和关联 STEP。
- 通过 DevTools 对该行自动报价图标仅点击一次；账号列表 `GET /api/v1/cnc/cnc_part_config/1/quote/accounts`、启动 `POST /api/v1/cnc/cnc_part_config/1/quote/runs`、状态轮询均为 HTTP 200。单账号自动选中，无账号选择弹窗。
- 本次 run：`3804d1cd-84fb-486e-b73a-5f326809cb95`；最终 `FAILED / prepare / PROVIDER_AUTOMATION_UNVERIFIED`，`result=null`。弹窗展示固定中文失败说明，没有价格；控制台无 error/warn，行操作 loading 已清除。
- 只读数据库复核：本次 run 没有 upload/configure/submit intent；无运行中任务、账号租约已释放。历史研究 run `e8dea2c1-3430-4279-832e-1e655ced79b8` 仍存在一条 `upload/uncertain`，没有重试或删除。

## 根因与后续

这是生产平台适配器尚未验收、因而故意 fail-closed 的能力缺口，不是 DevTools 点击失效，也不是登录/本地文件路径错误。要让第 4 项通过，需在不重放 uncertain upload 的前提下完成平台上传控件/文件选择语义、上传收据重对账、参数设置与回读、当前报价解析和价格语义的独立验证，然后再注册适配器。不能用猜测 selector、历史价格或模拟价格绕开门禁。

另外，行操作目前是无 `role` / `aria-label` / `tabindex` 的图标 DIV；本次 DOM 点击正常，故不是本次执行失败根因，但属于独立的可访问性问题。

## 证据

- `chrome-devtools-evidence-2026-10-23.jsonl`：当前 DevTools 页面检查与本次单击、弹窗和请求记录（local request IDs 31427–31439）。
- `quote-runtime-inventory-2026-10-23.json`：此前只读运行时基线；本次 run 状态、intent、lease 已另以只读数据库查询复核。
- `xometry-upload-evidence.json`：既有受控研究上传记录；其不确定 intent 仍按 no-retry 保留。
