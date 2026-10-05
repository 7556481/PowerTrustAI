# 扩大NLI微调与SSIAG文档留出对照 v3

2026-10-05，接续本地与远端均已核对的 `b4c8b176d737ac614bf464d5d02297540e391854`。按本轮明确授权确认69项具体监督建议，执行唯一一次扩大CPU训练，选定并封存检查点后才对SSIAG进行一次官方基座/微调对照。没有重复模型选择、数据扩充、划分准备、历史实验或DeepSeek调用；生产审核器、Harness/schema13/政策/工程规则/固定知识与默认检索均未改。

## 监督确认和数据冻结

实际读取忽略data/runtime_local/support-nli-review-v2中的69模板、正文材料、55拟开发与33留出及固定计划。新监督版本另存于support-nli-expanded-v3：confirmed-primary-69、confirmation-event、supervision-view-78-v3。逐ID/task_key/label/basis_ids/依据作用域确认；received理由完整写入监督及事件，source保持ai_assisted_user_supervised、reviewer为本机所有者事件，不标专家金标准。调用confirm_authorized复用support_training.confirm_template和scope校验，不把建议依据子集扩大为全部交付。6辅助/3hold仍pending/null，未确认或训练，原pending/旧建议/任务/预测不覆盖。

稳定性原19确认＋新36确认＝55，原固定13关联家族/43训练＋12验证不变；原五题仅已见开发。训练43标签supported15/contradicted16/insufficient12；验证12各4。SSIAG33标签supported10/contradicted13/insufficient10，仅文档留出。新69确认22/26/21，既有19确认7/7/5，不能把本次确认说成专家审定。

训练前冻结监督版本、原任务、固定分配、v2语义输入/token/有效集合、官方revision/全部模型文件、配置、实际解释器/依赖及相关源码SHA。全部88有效、0排除/0截断；开发57–200token，SSIAG76–149，max512。prepare使用完整交付原文，不按监督basis_ids选证据；行政title/publisher/applicability为typed记录不混premise，hypothesis保留立场/原命题/否定/数量/单位/必要条件和任务范围。

## 新入口、门禁和运行记录

`evaluation/support_nli_expanded.py`：confirm_authorized、validate_layout、verify_freeze、match_effective、train_expanded、evaluate_document_holdout、heldout_metrics；复用support_nli的v2投影、严格本地模型加载、predict/evaluate/Resources及既有partition/监督校验。

validate_layout显式分离train/validation/文档留出，拒绝重复ID、文档重叠、跨留出父谱系、错误分区、未确认监督、辅助/hold、变动数量。verify_freeze在两阶段核对输入/源码/模型SHA及固定官方revision；实际加载missing/unexpected/mismatched/error均空，分类头完整保留，实际输出0contradiction→contradicted、1entailment→supported、2neutral→insufficient_evidence。

train阶段只对开发验证调用predict；不产生任何SSIAG预测。所有epoch日志与验证逐项保存，最高macro-F1/同分最早选checkpoint。训练完成写selection-seal（epoch、配置/冻结清单/检查点SHA及heldout预测0）。独立heldout阶段先检查seal及全部SHA，再以同一冻结33有效ID分别加载官方基座/选中checkpoint，每模型一次。training-started/heldout-started使用排他写入，既有输出目录也不复用，避免同一配置自动重复执行。

本轮已实际调用的两个阶段（仅运行记录，不是新一轮授权）：

```powershell
& D:\PowerTrustAI\data\runtime_local\new-machine-restoration\training-env\Scripts\python.exe -m evaluation.support_nli_expanded train --config D:\PowerTrustAI\data\runtime_local\support-nli-expanded-v3\training-config.json
& D:\PowerTrustAI\data\runtime_local\new-machine-restoration\training-env\Scripts\python.exe -m evaluation.support_nli_expanded heldout --config D:\PowerTrustAI\data\runtime_local\support-nli-expanded-v3\training-config.json
```

独立环境复用Python3.13.2、CPU torch2.8.0+cpu/transformers4.57.1/numpy2.3.3/safetensors0.6.2/psutil7.1.0，完整实际依赖锁和executable另存，未重建/安装框架或改项目.venv。实际CIM核对X7-358H/16核16线程、33,873,752,064字节内存、Windows11家庭中文版10.0.26200；不配置NVIDIA CUDA或改驱动。

## 唯一训练和检查点

官方MiniLM原NLI权重，revision b95119ce93d3e065de6214e38cd4a97b0f2f2c6d，实际82,120,707参数；不是旧领域best-checkpoint。冻结CPU线程4/seed20261005/4epochs/batch1/AdamW lr1e-5/weight_decay0.01/clip1.0。

|epoch|平均训练loss|12验证macro-F1|用于选择|
|---|---:|---:|---|
|1|0.601204|0.915344|最高且最早，选中|
|2|0.056194|0.915344|同分，不覆盖|
|3|0.005194|0.915344|同分，不覆盖|
|4|0.002484|0.915344|同分，不覆盖|

