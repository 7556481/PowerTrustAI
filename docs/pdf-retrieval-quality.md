# PDF 页内切分与相邻上下文：开发对比记录

本轮只验证检索程序和可追溯定位。Harness、假 Agent、旧项目均未修改；未安装新依赖。项目解释器为 `.venv\Scripts\python.exe`，Python 3.13.2；可选 PDF 解析依赖仍为 pypdf 6.10.0。启动通过工具审批处理沙箱限制，未重建环境或更改权限。

## 实现文件与版本

- `rag/pdf_chunks.py`：`pdf-paragraphs-v2` 页内切分，默认最长 1200 字符。仅连续空白行作为候选段落边界，单个排版换行不作为段落。无可靠边界、疑似双栏/表格、顺序或字符映射风险时回退到有界窗口，并记录方法与质量标记。超长段落同样有界切分；不插入或修复字符，不拆 CRLF。
- `rag/storage.py`：新增派生版本和切分详情表。`derive_pdf` 从固定快照中保存的提取文本派生，不重新解析；保存切分配置、计划哈希、页内半开字符区间、相邻 ID。原文件哈希、逐页提取文本与解析器版本不变。旧版本及快照继续可查；入库和派生失败回滚。
- `core/models.py`：Evidence provenance 增加可选切分版本、方法与标记，旧契约默认值兼容。
- `rag/contracts.py`、`rag/context.py`：可选相邻上下文，保留每条独立 Evidence 和核心片段链接，标记 `adjacent_context_not_retrieval_hit`。不加检索分数，不合并原文，不解释为事实支持。
- `rag/retriever.py`、`rag/cli.py`：核心 BM25 排名确定后读取上下文；提供派生、查询、独立上下文与回查命令。
- `evaluation/pdf_quality_trial.py`：核对来源清单/文件哈希，三份文档分别建库，输出固定源版本的前后对比和逐页复核清单。
- `tests/test_pdf_chunks_context.py`：11 项新增测试，覆盖定位、回退、跨页邻接、限长、去重、旧版本、幂等、回滚、篡改检查及 CLI。

上下文默认关闭；开启后默认最多 2400 原文字符、6 个片段、邻接深度 1，深度可配置为 0–4。对比试运行采用深度 2。按距离、核心排名和前后方向稳定选择，排除所有核心片段，重复邻居合并链接；超预算整条跳过并记录原因，不截断 Evidence。可以跨页读取上一页末尾或下一页开头，也可要求同页。机械相邻关系不保证语义完整，预算可能遗漏条件。

历史 `pdf_report` 内的 `chunking=one-fragment-per-text-page-v1` 描述原始提取版本，继续保留以保证历史一致性；实际新切分配置单独保存在 `pdf_derivations` 并暴露于新 Evidence。当前支持旧页级和 v2 回查；将来升级切分器必须继续保留 v2 重建逻辑，不能只替换版本常量。

## 实际文件和试运行

来源与哈希见 `docs/knowledge-sources/manifest.json`，本轮核对全部实际文件，没有新下载。

| 官方资料 | 文件页数/旧片段 | 新片段 | 查询数 | 回退窗口数 |
| --- | ---: | ---: | ---: | ---: |
| NERC Reactive Power Planning Guideline | 57 | 268 | 14 | 57 |
| NERC VAR-001-5 | 16 | 40 | 10 | 16 |
| PNNL-35221 | 54 | 116 | 8 | 110 |

AEMO 此前 HTTP 403，来源清单没有成功文件和哈希，本轮未使用。三份文件均有提取文本，但仍标为待复核；PNNL 大部分片段是回退窗口，不能称为恢复了可靠段落。

每份文档分别检索，相同原文件/提取文本、BM25 参数和查询文本固定；查询集哈希、两个知识版本均写入结果。包括原有查询和自然提问。改变片段集合会改变 N、df、平均长度，因此即使参数固定，前后分数也不能直接作为质量增幅；不同文档分数亦不可直接比较。未计算模型自行判定的准确率。

完整 32 个查询的前三名、ID、原文、定位、分数、补充上下文和遗漏原因保存在本机：

- `data/retrieval_local/pdf-quality/comparison.json`：完整机器可读结果。
- `data/retrieval_local/pdf-quality/comparison.md`：排名定位对照。
- `data/retrieval_local/pdf-quality/manual-review.json`：127 页逐页问题、提取原文和片段区间。

所有 424 个派生片段及输出核心/上下文均自动核对 `page.raw_text[start:end] == evidence.text`。字符区间针对提取文本，不代表视觉原文。原 PDF、数据库、提取全文和视觉抽查图片留在被 Git 忽略的本地目录；公开可下载不等于可公开再分发。

## 观察结果和失败案例

下表为首名的文件页和页内字符区间；分数分别来自各自片段集合，仅记录运行结果。原文和全部 ID 请回查完整 JSON。

