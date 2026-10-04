# 文本型 PDF 入库与官方资料试运行

验证日期：2026-10-02。范围是检索程序与提取质量抽查，不是事实审核、人工标注验收或知识正确性评测。Harness 调度、假 Agent、BM25 算法和旧项目未修改。

## 来源核对

检查 docs/knowledge-sources/manifest.json 与本地文件：

| 资料 | 本地状态 | 本轮处理 |
| --- | --- | --- |
| NERC Reactive Power Planning Guideline | 存在；SHA-256 与清单一致 | 选择为真实试运行，57 页 |
| NERC VAR-001-5 | 存在；SHA-256 与清单一致 | 未入本轮试运行库 |
| PNNL-35221 | 存在；SHA-256 与清单一致 | 未入本轮试运行库 |
| AEMO 2024 Victorian Network Performance & Insights Report | 清单记录 HTTP 403；无本地原件、无哈希 | 未入库；未声称下载成功，本轮未重试下载 |

NERC 指南原件来自 https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/sams/reliability-guideline---reactive-power-planning.pdf ，内部日期 2016-12，含 PDF 文件第 57 页的 2017-03-07 勘误。本轮机构、日期、标题、来源 URL 直接复用经检查的收集清单，不从文件名或 PDF 元数据推断。指南是北美历史规划建议，不是所有地区的现行强制标准。

原 PDF、全文提取、数据库、完整命中和页面截图均在 .gitignore 已排除的 data/knowledge_local/ 或 data/retrieval_local/；没有 git add、commit、push 或全文公开再分发。旧项目 git status --short 为空。

## 实现及接口

| 文件 | 改动 |
| --- | --- |
| requirements-pdf.txt | 唯一可选依赖 pypdf==6.10.0 |
| rag/pdf.py | 严格逐页文本提取、诊断分类、解析器配置及提取指纹 |
| rag/storage.py | 复用版本/快照、事务与片段表；添加 pdf_versions、pdf_pages、pdf_fragments |
| core/models.py | EvidenceProvenance 增加可选文件页、解析器版本、提取哈希、邻接及质量字段 |
| rag/cli.py | 原 ingest 自动识别 .pdf；增加 inspect-pdf、pages；复用 query/lookup/verify |
| tests/pdf_fixtures.py、tests/test_pdf_retrieval.py | 临时生成明确 synthetic_fixture 样例，10 项 PDF 行为测试 |
| evaluation/pdf_trial.py | 已获取资料的哈希审计、NERC 入库、9 个查询及逐命中回查 |

Retriever/ RetrievalRequest/ RetrievalResult/ Evidence 接口继续复用，没有第二套检索器或证据模型。来源类别可以是 guideline，存储另用 pdf_versions 判断解析格式，避免把类别与文件格式混为一谈。

SQLite 是可加性扩展：旧 Markdown 的原文、ID、文档版本、知识快照和索引配置保持不变。首次可写打开时创建三张扩展表；只读打开旧 Markdown 库也能查询。原索引配置中的 parser 是 Markdown 解析配置；PDF 的解析器、模式及切分配置单独绑定到不可变 PDF 文档版本，知识快照再绑定这些文档版本。

PDF 文档版本哈希包括原文件哈希、显式来源元数据、解析器版本和完整提取报告指纹。报告指纹包含逐页文本、页状态、诊断、邻接及配置。库保存 PDF 原字节，但不伪装为 UTF-8 原文；每页提取文本保存在 pdf_pages.raw_text，片段原文与相应页完全一致。

PDF Evidence 回查不重新解析、不导入 pypdf：验证原文件哈希、提取指纹、逐页文本哈希、文档版本、页内区间、索引文本、片段 ID、相邻 ID 和传入 Evidence。它证明保存文本的可回查一致性，不能证明提取等于视觉原文。

## 提取与质量策略

