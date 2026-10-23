# MVP 执行计划（待最终规划评审）

当前平台修订（D-17，2026-10-22，用户已答复）：**Xometry US 第一（platform_code=xometry_us，provider_group=xometry），嘉立创 CNC 中国站第二（platform_code=jlc_cnc_cn，provider_group=jlc），RapidDirect 第三并延期**。可信入口为 https://www.jlc-cnc.com/cncOrder/#/placeOrder；不保存跟踪查询。当前目标覆盖前两平台全部既有功能；RapidDirect 要到前两平台功能与整体验收完成后再实施，不作为 02～05 的前置。此前 RD→Xometry 的选择/实测仅保留历史范围，具体以父 decisions.md D-17 为准。用户既有顺序实施授权继续有效，无需重新创建任务或重复审批。

进入规则：01 按 Xometry US 的真实首平台 G-01～G-07/E2 与安全停止点交接 02；02 真闭环及 01 嘉立创 CNC 的第二平台 E2 满足后才能全面实施 03；04/05 依赖前两平台真实链路。第二家待核验不会阻止首家满足门槛后进入 02；完整 MVP 仍必须两家独立 provider_group 的真实 QUOTED，不用同集团入口、参考价或待审核补数。Xometry 现有 A/B 人工受控报价不是完整 E2/E3；嘉立创目前观察到的系统预估价为 REFERENCE_ESTIMATE，不通过真实报价 gate。产品自动登录/加密会话/关闭重建 context 的实现与验证归 02/03，不能把尚未实现的产品会话能力倒置为 01 开发前置。

执行更新（2026-10-21）：用户已明确要求按现有 01 → 05 顺序实施，开发授权已记录，不再等待新的规划批准。子 01 已启动并完成本轮可独立的输入探针/验证记录；产品模块尚未开始。两家 G-01 的适用许可、几何及真实报价仍未通过，后续子项依照原进入条件等待；详见 [execution-status.md](execution-status.md)。本文件是可执行清单，不替代 implement.jsonl/check.jsonl。

## 进入研发前

- [x] 原始需求/SRS、仓库依据、父子范围与独立验收已登记。
- [x] Q-01～04 已回答；原平台选择由 D-17 更新为 Xometry US 和嘉立创 CNC，样件 A/B 引用已知；无新的范围选择题。
- [x] 用户新增逐网站 JSON 要求；旧 RD/Xometry 两配置及 Schema 已创建；D-17 后当前对为 Xometry US/嘉立创 CNC，各自未验证项保持未知，RD 目录仅作延期历史。
- [x] 用户指定 Deep Agents；已核验 SDK 基线 `0.7.29`，API/AgentSeek 参考范围已登记，见 agent-design.md / research/deepagents-2026-10-21.md。
- [x] D-13 协同分工已写入 workflow-design.md：固定 S01～S11、异常 E01～E13、Agent 在当前异常中选择受限策略、代码守卫/复验和固定恢复位置。
- [ ] 实施前复核最新非预发布/非撤回版本，解析并锁定 SDK/provider/checkpoint/浏览器依赖；实际模型工具调用和持久恢复未验证。
- [ ] Xometry 首平台完整 E2 与嘉立创真实报价仍待核验，不能从局部数值预填成功；使用子 01 时间盒。
- [ ] 读目标层 Trellis 规范，审阅 design.md 及各子交付，完成最新规划评审后才 task.py start。

## 5 天关键路径

| 日 | 任务与代码顺序 | 交付/完成标准 | 风险与降级 |
|---|---|---|---|
| 1 | 01：Xometry US A/B 受控真价/交期/参数核对；嘉立创 CNC feasibility；JSON 映射/证据；Deep Agents 最新版与模型/checkpoint 接入检查 | 首家人工可核对真价；两家 gate 与 SDK 技术未知分开记录 | 解析/审核限时排查；模型缺配显式记录，不以人工试价算 Agent 自动成功 |
| 2 | 02：loader/最小数据→固定 S01～S11/转移表/session/Xometry US adapter→E01～E13/恢复策略执行器→Deep Agents 恢复工厂/只读观察/策略 Schema/守卫/复验→API/证据 | 正常首价+改参、未知异常实际策略选择/恢复、step/incident版本与幂等预算到位 | 小 API/CLI 优先，正常步骤不增加模型选择；禁止开放业务规划/任意恢复动作 |
| 3 | 03：补嘉立创 CNC JSON/映射/适配器/Skills，复用 Agent 工厂、工具与提取规范 | 两个不同 provider_group 的 Agent 真价，同图同参数证据及首家回归 | 规格无法等价明确标记，不复制 Xometry US 或 RD IDs、不新增第二套 Agent 循环 |
| 4 前半 | 04：12 明细、租约/幂等/限流、每 item/thread、checkpoint 恢复/取消、既有 scheduler、两轮历史 | 重放/重启/重复 tick 不重复发；同价新观测保留且用量可追踪 | 砍跨平台并发/高级图表，保留持久恢复和共享预算 |
| 4 后半～5 | 05：Web 正常步骤/异常/策略/复验/待办/用量/结果/历史/证据/CSV，20 连续实测 | 两家 Workflow 真价/改参、真实 Agent 异常恢复分别验证，TC-DA/TC-WF/P0 可复算 | 报告实际偏差；受控异常 fixture 不替代平台 live 报价 |

