# Xometry 报价方法接入执行计划

## 当前阶段

In progress。用户在最终规划摘要后于 2026-10-25 明确回复“是”，授权开始实施；`task.py start` 已切换为 in_progress。已派发后端和前端 Trellis 实现 agent，文件所有权分离。原 `10-23-cnc-part-config-auto-quote` 的真实平台验收缺口继续保留。

2026-10-25 恢复会话 `01a170c9-ea02-76d1-82db-dceac06fdf60` 后，已恢复原任务指针并完成最终独立检查：报价 77、登录 62、浏览器 98（13 项既有跳过）、前端 6 文件/64 项及相关静态检查通过，最终生产构建再次通过（3988 modules，2m 52s）。当前继续真实托管页面核验；生产 binding 仍未启用，不把方法与隔离测试视作真实报价完成。详见 `research/final-check-2026-10-25.md` 和 `research/resume-2026-10-25.md`。

后续当前站点核验发现 Xometry 身份接口匹配、报价页却明确要求登录的复用缺口。已按 design 限定范围完成登录判断修复与最终独立复核：报价套件实际收集 84 项（原 77 项加并行 JLC 工作的 7 项）、登录 65 项、Xometry owner 9 项及相关静态检查通过。上方 77/62 是首次检查节点；最终结果见独立报告。前端运行代码未变更，最终前端构建仍适用。修复后受控实测正确停在 `WAITING_HUMAN / PROVIDER_VERIFICATION_REQUIRED`，等待用户通过现有账号管理完成平台验证；尚未执行新的报价变更。

- [x] 修复 Xometry 显式登录阻断下错误返回 READY，保留正常有效会话与其他平台行为。新增只读有界就绪检查；登录 65 项、Xometry owner 9 项和相关静态检查通过。
- [x] 复核该修复及回归，记录最终真实页面结果（人工验证待完成，不等于真实报价验收通过）。

### 本次接续的新证据与修复

- [x] 恢复已批准的原任务及文件/账号预检，保留另一文件的既有 uncertain upload。
- [x] 核对当前官网部署源码：`vercel_part_config` 属于 V2 编辑器实验；增加显式 binding 变体门槛并通过 13 项 adapter 测试和独立检查，生产 binding 仍未注册。
- [x] 在同一受控 owner 中记录登录跳转、页面状态及业务响应；证实旧登录落在无控件错误页，未发现验证码/短信挑战。
- [x] 用原账号的独立受控新上下文定位迟到登录结果：密码仅提交一次，回跳报价页发生在按钮等待超时之后，原逻辑未重新核对。
- [x] 补 Xometry 登录提交超时后的有界只读核对、回归及独立检查，不重复提交凭据。见 2026-10-26 实施/独立检查报告。
- [x] 同一只读完成核对覆盖正常成功提交，阻止已实测的加载空壳误报 READY；不重发密码、不扩展 runtime/JLC。最终登录 74 项、owner 9 项及范围静态检查通过。
- [x] 对随后追加的正常成功分支与唯一原生账号控件约束做最终独立复核；2026-10-26 接续后登录 74、owner 9 及范围静态检查通过，无新增代码缺陷，见 `research/login-final-independent-check-2026-10-26.md`。
- [x] 将已核实过时的 Xometry `/account/login/` 固定兜底入口更新为当前官网原生入口 `https://xometry.com/login`，保留 hosted form 复用、单次凭据提交、身份与稳定页面完成核对；新增 6 项实际 submit 入口回归，登录 80、owner 9 及范围静态检查通过，独立检查通过。此改动不代表已解决新版身份缓存衔接。
- [ ] 在当前受控页面确认可用上传入口、精确文件回执和真实报价链路；需要用户文件声明决定时在同一运行询问并等待。

源码证据和本次阶段检查分别见 `research/site-auth-source-2026-10-25.md`、`research/variant-binding-2026-10-25.md`、`research/incremental-check-2026-10-25.md`。登录研究按每次尝试保留独立脱敏 JSON，不把页面就绪或本地检查当作同文件报价验收。

2026-10-26 按用户明确要求记录后暂停；原任务和实施授权保留，未完成、不归档、未提交代码。完整接续入口为 `research/pause-handoff-2026-10-26.md`。同一账号在参考浏览器已核对身份且能打开无登录阻断的空上传弹窗；受控应用会话的新身份缓存衔接仍未解决，未执行新上传或报价变更，正式 binding 仍未启用。

随后用户以指定会话 ID 明确恢复编程，已解除暂停并完成上方独立复核及原生入口修订。新的受控证据确认登录前 legacy、回跳后 Next guest；允许官网原生跳转的同源刷新 GET 返回 404 HTML，不能作为新身份缓存 bootstrap。三次诊断均已关闭资源；没有新的文件/报价变更。当前完整接续入口为 `research/resume-programming-2026-10-26.md`；用户受控窗口登录就绪确认仍待反馈。

## 实施前门槛

- [x] 创建任务并记录用户请求、现有页面入口、后端适配缺口和登录复用边界。
- [x] 阅读 Xometry 技能/引用、现有 quote/login/browser 契约和相关历史证据。
- [x] 完成 PRD、design、implement、research 与 agent JSONL 清单。
- [x] 展示最终规划摘要；随后取得用户明确实施批准。
- [x] 运行 `python ./.trellis/scripts/task.py start .trellis/tasks/10-25-cnc-xometry-quote-methods`，读取 Phase 2.1、before-dev 和相关规范。

## 按顺序执行

