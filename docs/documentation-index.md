# 文档索引

## 2026-10-05 中文问答与展示 v1（最新）

[qa-usability-v1](qa-usability-v1.md)：有限跨语言补检、无回答待补充/不适用、中文生成提示、答案引用/默认折叠；唯一真实运行连接失败与未完成范围。私有qa-usability-v1保留冻结/原始运行/实际浏览器/测试/哈希/审阅包，历史不回填。

## 2026-10-05 产品逻辑与性能改进 v1（最新）

- [产品处置、适用范围、真实失败、性能与试用](product-improvement-v1.md)：原v1四真实结果、新v1.1离线修复、直接AI失败和未完成检查分开报告。
- harness/product_policy.py与原runtime/states；core产品合同；backend日常装配/页面；generation可选提示；只读PDF校验缓存及tests/test_product_policy.py。
- 忽略product-improvement-v1：修改前源码诊断、冻结预期/配置、原真实/合成结果、政策重放、性能/资源缺口、浏览器/重启/测试和ZIP；无凭据/DB/权重。长期学习内容暂停，仅记录后续知识点。

## 2026-10-05 连续连接体验（最新）

- [固定令牌路径、浏览器主动记忆、401与验证](connection-memory-v1.md)：不同验证目录是不同服务身份，日常固定文件复用，579回归/实际浏览器通过。
- backend/static/connection_memory.js及app.js/页面，backend/api静态白名单；tests/test_connection_memory.py和ui_connection_memory_probe.js执行实际脚本，不导出令牌。
- 忽略connection-memory-v1仅保存路径/stat/布尔验证/截图/测试/verification-final，真实值和浏览器存储不归档。

## 2026-10-05 NLI真实接线v2（最新）

- [类型/组件范围修复与一次真实验证](local-nli-wiring-v2.md)：575离线，1实际组件、Fact/NLI同supported，业务仍review_required，4真实请求；浏览器/重启/停止已验证。
- services/local_nli.py的production_frames_v1保留及默认转换v2；evaluation/support_nli.py处理合法空provenance；tests/test_local_nli_wiring.py真实Harness schema13 synthetic贯通，不绕过转换。
- 忽略data/runtime_local/local-nli-wiring-v2：提交前request/source/config/preview/源码SHA、一次正常真实run及nli/trace/实际身份/全文token、只读历史类型对照、浏览器/重启hash、原记录不改/默认不变、ZIP与verification-final。DB/权重/令牌不打包，不重放run-id标记。

## 2026-10-05 本地NLI可选旁路（最新）

- [职责/配置/实际回放/浏览器/限制](local-nli-diagnostic-v1.md)：默认关闭、无最终审核权，固定epoch1，严格交付范围，不改原政策。
- services/local_nli.py、backend/nli_worker.py及backend服务记录/API/独立页面；tests/test_local_nli.py公开synthetic回归。
- 忽略data/runtime_local/local-nli-diagnostic-v1：错误说明修正及清单、profile/源码校验、初始失败、33+2已见诊断回放/原logits/输入、只读历史缺口、HTTP/浏览器截图/重启记录/资源、ZIP/verification-final。新回放数据库留本机，不打包，令牌不读/不输出/不打包。

## 2026-10-05 扩大微调与SSIAG文档留出实际结果（最新）

- [一次实际训练/留出/风险与运行](support-nli-expanded-v3.md)：69明确确认另版，43/12/33；epoch1，macro-F1提高但错误supported4/23，不接生产。
- evaluation/support_nli_expanded.py与tests/test_support_nli_expanded.py：确认子集、冻结SHA、开发/文档隔离、train/heldout阶段seal与排他输出、双分母/三类矩阵。
- 忽略data/runtime_local/support-nli-expanded-v3：confirmation-event/confirmed69/监督78视图、55开发/33留出、固定分配/输入/token/有效集合/config/源码模型SHA、独立环境、run-v1四epoch/selection-seal/两逐项logits/指标、错误分析/保留性检查、ZIP/verification-final。权重留本机不入ZIP/Git，原pending和历史保持。

## 2026-10-05 78项复核与扩大开发计划（最新）

- [复核接收/69pending/合并家族/SSIAG留出/适配器v2](support-nli-review-v2.md)：55开发→13家族→43训练/12验证，33文档留出，仅准备0训练/预测。
- evaluation/support_nli_review.py（read_review_archive/receive_pending/merge_groups/propose_split）、support_nli.py（v1保留、v2正文路由、pending训练前置拒绝）及公开合成测试。
- 忽略data/runtime_local/support-nli-review-v2：received原包/成员SHA、quality-version、69/6/3分流、三修改理由、69模板/清单、原划分/关联边/新划分、55合并与33留出、token预检、固定官方基座计划、验证/失败及审阅ZIP。原78/19/历史报告不覆盖。

## 2026-10-05 NLI实际比较、训练与新候选（最新）

