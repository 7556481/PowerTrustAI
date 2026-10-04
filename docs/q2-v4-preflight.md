# 第 2 题输出契约 v4：真实验证准备

准备日期：2026-10-03。本次只进行了离线检查，未读取真实 `.env`，未调用 API。
未创建 `evidence-review-q2-v4.json` 或对应 Markdown；这些文件由用户执行真实命令后产生。

## 已确认的入口与记录

`harness.evidence_review_demo` 使用 `ModelEvidenceVerificationAgent`，运行路径明确调用
`parse_verification(..., schema_version=4)`，没有历史协议的自动回退。

新结果 JSON 明确保存：

- `verification_contract_version`: `evidence-verification-output-v4`
- `verification_schema_version`: `4`
- `verification_prompt_version`: `evidence-verification-v4-typed-evidence`
- `claim_extraction_prompt_version`: `atomic-claims-v3-category-hints`

每次审核调用的记录及私有响应归档另存 `response_contract_version` 与 `prompt_version`，
包括审核格式纠正；连接失败的调用记录也保留契约版本。
归档的 `schema_version=1` 是归档封装版本，不能解释为审核响应契约版本。
未改写历史记录或为历史记录补填版本。

## 第 2 题离线输入核对

问题：What limitations does QV analysis have for identifying wide-area voltage stability problems?

读取原始五问记录并验证回答及引用约束；第 2 题的 6 条原始 Evidence 均通过固定 SQLite
知识版本回查。原文件 SHA-256：
`16209145a48f96352c3de011aa1a8cac579c7e2adcc60a1274f75ce764e699d0`。

固定知识版本：
`k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55`。

已有第 1 题 `evidence-review-q1-fixed-v2.json` 的状态为 `evidence_reviewed`，
输入哈希一致，已实际通过 `validate_selection((2,), ..., first_review, True)`。
该门槛认可同一批原始回答的成功局部审核记录，不要求第 1 题重跑 v4；
`--confirm-first` 表示用户确认已检查第 1 题，不能解释为总体工程审核通过。

用第 2 题归档的提取响应离线还原 11 个主张，再使用明确标记的 `synthetic_fixture`
无判断响应检查当前审核输入构造。该模拟检查不是新的真实审核结果。
审核响应只要求模型返回语义判断、主张类别、理由、条件、证据选择及可选实际发现。
回答 ID/版本、偏移、判断依据类别、完整输入快照绑定、元数据实际值和检查方法由程序绑定，
不得要求模型重复生成。主张 ID 和原引用索引仍需要模型选择已有标识，以映射其判断。
主张提取服务仍使用其原有契约，要求复制回答 ID/版本；审核 v4 的改动不扩展到提取协议。

原生成记录未保存可验证的完整生成输入快照，因此 `GENERATION_INPUT_SNAPSHOT=null`。
不能从当前检索结果补造历史完整输入集合；输入覆盖判断没有该快照时只能无法评估。
原引用只能使用其原本绑定证据，独立检索证据不能替代原引用依据。

## 用户手动执行命令

下面命令只运行第 2 题，不生成新的回答。模型 ID 使用已配置的 `DEEPSEEK_MODEL_ID`；
用户执行时入口会加载项目根目录 `.env`，已有环境变量优先。
准备过程未检查密钥或模型环境配置，配置缺失时入口在模型请求前报错。

```powershell
Set-Location D:\PowerTrustAI
& D:\PowerTrustAI\.venv\Scripts\python.exe -m harness.evidence_review_demo `
  --input D:\PowerTrustAI\data\retrieval_local\deepseek\official-trial.json `
  --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 `
  --questions 2 `
  --confirm-first `
  --first-review D:\PowerTrustAI\data\retrieval_local\deepseek\evidence-review-q1-fixed-v2.json `
  --output D:\PowerTrustAI\data\retrieval_local\deepseek\evidence-review-q2-v4.json
```

本次核对时新 JSON 和同名 `.md` 均不存在。入口拒绝覆盖已有输出或报告。
即使失败也不要自动重试；先检查新记录与响应归档，再决定后续操作。

## 调用与诊断上限

- 一次初始主张提取，最多一次格式纠正；成功后才进行独立检索与审核。
- 一次初始审核，最多一次格式纠正；总模型调用预算为 4。
- 格式纠正同样计入预算；连接器每次调用只发一次 POST，无隐式重试、连接测试或额外题目。
- 单次模型超时 90 秒，Harness 单步 200 秒，总运行 400 秒；检索调用上限 1。
- 单次输出上限 10,000 token，响应正文上限 96,000 字符。
- `response-diagnostics` 位于 Git 忽略目录，保存成功接收的结构化响应正文、提示词和契约版本、
  响应 SHA-256，以及具体校验错误；不保存凭据、请求头或请求配置。
- 纠正收到所有已检测错误（含阶段、字段路径、约束），不只第一个；不能保证一个严重结构错误
  后仍能检测所有依赖它的错误。网络失败没有响应正文；适配层提前拒绝的截断/超长响应也不保证归档。
- 正文不在普通日志整段打印。报告仍保留局部失败、已完成步骤和调用记录。

成功状态仅为 `evidence_reviewed`；模型语义判断仍待人工复核，领域审核未运行，禁止表述为整体真实审核 pass。
失败可能为 `review_required` / `failed`，入口返回非零退出码并停止，不自动重复付费试验。

## 离线验证结果

项目解释器：`D:\PowerTrustAI\.venv\Scripts\python.exe`。
针对性测试 50 项通过；全部回归 177 项通过（22.141 秒），没有真实 API 请求。
新增检查覆盖契约版本的结果记录、初次与纠正响应归档、连接失败记录，及已有第 2 题归档驱动的
当前输入构造。历史两份审核响应仍按历史 v3 契约记录为失败，未转换成成功。
