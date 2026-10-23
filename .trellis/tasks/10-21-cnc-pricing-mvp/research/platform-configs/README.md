# 按平台加载的 CNC 参数 JSON

本目录是可审阅、可校验的规划配置，尚未接入产品运行时。研发通过规划评审后，迁入 backend/app/modules/cnc/platform_configs/；不得把文件创建称为适配器或真实报价已完成。

正式运行按[固定 Workflow](../../workflow-design.md)执行适配器，[Deep Agents](../../agent-design.md)在未知异常中观察/分析并选择当前允许策略；本 JSON 负责参数/定位/提取及已验证备用变体。Skills 不替代 JSON 或扩展权限，Agent 不改受信配置，新定位建议经工程核验后版本化。

## 当前文件与真实性

用户 D-17 当前顺序：**Xometry US 第一、JLC-CNC 中国站第二、RapidDirect 第三**。先完成前两站及全部既定功能，再开发 RapidDirect；其历史研究配置和未通过证据保留。第二站属于独立 `provider_group=jlc`，不因替换候选而放宽双平台、真价或产品验收条件。顺序是研发决策，不是配置已验证或生产自动化启用依据。

| 文件 | 内容 | 状态 |
|---|---|---|
| xometry_us.json | 美国平台研究配置（当前版本见 JSON） | D-16 指定目录 No 已获用户确认；A/B 非零几何，1/2/5 有三档当前优惠 UI 价，数量 5 刷新回读保留；USD 有协议依据。仍 draft/自动化禁用，生产交期、参数等价及产品闭环未验证 |
| jlc_cnc_cn.json | JLC-CNC 中国站独立研究配置，干净入口 `https://www.jlc-cnc.com/cncOrder/#/placeOrder` | 既有 292.1301C 项有非零几何和系统预估金额；非本轮上传，远端字节身份未证实。`REFERENCE_ESTIMATE` 不满足 E2/QUOTED；币种仅见 ¥，ISO 待核；仍 draft/自动化禁用 |
| rapiddirect.json | 第三站暂缓开发；保留 CNC 页面目录及 Apply/保存后的参数回读依据，版本见 JSON | A/B/C 仍零几何、无真价；新增字段 IDs 未核验，D-15 用户已确认许可范围（未独立审阅协议） |
| platform.schema.json | JSON Schema Draft 2020-12，约束字段类型、配置键与安全规则 | 适用于三份独立 JSON；每次改动需运行全部配置结构校验，不代表业务闭环通过 |

JLC 配置保留协调者在 `2026-10-22T05:57:18.282Z` 的初始只读观察：既有条目 292.1301C、28 × 25 × 9.5 mm、1967.6 mm³；Al6061 未核实热处理态，喷砂/阳极氧化不等同无附加处理，GB/T1804-2000 m级不自动等同其他平台公差。数量 1 的单价/行价 212.51、税额 27.63、含税合计 240.14 均处于“系统预估价”及最终人工审核限定，优惠约 190.14 未应用。其身份、参数、币种、税运和生产交期仍需独立核验，不能宣称双平台完成。初始配置创建时两份归档尚待写入；当前 [实测记录](../../../10-21-cnc-mvp-01-platform-gates/research/jlc-live-validation-2026-10-22.md)与[结构化结果](../../../10-21-cnc-mvp-01-platform-gates/research/jlc-live-validation-2026-10-22.json)均已存在，配置 `2026-10-22.2` 追加了本地归档对账，而非新的平台实测：最后确定读回数量为 1，一次 1→2 请求报错后的数量未知，重试前须读回同一条目；较旧官方指南表明审核报价与订单流程耦合的风险，当前“提交询价”的独立无订单副作用路径仍未核实。不将原始待归档状态或工具错误当作当前永久阻塞，也不据此提升 QUOTED/E2。

JLC 页面声明 STEP/STP 为必需 3D，DWG/DXF/PDF 为补充图纸、最多 20 文件和 `<100M`；仅是 UI 声明，未测试上传边界，不推断字节换算或产品已支持补充格式。只观察到 `www.jlc-cnc.com`，未增加未核实认证/CDN 域。实际绑定与目录保持 null/空；“修改参数”、数量框、uploadFileBut 等只作证据，addCarCNC 禁止购物车动作，“提交询价”边界未明，停止于点击之前。未保留原链接的跟踪查询参数。

RapidDirect 采集时间为 2026-10-21T06:33:40.646Z，范围为当前用户页面、CNC process=1、material=36。读取到 23 分类、244 材料条目、当前 73 表面处理条目和 11 粗糙度条目；数量控件 min=1/max=999999/step=1。这些是组件已加载记录，不保证任意材料/处理/数量组合都可选或可报价。

## 数据约定

