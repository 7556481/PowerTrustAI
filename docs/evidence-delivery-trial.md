# 证据交付开发实验

默认检索和四 Agent 输出协议保持不变。复用原相邻上下文读取，增加可选 `cross_page_next_first`，在原字符/片段预算内优先交付已有物理下一页邻居。默认仍为 `storage_order`。它不恢复表格、不判定语义续接，也不代表事实支持。

2026-10-03 真实记录：`data/retrieval_local/deepseek/evidence-delivery-v1/`。六场景、两分支，共88次实际 DeepSeek 请求，全部正文、完整输入、响应、纠正错误与轨迹保存在 Git 忽略目录。最多312次预检上限，实际未追加重跑。领域规则是演示规则，没有工程仿真。

初始真实回答在两分支间冻结共享；初次有效提取也共享。数量和地区案例在真实生成之后使用明确标记的构造错误，真实生成结果单独保留。修订分支都重新提取并完整独立双审核。没有运行真实审核的部分不得称为完成。

本轮不采用实验优先策略。实际初次审核中各分支上下文**集合相同**，部分只是顺序变化；没有新增交付必要证据的收益。初次双审完成基线3/6、实验5/6，必需闭环完成基线3/6、实验2/6；单次模型波动和协议失败不能归因为上下文收益或退步。详细语义问题见本地 reading-notes-v1.md。

## 新目录复现（会付费）

不要再次运行已存在的实验目录。以下命令使用新目录，程序加载项目根 `.env`，不输出密钥。

```powershell
Set-Location D:\PowerTrustAI
.\.venv\Scripts\python.exe -m evaluation.evidence_delivery_trial plan --output-dir data/retrieval_local/deepseek/evidence-delivery-new
# 阅读 plan.json 中固定配置、各阶段上限之后启动：
.\.venv\Scripts\python.exe -m evaluation.evidence_delivery_trial live --output-dir data/retrieval_local/deepseek/evidence-delivery-new
.\.venv\Scripts\python.exe -m evaluation.evidence_delivery_report --output-dir data/retrieval_local/deepseek/evidence-delivery-new
.\.venv\Scripts\python.exe -m evaluation.evidence_delivery_analysis --output-dir data/retrieval_local/deepseek/evidence-delivery-new --version v1
```

## 已完成批次的离线检查

已有报告使用排他创建，不覆盖。进一步分析需要使用未使用过的版本名；不读取 `.env`、不调用 API。

```powershell
.\.venv\Scripts\python.exe -m evaluation.evidence_delivery_analysis --output-dir data/retrieval_local/deepseek/evidence-delivery-v1 --version offline-review-new
.\.venv\Scripts\python.exe -m unittest discover -q
```

## 修改职责

- `rag/contracts.py`：在现有 ContextOptions 末尾增加可选优先级，原参数及默认行为兼容。
- `rag/context.py`：只重排既有邻接候选，然后执行原有整片段预算、去重与定位约束。
- `harness/retrieval.py`：验证优先级、预算缩减时保留所选优先级；不修改调度。
- `evaluation/evidence_delivery_trial.py`：实验编排、分阶段最坏请求预检、原 Agent 输入归档与冻结配对；所有审核复用既有 Harness。为了共享初始回答/提取，修订阶段沿用现有有限修订服务调用方式，不新建生产调度器。
- `evaluation/evidence_delivery_report.py`：离线回查、阶段/字符/token成本与逐发现报告。
- `evaluation/evidence_delivery_analysis.py`：真实提取响应离线重放、实际候选集合/顺序对照。
- `tests/test_evidence_delivery.py`：入口构造、未知策略、版本绑定、调用上限和跨页预算选择行为。

## 已确认限制

预算省略保存在运行记录，但尚未将全部省略原因显式交付审核提示词。完整生成快照保存原文，核验使用的投影正文只有哈希；模型不能据此判断整个原始输入的语义覆盖。没有补齐缺失页条件；物理邻接不是完整依据组合。上述限制已报告，本轮没有借机修改审核协议。

后续应先离线处理已有主张类别、摘录覆盖及审核依据不一致的问题，再针对确实因预算丢失的条件设计一次证据交付实验。不要依据本轮单次完成率差异切换默认配置。
