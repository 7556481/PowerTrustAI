# v6：正文依据采用必选 quote_id

CLI `python -m harness.evidence_review_demo` 显式使用 `evidence-verification-output-v6`，当前提示词版本为 `evidence-verification-v6.2-required-quote-id`。v6.1 增补元数据合法路径反馈，v6.2 要求简洁理由以减少长响应截断；结构与支持约束未放宽。历史 v4/v5 按记录版本重放，历史失败不转换为成功；程序调用默认版本保留兼容行为。

## 模型与程序职责

正文依据仅允许 `{"type":"text_excerpt","quote_id":"输入候选 ID"}`。模型判断支持、冲突、证据不足或无法评估，并返回条件、理由和组成部分判断；程序从固定原文回填 Evidence ID、精确摘录及 Python 字符区间。未知 ID、错 Evidence、额外的 quote/evidence_id/偏移字段均严格拒绝，没有模糊匹配或静默丢字段。

其他类型依据仍使用严格的 metadata_reference、input_snapshot_reference、answer_text_reference 结构。技术结论不能仅凭元数据支持；历史输入快照缺失不能用后来检索补齐。无合适候选允许无正文依据并报告证据不足，不强迫选择。

独立检索与每条原引用都有单独的允许 ID 列表。原引用只能选择原绑定 Evidence 的候选，不能借用独立检索证据修复原引用。引用边界/覆盖问题与模型语义支持状态分别保留。

## 候选生成与回查

`services/quote_candidates.py` 的 `literal-quote-candidates-v1` 从输入原文生成候选，不改换行、标点或公式。每份 Evidence 首先保留完整片段，再按空行段落和至多 1200 字符的启发式窗口生成候选，每份最多 8 个。单个 PDF 排版换行不是段落边界。无安全词边界时保留完整片段，不修复文本。

候选 ID 绑定候选版本、Evidence ID、来源版本、整段内容哈希和区间。保存自身原文、区间、两侧约 320 字符上下文及质量告警；避免切断词时上下文长度可略增加。完整片段不受 1200 字符限制。上下文用于理解，不自动算作所选依据；条件在窗口之外时应另选候选或完整片段。

候选目录在审核请求之前写入 Git 忽略的本地诊断目录；请求记录保存目录路径，成功输出也保留目录。核心校验重新生成候选，检查目录、回填原文、版本与引用范围。失败的原始响应、全部校验错误、提示词/契约版本照常归档，格式纠正最多一次且计入四次/题预算。普通日志不整段打印回答资料。

## 验证边界

逐字一致只证明定位正确，不证明语义支持。测试包括未知 ID、范围错误、篡改、否定/因果原文保留、候选不足和纠正上限；还明确包含“合法候选但模型判断不支持原文”的结构合法案例，说明程序不会冒充语义裁判。

第 3 题 v5.2 两份真实响应按原契约离线重放仍失败（5/4 个校验错误）；直接套 v6 也因旧正文字段结构失败，没有自动迁移。新旧结构是否兼容与判断是否正确分别报告。所有真实审核只是 evidence_reviewed 局部阶段，没有真实领域审核或整体 pass。

## 运行示例

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe -m harness.evidence_review_demo `
  --input D:\PowerTrustAI\data\retrieval_local\deepseek\official-trial.json `
  --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 `
  --questions 3 --confirm-first `
  --first-review D:\PowerTrustAI\data\retrieval_local\deepseek\evidence-review-q1-fixed-v2.json `
  --output D:\PowerTrustAI\data\retrieval_local\deepseek\evidence-review-q3-v6-run1.json
```

该示例已经真实执行，不能原样重复覆盖。再次人工运行必须换新输出路径，并单独授权/计数。鉴权仅由现有程序加载环境配置，工具不读取或展示 .env。真实试运行结论与用量见本地 v6 汇总报告。

付费入口 `--max-output-tokens` 默认 10000，可显式设置 1..16000；响应字符上限相应调整，仍受既有单步/运行时限与最多四次/题预算约束。服务返回 length 作为执行失败保留，不能把截断 JSON 补全为成功。
