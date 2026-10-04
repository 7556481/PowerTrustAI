# 文档索引

## 2026-10-04 最新公开复现与并行轨迹修复

- [README](../README.md)：当前架构、标准库/锁定API测试、本机synthetic_fixture演示最短入口。
- [当前状态](current-status.md)：schema13真实基线与本轮无付费范围，BM25默认/Dense-RRF非默认/微调未实现；网络状态按日期记录。
- [公开复现](public-reproducibility-v1.md)：干净克隆、依赖、基线8错误、修复测试/跳过项、原Harness及HTTP演示证据。
- [并发轨迹](model-trace-attribution-v1.md)：稳定请求归属、共享预算、纠正/超时/取消与旧记录兼容。
- [实施接入点](implementation-roadmap.md)：逐主张证据、可选语义装配、支持判断微调数据与独立评测，均未在本轮实现。
- 本机材料：data/runtime_local/public-repro-v1/reading-notes.md、verification.json；baseline-*、candidate-*日志、dependency-install.txt、git-audit.json，隔离检出不复制原私有data/.env。
- 长期偏好见handoff最新节：用户授权检查提交后默认普通推送至核实origin和当前分支；旧不推送/网络失败记录保留历史含义。r1手册及PDF本轮不重建。

更新：2026-10-04。路径相对本文；data 下材料仅本机可用且被 Git 忽略。历史文档保留当时版本，不覆盖；其旧测试数、默认 schema、知识版本或“未实现”描述不代表当前状态。

## 本轮界面 v1 与真实 API 验证素材

| 入口 | 用途与实际边界 |
|---|---|
| [local-review-ui-v1.md](local-review-ui-v1.md) | 同源中文界面、令牌本机操作、字段/错误交互、修改职责、验证分层和已知问题 |
| `backend/static/index.html`、`style.css`、`app.js` | 静态界面、响应式布局、安全纯文本、内存令牌、单次POST、状态轮询/版本/证据/反馈 |
| `backend/api.py`、`store.py`、`service.py`、`assembly.py` | 静态路由/CSP与同源、受保护分页、实际反馈绑定和未完成原引用投影、当前版本完整性、资产哈希 |
| `tests/test_local_ui.py`、`tests/ui_client_checks.js` | 4项新增离线API测试；客户端DOM double验证未知POST/重复/409/文本安全，不当作真实浏览器 |
| [ui-v1-offline-final-tests.txt](../data/runtime_local/ui-v1-offline-final-tests.txt)、[ui-v1-client-checks.txt](../data/runtime_local/ui-v1-client-checks.txt) | 421项通过/57.127秒及客户端检查；零付费，保留最初420项阶段日志 |
| [ui-v1-demo-scenarios.json](../data/runtime_local/ui-v1-demo-scenarios.json) | 7条通过既有假组件服务生成的修订/部分失败/取消/执行失败/文本安全/中断场景 |
| [ui-v1-browser-checks.json](../data/runtime_local/ui-v1-browser-checks.json)、[截图目录](../data/runtime_local/ui-v1-screenshots/) | 实际内置浏览器两提交、排队/429、取消、恢复、证据、反馈、401、网络未知、文本安全；不含令牌/路径 |
| [ui-v1-delivery.json](../data/runtime_local/ui-v1-delivery.json) | 本轮文件SHA、验证摘要、14条演示/2条真实分别统计与归档完整性 |
| [冻结计划](../data/runtime_local/ui-v1-real-validation/plan-v1.json) | 两输入、原装配、schema12、知识/源码/模板哈希、每运行40上界/合计80硬界、停止条件；实际9次，无提额 |
| [真实问答](../data/runtime_local/ui-v1-real-validation/8f378eec606e4808b7319c6c8d4e274f.json)、[真实已有回答](../data/runtime_local/ui-v1-real-validation/c08a5ddcae4a46148a2a512100148731.json) | 浏览器POST经真实服务装配执行；6/3请求，均review_required，阶段完成、检查未全评估，均无Revision |
| [重启前结果/反馈](../data/runtime_local/ui-v1-real-validation/pre-restart-v1.json)、[重启对照](../data/runtime_local/ui-v1-real-validation/restart-verification-v1.json) | 两结果和最新反馈逐字段一致，无POST/无模型重发；用量与9个原始响应仍保留 |
| `tests/ui_real_validation.py`、`data/retrieval_local/service_private/{run_id}` | 授权真实入口预检/冻结与只读API采集；原消息、响应、格式失败、候选和快照由原组件归档，不复制全文 |

