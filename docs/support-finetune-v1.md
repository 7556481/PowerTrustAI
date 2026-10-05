# 三类支持判断监督、基线与首次微调实验 v1

日期2026-10-05。接续5dcbdb7；生产Harness、schema13、政策、检索默认和旧145项/预测不修改。模型/数据/真实响应全部在忽略目录。本轮仅开发实验，不接入生产审核器。

## 监督与材料

用户明确确认合并模板74项（旧33＋新36＋修订5）的具体建议标签。`support_training.confirm_template`使用模板的suggestion_label/suggestion_basis_ids，不使用样本内部旧建议；保存新事件、逐ID语义task_key、来源/依据/本地用户ID和新监督版本。另保存完整145新视图：74confirmed、71pending；31辅助/40hold不训练，A05辅助、原MW/MVA父任务仍hold。不称专家金标准。没有配置持久复核者注册表，建立明确的`local-user-powertrust-owner`标识。

训练许可采用显式来源白名单，所有交付文档均须通过。2026-10-05再次核对[AEMO许可](https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions)：公开AEMO自有材料可在准确署名下使用，排除保密/他方委托版权材料；本次仅其稳定性指南正文，不使用第三方图。本机清单保留原URL/作者/资料名。NERC许可仍未确认、PNNL本轮未独立清理，训练排除其相关样本；公开下载不等于训练许可。基线开发审核与训练筛选分别记录，不偷偷移除74监督候选。

筛选19项、7家族（7支持/7矛盾/5证据不足），全部来自AEMO同一文档。原筛选子集train14/validation5/test0，因此在模型执行前独立生成新家族划分：固定种子20261005，排序家族后shuffle，60%/20%/剩余，完整家族不拆。训练11/4家族（4支持、4矛盾、3不足）、验证3/1家族、测试5/2家族。原split保存，旧任务/分区不覆盖。新分组检查父子与token Jaccard≥0.9近重复跨集合；共享页面/同文档继续单列。只是资料内开发划分，未形成独立跨文档测试。

## 独立DeepSeek基线

复用原提示/任务协议与连接器，新增执行版本`support-independent-execution-v2`，默认每样本一请求。合同错误、输出错误、消息容量错误、单项超时保留失败/有效部分后继续；鉴权、余额、连接/服务、限流等全局故障或总deadline耗尽停止。每项至多一次格式纠正；不重新排队失败项。超时后复用服务Bundle.drain等底层工作结束再进入下一项，受剩余总运行期限约束，不能把async取消当线程已停止。

74个冻结task-only请求，不含监督/建议/recipe/历史理由。固定90秒单步、7200秒总期限、2000输出token、24000响应字符，完整初始/纠正消息容量240000/720000；148是74×(1+最多1纠正)的结构保护，不是任意付费批次上限、token或费用证明。原提示仍四类兼容，评测按三类监督标签统计，模型not_assessable预测另列矩阵列，不当成功删除。

实际74/74尝试，69有效/5失败，79请求（5纠正），93.596秒、317502token；估算USD0.05053557–0.10107114（2026-10-02连接器价目，非账单）。五样本初始和纠正均选择作用域外basis ID，共10无效响应；不事后修ID放行或把它计为语义错误/正确。全部79响应SHA与实际task核对，其他样本继续。

|监督标签|预测支持|预测矛盾|预测不足|未完成|
|---|---:|---:|---:|---:|
|supported|32|0|0|0|
|contradicted|0|20|0|2|
|insufficient_evidence|3|7|7|3|

有效69分母：supported P/R/F1=0.9143/1/0.9552，contradicted=0.7407/1/0.8511，insufficient_evidence=1/0.4118/0.5833，三类macro-F1=0.7965。错误supported=3/37有效非支持真值（3/35支持预测），5未完成仍单列；正确59/69、全74中完成且正确59/74，不冒充通用准确率。结构覆盖69/74=93.24%；原始/构造/修订与任务类型分层保存在baseline-strata，不把不同任务混称一项质量保证。

历史5预测保留，其中1条完整任务/协议相同可用于这74项，但本轮选择全部新跑一次，历史复用0，旧预测另列，不借父预测给修订。每样本checkpoint保留实际调用记录和失败，原消息/响应经既有ResponseDiagnostics保存到data/retrieval_local。首次准备误用runtime_local诊断路径，被既有安全检查拒绝：实际0调用，原冻结目录保留；随后新目录启动唯一付费批次，不把准备失败称付费重跑。实际阶段请求、用量、费用及指标以本机final-report/verification为准，不预写成功。

