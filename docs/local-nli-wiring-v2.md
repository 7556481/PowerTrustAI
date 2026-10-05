# 本地NLI真实接线验证 v2

2026-10-05，接续787dfc1e26a6d5494699dcfc3f0ccd1f16839a85。本轮执行唯一一次正常已有回答真实审核，并将事实Agent与本地epoch1 NLI关联到同run/answer版本/claim/component/knowledge。未训练/补标/换模型/改政策。BM25/aggregate及NLI关闭的代码默认保持；本轮独立服务明确per_claim_v1、NLI启用、top1/不扩相邻片段，不默认为生产配置。

## 接线核对与必要修复

实际生产ObligationClaim的component_basis_targets是按components同序保存的字符串数组，component_obligations也是同序数组；per_claim_v1原harness.fact_retrieval产生fact_bindings，body检索outcome为hits/empty、其他依据existing_basis_type、故障独立标记。verification.delivery_summary保存同一RetrievalRecord的序列化fact_bindings；whole_fragment候选由程序生成，不是模型选的basis子集。核对原回答/版本、claim/component、knowledge及实际全文，不能用当前索引或总运行pool替代丢失交付。

发现并纠正的类型问题：Core Evidence合法provenance:null，原support_nli元数据读取误触发AttributeError，导致旁路批次没有保存结果；现只将该可选行政对象读为空，不填作者/出处、不改正文，原输入metadata/null和task身份保留。这是类型读取问题，不是历史正文缺失。旧16记录只读v1/v2对照另存，缺typed目标/组件映射等仍拒绝，没有历史模型补算。

当前ClaimComponent没有独立原文span。v1给每组件拼整个claim.text，会把混合句其他组件带入hypothesis。保留production_frames_v1旧转换，新增默认production_frames版本local-nli-production-conversion-v2：只有唯一单组件父锚点、实际answer.text[start:end]等于claim.text、不与其他claim共享原文锚点、核验与提取同一claim、唯一当前组件review且fidelity faithful/asserted/technical_truth，才接受原文。绑定类型unique_single_component_parent_span记录offset/原文SHA/身份；归一化faithful仍是模型判断，不自动证明语义原子性。

多组件混合句没有独立组件原文绑定时mixed_component_literal_binding_missing；多claim共享父原文时shared_parent_anchor_without_component_literal_binding，均skipped，不靠字符串查找猜切子句。原支持类型/精确交付/完整候选/版本知识/未截断门禁仍保留，目标到诊断body的映射不改变原事实协议或支持标准。

## 真正的离线贯通

tests/test_local_nli_wiring.py使用现有make_fake_harness、真实索引Retriever/per_claim交付、当前v7提取parser、ModelEvidenceVerificationAgent schema13与synthetic ModelResponse解析，经过实际Harness输出→production_frames→LocalNLI模型接口stub→RunStore追加→真实API。没有手工构造frame绕过转换器。

覆盖正文单组件、混合正文/数学组件、元数据不支持、aggregate缺逐组件映射；旁路开关/模型失败/模拟分歧均不改变原policy decision。原模型辅助政策即使全部fact supported也可review_required，测试不强迫pass。最终完整575项离线通过（37.091秒、0跳过）；原Harness七场景完成预期验证。旧synthetic单元按production_frames_v1检验旧行为，新贯通直接使用v2。

## 真实任务冻结与执行

独立忽略目录data/runtime_local/local-nli-wiring-v2；source/request/config/检索预览/源码SHA在提交前冻结。选择现有NERC Reactive Power Planning（2016）官方提取正文中的概念关系：正常及故障条件下维持电压需要充分无功资源。实际完整英文输入/官方fragment/来源hash/页码留私有包；不宣称为中国当前运行规定、工程安全或视觉PDF验收。

采用正常POST /runs的assess_existing入口，existing_citations由原服务在固定knowledge snapshot解析官方fragment，不手工伪造Evidence/Agent结果；实际Factory.create调用原生产四Agent/提取/schema13/领域审核/有限修订，只覆写本轮已有RetrievalSettings为max_results1/contextNone/per_claim。预览完整并集243token，实际NLI保留模型抽取的正常/故障限定后282token（≤512），0截断。不是结果出来后换题或选择模型。

