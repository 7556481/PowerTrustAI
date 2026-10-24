# 断点选择与最小修复

归档：最近完整生产服务对照全部五分支（data/evaluation_local/langgraph-service-continuation-v1/batch-v1/summary.json），及旧批首项收集失败。生产业务 schema13/product1.5，原/图共享阶段；当时源码 efdb366749400d0fbef8198c5a904e9bb00652b1。当前提示/合同核查仍有相同行为，事实联合/两阶段/领域business候选不混入。

| 选项 | 证据/用户影响 | 成本与判断 |
|---|---|---|
| 修订正文混入修改历史，触发新证据义务 | LSI-03-G 正确改值但新历史叙述被重审判不足，阻碍完整交付；可查两轮与逐ID动作 | 仅修订提示，旧协议/资格/政策保留；选择此项 |
| 放宽至少一项modified且正文改变 | 两个实际Revision都有成立的阈值矛盾；没有被迫误改的实证 | 不放宽；条件存在不是错误证明 |
| 缺工程资料被过度质疑 | LSI-02-S/G 存在范围/依据分歧，但独立证据不能唯一判定所有必要输入关系 | 涉及提取/事实边界且归因弱；保留诊断 |
| 依赖结论/子问丢失 | 最近五条未直接证明该类断点 | 不因论文提到而硬改 |

假设：在一次有据纠错中，将过程说明留在finding_actions.explanation，正文只交付完整新答案，可减少与任务无关的修订历史主张及其审核阻断，同时保留正确解释、条件与缺口。并不预设pass提高或审核器一定正确。用户明确要求历史时允许历史；技术上必要的前后数值比较仍可保留。新prompt bounded-revision-v2-answer-delivery-v1；原revision-output-v2解析、modified与正文改变门禁、预算、全重审完全不变。显式开发配置revision_answer_delivery=answer_only_v1，默认production。
