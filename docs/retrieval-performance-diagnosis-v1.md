# 离线检索诊断 v1（原请求参数缺失，未重放）

2026-10-08，基线 `c60ce582965dd2099e5411bae514daee6bad9762`，既有run `e141cf2b761949f8ba9a5848a75c5d6f`。首版冻结、模型/政策/查询/排名/索引/交付不改。新增可选内部计时，只在显式capture时保存内存统计，普通运行不写新诊断；未调用模型、重跑整题或改原run。Windows 11 / Python3.13.2 / i5-9300H / 原.venv及完整kc-c25c9521…知识库保持。

## 请求核对与测量表

已核对原运行库、事件及15个该run既有诊断JSON，包含事件detail、消息content及delivery记录内嵌JSON。查询、用途、知识身份与输出排名/分数/已交付Evidence都有原记录；scenario_id保存在原TaskRequest。但**原max_results与context_options未保存**，全部既有归档未找到这些参数。3条输出不证明请求数量为3，输出邻接正文也无法唯一反推出字符预算、数量、深度、跨页与顺序参数。

按用户“若原请求不完整，不补造”的条件：**原请求重放0次，计划4次首次＋最慢两条各2次重复均未执行**。不拿当前默认参数或问题内容推算原请求。以下只有历史单调计数器，所有新分段/波动/一致性结果均明确缺测，不称已做历史等价验证。

| 脱敏请求 | 用途 | 原总秒 | 原返回核心数 | 首次重放 | 重复两次 | 排名/分数/正文/定位/身份比较 |
|---|---|---:|---:|---|---|---|
| R1 / f7837fa3… | 生成原查询 | 25.490 | 3 | 未执行 | 未执行 | 未测 |
| R2 / ffcf4c1f… | 生成主体补检 | 0.364 | 3 | 未执行 | 未执行 | 未测 |
| R3 / b6e684e4… | 独立事实 | 49.283 | 3 | 未执行 | 未执行 | 未测 |
| R4 / 75ea7bae… | 领域 | 62.605 | 3 | 未执行 | 未执行 | 未测 |

R1—R4的查询准备、SQL执行/取回/排序、正文/Evidence构造、验证均未知，统计JSON中为null；没有任何重放的首次/重复缓存条件可报告。本轮未清系统缓存，未创建实际索引或完整项目/库/模型副本。原环境和历史OS缓存状态未受控。完整脱敏标识与查询SHA见[小型统计](retrieval-performance-diagnosis-v1-stats.json)，不附查询/正文或原始响应。

## 最小内部计时

`rag/timing.py`用perf_counter记录起止和父span，记录run/retrieval opaque ID、固定阶段名、状态、机械计数；不保存查询、原文、异常文字、凭据或请求头。线程提交只传递ContextVar计时上下文，仍是原单线程/原连接生命周期/原忙碌、取消、超时语义。

```text
retriever_wait（包括等待，包住worker，不重复相加）
  retriever_worker（含连接打开/关闭等其他开销）
    immutable_seal（已有不可变身份校验）
    corpus_retrieve
      query_prepare
        immutable_seal（嵌套，可能包含首次进程全字节校验）
      fts_execute_fetch_sort（原SQL执行+fetchall；MATCH/评分/排序合计）
      body_evidence_construct（含原有正文哈希/定位校验）
      adjacent_context（邻接读取及构造）
    result_validation（另一worker调用，证书比较/正文验证或完整重放）
      corpus_retrieve…（仅原有fallback时发生）
```

父span包含子span；不能把wait+worker+SQL或body内seal相加。验证标记区分certificate_hit、ranking_replay_attempted，并从验证子树实际SQL span数生成ranking_sql_calls/ranking_replayed，而非凭执行分支猜测。合成回归确认同一完整即时请求验证0次FTS重排；改变请求进入fallback并实际1次FTS，错误结果/文件变动仍拒绝。**这不是原run的真实内部计时证据**，无法反填缺失秒数。未新增历史请求数据或替换历史结果，也未重构查询算法/SQL。

