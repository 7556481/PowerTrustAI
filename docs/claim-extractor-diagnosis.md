# ClaimExtractor 契约失败诊断（离线）

检查对象：`data/retrieval_local/deepseek/evidence-review-q1.json` 及同名 Markdown。
本轮不读取真实 `.env`、不调用 API、不覆盖原结果。

## 能确认及不能还原的内容

原记录保留两次 `atomic-claims-v1` 请求的模型标识、耗时、token、finish=stop、
服务执行 succeeded 和结构校验 invalid_structure；没有两次原始响应正文。
Markdown 也只有请求元数据和原回答。extraction_output、verification_output 都为空。
因此无法重放历史响应，也无法确定历史失败是哪个字段、定位或限定词问题。
finish=stop 和请求成功仅说明服务正常返回，不说明响应通过应用契约。

以下是从代码确认的问题，不能冒充历史响应的具体失败根因：

1. v1 提示词写“prefer the whole sentence”，但定位器强制完整句段边界。
2. JSON/字段/定位的具体异常被 structured_request 丢弃，最终只有泛化异常。
3. 格式纠正包含原失败响应，但没有具体违反项；失败正文只在内存中存在。
4. Markdown 在核验未完成时提前退出，未显示 execution_issues。

## 修复

提示词升级 `atomic-claims-v2-exact-source`。明确必填字段、类型、数组上下限、
冻结回答 ID/整数版本、终止标点与完整句段要求，提供响应结构形状。
quote 是回答原文精确摘录；proposition 是规范化原子命题，不参与字符定位。
重复摘录必须用紧邻字面 prefix/suffix 消歧。不做模糊或空白/Unicode归一化。

ClaimExtractor 现在报告静态安全诊断，例如：

```json
{"stage":"claim_extraction","field_path":"$.claims[0].quote","constraint":"complete_sentence_or_paragraph_boundaries_required"}
```

缺字段、未知字段、字段类型、数组数量、回答绑定、原文不存在、重复歧义、词内边界、
限定词不在原文、重复主张、非主张重叠均有对应路径和约束。
JSON 语法错误记录行/列；重复键、非有限数字记录 JSON 阶段。
诊断不回显模型字段值、未知字段名、原文、凭据或任意异常消息。
共享结构化调用器的其他旧解析器暂使用安全泛化兜底，不声称已逐字段改造所有 Agent。

每次请求记录 validation_error，保留首次与纠正的不同错误。
单次格式纠正收到具体 validation_error 和原失败响应（作为不可信数据），
仍计入原预算，最多纠正一次；第二次失败向 Harness 传播具体安全诊断。
Markdown 无核验结果时也展示执行错误及请求校验诊断。

原 Claim/CitationBinding 契约、精确片段、版本绑定、证据真实性与引用完整性不放宽。
未覆盖文本继续显式记录为未审核，语义原子性与限定完整性仍需人工复核。
没有更改 Harness 调度、真实核验判断或旧项目。

本次未新增原始响应持久化：未来仍可通过安全诊断确定违反项，但不能逐字重放
未保存的响应。若以后需要逐字重放，应另设明确的本地私有响应归档策略，
避免把可能含敏感资料的模型正文自动写入通用运行日志。

## 离线回归

`tests/test_claim_diagnostics.py` 全部使用明确标记 synthetic_fixture 的模拟响应，
不是历史响应，也不是知识正确性验收集。覆盖中英文定位、改写与原文分离、
歧义、错误边界、版本、字段、限定词、重复主张、JSON错误、具体纠正反馈、
两次失败记录和失败 Markdown 的诊断保留。原测试继续验证预算与超时、
索引真实性、引用完整性以及局部审核状态。

在项目根目录运行（不会调用付费 API）：

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

原文件 SHA-256（验证前）：

| 文件 | SHA-256 |
| --- | --- |
| evidence-review-q1.json | 4640bcba523cefb3041cb4313106bbe7597a623f23e76c32b6709852aecf26da |
| evidence-review-q1.md | e0d48f51a9e12128f3ab2de75fe2d9dd5353b6a5babdb92494e3fd88c0638f27 |
| official-trial.json | 16209145a48f96352c3de011aa1a8cac579c7e2adcc60a1274f75ce764e699d0 |

验证结果：项目解释器 `D:\PowerTrustAI\.venv\Scripts\python.exe`，
全部 **142 项通过**（原 130 项 + 新增 12 项），30.051 秒，退出码 0。
通过工具允许的审批机制启动解释器；未安装依赖、重建环境或调整权限。
验证后三份文件的 SHA-256 与上表完全一致；旧项目 Git 工作区无变动。
本轮实际 API 请求为 0，没有新的付费 token 或真实核验结论。