## 分阶段检查与交接

1. 01 验证报告和候选 JSON 交接 02；账号凭据不入任务目录。01/02 期间可继续人工验证第二家，全面适配编码在第一家闭环后。
2. 02 首条链路通过，再按相同请求/结果契约接入 03；解析器/状态/金额规则变更同步两家回归。
3. 04 只消费 02/03 已可用适配器；task/item 与监测轮次去重分开。参数定义从对应固定 JSON 版本提供给 API/Web。
4. 05 用实际样件/实际配置版本生成报告，记录账号人工接管次数，不将手工试价并入无人干预成功率。
5. 每个阶段继承 agent-design.md 和 workflow-design.md；02 的固定流程/门控、模型/Skills/工具/SDK 版本和持久预算贯穿 03～05。平台差异放 adapter/JSON，人工恢复按服务端 resume_step；不读用户当前激活模型覆盖冻结配置。

## 验证命令与统计边界

以下命令为拟执行入口，产品测试文件/Playwright 依赖尚未实现；不要在文件不存在时伪报通过。按子任务范围运行，发现新失败才扩展检查。

- backend 工作目录：uv run --offline pytest tests/cnc/ -q（对应阶段测试完成后）；既有安全/调度/迁移被改动时针对性回归 tests/test_security_defaults.py、test_scheduler_schedulability.py、test_migrations.py。
- backend 工作目录：uv run --offline ruff check app/modules/cnc tests/cnc（依现有 Ruff 规则；检查格式可用 ruff format --check 指定变动文件，不全库改写）。
- frontend/web 工作目录：pnpm run type-check；pnpm test -- <本阶段测试文件>；pnpm run build。现有环境/依赖目录不代表这些命令已通过。
- 规划上下文：python ./.trellis/scripts/task.py validate .trellis/tasks/<子目录>。
- JSON：用现有 Python json/jsonschema 校验 platform.schema.json 和当前前两平台文件；另检重复键、证据引用、平台隔离及无价格冒充。静态校验不能证明 RPA 接通。
- live 验收：记录 2×2×[1,2,5] 组合，每平台连续 10 项，总 20；保留所有失败/等待/人工介入，不剔除失败美化均值。按 SRS 报告均值/P95/墙钟吞吐和分母。
- Agent/workflow 检查：实现后在 backend 运行 `uv run --offline pytest tests/cnc/ -q` 的适用用例，覆盖 S01～S11、E01～E13、TC-DA-01～10、TC-WF-01～06。验证正常路径无模型依赖、异常策略选择/拒绝/守卫/复验、未决副作用不重发、步骤/incident版本、重启和预算；真实模型/受控页面与平台 live 分开记录。

## 高风险文件与回滚点

backend/app/__init__.py 的生命周期、api/v1/routers.py、core/ap_scheduler.py、模型发现与 Alembic、权限种子、私有数据目录的访问路由、crypto_util 调用、平台配置版本归档，以及 backend/pyproject.toml/uv.lock 的依赖解析、checkpoint 生命周期/私有持久卷、Agent 事件脱敏与模型工厂。复用现有能力，避免重写共享基类/调度锁或已有 Agno 聊天模块；不改用户已有 backend/README.md、移动端 .env 或未授权其他目录。

分阶段保留代码/配置/SDK/Skills/流程/策略版本与数据库/checkpoint 备份；回滚前关闭新领取/策略执行/恢复并安全停止，不删除历史/未决 intent/源模型。旧 checkpoint 只按匹配版本恢复。单独停用异常 Agent 时明确标记恢复能力不可用，正常已知流程可继续、需要 Agent 的异常转人工，不能计为自动恢复成功。提交/归档由主会话处理。

## BR-2026-10-21 实施增补（合并共用实现）

- [ ] 读[统一设计](../../../docs/browser-implementation-design.md)和[BR](../10-21-cnc-browser-reuse/prd.md)；复用基础组件。
- [ ] 所有平台/调度消费同一 Browser Executor，保留固定 Workflow 与受控异常 Agent。组件和真价分级验收，AC-01～13 不因合成测试而勾选。
- [ ] 新增共用修订任务先交付组件，原 01→02→03→04→05 的真实业务进入条件不变。
- [ ] 执行 MVP-BR-01/02 与原用例，记录命令/环境/失败/未验证项；秘密/STEP 不进模型或日志，Trace 仅私有授权诊断。