真实问答格式失败 `basis_indexes` 越界、一次纠正及原引用coverage告警见其run JSON和原始诊断；既有URL安全投影误隐藏官方HTTPS地址记为未解决，不因两运行完成改写为安全或语义认证。本轮最终手册仍未编写。

## 当前入口和实现说明

最终学习与面试手册要求见 [final-handbook-requirements.md](final-handbook-requirements.md)，目前未编写。下面的主题索引用于逐轮积累素材，不能作为已交付手册。

| 文档 | 地位与阅读用途 |
|---|---|
| [handoff.md](handoff.md) | 当前状态、装配、限制、验证与未提交工作 |
| [design-decisions.md](design-decisions.md) | 重要决策及代码/归档依据 |
| [local-review-service-v1.md](local-review-service-v1.md) | 当前应用服务/API、存储、令牌、安装、演示与反馈示例 |
| [fact-rereview-v3.md](fact-rereview-v3.md) | 最新真实事实阶段验证/schema12；不是新完整闭环 |
| [python-architecture.md](python-architecture.md) | 初始 Python 分层设计；具体实现以现有代码和服务装配为准 |
| [offline-harness.md](offline-harness.md) | 离线 Harness 与环境说明；旧测试数量为阶段记录 |
| [markdown-retrieval.md](markdown-retrieval.md) | Markdown/SQLite/BM25/Evidence 基础链路 |
| [pdf-retrieval.md](pdf-retrieval.md)、[pdf-retrieval-quality.md](pdf-retrieval-quality.md) | PDF 提取、页内切分、定位/邻接和解析风险 |
| [harness-retrieval.md](harness-retrieval.md) | Retriever 注入、冻结版本、预算和失败处理 |
| [generation-agent.md](generation-agent.md)、[deepseek-generation.md](deepseek-generation.md) | 生成/连接器基础说明；引用现使用 answer units/schema3，旧偏移协议非最新 |
| [evidence-verification.md](evidence-verification.md)、[power-domain-review.md](power-domain-review.md)、[bounded-revision.md](bounded-revision.md) | 各能力实现阶段说明；最新协议以 handoff/assembly 为准，领域规则仍为演示 |
| [semantic-retrieval.md](semantic-retrieval.md) | 已有可选 Dense/RRF；初始评测阶段的未标注状态已过时，不是默认服务配置 |
| [legacy-migration-principles.md](legacy-migration-principles.md) | 旧算法不得作为生产规范；其当时未实现能力声明不代表今天 |
| [知识来源 README](knowledge-sources/README.md)、[manifest.json](knowledge-sources/manifest.json) | 三份实际官方资料来源、哈希、版权/适用范围及获取失败记录 |
| [development-questions.json](knowledge-sources/development-questions.json) | 官方资料阅读开发问题，非专家标注验收集 |
| [deepseek.example.json](config/deepseek.example.json)、[.env.example](../.env.example) | 非敏感配置示例；不读取真实 .env |

## 历史协议修复与闭环准备

