# 输出契约 v5：组成部分与统一依据

## 第 2 题历史失败的含义

首条原主张是 “According to the NERC Reactive Power Planning guideline, QV analysis has two main drawbacks.”
技术命题是该指南列举 QV 方法的两个主要缺点；来源归属是其所指资料确为 NERC 的这份指南。
正文应支持方法缺点及数量/限定条件，来源字段应标识该资料。标题/机构字段不能证明正文内容，
正文命中也不能自动证明被归属到正确机构或文档。

可分别提取两个原子主张，共享同一个完整精确句子锚点；来源与技术部分需保留关联和“according to”
限定。若归属关系需要作为一个完整命题保留，则同一 Claim 显式保存多个 components，逐部分审核。
程序不会按关键词自动拆分技术/元数据语义。

第 2 题两份 v4 审核响应都在 technical_fact 的 evidence 内同时输出 excerpts 与 metadata_refs，
违反 v4 的互斥分支。新契约允许这些依据并存，但原始 v4 JSON 不是 v5 响应，仍按历史契约失败。
离线开发回归仅显式映射首项依据对象，验证原文/元数据回查与可表示性，不改变原判断或宣称语义正确。

## 提取及定位

新 CLI 使用 `atomic-claims-v4-explicit-components`，主张必须包含 1～8 个显式组成部分，
每部分由模型返回 category/proposition。程序根据主张 ID 与组成部分序号生成 component_id。
Claim 仍保存精确完整原文句段及 Python 字符区间；规范化 proposition 不用于定位。
共享同一原文区间的拆分主张有共同 anchor_group_id，不要求改写或缩短原文以制造独立定位。
各部分类别、原子性及限定条件完整性仍是模型判断，需要人工复核。

历史提取协议有明确兼容入口，缺失 components 不会自动推断；v5 审核拒绝没有显式组成部分的输入。
历史重放只对旧记录缺失的空默认字段作版本兼容投影，不抹掉新语义信息。

## 统一依据列表

初版审核提示词：`evidence-verification-v5-component-bases`，响应契约 `evidence-verification-output-v5`。
第 3 题离线诊断后版本为 `evidence-verification-v5.1-component-bases-classification` / `evidence-verification-output-v5.1`。
PDF 逐字摘录丢失换行的第二次诊断后版本为 `evidence-verification-v5.2-typed-quote-references` / `evidence-verification-output-v5.2`。
根节点只有 findings/citation_reviews；旧 v5 结构仍合法，原记录保留原版本。

finding 必填 claim_id、rationale、applicability_conditions、bases、component_reviews；可选 dimension_findings。
模型不重复返回程序绑定的回答版本、组成部分 ID、元数据值、知识版本或父级状态。

| type | 模型返回字段（除 type） | 程序校验与绑定 |
|---|---|---|
| text_excerpt | evidence_id，加 quote_id 或 quote 二选一；仅 quote 可选 prefix/suffix | quote_id 精确选择完整原文片段；quote 精确、唯一匹配并计算字符区间 |
| metadata_reference | evidence_id、field_path | 字段必须实际存在且非 null；读取真实值，模型不能返回 value |
| input_snapshot_reference | 无 | 只绑定已保存的完整生成输入快照；禁止用后来检索补造 |
| answer_text_reference | quote；可选 prefix/suffix | 对冻结回答精确匹配，用于回答范围声明 |

同一 finding 可包含多种依据；每种严格禁止额外字段，最多 24 项。
v5.2 输入提供 QUOTE_CATALOG：按 Evidence ID 与原文哈希生成 quote_id，对应完整原文片段的
字符区间 [0,len(text))。模型选择 quote_id 时，程序回填已有原文及已知区间，并保留 quote_id，
不生成/规范化文本，也不补造语义状态。未知 ID、跨 Evidence 的 ID、quote 与 quote_id 并存，
或对 quote_id 添加 prefix/suffix 均拒绝。原引用的 quote_id 仍只能选择原绑定 Evidence。
这是精确索引选择，不是模糊匹配，也不是重新检索。首版单元为完整片段，可能较长且含页眉、
公式乱码等，质量告警仍保留；更细的摘录仍可使用逐字 quote。
component_reviews 每项为 component_index、status、basis_indexes、rationale，完整覆盖输入各部分且不重复。
组件通过依据索引明确选择自己的依据，不以“整个 finding 有某种依据”替代组件对应关系。

supported/contradicted 的技术部分必须选正文摘录；元数据部分必须选实际字段；输入覆盖部分必须选完整
输入快照；回答范围部分必须选冻结回答摘录。复核建议仅为 not_assessable，不能借此隐藏事实前提。
证据不足可以 bases:[]/basis_indexes:[]。历史快照缺失时输入覆盖只能 not_assessable 且不绑定依据。
正文说明“建议自愿”等内容属于正文事实，不应误归为文件元数据。

父级状态由已完整覆盖的语义组件判断按合取规则汇总：任一 contradicted -> contradicted；否则任一
not_assessable -> not_assessable；否则任一 insufficient_evidence -> insufficient_evidence；全部 supported
才为 supported。组件记录始终保留，汇总不是总体风险分数，也不是工程审核 pass。

v5.1 允许组件审核显式报告可选 classification_issue（suggested_category、rationale）。
冻结类别仍保留不变，建议类别必须为不同的已知类别；存在分类异议时只能 not_assessable。
这不是允许模型重分类以绕过支持要求。例如“正文包含 D 曲线”若上游误标元数据，审核器可记录建议
technical_fact 和理由，但不能借该建议直接改成 supported。
正文内容/元数据/完整输入覆盖的分类自身也需要审核，不能把提取器分类当作可信事实。

原引用保留独立状态、原绑定 ID、边界与覆盖问题。其依据只能使用该引用原本绑定的 Evidence，包括元数据；
不能使用其他引用或独立检索证据修复。确定性原引用判断仍需原绑定正文摘录，元数据不能单独替代正文支持。

## 校验与诊断

解析器与 core 都检查组成部分覆盖、依据类型、类型内部字段组合、原文匹配、实际元数据值、快照绑定、
父级汇总及派生字段一致性。兼容展示字段 excerpts/metadata_refs 是已校验 typed bases 的投影，保留全部依据。
纠正反馈保留所有已检测错误，类型结构错误给出字段路径、允许字段和处理选项。
已知多余字段名可安全显示；任意未知字段名不直接回显，防止把不可信值当诊断泄露。
程序不自动删除额外依据，不补造语义判断。一次初始调用最多一次预算内格式纠正。
组件缺少对应类型依据时，纠正反馈明确提供冻结类别、所需依据类型、实际选择类型以及合法处理选项。
缺失历史输入快照时明确反馈唯一允许状态 not_assessable 和空 basis_indexes，不依赖泛化重试指令。

## 快照与运行边界

现有 Generation Agent 无论有/无证据均保存完整输入 evidence_snapshot；该集合包括未被引用的输入证据。
Harness/CLI 的 asdict 序列化保留该快照。新离线回归检验两条输入、只引用一条时仍保存两条。
原五问记录历史上没有完整生成输入快照，保持缺失，不把本次检索视为当时完整输入。

付费 CLI 显式选择 v5 + 新提取协议。Python API 的显式 v4 兼容路径保留既有离线模式，避免自动升级
历史响应；如单独构造服务，应设置 `schema_version=5` 和 `typed_components=True`。
未修改 BM25、PDF 切分、Harness 调度、假 Agent 或旧项目；没有新增依赖或新的 Agent。
原始生成与历史审核记录不可覆盖。成功只能是 evidence_reviewed，领域审核未运行，语义正确仍待人工复核。
