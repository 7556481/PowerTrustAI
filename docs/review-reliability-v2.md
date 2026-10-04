# 审核可靠性修复 v2

日期：2026-10-04。实现、离线回归和一次冻结真实批次完成；**尚不具备进入六场景固定回归的条件**。这不是整体审核通过或工程安全认证。

## 文件与职责

|文件|改动|
|---|---|
|`services/claim_obligations.py`、`services/claim_extractor.py`|可选提取 v7；区分原文锚点、规范化命题、模型立场和核验义务；有限正面计数声明不能只有文字存在性检查|
|`services/review_fidelity.py`、`agents/verification_contract_v9_scoped.py`|可选事实 v9.3/schema11；审核显式判断提取忠实性、立场及核验目标；异议/不确定不许 supported；继续复用旧分类异议和逐 finding 隔离|
|`core/models.py`、`core/validation.py`、`core/typed_evidence.py`、`evaluation/archive_replay.py`|注册 ObligationClaim/FidelityComponentReview 扩展，严格字段及目标/状态绑定；旧类型、旧归档字段不变|
|`tools/scalar_numbers.py`、`tools/unit_conversion.py`|可选 scalar-si-conversion-v2；明确 ASCII 小数和三位逗号千位分组，保存原字符串/归一化轨迹；拒绝畸形分组和后缀误取|
|`services/quantity_checks.py`|数量规则 v1.3 限于可解释的闭合正面声明；转述、反驳和嵌套语境保留检查未完成，不把模型角色当程序证明|
|`agents/power_domain_review.py`、`agents/domain_contract_v3.py`|可选领域 v3.1/protocol4、演示规则 v1.1；概念范围与厂站前提分开；厂站缺模型/限值/运行点/故障集合仍保留|
|`harness/runtime.py`|新协议注入既有工具/交付输入；调用原调度器与原政策，真实工具执行与预算/轨迹不另建体系|
|`evaluation/reliability_v2.py`、`evaluation/reliability_trial.py`|定向历史诊断、冻结两场景与三变体、60 次最坏预算、独立结果归档；可选参数保留旧入口默认行为|
|`tests/test_scalar_numbers_v2.py`、`tests/test_review_reliability_v2.py`|12 项新离线开发回归，不联网、不调用 API；不是语义质量证明|

默认检索、BM25/Dense/RRF、知识快照、旧项目、标签和审核决策政策未修改。新协议显式选择；单位工具默认仍为 v1。保存的 v1/v2 历史记录及保护文件哈希核对通过。

## 验证结果

项目解释器 `D:\PowerTrustAI\.venv\Scripts\python.exe`：390 项全量离线测试通过，48.969 秒。普通测试没有联网。

固定真实批次 `data/retrieval_local/deepseek/reliability-v2/`：模型实际返回 `deepseek-flash`，36/60 请求，7 次格式纠正，墙钟 194.407 秒。未重复失败场景、未在批次中改代码、未换模型或检索。

|必需阶段|两个重点场景|
|---|---|
|初次提取/事实/领域审核|各 2/2|
|按原政策一次修订|2/2|
|重提取/领域重审|各 2/2|
|事实重审|0/2 完整，合法同级结果保留|
|完整闭环|0/2|

三个变体：直接错误计数契约失败；引用并反驳和正确千位分组换算执行完成。变体不参与完整闭环分母。

已改善：原“四类额定值”保留技术真实性义务，没有再次只按 answer_scope 放行；230 kV=230 V 被实际判冲突；230 kV=230,000.0 V 可由实际工具结果核验；反驳句未产生确定性计数错误告警；工程输入缺失与执行失败分开。

**仍有真实漏检**：数量初审模型把有功输出当作第四类额定值，仍标 supported。程序枚举告警不能计作模型成功。修订文本指出有功输出不是另一额定值类别，但两个重点场景事实重审均有类型/立场异议契约失败，不能称为问题已完整解决。

实际根结构错误还有 `findings` 外附 `citation_reviews`：基础 system 存在联合根示例，后文又规定独立根仅 findings。实际响应继续混合，这属于提示协议表达冲突，不全归因于模型。一次纠正无效的失败原样保留，没有静默删除额外字段。

技术正确性与“回答写了这句话”仍必须区分；新增忠实性/立场字段是模型判断，不是程序证明。输入覆盖检查只针对实际交付内容；索引维护元数据不能冒充官方正文。标量换算不证明物理量类别、稳定或工程可行。

## 归档与阅读

全部私有材料在 Git 忽略目录 `data/retrieval_local/deepseek/reliability-v2/`：

- `reading-notes-v2.md`：人工阅读入口和剩余阻断问题。
- `full-report-v2.md`：逐主张、依据原文、定位、工具、修订动作及最终原因。
- `repair-checklist-v2.json`：问题→实际失败记录→代码→修复→验证。
- `targeted-scoped-replay-v2.json`：12 份旧事实响应按旧 scoped 契约重放，7 结构合法、5 失败；7 份其他阶段仅检查，没有重放全部历史请求。历史状态不迁移。
- `request-ledger-v2.json`、`failure-matrix-v2.json`：实际消息/响应路径、每次用量/错误及有效部分。
- `summary-v2.json`：逐阶段用量、候选数量、交付字符量、耗时；模型耗时之和包含并行重叠，不等于墙钟。
- `plan-v1.json`、`delivery-manifest-v2.json`：本轮协议、配置、代码及保护文件哈希。计划文件名沿用旧入口，内部 version 为 review-reliability-v2。

准备时 `targeted-diagnosis-v2.json` 的 joint-parser 投影检查不等于完整 scoped 重放，完整根字段结果以 `targeted-scoped-replay-v2.json` 为准。

返回 token：输入 671048、输出 28678、合计 699726；cache hit 251136、miss 419912。36 请求均提供用量。费用估算 USD 0.080947008–0.161894016，**不是账单**。2026-10-04重新核实[官方价格](https://api-docs.deepseek.com/quick_start/pricing/?tab=case-studies)；既有请求中的价格日期字段保留原样。

## 运行与停止边界

离线回归：

```powershell
Set-Location D:\PowerTrustAI
.\.venv\Scripts\python.exe -m unittest discover -q
```

本轮入口为 `python -m evaluation.reliability_v2 prepare/live --output-dir <独立目录>`；live 要求对应源码哈希的离线验证门禁，已有启动目录拒绝再运行。由入口加载 `.env`，不打印凭据、归档请求头或使用隐式重试。

最坏调用数：两个初审各7＋三变体各6＋两个修订/完整重审各14＝60。修订最多6个引用绑定，否则结束该场景，不超预算。规则警告、模型判断、人工待复核分别保留。

尚阻断下一次六场景回归：四类额定值语义漏检；独立/联合根表达冲突；重审类型与立场异议未稳定给出合法未完成结果；输入覆盖、文献描述及有限拒答分类不稳定。领域模型对概念范围仍可能过度要求工程输入，需人工核对。

本轮结束，不自动开始下一轮修复、付费重跑或六场景回归。
