# 审核可靠性修复 v1

本轮只修复主张定位、输入语境、依据类别、标量单位工具和交付范围。默认检索、切分、四 Agent、确定性审核策略、旧目录未调整。真实结果不能标为整体审核通过。

## 修改文件与职责

|文件|职责|
|---|---|
|`services/answer_anchors.py`、`services/claim_extractor.py`|atomic-claims-v5/v6：模型选择版本绑定段落锚点，程序计算逐字区间；规范化 proposition/semantic_qualifiers 与原文分开；记录 assertion_role 与完整上下文|
|`services/answer_basis_targets.py`|v6 显式模型依据目标与类别一致性校验；不把类别当正确性证明|
|`core/models.py`、`agents/contracts.py`、`harness/contracts.py`|显式扩展类型；保留旧数据类字段形状与旧归档兼容；新增语境主张、计算依据、真实工具及交付记录|
|`core/validation.py`、`core/typed_evidence.py`|严格字段/ID/版本/组件依据约束；计算只支持完整白名单标量关系；不降低文献支持要求|
|`agents/verification_contract_v9.py`、`agents/verification_contract_v5.py`|事实审核 v9.1；`agents/verification_contract_v9_scoped.py`提供可选v9.2单命名空间请求；独立核验与原引用使用各自目录；模型只选已有ID；完整目录校验；部分合法同级结果保留；实际快照正文交付与缺失前提分开|
|`agents/domain_contract_v3.py`、`agents/power_domain_review.py`|领域 v3 固定 prerequisite 数组；完成状态与缺失前提一致；保留演示规则、未仿真边界和输入语境|
|`services/quantity_checks.py`|v1.2 有限枚举核对；三类 rating 与其他影响量分开；转述语法与主张角色共同确认，否则检查未完成|
|`tools/unit_conversion.py`、`harness/runtime.py`|真实 SI 标量换算、输入/输出/规则/状态/结果ID；接入预算与轨迹，不能跨物理量类别换算或证明稳定|
|`evaluation/archive_replay.py`、`evaluation/reliability_archive_audit.py`|原协议恢复/88响应离线重放；扩展类型严格恢复，不迁移历史失败|
|`evaluation/reliability_trial.py`、`evaluation/reliability_repair.py`|冻结六场景、调用预算、版本隔离；独立有限修订验证，不自动反复运行|
|`evaluation/reliability_report.py`|离线逐阶段、逐finding、依据和费用报告；无模型调用|
|`services/structured_model.py`、`services/response_diagnostics.py`|批次结束后补齐未来逐请求消息预归档；只保存角色/正文，不保存鉴权、请求头、服务设置；此改动仅离线验证|
|`tests/test_review_reliability.py`|21项开发回归：精确锚点/共享区间、转述、枚举、单位、元数据、交付不足、原引用范围、部分失败、工具预算、长正文目录、安全消息归档|

## 协议与迁移边界

生成 v3、修订 v2、检索契约和 offline-policy-v1 不变。新主张 v5/v6、事实审核 v9.1/v9.2、领域审核 v3、数量规则 v1.2、单位规则 scalar-si-conversion-v1 显式选择。默认构造参数仍保留旧离线/旧协议行为。新类型通过已注册的扩展类恢复，未知字段和未知类型拒绝。

主张角色和规范化限定由模型判断，并非程序已经证明；用户陈述只是用户提供的数据。合法共享段落锚点不证明原子拆分完整，未覆盖内容明确保存。

完整生成快照保存和审核实际收到正文是两个事实。首版全文交付上限32000字符，超限只交付元数据/哈希并由程序拒绝该覆盖判断；检索省略按实际预算记录。索引 applicability/source_type 是维护信息，不能冒充官方 PDF 句子。

工具只使用明确标量与同一白名单物理量类别内的 SI 前缀换算。`230 kV = 230000 V` 具有可校验工具依据；无功被写成 MW 不能自动改成 Mvar。复合物理命题不能因含有两个单位数字就仅用换算结果通过。

