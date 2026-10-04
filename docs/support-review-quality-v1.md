# 91项监督审阅接收与新增候选质量检查 v1

2026-10-05，接续da4288b。用户提供PowerTrustAI-support-review-91-v1.zip并声明已监督审阅。附件仍保留审阅时的pending/confirmed_count=0，作为不可改写的来源；用户监督报告与逐样本标签确认是不同事件。禁止整包自动确认，33项是优先候选，29辅助按任务类型单列，29hold不进训练。

## 实际接收与核对

`evaluation/support_review_quality.py`只读指定ZIP的report/analysis两个成员，容量有界，不extractall，不执行附件中的命令。逐项核对原审阅包SHA、91唯一ID/实际task哈希、任务类型、家族/分区及依据ID范围；source包与旧4599438d…哈希一致，33/29/29及91覆盖通过。新导入版本不改变任何原task、监督建议或基线。逐项标签确认必须有明确selection（ID、task_sha256、label、basis_ids、reviewer_id），仅选择candidate_ready；不存在confirm-all开关。用户可以显式纠正AI建议，但改变标签/依据时须有理由，依据仍限原任务作用域；不能把AI建议设成不可纠正真值。

优先33：28factual_support＋5original_citation_support；建议supported16/insufficient_evidence12/contradicted5，保持原引用作用域。辅助29：input_or_metadata_support15、factual_support5、engineering_prerequisite7、scalar_calculation2；其中5项虽旧类型叫factual，审阅语义属于辅助，不能仅按旧字段混入主任务训练。hold29：18事实、8输入/元数据、1工程前提、2计算；缺快照/原proposal/执行账本的继续保留，不凭回答自述修补历史输入。

本次默认导入0标签确认；附件分类已接收为用户监督报告，33具体标签的确认范围另向用户核实。用户若明确确认33具体标签，则用逐IDselection另建监督版本，既不确认其余58项也不改旧包。若只确认分流结论，继续保留33为优先待确认。该状态以本机verification中的确认事件为准，不把附件pending覆盖成专家金标准。

重要修正：首次导入曾把全部quality_flags当阻断，错误拒绝有效ready样本；实际7项ready携带证据不足原因（地区来源地位、metadata非原文、原引用部分支持、全称范围缺依据）。现在区分损坏任务的阻断问题与有效abstention样本的原因告警。**程序告警不自动等于语义错误或必须删除样本。**公开回归保留这一边界。

## 对新增48项实际逐项应用

没有用变体配方确定标签；逐项比较实际主张、交付原文、限定、对象、任务类型与归属。结果36优先候选、1辅助标量边界、11hold，全部新增标签仍pending。36优先建议11支持/17矛盾/8不足；辅助1项的strict greater-than比较建议矛盾，不是能力/安全判断。11hold撤回直接标签建议，原生成建议仍存在冻结历史中。

发现及处理示例：

- 辅助设备“可以任意省略”与原in-service要求直接相反，新建议contradicted，未机械继承原配方的insufficient。
- “may include五类曲线”变“exactly five强制设备”缺类别/穷尽/必装依据；不因改数量自动判矛盾。
- 单个总分与独立稳定机制advice不是简单同义，保持证据不足建议，不机械翻转。
- >20MW是否满足>20MVA铭牌门槛缺“运行有功还是额定值”等定义；不能因为单位名不同就直接指定真假。
- 三项特定设备/实际厂站对象未定义、缺工程输入，先hold，不能按missing_engineering_inputs配方机械定not_assessable。
- 工具benchmark要求不证明每个工具已经benchmark；一般校准条件不证明某未提供厂站已获机构决定。
- 裸祈使句、this standard/The examples指代缺明确核验对象；正文元数据不能冒充已交付上下文。

创建6个修订任务：明确MOD来源/条款对象的首次验证、单机阈值、调相机类型、辅助设备要求、MVA条文门槛，以及补交Appendix D上下文的模型例子。每个实际task、sample_id/task哈希都更新，parent/原家族/分区保留；所有新标签与建议为空pending，清除旧模型观察/预测/监督标签，以source_origin保留原谱系。原48任务和两个冻结版本及ZIP未修改。5条旧有效预测在原91冻结任务中可用，新6中可用0；不沿parent搬用预测，不调用API。

新6依据均通过同一开发KnowledgeStore回查，引用原文/范围重新验证；补上下文来自已有页的实际提取文本，不修饰原文、不新下载资料。旧91 hold没有强行修完，缺原输入/执行记录的先形成修复需求，不能编造快照或重算后冒充历史工具结果。

## 运行与材料

```powershell
& .\.venv\Scripts\python.exe -m evaluation.support_review_quality --dataset <原dataset.json> --review-zip <用户ZIP> --source-zip <原审阅包ZIP> --output <全新目录>
# 仅有明确逐项监督确认时，追加 --confirmed-selection <逐ID确认.json>
& .\.venv\Scripts\python.exe -m unittest tests.test_support_review_quality -v
```

修订API为`amend_task(sample,new_task,reason=...)`，不改生产协议；必须有实际task改变，不接受只改元数据伪装新任务。预测复用`prediction_scope`核对实际task全JSON哈希，不能只靠parent或ID名称。来源/修订任务/原文在忽略data；公共测试仅synthetic_fixture。

本机`data/runtime_local/support-review-quality-v1/`包含`import-pending-v1/v2/`三个分流、原审阅报告、48项质量MD/JSON、`amended-tasks-v1/v2.json`/`amended-review-v1/v2/`、`prediction-scope-check.json`、`quality-supplement-v3.zip`及verification/reading-notes/测试日志。修订v2仅明示监督方法withheld，六个task/ID/哈希与v1一致，两版本保留。最终import-pending-v2关闭hold/辅助的主任务eligibility；`expansion-quality-dataset-v1.json`实际应用独立建议与门控，保存prior_supervision，48 task哈希不变。新ZIP包含这份质量视图/待审表及6新任务，原用户ZIP未修改，不替代旧监督包。

8项新公开回归涵盖不自动确认、显式选择、hold主训练门控、源包/错ID/哈希/依据作用域、重复记录、修订新身份与清除旧标签/备注、parent预测隔离，以及有效不足原因告警与阻断问题分开。首次测试夹具缺group_id导致1错误，补明synthetic分组后通过，未减少断言。AI质量层不能撤销既有confirmed/disputed监督。没有付费调用、训练、生产审核变更或PDF重建；最终全量测试、确认范围及普通推送记录以本机verification为准。
