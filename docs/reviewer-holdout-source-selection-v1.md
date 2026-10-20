# 少量保留来源候选与谱系初核

2026-10-20。先补齐[建设规则](reviewer-holdout-spec-v1.md)的调用上界、错误支持两个分母及训练污染限制，再选择以下**两份来源候选**；未出题、未定义预期标签、未预测、未冻结保留批次，也未调评测协议。

## 两份可追溯候选

| 候选组 | 原始资料与已核对身份 | 谱系处理 |
|---|---|---|
| CAND-MIT-6002 | MIT OpenCourseWare，Anant Agarwal，6.002 Circuits and Electronics，Spring 2007，Transcript – Lecture 1；官方资源6_0022007L01.pdf。实际文件16页、57,372字节，PDF第1页版权/引用页与课程资源页相符 | 课程内转录、讲义/录像、镜像与翻译按同组关联；课程大纲指定Agarwal/Lang的2005年教材Foundations of Analog and Digital Electronic Circuits，ISBN9781558607354，视为须关联核对的相关谱系，不把教材与配套课程自动拆入开发/保留两边 |
| CAND-BIPM-SI9 | BIPM，The International System of Units (SI)，9th edition 2019，实际PDF封面V4.01、June 2026；DOI10.59161/AUEZ1291，版权页ISBN978-92-822-2272-0。英文PDF102页、1,979,202字节 | 不同版本、英法版本、官方译本、摘要与镜像关联同一原文谱系。NIST SP330-2019官方前言明确为第九版英文文本的美国版本，须关联，不能仅凭换机构/URL认为独立 |

MIT：[官方资源页](https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/resources/6_0022007l01/)、[课程大纲及教材关系](https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/pages/syllabus/)、[官方转录PDF](https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/00c8847c48604169f00d53e0a46a4061_6_0022007L01.pdf)。选的是2007转录，不混用检索出现的Fall 2000幻灯片。

BIPM：[官方发布页](https://www.bipm.org/en/publications/si-brochure)、[实际英文PDF](https://www.bipm.org/documents/20126/41483022/SI-Brochure-9-EN.pdf)、[NIST谱系说明](https://www.nist.gov/pml/special-publication-330/sp-330-foreword)。搜索摘要仍有V3.02/August 2025旧信息，本次以实际下载封面V4.01/June 2026为准；同一URL会更新，后续按已取SHA冻结，不靠URL代表版本。

两候选均为原发布机构可追溯资料，尚未认可任何具体选段或推理题。BIPM属于计量/单位基础资料，后续能否符合本项目题型范围仍需确认，不能因为权威而自动纳入样本。MIT版权页声明署名、非商业、相同方式共享；BIPM版权页列CC BY4.0。这里只核对文件及版权身份，不推断获得模型训练许可、不公开再分发全文。

## 与既有开发资料的隔离核对

对本轮开始的HEAD f116d9827fe0b1cdc439d6cf32c96f5fa70ea3e9下docs/evaluation/tests/README，以及既有评测/运行的323份来源、冻结、manifest和报告元数据作名称/作者/域名/标识检索，未发现MIT候选、BIPM候选的使用记录。相关教材ISBN、NIST SP330及SI-Brochure别名追加检索也无命中。它们的发布机构与明确原文身份不同于DEV-CT/TR/SW/RC四个已知组，未发现已知转载或母文档关系。

**这只是已审计范围内“未见使用记录”，不是绝对无重合证明。** 没有扫描70GB语料库或完整原始请求响应档案，也没有做候选全文对全部历史正文的近重复比对。CT原始出处尚未核实，后续具体选段若无法排除与旧材料的近重复，应hold，不因本次无关键词命中直接放行。未来选段后仍需核对出处/引用/派生关系及相关题目的近似性。

来源阅读和封面核对本身属于允许的出题/标注准备，不代表已预测或将候选用于调协议。当前尚无新题，也不能称来源谱系独立性已最终验收。基础模型是否训练见过这些公开文档未知；项目隔离不能证明训练未见。

## 快照及状态

实际下载PDF SHA256：

- MIT：`8190acbf2ce7b75f5170c56d13257da49356a533aa1a0661c2531eb7a373a7d9`。
- BIPM：`5442eea2c680caf77a9d96879205a97f57c7c270b98a0bd0126c18fefe47e02c`。

原PDF、封面图、身份页提取及清单仅留忽略目录data/evaluation_local/holdout-source-selection-v1，合计两PDF约2.04MB，不复制数据库或建立语料索引。通过PDF技能渲染核对封面，字体替换警告没有影响已核对的标题/版本阅读；身份页之外未进行选段或题目设计。Python直接下载遇TLS证书校验失败，随后以命令级代理、正常SSL校验的curl成功取得，不关闭SSL、不改全局设置。

OpenStax University Physics Volume2亦曾作来源身份初筛，但其[当前前言/使用说明](https://openstax.org/books/university-physics-volume-2/pages/preface)包含生成式AI使用需进一步厘清的条款，本轮不推进为候选、不下载全文或制作题目；不是第三个保留来源组。

两候选状态均为**待本人复核及后续选段谱系核对**，不替代最终保留集确认。当前0模型调用，最终模型/参数/提示/匹配细则及执行计划仍未冻结，生产协议不变。未提交推送。
