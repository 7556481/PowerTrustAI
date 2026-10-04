# 事实重审稳定性 v3

本轮完成模板拆分、严格异议校验、离线回归及一次固定真实验证。只验证事实重审阶段，没有重新生成、Revision、领域审核或新完整闭环成功。默认检索、知识快照、审核政策、旧项目、原标签和历史记录不变。

## 实际结果

| 指标 | 结果 | 含义 |
|---|---|---|
| 两场景独立核验 | 2/2完成 | 各一次格式纠正，最终保留所有组成部分 |
| 原引用检查 | 两场景2/2；引用4/4完成 | 仅检查各引用原绑定 Evidence |
| 12例数量语义组件执行 | 11/12完成 | N11纠正后仍返回非法维度，明确保留失败 |
| 合成明确计数错误 | 模型4/4判 contradicted | 不计程序告警，不证明真实电力泛化 |
| 合成开发预期 | 9/10相符 | N12核验对象转换仍漏检 |
| 真实资料数量例 | N10无法评估；N11执行失败 | 不能称为正确识别错误或正确事实判断 |
| 调用 | 23/40上限，预先最坏预算32 | 5次格式纠正；6份响应曾违反契约，无原样重跑 |
| Token | 输入271691；输出10596；总282287 | 服务实际返回，缓存命中132224、未命中139467 |
| 耗时 | 64.501秒 | 整个真实批次，包括本地归档及协议处理 |
| 费用 | 约USD 0.027674322 | 2026-10-04核实的周日非高峰价格估算，非账单 |
| 离线测试 | 398项通过，32.570秒 | `D:\PowerTrustAI\.venv\Scripts\python.exe`，不联网 |