## 本机训练与固定配置

实际硬件i5-9300H（4核/8线程）、约8GB内存、GTX1650 4GB/驱动462.30；D盘约942GB空闲。独立CPU版torch报告cuda_available=false，不宣称当前CUDA已验证可用。采用[Google BERT-Tiny](https://huggingface.co/google/bert_uncased_L-2_H-128_A-2)：Apache-2.0，英语小型预训练编码器，两层/128维/512位置，可合理在本机CPU训练；不为4GB旧驱动强行LoRA。固定revision `30b0a37ccaaa32f332884b96992754e246e48c5f`，下载匿名/无远端代码，safetensors约17.7MB，分类模型4,386,307参数。

独立环境在忽略目录，Python3.13.2、torch2.8.0+cpu、transformers4.57.1/numpy2.3.3/safetensors0.6.2/psutil7.1.0，实际全部依赖freeze另存。项目.venv不安装训练依赖。复现：

```powershell
& .\.venv\Scripts\python.exe -m venv data/runtime_local/NEW-training-env
& .\data\runtime_local\NEW-training-env\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.8.0
& .\data\runtime_local\NEW-training-env\Scripts\python.exe -m pip install transformers==4.57.1 numpy==2.3.3 safetensors==0.6.2 psutil==7.1.0
& .\data\runtime_local\NEW-training-env\Scripts\python.exe -m evaluation.support_training --config YOUR_FROZEN_CONFIG.json
```

参数配置使用服务端/实验CLI路径，不新增普通API路径输入。材料筛选/确认可复用本模块函数，配置里的output必须新目录。模型文件须先下载到本机并固定revision，训练仅local_files_only，普通服务启动不会下载。

三类supported/contradicted/insufficient_evidence；不冒充四分类生产审核器。完整claim立场/限定/适用性与整条Evidence进入固定text_pair-v2；只消除与proposition完全相同的text/answer_excerpt重复，不截断原文。v1长度预检406–614，6项超窗；去冗余后所有19项406–490token，0排除。模型原生uncased WordPiece处理前后相同，不改生产解析文本。

一次全参数CPU轻量分类微调：seed20261005、2线程、batch1、AdamW lr5e-5/weight_decay0.01、梯度范数≤1、12epoch。验证macro-F1严格更好时选检查点，平分取最早；第3epoch被选中。测试同5项，初始模型一次、最终检查点一次，不据测试调参或再训练。初始模型是**相同预训练编码器＋固定种子随机三分类头**，不是已训练NLI审核器；checkpoint警告与该事实保留。分类头只输出类别，不生成经过审核的依据选择或修订，不自动接生产。

## 实际训练结果与限制

训练12.505秒，峰值进程RSS442,585,088字节（约422MiB，进程测量不等于整机峰值）。5/5测试输入/输出有效，前后相同评测集合、0截断/排除；初始/最终accuracy均2/5，三类macro-F1为0.190476→0.222222。错误supported由3/3非支持真值→1/3，但支持召回由2/2→0/2，证据不足召回均0/1。不将极小开发集的分数差称可靠收益，DeepSeek单独报告。

|类别|初始P/R/F1|微调后P/R/F1|测试监督项|
|---|---|---|---:|
|supported|0.4 / 1 / 0.5714|0 / 0 / 0|2|
|contradicted|0 / 0 / 0|0.5 / 1 / 0.6667|2|
|insufficient_evidence|0 / 0 / 0|0 / 0 / 0|1|

数据/模型/配置/实际报告：`data/runtime_local/support-finetune-v1/`。confirmed-primary、confirmation-event、source-filter、partition-plan、training-materials-v1/v2、training-config、model-revision、training-environment-lock、training-run-v1/initial-model/best-checkpoint/report、token预检及测试日志。诊断响应仅既有忽略根；私有材料不提交。

已完成最小可运行训练，不是被“尚不完美”阻断；下一步需更多独立家族/文档的用户监督标签、有效not_assessable任务、更多许可明确材料与更强且许可清楚的支持判断基座，保留本次失败作开发样本线索，不能直接把新模型自评当真值。任何扩大训练或替换生产都另行冻结评测，不在本轮自动开启。