安装并实测的是项目 .venv 中的 pypdf 6.10.0 / Python 3.13.2，固定在 requirements-pdf.txt。选择它是为了仅增加一个纯 Python 提取依赖；不安装 OCR、图像模型或额外布局解析库。版本信息见 [PyPI](https://pypi.org/project/pypdf/6.10.0/)，提取限制见 [官方说明](https://pypdf.readthedocs.io/en/6.10.0/user/extract-text.html)。

- 使用 strict=True、plain 提取模式；不尝试解密、不执行 OCR、不按视觉布局改写或补齐文本。
- 按 1 基文件页保存，页内位置是 Python Unicode 字符零基半开区间，基于保存的 pypdf 提取字符串。未知印刷页码、章节一律 null；即使正文内出现页码数字也不自动转换成元数据。
- 首版一页一个片段，不跨页拼接。字符范围为 [0,len(page_text))；保留所有提取内容，包括否定句、条件、页眉、页脚及脚注。page_lines 是提取字符串的 splitlines() 行号，不是视觉行号。
- 保存相邻文件页及相邻文本片段 ID。空白候选页没有片段，仍保存在页表；片段邻接可能跨过空白候选页，不表示已拼接内容。Evidence 记录 adjacent_page_context_not_merged。
- raw_text 完全保持提取结果；search_text 只做 casefold 和空白归一化。本轮不自动增强推测标题、还原公式、整理表格或去页眉页脚。

| 页级状态 | 判断依据和处理 |
| --- | --- |
| text_pending_review | 有非空提取文本；能检索，但仍待人工布局/完整性复核 |
| scan_candidate_unsupported | 观察到图片绘制、没有提取文本；只称疑似扫描，不确认真正扫描来源；整份入库拒绝 |
| blank_candidate | 未观察到绘制/文字操作或注释；疑似空白，仍需视觉确认；混合文本文件保留该页记录但不建片段 |
| no_text_pending_review | 无文本但观察到其他绘制/注释；不能可靠区分矢量文字、图形或其他页面；整份入库拒绝 |
| parse_failed | 文件读取或页面提取异常；包含实际异常类型和信息；整份入库拒绝 |

加密文件为 encrypted_unsupported；全空白候选为 no_extractable_text。混合文本/扫描候选 PDF 也拒绝，避免静默漏页。有文本且包含图片的页可以保存文本，但 images_not_interpreted 明确提示图片内容未接入；不能据此判定全文完整或不是扫描件。

坐标启发式只提供 possible_columns_or_table / suspected_reading_order；它可能误报或漏报。字符替换符/控制字符标 suspected_character_mapping。所有有文本页都保留 layout_pending_manual_review 和公式/表格未解释提示。ready_for_review 只表示具备可入库文本，不表示解析质量认证。

提取在提交前完成；任一不可接受页阻止提交并输出报告。全部原件、页面、片段、快照及 latest 更新在同一入库事务，后期 SQLite 失败整体回滚，不破坏旧版本。提取依赖缺失或版本不符明确报错；Markdown 和离线 Harness 仍可运行。

## 运行命令

从 D:\PowerTrustAI 项目根目录运行：

```powershell
$taskPython = 'D:\PowerTrustAI\.venv\Scripts\python.exe'

# 本轮已安装；其他环境可以只安装这份可选依赖。
& $taskPython -X utf8 -B -m pip install -r requirements-pdf.txt

New-Item -ItemType Directory data/retrieval_local -Force | Out-Null

# 预检；--db 为 CLI 公共参数，inspect-pdf 实际不打开数据库。
& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/official-pdf.sqlite3 inspect-pdf data/knowledge_local/nerc-guideline.pdf

# 推荐试运行入口：复用收集清单中的来源元数据，核对三份文件哈希。
& $taskPython -X utf8 -B -m evaluation.pdf_trial

$taskTrial = Get-Content data/retrieval_local/pdf-trial.json -Raw | ConvertFrom-Json
$taskKnowledgeVersion = $taskTrial.ingested.knowledge_version

$taskOutput = & $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/official-pdf.sqlite3 query 'dynamic reactive reserve STATCOM overload sustained maximum output' --knowledge-version $taskKnowledgeVersion --max-results 3 --purpose verification
$taskOutput
$taskQuery = $taskOutput | ConvertFrom-Json

& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/official-pdf.sqlite3 lookup $taskQuery.hits[0].fragment_id --knowledge-version $taskKnowledgeVersion
$taskQuery.evidence[0] | ConvertTo-Json -Depth 12 | Set-Content data/retrieval_local/pdf-evidence.json -Encoding utf8
& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/official-pdf.sqlite3 verify data/retrieval_local/pdf-evidence.json

# 固定快照的全部页面、状态、提取原文：
& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/official-pdf.sqlite3 pages nerc-reactive-planning-2016 --knowledge-version $taskKnowledgeVersion
```

如需手动入库，可使用同一 ingest 命令；例如另一个本地数据库中：

```powershell
& $taskPython -X utf8 -B -m rag.cli --db data/retrieval_local/manual-pdf.sqlite3 ingest data/knowledge_local/nerc-guideline.pdf --document-id nerc-reactive-planning-2016 --source-type guideline --source-uri 'https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/sams/reliability-guideline---reactive-power-planning.pdf' --publisher 'North American Electric Reliability Corporation (NERC)' --publication-date '2016-12' --document-title 'Reliability Guideline: Reactive Power Planning' --applicability 'North American bulk power system; historical voluntary guideline'
```

人工命令的适用范围元数据与试运行清单不同，所以知识版本也不同，这是预期行为。相同 ID 不同内容/元数据必须 --update；保留旧知识版本可以查询旧提取，不要求原路径仍存在。

## 实际试运行与限定条件检查

57 页均为 text_pending_review，57 个片段；重复入库 unchanged=true。原文件 SHA-256 为 1cefced2d010a84c7245885bc4c99df3bcc4f4bf47357d719a377794d5c3295f。实际知识版本：

```text
k-11127eb385cc70e05929f6c2d510e65a2331cb55678378ba2286f4b09d5dd041
```

以下为本轮开发试运行查询。评分均为 BM25-v1(k1=1.5,b=0.75,ln-positive-idf,unique-query-terms)，不是事实支持度；页码均指 PDF 文件页。完整 top-3 原文、全长片段 ID、排名、字符区间和哈希在忽略目录 data/retrieval_local/pdf-trial.json。

| 英文查询 | 首位文件页 / 分数 | 命中定位与开发者检查 |
| --- | --- | --- |
| dynamic reactive reserve STATCOM overload sustained maximum output | 25 / 18.180021 | Reactive Reserve 段；保留持续时间、短时过载排除和发电机稳态限制，未只截取定义句 |
| QV analysis may not reveal wide-area voltage stability problems | 22 / 19.992281 | QV 方法局限段，否定与预选母线条件在同页；开头承接 21 页，末尾继续到 23 页，完整 QV 论述需邻页 |
| PV analysis active power transfer operating limits | 23 / 13.106013 | PV 小节；保留前/后事故时间范围、仅自动控制及不能可靠研究部分相互作用的限制；第 2 位为 42 页区域案例，不是通用说明 |
| static dynamic reactive resources voltage squared | 8 / 8.650836 | Background 资源分类；额定电压条件保留；同页公式有明显字符映射损坏，不能用提取符号计算 |
| synchronous generator capability stator field current excitation limiters | 9 / 14.844157 | 激励限制器续段；不完整命中：定子、励磁电流、端电压及有功条件在第 8 页（第 2 位 13.052104）；须结合前页，不能只用首位回答全部问题 |
| NERC standards do not require minimum load power factor | 38 / 11.065944 | 推荐实践中的否定句及 TO/DP 边界限定保留；只适用于文档说明范围，不能扩展成全球规程结论 |
| STATCOM SVC errata voltage-current characteristics | 57 / 17.990512 | 勘误日期及图号；正文图所在第 11 页为第 2 位 10.609161；图形本身没有可靠文字表示 |
| voltage stability | 48 / 2.053486 | 不够准确：首位是 PJM 区域操作实践，后续 55、54 页也是区域标准案例，不能视为一般定义或最佳综述 |
| synchrophasor | 无命中 / 无分数 | 本指南无该词项，真实检索覆盖不足；不生成答案，不填充零分片段 |

所有非空命中均完成存储回查和页内原文切片相等检查。没有人工打相关性标签、没有判断 supported、没有真实 Agent 验证。这些查询偏向明确词项，不能据此报告检索精度或召回率。

视觉抽查了文件页 8、9、21、22、23、25、27、34、38、42、48、57，并对照本轮提取文本。渲染使用现成 Codex 随附 pypdfium2/Pillow，仅作诊断；应用和全部测试使用项目解释器及项目 pypdf，未安装额外渲染依赖。

待人工复核的重点：

- 8 页：公式符号重复、替换字符和词内空格。只能读取保留的自然语言，不可当可靠公式解析。
- 8–9、21–23、25–26 页：段落跨页。片段保持分离；邻接能定位上下文，但页眉/页脚夹在句间，不能盲目字符串拼接。
- 22、23、25、38 页：人工核对否定、时间范围、事故条件、地区和角色边界。抽查可见这些限制仍在提取文本中，不表示已完成专业事实审核。
- 27、34、42 页：多列合并表头、跨行单元格；plain 提取失去可靠行列关系。第 34 页尤其包含正常/长期/短期/紧急时间段，不得从扁平数字串推断阈值对应关系。
- 8、22、23 页的 possible_columns_or_table 在单栏正文上也触发；此次抽查没有确认正文双栏，不能声称整份文件无双栏。坐标启发式不是布局分类器。
- 48、55、54 页：区域实践容易被宽泛查询排到首位，保留原页地区名称也不足以自动约束后续回答。

自动坐标/字符映射告警页为 3、7、8、10、19、22、23、27、29、34、35、37、42、44、45、48、52、53、54；其余页仍是 layout_pending_manual_review，不能视为通过人工复核。

## 测试结果与限制

项目解释器绝对路径 D:\PowerTrustAI\.venv\Scripts\python.exe，Python 3.13.2。沿用此前允许的提升执行审批机制；未重建环境、未修改目录权限。

| 验证 | 实际结果 |
| --- | --- |
| 完整 unittest discover -v | 40 项通过（原有 30 + PDF 10），退出 0；11.789 秒 |
| -S -m unittest tests.test_harness tests.test_retrieval -v | 不加载 site-packages，原有 30 项通过，退出 0；6.422 秒 |
| -S -m harness.demo | 七个场景完成，退出 0 |
| 官方试运行 | 原件哈希核对、57 页入库、重复入库、9 个查询及每个命中回查完成 |

样例覆盖页内定位、否定/条件保留、真实空白内容候选、纯图片候选、非文本矢量页、混合 PDF、加密/损坏文件、注入页面失败、SQL 后期回滚、幂等与显式更新、历史回查、邻接、字符/版本篡改拒绝、疑似双栏/阅读顺序、旧 Markdown 库扩展及 CLI 往返。样例只在临时目录生成，不冒充真实扫描测试集或官方资料。

已知限制：无 OCR、图片理解、可靠公式/表格恢复、阅读顺序保证、自动印刷页/章节识别、跨页段落合并或真实审核。严格解析可能拒绝阅读器能显示的容错 PDF。整页片段较长且包含多主题，页眉页脚参与 BM25，可能降低排序质量。BM25 仍扫描完整快照；async 接口内部为同步工作，不适合高并发。存储回查重建完整报告和指纹，适合当前小语料，尚未优化。

下一阶段应先由人复核告警页、跨页上下文与实际检索相关性，再考虑不损害原文限定条件的页内段落切分，以及结构化表格专用适配；本轮不自动推进这些能力。
