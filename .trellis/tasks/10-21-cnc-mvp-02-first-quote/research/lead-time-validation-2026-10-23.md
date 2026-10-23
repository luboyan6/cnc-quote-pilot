# 交期契约续作验证（2026-10-23）

范围：02 已列明的共享交期类型/编解码/校验切片，消费既有 BR。沿用用户继续未完成任务及 D-15/D-17 授权；真实登录/01 E2、正式报价 API/持久化/前端、Agent 与监测的原 gates 不变。实现边界见 [设计](../lead-time-design.md)，证据范围见 [四个现存样例](lead-time-cases-2026-10-23.md)。

## 结果

| 检查 | 当前结果 | 边界 |
| --- | --- | --- |
| 浏览器全量隔离 unittest discovery | 94 项，81 通过、13 跳过 | 12 个显式 opt-in Chromium 场景及 1 个 Windows symlink 权限跳过，不计通过 |
| 登录回归 | 47/47 通过 | 既有 D-18 HTTP/服务/租约/runtime/provider/隐私/Windows 启动回归 |
| HTTP 测试格式修正复验 | 7/7 通过 | 根代理只格式化旧 test_http.py，保留全部断言 |
| Ruff lint | 通过 | browser/login/账号 CRUD 源及测试范围 |
| Ruff format --check | 41 文件通过 | 包含上述 test_http.py 的格式修正 |
| basedpyright | 最终独立检查进行中 | 最终结果返回后补充 |
| managed Chromium 合成 | 最终独立检查进行中 | 初版 12/12 通过；修正 legacy duration 语义后需重新执行，不能沿用旧结果声称新源已通过 |
| 真实平台登录/报价 | 未验收 | DNS 仍返回保留 IPv6 混合答案，现有出站策略拒绝 |
| 运行中 Web 页面联调 | 未执行 | CDP 仅完成安全页面状态读取；后续只读调用报告 master 未运行，未点击账号登录 |

## 实际行为

- `lead_time.py` 为唯一交期值对象、校验和快照编解码所有者；`contracts.py` 保留旧名字导入兼容，`validate_quote` 和 `ValidatedQuote.as_dict()` 复用这一实现。
- version2 明确 duration / production_duration / ship_date / arrival_date，保留原文与来源。日期只保存明确月日和可空年份，不从观察日补年份；日期不混入生产天数或工作日 basis。
- 旧构造和旧四字段快照都归 generic duration。初版将旧记录重标 production_duration 的语义错误已修正；显式 production_duration 需要非空来源。来源和起算点未知时仍为空，不把通用交期声明当作生产语义证明。
- 严格拒绝 bool/浮点天数、无效区间、未知版本/kind、缺字段/多字段、畸形日期、混合字段、无来源日期/生产时长；unknown/TBD 只有文字不能形成已知交期。
- 现存 A/B/JLC 文字仅用于独立值对象回归；workflow 和浏览器仍使用明确标注的合成站点。B PDF 的通用8工作日、JLC 的通用6工作日保留 generic duration，不据此证明生产起点、常规报价或真实验收。
- 价格/币种/范围、几何、身份、参数、新鲜度及 intent 校验保持。当前 QuoteObservation 没有报价性质字段；真实价格性质/REFERENCE_ESTIMATE 判断仍须后续 provider/domain 集成落实，本轮未交付估价状态守卫。

## 命令

在 `backend`，使用当前已安装环境，未改依赖/锁文件或业务数据库：

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests/cnc/browser -p test_*.py -q
.venv/Scripts/python.exe -m unittest discover -s tests/cnc/login -p test_*.py -q
.venv/Scripts/ruff.exe check app/modules/cnc/browser app/modules/cnc/login app/plugin/module_cnc/cnc_account tests/cnc/browser tests/cnc/login
.venv/Scripts/ruff.exe format --check app/modules/cnc/browser app/modules/cnc/login app/plugin/module_cnc/cnc_account tests/cnc/browser tests/cnc/login
.venv/Scripts/basedpyright.exe app/modules/cnc/browser app/modules/cnc/login app/plugin/module_cnc/cnc_account tests/cnc/browser tests/cnc/login
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Resolve-Path ..).Path '.trellis/.runtime/playwright-browsers'
$env:CNC_BROWSER_E2E = '1'
.venv/Scripts/python.exe -m unittest discover -s tests/cnc/browser -p test_browser_e2e.py -v
```

默认 discovery 的 skip 与随后显式启用 Chromium 的结果分别记录。前端未改，未重复前端构建；上轮 D-18 前端检查仍见 [原记录](login-validation-2026-10-22.md)。本轮未执行真实平台认证、模型/报价提交、订单/支付或用户安全设置操作，未修改 DNS/网络策略，也未启动正式报价 adapter。

## 仍未完成

正式领域 DTO/JSON 持久化/报价 API/前端展示须共用该 v2 decoder/serializer，并在原 01 首平台 E2/报价前置满足后集成。还需真实账号首次登录/复用/挑战、完整参数映射保存/依赖回读、同次真实价格性质/证据、真实 Workflow/Agent 恢复、第二平台及后续批量/监测/整体验收。不以此组件完成标记 02 整体完成或自动归档。
