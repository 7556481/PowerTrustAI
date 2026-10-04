# 真实 Retriever 接入现有 Harness

本阶段验证真实文档检索、证据交付、固定知识版本、预算和失败处理。四个 Agent 仍是假实现；配置产生的 supported、contradicted、pass 都只服务于集成测试，不构成真实问答或电力审核能力。未安装依赖，未改旧项目、分词、BM25 参数或 PDF 切分。

## 接口与模块

| 文件 | 本轮职责 |
| --- | --- |
| `harness/runtime.py` | 在原 OfflineHarness 注入 Retriever；复用状态流和并行审核；检索结果交付、未完成检索放行守卫 |
| `harness/retrieval.py` | 每次运行的确定性查询、检索调用/字符预算和结构化检索记录；不是第二套调度器 |
| `harness/contracts.py` | 字符预算、检索配置、RetrievalRecord，以及失败时仍可读取的证据与总耗时 |
| `rag/retriever.py` | 原 BM25 算法保持不变；新增 AsyncSQLiteBM25Retriever 单线程适配及固定索引结果校验 |
| `rag/contracts.py` | 原 Retriever 新增 `validate_result(request, result)` 校验接口 |
| `core/models.py`、`core/validation.py` | EvidenceBinding、报告来源标记及预算/引用约束 |
| `agents/contracts.py` | 四类输入附加来源标记和固定知识版本，默认值兼容原调用 |
| `agents/fakes.py` | 保留默认离线行为；记录生成输入，增加可选引用输入证据的模拟配置，不分析证据内容 |
| `harness/retrieval_demo.py` | 本地官方索引 + 假 Agent，完整 JSON 轨迹及模拟标签 |
| `tests/test_harness_retrieval.py` | 真实 SQLite/BM25 与受控故障的集成测试，全部知识样例标为 synthetic_fixture |

`OfflineHarness(..., retriever=None)` 保持原离线路径。开启检索时通过 `run(request, budget, knowledge_version=固定值)` 显式指定版本；未提供版本是 InputError，发生在 Agent 执行之前。不在运行中读取 latest。未知快照/无法打开数据库属于检索执行失败，由结果记录，不伪造资料或快照。

新增校验接口是为了避免只信任 Retriever 返回的 provenance。真实适配器在指定快照重放确定性查询，比较完整 Evidence、排名、分数、上下文及其关联；原文回查也校验来源哈希和定位。检索与校验都计入同一个单步时间限制。调用预算按实际启动的逻辑检索请求计数，验证索引不是第二个用途检索，但会额外执行一次评分和索引读取。目前优先保证正确性，没有缓存优化。第三方适配器必须正确实现异步 `retrieve` 和可信索引上的 `validate_result`；不能以空校验器代替。

直接给 Harness 注入持有 SQLite 连接的旧 `BM25Retriever(store)` 会在构造时拒绝；该类继续用于原 CLI 和离线直接检索。Harness 应注入按数据库路径构造的 `AsyncSQLiteBM25Retriever`。

## 数据流和确定性查询

1. 问答模式根据问题执行 generation 检索，然后将用户参考及生成证据传给 Generation。审核已有回答模式跳过这一步。
2. 从冻结回答提取唯一共享主张列表。
3. verification 查询是所有共享主张原文按换行顺序连接；一次查询覆盖共享主张列表，本轮未实现逐条主张查询规划。
4. domain_review 查询按固定顺序连接问题、主张、scenario_id 和固定词串 `engineering prerequisites constraints operating limits applicability`。这些词串不代表识别了真实工程前提。
5. 两个检索顺序执行；随后两类审核 Agent 有界并行，收到同一不可变回答对象和同一共享主张元组，但各自只获得用户参考与对应目的检索的证据。
6. Revision 获得已保留的有效证据、来源标记和固定知识版本。修订后重新提取主张，重新执行 verification 和 domain_review，并完整重审；不新增独立 revision 检索。

每次查询记录 `deterministic-question-shared-claims-scenario-v1` 方法名、实际全文、回答版本、知识版本。没有模型、Planner 或查询缓存。

## 证据来源与交付

Evidence 原契约继续保留原文、文件哈希、文档/索引版本、独立片段 ID、定位、质量告警、来源类型和适用地区；不截断原文，不修改 PDF 提取文本。附加的 EvidenceBinding 使用以下标签：

- `user_reference`：用户提供。即使其自行提供 provenance，也不会自动被标记为已核实官方索引材料。
- `index_core_hit`：经过固定索引回查的核心检索命中。
- `index_adjacent_context`：经过同一索引校验的邻接片段，独立 ID 和原文，绑定核心 ID；不是额外评分命中。
- `agent_output_unverified`：Agent 自行返回且没有经过索引核实的材料，包括默认旧假审核器的 synthetic_fixture。