- [NLI完整结果与限制](support-nli-v1.md)：两个预训练NLI头、事前验证/资源选型、唯一4epoch领域微调、5项开发对照、78pending候选与未来文档隔离。
- evaluation/support_nli.py、support_nli_candidates.py及对应合成测试；生产默认保持。
- 忽略data/runtime_local/support-nli-v1：模型来源/实际revision/冻结配置、comparison两报告、training-run-v1实际输入/前后预测/逐类指标、78候选/标签模板/来源/未来划分/审阅HTML、失败说明、ZIP与verification-final.json。权重/PDF/私有监督保持本机，不公开。
- 最终手册要求Markdown＋本地文档站/PDF可选；已追加NLI知识点与源码入口，本轮未建站或重写手册。

## 2026-10-05 新机上下文与长期手册要求

- [最终手册要求](final-handbook-requirements.md)：最新采用Markdown＋本地文档网站，PDF可选；38页r1为阶段版。本轮只维护要求，不建站或重写正文。
- [最新交接](handoff.md)：核对基线27ec898、当前生产配置、源码入口、已完成首次训练和待补NLI章节；具体NLI任务说明待补充。
- 本机恢复报告与验证：忽略`data/runtime_local/new-machine-restoration/new-machine-restoration.md`、`verification.json`、`browser-verification.json`。恢复已完成，不重复迁移/监督确认/首次训练；不把前轮536测试当本轮重跑。
- 当前训练结论仍以[support-finetune-v1](support-finetune-v1.md)及实际report为准；下面按日期保留历史素材，旧“未训练”不代表当前状态。

## 2026-10-05 监督74、独立基线与首次三类CPU微调

- [实际监督/材料许可/硬件/运行/结果与限制](support-finetune-v1.md)：74confirmed，71辅助hold未确认；79新请求/69有效/5作用域失败；同BERT基座实际一次微调，11训练/3验证/5测试，不接生产。
- evaluation/support_baseline.py执行v2；evaluation/support_training.py的模板确认、许可筛选、家族划分、完整文本投影及独立CPU训练；requirements-training-v1.txt只隔离环境；tests/test_support_independent.py、test_support_training.py公开synthetic_fixture。
- 忽略data/runtime_local/support-finetune-v1：confirmation-event/confirmed-primary/source-filter/partition-plan/training-config/model-revision/训练环境lock；deepseek-baseline-v3原冻结/预测/指标/checkpoint；training-run-v1初始模型/验证最优检查点/前后预测/report；reading-notes、final-report、verification-final、监督对照ZIP与失败日志。实际79响应在忽略retrieval_local/support-baseline-v2/full74-v1，逐SHA核对。
- 保留旧145、原91/48/6/旧预测、历史网络与PDF，不改写为新监督或成功结果。


## 2026-10-05 54复核接收与74候选基线准备

- [合并/依据子集修复/准备范围](support-review-merge-v1.md)：全145保留，74主候选仍pending，尚未运行基线。
- evaluation/support_review_merge.py及tests/test_support_review_merge.py：无API接收/合并/逐样本冻结；support_review_quality仅保留实际依据子集。
- 忽略data/runtime_local/review-expansion-54-v1/：received、merged-v1清单/分流/共享关系/请求冻结、合并报告、ZIP、reading-notes/verification与离线日志。原资料及任务保持，不重建PDF。


## 2026-10-05 91监督审阅接收与新增质量检查

最终本机入口：quality-supplement-v3.zip、expansion-quality-dataset-v1.json及import-pending-v2；hold/辅助实际从主任务eligibility排除，48原task保持、6修订仍pending。旧补充版本留存。

- [选择性监督、实际48项质量检查及新任务身份](support-review-quality-v1.md)：91分流33/29/29，新增48为36/1/11，另建6pending任务；不整包确认或沿parent搬旧预测。
- evaluation/support_review_quality.py；公开tests/test_support_review_quality.py（synthetic_fixture）。运行仅离线，不改生产协议。
- 忽略data/runtime_local/support-review-quality-v1/：import-pending-v1三个分流、源审阅报告、expansion-quality-review-48.md/json、amended-tasks-v1/v2及review、priority-confirmation-template-33、hold-repair-requirements-29、quality-supplement-v2.zip、prediction-scope-check、reading-notes.md、verification.json及测试。附件原pending字段与用户当前监督声明分别保留。
- 来源PDF/私有任务/标签不公开，最终r1手册不改。确认范围和Git/远端证据以本机verification为准。

## 2026-10-04 知识库与支持判断样本扩充 v1

