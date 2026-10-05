# 后续实施清单与实际接入点

2026-10-05最新：[NLI实验](support-nli-v1.md)已经实际完成，两候选事前冻结验证/资源规则选MiniLM，一次4epoch训练、同5项开发对照macro-F1 0.8222→1.0000，未接生产。下一步先审阅78pending新候选、保持SSIAG文档留出、清理概念重用，补独立来源/not_assessable/外部验证；不自动继续训练。新入口evaluation/support_nli.py及support_nli_candidates.py。最终详细中文手册Markdown＋本地文档网站，PDF可选；本轮仅更新要求和知识点。

2026-10-05最新：首次三类支持判断训练已经实际完成，不能再说仅数据准备。74模板监督confirmed、独立基线79请求（69有效/5scope失败）；许可筛选19 AEMO/7家族，CPU BERT-Tiny同基座一次12epoch训练，固定5测试结果见support-finetune-v1.md。下一步依赖更多许可明确文档/独立问题家族监督、有效not_assessable类别及独立外部评测，当前支持召回退步，不能直接接生产。实际接入点仍support_training确认/许可/完整文本→模型检查点→独立评测；生产事实审核协议/政策不动，不自动开启下一轮。


2026-10-05最新：54复核意见已接收，旧33＋新36＋修订5=74pending主候选，未确认或调用基线。下一步先明确逐项监督事件；独立基线执行前落实单样本契约失败继续/全局故障停止回归，当前execute不满足该行为。补not_assessable主任务、独立评测与NERC许可后再选训练模型和核对本机算力；本轮仅冻结输入，不训练。


2026-10-05更新：91用户监督审阅已接收/校验33优先、29辅助、29hold，具体标签确认必须逐ID明确selection；[质量检查](support-review-quality-v1.md)已落实到48扩充候选，并另建6新任务。下一步是监督确认优先项/新任务、补hold所缺原输入/正确对象/工具或执行账本；不能机械翻转变体标签、用父任务预测评修订任务或把辅助题混入支持训练。未开始训练，原基线不重跑。

2026-10-04最新：[知识/样本扩充v1](knowledge-support-expansion-v1.md)已经实际建立新开发/预留知识快照与48新pending候选，旧91种子及失败基线不动。接入点：evaluation/knowledge_support_expansion的来源锚定→support_dataset的复核/监督合并→support_baseline.training_export。下一步是用户返回两个复核包的监督结果、核对许可、补中国官方全文/设备资料、为预留文档独立构造冻结评测；不能把当前139pending或同资料预分当训练金标准。规划数百条已复核样本但不以数量保证质量。本轮未训练、未重跑旧基线，未来训练不使用预留文档/家族调参。

2026-10-04最新：[证据支持判断数据准备v1](support-judgment-dataset-v1.md)已实现evaluation/support_dataset.py、support_baseline.py的提取、冻结校验、家族预分、AI辅助复核、未微调基线、离线指标及仅确认监督出口。91项全pending；一次基线2请求后结构失败停止，5有效部分预测，不自动重跑。下一阶段接入点是review-labels.json→apply_reviews→training_export的监督JSONL（messages/group_id/split/supervision/origins），保留ResponseDiagnostics与RunStore反馈源。先确认标签、许可、独立家族/跨文档评测和冻结训练配置，再训练支持判断组件；本轮未安装训练框架、训练或替换schema13审核器，不能把模型自评当金标准。此前“尚无数据流水线”仅是当时状态。

2026-10-04最新：第二项[真实服务可选语义检索v1](semantic-service-v1.md)也已交付，服务三模式/启动核验/资源复用/公开回归/固定对照/单次真实链路完成，BM25仍默认。第一项逐主张已交付。下表为接入前设计记录；当前后续仅为更广的资源匹配对照与证据支持微调准备，不能把已实现项重复列成尚未接入。

微调准备实际接入点：ResponseDiagnostics候选目录/消息/响应→FactRetrievalBinding→RunStore.add_review来源事件。先人工区分模型语义错误、检索未交付与工程前提不足，按问题家族＋文档＋回答修订谱系隔离训练/验证，不以模型自评直接造金标准；schema13解析、fact_delivery范围与validation_diagnostics保持工程回归。尚无训练流水线，另轮明确数据许可、分组规则和独立评测后才能实施。

2026-10-04后续实施状态：第一项已交付可选[逐主张事实检索与交付v1](per-claim-fact-retrieval-v1.md)，不再是尚未接入；aggregate默认、其他两项计划保持。以下表保留原接入设计依据；进一步研究范围是更广、资源匹配的检索/交付对照和分类语义疑点，不在本轮自动开展。

2026-10-04。以下均是待实施事项，本轮未同时开发；默认BM25、支持要求和有限修订政策保持原样。

| 后续任务 | 实际接入点 | 前置依赖与独立验收 |
|---|---|---|
| 逐主张证据检索与交付 | `harness/retrieval.py::query_for`、`RetrievalSession.retrieve`，`harness/runtime.py`审核输入装配；`agents/evidence_verification.py`与 `services/evidence_scope.py` | 当前按目的组织查询与交付，尚非逐主张查询。需定义claim_id/answer_version→检索调用→候选→交付的显式绑定，复用Retriever与共享预算；区分未召回、容量未交付、执行失败。保留原引用作用域，独立检索不能补救原引用不足。新合同独立版本；公开回归验证跨主张借用、部分失败、版本变化与API持久化。 |
| 可选语义检索装配 | `rag/semantic.py::AsyncSQLiteSemanticRetriever`、`SemanticRetriever`、`VectorIndex`；`rag/embedding.py::E5ONNXEncoder`；`backend/assembly.py::ComponentFactory.create` | 已有Dense/RRF实现，可接同一Retriever接口，尚未装配为服务选项。需锁定模型文件/版本、知识与向量索引一致性、Context/Evidence回查，独立可选配置和资源关闭/drain。按unknown评测边界、必要组合覆盖和成本质量比较验证，不因实现存在就切换默认。 |
| 支持判断微调数据集与独立评测 | `agents/review_templates_v3.py`及事实审核合同、`services/validation_diagnostics.py`；现有 `evaluation/`评测材料 | 尚无训练流水线或微调成果。先定义主张/限定/候选原文/支持标签与依据范围，记录AI辅助反馈来源，不能直接视为专家金标准。按文档、问题和版本隔离训练/验证/独立测试，涵盖否定、单位、工程前提、跨引用借用与证据不足。明确发布许可、人工复核和指标，分开合同正确率与支持语义判断；不自动公开私有响应或官方全文。训练与模型替换须另轮冻结协议、数据和评测。 |

共同接入约束集中在现有Harness、固定知识版本、严格ID/原文定位与程序政策，不另建审核器。检索命中/规则告警不等于模型语义正确。细化设计和预算应基于阶段消息与实际调用结构，历史96014临时异常值不作为推荐配置。
