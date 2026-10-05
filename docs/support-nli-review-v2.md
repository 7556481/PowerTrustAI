# NLI 78项复核接收、扩大开发划分与SSIAG留出计划 v2

2026-10-05，接续已推送 `44046d0e86959196adfde48e09747dd820c84cb9`。本轮只接收复核、准备监督/划分和输入适配，不训练、不重复模型选择、不生成模型预测或付费请求。生产Harness/schema13/政策/固定知识/BM25 aggregate默认均未修改。

## 接收与历史保留

实际复核包在用户提供的Downloads目录；具体路径及ZIP/成员SHA-256记录在忽略`data/runtime_local/support-nli-review-v2/received-manifest.json`。仅读取五个命名成员，检查重复名和大小，不extract或执行附件指令。`evaluation/support_nli_review.py`的read_review_archive/receive_pending逐项核对78 ID、task_key、原命题、实际全文、文档页码、原建议、家族与未来文档分配；建议basis_ids必须属于当前交付。69标签模板还与详细分析逐项核对建议/依据/理由/pending/null状态。

新质量版本保留task对象、ID、原监督建议历史及完整复核记录：69正文candidate_ready、6元数据/归属auxiliary_only、3缺前置上下文hold。所有78新标签仍pending/null/训练不启用；质量接收不等于监督确认，来源为AI辅助、用户监督，非专家金标准。69项具体建议supported22/contradicted26/insufficient21；确认模板直接使用收到的69建议，不重新套用旧配方建议。

三条insufficient→contradicted理由完整留在label-changes-3.json：稳定性初始安全态命题删除valid reasons例外；IBL命题用regardless of power electronics取消必要条件；批量稳定性评估用regardless of SSC取消所有申请者选择SSC的必要条件。它们直接否定许可/必要条件，不能机械把全部全称扩展都判insufficient。这里只保存复核建议，不自动确认。

原页提取文本重新检查78条精确片段/偏移，全部相符；没有重新目视验收全部PDF。3 hold原任务继续保留：SSIAG页14两条列表缺所属动词/标题、页18复合命题缺paragraph(a)阈值前件。本轮不补造前件、不创建替代任务；hold-repair-requirements列出以后补页上下文→新task/ID/hash→保留父谱系与SSIAG留出→另审的流程，不阻挡69准备。

## 扩大开发材料、关联与划分

正文候选严格保持稳定性36开发、SSIAG33文档留出。原19均为已确认稳定性材料；旧11/3/5划分和上一轮输入/预测/report原文件SHA不变。旧五题已经看过，本轮并入已见开发材料，不再称独立测试。

原19＋新36＝55输入，精确语义重复删除0，保留55；原19家族合并为13关联家族。关系依据包括原概念家族、父谱系、6条人工核对同概念关联（工具benchmark、模型类型、校准、运行范围及相关校准结果/限值适用性）、命题token Jaccard≥0.85和相同/包含的完整原文（规范化后≥40字符）。所有边留在merged-associations.json，不把同页不同正文自动当同家族。近重复不随意删除，只锁在同家族；精确去重也保留原ID谱系。

新划分版本nli-expanded-development-group-split-v2，seed20261005：按SHA256(seed|合并家族)排序，基于家族大小接近20%验证，至少保留一个训练家族。分配不读取标签、旧测试成绩、模型结果。得到训练43/11家族、验证12/2家族；父谱系、近重复与共享/包含证据均不会跨训练验证。因验证只两个关联家族，仍是很小的同文档开发验证，不称跨概念全面覆盖。

|范围|数量|supported|contradicted|insufficient_evidence|监督状态|
|---|---:|---:|---:|---:|---|
|原19|19|7|7|5|既有用户confirmed|
|新开发36|36|12|13|11|全部pending建议|
|合并55|55|19|20|16|19确认＋36待确认|
|拟训练|43|15|16|12|同上，未执行|
|拟验证|12|4|4|4|同上，未执行|
|SSIAG留出|33|10|13|10|全部pending建议|