| 实际路径 | 状态 |
|---|---|
| [claim-extractor-diagnosis.md](claim-extractor-diagnosis.md)、[verification-contract-diagnosis.md](verification-contract-diagnosis.md) | 历史失败诊断，保持原失败状态 |
| [q1-review-boundaries.md](q1-review-boundaries.md) | 原引用、独立支持与输入覆盖边界 |
| [verification-output-v4.md](verification-output-v4.md)、[q2-v4-preflight.md](q2-v4-preflight.md)、[verification-output-v5.md](verification-output-v5.md)、[verification-output-v6.md](verification-output-v6.md) | 旧契约演化；不作为当前 schema12 请求模板 |
| [protocol-stability.md](protocol-stability.md) | 旧闭环执行稳定性修复与部分结果隔离 |
| [acceptance-preparation.md](acceptance-preparation.md)、[acceptance-candidates-v1.md](acceptance-candidates-v1.md) | 旧基线/候选验收设计；候选未经确认不称人工标准答案 |
| [evidence-delivery-trial.md](evidence-delivery-trial.md) | 六场景88响应交付对照；cross_page_next_first 未采用 |
| [review-reliability-v1.md](review-reliability-v1.md)、[review-reliability-v2.md](review-reliability-v2.md) | 历史真实性、单位、快照和模板失败，不因新代码改写为成功 |

## 本机归档：当前验证和关键失败

| 路径 | 含义 |
|---|---|
| [service-delivery-v1.json](../data/runtime_local/service-delivery-v1.json) | 服务v1初交付逐文件SHA、417测试、当时零付费、历史保护检查 |
| [http-demo-bab0e40a44814ec8925ab29baaf8f225.json](../data/runtime_local/http-demo-bab0e40a44814ec8925ab29baaf8f225.json)、[http-restart-verification-v1.json](../data/runtime_local/http-restart-verification-v1.json) | 实际 HTTP/重启演示，仅 synthetic_fixture |
| [fact-rereview-v3/full-report-v3.md](../data/retrieval_local/deepseek/fact-rereview-v3/full-report-v3.md) | 两场景与12数量组件逐条真实结果、语义疑点 |
| [plan-v3.json](../data/retrieval_local/deepseek/fact-rereview-v3/plan-v3.json)、[actual-failure-matrix-v3.json](../data/retrieval_local/deepseek/fact-rereview-v3/actual-failure-matrix-v3.json) | 冻结版本/哈希、实际结构错误与纠正 |
| [reliability-v2/reading-notes-v2.md](../data/retrieval_local/deepseek/reliability-v2/reading-notes-v2.md)、[full-report-v2.md](../data/retrieval_local/deepseek/reliability-v2/full-report-v2.md) | v2 实际失败阅读与逐阶段报告 |
| [official-trial-review.md](../data/retrieval_local/deepseek/official-trial-review.md) | 五问生成对照，引用可回查不等于支持 |
| [revision-summary-v1.md](../data/retrieval_local/deepseek/revision-summary-v1.md)、[protocol-failure-matrix-v1.md](../data/retrieval_local/deepseek/protocol-failure-matrix-v1.md) | 旧修订/重审实际契约失败 |
| [stability-minimal-v2.md](../data/retrieval_local/deepseek/stability-minimal-v2.md)、[stability-minimal-v3-rereview.md](../data/retrieval_local/deepseek/stability-minimal-v3-rereview.md) | 旧版本初审修订及重审；不能拼为最新服务协议完整成功 |

更多早期事实审核按实际文件名保存在 `data/retrieval_local/deepseek/evidence-review-*.json/.md`；原始响应在该目录的 `response-diagnostics/` 及各版本批次目录。服务未来归档在 `data/retrieval_local/service_private/{run_id}`；API不返回其本机绝对路径或整段原始响应。运行数据库和令牌为私有设施，不上传或打印。

## 检索与监督标注实验（已结束，不自动重跑）

