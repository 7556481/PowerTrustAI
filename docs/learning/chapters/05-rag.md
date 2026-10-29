# 05 RAG全过程：从文件到可回查Evidence

## 2026-10-29：派生索引与权威原文分离

本轮Tantivy0.27.0只在忽略目录建派生postings/ID与hash映射；同一jieba预分词串分别写入单字段FTS5和Whitespace Tantivy，命中仍通过原KnowledgeStore/Evidence/邻接层回查，既有source/version/locator不变。没有接入产品Retriever、生成或审核，也未验收异步取消。

48k同数据四宽TopK快3.86—5.86倍，但50k建库反复worker失败，只保住48k完整前缀；不能把小样本倍数或命中数相同当全库无损。48组来源专项含132根读取/115邻接通过，只证明映射；指定文献674质量集合单列，不混入分散样本冒称自然召回。当前生产仍SQLite FTS/schema13，PR #4取证解耦资产保持关闭。[详细边界](https://github.com/7556481/PowerTrustAI/blob/codex/tantivy-bounded-feasibility-v1/docs/evaluation/tantivy-bounded-v1/report.md)。

## 资料在哪里丢失：存在、命中、交付是三件事

自然v3的8份N稿全部缺目标NERC资料，审核没有制造改善；N4“单一大设备”和历史H3把when改only又属于独立漏检。后续有界定位确认目标268片段在原生FTS库中，但8个必需段落的原查询MATCH均为0。主体词NERC及泛词“文字”约束、中文问题对英文词项的间隙，是实际观察到的断点。未向量化不是已证根因。