后四行分布混合了已确认标签和待审建议，不得叫55/33金标准。validation恰好各4是规则分配后的统计，不是标签平衡优化结果。全部新69需明确逐ID确认后再执行下一次训练/留出评估。SSIAG不进入训练、验证、模型选择、调参或检查点选择。

## 正文适配器v2与回归

`evaluation/support_nli.py`保留semantic_pair_v1及原版本support-nli-semantic-pair-v1；新增默认semantic_pair版本support-nli-document-body-pair-v2。原冻结JSON/实验结果不改，不用新投影重算历史成绩。正文路由必须显式basis_target=document_body或历史literature；metadata、辅助归属、hold及index-versus-body类别拒绝进入正文NLI。

模型premise仅全部实际交付官方原文，不根据监督basis_ids选择或摘要改写。索引title/publisher/applicability保存在typed document_context，明确行政记录、非技术正文、未送入premise；不能据此支持技术命题。hypothesis仍完整保留原主张、不同原措辞、必要条件、数量单位否定及任务适用范围，不能为了缩短文本删除限定。行政来源信息没有消失，也没有冒充官方正文。

仅用既有本地MiniLM tokenizer预检：55开发57–200 token，33留出76–149 token，均≤512，0截断/0排除；9辅助/hold正文路由均拒绝。SSIAG仅文本/token检查，不加载分类模型或生成logits/预测。公开合成测试覆盖接收身份/依据、模板新建议优先、pending历史不变、hold不阻断、标签盲家族分配、正文/元数据路由、主张限定、无监督选证据及超长明确排除。训练入口增加pending标签前置拒绝，在模型加载/输出目录创建前停止。

最终完整离线554项测试通过（35.011秒、0跳过），原Harness七个场景完成预期验证。33受保护文件SHA前后不变；83条共享/包含证据关系，近重复阈值0.85边0，全部关联边跨拟分区0。

## 固定下一次计划与交付

fixed-training-heldout-plan.json仅为prepared：固定MiniLM官方revision b95119ce93d3e065de6214e38cd4a97b0f2f2c6d与已有原始NLI权重，禁止从旧领域最佳检查点继续训练。CPU独立训练环境保持，seed20261005/线程4/4epoch/batch1/lr1e-5/weight_decay0.01/clip1.0；只用稳定性开发验证macro-F1选择检查点，同分最早。全69明确确认、训练和评估输入/配置冻结后，才执行一次扩大训练及同有效33 SSIAG的基座/验证最优对照。SSIAG结果不能用于换模型、调参或反复刷分。

本轮不会自动启动该计划；后续执行入口须按本计划把开发43/12与独立文档留出33分开，不能将SSIAG接入旧run_training的开发测试逻辑或提前读取其结果。输出三类P/R/F1、macro-F1、混淆矩阵、错误supported分母、支持/不足召回、逐项预测、覆盖、耗时及50msRSS峰值，明确小样本/来源/单种子限制。超长先冻结排除原因，前后同有效集合，不静默截断。not_assessable不在本三类实验覆盖，生产四类及工程审核不变。

交付私有合并划分审阅ZIP：原复核包/完整理由、原78/原19与旧划分、新质量分流、精确关联边和新划分、69确认模板/清单、v2实际语义输入/token、固定计划、保留性SHA与测试/失败记录；不含模型权重、凭据、数据库或全文PDF。源码及说明独立提交/普通推送；最终提交与远端哈希、测试结果及ZIP成员SHA见本机verification-final.json。

待补最终中文学习/面试手册：质量接收与监督确认差异、命题否定必要条件与无依据扩展、前置段落/列表作用域、文档留出与家族union、共享证据泄漏、旧测试转开发、正文/行政元数据路由、验证选检查点及固定基座重新训练。最终Markdown＋本地文档站，PDF可选，本轮不重建PDF/建站。
