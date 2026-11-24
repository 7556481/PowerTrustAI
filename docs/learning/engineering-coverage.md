# 工程知识覆盖与证据清单

2026-11-24；应用基线e4fb27e。本表覆盖阅读路径，不能把“已有教学”理解为该模块所有能力已实现或已全面验证。源码链接指向实现，章节给出调用/数据/异常和验证边界。当前配置统一见[当前状态](../current-status.md)。

|知识模块|实现入口|教学与追问|主要约束与验证范围|状态|
|---|---|---|---|---|
|启动与配置|[backend/managed.py](../../backend/managed.py)|[30 / 30.1](chapters/30-maintenance-practice.md)|依赖/Factory/health与受管选择；结论按章节链接的测试/报告限定|已有教学|
|产品任务与处置|[harness/product_policy.py](../../harness/product_policy.py)|[21 / 21.2](chapters/21-product-contracts.md)|输入→发现→资格→处置；结论按章节链接的测试/报告限定|已有教学|
|语料下载|[rag/corpus_download.py](../../rag/corpus_download.py)|[22 / 22.2](chapters/22-corpus-engineering.md)|manifest/partial/hash与损坏排除；结论按章节链接的测试/报告限定|已有教学|
|构建与恢复|[rag/corpus_build.py](../../rag/corpus_build.py)|[22 / 22.1](chapters/22-corpus-engineering.md)|来源→正文→批事务→断点→发布；结论按章节链接的测试/报告限定|已有教学|
|原文与封印|[rag/corpus_index.py](../../rag/corpus_index.py)|[22 / 22.3](chapters/22-corpus-engineering.md)|知识版本/范围/邻接/冷seal；结论按章节链接的测试/报告限定|已有教学|
|分词查询|[rag/chinese_terms.py](../../rag/chinese_terms.py)|[23 / 23.1](chapters/23-search-boundaries.md)|分词一致性/别名/OR；结论按章节链接的测试/报告限定|已有教学|
|FTS和候选交付|[harness/retrieval.py](../../harness/retrieval.py)|[23 / 23.2](chapters/23-search-boundaries.md)|MATCH→排序→预算→消息；结论按章节链接的测试/报告限定|已有教学|
|Dense与Hybrid|[rag/semantic.py](../../rag/semantic.py)|[06 / 既有余弦/RRF解析](chapters/06-retrieval-math.md)|可选实验，非本机默认；结论按章节链接的测试/报告限定|已有教学|
|模型HTTP|[model_adapter/deepseek.py](../../model_adapter/deepseek.py)|[24 / 24.3](chapters/24-model-wire.md)|发送/线程/超时/响应边界；结论按章节链接的测试/报告限定|已有教学|
|结构与纠正|[services/structured_model.py](../../services/structured_model.py)|[24 / 24.1](chapters/24-model-wire.md)|strict_json→合同→一次纠正；结论按章节链接的测试/报告限定|已有教学|
|预算所有权|[model_adapter/runtime.py](../../model_adapter/runtime.py)|[24 / 24.3](chapters/24-model-wire.md)|run→调用→预留/结算；结论按章节链接的测试/报告限定|已有教学|
|生成|[agents/generation.py](../../agents/generation.py)|[25 / 25.1](chapters/25-agents-semantics.md)|问题/证据→正文引用；结论按章节链接的测试/报告限定|已有教学|
|提取|[services/claim_extractor.py](../../services/claim_extractor.py)|[25 / 25.1](chapters/25-agents-semantics.md)|原句→主张/覆盖/忠实性；结论按章节链接的测试/报告限定|已有教学|
|事实审核|[agents/evidence_verification.py](../../agents/evidence_verification.py)|[25 / 25.2](chapters/25-agents-semantics.md)|独立/原引用证据与判断；结论按章节链接的测试/报告限定|已有教学|
|领域审核|[agents/power_domain_review.py](../../agents/power_domain_review.py)|[21 / 21.1](chapters/21-product-contracts.md)|工况/任务义务/工具前提；结论按章节链接的测试/报告限定|已有教学|
|修订与授权|[services/bounded_repair.py](../../services/bounded_repair.py)|[25 / 25.3](chapters/25-agents-semantics.md)|发现→允许依据→版本→重审；结论按章节链接的测试/报告限定|已有教学|
|图阶段路由|[harness/graph_runtime_v1.py](../../harness/graph_runtime_v1.py)|[26 / 26.1](chapters/26-execution-control.md)|小state/context/无checkpoint；结论按章节链接的测试/报告限定|已有教学|
|Harness与并发|[harness/execution.py](../../harness/execution.py)|[26 / 26.2](chapters/26-execution-control.md)|预算/取消/early task/drain；结论按章节链接的测试/报告限定|已有教学|
|队列生命周期|[backend/service.py](../../backend/service.py)|[27 / 27.3](chapters/27-service-storage.md)|拒单/worker/收尾；结论按章节链接的测试/报告限定|已有教学|
|Store与兼容|[backend/store.py](../../backend/store.py)|[27 / 27.2](chapters/27-service-storage.md)|事务/objects/events/recover；结论按章节链接的测试/报告限定|已有教学|
|API与会话|[backend/api.py](../../backend/api.py)|[27 / 27.1](chapters/27-service-storage.md)|认证/提交未知/非幂等；结论按章节链接的测试/报告限定|已有教学|
|浏览器异步|[backend/static/app.js](../../backend/static/app.js)|[28 / 28.1](chapters/28-browser-consistency.md)|epoch/版本/辅助slot；结论按章节链接的测试/报告限定|已有教学|
|字符与意见|[backend/answer_annotations.py](../../backend/answer_annotations.py)|[28 / 28.2](chapters/28-browser-consistency.md)|码点/绑定/重叠/未定位；结论按章节链接的测试/报告限定|已有教学|
|测试与实验|[evaluation/batch_control.py](../../evaluation/batch_control.py)|[29 / 29.3](chapters/29-evaluation-math.md)|失败分母/冻结/停止；结论按章节链接的测试/报告限定|已有教学|
|依赖CI|[tools/public_checks.py](../../tools/public_checks.py)|[30 / 30.1](chapters/30-maintenance-practice.md)|公开夹具/版本/可选环境；结论按章节链接的测试/报告限定|已有教学|
|研究归档与退役|[docs/maintenance/tantivy-retirement-public-v30.md](../../docs/maintenance/tantivy-retirement-public-v30.md)|[33 / 33.1](chapters/33-case-tantivy.md)|固定报告/运行依赖/资产处置；结论按章节链接的测试/报告限定|已有教学|

## 仍缺依据与实际未实现

- 卡特彼勒复盘仅作本轮教学缺口输入，不公开个人求职、情绪、未确认贡献或其他团队经历。DeepSeek个人选型理由未获受控选型证明。
- 未实现：通用跨重启幂等提交、模型调用断点续跑、全库统一真实召回率、工程安全认证、自然问答自主纠错的普遍收益。对应专题解释原理及限制，不填成功率。
- 待补：每个动态配置分支的逐符号消费者图、所有schema字段逐项合法/非法示例、每个请求状态下完整预算账本演算；现有24/25/27章只是主路径与重点边界，不能视作穷尽。
- Windows替换错误5的实际阻塞持有者仍未知；不指认杀毒或具体程序。
- 全量Tantivy和spool已退役，本轮不重建；案例依固定报告，不能把链接存在当资产可运行。

## 内容验收方法

逐页检查实现、输入、异常、验证和限制；每道重点解析给判断过程、项目入口、误答与继续追问。构建验收另外检查源码身份、Markdown链接、HTML锚点、搜索和折叠答案。人工内容复核与程序结构检查是两层，结构通过不证明所有解释语义正确。