| 路径 | 状态/结论 |
|---|---|
| [dataset-v1.json](../data/retrieval_local/semantic/dataset-v1.json)、[comparison-v2.md](../data/retrieval_local/semantic/comparison-v2.md) | 原30问题/三方法阶段比较；自然问题、关键词和家族要分开 |
| [盲审包 README](../data/retrieval_local/semantic/blind-review/README.md) | 盲审材料；mapping 与盲审正文分离，候选池有覆盖限制 |
| [supervised-v3-eval-v3/evaluation.md](../data/retrieval_local/semantic/annotations/supervised-v3-eval-v3/evaluation.md) | AI辅助、用户监督标注评测；不是独立专家全语料金标准 |
| [body-priority-v1/report.md](../data/retrieval_local/semantic/body-priority-v1/report.md)、[audit-supplement.md](../data/retrieval_local/semantic/body-priority-v1/audit-supplement.md) | 正文优先/编码核查历史实验；读取补充审计，不按标题推断收益 |
| [term-expansion-v1/development-v2/report.md](../data/retrieval_local/semantic/term-expansion-v1/development-v2/report.md) | 单变量术语扩展实验及一次有界补标准备 |
| [term-expansion-27-final-v1/report.md](../data/retrieval_local/semantic/annotations/term-expansion-27-final-v1/report.md) | 27补标合并、对称回算；BM25局部收益未改善最终完整依据，保留基线 |
| [reranker-v1/report-v2.md](../data/retrieval_local/semantic/reranker-v1/report-v2.md)、[truncation-review.json](../data/retrieval_local/semantic/reranker-v1/truncation-review.json) | 单模型固定池实验；局部改善/组合退步，不采用；关键已标退步不能归因截断 |
| [reranker-v1/pool-hash.json](../data/retrieval_local/semantic/reranker-v1/pool-hash.json)、[resource-record.json](../data/retrieval_local/semantic/reranker-v1/resource-record.json) | 候选/配置哈希、耗时/内存测量，不是事实支持分数 |

原 PDF：`data/knowledge_local/nerc-guideline.pdf`、`nerc-var-001-5.pdf`、`pnnl-35221.pdf`。AEMO未成功获取，不作为现有语料。原全文和复核派生包未明确允许公开再分发，留在忽略目录，不提交Git。

## 最终手册主题素材索引

代码路径相对项目根。以下入口均已核实存在；大型归档只索引，不复制。当前协议为真实服务装配的schema12及其配套版本，完整版本表见handoff；旧契约代码保留兼容，不意味着服务采用它们。

| 主题 | 实际代码阅读入口 | 说明/实验/归档与状态 |
|---|---|---|
| 目标、架构、边界、旧项目迁移 | `backend/assembly.py`、`harness/runtime.py`、`agents/contracts.py` | 当前handoff/design-decisions；python-architecture为初始设计；legacy-migration-principles为历史迁移原则 |
| 四Agent/Extractor/Harness完整流程 | `agents/generation.py`、`agents/evidence_verification.py`、`agents/power_domain_review.py`、`agents/revision.py`、`services/claim_extractor.py`、`harness/states.py`、`harness/policy.py` | 当前服务说明；旧bounded-revision/protocol-stability报告；真实闭环与最新事实阶段必须分别引用 |
| 入库、切分、存储、溯源 | `rag/markdown.py`、`rag/pdf.py`、`rag/pdf_chunks.py`、`rag/storage.py`、`rag/context.py`、`rag/contracts.py` | markdown/pdf-retrieval及pdf-retrieval-quality；官方来源manifest；原PDF仅本机data/knowledge_local |
| BM25/Dense/RRF与实验取舍 | `rag/bm25.py`、`rag/embedding.py`、`rag/semantic.py`、`rag/retriever.py`、`rag/query_terms.py`、`rag/reranker.py` | semantic-retrieval；body-priority、term-expansion-27-final、reranker-v1报告（上表）；服务当前只默认BM25，实验无模型事实审核含义 |
| 契约、引用、版本、快照 | `core/models.py`、`core/typed_evidence.py`、`core/validation.py`、`services/answer_units.py`、`services/answer_anchors.py`、`services/quote_candidates.py`、`services/evidence_scope.py` | generation/旧v4-v6说明属协议历史；当前独立模板 `agents/review_templates_v3.py` 和 `agents/verification_contract_v9_scoped.py` schema12 |
| 工具、预算、超时、取消、隔离 | `tools/contracts.py`、`tools/unit_conversion.py`、`tools/scalar_numbers.py`、`harness/contracts.py`、`harness/retrieval.py`、`model_adapter/runtime.py`、`services/review_isolation.py` | harness-retrieval/服务说明；SI工具v2、阶段预算、底层取消限制；工具不证明稳定/物理类别 |
| 修订与完整重审 | `agents/revision.py`、`agents/revision_contract_v2.py`、`harness/runtime.py`、`harness/policy.py` | 旧revision-summary-v1/stability-minimal系列真实归档；fact-rereview-v3只有事实阶段，不是最新全闭环 |
| API、持久化、人工反馈、未来界面 | `backend/api.py`、`backend/service.py`、`backend/store.py`、`backend/serialization.py`、`backend/local_access.py` | 当前local-review-service-v1；service-delivery/HTTP重启报告为synthetic_fixture真实HTTP，不是付费模型演示；界面本轮已实现，见local-review-ui-v1和本轮索引 |
| 模型连接与配置排错 | `model_adapter/contracts.py`、`model_adapter/deepseek.py`、`harness/deepseek_trial.py`、`backend/config.py`、`backend/__main__.py` | deepseek-generation/服务说明、requirements-api.lock.txt；只使用无密钥示例，真实.env不作为文档素材 |
| 真实失败、修复、未解决问题 | `services/review_fidelity.py`、`services/claim_obligations.py`、`services/quantity_checks.py`、`services/validation_diagnostics.py`、`services/response_diagnostics.py` | reliability-v1/v2、fact-rereview-v3报告及其实际failure-matrix；N10/N11/N12保留结果，不能用规则替代模型识别 |
| 测试、指标、标注、结论限制 | `tests/`、`evaluation/supervised_retrieval.py`、`evaluation/term_supervised_final.py`、`evaluation/reranker_report.py`、`evaluation/report_fact_rereview_v3.py` | 初交付417项见service-delivery；最新421项见本轮离线日志；监督标注eval-v3/27-final来源明确；12数量例是开发组件测试，非独立专家验收 |
| 面试代码阅读路径 | `backend/assembly.py → harness/runtime.py → agents/contracts.py → core/models.py`，再按RAG/依据/工具/API分支阅读 | 本表提供当前入口；最终需解释设计追问、失败与取舍，不提前编造最终面试回答 |
| 后续微调/采用条件 | 当前没有事实支持判断微调训练管线 | design-decisions及fact-rereview-v3语义漏检是需求依据；人工反馈和监督标签不能未经核实直接当训练金标准，具体方案待后续授权设计 |