使用原环境加载器在已授权服务中加载凭据，没有显示/归档密钥或令牌；官方DeepSeek TLS预检无POST/无凭据，实际API按原HTTPS连接。保留现有预算40model calls/12retrieval calls、90s模型/110s步骤/800s运行、最多一次Revision/有限纠正，不加本轮任意付费批次总请求帽。submission-attempt排他标记只保障唯一任务不自动重发，不限制任务正常阶段模型调用。

真实run：`c6dfce08803842679925392ac212e684`，answer v1。1个真实正文组件可转换，NLI complete1/skipped0/failed0；事实独立核验supported、原引用核验supported、NLI supported，无分歧。NLI与事实组件绑定为同claim/component/answer_id/v1/knowledge，完整实际正文只有该组件明确交付的1段768字符，未借用总pool或按判断缩证据。字面绑定offset[0,133)，输入身份/正文SHA/完整语义input/logits在live-wiring-audit/nli中。

实际4个远程模型请求全部succeeded：一次提取、独立事实核验、领域审核、原引用核验（执行顺序可并行交错）。0纠正、0Revision、0执行问题、必需阶段完整；13588输入＋837输出＝14425token。自然原业务决策仍review_required，NLI supported没有升级为pass，未作工程可靠性结论。本地推理0.118475秒，模型加载0.147949秒（不含进程/库启动），记录点RSS504,352,768字节≈481MiB，非精确瞬时峰值。

## 浏览器、重启和停止

本机127.0.0.1:8768实际页面，用户仅本机填写新服务令牌。通过历史按钮打开同真实run：看见事实原判断与NLI均支持、同v1组件ID、282token、无分歧、风险4/23和原业务“需人工复核”；展开模型版本/logits/实际输入及绑定，不提交新任务。

正常lifespan关闭服务，再启动同目录：脚本检测已保存run_id只查询，不POST，原审核raw_result SHA、诊断UUID/输入/结果SHA、远程model记录数4均相等。实际浏览器点击查询状态重新完成请求，同结果仍显示；browser与restart证据单独记录。查询0模型补算/0远程重发，随后服务再次正常关闭，模型子进程按已有生命周期释放。没有启动训练或第二批。

私有启动脚本仅用于恢复查询已保存记录：

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe D:\PowerTrustAI\data\runtime_local\local-nli-wiring-v2\serve-one-real.py
```

原run-id/submission-attempt保留，不删除后重放；最终停止标记保留，避免意外再次运行。若所有者以后只恢复查询，应先确认run-id.json存在，把stop-request停止标记另存为新的历史文件，再启动；绝不删除提交标记，不会创建第二任务。源码中server.should_exit触发既有lifespan正常关停。最终服务状态/提交与远端见verification-final。

## 交付、限制与教学

审阅ZIP含实际冻结输入/配置/官方选段、产出/trace/Fact与NLI关联/源码hash、原审核与重启hash、浏览器截图、测试/失败/资源与简明阅读说明；不含凭据、完整PDF/数据库或模型权重，实际模型消息/响应仍由原归档保留本机，包只收无请求头的指定记录。代码说明独立提交普通推送，命令级代理127.0.0.1:7897；不修改持久代理/SSL。

这是一次真实接线验证，不是NLI准确率/安全认证。当前独立组件原文span缺口仍存在，混合/共享锚点保守跳过；nullable行政元数据读取修复不代表未知出处可信。固定提取正文带PDF/layout质量告警，未重新视觉核对。模型既有4/23错误支持不消失，未改NLI权重/标签/分类头或原决策。长期手册补“真实Harness贯通与手工frame回放的差异”、原文/归一化/组件对象边界、None与历史缺记录区分、复合任务skip、真实身份/交付证据、NLI与policy分离及重启无补算；不重建整本PDF或网站。
