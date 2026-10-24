# 产品配置自动报价 — 执行计划

## 状态与执行边界

最终规划摘要后用户已明确回复“开始实施”，进入执行。此请求是一条完整用户链路，使用单一任务及顺序工作包，避免将未接通的按钮当作独立完成。

本任务直接承担新增配置入口及报价集成；原 02/03 的平台适配证据与进入门槛需要协调使用。Xometry 在先、嘉立创在后，RapidDirect 延期。真实验证未通过时保留未完成状态，不能用本任务归档整个原 MVP。

## 执行清单

- [x] 创建任务，记录用户请求与账号选择决定。
- [x] 检查登录/浏览器/配置/图纸/API、历史平台研究及原任务边界。
- [x] 完成 PRD、设计、执行计划与 spec/research JSONL。
- [x] 展示最终规划摘要并取得随后明确实施批准，再执行 `python ./.trellis/scripts/task.py start .trellis/tasks/10-23-cnc-part-config-auto-quote`。
- [x] 加载 before-dev、相关层规范以及 UI 实现技能；按项目 auto 模式派发 Trellis 实现 agent。派发首行必须为 `Active task: .trellis/tasks/10-23-cnc-part-config-auto-quote`，明确文件责任、共享工作区与不得覆盖他人改动。

### 工作包 A：平台证据与纵向接口

- [ ] 读取已有 Xometry/JLC 研究并通过既有受控执行器核对当前页面、文件大小限制、参数绑定、几何和返回报价语义；验证真实 DNS/登录。需要桌面或 Orca 浏览器时加载对应技能，不能借个人 profile 替代服务端会话验收。
- [ ] 原始研究不改为已验证；将本次可信定位/映射/无订单触发证据写入本任务 research。先获得 Xometry 可自动化证据，再实现其生产操作；JLC 按顺序单独检查。
- [x] 核验插件模型发现、CNC 路由注册和现有权限模式；确定新持久表位置及迁移 head，保留用户现有迁移。新迁移已隔离验证、SQL 审阅并经用户工具授权应用，见 research/operations-2026-10-23.md。

### 工作包 B：持久化与执行器

- [ ] 新增 quote 契约/模型、最小迁移、事务 repository：run 去重、冻结输入、结果/证据及符合既有协议的 durable IntentStore。
- [ ] 服务端重读配置/平台/图纸/账号，处理零/一/多个账号、权限、上传授权和文件快照；site_type 使用平台记录 ID，不使用旧枚举注释。
- [ ] 在已有登录 owner 内接入有界报价推进、独占账号、阶段续租、只读身份复验、WAITING_HUMAN/resume、取消/终止清理；不跨 task 操作浏览器。
- [ ] 接通 Xometry 可信适配器：官方上传、解析、完整参数回读、报价提取与 validate_quote；再接通 JLC，准确返回系统预估/待审核/真价，不点击未知副作用按钮。
- [ ] 新增报价私有路由、严格输入/响应类型、相同权限与脱敏审计；测试重启/不明回执不重发。状态与结果查询不依赖仍存活的 HTTP DB session。

### 工作包 C：列表与弹窗

- [ ] 给配置每行增加自动报价按钮及行 loading；保留未提交 CRUD/选项变更。
- [ ] 增加账号选择、报价阶段与结果对话框和串行轮询 composable；切换/关闭/卸载保护迟到响应并撤销 object URL。
- [ ] 复用或抽取账号受控浏览器画面，登录/挑战时可操作；自动阶段禁止人工并行改参；验证后同次运行继续且不重复提交。
- [ ] 显示金额/币种/单价或总价/数量/交期原文与参数，区分估价、待审核和失败；报错使用固定中文原因映射。

### 工作包 D：检查与真实验收

- [ ] 派发 trellis-check 复核跨层契约和所有改动；优先修复权限、串账号/串图纸、重复变更和错误成功状态等问题。
- [ ] 自动检查完成后分别运行两站真实链路、同账号登录复用、失效/人工挑战、改数量后的新报价；保存核对结果。
- [ ] 对照 PRD AC-01～06 提交证据矩阵；某平台被阻断就明确标注未验收，不把合成用例计为真实成功。
- [ ] 更新必要 spec，记录本轮改动与检查；尊重现有未提交工作和用户会话提交偏好，按 finish-work 流程结束，不擅自归档原任务。

## 验证命令与关键场景

### 2026-10-23 resumed session: independent site skills

用户进一步要求先完成 Xometry US skill，再创建嘉立创 CNC skill，分别维护站点上传/报价按钮与材料选择流程；同轮授权执行任务所需命令并要求自行验证。此交付复用本任务，不创建新任务，也不代表生产适配器或真实平台报价已验收。

