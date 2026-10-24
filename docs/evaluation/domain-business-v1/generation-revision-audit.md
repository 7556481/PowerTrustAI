# 生成与修订实际路线及整理

Factory生产生成器：EvidenceGenerationAgent(schema3, product_guidance) → messages_for → structured_request → parse_units/answer_units.assemble → evidence_scope.make_snapshot → Harness提取审核。无证据时显式不足出口，不发模型。输入是当前任务、实际证据、绑定、知识版本和回答要求；输出是AnswerDraft、证据充分性、调用记录与快照。

Factory生产修订器：ModelRevisionAgent(protocol2, clean_answer_body) → revision_contract_v2.run → program finding catalog → 一次structured_request → finding_actions逐ID及answer_units.assemble → 既有长度和正文校验 → evidence_scope.make_snapshot；外层重新提取、完整事实/领域审核并保存新版本。输入允许证据与两审发现，输出变更/未解决项与新快照。修订资格仍由既有bounded_repair/政策负责。

已复用的公共实现：answer_units、answer_constraints、evidence_scope.make_snapshot、structured_request、validation_diagnostics。快照调用参数不同：生成绑定evidence/answer_requirements，修订绑定allowed_evidence及包含修订上下文的requirements；不把表面相似调用误合并成丢失上下文的辅助函数。本轮未发现值得新封装的等价重复逻辑，保留现有公共模块，未修改任何生成/修订提示、长度政策、资格或审核要求。新增领域接线只改领域构造，不复制Harness或Master。

下一项优先：在既有一次生成中验证短答案对原问题各子问和必要条件的覆盖，先固定失败参考再做单一改造；随后检查多缺陷修订的modified/retained/unresolved与重审对应。不要同时重写两Agent，不以领域常识造事实修订依据。