同一个 Evidence ID 的内容冲突会被拒绝。用户材料与索引命中 ID 相同也拒绝，不自动重标记；Agent 不可创造或修改索引 provenance。返回的索引原文、定位、快照和评分被篡改时，整个对应检索失败，另一方有效步骤继续保留。

排名与 BM25 分数只在检索记录中记录，没有转换为 VerificationStatus 或审核置信度。演示用现有 FakeEvidenceVerificationAgent 的可选 `reference_input_evidence=True`，将配置结论关联到收到的核心证据 ID；该关联没有进行支持匹配或事实判断，rationale 明确标记为模拟。

## 实际预算与失败语义

RunBudget 默认检索最多 12 次、单次交付 16000 字符、累计交付 64000 字符。相邻上下文计入字符预算。字符按 Python `len(raw_text)` 计算，保留换行；不是 token 数。每次交付计数，同一证据在不同用途/轮次再次传入也再次计数；结果报告按 ID 去重。用户参考不计入检索字符预算，没有新增用户输入大小限制。

先按排名选择能够整条容纳的核心证据，再选择上下文。核心超限整条省略、保留其余完整证据，并将该检索标为 `budget_exhausted`，阻止放行。上下文为可选，削减或省略上下文单独记录，可以保留核心完整检索成功；这不保证所有语义条件已补全。没有静默截断定位文本。

| 检索结果 | 记录/处理 |
| --- | --- |
| 成功有命中 | `succeeded/hits`；对应 Agent 可执行 |
| 成功无命中 | `succeeded/empty`，不是执行错误，也不代表主张为假；阻止最后完整放行，必要时返回证据不足 |
| 执行/校验失败 | `failed/failed`，对应 Agent 不运行，另一方仍可完成；需要人工审核 |
| 单步或总时限耗尽 | `timed_out/timed_out`，不能伪装成空命中；需要人工审核 |
| 调用或核心证据预算耗尽 | `failed/budget_exhausted`；保留已经核实的完整片段及有效审核；需要人工审核 |
| 用户取消 | `cancelled/cancelled`，保留既有有效证据、步骤和检索记录 |

生成必需检索失败时不执行假生成、不编造回答：report 可以为 null，HarnessResult 仍有证据、来源标记、轨迹及终止原因。审核检索失败时保留另一方结果；任何必需检索未完成都覆盖潜在 pass。成功空命中不会由 Harness 生成 contradicted；假 Agent 的结论仍由模拟配置产生。

TraceEvent 包含检索记录的 JSON 和输出证据 ID，HarnessResult.retrieval_records 同时提供结构化记录：用途、查询和方法、版本、核心/上下文 ID、排名及评分方法、执行状态、耗时、提供/接受字符数、累计字符数、已用调用数、整条省略 ID 和上下文遗漏原因。HarnessResult.duration_ms 记录运行耗时。完整历史回答/审核持久化和崩溃恢复仍未实现。

## 线程归属与超时限制

适配器只有一个工作线程，每次任务在该线程内创建、使用、关闭只读 KnowledgeStore 连接；不传递调用线程的 SQLite 连接，不关闭 SQLite 的线程检查。SQLite、BM25 以及来源重建验证均在该工作线程执行。

当前任务运行时拒绝新任务，不无限排队。超时/取消用 asyncio 停止等待，底层 Python/SQLite 工作不会被强制终止；适配器保持 busy，直到实际任务完成。后续检索可能因此记录执行失败。`close(wait=False)` 也不会杀掉运行线程，解释器退出仍可能等待工作结束。Agent 的超时也是合作式异步限制；没有进程隔离、CPU/memory 硬限制、SQLite 进度中断或工程生产控制能力。

## 从项目根目录运行

已有索引和固定派生版本可从此前三资料对比输出读取，无需重新下载或解析 PDF。原 PDF 和完整演示 JSON 留在 Git 忽略目录。

```powershell
$py = 'D:\PowerTrustAI\.venv\Scripts\python.exe'
$trial = Get-Content data/retrieval_local/pdf-quality/comparison.json -Raw -Encoding UTF8 | ConvertFrom-Json
$kv = $trial.documents[0].derived.knowledge_version
$db = 'data/retrieval_local/pdf-quality/nerc-reactive-planning-2016.sqlite3'

# 真实检索 + 模拟生成/审核；一次模拟修订并重审
& $py -X utf8 -m harness.retrieval_demo --db $db --knowledge-version $kv --revise-once --output data/retrieval_local/harness-integration/official-revision.json
# 审核已有的模拟回答：两种审核检索
& $py -X utf8 -m harness.retrieval_demo --db $db --knowledge-version $kv --mode assess_existing --output data/retrieval_local/harness-integration/official-assessment.json
# 预算耗尽后保留已完成证据及事实审核步骤
& $py -X utf8 -m harness.retrieval_demo --db $db --knowledge-version $kv --max-calls 2 --output data/retrieval_local/harness-integration/official-budget.json
# 生成检索为空；其他目的查询仍可能有命中
& $py -X utf8 -m harness.retrieval_demo --db $db --knowledge-version $kv --question qzxnohit --output data/retrieval_local/harness-integration/official-empty.json

& $py -m unittest discover -v
& $py -S -m unittest tests.test_harness tests.test_retrieval tests.test_pdf_chunks_context.PDFSplitterTests tests.test_harness_retrieval -v
& $py -S -m harness.demo
```

