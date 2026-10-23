# RapidDirect 实际配置页与目录采集

后续实测（2026-10-21）：A/B 的 Apply/Save configuration 已执行，发现 Apply 后新增必填字段且当前样件无即时报价；empty Finish 回读为 Not required。详见[子 01 实测](../../10-21-cnc-mvp-01-platform-gates/research/live-validation-2026-10-21.md)和配置版本 `2026-10-21.2`。下文保留首次只读采集的时间与限制，不代表当前尚未点击 Apply。

2026-10-21。来源为用户两张截图和已授权 CDP 浏览器读取；不含登录凭据、Cookie 或会话文件。平台参数文件见 [rapiddirect.json](platform-configs/rapiddirect.json)，统一契约见 [配置说明](platform-configs/README.md)。

## 用户证据

- [配置截图](evidence/rapiddirect-user-configuration.png)：Process=CNC Machining；材料 Aluminum 6061-T6 | 3.3211 | AlMg1SiCu；Surface Finish=Anodizing Type II Matte；颜色 Bright Silver；Roughness=As machined (Ra3.2)；Cosmetic part=Yes；Inserts=Yes；Part Marking/Inspection Report 未选；Quantity=1；按钮 Save。
- [零件卡片截图](evidence/rapiddirect-user-part-card.png)：D14 文件条目存在，材料/粗糙度未设置，提示 Please configure your part to get a quote；尺寸显示 0 x 0 x 0mm。存在顶部批量 Configure 与右侧单零件 Configure。
- 截图只能证明上传条目及可见字段，不能证明几何解析完成、配置已保存或价格已生成。0 尺寸是待核实状态，不直接判为文件损坏。

## CDP 连接恢复与实际行为

1. 工具最初返回 TMWebDriver master 未运行。找到本机现有 E:/AIWorkspace/cdp-bridge-mcp 源码和 SOP；18765/18766 无监听。该目录 .venv 未装 mcp，未安装/升级依赖。
2. 通过已获批准的只读进程查询定位当前 MCP 使用的现有 uv 缓存 Python；从现有代码临时启动仅绑定 127.0.0.1 的 master，浏览器扩展已接入。临时进程最长 900 秒，不是产品后台服务/部署方案，可能到期；正式 RPA 不依赖此临时工具修复。
3. browser_get_tabs 成功，仅操作 app.rapiddirect.com 的现有业务页。browser_observe 返回 Unknown cmd: semantic（工具/扩展能力不匹配）；改用 browser_execute_js 只读 DOM 和参数组件 props，不读取账号信息。
4. 确认当前页面只有目标样件，并点击该零件范围的 Configure；未点击 Apply/Save，未改数量/材料/处理，未新上传文件或提取报价。
5. 只读提取 MaterialSelect、FinishSelect、RoughnessSelect 的 options 与平台 ID、数量控件边界。排除价格、图像、自由描述等非参数属性。此读取用于配置调研，正式适配器不能依赖框架内部状态写入或绕过可见界面。

## 实际读到的界面

时间：2026-10-21T06:33:40.646Z；页面 origin=https://app.rapiddirect.com，path=/quote/detail3.0；过程 CNC (value=1)，当前材料 value=36。

| 项目 | 实际观察 | 限制 |
|---|---|---|
| 材料 | 23 分类，合计 244 材料条目 | 当前组件已加载目录，不保证每项/组合可报价；保留状态字段 |
| Finish | 当前 6061-T6 下 73 条记录，value=[] | 未选/未保存，不能自行断言无处理已生效 |
| Roughness | 11 条记录，value=5，显示 As machined (Ra3.2) | 不等于 Finish，单位未从控件明确核实 |
| Quantity | value=1，min=1，max=999999，step=1 | 控件限制不等于网站可为全部数量即时出价 |
| 按钮 | 当前实际为 Apply，返回按钮 Back to quote | 截图另为 Save，需保留变体上下文 |
| 额外字段 | 当前可见配置表未显示 Cosmetic/Inserts/Marking/Report | 不推断为 No 或平台整体不支持 |
| 价格/交期 | 尚未取得 | 没有执行真实价格核对或改数量重算 |

## 已观察的 DOM 绑定

| 目的 | 实际选择器 | 作用范围 |
|---|---|---|
| 单件配置入口 | .parts-list-card .configure-btn-wrapper button | 当前只有一个目标零件；多件时须按远端零件引用限定，不用 nth 猜测 |
| 工艺 | form.el-form .el-select input[placeholder='Please select process'] | 当前可见单件表单 |
| 材料 | form.el-form .material-select__trigger | 同上 |
| 表面处理 | form.el-form .finish-select__trigger | 同上 |
| 粗糙度 | form.el-form .roughness-select__trigger | 同上 |
| 数量 | form.el-form input[role='spinbutton'][aria-label='Qty'] | 同上 |
| 保存配置 | form.el-form button.apply-btn | 仅观察到按钮；保存效果尚未执行 |

这些绑定已观察存在，不代表跨会话、批量页或网站升级后仍稳定。执行时要求 origin、页面状态、可见性及唯一性；下拉选项定位和结果定位尚未实测，不虚构。

## 后续真实验证

先让 A 文件完成一次明确配置并保存，回读尺寸/材料/Finish/Roughness/数量，再记录实际金额、币种、价格范围和交期。若尺寸持续为 0 且预览无法加载，先排查解析状态/等待时长，再限次尝试 B；不得宣称已通过几何校验。人工审核、参考价和无价分别记录，不能用目录 is_auto_price 或材料 price 替代。