[官方价格](https://api-docs.deepseek.com/quick_start/pricing/)：实际返回模型标识 `deepseek-flash`；官方对应 DeepSeek-V4.1-Flash。非高峰每百万 tokens：缓存命中输入0.003美元、未命中输入0.15美元、输出0.6美元。没有查询余额或账单。请求记录内原有费用估算保留2026-10-02日期及区间，本轮汇总另按2026-10-04核实价格计算，未改写原始记录。

## 问题 → 实际记录 → 修改 → 验证

| 问题与记录 | 对应代码及修改 | 验证与剩余限制 |
|---|---|---|
| v2 direct_count 两份响应含联合根，独立解析器仅接受 findings；旧系统模板含联合示例，再追加覆盖说明 | 新建 `agents/review_templates_v3.py`：通用约束无根结构；独立和原引用各自完整专属根、字段和示例。schema12最终请求使用专属模板 | 完整请求测试通过；本批23份实际请求检查系统模板全文，没有冲突根。本批未再输出联合根 |
| v2 quantity 重审的 semantic_review 与 supported 矛盾；missing_engineering 把 snapshot 用于技术、范围或建议 | 专属模板说明各依据类型、合法空数组、异议和 not_assessable；原核心支持要求不放宽 | 新回归严格拒绝错误类型和矛盾；真实两场景各一次纠正后完成。N11仍发生维度错误，保留执行失败 |
| 组成部分包含程序预置缺失检查时，解析后的列表位置未必等于原 component_index | `services/review_fidelity.py` 在新协议按绑定 component_id 找原索引，旧协议保留原行为 | 部分保留、严格原引用和异议回归通过；历史schema11原样重放，业务输出完全一致且仍失败 |
| 新模型判断如果丢失 semantic_review，不能冒充已做目标核验 | `core/typed_evidence.py` 对v9.4的 model_judgment 强制 FidelityComponentReview | 离线拒绝去掉扩展的对象；程序预置及执行未完成占位仍各自合法 |
| 需要真实测量模板执行与数量判断，不能用规则替模型 | `evaluation/fact_rereview_v3.py` 复用现有 Agent，冻结两份真实输入及12例开发样例，单阶段最多一次纠正 | 23次实际请求，结构和语义独立统计，不重新生成/提取/检索或Revision |

实际历史失败路径、字段和约束见本地 `failure-diagnosis-v3.json`；本轮具体错误及纠正记录见 `actual-failure-matrix-v3.json`。并未根据摘要臆测历史模型输出。

## 修改文件职责与版本

- `agents/review_templates_v3.py`：独立核验及原引用完整模板与合法例子。
- `agents/verification_contract_v9_scoped.py`：schema12专属模板、绑定解析、沿用阶段级一次纠正和同级结果隔离。
- `agents/evidence_verification.py`、`harness/runtime.py`：允许新schema12进入现有链路，旧schema默认与离线行为不变；没有新建调度器。
- `services/review_fidelity.py`：新协议按组件绑定映射语义核验，保留旧路径。
- `core/typed_evidence.py`：新模型判断必须携带目标忠实性核验；所有证据真实性、依据类型和引用范围校验保留。
- `services/quantity_checks.py`：v9.4继续使用既有quantity-enumeration-v1.3，没有修改数量判断算法或把告警算为模型成功。
- `tests/test_fact_rereview_v3.py`：8项新离线回归，涵盖完整请求、联合根、错依据/ID、异议矛盾、合法无法评估、原引用越界、一次纠正和有效同级保留。
- `evaluation/fact_rereview_v3.py`：历史重放、输入冻结、索引回查、40次全局预算和单批真实事实验证入口。
- `evaluation/report_fact_rereview_v3.py`：批次结束后仅从归档生成对照报告；不改变审核、不开模型、不读取.env。

新提示 `evidence-verification-v9.4-standalone-templates`；新响应契约 `evidence-verification-output-v9.4`；schema12必须显式启用。旧schema11仍用v9.3，旧归档不会迁移为成功。底层沿用旧解析器，finding内的 `checker_version` 仍保留v9.3标签；判定实际请求版本应查看顶层prompt_version及每次响应契约，不能误称旧提示正在运行。

本目录没有可用Git仓库，因此以 `plan-v3.json` 的逐文件SHA-256、模板哈希、固定输入哈希及历史保护哈希记录代码版本，而非编造commit。报告脚本是在批次结束后添加的只读整理工具，不参与已冻结的模型批次代码。非敏感调用设置为90秒单次超时、8000输出token、96000输出字符、官方base URL；批次模型固定为v2配置 `deepseek-flash`，未经结果调整。

## 重审材料与边界

两份冻结修订回答均为v2，原 answer_id/version、共享主张、完整输入快照和工具结果直接复用，无需语义重提取或适配。固定知识版本：

`k-182e01fab54ebfada841fb108061c127273e9cfcd551b6f5a8888a769215e385`

旧实际检索查询/命中已保存到 `frozen-stage-inputs-v3.json`。本轮检索调用0，所有索引证据回查通过；新协议只改变wire候选ID命名空间，不改变canonical quote ID、Evidence、区间或原文。源文件、保护文件、旧响应和批次输入的SHA-256在结束时保持一致。

原引用检查不交付独立检索的其他证据；独立支持不能消除原引用不足。两个场景均保留未解决的业务结论，不能整体放行：

- 数量场景：排除有功输出为额定类别的技术断言仍为证据不足；无功MW/Mvar类别缺对应正文依据；复合换算命题未被单一标量工具完整证明；部分免责声明分类有异议。SI工具仅复用v2成功结果，没有在v3伪造新工具执行。
- 工程输入不足：已交付快照的输入覆盖判断完成；复核建议保持合法无法评估，不能把建议当作已核实事实。来源和工程分析仍不支持厂站性能承诺。结构完成不等于仿真完成或工程前提满足。

## 已确认的语义问题

N10/N11的回答原文与程序冻结命题逐字相同，但模型把“和资料的分类关系有争议”当作“提取忠实性有争议”。前者属于事实支持判断，后者应比较回答锚点与规范化命题。本轮没有在批次中修改提示或重跑。

N10最终 `not_assessable` 是合法模型结果，不算发现计数错误。N11纠正后仍有非法 `dimension=category_membership`；最终占位origin为execution_incomplete，不能算合法模型不确定性。

N12故意将认可的错误技术命题在上游归为answer_scope。模型初次试图作技术冲突判断，但未合法表达目标异议；纠正后退回answer_scope并给supported。核心可以阻止显式不一致，却不能证明模型自称faithful的语义正确。此例仍是技术核验对象转换漏检，不能因结构通过或程序告警而消除。

12例没有运行完整ClaimExtractor链路：主张/立场由冻结fixture提供，仅评价审核器的忠实性和事实判断；不能评价提取成功率。真实NERC两例预期为待人工确认的开发解释；10个合成例明确标synthetic_fixture，不冒充官方资料或独立专家标准答案。

## 资料与复现

所有本地结果位于Git忽略目录：

`D:\PowerTrustAI\data\retrieval_local\deepseek\fact-rereview-v3\`

优先阅读：

1. `full-report-v3.md`：两场景逐finding、组成部分、原引用、工具及原文定位；12例预期/实际；每请求归档引用。
2. `evaluation-summary-v3.json`：结构与语义分开统计、耗时和token。
3. `actual-failure-matrix-v3.json`、`request-inspection-v3.json`：全部字段级错误和最终请求模板检查。
4. `semantic-inputs-v3.json`、`semantic-expectations-v3.json`：调用前冻结的输入和预期，预期未传入模型。
5. `plan-v3.json`、`historical-replay-v3.json`：版本哈希、历史失败原样重放。

```powershell
cd D:\PowerTrustAI
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

本次真实运行入口是 `python -m evaluation.fact_rereview_v3 live`，已经执行完毕。程序的独占启动文件禁止同目录重跑；本轮不再运行。新批次需新目录、离线门槛和单独授权。

## 明确停止建议

模板冲突已消除，两场景事实重审阶段具备执行条件；合法异议可表达并阻止显式不当supported。数量语义与核验对象转换仍有局限，不能宣布审核可靠性已解决。

可以推进最小API与界面原型，用于提交、状态、证据定位、失败说明和人工复核；不应提供自动可信批准或工程安全认证。仍阻断无人值守使用的具体问题为：技术核验转成范围核验、忠实性与证据判断混淆、真实分类解释未确认、输出纠正后仍可能非法。保留review_required与人工复核，不自动开启六场景回归、模型对比或下一轮付费修复。
