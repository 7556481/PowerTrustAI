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
- 主路径字段、正常/失败提取、引用隔离与预算状态演算见[协议实操](chapters/37-protocol-ledger-lab.md)。仍需补足每个动态配置分支的逐符号消费者图及所有schema版本逐字段示例；本书覆盖正式主路径与重点反例，不能视作所有实验开关的穷举手册。
- Windows替换错误5的实际阻塞持有者仍未知；不指认杀毒或具体程序。
- 全量Tantivy和spool已退役，本轮不重建；案例依固定报告，不能把链接存在当资产可运行。

## 内容验收方法

逐页检查实现、输入、异常、验证和限制；每道重点解析给判断过程、项目入口、误答与继续追问。构建验收另外检查源码身份、Markdown链接、HTML锚点、搜索和折叠答案。人工内容复核与程序结构检查是两层，结构通过不证明所有解释语义正确。

## 主路径的调用方、被调用方与持久化对象

下面是职责边界图表，读代码时从左到右，再按run/版本回到保存对象。它不是所有历史实验开关的完整静态调用图。

|入口或调用方|模块内动作→下一层|保存对象与失败边界|
|---|---|---|
|start-powertrustai.cmd / backend.managed|读取受管选择→launcher/config→ComponentFactory或overlap|配置manifest记录实际协议与源码；端口监听不能替代身份|
|backend.api|校验会话与请求→ReviewService.submit|RunStore.create保存queued/request/config；响应丢失提交可能未知|
|ReviewService.worker|取队列→Factory.create→OfflineHarness|run_id绑定observer；异常仍需queue.task_done与资源收尾|
|OfflineHarness / graph_runtime_v1|运行RunExecution七阶段→条件路由|事件/checkpoint由Store保存；图没有自带可恢复业务checkpoint|
|generate / prepare_review / revise|retrieve_for按purpose→harness.retrieval→rag.retriever|目的、输入查询、交付记录绑定知识版本；检索失败不伪装空支持|
|rag.retriever|KnowledgeStore→corpus_index MATCH/排名→原文与邻接|EvidenceProvenance保存版本/fragment/range/hash；预算选择后还要看发送边界|
|corpus_download / corpus_build|固定manifest→Parquet批次→add_record→publish|partial、正文/duplicates/identity、progress、发布封印；事务断点与排除分母分开|
|生成Agent|结构客户端→模型→generation parser|Answer及citations按answer_id/version保存；结构失败不能制造正文|
|claim_extractor|原句锚点→规范主张→覆盖校验|Claims绑定输入正文；未覆盖不等于非事实|
|事实Agent|review_inputs→独立审核/原引用分组→review_transport|findings、组件及引用绑定保存；外部ID或其他scope引用拒绝|
|领域Agent|任务义务、规则、工具与领域Evidence→模型合同|missing_prerequisites/领域发现保存；无法获取现场输入不等于事实反证|
|merge_and_decide|policy / product_policy→资格→修订或终态|Report保存程序处置；意见存在不等于可改稿|
|revision Agent|发现catalog→动作/新正文parser→版本应用|finding_actions和新版Answer；随后新提取和双审，不沿用旧版通过|
|structured_request|strict_json→parser→至多一次纠正|调用记录/诊断保存；部分响应不能绕过完整合同|
|模型客户端 / DeepSeekAdapter|预算claim→线程HTTP→response/usage校验|run/component/version调用归属；超时或取消不保证远端未执行|
|ReviewService observer|RunStore.index/checkpoint/mark|objects/events/runs短事务；写失败保留未确认持久化状态|
|历史API / presentation|Store.get/objects/evidence→serialization兼容|只读旧版本；不调用模型、不覆盖旧意见|
|app.js / inline_review.js|主读取与辅助slot→归属检查→码点标注|浏览器不创造权威版本；反馈追加到对应run/answer/finding|
|用户取消 / service.stop|拒新单→取消任务→gather/drain→close|在途结算、资源释放、Store终态分别核对；重启旧run标中断|
|public_checks / evaluation入口|公开夹具/合同/API测试，固定批次另冻结|测试日志与报告；跳过私有归档不能包装为真实语义重测|

每一行的异常需与对应章节的反例一起读；正常路径图不会证明所有失败都可靠恢复。
