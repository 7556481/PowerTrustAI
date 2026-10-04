# 首批英文官方资料：电压稳定与无功控制

检查日期：2026-10-02（Asia/Shanghai）。本轮只收集资料，未修改业务代码、安装依赖、实现解析器或执行 OCR。

原件为英文 PDF；本说明只是选材导航，不作为 Evidence 或原文替代品。
完整元数据、下载结果与失败 URL 见 [manifest.json](manifest.json)。
13 个问题及定位见 [development-questions.json](development-questions.json)：全部是模型根据已读内容提出、**待人工复核的开发集**，不是人工标注验收集。

## 资料清单与阅读顺序

| 顺序 | 资料 | 类别 | 文档日期 / 版本 | 本地下载 |
| --- | --- | --- | --- | --- |
| 1 | NERC Reliability Guideline: Reactive Power Planning | 自愿性指南 | 2016-12；含 2017-03-07 勘误 | 成功；57 页，57 页有可提取文本 |
| 2 | PNNL-35221: Online Monitoring Applications Enabled by Phasor Measurement Units: Technical Assistance to the Power Sectors of Southeast Asia | 技术研究报告 | 封面 2023-11；官网发布 2024-02-15 | 成功；54 页，54 页有可提取文本 |
| 3 | NERC VAR-001-5 — Voltage and Reactive Control | 可靠性标准 | 版本 5；2018-08-16 采纳，官网生效日 2019-01-01 | 成功；16 页，16 页有可提取文本 |
| 4 | AEMO Victorian Network Performance & Insights Report | 历史运行案例报告 | 封面 2024-10；年度 2024，观察期 FY2023-24 | 失败；官方直链和 VicGrid 官方副本均 HTTP 403 |

页码约定：PDF 文件页从 1 开始；下文正文页为印刷页，不混用。文本字符位置仅针对本地保存的逐页提取结果。

## 已读章节与入选依据

### NERC 规划指南

