# 主张提取与真实模型证据核验（局部阶段）

当前付费入口显式使用 v7 程序前提协议，详见
[power-domain-review.md](power-domain-review.md)；v6 必选候选摘录 ID 协议详见
[verification-output-v6.md](verification-output-v6.md)。以下阶段记录保留历史语境。
v5.2 统一类型依据与组成部分审核说明见
[verification-output-v5.md](verification-output-v5.md)。v2/v3/v4 的历史记录仍保留原契约与失败状态；
[verification-output-v4.md](verification-output-v4.md) 是上一阶段协议说明。固定维度列表不表示检查已完成。

归档 v2 的语义边界复查与 v3 分类依据/生成输入快照说明见
[q1-review-boundaries.md](q1-review-boundaries.md)。旧记录始终保留，v2 离线解析仅用于历史重放；
此处 v3 说明属于历史阶段；新的付费运行使用 v7.1 及显式组成部分提取，不自动升级历史响应。

审核器字段诊断与本地响应归档的后续修复见
[verification-contract-diagnosis.md](verification-contract-diagnosis.md)。

后续 q1 契约失败的离线诊断、v2 精确摘录提示词和逐字段错误修复见
[claim-extractor-diagnosis.md](claim-extractor-diagnosis.md)。历史响应未保存，
不能据此还原当时具体失败字段；本次修复没有重新运行付费核验。

## 本轮状态与范围

实现了模型驱动的 ClaimExtractor 服务及 Evidence Verification Agent，复用既有 DeepSeek 标准库连接器、ModelClient、Retriever 和 OfflineHarness；没有第五个 Agent、真实领域审核或 Revision Agent，没有工程仿真、BM25/分词/切分改动或新依赖。普通测试使用模拟响应，不调用付费 API。

已阅读原五问结果及人工对照报告，保留原始生成记录。原 JSON SHA-256 为 `16209145a48f96352c3de011aa1a8cac579c7e2adcc60a1274f75ce764e699d0`。离线预检五题保存的 Evidence 均与固定 SQLite 索引一致，原 JSON 未变，预检记录在 `data/retrieval_local/deepseek/evidence-review-preflight.json`。索引一致性不证明语义支持。

**本轮未读取真实 `.env`、未启动付费核验；新增真实核验调用为 0，真实核验 token/结论尚无。** 提供人工启动入口，先第 1 题，查看结果后再显式启动其余题。不能把原生成记录里的 6 次请求或 47,493 token 当成本轮审核用量，也不能把开发回归结果当成真实五问审核。

## 文件与兼容契约

| 文件 | 职责 |
| --- | --- |
| `services/text_location.py` | 原文精确定位、重复消歧、保守句段边界及旧引用告警 |
| `services/claim_extractor.py` | 主张提取服务、程序生成 ID、显式未覆盖与非主张范围 |
| `services/structured_model.py` | 初次结构化请求与最多一次格式纠正，共用实际预算 |
| `agents/generation.py` | 新提示词返回精确引用文字，程序生成既有 CitationBinding |
| `agents/evidence_verification.py` | 独立检索主张判断与原引用检查，两类结果分开记录 |
| `core/models.py`、`validation.py` | 兼容扩展原 Claim/VerificationFinding；新增原文摘录、覆盖范围及引用检查契约 |
| `agents/contracts.py` | 核验输入保留独立证据和原引用证据，输出请求记录及原引用判断 |
| `harness/runtime.py`、`contracts.py`、`states.py` | 原调度器增加 evidence_only 局部流程、模型提取预算及记录 |
| `rag/retriever.py`、`harness/retrieval.py` | 在线程所属连接回查保存证据；已验证的索引引用与用户材料分开标记 |
| `harness/evidence_review_demo.py` | 人工启动付费核验，读取旧回答、不再生成，逐题输出 JSON 和 Markdown |
| `tests/test_evidence_verification.py` | 定位、提取、判定结构及真实 SQLite/模拟模型集成验证 |
| `tests/test_harness_retrieval.py` | 保留原 50ms/200ms 慢验证检查，先准备真实检索结果再回放，隔离磁盘时序抖动 |
| `tests/fixtures/evidence_verification_development.json` | 明确标注的虚构开发回归案例，不是独立验收集 |

