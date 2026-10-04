# q1 v2 归档复查：判断依据与引用边界

本轮未读取 `.env`、未调用 API、未覆盖原 JSON/Markdown/响应归档。
实际读取并离线重放了两份归档响应：`response-590a6dd6afe44fc29f29c580c623ca55.json`
与 `response-873aa371234b41e8aa0c89cbeeff9a58.json`。
重放 17 条主张和 4 个原引用检查，精确摘录、主张 ID/版本、历史状态均一致。
结构重放成功不代表语义判断正确。本次保留历史模型判断，不生成新的真实审核结论。

## 确认的问题

### Original citation 3（零基编号）

回答区间为 `[960:1234)`，开始于 `ast, typically only`，结束于
`Reactive reserve requirements can also be defined as the `。
截断了前一主张开头和 PV 主张结尾；原报告已记录词内/句段边界告警，却仍以 supported
作为标题。模型理由声称剩余 PV 内容由相邻证据或其他引用支持，可以不归咎于此引用。
这是错误的引用责任边界：其他支持材料不能使本引用得到完整支持。

| 项目 | 原绑定证据 | 独立判断材料 | 复查结论 |
| --- | --- | --- | --- |
| 动态储备计入、故障前储备作用 | `e-e293703220e3fae2b6c5c5444dfe05027bf2ba5a2b6c43ac411326e5dfb55a92`，文件页 25，片段页内 `[762:1803)` | 同一片段 | 原文可供复核，但引用的回答范围截断，不能宣称绑定完整 |
| PV 曲线 margin 主张 | 原绑定仍只有上述片段 | `e-50e84331306f7bd4290268486f12569b40fb0dd307adfabc89da9b3f673c9906` | 独立 finding 的支持不能迁移到 citation 3；该引用对 PV 部分未建立支持覆盖 |

原绑定摘录精确存在，且程序已禁止把其他 Evidence ID 直接塞进原引用的摘录。
问题发生在语义理由和“部分有支持”向整体 supported 的推论，不能靠 ID 合法判为正确。
本轮通用覆盖诊断指出：partial_claim_anchor_coverage_requires_review，
以及 independent_support_uses_unbound_evidence_not_original_citation_support。
原 status 作为历史模型判断保留；报告把它与未解决的边界/覆盖问题分开。
锚点区间覆盖检查本身也不证明原子命题的语义覆盖。

### 分类与依据

历史提取把全部 17 条命题标为 technical，审核契约要求肯定/否定判断必须正文摘录。
这使质量元数据和回答范围声明被强行附上无关的 reactive-reserve 正文。
例如“text_pending_review、layout pending review、formula/table not interpreted”
应查 provenance.quality_status / quality_warnings / text_basis，而不是定义正文。

以下分类是本次人工可读的开发复查建议，不是模型自动重新判分或独立验收标签：

| 命题内容 | 建议类别及依据 | 仍需注意 |
| --- | --- | --- |
| 前八条储备定义、持续时间、STATCOM、发电机、崩溃、PV | 技术事实；独立正文摘录与条件 | 语义与数量/否定/条件/因果须人工复核；原引用另审 |
| 北美来源、指南身份、不属于中国运行标准 | 来源/地区元数据与文档适用性事实 | 可能是复合命题，应拆分；curator applicability 字段不是所有中国规则不存在的证明 |
| 自愿建议、地区实践差异 | 文档政策/适用性事实与来源属性 | 应分别定位正文声明与元数据，不能自动归为无需核验的免责声明 |
| PDF 待复核、布局/公式表格未解释 | 来源/质量元数据 | 查实际字段，说明这是解析记录的属性，不是视觉原文已验证 |
| 建议核对视觉原文 | 复核建议 | 建议不是技术真值；若夹带事实前提，该部分仍须拆分核验 |
| 输入涵盖哪些问题、未提供哪些定义/语境 | 输入证据覆盖声明 | 必须针对生成输入集合，不能用核验 top-k 排空或扩大至整本文献/所有资料 |
| 回答限于所引指南 | 回答范围声明 | 对照回答及其引用来源；不是用无关定义正文证明范围诚实 |

原生成记录保留了 7 份候选 Evidence，后续审核也保留这些资料。
但历史记录没有显式保存精确生成输入快照/完整性清单，不能仅因它们位于 result.evidence
就自动认证它们等于模型完整输入。保守处理：无法确认完整输入时，相关覆盖声明为
not_assessable，范围是本次输入；不改称“文献不存在”或“所有资料均没有”。
本轮没有离线重写原模型的 insufficient_evidence 等历史状态。

