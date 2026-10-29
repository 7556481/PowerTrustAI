# Tantivy有界后端可行性 v1

状态：固定版本、语义专项及查询冻结完成，隔离样本正在建库/计时；不是生产发布。模型调用0。独立分支基于默认3cb0535，不把PR #4代码一并带入。PR #4/cc991a3保持：8链完整、一次正确修订闭环、中位省6.932秒但未过30%，40→50请求、501340→714844token，属于可复用但未产品入口验收资产，不启用。

## 比较条件

真实70,847,647,744字节、24,620,273片段。生产`corpus_fts`是单terms字段、contentless FTS5、默认unicode61；建库前使用jieba0.42.1、固定电力词典、HMM关闭，过滤为ASCII字母数字/中日韩汉字并casefold，不是rag/bm25.py的字符unigram/bigram参考实现。行业正文索引原片段文字；原文献native索引既有search_text（含原有标题增强）。两后端每份样本使用同一个预处理串，保存terms SHA256，不截断字段，不翻译或扩词。

生产topic_v4_subject_v1调用topic_lanes.plan，实际是宽OR与主体OR的AND，使用有引号词项、括号及显式AND/OR；来源名目前只是正文词项，不是按metadata做来源ID过滤。自然语言中的“不”等不自动变为Boolean NOT，这是原查询构造的边界，原问法和最终表达式都冻结。Tantivy将相同表达式解析为显式AST→Term/Phrase/Boolean，避免默认解析器差异；支持单terms字段及二元NOT，其他字段/NEAR/隐式AND等显式拒绝，不能静默改写。本轮12真实表达式均属支持子集。

Tantivy Python绑定及Rust核心均固定0.27.0（index format7），Windows abi3 wheel，不改生产依赖列表；单独requirements-tantivy-prototype.txt。Whitespace分析器不加lowercase、长词过滤或stemmer，因为源串已经是最终词项；保留词频和位置。8个合成全成员比对（含长词、短语、AND/OR、NOT、字段）及4个拒绝检查通过。

评分不能称等价。SQLite FTS5和Tantivy的k1=1.2、b=0.75虽相同，SQLite使用按短语的ln((N-df+0.5)/(df+0.5))并将非正IDF压到1e-6，结果负数；Tantivy采用正IDF、f32及有损fieldnorm。SQLite排序为score升序、原rowid升序、LIMIT3；Tantivy正常TopDocs按分数降序及内部DocAddress边界，不额外过取后筛成相同Top3，也不伪称全局同分等价。[SQLite公式](https://www.sqlite.org/fts5.html#the_bm25_function)、[Tantivy BM25源码](https://docs.rs/tantivy/0.27.0/src/tantivy/query/bm25.rs.html)、[固定绑定版本](https://pypi.org/project/tantivy/0.27.0/)。

## 资源和样本冻结

原库只读。派生数据在忽略data/retrieval_local/tantivy-bounded-v1，不复制项目、原库或独立来源全文。原片段ID、正文hash及terms hash映射保留，命中通过原有corpus_evidence/KnowledgeStore回查原文/来源/定位；邻接仍使用原来源链。

初始空闲内存约1GiB，进程RSS及private commit上限224MiB（低于可用量四分之一），writer16MB/1索引worker、单馈送线程、低优先级、最多2核。每1000份commit并排空merges后才下一writer，避免多批并行合并；native库可能拥有空闲维护线程，不声称OS总线程只有2。服务active或queued则在检查点正常停下，保存双索引进度。总派生/临时文件≤30GiB、剩余磁盘≥30GiB；保守整体4小时墙钟限制也覆盖建库累计上限，不清缓存。

固定嵌套前缀50k→250k→1m→最多4m，先50k因为内存边界；对正片段ID执行可逆仿射置换`id=((position*48271+12345)%24620273)+1`，与24,620,273互质，跨原全库分散选取，不挑答案邻近段。674份native原文献单列质量集，不混入随机样本。每份样本B/T完全相同成员、索引串与字段。

## 固定计时与门槛

12原查询：原selective MATCH档案Q1/Q2与上一轮S5/S8原verification查询为4慢宽查询；旧Q3/Q4/Q6/Q9为4正常类型，旧Q7/Q10为2文献类型，旧Q11/Q12为2低命中/不足类型。只复用原表达式，不重新做MATCH候选。冻结文件保存全文、来源run/retrieval ID、表达式、转换AST和目标。

每规模每查询每后端3次，交替B/T、T/B、B/T。记录第一次与后续，不清OS缓存，首次是建库后首次观测而非冷盘。正常TantivyTopK明确count=False；精确count另在三轮后各做一次并计时。只按同样本比较，70GB旧FTS耗时仅现实背景，不与小索引做倍率。先满足来源/语义有效、慢宽中位至少2倍趋势、无未解释关键质量损失和资源余量，才扩大。

结果、每次命中文本和资源峰值留忽略存储；正式计时不调权重或为单题增规则。后续补最终逐规模性能与质量复核。