## SQL、计划与索引

实际SQL保持：

```sql
SELECT rowid,bm25(corpus_fts) AS score FROM corpus_fts
WHERE corpus_fts MATCH ? ORDER BY score,rowid LIMIT ?
```

原查询文本只在内存生成原query_version对应表达式；EXPLAIN QUERY PLAN规划原SQL结构。缺失原数量时**明确绑定诊断LIMIT 0**，绝不称恢复的原请求或运行时计划；只做prepare/规划，没有执行MATCH或评分排序。四条计划均为 `SCAN corpus_fts VIRTUAL TABLE INDEX 0:M1` 和 `USE TEMP B-TREE FOR ORDER BY`。M1是FTS MATCH虚拟表访问约束，SCAN字样不能直接解释为全库正文扫描；临时B-tree表示排序步骤，不证明落盘、排序秒数或主要耗时。

低成本PRAGMA元数据：corpus_chunks有唯一fragment_id索引与corpus_chunk_record(record_id,start)；corpus_native.id是主键。未额外COUNT MATCH、FTS词表扫描、全库计数或EXPLAIN秒数推算。匹配规模未知，只知道原返回各3个核心结果。

## 137.742秒口径纠正

**137.742/151.643≈90.8%只是原RetrievalRecord累计耗时与后台Harness计数器的比值，不是测得的关键路径占比。** 原代码顺序await检索，4个独立record本身无同层并行相加；但其timer包含prepare/线程等待/执行/取回/验证/交付，不能改称FTS净秒数。

事件具有嵌套：retrieval_original_generation=25.503秒，retrieval_subject_generation=25.872秒从原查询前开始，retrieval_generation=25.885秒包住两次请求。将全部5个retrieval事件直接相加得到189.176秒，会重复计入生成部分。仅合并3个外层事件（生成25.885/事实49.303/领域62.613）UTC推导区间，约137.801秒，未观察到同层重叠；UTC对齐/毫秒截断/observer边界使其不是严格单调区间union或精确关键路径贡献。模型双审另有并行，不能与嵌套子阶段重复求和。

已证实：历史检索等待量大、三个外层检索顺序、统计事件确有嵌套；SQL结构包含MATCH约束和临时排序。推测：宽泛OR与评分/排序可能昂贵。未知：原SQL净耗时、正文/验证分别占比、实际证书路径秒数、重复波动/匹配规模、精确关键路径占比。不得据此宣布FTS排序已被单独测实。

## 优化建议与复现

1. 先完善实际请求参数留存，再使用新计时器做忠实离线重放。至少保存max_results及实际clamp后的ContextOptions，复用已有query/scenario/purpose/知识/请求ID，不额外复制正文。这是恢复可测性，优先级最高、低风险；本轮未补写原历史或发起新run。
2. 有分段证据后，研究保持完整结果/分数/稳定顺序的排序访问或数据布局，潜在收益较高；必须独立版同请求等价验证。旧rank游标曾更慢，不直接采纳。
3. 检索并行需独立连接、预算/取消/证书身份设计，还可能资源竞争，风险和收益不确定；当前不修改单线程。改变OR词集、分词、候选或证据范围会影响召回/审核，风险更高，不能借本轮缺测直接采用。

```powershell
# 只读历史/索引元数据及计划；不执行MATCH、不调用模型、不重放。
& .\.venv\Scripts\python.exe -m evaluation.retrieval_diagnosis --index data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3 --run-id e141cf2b761949f8ba9a5848a75c5d6f --output data/runtime_local/retrieval-performance-diagnosis-v1/stats.json
```

31项必要离线检查通过：计时身份/父子/元数据白名单、缺失请求不推断、重复区间合并、跨线程计时、结果保持、证书/fallback/篡改和原Harness预算/超时/取消/知识身份回归。只用小型合成库，不把合成计时当真实四请求结果。公开仅计时源码、仅读诊断脚本、测试、短报告/小统计和交接；原运行/诊断库不改，0新模型任务、0付费请求，无ZIP、新环境、下载、实际库/索引重建。
