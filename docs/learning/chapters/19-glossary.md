# 19 术语词典：每个词对应哪个工程对象

## 阅读约定

词典用于回查，不替代前18章推导。每个词说明在本项目的具体含义和一个易混对象。遇到不同代码版本，优先manifest与源码；不要因为中文翻译相同而交换字段。

## 数据与依据

- TaskRequest：用户问题、模式和上下文组成的冻结任务。task_id是身份，不是问题文本摘要。
- AnswerDraft：某answer_id的一版实际回答，含正文和引用绑定。version变化必须独立审核，不是只改页面标题。
- Claim：从答案锚点提取的核验命题。它应忠实保留原意，不能为了得到supported改正确答案。
- Component：混合主张中的一个类型化义务。单个claim可包含正文、元数据和输入覆盖，依据不能混用。
- Proposition：规范化命题正文。规范化可以消除无关重复，但不能删除否定、数量、条件或立场。
- Assertion role：asserted/conditional/转述等立场，描述答案怎样表达命题。input_provided是义务，不自动等于input_report立场。
- Verification obligation：technical_truth、metadata_value、input_provided、answer_scope等核验责任。文字存在和事实为真不是同一义务。
- Evidence：实际可交付和回查的依据对象，包含正文、来源定位、适用性及provenance。相似度不属于事实证据。
- Provenance：文档/版本/片段/哈希/区间等来源轨迹。完整provenance证明可追溯，不证明出版物正确。
- Raw text：保留的原文权威。不能为优化搜索把它改成模型摘要。
- Search text：用于排序的派生搜索表示，可含标题/词项增强。它与Evidence原文分开，不能作为原文摘录回查。
- Locator：来源中的页、行、字符或分片/原行等位置。位置只有结合版本才有意义。
- 半开区间：文本[start:end]包含start不包含end，便于无重叠拼接。错误off-by-one会漏/多一个字符。
- Document version：原件和解析/派生相关的版本身份。不是按文件名修改日期猜“最新”。
- Knowledge version：某个固定文档版本集合。缓存和向量必须匹配它，不随库更新静默变化。
- Quote candidate：从允许Evidence产生的字面摘录候选。模型选择ID而非猜offset，不证明该摘录支持命题。
- Quote ID：当前候选scope中的身份。不是可以在所有运行全局借用的原文索引。
- Scope：一次审核对象允许的输入边界。原引用scope与独立审核scope不同，同文字也不自动跨借。
- Condition carrier：完整既有quote承载的来源条件候选。它不是程序已证明必要的最小条件片段。
- Typed basis：text_excerpt、metadata_reference、answer_text_reference、input_snapshot_reference、calculation_result_reference等明确类型依据。
- Original citation：答案原本引用的资料区间。独立找到其他资料不能使原引用自动正确。
- Delivery：这一步真正交付给该对象的Evidence。全运行池有材料不表示每个组件读过。
- Snapshot：冻结输入或结果视图，记录当时的内容与身份。现在补检索不能修改历史交付快照。

## 检索与索引

