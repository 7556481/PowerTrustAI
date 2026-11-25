# 17 深入面试、公式和代码练习

配置、启动与能力边界见[当前状态](../../current-status.md)。可先按[学习索引](../resume-learning-map.md)补齐不熟悉的技术，再用本章演练项目介绍和逐层追问。

## 当前面试介绍（唯一主入口）

PowerTrustAI根据电力资料回答问题，保存带引用的初稿，再提取主张，分别做事实与领域审核。事实审核检查原文支持及限定，领域审核检查工况、适用条件与必要输入。LangGraph路由已有业务阶段，Harness管预算、超时和取消。有明确修改依据且符合资格时最多修订一次，新版重新提取并完整双审；SQLite保存每版正文、证据和审核记录。

本机受管配置使用SQLite FTS5/BM25、schema13和云端DeepSeek Flash，启用事实审核与领域检索重叠；通用配置与历史候选不能混说。上述是项目机制介绍，个人负责哪些步骤由本人确认，不预写个人贡献。

## 六组当前逐层追问

### 1 为什么需要RAG，资料怎样进入模型
简答：模型已有知识不能替代本次指定资料。Retriever查询SQLite，取得按版本和范围绑定的Evidence，交付器选择根与邻段，生成消息实际携带正文和引用目录，而不是给云端模型一个数据库连接。

例子：库里有三段，Top-K只有定义没有恒压条件，则初稿仍可能缺限定。应逐层查在库、候选、预算交付和发送消息，不能说“库里有所以模型看到了”。源码：[corpus_index](../../../rag/corpus_index.py)、[retrieval](../../../harness/retrieval.py)、[generation](../../../agents/generation.py)。继续追问：LIMIT限制返回条数，不保证排序只处理K条；词面命中也不是支持证明。

### 2 为什么分事实与领域审核
简答：事实审核问原文是否支持主张及限定，领域审核问工程工况、输入和前提是否齐备。它们有不同输入、证据目的与输出合同，不只是两套角色名称。

例子：“常见装置”被写成“最典型”，事实要查比较依据；“可以确定现场投切方案”还需运行参数，属于领域前提问题。缺参数不是反证，不能一律标contradicted。源码：[事实Agent](../../../agents/evidence_verification.py)、[领域Agent](../../../agents/power_domain_review.py)。继续追问：两者都认可仍可能共同漏错；政策不靠投票决定真伪。

### 3 一次请求怎样经过函数、对象和持久化
简答：API Submit→ApplicationService.submit→RunStore.create与queue→worker→ComponentFactory.create→Harness/RunExecution→阶段observer→RunStore.checkpoint/mark。请求、Answer版本、Claims、Findings和Evidence分别保存关联。

例子：生成后v1已保存而审核仍running，页面可读初稿；修订为v2后须重新提取和双审，不能把v1意见贴过去。源码：[api](../../../backend/api.py)、[service](../../../backend/service.py)、[store](../../../backend/store.py)。继续追问：DB创建与内存入队不是跨进程原子事务，响应丢失时提交可能已成功，不能自动再POST。

### 4 超时、取消、非法输出怎样分别处理
简答：模型调用有期限；结构非法由structured_request显式至多纠正一次；用户取消是协作取消，底层已发HTTP可能继续，资源drain后再close。三者都不能改名为资料不足。

例子：HTTP200但content多出unexpected字段，首答记非法并再扣一次调用；429不是格式错误，不走同一纠正。源码：[structured_request](../../../services/structured_model.py)、[ModelClient](../../../model_adapter/runtime.py)、[适配器](../../../model_adapter/deepseek.py)。继续追问：取消不证明未计费，未知usage按相应账本保守保留。

### 5 为什么LangGraph仍需要Harness，overlap为何有时有效
简答：LangGraph连阶段和路由，修订后回提取；Harness及RunExecution持有业务对象、预算、期限和取消。本项目checkpointer=None，节点retry_policy=[]，没有透明恢复远端模型调用。结构纠正在业务请求层，不由图任意重放付费节点。

例子：第一组F=2、领域读取4、事实审核10、领域审核5，旧终态16秒，新终态12秒；第二组F=2、领域读取4、事实审核6、领域审核9，旧终态15秒，新终态15秒。第二组同时改变了事实与领域耗时，此时领域路径决定结束时间，事实提前完成没有缩短最终等待。资源竞争或纠正变化时重算，不套理想上界。源码：[图节点](../../../harness/graph_runtime_v1.py)、[prepare_review/review_pair](../../../harness/execution.py)。继续追问：create_task不等于HTTP线程已启动；换Tantivy的读取优势没有兑现产品终态收益，不能乘以overlap倍率。