旧假提取器继续返回 Tuple[Claim, ...]；新服务返回 ClaimExtractionOutput，原 Harness 同时接受。Claim.text 仍必须等于回答的精确切片，proposition 是模型拆分的原子命题，不能当成原文；模型的命题改写、限定保留和完整性仍需要人工检查。既有数据类新增字段都有兼容默认值。

## 引用定位改进

旧提示词要求模型直接计数 Python 字符偏移。五问的数字偏移虽在合法范围，实际经常切在单词中间或挂到错误句子。全局 validate_answer 继续保留范围/ID 检查以便审核历史记录；不会偷偷修复原五问。

新生成提示词 `evidence-bound-generation-v2-exact-quotes` 要求引用对象为：

```json
{"quote":"Exact complete sentence from the returned answer.","evidence_ids":["input-evidence-id"]}
```

quote 必须精确存在于正文并覆盖完整句段。重复时可提供紧邻的字面 prefix/suffix；没有唯一匹配就拒绝，进入有预算的单次格式纠正，不选择第一个。不做大小写、空白、换行、Unicode 或标点归一化。程序用 Python Unicode 字符索引生成 CitationBinding，保留 ID/区间契约。英文、中文及 emoji 不用 UTF-16 或字节索引。

旧调用方的数字 JSON 结构仍可解析，但新输出中的词内或句中边界会拒绝；为兼容已有测试/调用，允许末尾排除句末标点。历史记录通过原契约加载后，只记录 boundary warnings，不改原数字。句段识别是保守标点/空段落规则，缩写、复杂公式、枚举等可能被拒绝或切错，不是通用语言分析器。

## 提取：一个服务，不增加 Agent

模型接收冻结 AnswerDraft（ID、版本、正文），返回 JSON 中的精确源句、原子 proposition、claim_type、原文 qualifiers，以及显式 non_claims。允许一个复合源句对应多个独立命题，每个命题应保留自身数量、否定、条件、因果、地区和 may/usually/some 等措辞。qualifiers 必须能在源 quote 中逐字找到。每题最多 32 个主张、64 个非主张范围；超出即失败，不静默丢弃。

程序负责定位源句并由回答 ID、版本、源区间和命题内容生成稳定 SHA-256 派生 ID。空提取、重复 ID、未知版本、改写的源 quote、歧义、非主张与主张重叠等拒绝。模型不输出主张 ID 或字符计数。

对未被任何主张源区间或显式非主张范围覆盖的非空白正文，程序生成 uncovered_spans（原文、区间、未审核原因）。non_claim_spans 也保留原文和模型分类原因，不称为已审核。提取失败保存执行错误和实际请求记录，不进入“空主张全部通过”。

**区间覆盖仅证明文字被用作锚点，不证明一个复合句的每个命题都被拆出，也不证明 proposition 没有遗漏限定。** 即使 uncovered_spans 为空，语义完整性仍未被机械验证；输出和报告持续标明这一点，不把剩余文字默认当成审核通过。

本轮 Claim 区间契约绑定 answer.text；assumptions 和 missing_information 原字段仍保留，但不单独提取其中的主张。结果警告和报告明确标记这两个字段未单独核验，不能把其内容默认当成事实已审核。

## 核验：独立材料与原引用分开

原 Harness 根据共享主张构造既有 deterministic 核验查询，使用同一冻结 knowledge_version 的 SQLite/BM25 索引。首版仍是每轮一个共享查询和有限 top-k/相邻上下文，不保证每条主张都命中；未增加 Planner、语义检索或调整 BM25。找不到相关材料可以是 insufficient_evidence，不能直接判 contradicted。

输入分为 INDEPENDENT_EVIDENCE 和 ORIGINAL_CITATION_EVIDENCE。原引用检查拿到原始 CitationBinding 实际指向的回答切片、原 ID、边界告警及重叠主张 ID，不替换为附近句子。模型分别返回：