[官方指南目录](https://www.nerc.com/our-work/guidelines/reliability-guidelines)；[官方原件](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/sams/reliability-guideline---reactive-power-planning.pdf)。
当前目录页面未找到这份历史资料条目，不将它宣称为最新或当前目录在列文件。

建议先读正文 3-8 页（PDF 7-12）的资源类型与设备行为，再读正文 17-22 页（PDF 21-26）的 QV/PV 方法和无功储备；正文 33-35 页（PDF 37-39）补充跨实体协调。
它提供物理背景、评估方法及规划条件，适合作为基础知识来源；序言明确区分自愿指南与强制标准，地区做法不能直接泛化。

末页勘误为正文 53 页（PDF 57）：2017-03-07 更新正文第 7 页的 STATCOM/SVC 图 5、6 为 V-I 特性。此下载版本已包含该页。PDF 内嵌标题只有 Report，不能替代封面标题。

### PNNL 技术研究报告

[官方介绍页](https://www.pnnl.gov/publications/online-monitoring-applications-enabled-phasor-measurement-units-technical-assistance)；[官方原件](https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-35221.pdf)。

重点读第 4 章，正文 17-21 页（PDF 23-27）。已读 4.1 的长短期失稳与研究范围，以及 4.2 的监测分类、VIP 和 RPM 说明。
它补充监测与稳定裕度知识，也能用于检索方法适用边界。北美工具实例服务于东南亚技术援助，不属于当地或中国的强制运行规程。
封面日期与官网发布日期分别记录，没有推定版次。在本次检查的材料中未发现独立勘误，不等于保证不存在。

### NERC VAR-001-5

[官方标准页](https://www.nerc.com/standards/reliability-standards/var/var-001-5)；[官方原件](https://www.nerc.com/globalassets/standards/reliability-standards/var/var-001-5.pdf)。

重点读第 1 页适用对象、第 2-4 页 R1-R6，以及第 15-16 页技术理由。已核对 R1 电压计划、R2 无功资源安排与 R5 发电机侧计划和通知要求。
它为领域审核提供可以明确定位的条款，但应区分要求、证据措施、技术理由和 WECC 地区差异；不能转换为所有地区的通用操作授权。

第 13-14 页有版本历史及较早版本勘误。官网文件 Modified 日期 2025-06-12 不是新版本出版日期。
PDF 内嵌标题仍含 Proposed Final；正文和当前官方标准页均标识 VAR-001-5，应保留这一元数据不一致，不能只按元数据判断为草案。

### AEMO 历史案例报告

[原 AEMO 介绍页](https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/nem-forecasting-and-planning/victorian-planning/victorian-annual-planning-report)现重定向到 [VicGrid 官方目录](https://www.vicgrid.com.au/transmission-planning/victorian-annual-planning-report)，目录直接列出该报告。
[AEMO 原件链接](https://www.aemo.com.au/-/media/files/electricity/nem/planning_and_forecasting/vapr/2024/2024-victorian-network-performance-and-insights-report.pdf)；[VicGrid 官方托管副本](https://www.vicgrid.com.au/__data/assets/pdf_file/0026/763118/2024-victorian-network-performance-and-insights-report.pdf)。

通过浏览工具实际阅读 2.3.2，第 21-22 页低需求电压管理，以及 4.3，第 40-42 页最小需求情景。前者讨论新增电抗器后的剩余高电压挑战，后者提供轻载工况案例，能补足单纯关注无功不足的资料。
观察期与地区限定必须随证据保留。没有本地原件、SHA-256 或本地逐页文本统计；浏览工具能读取相关正文，不表示原件下载已成功。

## 待人工复核的检索开发问题

以下问题不附生成式答案，原文定位不等同于事实支持标注。JSON 另记录文档 SHA-256、提取文件哈希和可复查的标题/段落锚点字符区间。

| ID | English retrieval question | 原文位置：PDF 页 / 正文页 |
| --- | --- | --- |
| dev-01 | How do static and dynamic reactive resources differ in their response to changes in grid voltage? | NERC 指南 8 / 4，Background 开头两类资源定义项目 |
| dev-02 | Which equipment limits constrain the reactive capability of a synchronous generator? | NERC 指南 8-9 / 4-5，同步发电机项目及励磁限制器续段 |
| dev-03 | What does QV analysis assess, and what limits its ability to reveal wide-area voltage stability problems? | NERC 指南 21-22 / 17-18，QV 小节及缺点段落 |
| dev-04 | How is PV analysis used to assess active-power transfer limits associated with voltage stability? | NERC 指南 23 / 19，PV 小节 |
| dev-05 | How does the guideline define dynamic reactive reserve, and why is a short-duration STATCOM overload not counted in that reserve? | NERC 指南 25 / 21，储备小节前两段 |
| dev-06 | Under VAR-001-5 R1, what form must a system voltage schedule take, and when must it be provided to a requesting coordinator or adjacent operator? | VAR 标准 2 / 2，R1 与 1.1 |
| dev-07 | What normal and contingency conditions does VAR-001-5 R2 address when scheduling reactive resources? | VAR 标准 2 / 2，R2 |
| dev-08 | Where may the transmission operator specify the generator voltage or reactive-power schedule, and what communication obligations appear in R5? | VAR 标准 3 / 3，R5 与 5.1-5.3 |
| dev-09 | How does PNNL distinguish long-term and short-term voltage instability, and which type is the report's monitoring discussion primarily focused on? | PNNL 23 / 17，4.1 两项分类与范围段落 |
| dev-10 | What are the two broad categories of voltage stability monitoring tools described by PNNL? | PNNL 24 / 18，4.2 图 20 上方分类段落 |
| dev-11 | What measurements and topology information does the reactive power margin method use, and what phenomena can it distinguish? | PNNL 24-25 / 18-19，RPM 说明及实例续段 |
| dev-12 | According to the 2024 Victorian report, why did new shunt reactors not completely remove low-demand overvoltage challenges? | AEMO 21 / 21，2.3.2 前三段；仅浏览读取 |
| dev-13 | What operating conditions and reactive-power absorption limitations contributed to the daytime minimum-demand voltage case on 31 December 2023? | AEMO 40 / 40，4.3.1 开头、项目列表及其后段落；仅浏览读取 |

三份本地文件 SHA-256 与 manifest 一致；11 个本地问题锚点实际命中。AEMO 两题没有本地文件哈希或偏移，须取得文件后复核。尚未人工选取完整支持区间或打相关性标签。

## 使用与再分发说明

- NERC：[Terms of Use](https://www.nerc.com/terms-of-use-policy) 已读取页面内部正文，主要约束商标；未找到授予全文公开 GitHub 再分发的一般许可。两个 NERC PDF 只本地保存。指南还含 CIGRE 等第三方图。
- PNNL：[Important Notices](https://www.pnnl.gov/important-notices) 的 Copyright Status 允许非商业科学与教育用途分发及使用；不是无限制商业许可。报告含第三方署名图，本轮仍保持原件本地、不发布。
- AEMO：[Copyright Permissions](https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions) 允许对公开 AEMO 材料适当署名使用，但排除部分非 AEMO 所有材料。报告第 2 页指向该政策；整份报告第三方内容尚未完整复核，而且本地下载失败。

所有原件、提取全文、页面截图与网页快照在 data/knowledge_local/，通过根 .gitignore 排除；没有执行 git add、commit 或 push。
可公开整理的材料为本目录来源元数据、定位问题和下载说明；不把 PDF 或提取全文混入项目代码许可证。

## PDF 检查与限制

使用已有随附 pypdf 6.10.0 对三份下载原件逐页检查；以现有 pypdfium2 渲染抽样相关页检查布局，未安装任何包。

| 文档 | 抽样视觉检查 | 解析风险 |
| --- | --- | --- |
| NERC 指南 | PDF 7、11、21、22、57；所查正文为单栏 | 公式符号提取损坏；图不能化为文本证据；脚注、跨页 QV 段落；附录表格 |
| VAR-001-5 | PDF 2、5、13；要求正文为单栏 | 多列表格行列丢失、分级编号、要求与措施混淆 |
| PNNL | PDF 23、24、26；所查正文为单栏 | 数学符号、连字/断词、图内多面板与仪表截图不能直接提取成数据 |
| AEMO | 本地视觉检查未完成；浏览截图取回也失败 | 目录及正文有表格、图表、网络图；双栏及公式质量未经核实 |

有可提取文本只证明不是纯图片正文，不证明字符、公式、表格或所有阅读顺序正确。上述检查不是生产入库解析器，也没有生成正式 Evidence/chunk ID。

## 下载与哈希复核

下载时沙箱网络 socket 被拒绝，经允许的提升权限执行官方公开 HTTP 请求。AEMO/VicGrid 返回 403 后停止，不使用登录、付费镜像或反限制手段。
如将来在正常浏览器成功下载 AEMO 文件，先计算哈希并核对封面与页码，再补全 manifest；不要用浏览缓存推定 SHA-256。

```powershell
# 从 manifest 对应官方 URL 下载；若返回 403，保留失败记录。
Invoke-WebRequest -Uri '<official download URL>' -OutFile 'data/knowledge_local/<filename>.pdf'
Get-FileHash -Algorithm SHA256 'data/knowledge_local/<filename>.pdf'
```

复核开发集时，先确认文档哈希和 PDF 页码，再人工选择完整证据范围、相关性等级及问题可回答性。
AEMO 两题在原件取得前只保留为候选定位题；不得纳入声称具备完整本地溯源的评测结果。
