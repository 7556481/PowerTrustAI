# 剩余8项v5开发评测计划（待执行批准）

后续状态：本人已明确批准计划/目的地/载荷/最多16调用并执行。4有效、1失败、3未执行，按计划停止；见[结果与分歧](reviewer-remaining8-v5-results.md)。下文“尚未批准”为准备阶段历史状态，不自动授权再次执行。

2026-10-21。coverage v2的30槽文本已分两轮确认，原参考、历史失败及支持标签保留。本计划仅准备原未执行的8项，不恢复旧批、不重测A04，不称独立验收。**当前0调用，尚未获本计划执行批准。**

## 固定清单

| 项目 | coverage v2参考（R1/R2/R3） | 支持参考单元数 |
|---|---|---|
| H-MIT-001-A05 | covered / covered / — | 2 |
| H-MIT-001-A06 | missing / missing / — | 1 |
| H-SI-001-A01 | covered / covered / covered | 3 |
| H-SI-001-A02 | partially_covered / covered / covered | 3 |
| H-SI-001-A03 | covered / covered / covered | 3 |
| H-SI-001-A04 | covered / covered / partially_covered | 3 |
| H-SI-001-A05 | missing / covered / covered | 2 |
| H-SI-001-A06 | covered / covered / covered | 3 |

22个要求槽，17 covered、3 missing、2 partial；20个原支持参考单元。问题、证据、回答及程序单元逐项等同旧批对应输入；新coverage只在评测侧，不进入模型。原支持性复合单元不拆改标签，复数规则/同表达式范围及句末例外按已确认边界处理。

## 参数与停止

v5精确字段诊断，原提示与结构/证据/ID校验不改。deepseek-flash，https://api.deepseek.com；8次初始请求，每项最多一次格式纠正，推导最大16调用；每次90秒、批次1800秒，max_output_tokens=2000，响应24000字符，消息90000字符。采样使用提供商默认值，未固定温度或种子。无传输重试、语义重跑、Revision、追加或换样例。

首次执行/传输/存储/最终契约失败停止，余项记录未执行；语义分歧记录而不重跑。复用现有execute/batch_control，新增evaluation/reviewer_remaining8_v5.py只做精确8项门禁、身份校验和独占attempt防重发。旧入口不改。三个离线门禁回归通过（精确清单、拒绝多/少/重排、拒绝标签混入及单元篡改）；全量消息预览与SHA离线回查通过，不构造模型客户端、不加载凭据。

准备目录为忽略的`data/evaluation_local/holdout-source-selection-v1/remaining8-v5-plan-20261021-v1/`：input、reference-private、messages-preview、alignment-policy及plan。plan绑定所有文件及源码SHA；用户的文本确认不记为其核验JSON/SHA。真实调用前再次回查；身份变化须重新准备，不能覆盖旧执行记录。

## 预先确定的匹配与统计

逐要求比较coverage v2与预测，报告计数/混淆及分歧；全部22槽含失败/未执行，不能仅展示有效项。支持性先以原参考精确文本定位载体，再做保留否定、例外和范围的AI辅助语义匹配，匹配结论仍待本人复核。同一参考只计一次；等价拆分可联合匹配，复合单元若出现混合支持标签或仅部分等价，则列无法对齐，不自动合并为无据，也不只挑正确子句。冲突和额外预测另列。

同时报告F/A_NS与F/A_SP及原始数，零分母N/A；所有20参考单元的对齐、无法对齐、契约失败和未执行均交代。不合并总准确率，不把执行通过当语义正确。旧批与A04复验分别保留，不拼成新独立成绩。

执行批准须明确外部目的地、两题要求/选定MIT与BIPM正文/这8份回答载荷、至多16调用；不发送任何预期标签、参考答案角色或匹配统计。本计划不改变生产，不追加收费实验，不自动提交推送。
