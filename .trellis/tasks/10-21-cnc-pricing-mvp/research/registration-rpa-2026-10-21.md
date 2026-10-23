# 首批注册与 RPA 评估补充

日期：2026-10-21。来源为用户当前回答及官方公开资料；未登录用户账号、未上传图纸、未实测 RPA 成功率。

## 用户已确认

用户已注册 RapidDirect，并在 Q-02 确认能正常登录进入报价页；验证频率、自动化可定位性、会话持久性与真实报价尚未实测。

Q-04 更新：用户明确选择第二家为择幂美国 Xometry US，因择幂中国在当前环境无法访问。中国行仅保留为原始调研历史，当前不再推荐用户反复尝试该入口，也不推断美国账号已经开通。

## 推荐及证据

| 平台 | 推荐 | 一手依据 | RPA 判断与待验证项 |
|---|---|---|---|
| RapidDirect | 保留现有账号，第一家优先验证 | [官方帮助](https://www.rapiddirect.com/help-center/)列 STEP/STP 与选择/拖拽上传；[平台说明](https://www.rapiddirect.com/our-platform/)列材料/数量/表面处理及即时/人工报价分支 | 已注册减少准备成本；固定上传/配置/读取流程适合优先验证 Playwright。登录挑战、控件、会话与样件真报价仍待实测 |
| 择幂美国 Xometry US | 用户已明确选为第二家；账号/报价尚未实测 | [美国官网操作说明](https://www.xometry.com/how-xometry-works/)列客户注册、模型上传、工艺/材料/表面/数量配置、价格交期更新及 DFM | 按固定流程验证 Playwright 的工程候选；美元/税运/目的地和材料标准需独立回读，不承诺无验证挑战或真实报价成功 |
| 择幂中国 Xometry Asia | 历史推荐，已被用户选择 Xometry US 覆盖 | [中文官网](https://xometry.asia/zh-hans/)及[IQE 说明](https://xometry.asia/zh-hans/instant-quoting-engine-3/)为原调研依据 | 用户报告当前环境不可达，不推断站方整体停服，不强制继续此入口 |

当前第二家从 [Xometry 美国官网](https://www.xometry.com/)客户报价入口进入，按实时页面完成注册，不进入供应商账号。官方操作说明已读取，但具体账号可用性、选项及报价性质仍待实测；不得虚构无验证码、自动化许可或账号已开通。历史中国 IQE 详情直接抓取超时，原细节来自官方搜索索引。

RPA 排序是依据本项目真实报价闭环、现有账号和公开流程作出的工程判断，不是平台间完成过的自动化对照测试。页面是否可稳定定位、能否复用会话及能否取得明确有效报价，必须由 G-02～07 决定。

## 验证解释

- CAPTCHA 为人机验证，例如图形/滑块/点选；[Cloudflare 说明](https://www.cloudflare.com/learning/bots/how-captchas-work/)。
- MFA 为两个或更多不同因素验证身份，例如密码加认证器/手机验证；[CISA 说明](https://www.cisa.gov/audiences/small-and-medium-businesses/secure-your-business/require-multifactor-authentication)。
- 邮箱/短信一次性验证码可用于注册或单因素登录，不应一概称为 MFA。
- 本项目暂停自动化，让账号持有人在受控浏览器完成验证；恢复后复验身份，加密复用会话，过期/再次挑战时重新处理。不破解、不自动降低安全设置、不在对话中索取验证码。

## 后续输入与技术核验

Q-01～04 均已回答：RapidDirect 第一家，Xometry US 第二家，样件目录与候选已登记。按[首轮步骤](live-quote-validation-2026-10-21.md)人工/受控试价，不重复追问已答内容。CDP 曾失败，后续已临时恢复并读取[实际配置目录](rapiddirect-configuration-2026-10-21.md)，未操作凭据或取得价格；正式 RPA 按 SRS 使用 Playwright。每平台独立 JSON，未知美国选项不复制 RD 值。
