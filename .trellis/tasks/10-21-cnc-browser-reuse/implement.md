# BR 实施清单

- [x] 检查业务栈、任务树、原有用户修改。
- [x] 只读源码核验参考路径/Commit/方法/调用链/许可/依赖，落盘 docs/browser-reference-analysis.md。
- [x] 确定直接 SDK → 薄 Adapter → 独立 MIT 组件 → 领域最小自研的方案。
- [x] 递归修订六个相关任务的 PRD/design/implement/context，保留原状态/依赖/研究与 bootstrap，新增本项。
- [x] 冻结 docs/browser-implementation-design.md，读取 backend/guides 规范；按用户已确认推进实现的授权开始。
- [x] 实现共用 contracts/policy/session/workflow 与独立 MIT 出站组件，单消费者/账号隔离、会话加密注入、文件校验、只读有限重试、intent 不重放。
- [x] 增加 optional Playwright==1.58.0 与实际 lock 解析，提供安装说明；不改变 Agno/既有路由。
- [x] 单元/Mock 集成：scope、秘密、SSRF、文件/金额/参数、重试/异常/取消/释放与 intent。Windows 62 项中 61 通过/1 权限跳过；原 OS 符号链接负向用例已在现有 Ubuntu 原样执行，1 项通过、0 跳过，详见本轮补验。
- [x] Chromium 合成 E2E：实际 DOM、STEP 文件框、自动等待、参数/报价回读、会话/账号隔离与受控故障；记录浏览器版本。真实平台项单独标未验证。
- [x] 独立 trellis-check 审查/必要修正，更新测试报告、任务审计与执行状态；质量通过后按实际范围收尾，不勾选 01–05 live 条目。既有审查已完成，本次独立复核及 Ubuntu 原用例补齐 BR-04；组件验收通过，Git 提交/归档单独保留。

## 2026-10-22 续作：Windows 连接释放

用户明确要求继续未完成任务，原实现授权与状态保持。续作基线：46 项单元/Mock 中 45 通过、1 项符号链接 OS 权限未验证；Ruff/类型/lock/任务审计通过。安装配套 managed Headless Shell 145/build1208 后，实际 11 项 E2E 中 10 通过、1 项因禁止域重定向后的 Proactor peer-reset 清理失败而错误；没有弱化该验收。

- [x] 在写代码前补充公开 Socket/Streams 所有权 Adapter 设计及来源，保留原 SOCKS/出站政策。
- [x] 只为 Windows 自有接受连接增加 Adapter；准确处理已断开连接的 WinError10054，其他错误仍报告；跟踪 raw→Streams 交接和全生命周期。
- [x] 回归真实 RST、交接失败/取消/关闭后连接、其他错误不被吞掉，再独立检查并实跑完整 managed E2E。
- [x] 同步最终结果到 docs/browser-test-report.md、相关设计/spec 和当前 task.json；保留失败历史和真实平台未验证项。

最终实测：Windows 专项 16/16；完整单元/Mock/本机 TCP 62 项中 61 通过/1 明确跳过；managed E2E 11/11（23.707s）及 Chrome E2E 11/11（37.981s）；Ruff/18 文件格式/全部核心与测试类型检查通过。严格取消/重定向释放断言保持，完整 E2E 日志无之前的 transport/WinError 警告。待补 OS 符号链接用例；参考仓库、原任务状态与真实 live gates 保持。

沙箱外授权重试同一符号链接用例：1 项 / 0.023s，仍为 `UNVERIFIED: Windows symlink privilege unavailable`。不以 skip 作为通过，不变更系统/账号权限；本项因此保持 in_progress。

验证入口：backend 的 Ruff 配置；`python -m unittest discover -s backend/tests/cnc/browser -p 'test_*.py' -v`（避免加载无关全站 DB/Redis fixtures）。真实 Chromium 测试单独可控入口，缺二进制报告未验证，不能仅 skip 后宣称 E2E 通过。实际命令与结果由 docs/browser-test-report.md 记录。

回滚仅停用新增组件/optional extra，保留 intent 与远端记录。参考仓库只读，用户已有 backend README/移动端环境等改动保持；不提交 git，不重置或递归删除。

## 2026-10-22 本次续接：Linux 原用例补验

- [x] 使用已运行的 Ubuntu/WSL2、隔离 Linux Python 3.12.3 环境，不修改 Windows/账号权限。
- [x] 网络超时后按既有 lock 下载标准 Linux wheels 并离线安装最小导入依赖，不修改项目依赖/锁文件。
- [x] 原 `test_symlink_escape_rejected` 实际执行：1 项 / 0.024s / 0 跳过 / exit 0，测试 SHA-256 前后一致；BR-04 已补齐。
- [x] Linux 原跨平台模块 46/46 / 3.385s / 0 跳过；包含 Windows-only Adapter 的扩大诊断 62 项实际 58 通过/2 errors/2 原 Windows skip，完整保留错误，未新增跳过或改测试。
- [x] 独立 Windows 完整组件 lint/format/types/unit/lock 复核；生产代码和 E2E 测试未变更，既有两套 11/11 合成 E2E 结果保留。

命令、环境、Linux 回归及边界见 [Linux 证据](research/linux-validation-2026-10-22.md)与[独立审查](research/check-review-2026-10-22.md)。上文保留的未验证叙述属于之前的执行历史；不得据本次组件验收勾选原 01–05 的平台/业务/部署条件。仍按既有边界不提交 Git，不自动归档。
