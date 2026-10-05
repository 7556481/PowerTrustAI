# NLI基座比较与一次领域微调 v1

2026-10-05，接续实际代码基线 `27ec89858480cd92c00e48ffa3bdc5f315936894`。本轮为离线CPU开发实验，不接生产审核器；未重复迁移、74监督确认、BERT-Tiny训练或付费DeepSeek基线，付费调用为0。公开实现随本说明独立提交，最终提交/远端/审阅ZIP哈希记录在忽略目录的verification-final.json。

## 当前实现与边界

生产可运行四Agent Harness、有限一次Revision、schema13事实审核、领域协议4、Revision协议2、Evidence原文定位、SQLite历史回查及可选逐主张/语义检索。固定知识、BM25/aggregate是默认。本轮未修改backend、harness、schema、政策、检索默认、知识索引或演示数据库。此前首次BERT-Tiny实验已完成但初始随机分类头不具备NLI能力；本轮保留官方已训练NLI分类头。

74标签来源是AI辅助、用户监督，非专家金标准。仅复用已许可筛选19 AEMO材料和原11训练/3验证/5测试、7家族；辅助和hold排除。五项测试此前已查看、同文档，是开发对照，非独立验收。

## 两候选与事前规则

规则在比较前写入selection-plan.json：最多两候选，不读取test预测；完整14训练/验证输入均可处理，分类头完整加载，CPU单步损失有限，峰值RSS低于20GiB，单步少于180秒、单项推理少于30秒。可行候选依次比较验证macro-F1（高优先）、错误supported（低优先）、验证推理耗时（低优先）、实际参数量（低优先）。训练集指标仅诊断，不用于选模型。每候选单步探针模型丢弃，实际训练从固定官方权重重新加载。

|候选|官方许可 / revision|实际参数量|safetensors字节|上下文|输出顺序0/1/2|
|---|---|---:|---:|---:|---|
|cross-encoder/nli-MiniLM2-L6-H768|Apache-2.0 / b95119ce93d3e065de6214e38cd4a97b0f2f2c6d|82,120,707|328,499,560|512|contradiction/entailment/neutral|
|FacebookAI/roberta-large-mnli|MIT / 2a8f12d27941090092df78e4ba6f0928eb5eac98|355,362,819|1,425,698,116|512|CONTRADICTION/NEUTRAL/ENTAILMENT|

