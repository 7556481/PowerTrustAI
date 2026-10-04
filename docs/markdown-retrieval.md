# Markdown → SQLite → BM25 → Evidence

后续文本型 PDF 扩展已复用此链路，见 [pdf-retrieval.md](pdf-retrieval.md)。下文记录第一批实现与验证结果。

实现与验证日期：2026-10-02。本轮仅验证程序行为；所有测试输入明确标记为 synthetic_fixture，不是官方资料或知识质量评测集。没有新增依赖；项目解释器为 D:\PowerTrustAI\.venv\Scripts\python.exe，Python 3.13.2。

## 修改文件与边界

| 文件 | 职责 |
| --- | --- |
| core/models.py | 增加可选 EvidenceProvenance；Evidence 原有位置参数仍有效 |
| rag/contracts.py | 复用 RetrievalRequest/Result/ Retriever；增加可选 hits，记录评分与排名 |
| rag/markdown.py | 保留原文的 Markdown 块切分、标题路径和层级、字符与行号定位 |
| rag/storage.py | SQLite 模式、事务入库、不可变版本与快照、Evidence 适配和回查 |
| rag/bm25.py | 确定性词项处理与 BM25 评分 |
| rag/retriever.py | 实现现有异步 Retriever 契约，四种 purpose 共享同一快照 |
| rag/cli.py | ingest、query、lookup、verify、latest 命令 |
| tests/test_retrieval.py | 14 项行为测试，含 CLI 往返及独立 BM25 计算 |
| tests/fixtures/retrieval_synthetic.md | 明确标记的合成 Markdown |
| .gitignore | 忽略 data/retrieval_local/ 的本地数据库和输出 |
| README.md、docs/python-architecture.md、docs/offline-harness.md | 补充本阶段运行入口及范围 |

Harness 调度、假 Agent、既有测试与旧项目代码不变。Retriever 返回的 evidence 元组符合既有 Agent 输入契约，可由调用方传入 TaskRequest.provided_evidence；本轮不自动改变 Harness 调度。Evidence 没有事实支持判断字段；检索分数只出现在 RetrievalResult.hits。

## 原文、定位及 Markdown 子集

- 使用 read_bytes() 计算原文件 SHA-256，再严格 UTF-8 解码。SQLite 同时保存原字节与完整 raw_text。拒绝无效 UTF-8 和 BOM，避免悄悄改变原文。
- 不统一换行、不 strip 原文、不渲染 Markdown。保留 CRLF、LF、CR（含混合换行）。仅这三种序列定义行边界；CRLF 算一次换行。
- 字符区间为 Python Unicode 字符零起始半开区间，不是字节或 UTF-16 偏移；行号为一基闭区间，包含实际文本行，行末换行包含在 raw_text 内。
- 识别 1–6 级 ATX 标题、Setext 标题、空行分隔的段落和围栏代码。保存标题名称路径及原始级别，允许跳级。标题行仍完整保存在文档原文，不单独产生片段；只有标题、没有内容的文件拒绝入库。
- 表格、公式和列表按原样保留在块中，不做结构语义分析。围栏内的空行和 `#` 不被当成段落/标题。未闭合围栏保留到文件末尾。
- search_text 单独保存：标题路径增强 + 内容，casefold + 空白归一化。raw_text 与 Evidence.text 都是原文切片。首版不做术语扩展或生成式改写。
- 不解析完整 CommonMark、HTML、front matter、引用块内标题或嵌套块结构；它们以普通文本保留。不对超长块进行长度裁剪。

## SQLite 与版本规则

documents 保存显式 document_id；versions 保存原字节、完整原文、原文件哈希和调用方提供的来源元数据；fragments 保存原文/检索文本、位置、标题及词项；snapshots 与 snapshot_documents 保存完整知识快照；settings 保存 schema、索引配置和 latest 指针。

