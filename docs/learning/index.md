# PowerTrustAI 学习入口

从产品里的一个审核意见出发，沿一次请求读到代码，再练习解释能力与边界。运行配置只看[当前状态](../current-status.md)；本书的旧代码与实验按绑定版本阅读。

## 先选一条路线

- [第一次了解产品](chapters/01-product.md)：读完能解释用户会拿到什么，以及“给出意见”和“修改正文”有什么区别。
- [沿一次请求读源码](chapters/14-code-tour.md)：读完能追踪检索、生成、双审、修订与版本保存，指出每一步能验证什么。
- [准备面试](chapters/17-interview.md)：读完能用证据讲清技术取舍与失败边界，再完成[从产品到代码的实操](chapters/20-workshops.md#从产品到代码常见与最典型)。

## 最终交付系统优先路线

[能力—正文—代码—练习索引](resume-learning-map.md)：先读24→25→26→27，再读31修订授权、35并行时间线与37正式协议。Dense/RRF、NLI和训练保留历史/进阶，不作为首读前置。其他技术见[邻接基础](chapters/38-adjacent-foundations.md)。

## 按主题系统学习

先读[知识覆盖与证据清单](engineering-coverage.md)，再沿以下概念依赖学习。21—30是工程专题，31—36把同一机制放回真实失败和取舍。旧1—20章保留详细公式、代码摘录和绑定版本的实验原文。

- [21 从用户问题到可交付对象](chapters/21-product-contracts.md)
- [22 数据发布、事务与稳定原文身份](chapters/22-corpus-engineering.md)
- [23 从SQL走到模型实际读到的证据](chapters/23-search-boundaries.md)
- [24 云端请求、结构纠正与未知费用](chapters/24-model-wire.md)
- [25 主张、支持关系与修订权限](chapters/25-agents-semantics.md)
- [26 图编排、关键路径与资源所有权](chapters/26-execution-control.md)
- [27 接单、存储、停服与旧版本读取](chapters/27-service-storage.md)
- [28 初稿、异步读取与字符标注](chapters/28-browser-consistency.md)
- [29 从指标分母到用户等待的可计算评测](chapters/29-evaluation-math.md)
- [30 依赖、CI与安全删除的工程依据](chapters/30-maintenance-practice.md)
- [31 案例：修订合同：给定发现后的四例闭环](chapters/31-case-revision.md)
- [32 案例：跨语言：目标交付与投入退出换义](chapters/32-case-cross-language.md)
- [33 案例：Tantivy：快读取为何没有快交付](chapters/33-case-tantivy.md)
- [34 案例：Windows writer：直接证据与未知持有者](chapters/34-case-windows-writer.md)
- [35 案例：Overlap：让模型工作盖住领域读取](chapters/35-case-overlap.md)
- [36 案例：前端与生命周期：从具体故障到归属守卫](chapters/36-case-ui-lifecycle.md)

- [37 协议字段与预算状态实操](chapters/37-protocol-ledger-lab.md)：先读24/25章，再练JSON边界、引用隔离和持久预留演算。

## 正文与历史怎样分开

前20章先读最终机制与基础推导，带日期/候选补记转入逐字归档；每章末可展开旧标题定位。面试只从[第17章当前入口](chapters/17-interview.md#当前面试介绍唯一主入口)开始。历史快照是旧记录，不是当前配置；32—34章分别练控制变量、产品等待和恢复状态。

## 归档案例路线

保留 N1 → A3 → N4，先读两稿和原文，再解释改善发生在哪一层；这些是2026-10-26/27归档材料，不现场生成、不调用模型。

|顺序|案例|能回答的问题|
|---|---|---|
|N1|[资料取回后回答怎样变化](chapters/05-rag.md#完整案例一n1从资料不足到有据回答)|命中、交付和生成改善为什么要分账？|
|A3|[一次有据修订怎样重审](chapters/04-harness.md#从修订04到44究竟修复了哪一层)|给定成立发现后的修订，为什么不能称自动发现错误？|
|N4|[为什么有引用仍可能答错](chapters/08-verification.md#同一自然稿审核真正的识别收益怎样计算)|可回查与supported为何仍可能漏掉排他错误？|

## 接着读什么

- [第16章：性能与可观测性](chapters/16-performance.md)：分清读取、首稿后审核等待、提交到终态的不同口径。
- [第18章：启动与运维](chapters/18-operations.md)：分清公开演示、本机配置与实时健康检查。
- [第20章：实操与答案](chapters/20-workshops.md)：先作答再展开解析；只有合成夹具操作，不使用正式历史或付费模型。

## 独立阅读与历史

双击 `start-learning.cmd` 使用本机8770学习服务；也可只带走 `site/`，直接打开 `index.html`，目录、搜索和折叠答案不依赖网络请求。Markdown 是唯一正文，HTML、搜索和清单由构建器派生。外部固定报告仍需联网查阅。

[发布与研究历史索引](../history-index.md) · [旧首页补记](reading-history.md) · [继续完善教材的问题](questions-for-chatgpt.md)

四个判断层次：JSON可解析、必需步骤完整、给定证据下的supported、政策处置pass。它们不能互换；教学构造、AI辅助用户监督的开发复核与真实运行分别标记。