## 实现改动

- `services/evidence_scope.py`：生成输入快照、ID/版本/正文与知识版本绑定、完整字段校验，
  元数据字段清单、独立于语义状态的引用覆盖诊断。
- `core/models.py`、`agents/contracts.py`：保留旧字段，增加类别、核验依据、元数据引用、
  输入范围 ID、生成快照、原引用部分锚点与覆盖问题。
- `agents/evidence_verification.py`：v3 响应明确五类主张及依据；元数据只接受实际非空字段，
  技术判断仍要匹配正文；输入范围缺失不能放行；原引用只接受其原绑定 ID。
- `services/claim_extractor.py`：v3 分类提示，要求复合事实拆分、不借建议/范围声明隐藏事实。
- `agents/generation.py`：未来生成结果保存真正传入的完整 Evidence 集合，不读取旧默认知识。
- `harness/runtime.py`：仅传递/校验快照，不改变调度顺序；修订版本不能复用旧版本快照，
  保存的快照必须与提供的原记录及知识版本一致。
- `harness/evidence_review_demo.py`：恢复已保存快照；分开展示语义状态、边界和覆盖问题，
  显示元数据字段，不用无关正文硬凑依据。
- `evaluation/evidence_review_replay.py`：纯离线重放，有哈希、调用和提示词绑定检查；
  只新建忽略目录下报告，拒绝覆盖。

新增依据是适用于不同类别的严格契约，不是删除原真实性约束：文本类仍有精确匹配、
Evidence ID 和完整审核覆盖检查；元数据增加字段和值的匹配；范围类增加完整快照绑定。
分类和语义仍由模型判断，程序不能证明模型分类正确；错误类别须人工复核。
原引用的状态也可能仍语义误判，本轮修复能隔离材料和显式保留覆盖问题，不宣称自动证明语义。

生成快照的哈希只校验一致性，不是密码签名，也不能证明外部伪造集合完整。
可信完整性来自生成入口捕获确实传入的输入；导入外部声明不能自动获得同等信任。

## 离线验证

`tests/test_review_boundaries.py` 使用明确标记的 synthetic_fixture，加一项私有归档开发回归。
验证的不只是结构合法：新证据不能改善原引用；边界告警不可抹去；元数据错值/无关摘录拒绝；
缺完整集合不可评估；后续检索不能混进生成输入范围；建议不是技术事实；快照绑定不可篡改。
生产规则没有硬编码 q1、PV 或某个 Evidence ID。

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe -m unittest discover -s tests -q
& D:\PowerTrustAI\.venv\Scripts\python.exe -m evaluation.evidence_review_replay `
  --input data/retrieval_local/deepseek/evidence-review-q1-fixed-v2.json `
  --output data/retrieval_local/deepseek/new-offline-review.md
```

私有档案缺失时真实重放项明确 skip，其他通用模拟回归仍运行；本机实际已完成真实档案重放。
不是独立知识验收集，不是新的真实审核通过。旧算法检查与迁移原则见
[legacy-migration-principles.md](legacy-migration-principles.md)。

最终验证：项目解释器 `D:\PowerTrustAI\.venv\Scripts\python.exe`，全部 **165 项通过**
（原 154 项 + 新增 11 项），31.197 秒，退出码 0，私有归档回归实际运行、没有 skip。
通过工具审批启动解释器，未安装依赖/修改权限。新增真实请求 0，旧项目工作区未变。

最终完整私有对照报告：`data/retrieval_local/deepseek/evidence-review-q1-fixed-v2-offline-final.md`。
原输入及归档哈希如下，检查后与最终复核一致：

| 原记录 | SHA-256 |
| --- | --- |
| evidence-review-q1-fixed-v2.json | 6a31229773a580e9615bf146a38a38444c55ab432ebb04e10c87280ce9568660 |
| evidence-review-q1-fixed-v2.md | 9b4a248705ac504c35304634ea77f6846687de6e29141f4b22772390a5d00537 |
| response-590a6dd6afe44fc29f29c580c623ca55.json | 1456941e6406b3af9fa1a5c0ad09075913e6e480994522131c28750f5deba0f4 |
| response-873aa371234b41e8aa0c89cbeeff9a58.json | 59666b1feeaa7aeb1b1f8c9eb1aafe25957bde8ed4aa84d555e66ee6e37ab4f7 |
