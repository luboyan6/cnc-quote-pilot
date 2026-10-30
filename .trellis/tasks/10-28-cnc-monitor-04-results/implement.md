# T4 实施计划

> 待实施，先核对 T1～T3 的实际模型、API、指标和验收记录；本轮未修改 UI 或运行产品构建。

## 顺序

- [ ] 加载 backend/frontend 相关规范及现有 API/页面，读取本项上下文；界面实现时再按项目技能路由加载设计指南。
- [ ] 增加比较/商业口径/证据元数据迁移，旧结果可读且未知字段不补造事实。
- [ ] 统一 list/stats/history/detail/screenshot 记录范围与安全错误，覆盖软删除、越界和跨用户访问。
- [ ] 修正正式/参考/待审和重试分母；增加时间区间指标、Decimal 字符串与可比键历史 API。
- [ ] 建立私有证据读取，新增截图写入私有目录；检查静态挂载绕过；形成旧证据迁移/清理清单并验证后处理。
- [ ] 增加前端批次/计划 API 类型、页面与配置列表批量入口，显式登记菜单/按钮权限。
- [ ] 扩展结果页筛选/卡片/历史/详情与带认证 Blob 截图，沿用现有 Vue/Element Plus/ECharts。
- [ ] 实现串行读取、generation、路由清理与请求/Blob 生命周期，保留原单次对话框关闭协议。
- [ ] 运行定向交互/类型/构建、后端结果权限与指标检查，按父验收执行整链路评审。

## 验证

拟新增 backend/tests/cnc/results/ 的指标、比较、权限、证据与迁移测试；金额/空值/同价、不同数量/币种/quote_kind、最近 N 条以及分母均用实际持久记录验证。

实现后从 backend 执行：

~~~powershell
uv run pytest tests/cnc/results tests/cnc/batch tests/cnc/monitor tests/cnc/quote
uv run ruff check --no-fix app/plugin/module_cnc/cnc_quote_result
~~~

frontend/web 执行：

~~~powershell
pnpm exec vitest run src/__tests__/cnc-quote-batch.spec.ts src/__tests__/cnc-quote-schedule.spec.ts src/__tests__/cnc-quote-result.spec.ts src/__tests__/cnc-part-config-auto-quote.spec.ts src/__tests__/cnc-account-login.spec.ts
pnpm run type-check
pnpm run build
~~~

新测试文件在实施中创建；按最终文件路径更新命令。对变更文件执行 ESLint/Prettier/Stylelint 检查模式；不要全局自动修复。浏览器人工核对批次关闭不取消、人工状态、空结果/失败/无证据、筛选切换、窄屏及表格操作可访问性。

## 评审门与回滚

V-AC01～08 和父 AC-01～14 逐项记录，真实两轮与隔离 UI/接口验证分别报告。若后端接口、金额类型或历史口径有变化，先同步共享契约/前端类型后复验。

回滚采用关闭新增入口与兼容读取，保留历史/Intent/私有证据；不得以删结果或放开截图公共访问解决回归。记录当前实现的限制，再按 Trellis 完成质量/spec/交接阶段。

