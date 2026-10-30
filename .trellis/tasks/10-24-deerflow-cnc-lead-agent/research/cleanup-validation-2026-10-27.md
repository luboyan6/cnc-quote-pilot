# 2026-10-27 计划修订与旧 Agent 清理验证

## 本轮结论

用户确认“先修改计划并清理旧实现”。已完成该范围的计划修订和代码删除，未安装或实现官方 Client。
旧应用聊天、CNC/MCP/浏览器及其他未提交工作保留；无提交/推送、真实模型/平台调用或用户数据库操作。
后续官方 Client/聊天接入保持 planning，不把本轮清理视为官方能力验收。

本次清理的静态检查通过，但现有回归不是全绿：整体质量门禁未通过，SC-02 / CL-02 保持未勾选。
实现代理与独立复核代理均确认失败路径不经过已删除 Agent，相关 CNC 模型/服务/测试本轮未修改。

## 清理内容

- 删除 app/modules/ai/agent/：13 个源码/资源/说明文件及 10 个专属字节码。
- 删除 tests/ai/agent/：3 个专属测试及 3 个字节码。
- 删除 requirements/agent.txt 和 scripts/cnc_agent_smoke.py；后者仍有 8 处旧模块导入，由独立复核补删。
- 移除旧 agent optional extra 和 AI_AGENT_ENABLED / AI_AGENT_QUOTE_WRITES_ENABLED 两个无调用者设置。
- uv.lock 从 144 包降为 125 包：无新增包、保留包版本零变化，Agno/MCP 依赖保留。
- 移除 19 个仅旧实现需要的依赖：jsonpatch、jsonpointer、langchain、langchain-core、langchain-openai、langgraph、langgraph-checkpoint、langgraph-prebuilt、langgraph-sdk、langsmith、orjson、ormsgpack、regex、requests-toolbelt、tenacity、tiktoken、uuid-utils、xxhash、zstandard。
- 修订现有父任务与四个子任务、规范/索引、十个 manifests；四份旧研究加历史覆盖说明。
- 未运行 uv sync 卸载环境已安装包，未安装官方包。

## 静态、计划与依赖检查

| 检查 | 结果 |
| --- | --- |
| 全 backend 无旧运行层导入、配置引用；旧目录和专属文件移除 | 通过 |
| uv lock --check | 通过 |
| 设置文件 Ruff --no-fix / basedpyright | 通过，类型检查 0 errors/warnings |
| 产品清理范围 git diff --check | 通过 |
| 五任务十个 manifests Trellis validate | 通过 |
| 现行计划本地 Markdown 链接 | 无失效引用 |
| 官方职责与未来实现状态独立复核 | 通过，未声称 Client 已实现 |

官方 API/依赖与取消等后续门禁见 [源码核验](../../10-24-deerflow-cnc-agent/research/harness-client-replan-2026-10-27.md)。

## 迁移保护

唯一 head 为 b76d50ea5d8f，链 a7d30f26b8e1 → 23f445d964cc → b76d50ea5d8f 保持完整。
三条文件 SHA256 前后精确相等：

| Revision | SHA256 |
| --- | --- |
| a7d30f26b8e1 | add4701227b0c13d57127d58c1aa0709b7ad05e660d56d3807c25b1b166ed690 |
| 23f445d964cc | 2526c5c1d9c484d8d03e2d1a76eacee27e5dc49890738588673124724bfb5613 |
| b76d50ea5d8f | f8721347287fa80b9c5b8914e478a75b2dc39b061597f76764c0e43ac86a1fc7 |

仅验证图和文件，不执行用户数据库迁移/降级/清表。历史表不再被运行层使用；Alembic 现有 include_name 过滤继续保护非模型表。

## 隔离回归结果

在 backend/ 使用现有 .venv，按两个独立 pytest 进程运行：
```powershell
.venv/Scripts/python.exe -m pytest tests/cnc/login tests/cnc/browser tests/cnc/quote tests/cnc/upload tests/test_migration_safety.py tests/test_migrations.py -q
.venv/Scripts/python.exe -m pytest tests/cnc/mcp -q
```

| 分组 | Passed | Failed | Skipped | Error | 备注 |
| --- | ---: | ---: | ---: | ---: | --- |
| CNC / 迁移 | 293 | 9 | 13 | 1 | 411.54 秒；9 含 4 常规失败和 5 unittest subtest 失败；另 466 subtests passed，1 warning |
| MCP | 22 | 8 | 0 | 0 | 20.27 秒 |
| 合计 | 315 | 17 | 13 | 1 | 非全绿，不能标全量回归通过 |

### 未通过项

- tests/cnc/login/test_providers.py：既有 Xometry 表单/密码 locator 测试桩缺少 nth（现有 providers.py:309），及 timeout reconciliation 预期 evaluate 3 次、实际 18 次。
- tests/test_migrations.py::test_bootstrap_matches_metadata：SQLite 无法编译现有 cnc_account.pricing_context_json 的 PostgreSQL JSONB。
- MCP：7 个数据库测试在 CncPartModel(upload_authorized=False) 构造时 TypeError；1 个 HTTP 测试因响应 schema 缺少 upload_authorized 而 KeyError。
- 13 skips：12 个 BrowserE2ETests 需要 CNC_BROWSER_E2E=1；1 个 Windows symlink 权限不足。

这些失败由实现代理报告并经独立复核确认属于既有、非本轮改动的 CNC 代码/测试，未为本轮清理扩展修复或削弱断言。

### 测试收集限制

最初合并全范围因 login/test_http.py 与 mcp/test_http.py 同名而收集失败，未完成测试。
随后 importlib 模式与现有 _support / _quote_support 裸导入不兼容，也不算通过。
上表来自拆分后的两个完整进程，保留既有测试结构，不把失败的早期尝试算作通过。