### 1. 当前正式链路核验

- [ ] 清点正在运行的服务/受控会话和既有 uncertain upload；只读核对，保留原记录。
- [ ] 在现有允许范围内验证正式托管页面、账号身份核验、主 CAD input/大小限制和远端 part/geometry 证据来源。
- [ ] 核对材料选项标题、工艺/表面处理/extras 依赖、Save Configuration 和重算语义、完整有效值回读、金额/币种/口径/交期。
- [ ] 将可用证据与缺口记入 research；无法核对的选择器不作为已验证 runtime binding。没有精确文件决策不执行出口声明。

### 2. Xometry 方法与持久运行

- [x] 按 Trellis auto 模式派发 `trellis-implement`，首行 `Active task: .trellis/tasks/10-25-cnc-xometry-quote-methods`。优先使用 native context injection，缺失时 child 从 JSONL 加载。
- [x] 指定 worker 文件所有权并要求保留他人未提交改动。后端先明确声明 DTO/固定 API 后，前端按相同契约实现。
- [x] 实现 `xometry.py` 的 page inspection、官方冻结字节上传、解析 receipt、参数设置/保存回读、当前报价读取、只读 reconcile 方法。
- [x] 上传/配置保存/报价触发分别使用现有 durable intent。保存自动重算时避免额外重复触发。超时、取消、确认失败后不重复发送。
- [x] 按需补固定类型声明确认：当前文本版本、服务端文件 hash/actor/run/时间持久记录、owner 命令和独立 intent。新字段保持可选，兼容既有 run/receipt。
- [ ] 正式证据具备后才注册 Xometry binding；其他平台行为保持。对不可用/歧义映射返回明确原因。

### 3. 目标页面方法接入

- [x] 在 `cnc_part_config/index.vue` 保留行入口与权限，连接模块的发起、继续、停止方法。
- [x] 复用 `useAutoQuote` 账号选择、串行轮询、late-response 保护、关闭清理；不新建另一登录运行。
- [x] 在现有弹窗中补充必要声明/参数确认提示和事件；状态结果保持 QUOTED/REFERENCE_ESTIMATE/PENDING_REVIEW 的区别。
- [x] 对新增固定原因维护 allowlist 中文映射；保留已有 CRUD、图纸/平台选择与账号页未提交改动。

### 4. 质量与真实验收

- [x] 添加针对真实 adapter 的有意义回归：精确 buffer/receipt、选项歧义、未知 extras、保存回读不符、声明未确认、旧价/缺币种、未确认操作不重发。
- [x] 回归持久 intent、同 owner 登录复用、身份失效/挑战、权限变化、关闭/重开/取消与租约清理；保持原账号登录接口兼容。浏览器 13 项 opt-in/平台跳过如实单列。
- [x] 运行相关前端 Vitest、类型检查、改动文件 lint/format 和构建。
- [x] 派发 `trellis-check` 对最终实际改动做独立全范围复核，无需产品代码修复；见最终检查报告。
- [ ] 在既有授权与可核对运行上完成真实站点验证；未确认历史上传、未知声明或正式站点条件受阻时只读记录缺口，不制造新上传。
- [x] 逐项记录 PRD 验收证据，区分合成方法验证和真实站点结果；未满足项明确保留，见恢复记录中的 AC 表。
- [ ] 更新必要 spec 与任务进展，按 finish-work 约定收尾；不自动归档旧任务或宣称整个 CNC MVP 完成。

## 相关验证命令

以后端实际测试入口为准；现有 quote 测试基于 unittest 和独立 SQLite fixture，不为此引入整站数据库/Redis。

从 `backend`：

```powershell
uv run --offline python -m unittest discover -s tests/cnc/quote -p "test_*.py" -v
uv run --offline python -m unittest discover -s tests/cnc/login -p "test_*.py" -v
uv run --offline python -m unittest discover -s tests/cnc/browser -p "test_*.py" -v
uv run --offline ruff check --no-fix app/modules/cnc/quote tests/cnc/quote
uv run --offline basedpyright app/modules/cnc/quote
```

Ruff/type-check 同时覆盖实际修改的 login/browser 文件；仅对本次改动做 format 检查。已知基线失败或环境 skip 单独记录，不计为本轮通过。

从 `frontend/web`：

```powershell
pnpm exec vitest run src/__tests__/cnc-part-config-auto-quote.spec.ts src/__tests__/cnc-part-config-quote-api.spec.ts src/__tests__/cnc-part-config-options.spec.ts src/__tests__/cnc-account-login.spec.ts src/__tests__/cnc-account-api.spec.ts src/__tests__/cnc-account-platform-options.spec.ts
pnpm run type-check
pnpm run build
```

按实际改动文件追加 `pnpm exec eslint <files>`、`pnpm exec prettier --check <files>`、`pnpm exec stylelint <changed-vue-files>`。不执行全仓自动 --fix。构建必须在最后一次产品代码修改后运行。

## 风险与回滚点

- 正式站点 DOM/回执/几何/币种尚待当前验证；不能从历史控件猜价格提取。
- 既有 uncertain upload 是真实阻断，不能新 run 绕过。先实现与隔离检查，真实场景按可核对结果报告。
- `login/runtime.py` 是共享所有权边界；仅做必要扩展，变更后登录全回归。
- 优先不用迁移；若确需改变持久结构，说明具体必要性并更新设计。
- 回滚关闭新增 binding，保留运行、声明、receipt 和 intent；不删数据，不变更本机 DNS/代理，不影响原有登录。
