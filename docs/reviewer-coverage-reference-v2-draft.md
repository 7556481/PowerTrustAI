# 开发侧覆盖参考v2草案（待本人复核）

后续复核：本人接受四项covered，将SI-A04/R3改为partially_covered，仅确认五项文本意见，不确认其余25槽或JSON/SHA。见[开发侧覆盖定义v2](reviewer-coverage-definition-v2.md)。下文“五项均拟covered”保留为被修订的历史草案，不是现行标注或执行预期。

2026-10-21。A04复验结束后，先解决原人工not_met与coverage不一致，不追加付费测试。此次只读回答/原要求及原标签，另建30要求槽的覆盖参考草案；没有按模型预测修改预期，没有重新解析历史响应，没有改提示/解析器/原标签或支持性参考。

coverage表示要求所请求的方面是否在回答中出现，正确性由支持性另评。明确但错误的结论可以涉及该方面；必要限定或解释缺失仍可能只是部分覆盖。此草案不是自动把not_met一律换成covered的程序规则，而是对以下五处逐项提出语义复核建议。

| 样例/要求 | 原标签 | 拟覆盖标签 | 理由与仍须保留的问题 |
|---|---|---|---|
| H-MIT-001-A05 / R2 | not_met | covered | 明确给出了温度—阻值关系的否定结论；谈到了该方面，原支持性contradicted不变 |
| H-SI-001-A03 / R2 | not_met | covered | 说出了符号的复数规则，同时把禁令扩大到所有名称；附加范围仍无据 |
| H-SI-001-A04 / R3 | not_met | covered（重点复核） | 回答了符号/名称同时使用的问题，但将范围扩大到整篇文档；是否仍算充分涉及“同一表达式”需本人明确，不能凭更强禁令就认定表达正确 |
| H-SI-001-A06 / R2 | not_met | covered | 对复数给出了明确反向结论；原contradicted不变 |
| H-SI-001-A06 / R3 | not_met | covered | 对同表达式混用给出了明确反向结论；原contradicted不变 |

其余25槽沿既定met→covered、missing→missing、partial→partially_covered草拟，不改变原预期含义。尤其SI-A02省略句末例外仍拟partially_covered，支持标签仍按原包保留；不能因这一轮区分正确性就自动把所有省略条件的回答判完整。复合单元支持性对齐问题也没有因此解决，仍需执行前单独冻结。

30槽JSON草案位于忽略目录`data/evaluation_local/holdout-source-selection-v1/coverage-reference-v2-draft/coverage-proposal.json`，保存旧文件SHA、逐槽原标签/新建议/理由及待确认状态。原已审核答案、标签与所有失败记录不覆盖；公开报告不附完整回答或证据。

下一步请本人重点复核上表，尤其SI-A04/R3。如果该项认为应为partial或uncertain，先写清所缺的是范围表达还是根本未涉及该要求，不用预测结果决定标签。本页及JSON均未冻结为执行预期。确认后才准备剩余8项的独立开发批次；不恢复旧批，也不再重测A04。当前0模型调用、未提交推送，生产不变。