- Token：分词器产生的单元，英文词、中文字/双字或WordPiece均可能。字符数和token数不能直接互换。
- Tokenizer version：分词行为身份。文档和查询用不同处理会让索引可建但不可正确命中。
- Jieba/HMM：中文分词组件及未知词统计路径。本项目固定词典和HMM关闭，不训练分词模型。
- TF：词在某片段的频次。BM25通过饱和分式使用它，不是次数线性相加。
- DF：含该词的片段数，用于IDF。它取决于候选集合，知识变化会改变。
- IDF：稀有词贡献，项目小库采用正值对数形式。稀有不等于权威。
- BM25：基于TF/DF/长度的相关性排序。score不是支持概率。
- FTS5：SQLite全文倒排扩展。中文能力来自显式预分词，不是扩展名称本身。
- Posting：词到出现文档/位置的列表。倒排避免每题扫描全部原文，仍有候选和回查成本。
- Embedding：模型派生的向量表示。不能代替原文或修正出版错误。
- E5：当前可选多语言双塔编码器，query/passage前缀属于profile。
- Pooling：把token或窗口表示聚合为向量。平均与归一化次序影响结果。
- L2 normalization：向量除范数，使点积可等于余弦。零范数/非有限值需拒绝。
- Cosine：方向相似性；归一化后点积。0.96不表示96%真实。
- RRF：按排名倒数融合，缺失路无贡献。多路出现不等于多个独立证据证明。
- Cross-encoder：把查询与候选一起编码的排序/分类模型。不同于预计算每文档向量的双塔。
- Reranker：重排给定候选池；不能召回池外资料。
- Top-k：输出核心候选数量，与检索深度和上下文数量不同。
- Context：有界相邻片段；保持独立身份，不伪造核心排名。
- Candidate pool：固定可比较候选集合。扩大池会改变可召回上限，不能只将效果归给排序。
- Profile：模型revision、文件哈希、维数、精度、池化、窗口及编码处理的联合配置。

## 判断与执行

- Supported：给定对象由实际合法依据支持，不等于总体回答通过。
- Contradicted：有依据冲突；没有依据不是矛盾。
- Insufficient evidence：支持/反驳所需依据不够，可能可补资料，不机械触发Revision。
- Not assessable：对象不能有效评估或存在未解决分类/忠实性异议；不等于模型接口失败。
- Fidelity：提取对象对答案原文的忠实程度，和事实支持分开。
- Severity：发现影响严重度，与真假及最终处置分别记录。
- Disposition：通过/不通过/待补充/复核/执行未完成等业务处置。
- Resolution：当前问题完整、部分或无法回答，不用“合法JSON”代替。
- Harness：受控流程执行器，不是另一个无限自主模型。
- Observer：阶段事件的记录者，不发起新业务调用。
- Structured correction：一次有限输出格式纠正，修接口不等于修答案。
- Revision：针对审核发现生成新答案版本，需全重提取和双重审。
- Raw judgment：模型真实原始判断。有效派生可以更保守，但不得覆盖原判断。
- Effective judgment：程序根据合法异议、条件和责任计算的可用于处置状态。
- Deadline：剩余墙钟期限。达到期限不应再发新调用。
- ModelBudget：每运行实际请求资源账本，不由提示文本自报控制。
- ContextVar：协程上下文变量，用于阶段调用归属；并发任务共享run预算但有独立invocation。
- Drain：等待底层线程/模型工作安全结束再关闭或复用，不是强杀。

## 数据、训练与运维

- Pending/confirmed/hold：待审、用户授权确认和暂缓分流；confirmed非专家金标准。
- Parent lineage：任务变体父谱系。跨集合共享会产生开发泄漏。
- Family：通过概念、父关系、共享证据和近重复合并的关联组，不能按模型成绩拆分。
- Document holdout：另一文档留出，不参与训练、验证、选模型或checkpoint。
- Macro-F1：各类F1等权平均，需明确有效集合和类定义。
- False supported：误预测supported；4/23与4/14两个分母不同。
- Logits：分类头未归一原始分数，不是可信概率。
- Checkpoint：模型参数及配置的保存版本。best必须有事前选择规则与哈希。
- Seed：随机状态条件之一，不保证跨所有平台逐位复现。
- Parquet batch：流式读取小批列式数据，不把全库转Python列表。
- Internal row ID：缺原ID时固定revision/分片/绝对行号生成的明确内部身份，不冒充原出版ID。
- Exact dedup：正文SHA一致的精确去重，来源谱系仍保留。
- Transaction：数据与断点同成功/同回滚的原子写入单位。
- WAL：SQLite预写日志模式，帮助快照读取与单写者协调，不是多写者并行保证。
- Immutable publication：构建后封印并独立发布新文件，不能边改边作为固定快照服务。
- Local session：本机引导换取的HttpOnly会话；DeepSeek密钥仍服务端。
- Idempotency：相同提交不产生重复任务的服务端协议；当前页按钮锁不等于此能力。