使用 `--output` 写入 UTF-8，输出路径限定为本地 `data/retrieval_local`，防止演示全文误写入可提交目录。Windows 控制台使用 `-X utf8`；若另外用 PowerShell 管道保存全文，还需按之前说明设置 UTF-8 的 Console/OutputEncoding。退出码 0 表示演示成功生成了结果，业务 decision 可以为 review_required 或 insufficient_evidence；CLI 参数/输入约束错误退出码 2。

## 实际官方资料演示

使用此前取得的 NERC Reliability Guideline: Reactive Power Planning，原文件 SHA-256 与来源清单和 Evidence 哈希一致：`1cefced2d010a84c7245885bc4c99df3bcc4f4bf47357d719a377794d5c3295f`。
固定知识版本：`k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55`。
生成查询：`Does a STATCOM's short overload capability count as reactive reserve?`。

| 顺序 | 用途 | 回答版本 | 交付字符 | 累计字符 |
| --- | --- | --- | ---: | ---: |
| 1 | generation | 尚未生成 | 4137 | 4137 |
| 2 | verification | 1 | 4137 | 8274 |
| 3 | domain_review | 1 | 5182 | 13456 |
| 4 | verification | 2 | 4137 | 17593 |
| 5 | domain_review | 2 | 5182 | 22775 |

生成首名为文件页 25、页内字符 `[1803:2479)`、片段 `f-589e47cf105b6cfb204d7a053a498671ccf4b2507739397c5c681ec2c4db13be`，BM25 分数 18.072850281148025。该次 3 条核心命中和 6 条补充上下文分别记录，Evidence 保留“持续时间”和排除短时过载的原始限定条件，但本轮没有事实支持审核。完整英文原文、实际三个用途查询和全部 Agent 输入在本地演示 JSON，不以模型摘要替代。

模拟修订最终 pass 只表示配置路径通过，不能用于真实知识能力验收。审核已有回答试运行执行 2 次检索；调用上限 2 的问答试运行记录 `hits,hits,budget_exhausted`，保留事实审核、9 个有效片段，返回 review_required；空命中演示记录 `empty,hits,hits`，返回 insufficient_evidence。空命中演示的模拟回答前缀本身也参与共享主张查询，说明确定性构造可能引入无关命中，不能据此评价知识质量。

## 已知限制与下一阶段

最终测试使用项目 `.venv\Scripts\python.exe`，Python 3.13.2，按工具审批机制处理沙箱启动限制，没有更改目录权限或重建环境：

- `unittest discover -q`：74 项全部通过，24.155 秒，退出码 0；保留原有 51 项，新增 23 项。
- 关闭 site-packages 的 `-S` 回归：56 项中 55 项通过、1 项可选 PDF 样例跳过，14.482 秒，退出码 0。
- 原 `harness.demo` 七个场景全部按预期完成，退出码 0。
- 四个官方索引演示命令均退出码 0，分别保存完整结果；这些退出码不是业务能力验收。

新增测试覆盖无检索器、问答/审核模式、三种目的、空命中、执行失败及返回的失败状态、单步/总超时、校验阶段超时、调用/字符预算、完整片段保留、核心/上下文质量标记、用户来源冲突、证据/定位/评分/知识版本篡改、数据库记录破坏、运行中索引更新、修订重检索、线程归属与真实线程取消限制、用户取消，以及演示 CLI 模拟标签。

没有真实模型、NLI/支持匹配、反证覆盖保证、工程工具和可信领域规则。批量主张查询可能被较长主张主导；固定工程词串可能引入噪声。补充上下文预算无法保证跨页条件完整。来源索引校验意味着与存储一致，不代表文档权威性、时效性或地区适用性已经被审核。

固定快照可防正常追加更新影响本次运行，不能防止数据库文件被外部破坏或旧快照被直接删除；这类情况失败并要求人工审核。工作线程超时无法硬取消，忙时拒绝会降低同一实例并发可用性。没有增加缓存、无限并发、自动重试或持久运行恢复。

下一阶段可先人工验证证据交付及必需限定条件，再实现真实 Agent 的支持/反证审查和领域约束；不要先以模拟 pass 作为可信问答准确率。
