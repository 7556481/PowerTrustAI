# 54项复核接收与74项基线准备 v1

2026-10-05，接续已推送 f70fac7。本轮按用户最新限定仅接收意见、合并和准备，不执行包内建议的真实基线；模型请求0，标签全部pending，不训练、不替换生产审核器。

## 已落实

项目根目录没有指定ZIP，使用用户附件明确指定的Downloads文件；安全成员检查后解压到新的忽略目录 `data/runtime_local/review-expansion-54-v1/received/`。读取README、逐项报告、analysis及next-codex-prompt；两份原输入ZIP哈希核对，54项ID/task_key与原冻结任务一致。用户附件和旧91/48/6任务、旧预测不覆盖。

新48为36主要/1辅助/11hold；修订6为5主要/1辅助。A05虽有supported建议，但换了原MW/MVA核验对象且与A02近邻，保留辅助，其父任务仍hold，不称原单位问题已修复。

全145项新视图：74主要（旧33＋新36＋修订5）、31辅助、40hold。主要69事实支持＋5原引用支持、25关联家族；预分train36/validation25/test13。建议32supported/22contradicted/20insufficient_evidence/0not_assessable，确认0。不能声称四类训练覆盖或独立评测。

全145项有84组共享摘录（22跨集合）、79组共享Evidence（23跨集合）、6共享文档（6跨集合）；按现有同任务类型token Jaccard≥0.9规则19对近重复，0跨集合。统计的是共享组/对，不是独立样本量；阈值未调，既有分组未重排，未宣称所有语义近重复都被识别。A02/A05的定性近邻判断另由复核报告保留。

质量层实际会把复核依据子集重填全部引文；仅修复 `apply_quality_layer` 保留原basis_ids子集（包括空集），越界仍拒绝。新增公开synthetic_fixture验证pending不升级、错哈希/文本/ID、父谱系隔离、依据子集、共享材料报告与请求不含标签/recipe。

## 可复现准备入口

运行 `python -m evaluation.support_review_merge --help`，使用项目 `.venv/Scripts/python.exe`；参数old/expansion/amended指向原91审阅视图、48质量视图、6修订任务，review-directory指向本次安全解压目录，original-zip/quality-zip指向两份原冻结ZIP，baseline指向旧predictions，output必须新建。具体完整命令保存本机reading-notes，真实任务/官方摘录不随公共代码发布。

输出all-pending、primary-pending、逐IDmerge-manifest、辅助/hold分流、relationships和baseline-preparation。清单保留语义task_key与完整task SHA（两者用途不同）、建议来源/依据、parent、group/split。前者识别候选，后者严格限制预测复用。

基线准备复用现有support_baseline.messages/pack；逐样本请求74个，0容量排除，最大初始消息32136字符，默认容量240000。预期标签/建议/配方/旧模型理由不在请求；系统提示保留四类名称。每样本最多一次纠正，结构性至多148请求；只复用完全匹配的1条旧有效预测时至多146。此数量是固定请求结构推导，不是token、费用或成功保证，不新增任意付费批次上限。本轮实际调用0、指标null；旧5有效预测和失败保留，修订不借父预测。

**尚不能直接执行包内要求的完整新基线**：当前support_baseline.execute遇任意batch异常就break。已冻结独立请求但没有改变历史入口失败语义，也没有把它标成支持单项失败继续。执行前须独立回归单项合同失败继续、全局鉴权/服务不可用停止、有限纠正/超时及失败账本；本轮不运行。已确认标签且有有效预测后才计算分类型/原始/构造/修订指标，pending不算准确率。

## 本机交付与后续边界

忽略目录 `data/runtime_local/review-expansion-54-v1/`：received、merged-v1、合并Markdown、准备包ZIP、reading-notes、verification及离线日志。报告输入ZIP日期2026-10-04，接收日期2026-10-05，不改历史。未重新打开官方PDF或声称视觉原文核验。

首次微调仍缺具体逐项监督确认、not_assessable有效主任务、独立评测资料/问题家族、NERC训练使用许可，以及实际训练模型/算力配置核对。保留现有支持判断任务格式和确认后JSONL接口；不安装框架、下载模型或借未确认标签训练。本轮不扩写手册/PDF、不改生产协议/默认检索。