初期学习手册参考：`C:\Users\37307\Desktop\PowerTrustAI_Project_Study_Handbook_20261003.pdf`，2026-10-04确认存在，284440字节。本轮未读正文、未复制到项目；是历史形式参考，不是当前有效版本的实现报告。

## 2026-10-04 新会话素材维护记录

本轮已读五份基线/交付规则文档，并只读核对 backend/assembly.py 的 BM25、OfflineHarness 和显式 schema12 装配。无新增实验、失败或测试结果；当前任务等待用户提供具体内容。最终中文手册仍未编写，既有主题素材索引继续保留，历史记录与默认检索不变。


## v0.1收尾素材（2026-10-04）

- [prototype-v0.1.md](prototype-v0.1.md)：统一运行、令牌/密钥区别、中文结果解释、版本/证据/反馈、错误与重启；明确完整验收未完成。
- [验收结论](../data/runtime_local/v0.1-acceptance/reading-notes.md)、[修订预检审阅](../data/runtime_local/v0.1-acceptance/revision-review.md)、[机器验证记录](../data/runtime_local/v0.1-acceptance/verification.json)：本轮修改、零新增模型调用、真实/演示分层、Git限制。
- [最终冻结预检](../data/runtime_local/v0.1-acceptance/frozen-plan-final.json)：构造输入、知识与源码配置哈希、14+C2预算证明缺口；未提交模型批次。
- [最终测试](../data/runtime_local/v0.1-acceptance/offline-tests-final.txt)、[客户端检查](../data/runtime_local/v0.1-acceptance/client-checks.txt)：427项离线通过及链接/恶意文本/重复POST等客户端检查。
- [重启对照](../data/runtime_local/v0.1-acceptance/restart-verification.json)：两旧真实结果和演示v2反馈一致，无重发；旧9次调用不计为新增验证。
- [中文摘要截图](../data/runtime_local/v0.1-acceptance/chinese-summary.jpg)、[来源截图](../data/runtime_local/v0.1-acceptance/source-links.jpg)、[演示修订截图](../data/runtime_local/v0.1-acceptance/demo-revision.jpg)：实际内置浏览器，无令牌。
- backend/presentation.py、serialization.py、static/app.js 与 tests/test_v01_presentation.py：确定性中文解释和结构化来源处理；最终手册的重要架构/失败素材，当前不编写手册。
- [源码快照](../data/runtime_local/v0.1-acceptance/source-snapshot-v0.1.zip)、[路径哈希清单](../data/runtime_local/v0.1-acceptance/source-snapshot-manifest.json)：本机文件恢复材料；Git身份缺失未提交，不冒充Git可回退基线。