- [x] 恢复指定会话，核对当前服务、产品失败弹窗及既有 uncertain upload，不重发报价/上传。
- [x] 读取 skill-creator 与两个站点已有证据，重新观察 Xometry 材料搜索下拉与嘉立创公开上传页；分别记录当前页面范围和未验证项。
- [x] 先更新并校验 `cnc-xometry-quote`，再独立创建并校验 `cnc-jlc-quote`。
- [x] 对两个 skill 做独立情景审查、引用和格式校验，再安装到项目 `.agents/skills/`；记录验证结果。两站安装后 quick_validate 通过，四文件与审查稿一致，详见 `research/site-skills-completion-2026-10-24.md`。原任务保持 in_progress，保留真实报价验收缺口。

从 `backend` 执行（新增文件名落定后采用真实路径）：

```powershell
uv run --offline pytest tests/cnc/quote tests/cnc/login tests/cnc/browser -q
uv run --offline ruff check --no-fix app/modules/cnc app/plugin/module_cnc/cnc_quote tests/cnc
uv run --offline basedpyright app/modules/cnc/quote
```

如果独立 browser 测试采用 unittest，按既有测试入口拆开执行，不为凑命令导入完整应用 fixture。Ruff/basedpyright 覆盖所有本轮修改，生成 CRUD 的既有基线问题与新问题分别列出；不要用全仓自动修复覆盖用户改动。迁移在隔离数据库验证升级/兼容，读取真实迁移链，不自动作用于用户业务库。

从 `frontend/web` 执行：

```powershell
pnpm exec vitest run src/__tests__/cnc-part-config-auto-quote.spec.ts
pnpm exec vitest run src/__tests__/cnc-part-config-options.spec.ts
pnpm run type-check
pnpm run build
```

追加现有账号测试的实际文件及本轮组件 lint，采用 `pnpm exec eslint <changed files>`、`pnpm exec prettier --check <changed files>`、`pnpm exec stylelint <changed Vue files>`；不运行全仓 --fix 脚本。命令对应现有 package.json，测试路径以实现最终文件为准。

必要行为验证：

- 账号零/一/多选择、平台 PK 非 1/2、跨平台账号拒绝、普通用户越权/禁用/删除。
- 图纸不存在/路径逃逸/不符 STEP/未授权/已变更/超限；实际发送缓冲与冻结 hash 一致。
- 已登录免重复凭据、挑战复验续跑、quote 中只读复验不导航丢配置。
- 重复点击/POST 超时/取消/重启/存储确认失败：mutation intent 不盲重发。
- 60 秒 lease 续期、租约丢失、账号页与报价争用、有界阶段不阻塞整个轮询生命周期。
- 参数依赖/未知键/歧义映射、保存后不同参数、旧缓存价格/错误几何/货币性质不明不得 QUOTED。
- REFERENCE_ESTIMATE/PENDING_REVIEW/FAILED 与真实 QUOTED 分开展示；人民币符号等不明依据不能猜 ISO。
- 前端切行/迟到响应/关窗/离开页面、资源释放、既有账号对话框及配置 CRUD 回归。

## 风险与回滚点

真实出站、平台 DOM 和报价无订单语义均尚未重验，先通过证据门槛再启用适配器，不修改安全策略或以猜测控件继续。owner runtime 是高风险共享文件，改动后必须回归原登录全流程。新增表使用增量迁移，失败回滚入口/执行器并保留结果和 intent，不删除现有凭据、图纸或用户修改。

## 2026-10-23 Chrome DevTools 会话交接

用户要求记录并新开会话接续。当前真实页面已登录并加载配置，尚未点击自动报价；不能声称浏览器端到端验收完成。最终前端66项、后端quote40项及login50/upload12项通过；browser混合DNS契约相关12 failures/1 error/13 skipped仍待解决。生产适配器仍禁用，.setp报价校验兼容和行图标可访问性问题已记录。详细恢复入口：[会话交接](research/session-handoff-2026-10-23-chrome-devtools.md)。任务保持in_progress，无新任务、提交或归档。

## 2026-10-23 Chrome DevTools continuation result

后续会话已在真实配置页点击报价并验证安全失败路径：唯一 Xometry 账号自动选择，运行在 `PROVIDER_AUTOMATION_UNVERIFIED` 终止、`result=null`，未产生该运行的上传/报价 intent；停止运行返回 `CANCELLED`，关闭后无后续轮询且页面恢复空闲。浏览器控制台无 error/warn。地址过滤方案已按用户明确选择同步契约；`.setp` 上传至报价冻结边界已修复并有回归。详细浏览器证据与仍未满足的真实平台验收项见[续测报告](research/chrome-devtools-acceptance-2026-10-23.md)。研究运行 `e8dea2c1-3430-4279-832e-1e655ced79b8` 的 uncertain upload intent 仍保留，禁止盲重试。生产报价适配器仍禁用，Xometry参数回读/同次价格及嘉立创真实报价未验收；任务保持 `in_progress`。
