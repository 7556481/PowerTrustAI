# 审核输出 v4：语义判断与确定性绑定分离

本轮离线读取第 2 题两份真实归档并重放，不调用 API、不读取真实 `.env`、
不覆盖历史报告或响应。历史提示词 `evidence-verification-v3-basis` 不变；
后续模型入口使用 `evidence-verification-v4-typed-evidence`。

## 历史错误与确认的不一致

`response-7f5ce9342b534dc6ac4891d2b3ec6dc2.json` 的全部 11 个 finding 缺
checked_dimensions；`response-f02fca79bd24484a9cc71be81aba9066.json` 的
findings[9] 缺 excerpts、scope_id。按 v3 离线重放仍然失败，历史状态仍为 review_required。

v3 提示词由 v2 示例加 v3 规则拼接，示例没有覆盖完整 v3 必填结构；
所有类型均要空占位字段，且报错只反馈第一个缺失。固定维度数组既增加输出负担，
又可能被误读为“已完成五项检查”。这些是确认的设计问题，但不是模型全部语义错误的证明。

## 哪些字段由谁决定

| 来源 | 字段 | 含义 |
| --- | --- | --- |
| 模型必须作出的判断 | claim_category、status、rationale、applicability_conditions、依据选择 | 不由程序补造；空条件列表只代表模型未列出条件，不代表普遍适用 |
| 模型选择已有目标 | claim_id、citation_index、Evidence ID、精确 quote、元数据 field_path | 必须指向输入；有歧义必须消歧，完整覆盖检查保留 |
| 程序从冻结输入确定 | answer_id/version、basis、scope_id、元数据实际值、字符偏移、原绑定 ID、交叠与边界问题 | 从输入准确计算/读取，记录为确定性绑定，不能当成新审核事实 |
| 程序固定展示 | 方法版本、required_dimensions | 表示要求检查哪些维度，不表示模型已检查 |
| 模型可选实际发现 | dimension_findings：dimension、observation | 有实质观察才报告；遗漏或 [] 表示未报告，不补成“完成” |

v4 输出的 checked_dimensions 为空；历史 v2/v3 字段保留用于历史回放展示，
标明 checklist，不作为完成证明。即使模型写了 observation，程序也只能验证记录合法，
不能证明检查确实执行或语义正确。模型不得把技术事实改归“建议”来免审，仍需人工核对分类。

## 一个模型响应的结构

顶层仅 `findings` 和 `citation_reviews`。finding 的必填键：
claim_id、claim_category、status、rationale、applicability_conditions、evidence。
可选 dimension_findings 仅用于 finding。原引用的必填键：
citation_index、status、rationale、applicability_conditions、evidence。
两类审核的 Evidence 白名单仍分开；原引用仅能用其本来绑定的 Evidence。

`evidence` 必须显式出现，按类型是 null 或一个分支对象；不让全部类型承担所有空字段。

| 类型 | supported / contradicted | insufficient_evidence / not_assessable |
| --- | --- | --- |
| technical_fact | `{"excerpts":[非空精确摘录]}` | 允许 `null`，也可列已有相关摘录但不代表支持 |
| source_quality_metadata | `{"metadata_refs":[非空字段引用]}` | 允许 `null`；不得附无关正文 |
| input_evidence_coverage | 完整生成输入快照必需；`{"excerpts":[]}` 可用于范围内缺失判断，或列范围内摘录 | 缺快照仅允许 not_assessable + null；有快照仍只能判断该输入集合 |
| answer_scope | `null`，对照被冻结回答本身 | `null` |
| review_recommendation | 不允许 definitive 事实结论 | not_assessable + null；事实前提仍须拆出 |
| 原引用检查 | 非空、精确、仅原绑定 ID 的摘录 | 允许 null，不借新证据清除原引用问题 |

元数据引用对象仅含 evidence_id、field_path，程序读取实际非空字段值并保存 canonical JSON。
正文摘录仍含 evidence_id、quote，可选紧邻字面 prefix/suffix；无模糊匹配。
每项依据数组不超过 16 个。完整输入的 hash/ID/版本、知识版本及现有真实性约束继续校验。
完整快照是判断有限输入的前提，不会自动证明模型的缺失判断正确，更不能变成“所有资料不存在”。

