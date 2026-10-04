# 知识库与支持判断样本扩充 v1

记录日期：2026-10-04；接续已推送 `c5bd386`。本轮实际获取、解析、入库官方资料并导出新候选，没有训练、调用模型、重跑旧基线或更换生产知识配置。公开适配器 `evaluation/knowledge_support_expansion.py` 只负责来源锚定和版本隔离，复用 `KnowledgeStore`、`make_sample/deduplicate/group/export_review`，不是第二套样本流水线。

收尾日期2026-10-05：最终511项离线测试OK（65.784秒，0跳过），新增9项公开回归；48引文重开回查、parent分区及最终代码重建任务一致通过。另查四封面元数据，不从预留正文生成候选。ZIP实际69,256字节。最终Git/远端记录在本机verification.json，不以测试数量证明标签正确。

## 覆盖与真实来源

原三份资料是 NERC Reactive Power Planning（2016-12）、VAR-001-5 与 PNNL-35221（2023-11）。分别覆盖规划/无功储备原则、电压无功控制职责和PMU监测；不充分覆盖具体能力验证程序、限制器组合与测量例外、稳定性模型/工况选择。旧VAR标题存在编码显示问题、发布日期未提供，保留原历史元数据，不以猜测更正旧版本。

| 新来源与官方原文 | 版本、地区 | 实际获取与角色 | 补充内容及重复关系 |
|---|---|---|---|
| [NERC MOD-025-2](https://www.nerc.com/globalassets/standards/reliability-standards/mod/mod-025-2.pdf) | MOD-025-2；发布日期未提供；NERC适用实体 | 282,668字节，20页；开发库 | 机组/调相机能力验证、单机与整厂容量、验证条件；与原规划指南概念相邻，非相同全文 |
| [NERC Power Plant Model Verification and Testing for Synchronous Machines](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/irps/reliability_guideline_-_ppmv_for_synchronous_machines_-_2018-06-29.pdf) | 正文July 2018；文件名日期不冒充发布日期；历史技术指南 | 9,086,432字节，141页；开发库 | 能力曲线/限制器组合、电压依赖、设备测量例外与简化模型；涉及旧标准编号，不能当作当前合规清单 |
| [AEMO Power System Stability Guidelines](https://www.aemo.com.au/-/media/files/electricity/nem/security_and_reliability/congestion-information/2026/power-system-stability-guidelines-v3.pdf?rev=f9a92c88668643deb6666a6fbe912efb&sc_lang=en) | 3.0 FINAL，2026-01-12生效；澳大利亚NEM/NER | 567,598字节，33页；开发库 | 不同稳定机制、工具基准、模型校准、工况范围及适用法；不是中国或自动适用WEM的规范 |
| [AEMO Limits Advice Guidelines](https://www.aemo.com.au/-/media/files/electricity/nem/security_and_reliability/congestion-information/2025/limits-advice-guidelines.pdf?rev=62023af4877940f097e83bcf3dc02f45) | 封面February 2025；官方目录日期2025-02-06；NEM | 600,654字节，11页；独立预留库 | 在候选生成前冻结为跨文档评测材料；未从其正文生成训练样本、答案或调提示 |

原URL、重定向后的官方URL、下载日期、SHA256、发布主体、版本与用途分区保存于本机 `source-manifest.json` / `acquisition.json`。四份全文哈希互异，新增开发资料与原三份全文哈希无重复；概念重叠仍存在，不以片段增加证明覆盖质量或无泄漏。AEMO最新版以[官方目录](https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/system-operations/congestion-information-resource)及正文核对，未混入旧v2或修订标记版。

获取条件：匿名官方HTTPS，无登录、访问限制绕过或第三方转载。NERC[法律说明](https://www.nerc.com/legal-privacy-policy)保留版权，访问本身不授予许可；其资料训练/再发布许可尚未确认。[AEMO专门版权许可](https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions)允许准确、适当署名的AEMO Material用途，排除保密及他人拥有版权的委托报告；一般网站条款不是完整许可结论，专项核对记录另存 `license-review.json`。本轮全文/样本只在本机忽略目录，未公开发布数据或开始训练；具体训练用途、第三方图表权利需沿来源再核对。

获取失败保留：NREL/NLR-67799、73848原官方文档端点URLError；67799现官方NLR链接再次HTTPError，官方OSTI页面查询502。未用第三方替代。并网变流器实际设备特性/控制实验依据因此仍有缺口。[官方研究条目](https://research-hub.nlr.gov/en/publications/demonstration-of-essential-reliability-services-by-a-300-mw-solar/)仅核实67799出版元数据，不视作全文已入库。

中国来源单列：[GB38755-2019官方元数据](https://std.samr.gov.cn/gb/search/gbDetailed?id=9B70DDA94011A80CE05397BE0A0A84AC)及[国家标准公开平台](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=1D988D54A435E864E67CAA13217E8A99&refer=outter)核实标准号、2019-12-31发布/2020-07-01实施；本轮未取得可合法解析全文，没有入库或宣称具体中国运行限值。后续需中国官方稳定、励磁/无功及相关运行规范原文与现行适用条款。国外阈值不代替中国要求。

## 新快照与解析边界

通过SQLite backup只读复制原 `data/retrieval_local/semantic/corpus.sqlite3`，新库保留全部旧版本/快照；原库未写入。两份独立新库均重新验证原快照424片段全文哈希、版本和定位，重开后仍可回查。

- 开发库：`data/runtime_local/knowledge-support-expansion-v1/development.sqlite3`；原3＋新3，共6文档、618片段；快照 `k-8272a6d605b7555e1f34ce12bd6bbb2375372946af44f6fc461755f15713f493`。
- 预留库：同目录 `reserved-evaluation.sqlite3`；原3＋预留1，共4文档、435片段；快照 `k-f44d40d09985a58223d8d3c92ad49ab2ea920fce510e0fc14fc06ce2ba8fa314`。预留文档没有进入开发库，适配器拒绝为reserved角色生成候选。
- 原快照 `k-182e01fab54ebfada841fb108061c127273e9cfcd551b6f5a8888a769215e385` 继续回查。服务/向量索引仍是原配置；新BM25知识快照不冒充已匹配的旧语义索引。

当前pypdf 6.10.0/plain-pages-v1解析四份205页均为text_pending_review，ready_for_review只表示可进入人工复核。新增PDF按现有逐页片段解析，没有OCR、公式还原、表格重建或新切分参数。所有页保留提取/布局/公式表格警告，PPMV另有4页字符映射风险。Poppler渲染NERC13页、PPMV33页、AEMO8页并视觉检查选择的文字段落；渲染出现缺替代字体告警，未据曲线生成数值。没有全205页视觉校对，样本仍明确为提取文本，不把局部视觉检查提升成全文认证。

## 新候选、监督与隔离

冻结16个不同概念家族，48原始/48去重候选，全部synthetic、pending、0确认。每家族是来源文字原命题＋明确受控错误＋不同范围/条件/工程前提变体；不是从旧模型预测复制真值。45事实支持任务、3工程前提任务；建议supported16、contradicted17、insufficient_evidence12、not_assessable3。包括单机/整厂20/75MVA边界、MW/MVA类别、调相机核验、辅助设备工况、能力限制器组合、电压依赖、数字励磁测量例外、简化模型、法律地区、稳定机制、工具基准、模型选择/校准、工况范围与时间尺度。标签建议与理由需用户逐项监督，受控改动本身不证明建议正确。

原命题必须逐字锚定原页（只允许空白规范化比较）；字符区间、Evidence ID、文档/知识版本、SHA、原文/出处/页码、适用范围、方法/parent/answer-version/component均保存。不存在真实模型请求/响应，哈希字段显式null；交付方法是curated_exact_anchor，不能当成生产检索召回测试。缺锚、错误角色/歧义/建议失败整家族报错，其他有效家族保留；不截断后放行。新候选本轮48项全部锚定成功。

沿既有谱系＋问题家族＋0.9近重复并集规则，预分train36（12家族）/validation9（3家族）/test3（1家族）。同家族、parent/变体不跨集合。相同交付引文SHA跨集合0；**同Evidence页/片段跨集合3**，三份新开发文档均跨集合共享，不能只用短引文不重叠宣称无泄漏。与91种子比较0近重复对/0完全相同交付引文，但同主题/机构和旧指南知识重叠；旧种子分区绝不改写。全体候选合计139项、确认仍0，未合并成训练集。

同资料内评测：这些预分仅供人工复核后的开发对照，测试只有1家族，不能可靠估计泛化。跨文档评测：预留Limits Advice及两个问题家族，当前0已构建独立评测样本；后续另行监督构造/冻结，不能训练后挑题。它与开发AEMO指南有主题/引用联系，不宣称跨机构或完全无知识暴露；可靠泛化仍需更多独立机构/资料和问题家族。规划数百条用户复核样本是小规模实验目标，数量不是质量保证或本轮配额。

旧91项的task/建议/pending/家族/分区、旧ZIP、5有效预测和失败记录保持，关键文件前后SHA相同；本轮没有旧基线重跑。监督结果仍用原 `support_dataset` review入口合并，只有明确确认标签可进入训练出口。不能用构造样例自评替代用户标签或专家金标准。

## 可运行入口及复现

公开代码不依赖私有data。普通回归：

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_knowledge_support_expansion -v
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

资料取得并冻结清单后，指定新目标/报告，不覆盖已有版本：

```powershell
& .\.venv\Scripts\python.exe -m evaluation.knowledge_support_expansion ingest --base <原库> --destination <新的开发库> --manifest <source-manifest.json> --role development --report <新的入库报告.json>
& .\.venv\Scripts\python.exe -m evaluation.knowledge_support_expansion ingest --base <原库> --destination <新的预留库> --manifest <source-manifest.json> --role reserved_evaluation --report <新的入库报告.json>
& .\.venv\Scripts\python.exe -m evaluation.knowledge_support_expansion prepare --database <开发库> --knowledge-version <冻结快照> --manifest <清单> --families <curated-families-v1.json> --output <新的输出目录> --seed <旧dataset.json>
```

这些路径是离线开发CLI，未新增普通API文件路径输入。manifest的sources每项含document_id/role/file/sha256/SourceMetadata，families含family_id/document_id/file_page/anchor_text/base_proposition/variants（proposition/operation/suggestion/reason）；旧种子只读。实际重现文件在本机目录，官方全文不随Git发布；干净检出使用临时Markdown synthetic_fixture运行公开边界测试。

交付包 `data/runtime_local/knowledge-support-expansion-v1/support-review-expansion-v1.zip` 含48项MD/JSON待复核表、逐条定位及来源、来源/划分报告、说明，排除数据库、全文和预留文档正文。`candidates-v1`保留，`candidates-v2`仅另存共享Evidence完整报告，48任务ID/哈希一致。关键测试覆盖精确定位/旧快照、分区拒绝、重复合并、parent组、非法来源协议/哈希、原命题忠实、部分失败/整家族原子性、不可覆盖与旧种子重叠报告。首次新测试7个Windows清理错误来自未显式关闭SQLite备份连接，已修正并回归；编码查页和Poppler字体失败记录保留。实际日志、质量/证据检查、ZIP哈希及提交/远端记录见本机reading-notes.md与verification.json。