- 每条主张一个独立判断：supported、contradicted、insufficient_evidence 或 not_assessable；保存主张 ID、证据 ID、原文摘录、理由、适用条件、数量/否定/因果/条件/地区五项检查及方法。
- 每条原引用一个检查：原 citation_index、重叠主张 ID（程序计算）、原绑定 ID、状态、摘录、理由、条件与边界告警。重叠不证明整条主张被引用覆盖；错误或部分引用仍需人工确认。

新检索 supported 不会覆盖原引用的 insufficient_evidence/contradicted/not_assessable。原引用判断只允许摘录其原绑定 ID，独立判断只允许摘录独立输入里的 ID；禁止“找到其他支持就把原引用改为正确”。保留核心命中、相邻补充、原索引引用、用户材料的角色/来源信息。

supported/contradicted 必须有匹配的证据摘录，另外两类允许空摘录。程序校验证据 ID、精确 quote、唯一位置及计算后的切片；Evidence 原文和 provenance 不修改。摘录是 Evidence 内相对字符区间，PDF 文件页区间由片段起点加相对起点计算，明确对应提取文本，不声称等于视觉原文。

“没有检索到”不等于“不存在”：对缺少相关文档通常证据不足；关于整个语料/世界不存在某资料或规则的绝对结论，不能仅用局部检索排空来评估，可标 not_assessable。跨地区、历史标准版本、数量矛盾及否定变化都需结合匹配条件判断，不把不相关北美材料当成中国规则，也不强行把地区不匹配判为反证。

精确引文匹配不是语义正确性的证明。模型可能照着可匹配文字作错判断；测试明确展示这一限制。五个 check_dimensions 字段只能证明记录完整，不证明模型真的逐项判断正确。工程完整可行性、动态仿真和 Power Domain Review 不属于本轮职责。

## 局部 Harness 状态与预算

仅审核已有回答使用 `evidence_only=True`：

```text
validated → 原索引证据回查 → extracting_claims
          → verification purpose 检索 → verifying → evidence_reviewed
```

失败分别保留 failed/review_required、执行错误、提取结果、有效证据及请求记录。局部成功仍为 report=null，没有 domain_review、revision 或整体 pass。覆盖缺口保留在局部结果中。混合模型核验与假领域审核的完整模式也加门控，不能产生整体真实 pass 或进入假修订来掩盖问题；原纯离线假模式保持兼容。

保存的官方 Evidence 必须先由 AsyncSQLiteBM25Retriever.validate_evidence 在线程所属只读连接中，按固定快照逐条与索引比对。通过后才标 index_saved_reference；普通用户材料保持 user_reference，不能靠自行填 provenance 冒充已核实资料。索引引用与重新检索命中可以使用同 ID，但两种角色独立记录。

人工入口预算固定为每题最多 **4 个实际模型请求**：提取 1 次 + 最多 1 次纠正，核验 1 次 + 最多 1 次纠正。请求通过原 ModelClient/Harness 共享计数，不额外计一个 Agent 槽，也不包含新的短连接测试。标准两轮（第 1 题、其余 4 题）上限为 4 + 16 = **20 次新请求**；没有失败自动重跑。正常各阶段一次则每题 2 次。超时/连接失败不自动重试；格式失败最多一次纠正。

每题最多 1 次核验检索；默认核心 top-3 加原有限相邻上下文，单次检索证据字符预算 16,000，累计 64,000；原保存材料超过 64,000 字符拒绝，不截断。模型单次等待 90 秒，输出上限 10,000 token，响应上限 96,000 字符；Harness 单步 200 秒、每题总时限 400 秒。字符/token 上限是不同的限制。

同步 HTTP 和 SQLite 都在既有受限单线程执行器工作；异步超时不能强制终止底层线程，已发请求可能收费且用量未知。CLI 在题目未达 evidence_reviewed 时停止后续批量，保留已完成记录。真正完成的费用/token 使用量按服务返回记录；未提供为 null，不是零。

## 人工付费运行：先一题，再其余

下面只提供命令，**本轮未执行**。用户在本机手动启动付费 CLI 后才会加载项目根目录 `.env`，读取凭据到客户端内存，不输出其内容；模块导入、普通测试及 --help 不加载真实 `.env`。模型 ID 沿用本机 DEEPSEEK_MODEL_ID，也可显式 --model-id。