没有支持证据时不会生成支持摘录；没有模型理由、状态、条件或 evidence 字段时不会默认补齐。
内部统一 DTO 的空元数据数组/空摘录或空 scope，是已验证的分支投影，不是声称找到了支持。

## 提示词与解析器一致性

`agents/verification_contract_v4.py` 的 COMMON/CITATION/EVIDENCE_FIELDS 是分支定义，
提示词直接展示相同必填键，并生成 11 份完整形状示例。
测试为每份示例提供对应的虚构输入上下文，逐一实际解析，包括 []、null、支持、冲突、
元数据、完整输入存在/缺失、建议和原引用。示例不是本轮电力证据，不能复制 example ID。

v4 解析先逐对象收集可以独立检测的错误，再建立统一 DTO；缺依赖时不猜测其下游事实。
格式纠正收到 validation_errors 全部列表，validation_error 保留首条以兼容现有记录。
JSON 语法无法解析时只报告语法位置，不能伪装已检查内部字段。
同一对象的依赖约束、未知内部异常或 core 最终校验不保证全量可穷举；报告的是全部已检测错误。
历史 v3 增加结构预检，能一次列出 11 / 2 个实际遗漏，但不放宽任何旧要求。
模型请求仍最多初次+一次纠正，共用已有预算；没有 SDK 隐式重试或新 Agent。

## 兼容规则

历史 v2/v3 原始响应按显式历史 schema_version 解析，原状态/响应/提示词版本不变。
新 ModelEvidenceVerificationAgent 严格使用 v4，不尝试把历史输出静默升级。
直接把本次 v3 原响应交给 v4 也拒绝，因为模型输出的字段形状不同。
旧响应若要用于 v4 的开发样例，必须显式构造并标记为转换样例，不能计作历史真实请求成功。
原有测试中的模拟模型响应已显式更新协议；直接校验旧契约的测试仍保留旧形状。

## 文件与验证

| 文件 | 改动 |
| --- | --- |
| agents/verification_contract_v4.py | 分支契约、完整提示词示例、多错误解析与确定性 DTO 绑定 |
| agents/evidence_verification.py | 新入口强制 v4；历史 v2/v3 保留，增加全结构遗漏预检 |
| services/validation_diagnostics.py | 安全错误集合与独立捕获，不回显未知模型值 |
| services/structured_model.py | 格式纠正传递全部已检测错误，保存实际诊断列表 |
| core/models.py、validation.py | 要求维度与实际观察分开；继续检查类型、来源、摘录、范围、覆盖 |
| harness/evidence_review_demo.py | 分开展示 required_dimensions、observations、历史 checklist |
| evaluation/evidence_review_replay.py | 按归档提示词版本选择历史/新契约 |
| tests/test_verification_v4.py | 11 项新离线回归，包括真实 Q2 归档、所有示例、预算与批量错误 |
| tests/test_evidence_verification.py、test_verification_diagnostics.py | 明确升级模拟响应协议，保留原测试目的与断言 |

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

真实 Q2 归档回归是开发回归，不是独立知识验收集；没有重跑付费批次或新真实审核结论。

验证结果：项目解释器 `D:\PowerTrustAI\.venv\Scripts\python.exe`，全部 **176 项通过**
（原 165 项 + 新增 11 项），31.512 秒，退出码 0；真实归档测试实际运行，没有 skip。
原项目保持不变。通过工具审批启动解释器，未安装依赖、修改权限或重建环境。
本轮真实请求 0，新增真实 token/费用 0。

原记录的最终 SHA-256 与检查时一致：

| 文件 | SHA-256 |
| --- | --- |
| evidence-review-q2-q5-v1.json | 3865fcfc52ece89288766ea25e311939a3dc4d0b5ac6efd55bb6d489d2e030d0 |
| evidence-review-q2-q5-v1.md | b496622a681c8260a6c0e32e510b073383c9a874447cb83164d064b8eb12d762 |
| response-7f5ce9342b534dc6ac4891d2b3ec6dc2.json | 0ae1ae9ae0d61cec2bc092ab8623d798b0a288433b2477f4eb2fb4b022dfa0c3 |
| response-f02fca79bd24484a9cc71be81aba9066.json | aadd0cfa458e0a41ed041bbb43ad4fc27f4aeef4bec4385a928d266cd77f9d95 |
