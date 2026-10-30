# 源码融合计划核对（2026-10-29）

## 本轮范围

只修订现有父任务与 Lead、聊天、报价、批量监测结果四个子任务的计划、元数据、上下文和对应 Agent 规范。
采用 DeerFlow 必要源码按当前 FastAPI 模块/服务职责适配的方案；没有运行时 Client/Gateway 依赖，不整目录移入。
本轮未创建或激活任务、未移植产品代码、未安装依赖、未操作用户数据库、未运行模型或真实平台、未提交推送。

## 已执行检查

- 对五个任务分别执行 `python ./.trellis/scripts/task.py validate <task-dir>`，implement/check 共 10 份 manifests 均通过，所有引用文件存在。
- 检查五份 task.json 的 planning 状态、源码融合架构标记、未授权产品实施标记、父子关系和前置依赖：通过。
- 检查现行 PRD/design/implement、任务图和共享契约的本地链接及代码围栏配对：通过。
- 保留父 R-01–09 / AC-01–09，以及子任务 L/C/P/M-01–06 和 LA/CA/PA/MA-01–06 的需求/验收映射；产品验收均未误勾通过。
- 检查当前文档/manifest 不再将 Client-only 作为现行接入约束；旧架构仅保留于历史记录/previous_architecture。
- 核对当前 `app/modules/cnc/`、DOMAIN_CONTROLLERS、AuthSchema、async_db_session、lifespan 和已有批次/计划/结果页面；已移除重复基础建设清单。
- 对已跟踪的规范索引执行 `git diff --check`，通过；其他改动为既有未跟踪任务文档/规范，按内容检查。

## 仍未验证的实施门禁

源码依赖闭包/安装、真实融合图、首 token 前一秒内停止、模型/用户隔离、checkpoint 重启及平台报价验收均未执行。
这些属于后续实施工作，不以规划核对替代。旧清理回归失败记录保留，本轮未扩大到修复既有业务。
源码参考提交、组件取舍及历史覆盖关系见 [本轮依据](source-integration-replan-2026-10-29.md)。
