# 逐主张事实检索与证据交付 v1

2026-10-04；接续已推送bb0b208。默认仍为aggregate，同一BM25/固定知识/上下文规则、schema13、原引用分组、四Agent/Harness、SQLite与模型连接器继续复用。本轮实现了可选策略，不训练模型或调整排名/支持要求/最终政策。

## 查询与交付

`RetrievalSettings.fact_strategy` 接受 `aggregate` 或 `per_claim_v1`。后者根据冻结组件的basis_target选择真实核验对象：document_body/technical_content使用组件proposition及去重后的必要限定；不拼接整段回答，不让另一次模型改写主张。旧技术Claim无组件时有明确兼容回退；真实协议7有显式组件与目标。

index_metadata、input_snapshot、answer_text、recommendation、mathematical_relation保留原依据类型，不强制文献查询。未知目标记录classification_unresolved及执行缺口，不改分类规避检查；模型原有classification_issue与语义忠实度机制保留。其他依据只能使用当前实际可用输入/元数据/锚点/工具；没有可用资料不补造。

同快照、相同查询/结果数/上下文配置复用已经校验的结果。同一轮重复查询仅一次检索；跨修订版本可复用固定索引结果，但新retrieval_id、answer_id/version和映射重新建立，原映射不能当新版本依据。所有索引Evidence仍经原Retriever/KnowledgeStore回查，原文、哈希与定位不变。

逐对象保存 `FactRetrievalBinding`：回答版本、claim_id/component_id、category/basis_target、查询/方法版本、retrieval_id、核心命中、实际交付ID、邻接链接、具体省略原因及复用来源。每查询RetrievalRecord和整轮summary保留；去重后的证据仅一次进入当前独立审核请求。同Evidence可在多个对象显式交付，候选不能跨到未交付对象、旧回答版本或作用域外。v1不自动把其他查询的全部材料分配给每个对象；这会限制跨对象泛用材料，须人工查看。

| 状态 | 含义 |
|---|---|
| empty | 此查询成功但无正分命中；不是事实错误，不证明整个语料无依据 |
| hits | 索引回查与交付完成，仍需模型判断是否足够支持 |
| budget_exhausted + 仍有hits | 找到材料，但完整核心片段未能交付；不截断后放行 |
| failed/timed_out/cancelled | 检索执行问题，与事实矛盾分开 |
| 模型insufficient_evidence | 已收到允许材料，语义审核判断依据不足；不是查询失败 |

某条查询失败仍处理其他条目并保留其发现；失败对象要求not_assessable/空依据，执行问题进入报告，不能整体pass。共享文本在同一版本按唯一Evidence计交付额度；新版交付重新计费字符，索引缓存只减少检索调用。生成/领域检索仍使用原方法。真实调用记录与模型预算不按主张数扩大。

## 版本与运行

输入扩展为 `fact-evidence-delivery-v1`；新策略提示版本为原v9.5加 `-fact-delivery-v1`。输出仍为schema13/v9.5，同一个独立请求附FACT_EVIDENCE_DELIVERY及逐组件allowed_quote_ids，程序验证组成部分实际选中的依据。原引用请求无此映射，仍仅选各自原绑定Evidence；独立召回不能补救原引用不足。aggregate不附新映射，旧协议/归档按旧含义恢复；新观察字段缺失为None或空，不迁移历史结果。

```powershell
cd D:\PowerTrustAI
# 真实模式沿用既有服务端配置；提交会调用模型
$env:POWERTRUST_FACT_RETRIEVAL_STRATEGY='per_claim_v1'
$env:POWERTRUST_MAX_RETRIEVAL_CALLS='128'
& .\.venv\Scripts\python.exe -m backend --port 8765
# 停止后回到默认aggregate
Remove-Item Env:POWERTRUST_FACT_RETRIEVAL_STRATEGY
Remove-Item Env:POWERTRUST_MAX_RETRIEVAL_CALLS
```

服务端from_environment默认aggregate/12次检索；可选per_claim_v1默认128次本机检索，显式配置可以覆盖。旧12只适合少数整批检索，新预算为正常多组件及一次重审预留空间：例如62个独立查询×2版本+一次生成/两次领域=127，去重会减少；不是最坏成本证明或付费批次授权上限。字符、步骤/总超时、实际计数、有限纠正与一次Revision仍生效；超过容量/额度明确留执行缺口。直接代码构造ServiceConfig需显式提供相应budget，不能依赖环境工厂的调整。

manifest保存策略、输入合同、提示与全部预算。运行SQLite与API `retrieval`投影保存查询和绑定；页面“事实检索查询、逐主张交付与省略（详情）”使用安全文本JSON展示。API仍不接受客户端指定策略、数据库或本地路径。演示服务仍为synthetic_fixture，不能把其fake结果当真实新策略模型审核。

## 验证与复现

公开13项新回归：关键词竞争、去重、无命中、部分失败、容量省略、共享Evidence、错ID、版本隔离、原引用隔离、同级发现保留、固定对照驱动、SQLite与HTTP重启持久化。普通测试无付费请求：

最终本机完整468项/75.028秒全部通过；独立无原data/.env的公开检出13项新回归通过；页面脚本node --check通过。未把历史失败或未分发材料改为成功。

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_fact_retrieval_v1 -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

固定真实资料对照见[报告](per-claim-fact-comparison-v1.md)。本机已有获准知识索引和冻结案例时，可用公开驱动重复零模型比较：

```powershell
& .\.venv\Scripts\python.exe -m evaluation.fact_retrieval_comparison --index data/retrieval_local/semantic/corpus.sqlite3 --plan data/runtime_local/per-claim-fact-v1/comparison-frozen.json --cases data/runtime_local/per-claim-fact-v1/comparison-results.json --output data/runtime_local/per-claim-fact-v1/comparison-new.json
```

输出以独占创建，不能覆盖旧报告；官方全文及冻结真实资料不随Git分发。真实run `53613803b0a248819bf3d063ce41d5c8`：10模型/7检索、自然一次Revision、完整重提取双审核；初审独立审核一次格式纠正保留。无最终执行问题，必需阶段完整，review_required、工程前提未齐。223532 token，51.573秒，估算USD0.026815116–0.053630232（适配器价格快照区间、非账单）。逐组件/原引用范围与Evidence回查通过；重启结果相等、10→10无重发。未做新的浏览器交互验收，已实现同源详情并经HTTP/公开投影测试；本轮服务8766已停止。

原始请求/响应、冻结运行代码哈希、输入、逐主张证据链、用量、失败和最终提交/推送见忽略目录 `data/runtime_local/per-claim-fact-v1/`。未读出/归档密钥或请求头；未改旧30题与历史结果，不重建手册PDF，不开启下一实验。