官方卡片：[MiniLM](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768)、[RoBERTa MNLI](https://huggingface.co/FacebookAI/roberta-large-mnli)。前者SNLI/MultiNLI、后者MNLI已训练分类器；不以参数量推定领域质量。按实际配置核对映射entailment→supported、contradiction→contradicted、neutral→insufficient_evidence；不等于生产四分类，不覆盖not_assessable。

|候选|训练macro-F1|验证macro-F1|验证错误supported|验证3项秒|单步秒|进程峰值RSS GiB|
|---|---:|---:|---:|---:|---:|---:|
|MiniLM|0.6111|0.5556|0|0.1566|0.6688|1.84|
|RoBERTa|0.5758|0.5556|0|0.8732|2.3962|6.09|

两者均可行，验证质量及错误supported打平，规则据耗时选择MiniLM。不能据三条验证认定两者普遍等效。下载文件大小/官方SHA-256逐项核对，RoBERTa一次下载超时后验证Content-Range续传成功；失败记录保留。

## 输入与源码入口

`evaluation/support_nli.py`：semantic_pair、output_mapping、load_model、prepare、run_comparison、run_training。适配器版本support-nli-semantic-pair-v1。premise包含全部实际交付原文，保持原文字句、否定、单位、条件及顺序，不用监督basis_ids选证据。文档归属/索引适用性单独声明为行政上下文，不能冒充官方正文；hypothesis保留原命题、不同原措辞、必要限定与任务范围。URL、哈希、ID、定位与JSON不作语义正文。当前只接受已实现的asserted立场、事实/原引用支持任务，其他依据或立场显式拒绝。

完整token长度预检，truncation=False；超长明确排除，不静默截断。比较14项114–166 token，最终19项114–188，全部有效、0排除。检查输入身份、完整家族划分、监督来源；公开synthetic测试验证无标签选证据、正文完整、元数据隔离、标签顺序、超长处理等边界。

`evaluation/support_nli_candidates.py`：exact_anchor保留原始页文本字符偏移；validate_pending检查原文SHA/定位、pending状态、不进训练、任务新身份、近重复及父谱系不跨未来分区。`tests/test_support_nli.py`和`tests/test_support_nli_candidates.py`为公开合成回归，无公开私有原文/标签。

## 唯一实际训练与开发对照

独立训练解释器 `D:\PowerTrustAI\data\runtime_local\new-machine-restoration\training-env\Scripts\python.exe`，Python3.13.2；CPU torch2.8.0+cpu、transformers4.57.1、numpy2.3.3、safetensors0.6.2、psutil7.1.0，实际完整依赖另存锁定记录。X7-358H、32GB内存，线程4；不改项目.venv、驱动或GPU框架。

一次冻结：seed20261005，4 epoch，batch1，AdamW lr1e-5、weight_decay0.01、clip1.0；最高验证macro-F1选检查点，同分取最早。四轮验证0.2222/0.2222/0.5556/0.5556，选epoch3。没有按测试调参、换划分、重跑或换基座。训练14.2404秒（含验证/保存），前测0.2761秒、后测0.2581秒，进程峰值RSS2.70GiB（50ms采样及关键点采样，不等于精确操作系统瞬时峰值）。

|类别|前P|前R|前F1|后P/R/F1|测试标签数|
|---|---:|---:|---:|---:|---:|
|supported|1.0000|0.5000|0.6667|1.0000|2|
|contradicted|0.6667|1.0000|0.8000|1.0000|2|
|insufficient_evidence|1.0000|1.0000|1.0000|1.0000|1|

macro-F1 0.8222→1.0000；accuracy4/5→5/5；错误supported均0/3非支持项，支持召回1/2→2/2，证据不足召回1/1→1/1，覆盖均5/5。行/列顺序S/C/I，前混淆矩阵[[1,1,0],[0,2,0],[0,0,1]]，后[[2,0,0],[0,2,0],[0,0,1]]。机器指标复用四标签计数结构，其中not_assessable全零，不纳入本轮三类macro-F1。逐项预测、logits、token及原文均在私有审阅包。小样本、已见测试、同文档、单种子限制保留；不宣称生产可靠性或跨文档泛化，不采用为生产审核器。

## 下一批监督候选

实际78项、26概念家族、2官方文档，全部pending/label=null/training_eligible=false，模型预测0。稳定性指南v3是既有开发文档，SSIAGv2.2是新文档；没有使用此前隔离预留文档。先固定文档/家族划分：稳定性新增候选future_training_development，SSIAG候选future_document_heldout_evaluation_review，父谱系共享正文保持同分区。划分不是许可训练或调参授权。

原文、页码、字符偏移、PDF/片段SHA、来源署名、必要条件及父谱系完整保留。覆盖直接冲突/无依据全称扩展、条件删除、MW/MVA类别、SCR例子、否定、来源和索引/正文区别。不是26个全部独立新知识家族：稳定性部分复用既有概念；与原19命题token Jaccard≥0.7有1对，单独列入待审。新候选内部≥0.9近重复对0，原任务ID复用0，不用近重复凑数。

[AEMO公共材料权限](https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions)允许署名使用其自有公开材料，排除保密、委托/第三方版权内容；本轮仅自有正文，不取图表、IEEE附录或外部定义作为新增训练许可。官方来源记录/日期/PDF哈希保留。78精确页文本锚点通过；两页（SSIAG8、稳定性10）实际渲染目视核对，其余未逐页目视检查，不把文本检查冒充全PDF视觉验证。

候选审阅输入104–247 token、0超长。4项publisher元数据任务用单独pending-metadata-review-pair-v1显示publisher声明；它仅供待审展示，未用于本轮训练/预测，不回改冻结适配器。其余使用原适配器。AI建议仅复核提示，不确认标签；new-label-template.json供所有者另行审阅，candidate-review.html可本地阅读，未搭建长期文档站。

## 验证、交付与待补

最终完整离线546项测试通过（35.117秒、0跳过），原Harness演示七个既定场景完成，包含预期契约失败路径；详细结果见本机verification-final.json和日志。已有监督/材料划分与backend/harness共28文件前后SHA一致，演示服务不参与本轮、未读写其数据库。必要代码/合成测试/说明提交，私有资料保持忽略。

审阅ZIP只按允许列表收集实际语义输入/token、固定revision/许可/config/tokenizer元数据、规则/冻结配置、训练日志/预测/指标、候选/标签模板/来源/失败说明及SHA清单；不含模型权重、完整数据库、凭据或密钥。完整PDF留本机，包内提供选段和官方原件链接。首次模型超时、PDF渲染缺库后的工具回退、合成测试夹具错误及审阅脚本导入路径错误均如实记录，未因此重跑实验。

下一步：所有者审阅78新候选、清理概念重用并保持文档留出；补更多独立来源、not_assessable及工程不可评估机制、多种子/外部验证另行授权后开展。长期手册待补NLI语义映射、加载分类头证明、训练/验证/测试隔离、三类手算混淆矩阵、资源测量、同文档过拟合与元数据依据作用域；结合实际源码教学，最终Markdown＋本地文档站，PDF可选。本轮不建站、不重写38页阶段手册。