- platform_code 是受信注册键：xometry_us → xometry、jlc_cnc_cn → jlc、rapiddirect → rapiddirect；provider_group 用来避免同一服务商不同地区凑数。研究输入探针固定核验三份配置，包含暂缓的历史 RapidDirect 配置；这不是运行时开放任意 provider 的注册机制。
- parameters 定义统一字段、精确映射、依赖、可见性与实际控件绑定。catalog 保留站方原文、数值 ID、分组及条件列表；IDs 仅属于对应平台/上下文，不在平台间复用。
- 子项映射还须匹配 mapping_context：例如当前 Bright Silver=2833 只记录于 CNC/6061-T6/Anodizing Type II Matte=22 这一父级上下文，不能把此颜色 ID 沿用到另一种 Finish。
- catalog 中的 is_auto_price 只是网站目录标记，不是报价结果，也不是已验证性能。材料原数据中的 price/price_3d 等已排除，不能拿材料基础价格当零件加工报价。
- 网站原文 As machined (Ra3.2) 位于 Roughness；与 Finish 分开。阳极氧化、颜色、嵌件、外观件、检验/标记及交期均须保留有效快照，不按名称相似自动等同。
- 当前 live UI 先使用 Finish / Apply，之后显示 Save configuration 和 Cosmetic/Tolerance/Threads/Inserts/Marking/Report；用户截图另为 Surface Finish / Save。分别存为 ui_variants；不能把截图或最初表单的字段范围强制用于所有步骤。
- 06:33 的 surface_finish=[] 是当时未保存状态；09:17 在 CNC/6061-T6 的无价试验中经 Apply 和 A 配置保存后回读为 Not required。该证据不代表几何、可报价性或完整 canonical runtime 映射已通过。test_intent 仍不是冻结默认；截图的 Yes 和本轮页面的 No 都不是用户业务默认要求。
- 空 options/null/未观察字段意味着未知，不意味着网站不支持；不自动转成 No、0、无处理或忽略必填。Other/Custom 没有确定参数时进入人工待办。
- allowed_hosts 约束自动化主动导航；不能由页面文本/模型输出扩展。各站真实重定向域须核验后加入；不复制其他平台白名单或选择器。
- quote_extraction 是提取契约，价格/币种/交期定位器仍为 null。金额只能来自同次已配置零件的报价；Decimal 字符串、单价/行总价、税运 null、原始交期文本分别保存。
- 不在配置存账号密码、Cookie、Token、STEP 绝对路径或会话。登录态在账号隔离的加密存储管理。

## 运行时加载契约（待实现）

1. 后端受信常量注册表将 platform_code 映射到固定 JSON 路径和 adapter_id。拒绝未知键、路径穿越、绝对路径和任意动态 import；不拼接用户提交的文件路径。
2. 启动/发布时用 Pydantic 严格模型加载并校验（JSON Schema 用于配置审阅和静态校验）；拒绝未知可执行配置、重复字段键、非有限数值、无来源映射及依赖循环。
3. API 按 platform_code 返回脱敏参数定义和当前版本；隐藏内部定位、目录原始属性和证据路径。按 process/material/finish 返回可选子集，不向 Web 下发整份原始目录。
4. 任务创建时固定 config_version、文件字节 SHA-256、adapter_version 与完整配置快照/私有归档引用。运行中不热切换；文件改变不影响已排队任务。
5. requested canonical 参数经对应平台精确映射为 platform_value。平台 ID 只能用于核对/当前 UI 选择，不能据此构造未验证的私有 API。
6. 通过确定性适配器选择控件；每次改变材料重读 Finish/Roughness，改变 Finish 重读颜色等子项。发现列表变化、歧义或无匹配就停止，不自动替换最近似值。
7. Apply/Save 前后回读所有有效参数及新增必填项。只有截图/组件目录的配置不能直接开启自动运行：需实测控件、保存效果、几何解析、参数回读和真实报价提取证据。
8. 价格/交期提取采用代码中固定的解析器注册表，不在 JSON 配置任意 JS、表达式或大模型指令。网站返回内容不修改配置权限。
9. 保存 requested/effective、平台原文/ID、配置版本/哈希、价格口径和证据。历史可比性依据完整有效规格与商业口径，不能仅看相同 canonical key；未知项禁止严格比较。

设计伪代码（适配器内部的配置/提取/事务边界，完整 Workflow 与异常分支另见父设计；不是已实现代码）：

    cfg = registry.load_exact(request.platform_code)
    cfg.validate_request(request.parameters)
    pinned = snapshot_config(cfg)
    adapter = ADAPTER_REGISTRY[cfg.platform_code]
    effective = await adapter.configure_and_read_back(pinned, request)
    assert_requested_parameters_match(effective)
    quote = await adapter.extract_displayed_quote(pinned, effective)
    persist_quote_and_evidence_atomically(quote, effective, pinned)

## 配置验证用例

| 编号 | 输入/操作 | 预期 |
|---|---|---|
| TC-CFG-01 | 读取三份 JSON 并做 Schema 校验 | 结构通过，draft 配置仍不可当作已上线适配器；JLC 的系统预估价仍为 REFERENCE_ESTIMATE |
| TC-CFG-02 | 未注册 platform_code、../、绝对路径、附带脚本字段 | 在打开浏览器前拒绝，不读任意文件/执行脚本 |
| TC-CFG-03 | Xometry 直接提交 RapidDirect 的材料 ID 36 | 不复用 ID；映射尚未核验时拒绝自动执行 |
| TC-CFG-04 | 6061 更换材料或改变 Finish | 重新核对子项；旧颜色/粗糙度不能沿用为已验证值 |
| TC-CFG-05 | 数据中含材料 price；Finish 与 Roughness 同名部分相似 | 不当作零件报价，不混淆粗糙度与表面处理 |
| TC-CFG-06 | 建任务后修改 JSON，再执行/重试 | 仍用固定快照；记录旧/新版本，不静默热更新 |
| TC-CFG-07 | 当前 UI 无 Cosmetic/Inserts，截图为 Yes | 有效值保留未知/不适用的证据，不推断 No；不满足请求时不宣称成功 |
| TC-CFG-08 | 当前 Apply 与截图 Save；或同名 Configure 两个 | 使用实际界面变体及样件范围，歧义时停止 |

执行器与接口测试在研发阶段实现；本轮仅运行 JSON/Schema、引用和任务上下文检查，不把其计作真实报价测试。