从项目根目录运行第 1 题，不重新生成答案：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m harness.evidence_review_demo --questions 1 --output data/retrieval_local/deepseek/evidence-review-q1.json
```

查看同目录 `evidence-review-q1.md`：逐条核对原子主张、独立判断、原引用判断、摘录和文件页区间；即使 state=evidence_reviewed 也不等于判断正确。确认该输出可用后，人工显式启动：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m harness.evidence_review_demo --questions 2,3,4,5 --confirm-first --first-review data/retrieval_local/deepseek/evidence-review-q1.json --output data/retrieval_local/deepseek/evidence-review-q2-q5.json
```

其余题入口检查第一份结果确为同一原 JSON 哈希、第 1 题局部运行已完成，以及显式 --confirm-first；不会自动派发。--confirm-first 是用户确认已经检查输出，不是自动人工验收。输入默认是原 official-trial.json，DB 默认是已验证 NERC 索引，知识版本从原 JSON 固定。可指定 --input/--db，但仍要求保存五问且具有索引 provenance。

输出必须是被忽略的 data/retrieval_local 下的新 JSON 和同名新 Markdown；拒绝原输入路径及现存输出，避免覆盖历史或意外重复收费。失败修复后若用户主动重跑，应选择新文件名并理解其会产生新的调用与费用。只审核所选旧回答，保留原回答 ID/版本/偏移；运行结束重查原 JSON 哈希未改变。

报告包括逐条 Claim 原句及命题、数量等限定、判断和摘录、原绑定问题、未覆盖/非主张范围、固定知识版本、每次模型标识/耗时/用量/纠正/结束原因，以及实际调用数和独立成本估算。每轮逐题落盘，即便后面失败也保留前面有效结果。读取原数据和源文件质量告警仍需人工复核。

## 开发回归与验收边界

最终验证使用项目 `D:\PowerTrustAI\.venv\Scripts\python.exe`（Python 3.13.2），经工具允许的审批机制执行，没有重建环境或改变权限。完整 **130 项测试通过**（26.934 秒，退出码 0）：保留原 104 项，新增 26 项。人工 CLI 的 --help 也验证退出码 0，且不加载 `.env`。旧项目 Git 状态为空。

中间回归发现原 50ms 检索超时测试受真实磁盘/线程启动抖动影响：正常检索约 32–47ms，导致本来只应验证慢验证步骤的测试偶发在其他阶段超时。已在测试中先取得并验证真实 SQLite/BM25 结果，再按原请求回放；仍保留 50ms 预算、200ms 故意延迟和原断言，运行时没有缓存或预算放宽。稳定化后的专项及完整回归通过。

虚构开发集包含三/四类数量差异、新证据不掩盖原引用错误、北美/中国地区错配、未覆盖不等于不存在、正常电压充分性否定、以及有边界的不足说明。预置模型响应测试数据传递和记录，**不能称为独立验收集，也不能据此声称真实模型已检测这些错误**。

逐例模拟输出保存在 `data/retrieval_local/deepseek/evidence-development-results.json` 和同名 Markdown：6 次预置响应模拟请求、0 次付费请求，token 未提供。它们明确标注 SYNTHETIC_DEVELOPMENT，不是对真实五问的审核。虚构证据没有真实文件页码，不补造来源。

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_evidence_verification -v
& .\.venv\Scripts\python.exe -X utf8 -m unittest discover -q
```

验证包括：中英文/emoji 程序偏移、重复句段消歧、词内/句中边界、共享源句原子命题/限定/ID、覆盖缺口与非主张、错误版本/引用/摘录、四类状态、原/新证据隔离、超时、纠正上限和预算、资料/回答指令注入消息边界、伪造摘录偏移、固定版本中途更新、索引证据篡改前置拒绝、空检索和检索预算失败、局部状态门控、人工两轮入口及原记录哈希保持。

实测真实核验质量尚待人工启动及复核。尤其关注：原子拆分是否遗漏限定、原引用错配是否仍被模型误判 supported、正常电压问题的反向过度推论、NERC 历史版本是否误当中国当前要求、PDF 乱码/跨页上下文和可能未提取命题。没有可靠自动事实真值评估或完整工程审核。