## 真实结果与版本

全部结果在 Git 忽略的 `data/retrieval_local/deepseek/`：

- `reliability-v1/`：v9 首批28请求；确认长正文目录程序缺陷，失败保留。
- `reliability-v1-patch1/`：v9.1 六场景初审23请求，复用成功生成；修订前恢复边界错误，中止并保存。
- `reliability-v1-repair1/`：从 canonical JSON 恢复地区场景，1次修订与完整重审5请求；事实重审仍失败。

- `reliability-v1-followup1/`：追加授权后13请求；提取与领域有效，schema10输入接线失败。
- `reliability-v1-followup2/`：接线修复后66请求；最终六场景初审5/6完整、五次修订、两次完整重审。

累计135请求，用户追加授权后原60上限解除。最终固定批次上限160，最坏154，未反复试到通过。普通测试不调用API。不能合并成同版本实验或语义准确率。最终提取6/6、事实初审5/6、领域初审6/6；修订5次，完整重审2/5。完整执行但需人工复核，与契约失败、证据不足、工程输入缺失分开报告。

已有请求保存了实际 Agent 输入、候选/交付 payload、响应与校验错误。完整 system/user 消息未全部按请求单存，不能声称已获得请求时完整消息归档；结束后补齐消息归档，追加授权后的新请求已真实使用；前期记录不伪造补为请求时归档。历史无法由后续检索补成生成输入。

## 运行

```powershell
Set-Location D:\PowerTrustAI
.\.venv\Scripts\python.exe -m unittest discover -q
```

离线88归档重放使用新目录，拒绝覆盖已有结果：

```powershell
.\.venv\Scripts\python.exe -m evaluation.reliability_archive_audit --output-dir data/retrieval_local/deepseek/reliability-replay-new
```

新真实批次需独立目录、冻结代码及通过离线验证；以下仅作复现说明，本轮已结束，不自动执行：

```powershell
$batch = 'D:\PowerTrustAI\data\retrieval_local\deepseek\reliability-independent-new'
.\.venv\Scripts\python.exe -m evaluation.reliability_trial prepare --output-dir $batch --cap 160 --claim-protocol 6 --verification-protocol 10 --reuse-generations data/retrieval_local/deepseek/reliability-v1 --prior-calls 135
if ($LASTEXITCODE -ne 0) { throw 'Prepare failed' }
.\.venv\Scripts\python.exe -m unittest discover -q
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
$plan = Get-Content -LiteralPath "$batch\plan-v1.json" -Raw | ConvertFrom-Json
@{ passed = $true; source_sha256 = $plan.source_sha256; interpreter = 'D:\PowerTrustAI\.venv\Scripts\python.exe' } |
  ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$batch\offline-validated-v1.json" -Encoding utf8
.\.venv\Scripts\python.exe -m evaluation.reliability_trial live --output-dir $batch
```

程序加载项目 `.env` 仅鉴权。不要显示文件内容、密钥、请求头；不使用 SDK 隐式重试。已开始目录拒绝再启动。并发仍限于现有双审；SQLite同步检索沿用线程隔离，异步取消不代表底层线程被强制结束。

## 限制

真实类别/依据混淆（含把技术数量改写为answer_scope）、索引元数据误归属、千位逗号与单位复合主张表达、概念问答被演示规则要求工程前提等问题仍存在。严格拒绝避免了错误放行，但不能用严格校验替代有效语义判断。模型局部 supported 不代表整体完成或工程安全；本轮未使用新的检索实验、微调或仿真。

最终378项离线测试通过（47.310s），普通测试不联网。人类阅读入口：`data/retrieval_local/deepseek/reliability-v1-followup2/reading-notes-v1.md`，完整账本与六场景报告同目录。所有历史记录、原PDF全文及私有派生报告均未提交到Git。