document_version = SHA-256(原文件哈希 + 规范化来源元数据)。fragment_id 绑定文档 ID、文档版本、块序号与解析器版本。knowledge_version 为完整文档版本映射与索引配置的内容哈希。Evidence ID 绑定知识快照与片段 ID。因此相同片段在不同知识快照中的 Evidence ID 可以不同。

同一 ID、相同内容及元数据重复入库无新增记录；相同 ID 内容或元数据变化必须显式 --update。旧版本和旧快照不删除；恢复旧内容可以重新指向已有快照。不同 document_id 即使内容相同也作为不同来源保存，不做跨 ID 合并。来源、机构、出版日期、文档标题均仅来自显式输入，不从文件名或 Markdown 首标题推断；未知为 null。

入库在 BEGIN IMMEDIATE 事务中写入所有文档、片段、快照及 latest；失败整体回滚。索引配置包括解析器、分词器、评分参数、标题增强和扩展开关；遇到不兼容配置拒绝运行，不静默重建。首版无迁移/清理命令。只读 CLI 命令使用 SQLite mode=ro，不会因数据库路径写错而创建空库。

query 必须指定完整 knowledge_version；latest 只作为发现版本的便利命令，正式复现应保存查询返回的版本字符串。快照查询以完整快照片段计算语料统计。Evidence 回查验证快照成员哈希、原字节哈希、原文、文档版本、片段 ID、字符范围、行号、标题和词项；verify 还比较传入的完整 Evidence，篡改任意来源字段或原文会失败。

## 分词、评分和排序

分词版本：latin-alnum-cjk-unigram-bigram-v1。英文/数字串 casefold 后保留为词项，技术缩写如 STATCOM、PMU、MVAr 不设停用词；Q-V 等标点分隔为 q、v。汉字范围 U+3400–U+4DBF、U+4E00–U+9FFF 使用连续字串的一元字和相邻二元字；无外部中文词典。此方案提高基础中文命中能力，但容易出现单字噪声，不能声称专业术语分词已解决。

BM25：k1=1.5，b=0.75，idf(t)=ln(1+(N-df(t)+0.5)/(df(t)+0.5))；每项贡献为 idf × tf×(k1+1)/(tf+k1×(1-b+b×dl/avgdl))。dl 包括检索增强标题及中文一元/二元词项。查询重复词去重，不加入查询频次权重。无词项命中返回空 evidence/hits，不填充零分片段。

按分数降序，再按 document_id、document_version、块序号、fragment_id 稳定排序；目的不会改变首版打分。检索分数不是置信度、真实性或事实支持度。

## 从项目根目录运行

以下 PowerShell 命令工作目录为 D:\PowerTrustAI，不需要激活环境或安装依赖：

```powershell
$taskPython = 'D:\PowerTrustAI\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Path data/retrieval_local -Force | Out-Null

$taskIngest = & $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/demo.sqlite3 ingest tests/fixtures/retrieval_synthetic.md --document-id synthetic-voltage --source-type synthetic_fixture
if ($LASTEXITCODE -ne 0) { throw 'Ingestion failed' }
$taskIngest
$taskKnowledgeVersion = ($taskIngest | ConvertFrom-Json).knowledge_version

$taskOutput = & $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/demo.sqlite3 query STATCOM --knowledge-version $taskKnowledgeVersion --purpose verification
if ($LASTEXITCODE -ne 0) { throw 'Query failed' }
$taskOutput
$taskQuery = $taskOutput | ConvertFrom-Json

& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/demo.sqlite3 lookup $taskQuery.hits[0].fragment_id --knowledge-version $taskKnowledgeVersion

$taskQuery.evidence[0] | ConvertTo-Json -Depth 10 | Set-Content data/retrieval_local/evidence.json -Encoding utf8
& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/demo.sqlite3 verify data/retrieval_local/evidence.json

# 中文、空命中
& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/demo.sqlite3 query '无功支撑' --knowledge-version $taskKnowledgeVersion
& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/demo.sqlite3 query zzzzunmatched --knowledge-version $taskKnowledgeVersion

# 对同一文档显式更新（将路径替换为你准备的新 Markdown）
# & $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/demo.sqlite3 ingest path/to/updated.md --document-id synthetic-voltage --source-type synthetic_fixture --update
# 更新后仍可使用保存的 $taskKnowledgeVersion 查询旧快照。
```

