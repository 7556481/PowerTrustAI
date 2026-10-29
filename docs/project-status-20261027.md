# PowerTrustAI 阶段交付清单 · 2026-10-27

**阶段封存、可演示、审核收益待研究。** 今天只整理展示与验收，项目模型请求0、费用0；未加载.env、启动旧实验或业务服务，没有把全部研究目标标为完成。

## 提交身份与入口

|身份|完整提交SHA|
|---|---|
|应用基线|1a92d03da49ae25f311e950373003d6ab32d09f5|
|最新评测实现|babdfe1a429e740cc06aec178b18fb72aa05dccb|
|自然审核归档|865eb65c617e14c04d443283bec8b27af1da0f14|
|本次起点/学习站v6归档|112733ddb6cc2931e97e03b46d391c427a7c65f2|

当前封版提交身份由Git HEAD确定，最终交付消息列完整SHA；不把文件自引用当可实现的提交哈希。分支codex/project-closeout-20261027，不合并主分支、不发release/tag。

最短演示：双击项目根[start-learning.cmd](../start-learning.cmd)，访问http://127.0.0.1:8770/；或直接打开[静态首页](learning/site/index.html)。首页按N1→A3→N4→返回路线讲解约7分钟；[17章简历与讲稿](learning/chapters/17-interview.md)。这些都是历史归档阅读，合成fixture另标，不现场生成或回写Store。

```powershell
# 项目根目录；有Python即可，仅标准库
python -m tools.learning_site serve --port 8770
# 若克隆缺少派生HTML，先离线构建
python -m tools.learning_site build
```

没有Python时直接打开已提交HTML。若源码/HTML均缺失，重新取得公开仓库文件；不自动下载大库/模型。本机既有解释器为`.venv/Scripts/python.exe`，本轮不建环境、不安装依赖。

## 当前状态、模块和回退

生产schema13、原检索topic_v4_subject_v1、原审核/政策保留，8765停服；受管编排langgraph_v1，未配置源码fallback sequential。chinese_first_cross_language_v1及literal_v1/source_actions_v2仍为默认关闭候选，NLI关闭；新请求只允许Flash，旧Pro仅历史。

|入口|用途与边界|
|---|---|
|tools/learning_site.py；start-learning.cmd|独立静态8770，不导入业务、不读运行库/凭据、不调用模型；Ctrl+C释放本任务服务|
|backend/assembly.py；harness/runtime.py；harness/execution.py|原Factory、OfflineHarness、外层图及四职责；预算/版本/完整重审复用|
|agents/；services/evidence_scope.py；harness/product_policy.py|生成/事实/领域/修订、Evidence作用域及政策；ClaimExtractor为服务|
|rag/corpus_index.py；rag/chinese_first.py|默认FTS/BM25与默认关闭跨语言候选，70GB不是向量库|
|backend/store.py|原版本及失败持久化；旧Store不回写|
|start-powertrustai.cmd|业务8765入口，可能加载服务端.env；真实任务可能付费，今天不执行|

原编排回退方式：正常停服后将受管orchestration.json的execution_path设为sequential再按原入口启动；不是失败自动重发。候选通过显式profile/合同选择进入，回到原默认即可退出，不改库/切分/schema。这里只说明既有方式，本轮未实施回退或生产切换。

## 已证明、未证明与明确失败

|证据|可说|不能说|
|---|---|---|
|[固定16生成](https://github.com/7556481/PowerTrustAI/blob/a6ba66d4787e2806d828edd84ec6435cc6e2d64f/docs/evaluation/retrieval-evidence-answer-check-v1/report.md)|8题5净改善/3混合；正确完整语义槽1/25→19/25|没有B回答组，不能全归翻译；不是普遍准确率或审核增量|
|[给定历史发现修订](https://github.com/7556481/PowerTrustAI/blob/73c25ca0af9ba9fd5143527c6341aae52170fffd/docs/evaluation/local-revision-v2-flash-check-v1/report.md)|4/4实际改对、保留正确内容且完整重审|首轮发现回放，不是自主发现率|
|[自然8稿新初审](https://github.com/7556481/PowerTrustAI/blob/865eb65c617e14c04d443283bec8b27af1da0f14/docs/evaluation/natural-draft-audit-v1/report.md)|N2/N4支持关系被误认且未修，19/25不变；N5执行失败、N8争议改写|未证明关键纠错收益；不能把pass/合法引用当正确|
|[三路检索](https://github.com/7556481/PowerTrustAI/blob/99b93497cb78bf3f040f1874ad07cb525be6d64b/docs/evaluation/chinese-first-cross-language-retrieval-v1/report.md)|B完整2/8，C原始证据25/25；N6换义、旧gate=false|资料在库不等于召回；输入行语言分类不等于去重后比例|

N1/A3/N4三个演示点的完整正文和来源定位已在v6页面；新导航不重写旧结果。AI辅助/用户监督，非专家金标准；工程参数、仿真及安全认证仍无此证据。

## 最近三批用量（分别归属，不是全项目总账）

|历史批次|Flash新增请求|token|实际金额|
|---|---:|---:|---|
|跨语言查询转换|8|1359|未知|
|固定A/C证据生成|16|147049|未知|
|固定C自然稿审核|32|380949|未知|
|今天文档封版|0|0|0，无项目请求|

各历史批彼此独立，转换不重算到生成/审核，缓存明细见原报告。旧gate=false及N6争议保持，不恢复未执行条件槽，不拼历史阶段耗时为当前端到端时延。

## 公开与私有的交付边界

公开克隆可阅读README、学习站20章88题、完整案例答案、必要预测和来源身份/位置；静态构建与阅读只需标准库。公共synthetic_fixture可供离线工程学习，但不是本轮执行项或真实语义成绩。完整后端/公开测试按仓库依赖清单准备，今天未安装或重跑。

旧电脑私有知识库、官方全文、实际输入/响应、原始运行Store及模型权重位于忽略data，不在公开仓库；其缺失时不能复跑真实语义批次，公开案例仍可阅读。真实业务入口需要获准私有资料和服务配置，提交任务可能付费；本轮不连接。未跟踪设计/论文、独立历史仓库保持原样，不纳入封版提交。

## 验收范围和停止

本次只验README/状态链接、学习站build/learning_checks、source-version与源码身份、截图/案例索引，以及修改后的首页→三案例→返回路线，桌面/窄屏抽查；明细见learning/closeout-20261027-verification.json。复用[v6浏览器记录](learning/browser-acceptance.json)的搜索/其他章节/88解析等历史检查，非今天全站重验。不重跑1324全套，不做能力实验或任何模型调用；启动脚本仅读，不改。

唯一下一研发方向：重新设计事实支持关系判断，优先解决“协调重要/可能需→普遍必须”和“未说明→排除”的误判。待决问题是如何表达及验收支持强度、反例与来源适用范围，**没有待运行批次**，不自动执行旧source-comparison设计。完成定向推送及远端SHA/关键文件核对后停止。