chinese_first_cross_language_v1候选先核对机构/标题目录，再决定是否进行一次中英查询转换。目录保留同机构多文档、同标题多版本，冲突/未知不能静默挑一个。它默认关闭；本轮固定稿审核完全没有重新打开70GB库。[完整证据](https://github.com/7556481/PowerTrustAI/blob/99b93497cb78bf3f040f1874ad07cb525be6d64b/docs/evaluation/chinese-first-cross-language-retrieval-v1/report.md#)。

::: answer 新增：库内有268片段，为什么仍答资料不足？
库内存在只证明可供检索。MATCH可能因subject或语言词项为0；命中后还可能被排序、截断、相邻交付丢失。必须分别看目录、原MATCH、top-k、实际Evidence及生成快照。给未交到模型的原文打正确标签，是回填历史。A稿按自身资料说明不足是合理行为。[完整证据](https://github.com/7556481/PowerTrustAI/blob/99b93497cb78bf3f040f1874ad07cb525be6d64b/docs/evaluation/chinese-first-cross-language-retrieval-v1/report.md#)；[完整证据](https://github.com/7556481/PowerTrustAI/blob/a6ba66d4787e2806d828edd84ec6435cc6e2d64f/docs/evaluation/retrieval-evidence-answer-check-v1/report.md#)
:::

## 完整案例一：N1从资料不足到有据回答

上轮固定证据回答诊断，以原中文问题问TO/DP边界建模及位置。A使用原检索的实际材料，C使用跨语言候选归档Evidence；没有重译问题，也没有把错误查询当事实来源。

A原稿全文：

所给NERC相关资料只涉及电网运行安全角色与要求（如电力传输运营商等责任实体），未描述TO与DP边界负荷的建模方法，也未列出建模位置选项，因此无法据此回答。

C原稿全文（也是本轮审核前后相同的交付）：

NERC指南指出，TO与DP在潮流、稳定分析和实时运行中的边界通常用显式负荷（以MW和Mvar表示）定义。建模位置可选：直接放在母线/变电站高压侧，或放在降压变压器之后和/或等效配电阻抗之后。

跨边界建模的负荷功率因数（LPF）会影响BES的电压与无功表现；负荷不应过度依赖BES的无功支撑，BES也不应仅依赖负荷的无功支撑。

A没有读到目标段，说明不足合理，不能称错误拒答。C的完整来源为NERC 2016 Reactive Power Planning，Transmission to Distribution Coordination / Modeling，Evidence e-62aa9c4011e99f7ace774dff4a002625d1e319d8aee364b0154c5eaddccbc247；实际抽取文件第37页，page_chars[0:1193)、page_lines[1:21]；目录、版本及引用绑定见[冻结案例](https://github.com/7556481/PowerTrustAI/blob/a6ba66d4787e2806d828edd84ec6435cc6e2d64f/docs/evaluation/retrieval-evidence-answer-check-v1/cases.md#)。两类位置及and/or保留，必答2/2。改善属于资料交付后的生成，本轮审核未增加正文收益。

归档身份核对：A运行f7dc7f6eb45b40e8a73e8d26c15ead75，实际来源示例为dataset-record-eb646d26de0626d5f5609d11a1adc4ac5b93f5b0838fa0faed1eda141ef0ec03，版本e15146cdf43916c5833e6ff91c1956ecec6f596717bbf74915e7332662db4662，Evidence e-a3b05eaf89e8e55745237c6123ca44cf3d409683836459b71c6fd9720cfe5140，定位shard=chinese/middle/rank_00415.parquet;row=67967;record=397600026370;chars[2101:3158)，类型industry_corpus_unverified；不是NERC官方建模段。C运行ab2d55acdd994b4782b0fb4abeaf72a8，实际来源nerc-reactive-planning-2016，版本dbf1bc7c3e57ae2b3b70b01a677eb0ac1479873fdcc7075eb101c93e1f54e193；上述页37原文Evidence来自它。示例不能冒充全部来源，逐Evidence映射及实际快照哈希见冻结案例；今天只读公开归档，不重检索或生成。

[演示下一站：A3修订](04-harness.html#section-3) · [返回7分钟路线](index.html#section-2)

## 历史说明与基础知识（保留原日期，当前状态以上文为准）

## RAG是什么，为什么不能只存embedding

RAG是先检索再生成。它可以让模型基于实际交付资料回答，但不会自动使资料正确或引用支持成立。若只存向量和一段摘要，后续无法证明某个限定是不是原文存在。本项目把SQLite中的原文、版本和字符区间作为权威，搜索表示只是派生物。

教学构造：原文“在C下，A才导致B”，搜索词可以包含A/B/C和标题，Evidence.text必须保留完整原句及定位。模型看到摘要“A导致B”时，不能再宣称它读过必要条件。召回、排名、上下文交付、生成选用、最终引用五步要分别追踪。

## 入库：字节、文档版本与知识快照

KnowledgeStore.ingest读取实际文件和SourceMetadata，计算原件哈希，解析Markdown或PDF，建立文档版本、派生片段及新的知识集合。metadata可登记机构、日期、地区和类型；没有证据的字段保持未知，不用文件名猜出版机构。

文件SHA用于“同一个原件”，解析版本用于“同一次文本派生”，knowledge_version用于“本次检索允许哪些版本”。更新不是在旧版本上直接改text。原始内容、解析和切分共同影响身份；一个新切分方案必须能与原记录分开回查。

## Markdown与PDF：字符定位不等于视觉正确

Markdown块可以按标题和段落切分；PDF要处理页码、字符区间、表格和公式。rag/pdf.py、pdf_chunks.py、storage.py保存解析报告、质量告警及派生版本。页码至少区分文件页与印刷页；章节号不是页码。多栏顺序错误、脚注混正文、表格断行会使可精确回查的文本仍不等于视觉原稿。

字符区间通常采用半开区间[start,end)，原文[start:end]必须等于Evidence.text。这样相邻区间不会重复边界字符。摘要、空白归一和原文映射必须另有版本说明，不能把人工写答案冒充来源。真实教材小节曾保留非空白逐字一致及原页映射，这与“我觉得这样讲更清楚”的改写不同。

## 切分：长度、边界和必要条件

片段太长会增加请求成本和token溢出；太短会割掉条件、来源范围或代词对象。项目有固定切分配置和有界相邻上下文，预算不够时省略完整片段并记录，不能静默切半条原文。邻居是独立Evidence，不伪装成高分核心命中。

教学练习：把“当电压和有功保持不变时，电流随功率因数提高而减小”从逗号处分开，第二片只有结论。问为什么补邻片仍不能保证正确？参考：机械相邻不保证同一逻辑范围，后页可能新章节；需要版本邻接和语义检查，不能默认拼接即支持。

## 小库BM25与大库FTS5

rag/bm25.py对英文提小写字母数字，对中文提单字及双字组合，避免直接按空格把整句当一词。原小库可全快照打分；大库几百万行不能每题扫描全部text，因此corpus_index.py采用预分词的SQLite FTS5倒排与BM25排序。

倒排索引是“词→出现位置/文档”的结构。查询少数词只访问命中候选，而不是读取所有正文。FTS5内置分词不自动解决中文：项目固定jieba0.42.1、电力词典和HMM关闭，查询与文档一致处理。术语、普通问句和同义表达都需验证；“功率因素”和“功率因数”的别名必须有明确范围，不能随意扩展所有词。

## 生成交付与审核交付

Generation用途检索围绕原问题，Verification可围绕冻结主张，Domain围绕工程范围。默认aggregate保持；per_claim_v1按组件basis_target组织交付，只在明确配置时使用。不能把全运行检索池都说成每个组件已读；每个交付要保存实际Evidence和绑定。

中文原查询成功但空命中、且语料语言差异满足门控时，已有有限英文补检只转换查询再检索一次。查询转换不回答问题，不添加新技术结论。仍为空应说明“当前检索未找到依据”，不声称整个库无资料。生成跟随用户语言，不额外翻译已生成答案。

## 覆盖缺口分三层，不靠扩大库一并解决

资料未在固定快照、资料存在但未进入排名候选、候选存在但未实际交付，是三类不同问题。大库主要扩大第一层覆盖，不保证候选/交付，更不保证生成保留条件。原中文词项与英文正文不匹配不等于BM25不适合中文；索引和查询分词、术语方案必须一致，不能把主题相似视为完整依据。

预分词FTS5是全文关键词索引，不自动建立全部正文的Dense向量。旧向量profile与知识版本仍须匹配；输入行、唯一正文、片段、向量是不同计数。2026-10-08日常已显式切完整发布FTS快照：70有效片14336177行、8630479正文、24620273片段；3不可读原分片核验排除。旧部分快照保留，完整FTS不等于完整知识覆盖。

对用户应说“本次交付的资料尚不足以支持这句回答”。这不等于该句为假、全库不存在或现实无依据。检索没执行完先说明执行问题；来源未核实则分内容解释与规范权威。

## 验证与故障定位

对一个漏答问题依次问：正文是否入库？查询词是什么？排名在截断前后哪里？上下文实际交付了吗？模型输入有完整段落吗？答案引用了哪个区间？原引用审核如何解释？实验指导书第60页正文旧排11，未进入前三及上下文，属于排名/交付缺口，不是生成看完后故意忽略。

不能把显式配置BM25写成“向量坏了自动回退”。ComponentFactory.initialize_retrieval在bm25模式直接返回；dense/hybrid调用VectorIndex.load，模型/profile/维数/知识/片段不匹配就抛ConfigurationError拒绝启动，不会静默改BM25。新快照没有匹配向量时，管理员可以明确配置BM25；这是一项配置选择，不是程序自动降级。构建/打开和逐命中校验仍保持。

## 面试与练习

面试说法：“我用SQLite保留原文与版本，倒排和向量只是检索派生。中文分词是显式方案，不把FTS5当中文能力保证。生成实际交付与原引用分别归档，可以区分库里有、检索到、模型读到和引用支持。”

练习：同一片段text不变但knowledge_version改变，Evidence是否可以不变？参考：片段内容可复用，但Evidence的快照归属与绑定需要新身份；不能拿旧缓存暗示新集合已完整验证。

## 缓存逐项核对：哪些已经实现

| 实际对象/函数 | 缓存键或范围 | 失效与仍执行的检查 |
|---|---|---|
| RetrievalSession.query_cache / retrieve | 同一run；knowledge_version、retriever.cache_identity、query、max_results、实际ContextOptions | 只在fact_query=True查询和写入；新run新字典，知识/模式/profile/查询/上下文变更另键；命中仍validate_result完整确定性重放 |
| retrieve_facts内deliveries | 单次逐组件审核；完整规范查询字符串 | 本次同查询复用Delivery；下一轮重新创建字典，组件映射/回答版本重新绑定 |
| KnowledgeStore._load_pdf_report | 只读连接局部；SQLite data_version/total_changes、知识、文档、版本、file_hash及缓存版本 | 外部提交改变stamp；可写Store禁用；返回deepcopy；容量达到8清空。不是排名/审核结论缓存 |
| corpus_index._OPENED / seal | 进程内路径＋knowledge_version；已验证文件size/mtime_ns | stamp变化拒绝；新进程严格sidecar/库内manifest与全文件SHA；字节一致复用发布时SQLite/FTS/成员检查，不在每题全库SHA；逐命中原文和区间继续校验 |

AsyncSQLiteBM25Retriever._work每次工作打开只读KnowledgeStore，所以PDF报告缓存不能跨这些新连接任意复用。aggregate普通检索不启用上述fact_query结果复用；不能把per_claim的优化写成默认aggregate行为。当前没有通用跨服务答案缓存或用缓存跳过必需审核。减少重放等其他优化只是建议，需要另行证据，未在本轮实现。

独立审核只判断实际交付；空命中/交付预算遗漏分别记录。“这个查询未找到”与“库内没有”不同，知识快照固定也不等于全量穷尽检查。

## 2026-10-08 当前行为核对

ordinary-chain-v2将明确概念问题/正文断言的语法主体补检前置到Generation与aggregate事实输入之前，保留首查询、排名、完整原文及身份。不是按模型结论选证；模糊或不支持语法跳过，per_claim不借aggregate证据。旧审核后合法不足补检独立保留。普通变压器完整定义实际交付后，36字回答完整审核通过，仅此已见开发例。

## 三道自测：先作答，再展开

### 自测1：dense索引不匹配是否自动BM25？

::: answer 展开参考答案1
不会；拒绝配置。BM25需显式选择。
:::

### 自测2：当前交付不足是否证明全库无资料？

::: answer 展开参考答案2
不能；查询/排名/预算都可能限制交付。
:::

### 自测3：query_cache是否跨服务？

::: answer 展开参考答案3
否；RetrievalSession每run新建，且只用于fact_query路径。
:::

## 2026-10-08 完整库接入核对

完整有效分片FTS已独立发布并接入日常，旧prefix历史保留。新进程仍读取约70.85GB做全文件SHA，sidecar与库内封印严格一致；字节一致时复用发布时结构/FTS/成员核验，未发布fixture仍直接检查SQL。进程内_OPENED只记路径/知识及size/mtime_ns，变化拒绝；没有跨进程跳过SHA的缓存。命中原文、字符区间、哈希仍验证。首启约52秒，后续正常重启43.5秒；未清OS缓存，不能称物理冷机或稳定SLA。四主题FTS查询0.11–4.76秒，命中不等于回答正确。唯一概念任务双审完整而业务待补充，知识接入与审核适用性问题分开。当前接入记录见项目源码目录的 `docs/full-corpus-adoption-v1.md`。

## 2026-10-09 第二版定向补记

第二版默认topic_v4_subject_v1：完整正向词项OR与每句主体OR相交，原BM25稳定score/rowid Top-K。每run有界8项数字排名复用只存rowid/score，绑定发布身份/版本/表达式/K；每请求仍重读正文/邻接/版本/定位，审核结论不缓存。命中不证明首次查询解决；v5保留可选，覆盖及排序退步未充分验证，不能切默认。完整库不重建、不原地修改。
