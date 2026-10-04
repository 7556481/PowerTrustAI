# 已实现 BM25、Dense 和 RRF 混合检索，保留原 BM25、闭环基线与审核协议。

2026-10-04当前接入状态：[真实服务可选语义检索v1](semantic-service-v1.md)已完成三模式服务器配置、资源生命周期、公开回归及单次真实HTTP验证；BM25仍默认。下文309项/旧30查询等是当时历史记录，不代表当前测试或装配状态，未重标/覆盖历史对照。

- 模型：multilingual-e5-small，MIT，384 维，CPU ONNX；模型与分词器约 487 MB。
- 三份官方资料共 **424 个片段**，使用固定知识快照，搜索前限定版本并检查索引完整性。
- **309 项测试全部通过**；项目 `.venv` Python 3.13.2。原基线 126 个文件哈希未变。
- 30 条查询完成三方法对照，耗时约 125 秒，峰值内存约 1.11 GiB；付费 API 调用 **0 次**。

结果有改善，也有退步：中文 QV 局限问题找到更直接的正文；中文正常电压问题却命中链接脚注，混合检索还把部分有效正文挤出前五位。**尚无人工确认标签，因此未计算真实 Hit@5、Recall@5、MRR@5，也不宣称整体质量提升。**

交付文件：

- [实现说明、文件职责与完整运行命令](D:/PowerTrustAI/docs/semantic-retrieval.md)
- [三方法对照报告](D:/PowerTrustAI/data/retrieval_local/semantic/comparison-v2.md)
- [18 个候选的原文与建议标签表](D:/PowerTrustAI/data/retrieval_local/semantic/annotation-candidates-v1.md)：全部待人工标注
- [中文查询与 Evidence 回查示例](D:/PowerTrustAI/data/retrieval_local/semantic/query-zh-v1.json)
- [版本及验证记录](D:/PowerTrustAI/data/retrieval_local/semantic/verification-v1.json)

从根目录重新运行对照：

```powershell
$run = Get-Date -Format 'yyyyMMdd-HHmmss'
& D:\PowerTrustAI\.venv\Scripts\python.exe -m evaluation.semantic_trial compare `
  --db data/retrieval_local/semantic/corpus.sqlite3 `
  --vectors data/retrieval_local/semantic/vectors.sqlite3 `
  --dataset data/retrieval_local/semantic/dataset-v1.json `
  --output "data/retrieval_local/semantic/comparison-$run.json"
```

下一步应先人工确认相关片段、限定条件及地区范围，再据标签比较方法；当前仍存在目录、页眉、脚注干扰及跨片段条件不完整的问题。