| 文档/查询 | 页级首名/分数 | 新首名/分数 | 待复核问题 |
| --- | --- | --- | --- |
| NERC: dynamic reactive reserve STATCOM overload sustained maximum output | 25 / 18.180021 | 25:1803–2479 / 28.156824 | 保留持续输出及短时过载排除条件；需视觉核对 |
| NERC: QV analysis may not reveal wide-area voltage stability problems | 22 / 19.992281 | 22:1197–2396 / 22.348726 | 包含否定及预选节点条件，但窗口起止不一定完整段落 |
| NERC: synchronous generator capability stator field current excitation limiters | 9 / 14.844157 | 8:2381–3363 / 20.361968 | 页 8 末尾 “The generator” 在页 9 继续，必须检查独立邻接片段 |
| NERC: voltage stability | 48 / 2.053486 | 47:1937–2252 / 4.080651 | 仍为地区案例，未成为通用定义首名 |
| NERC: What is voltage stability and how is instability assessed? | 23 / 6.031310 | 50:1555–2084 / 11.433155 | Southern Company 标准的适用范围标题在核心片段之外 |
| NERC: What limits a generator's ability to supply reactive power? | 7 / 6.442928 | 7:2398–3166 / 9.417670 | 自然问题没有优先命中页 8–9 条件，上下文也受预算限制 |
| VAR: How quickly must a voltage schedule be supplied when requested? | 16 / 10.144709 | 16:2395–2838 / 11.143969 | 命中 R6 rationale，未优先命中页 2 规范 R1；明确失败案例 |
| PNNL: What is voltage instability? | 23 / 7.252533 | 23:1200–2399 / 7.527742 | 新核心是后续讨论，定义在前一窗口，需要独立上下文 |
| PNNL: How do PMUs help detect a lack of reactive power support? | 18 / 6.102568 | 29:1197–1905 / 7.569609 | 命中小信号特征值公式，偏离电压监测主题；明确失败案例 |

NERC “How long must maximum reactive output be sustainable?” 首名由页 45 转到页 25，但这只是排名观察。`synchrophasor` 仍为空结果。勘误查询新排序中页 57 的短标题排在原页 11 图说明之前，短片段可能产生噪声；勘误和正文各保留定位，没有自动修改正文。VAR 自然问题也可能混淆规范、解释章节和 WECC 地区条款。PNNL reactive margin 的自然问题优先命中工具分类，RPM 输入数据段并非首名。

## 人工复核清单和视觉抽查

本轮开发者视觉抽查：NERC 页 47、50；VAR 页 2、3、10、13、16；PNNL 页 23、24、25、29。抽查发现地区标题/规范层级可落在窗口外，版本历史表失去行列关联，PNNL 图形与公式不能由文本检索恢复。开发者抽查不是人工标注验收；清单全部保持 `pending_human_review`。

重点人工核对：NERC 页 8–9（能力和跨页条件）、21–23（QV/PV 及局限）、25（持续时间和否定）、27/34/42（表格）、47/50（地区适用范围）、57 与 11（勘误/正文）；VAR 页 2–3（R1/R2/R5 条件）、6–10（WECC）、11–12（VSL 表）、13–14（版本表）、15–16（rationale）；PNNL 页 23–26（定义、长期范围、FIDVR、图表）、29（公式和主题错配）。清单逐页提供提取原文、ID、字符区间和需要视觉核对的问题；自动一致性通过不证明提取顺序或事实正确。

## 从项目根目录运行

```powershell
$py = 'D:\PowerTrustAI\.venv\Scripts\python.exe'
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
& $py -m unittest discover -v
& $py -S -m unittest tests.test_harness tests.test_retrieval tests.test_pdf_chunks_context.PDFSplitterTests -v
& $py -S -m harness.demo
& $py -m evaluation.pdf_quality_trial

$trial = Get-Content data/retrieval_local/pdf-quality/comparison.json -Raw -Encoding UTF8 | ConvertFrom-Json
$guide = $trial.documents[0]
$db = 'data/retrieval_local/pdf-quality/nerc-reactive-planning-2016.sqlite3'
$base = $guide.baseline.knowledge_version
$new = $guide.derived.knowledge_version
& $py -X utf8 -m rag.cli --db $db derive-pdf nerc-reactive-planning-2016 --knowledge-version $base --max-chars 1200
& $py -X utf8 -m rag.cli --db $db query "Does a STATCOM's short overload capability count as reactive reserve?" --knowledge-version $new --max-results 3 --context-chars 2400 --context-depth 2
& $py -X utf8 -m rag.cli --db $db query "Does a STATCOM's short overload capability count as reactive reserve?" --knowledge-version $base --max-results 3
$fid = $guide.queries[0].results.paragraph_derived.evidence[0].provenance.fragment_id
& $py -X utf8 -m rag.cli --db $db lookup $fid --knowledge-version $new
& $py -X utf8 -m rag.cli --db $db context $fid --knowledge-version $new --max-chars 2400 --depth 2
```

实际 CLI 示例的自然 STATCOM 问题首名为页 25、字符 [1803:2479)、分数 18.072850；补充 6 个独立上下文，共 1867 字符。查询、lookup、verify 和旧快照查询退出码均为 0。初次使用 Windows 默认 GBK 输出时遇到 UnicodeEncodeError，且 PowerShell 解码造成保存的 Evidence 与原文不一致，回查正确拒绝；上面的 UTF-8 设置及 `-X utf8` 已验证解决。保存/往返 JSON 时也必须使用 UTF-8，不可忽略原文字符变化。

最终完整回归 51 项通过（10.047 秒），原有 40 项全部保留。关闭 site-packages 后 33 项通过（4.191 秒），七个 Harness demo 正常运行，证明纯切分/检索/Harness 不需 PDF 解析包。全套 PDF 集成测试需要该可选包。验证均使用项目解释器。

## 已知限制与下一阶段

没有 OCR、图像理解、公式修复、表格语义恢复、自动章节识别或真实 Agent。空白行和风险启发式可能误判；回退可以切断句子及跨页条件。短标题、页眉页脚和分词匹配可能干扰排名，邻接深度/预算不能保证语义完整。SQLite 当前派生版本复制原 PDF 字节和页记录，尚未做物理去重。v2 的最大长度改变会产生独立派生版本，旧快照不覆盖。

建议先人工复核固定查询集并标注目标原文与必需条件，再考虑可追溯的章节/规范类型元数据和短标题检索处理；最后用复核结果校准上下文预算。不能以本轮结果替代知识质量评测或事实审核。