- [实际官方来源/覆盖缺口、入库快照、pending样本与隔离](knowledge-support-expansion-v1.md)：新4PDF（3开发＋1预留）、48新候选/16家族；不覆盖旧91或重跑基线。
- evaluation/knowledge_support_expansion.py：离线复制知识历史、来源锚定、原文定位及复用候选/复核出口；tests/test_knowledge_support_expansion.py：公开临时synthetic_fixture。
- 私有data/runtime_local/knowledge-support-expansion-v1/：source-manifest/acquisition、development.sqlite3/reserved-evaluation.sqlite3、ingestion、parse-summary、curated-families、candidates-v1/v2、support-review-expansion-v1.zip、reading-notes.md、verification.json、offline-tests与选页PNG。全文/候选不入Git，预留文档不进开发库。
- 最终r1手册继续保留，未扩写或重建PDF。pending不能替代用户监督或独立金标准。

## 2026-10-04 证据支持判断数据集与未微调基线 v1

- [任务/标签、实际候选/划分、运行命令与失败基线](support-judgment-dataset-v1.md)：未训练、未改生产审核；pending不计算语义指标。
- evaluation/support_dataset.py：提取/校验/去重/家族分组/AI辅助复核导出与监督合并；evaluation/support_baseline.py：现有连接器基线、离线四分类指标、仅确认标签JSONL出口。
- 公开tests/test_support_dataset.py、test_support_baseline.py；实际页面脚本tests/ui_render_probe.js及test_ui_render.py。数据/原文/实际响应不入Git。
- 本机data/runtime_local/support-dataset-v1/：reading-notes.md、verification.json、prepared-review-v2/、support-review-package-v1.zip、baseline-frozen-v1/、offline-review-v2-metrics.json、offline-tests日志和browser-verification.json。91项全pending，2请求后结构失败停止，仅5有效部分预测；0确认，不宣称语义正确率或完成整批。
- 来源与划分报告保留22片段跨集合共享、274缺冻结请求跳过；既有私有历史不覆盖，r1/PDF不重建。当前状态与路线已区分数据准备已实现、训练尚未启动。


## 2026-10-04 真实服务可选语义检索 v1

- [运行、配置、生命周期、三模式固定对照与真实结果](semantic-service-v1.md)。bm25默认、事实策略独立；不下载/建索引/退回默认，完整重放开销明确。
- 服务backend/config.py、assembly.py、service.py、api.py；rag/semantic.py、embedding.py、harness/retrieval.py；安全页面详情backend/static/app.js。公开固定对照入口evaluation/semantic_service_comparison.py、七项公开tests/test_semantic_service.py。
- 本机data/runtime_local/semantic-service-v1/：reading-notes.md、verification.json、comparison*.json、resource-*.txt、冻结计划、475项根/干净测试日志、real-summary.json、real-verification.json、Evidence和restart-verification.json。run4676b27e：11请求、一次自然Revision、必需阶段完整/0执行问题，业务仍review_required。实际输入/响应/模型/库保持忽略。
- 旧手册/PDF、semantic历史报告保留。真实HTTP检查不替代浏览器检查；消息投影不冒充已发送/已验证，计数与资源测量口径见说明。当前提交/普通推送回查在本机verification.json及Git日志。

## 2026-10-04 逐主张事实检索与证据交付 v1

- 实现提交02c71bd已普通推送master并回查远端同哈希；最终交付说明提交及回查记录在本机verification.json。使用命令级127.0.0.1:7890代理，未改全局代理或SSL。

- [实现与运行](per-claim-fact-retrieval-v1.md)：可选策略、事实对象/依据分流、查询缓存、显式版本/范围、失败与容量、schema13输入v1、预算及安全页面详情。
- [固定对照](per-claim-fact-comparison-v1.md)：四组相同回答/主张/知识/BM25，目标命中与交付、持平/增益及额外资源/延迟；保留aggregate默认。
- 源码：harness/fact_retrieval.py、services/fact_delivery.py、evaluation/fact_retrieval_comparison.py；13项新公开synthetic_fixture测试test_fact_retrieval_v1.py。
- 本机data/runtime_local/per-claim-fact-v1/：comparison-frozen.json、comparison-results.json、comparison-final.json；frozen-real-plan.json、api-result.json、api-trace.json、real-summary.json、real-verification.json、evidence-roundtrip.json、restart-verification.json、offline-tests-delivery.txt、reading-notes.md、verification.json。真实请求/响应仍在data/retrieval_local/service_private/53613803b0a248819bf3d063ce41d5c8。
- 自然一次Revision，10模型/7检索/1纠正，最终无执行问题、必需阶段完整但业务review_required；重启相等无重发。官方资料/实际响应不入Git；PDF未重建，旧30题未重标。

## 2026-10-04 最新公开复现与并行轨迹修复

- 代码提交97e3523最终独立克隆455项通过；final-stdlib-tests.txt、final-locked-tests.txt、final-harness-demo.txt、final-http-demo.txt保存实际提交验证。普通push因github.com:443连接失败未成功，最新提交与待推送范围见verification.json，不能以旧origin/master冒充远端同步。

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