### 用户撤销30上限后的真实修订素材

- [新授权冻结计划](../data/runtime_local/v0.1-acceptance/frozen-plan-authorized.json)：单一构造输入、独立预算、默认配置保持；早期停止记录不覆盖。
- [实际真实运行](../data/runtime_local/v0.1-acceptance/e1c6bc1336cd4c89acee8bd2795a0ebb.json)：浏览器唯一API POST；v1 contradicted→一次Revision→v2重提取/双审；8请求、最终review_required。
- [原响应和消息核验](../data/runtime_local/v0.1-acceptance/raw-archive-verification.json)：8份原响应SHA与消息路径；实际消息/响应留data/retrieval_local/service_private对应run，不进Git。
- [真实重启核验](../data/runtime_local/v0.1-acceptance/real-restart-verification.json)：具体v2 finding反馈与完整结果一致，8→8、无POST重发。
- [真实修订截图](../data/runtime_local/v0.1-acceptance/real-revision.jpg)、[反馈截图](../data/runtime_local/v0.1-acceptance/real-feedback.jpg)、[重启截图](../data/runtime_local/v0.1-acceptance/real-restart.jpg)、[最终摘要](../data/runtime_local/v0.1-acceptance/real-final-summary.jpg)：实际内置浏览器，无凭据。
- [批次后最终测试](../data/runtime_local/v0.1-acceptance/offline-tests-post-batch.txt)：428项通过，45.986秒；修复JSON诊断位置后离线验证，无新模型调用。
- [冻结真实源码](../data/runtime_local/v0.1-acceptance/frozen-real-runtime-source.zip)：保存已执行批次的manifest源码；最终源码另存快照，二者投影差异明确，不能混为同一版本。
- reading-notes-preauthorization.md、revision-review-preauthorization.md及早期冻结预检：真实保留预算停止与后续授权历史，当前结论以reading-notes.md/revision-review.md为准。

## GitHub新项目基线上传素材（2026-10-04）

用户指定新仓库 https://github.com/7556481/PowerTrustAI.git；仅D:/PowerTrustAI，旧独立项目不操作。检查基线明确清单、暂存/历史blob、远端引用和推送回查证据将保存在 data/runtime_local/github-baseline/，不含凭据。提交/推送不会改变最终中文学习与面试手册要求，不替代手册交付。

### 最新本地基线与手册交付

- 本地基线：master / `3d5e0cd842a1039731aafb209fb5444bd1905622`，218个文件；candidate-audit.json、staged-audit.json、history-audit.json证明明确路径和历史blob核对。旧段落的未提交/身份缺失为当时状态，最新提交覆盖其当前状态。
- [GitHub网络诊断与修复步骤](github-upload-troubleshooting.md)：只读连接重置、未到登录、未推送，代理凭据不输出；远端历史仍未知。
- [中文项目学习与面试手册源](PowerTrustAI-project-study-interview-handbook.md)：17章，实际代码、真实失败、指标分母与面试追问；README不替代。
- [图源](handbook-diagrams.md)、`tools/build_handbook_pdf.py`：可编辑Mermaid与PDF矢量图/分页/目录生成。文档工具不修改项目模型/服务环境。
- `output/pdf/PowerTrustAI_Project_Study_Interview_Handbook_v0.1.pdf`：31页最终交付，中文嵌入字体、目录书签、分页；全部页面实际渲染。
- `data/runtime_local/final-handbook/build.json`、`pdf-verification.json`、联系表与页面PNG：SHA/页数/55个代码路径/视觉检查。旧桌面PDF正文未读，自动审批拒绝记录见handoff。
- 本轮新增付费请求0，未重跑历史检索实验；现有428项最终测试证据不宣称本轮重新执行。Git基线之后的手册及交接资料仍未提交，精确清单见github-baseline/final-delivery.json。

