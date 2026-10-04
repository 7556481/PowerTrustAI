# 后续实施清单与实际接入点

2026-10-04。以下均是待实施事项，本轮未同时开发；默认BM25、支持要求和有限修订政策保持原样。

| 后续任务 | 实际接入点 | 前置依赖与独立验收 |
|---|---|---|
| 逐主张证据检索与交付 | `harness/retrieval.py::query_for`、`RetrievalSession.retrieve`，`harness/runtime.py`审核输入装配；`agents/evidence_verification.py`与 `services/evidence_scope.py` | 当前按目的组织查询与交付，尚非逐主张查询。需定义claim_id/answer_version→检索调用→候选→交付的显式绑定，复用Retriever与共享预算；区分未召回、容量未交付、执行失败。保留原引用作用域，独立检索不能补救原引用不足。新合同独立版本；公开回归验证跨主张借用、部分失败、版本变化与API持久化。 |
| 可选语义检索装配 | `rag/semantic.py::AsyncSQLiteSemanticRetriever`、`SemanticRetriever`、`VectorIndex`；`rag/embedding.py::E5ONNXEncoder`；`backend/assembly.py::ComponentFactory.create` | 已有Dense/RRF实现，可接同一Retriever接口，尚未装配为服务选项。需锁定模型文件/版本、知识与向量索引一致性、Context/Evidence回查，独立可选配置和资源关闭/drain。按unknown评测边界、必要组合覆盖和成本质量比较验证，不因实现存在就切换默认。 |
| 支持判断微调数据集与独立评测 | `agents/review_templates_v3.py`及事实审核合同、`services/validation_diagnostics.py`；现有 `evaluation/`评测材料 | 尚无训练流水线或微调成果。先定义主张/限定/候选原文/支持标签与依据范围，记录AI辅助反馈来源，不能直接视为专家金标准。按文档、问题和版本隔离训练/验证/独立测试，涵盖否定、单位、工程前提、跨引用借用与证据不足。明确发布许可、人工复核和指标，分开合同正确率与支持语义判断；不自动公开私有响应或官方全文。训练与模型替换须另轮冻结协议、数据和评测。 |

共同接入约束集中在现有Harness、固定知识版本、严格ID/原文定位与程序政策，不另建审核器。检索命中/规则告警不等于模型语义正确。细化设计和预算应基于阶段消息与实际调用结构，历史96014临时异常值不作为推荐配置。