可显式提供 --source-uri、--publisher、--publication-date、--document-title 及可重复的 --applicability。未提供的来源字段为 null。ingest 输出文档与知识版本；query 输出完整 Evidence 与排名、原始分数、评分方法和知识版本。正常空结果退出 0；输入、回查或 SQLite 错误退出 2，stderr 记录异常类型；执行异常不被包装成事实审核结论。

## 本次实际示例

合成文档入库 6 个片段，查询 STATCOM 返回 1 个结果：rank=1，score=2.5484983113686543，scoring_method=BM25-v1(k1=1.5,b=0.75,ln-positive-idf,unique-query-terms)。原文（结尾保留 LF）：

```text
STATCOM reactive support sample alpha. STATCOM supplies synthetic tokens.
```

- source_id：synthetic-voltage；source_type：synthetic_fixture；来源 URL、机构、出版日期、文档标题均 null。
- 定位 chars[213:287)，第 8 行；标题路径 synthetic_fixture → English control sample，级别 [1,2]。
- 原文件 SHA-256：854947ad95ef40cec4971bcae1a7d5f64329eb0e222ab45a57d72d9cf857d1f4。
- 文档版本：e7d991f276455713956703ed33a565ceebe2587fa7b9751149494e713f409d68。
- 知识版本：k-a9bfe2223127376b3e977f34f52f850551f244d979a5cc855adf41700abaf853。
- fragment_id：f-2361f3106777424693f38e9dc34f13d7b39ff64af9aeee2490219d6dfadf04e6。
- lookup 和 verify 均退出 0，lookup_valid=true，回查原文与查询 Evidence 完全一致。该标志仅表示存储回查正确，不代表事实成立。

本地示例数据库、query.json 和 evidence.json 在 data/retrieval_local/，不进入 Git。

## 测试与取舍

```powershell
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -X utf8 -B -m unittest discover -v
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -X utf8 -B -m harness.demo
```

2026-10-02 项目 .venv 在受限沙箱中 --version 启动失败，原始输出为 `Unable to create process using '"D:\PowerTrustAI\.venv\Scripts\python.exe" -B --version': ?????`。经工具审批提升执行权限后，同一解释器确认 Python 3.13.2，30 项 unittest 全通过（14 检索 + 16 Harness），退出 0，耗时 5.490 秒；Harness demo 七个场景完成，退出 0；CLI 入库、查询、lookup、verify 退出 0。没有修改权限或重建环境，没有以随附解释器替代验证。

测试包含：重复入库与重开数据库、显式更新与恢复旧版本、来源元数据更新、旧快照不变、CRLF/LF/CR 原文定位、中文/英文/缩写、标题和围栏、空命中、四种检索目的共用索引、稳定排序、BM25 独立手算、回查与篡改/跨快照拒绝、事务中途失败整体回滚、未知索引/版本与只读错误路径、CLI 往返。

标准库实现便于保持离线导入，但 SQLite 中存词项并在 Python 扫描完整快照，适合小型语料；不是可扩展倒排索引。回查重解析源文档，也有额外成本。async Retriever 当前执行同步 SQLite/评分，不能视为非阻塞服务或高并发实现；连接应由单一调用线程持有。

固定知识快照保证文档、词项及算法配置的可回查性；不提供防恶意修改数据库的数字签名或权限边界。首版无全文 Markdown 语法兼容、PDF/OCR、语义/混合检索、真实 Agent、网络接口或知识质量评测。

下一阶段建议先人工复核真实 Markdown 来源与片段边界，建立人工相关性标注；再用独立适配器接入 PDF 并保留页码。保持现有 Retriever 接口，随后可替换为倒排/混合后端；接入 Harness 时另行实现检索预算、执行问题及版本轨迹，不把评分当作事实审核。