训练112.8836秒（包含验证/检查点保存，不含模型加载0.1332秒），进程采样峰值RSS2,911,465,472字节≈2.71GiB。训练loss继续下降，验证macro-F1没有提高，不能据loss接近零宣称泛化可靠。检查点epoch1先封存；以下SSIAG结果不用于任何选型/重训/调参。

## SSIAG33项一次留出结果

|指标|官方原始基座|epoch1微调|
|---|---:|---:|
|macro-F1|0.656914|0.819349|
|accuracy|22/33 = 0.666667|27/33 = 0.818182|
|错误supported / 非supported真值|0/23|4/23|
|supported预测中错误支持|0/5 = 0%|4/14 = 28.57%|
|supported召回|5/10 = 50%|10/10 = 100%|
|insufficient召回|6/10 = 60%|8/10 = 80%|
|有效覆盖|33/33|33/33|
|推理秒|3.0979|3.8054|
|加载秒|0.1287|0.3598|
|进程峰值RSS字节|503,058,432|511,569,920|

两模型三类P/R/F1如下：

|类别|基座P|基座R|基座F1|微调P|微调R|微调F1|
|---|---:|---:|---:|---:|---:|---:|
|supported|1.0000|0.5000|0.6667|0.7143|1.0000|0.8333|
|contradicted|0.6875|0.8462|0.7586|0.9000|0.6923|0.7826|
|insufficient_evidence|0.5000|0.6000|0.5455|0.8889|0.8000|0.8421|

混淆矩阵行是真值、列是预测，顺序supported/contradicted/insufficient_evidence。基座[[5,1,4],[0,11,2],[0,4,6]]；微调[[10,0,0],[3,9,1],[1,1,8]]。复用指标内not_assessable行列全零，不进入本三类macro-F1。逐项logits、token、标签、监督依据与理由在私有审阅包，不公开原输入。

总体F1提高同时错误支持增加，这是实际能力限制，不能概括成审核可靠性提升。19项两模型都对、8项改善、3项退步、3项仍错；错误supported4项中3个是基座正确→微调错误，另1个是基座本已错但进一步给出错误支持。

错误分析重点：微调把MW额定值扩展成充分证明；漏掉影响可忽略的“无不利影响”必要条件；漏掉联合评估SSC选择条件；颠倒咨询与提供结果的时间先后。两个模型仍未识别IBL合取必要条件被删除的直接矛盾，仍把未给出同一精确最低值的扩展判断为矛盾。部分来源归属/单位外推得到改善不能代表整个相关家族可靠。完整逐项理由/原文在error-analysis.json/md，保留失败，不据此再调参。

仅单个SSIAG留出文档33项、小样本、AI辅助用户监督、单种子；开发验证仅2关联家族。资料/任务此前已人工审阅不代表专家金标准；文档留出也不代表独立外部认证。NLI支持三分类不覆盖生产not_assessable、执行账本、工程前提或最终政策。RSS为50ms进程采样及关键点，可能遗漏瞬时峰值；两留出模型在同一独立评估进程顺序加载，RSS不是完全独立子进程比较。未替换生产审核器。

## 验证、交付和停止

执行前完整560项离线测试通过（66.249秒、0跳过），发布前审阅修复后完整561项测试再次通过（35.102秒、0跳过）。原Harness七场景预期验证完成；新增公开synthetic_fixture覆盖确认依据子集、原pending不变、反序模板ID绑定、布局分离/未确认门禁、检查点seal前拒绝留出、token冻结一致及错误支持双分母/混淆矩阵。唯一早期合成fixture重复ID被门禁正确拒绝，已修复fixture，未重跑真实训练；CIM沙箱拒绝后工具授权只读查询成功，无系统配置修改。

77历史/生产文件SHA前后不变，实际输入/监督/配置/分配/官方权重均与原冻结一致。发布前代码审阅修复confirm_authorized的排序假设：事件按sample_id绑定，模板重排也不把理由/历史写到另一个ID，并新增反序模板回归。本次实际69模板顺序一致，逐ID核对及输出未受影响，没有重复确认/训练/留出。执行时源码及测试原字节另存execution-source，对应原冻结SHA；发布源码及测试的新SHA单独保存于post-execution-source-review，原freeze不重写，不能将发布后修复冒充训练时已执行代码。模型加载及数学检查无失败，训练1次、每模型留出评估1次、DeepSeek/付费API0。私有ZIP按允许类型打包监督事件/新确认、冻结配置/分配/输入/源码SHA、epoch记录/逐项预测/logits/指标/错误分析/环境/验证与文件SHA；不含凭据、全文PDF、数据库或权重。最终提交/远端回查与ZIP自身SHA在忽略目录verification-final/review-zip-verification；公开代码/测试/说明独立提交普通推送，不强推，网络仅命令级指定代理。

实验到此停止，不自动续训、换模型或继续扩大候选。下一步应由所有者决定是否另行补独立来源/概念监督和更稳健风险评测，不用这33题继续刷分。长期中文手册待补确认事件/子集作用域、两阶段源码读法、完整投影/token冻结、训练loss与验证、earliest tie、文档留出混淆矩阵手算、错误支持两分母及必要条件/顺序失败；最终Markdown＋本地文档站，PDF可选，本轮不重建整本手册或PDF。
