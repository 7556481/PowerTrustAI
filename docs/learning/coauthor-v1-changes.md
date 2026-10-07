# 共同作者补充 v1：定向修改与事实核对

日期：2026-10-07。应用/审阅基线：d29eccf4cc87d55c05a38bd4557685c44ec92a50。来源为用户提供PowerTrustAI-learning-coauthor-supplement-v1.md（SHA-256：dfad348fcb32a1f5a372a16d0f831b3f4923ebbfe3da6ab939e13b3978fd50a2）；附件中的写作提议不是业务运行指令。本轮只改文档，不训练、调用API或更改模型/政策/快照。现有布局/图示/60自测不动，未新增第21章或重复整篇附件。

## 逐章修改

|章|定向修改|
|---|---|
|01-product.md|产品动机分证据等级，Revision时效/高风险规则/SI范围|
|02-architecture.md|自有Harness与框架讨论边界|
|03-agents.md|文本与语义覆盖、独立性及调用数|
|04-harness.md|格式纠正与业务修订对象|
|05-rag.md|快照/排名/交付缺口，FTS与Dense|
|06-retrieval-math.md|reranker已做20题/180.0605秒/unknown与不采用|
|07-corpus.md|输入行/记录/片段/向量计数|
|08-verification.md|四层定位及实际不足→未知条件→无法评估|
|09-engineering-tools.md|有限工具与理论公式区别|
|11-supervision-metrics.md|召回满分仍误支持的教学反例|
|12-training-nli.md|已有NLI分类器的领域适配起点|
|13-local-nli.md|旁路价值与决策权界限|
|15-failures.md|PF原失败及新Ω成功并存，共同责任复盘|
|16-performance.md|采集/用量缺失/记录恢复的归属|
|17-interview.md|AI协作口述稿、本人贡献与追问|
|20-workshops.md|四个只读实操合并到已有工作坊之后|

## 核验依据与处理

- 真实Revision：只读contract-comparison-v1/full-repair/result.json，f61a804c…有2版本/2轮、完整执行，2ω→ω保留原范围；第01/15/17的笼统未验收描述改为该局部成功＋原PF0Revision并存。旧运行/失败不改。
- PF：identity-fidelity-v1摘要、原章节及schema-choice-v1报告仍记录repair=null/0Revision；此处没有重跑或把其他题成功回填。
- 字符覆盖：services/claim_obligations.py覆盖结构与harness/product_policy.py的NONCLAIM_CLASSIFICATION_UNCERTAIN门禁；字符/摘录验证不证明全命题提取。
- 高严重度：ProductAuditPolicy默认high_risk_rules为空，真实Factory未注册权威生产规则；区别拒绝机制与实际工程认证能力。
- 工具：tools/unit_conversion.py与提取器DAILY_SYSTEM只支持有限标量换算；P/S、cosφ教学不代表已运行通用功率计算。
- schema14：原no_evidence/output.json实际raw insufficient_evidence、条件required=true/preserved=null、objection=null，派生not_assessable；只解释交互，不改预测或一概确认误判。
- 检索：rag/corpus_index.py、rag/semantic.py及第05/07章已核对机制；本轮不读取动态构建进度，输入行/FTS/Dense计数分开。reranker固定20题report-v2及reranker-results.json确认180.0605494秒，非隔离/日常性能承诺。
- NLI：support-nli-expanded-v3固定报告与既有第12章矩阵一致，43/12/33、epoch1、0.656914→0.819349及4/23、4/14保留，新增解释而不重复指标表；手算为教学。
- 个人背景：毕业论文起点、独立写代码/掌握函数程度及历史框架实测缺充分证据，保留个人待确认；“三天项目”等概括不采用。可核查实现、共同复盘、个人待确认分开。

questions-for-chatgpt已将完成部分归入对应章，个人经历/学习进度继续保留。第20章四实操只读记录/公式/源码，不新增任务。正文源码版本见source-version.json；源码哈希未变化。

静态站由既有构建器生成，Markdown唯一正文。构建/源码/链接验证不等于浏览器验证；实际显示若工具不可用明确记录。文档写作不证明产品稳定，不更新历史指标或生产状态。

## 实际检查结果

既有构建器生成20章、60折叠自测；源码文档哈希/本地链接检查通过，6项已有渲染测试通过。业务/测试/构建工具文件原SHA核对一致，布局资产未变。浏览器getState在Node初始化时退出，未检查新增页面实际显示。补充阶段0 API调用、0训练，当时尚未提交或推送。后续用户明确授权独立文档提交及普通推送，实际提交和远端结果按Git记录与交付回查报告，不将浏览器补验改为已完成。