### 2026-10-04 学习手册定向修订r1（当前阅读入口）

- [r1可编辑手册](PowerTrustAI-project-study-interview-handbook-r1.md)：六项定向纠正、BM25/E5/RRF与unknown算例、必要组合、5段真实短代码、面试追问。应用仍v0.1，文档r1。
- [r1修改清单](handbook-r1-changes.md)：逐项依据、实际职责、未修复限制与旧版保留。
- [r1图源](handbook-diagrams-r1.md)、tools/build_handbook_pdf_r1.py：控制/数据/observer关系，独立构建不覆盖旧文件。
- output/pdf/PowerTrustAI_Project_Study_Interview_Handbook_v0.1-r1.pdf：38页新PDF，18个目录书签，全部页面重新渲染复核；旧31页PDF保持不变。
- data/runtime_local/handbook-r1/original-hashes.json、code-excerpts.json、build.json、verification.json：旧SHA、源码行号/摘录SHA、当前HEAD、源码比对、教学算术、全页渲染和排版核验。
- 当前本地历史仍仅3d5e0cd/master，无基线后文档提交；128个应用源/资源未变。本轮API/模型/历史实验/网络查询/提交/推送均0。前轮网络重置为2026-10-04记录，不作永久现状。旧索引的“当前手册31页”以本节r1入口接续。

### 2026-10-04 手册r1独立本地文档提交

按后续授权提交15个明确文档交付路径，包含旧版与r1源/PDF/图源/构建器、修改清单及相关说明；应用代码不变，不推送。data/runtime_local/handbook-r1/document-commit.json记录实际提交哈希、父提交、逐文件SHA与最终工作区状态。前节无文档提交为修订完成时的历史状态；引用工作量修复尚未开始，本轮不扩写手册、不调用API。

### 2026-10-04 引用工作量边界v1

- [诊断、配置与复现](citation-review-workload-v1.md)：schema13/v9.5稳定有界分组、项级作用域、调用结构、API薄接线与容量失败。
- data/runtime_local/citation-review-workload-v1/reading-notes.md、verification.json：最终离线、真实范围、冻结/最终源码SHA与本地提交；全部私有，不进Git。
- frozen-plan.json、frozen-runtime-source.zip、api-result.json、api-trace.json、real-summary.json、raw-archive-verification.json、evidence-roundtrip.json、restart-verification.json：唯一真实2引用/1组/3调用；执行未完整的真实失败保留，修后未重跑。
- offline-tests*.txt、targeted*.txt、api-debug.txt：早期失败、schema13输入接线与容量范围修复、最终回归；不以测试数量代替语义正确。
- 用户手动推送后fetch成功，origin/master核实526bdee；本轮新提交仅本地，不覆盖历史网络记录。手册r1 Markdown只补状态，不重生成PDF。


### 2026-10-04 schema13最终接线回归

- citation-review-workload-v1.md最新小节：fb235746真实初审→自然一次Revision→重提取/双审；三审核阶段完成，业务未全部可评估。
- data/runtime_local/citation-review-workload-v1/schema13-final/reading-notes-final.md、verification-final.json：新run b4ede2ab、10请求/1纠正、逐目的请求/消息容量/每项绑定范围、用量、Git文档提交。
- 同目录frozen-plan.json、api-result.json、api-trace.json、evidence-roundtrip.json、restart-verification.json：原样输入与固定知识，旧31459a原档SHA不变，新旧独立库存在，重启相等无新增调用；实际消息/响应留service_private对应run并核对SHA。
- 仅HTTP接线验证，无浏览器检查或PDF重生成；上一批真实失败保持原结果，最新回归独立解释。