### 6 哪些已有验证，哪些尚未证明
简答：离线合同、绑定、重审和存储有工程验证；固定历史错误稿给定发现后的四例修订闭合有真实结果；自然问答自主纠错的普遍收益未证，十题基线六题完整且无有据修订。

例子：v23七完整对测首稿后的审核等待；v28六完整对测客户端提交到终态，两个实验起点不同。源码与证据：[评测正文](29-evaluation-math.md)、[十题报告](../../evaluation/stable-product-baseline-v1/report.md)。继续追问：执行完整、字段合法、语义正确和工程安全不能互换，个人贡献仍须本人材料。

::: answer 自己推演：v2新增一句话，旧版通过结论能复用吗？
先写对象：Answer保持回答身份但version=2，原Claims按v1锚点，不能覆盖新句；重新提取生成v2 Claims，再双审并保存v2 Findings/Report。历史v1对象保留可读，不覆盖。若预算耗尽则报告重审未完整，不能借旧pass交付新版已通过。对应RunExecution.revise回extract_and_tools及Store版本索引。
:::

## 效果如何陈述

正式十题六题完整审核，该批没有有据修订；历史给定发现四例修订成功不等于自主发现收益。v23七完整同初稿对照33.48→23.71秒，起点是首稿交审核；Tantivy最终产品比较更慢且已退役。数字对应[性能正文](16-performance.md)及固定报告，不相乘，不包装工程安全认证。


## 历史内容定位

整理前原文完整保留于[历史快照](../archives/17-interview.md)；这里只放一套旧定位。

::: answer 展开历史内容定位
<a id="先练解释不认领未经确认的经历"></a>

- [先练解释，不认领未经确认的经历](../archives/17-interview.md#先练解释不认领未经确认的经历)

<a id="阶段封版面试演示与简历表述2026-10-27"></a>

- [阶段封版面试演示与简历表述（2026-10-27）](../archives/17-interview.md#阶段封版面试演示与简历表述2026-10-27)

<a id="2026-10-26新版30秒介绍"></a>

- [2026-10-26新版30秒介绍](../archives/17-interview.md#2026-10-26新版30秒介绍)

<a id="2026-10-26两分钟历史口述草案与追问"></a>

- [2026-10-26两分钟历史口述草案与追问](../archives/17-interview.md#2026-10-26两分钟历史口述草案与追问)

<a id="历史说明与基础知识按记录日期和绑定版本阅读"></a>

- [历史说明与基础知识（按记录日期和绑定版本阅读）](../archives/17-interview.md#历史说明与基础知识按记录日期和绑定版本阅读)

<a id="30秒项目介绍理解后再用自己的话讲"></a>

- [30秒项目介绍：理解后再用自己的话讲](../archives/17-interview.md#30秒项目介绍理解后再用自己的话讲)

<a id="两分钟版本与本人贡献"></a>

- [两分钟版本与本人贡献](../archives/17-interview.md#两分钟版本与本人贡献)

<a id="架构追问"></a>

- [架构追问](../archives/17-interview.md#架构追问)

<a id="数据与安全追问"></a>

- [数据与安全追问](../archives/17-interview.md#数据与安全追问)

<a id="rag与算法追问"></a>

- [RAG与算法追问](../archives/17-interview.md#rag与算法追问)

<a id="微调追问"></a>

- [微调追问](../archives/17-interview.md#微调追问)

<a id="执行与产品追问"></a>

- [执行与产品追问](../archives/17-interview.md#执行与产品追问)

<a id="公式练习与参考答案"></a>

- [公式练习与参考答案](../archives/17-interview.md#公式练习与参考答案)

<a id="代码阅读练习与参考答案"></a>

- [代码阅读练习与参考答案](../archives/17-interview.md#代码阅读练习与参考答案)

<a id="简历写法与不能写的说法"></a>

- [简历写法与不能写的说法](../archives/17-interview.md#简历写法与不能写的说法)

<a id="三道自测先作答再展开"></a>

- [三道自测：先作答，再展开](../archives/17-interview.md#三道自测先作答再展开)

<a id="自测1面试能否声称全代码手写"></a>

- [旧位置转到归档](../archives/17-interview.md#自测1面试能否声称全代码手写)

<a id="自测2局部指标涨为何不采用"></a>

- [旧位置转到归档](../archives/17-interview.md#自测2局部指标涨为何不采用)

<a id="自测3未来计划能否写已实现"></a>

- [旧位置转到归档](../archives/17-interview.md#自测3未来计划能否写已实现)

:::
