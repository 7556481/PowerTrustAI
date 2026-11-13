# Tantivy实验资产退役与当前交付状态

2026-11-13。当前日常配置为SQLite全文库＋事实审核与领域检索重叠，保留schema13、DeepSeek Flash和事实内部serial_v1。日常运行根目录`start-powertrustai.cmd`；零模型演示运行`start-powertrustai.cmd --demo`；回退调度使用`rollback-overlap.cmd`。私有知识库、历史和凭据不随Git分发；新克隆请先用演示入口。本文记录配置与验收，不声称8765此刻正在监听。

|证据|结果与边界|
|---|---|
|v18四条冻结宽查询|SQLite/Tantivy读取墙钟比中位约1.87；普通题约0.58，不能推广为终态收益|
|v23另批同初稿审核，7完整对|首稿之后到审核终态中位33.48→23.71秒；不是提交到首稿或完整产品提速|
|v28从生成开始、两路均overlap，固定8题16链|6完整对客户端提交到终态中位SQLite29.99秒、Tantivy37.60秒，候选慢7.62秒/25.4%；全8题首稿中位5.32→7.09秒|

v28两路各7/8完整；候选Q3、SQLite Q7事实审核失败保留分母，100次Flash请求/1835305可信token，无补跑。未达至少15%且3秒的终态门槛，结束Tantivy产品路线，不有限启用。未宣称最终正文逐句语义复核通过，审核完整不等于质量认证。[v28固定报告](https://github.com/7556481/PowerTrustAI/blob/2456646a2398e7ca634dab8f79b0585146e725b7/docs/evaluation/tantivy-product-acceptance-v28/report.md)。

v29经用户另行批准，仅删除清单一致的实验文件：1661个原生索引文件13652619520字节、90个映射5894086656字节、spool53678977024字节，共1752文件/73225683200字节。删除窗口D盘可用空间777146970112→850375540736字节，净增73228570624字节（约73.23GB）；文件体积和磁盘净增分列，差额不计作额外删除。

清理前后在隔离8787使用正式SQLite配置检查历史答案、原文和邻接；原探针证据前后hash一致，但收尾发现它未被正文引用。另补查真正正文引用，与清理前Store副本和保留SQLite比对通过；缺少这第二条引用的清理前API观测，保留验收偏差，不声称完整同引用前后API实测。正式110条历史及预算逐表hash不变；0模型、0正式重启，隔离服务已退出。[v29固定公开回执](https://github.com/7556481/PowerTrustAI/blob/99d92cd51f9d6e755f10344cc1a10f5591757a99/docs/maintenance/tantivy-retirement-v29.md)。私有本机回执和逐文件清单不提交。

90片、映射和spool实体现已退役，历史manifest和报告不能证明资产仍可运行；保留正式SQLite、Store、预算、历史反馈、代码和报告。没有将小样本单套资产原型当全库单库迁移完成。

归档入口（本轮核对）：[PR #8](https://github.com/7556481/PowerTrustAI/pull/8)和[PR #9](https://github.com/7556481/PowerTrustAI/pull/9)均开放草稿、未合并。PR状态可能后续变化；固定[v27提交](https://github.com/7556481/PowerTrustAI/tree/99269c15a317403d19458bebcd3b7bf0d71ed2ba)、[v28实现](https://github.com/7556481/PowerTrustAI/tree/b674124e3bb8289731044f744cec75571fb6db8d)、上述固定报告及[v18/v23归档](https://github.com/7556481/PowerTrustAI/tree/75cbbdd)保持可查。本轮仅文档同步，不合入实验代码，不改历史报告。
