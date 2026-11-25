# 14 核心源码阅读路线：输入、调用、异常与取舍

配置、启动与能力边界见[当前状态](../../current-status.md)。本章按正式请求与历史候选分别给出源码入口。按技术主题查讲解与练习，可用[学习索引](../resume-learning-map.md)。

## 先追一次请求



1. [API入口](../../../backend/api.py)接收问题；[ApplicationService](../../../backend/service.py)保存身份与配置、排队，再由Factory创建一次任务组件。提交被接收不等于模型已调用。

2. [组件装配](../../../backend/assembly.py)把SQLite Retriever、四项职责和提取服务交给Harness；[受管选择](../../../backend/managed.py)只在显式配置下启用事实审核与领域检索重叠。

3. [LangGraph阶段路由](../../../harness/graph_runtime_v1.py)连接七个共享阶段；[RunExecution](../../../harness/execution.py)执行检索、生成、提取、双审、政策与至多一次修订。预算、取消、停止仍由Harness执行，生成与审核的调用次数不固定为四次。

4. [RunStore](../../../backend/store.py)按run、answer_id/version保存正文、证据和意见；历史GET读取已有结果，不发模型请求补算。用[第20章练习](20-workshops.md#从产品到代码常见与最典型)把一个标注追到审核与修订资格。



下面的代码摘录与实验分支按各自绑定版本理解，不因本次阅读路线更新而改写。



## 一页请求对象流：先认对象，再读源码



|阶段|对象及身份|数据进入和离开|失败/保存边界|
|---|---|---|---|
|API接收|Submit→TaskRequest；服务产生task_id/run_id|用户问题、可选原回答；客户端不能提交模型路径|先类型校验；无效输入未受理，不算模型失败|
|队列/worker|RunStore保存请求/配置；ComponentFactory产生Bundle|固定知识版本/政策/schema；不把预期标签交模型|共享装配错误停止后续；接受后不能盲重发|
|Generation|AnswerDraft(answer_id,version,text,citations)|实际交付Evidence；答案引用与事实独立检索分开|无实质答案后续不适用；连接/生成失败单列|
|提取|ObligationClaim＋组件ID/原文锚点|立场、数量、必要限定、核验义务|忠实性不同于来源支持，不强制faithful|
|双审|实际EvidenceVerificationInput扩展；领域输入|身份/版本/候选由程序绑定；模型评估支持/条件/异议|Fact与Domain并发；有效同级结果保留；非法ID不补造|
|政策|执行完整性＋业务处置＋问题解决程度|不是多数投票；来源及支持要求仍阻断|可定位局部错误才修订；缺输入不靠删除问题解决|
|Revision|新回答版本，重新产生主张对象|一次实质纠错，重新交付并完整双审|原版错误不抹去；不得修订后直接通过|
|持久化/UI|observer→checkpoint/结果；版本独立|回答、处置、依据先展示，技术详情折叠|刷新/查询/重启只读既有结果，不补算或远程重发|



教学构造：task=T、answer=A/v1、claim=C/组件C0、Evidence=E/知识K；Fact仅可在C0的候选范围选依据，原引用R0仅可用原交付。候选ID不是跨目标通行证。详细synthetic对象与实际函数摘录见下节。



主要契约对照冻结同回答/主张/完整交付，只改13/14；这能减生成/检索混杂，但不能证明完整产品。完整服务与Revision另测，阶段、结构、语义和业务分母分开。采集故障也必须停止并记录，已发请求只离线恢复；否则统计会把报告工程缺陷误算模型失败。





## 如何读，不被版本文件淹没



先看backend/__main__.py和assembly.py，再读OfflineHarness.run，最后才深入当前Agent协议。目录里旧v4/v6/v9不是多个并行审核器，而是历史契约保留。当前manifest明确schema和prompt；不要凭文件名最大数字猜采用版本。



本章提供调用路线；早期代码摘录已移入章末链接的历史快照，按摘录绑定版本阅读，不代表最新实现。查现行实现时，从本章源码链接进入完整函数，再核对装配与调用方。源码身份检查证明文件与记录一致，不自动证明教材解释正确。



在learning-audit-v1历史版本中，新增紧凑协议入口agents/verification_contract_v14.py的ReviewCatalog/run只通过直接组件回归，真实Harness输入包装遗漏导致12题失败；默认日常仍13。查看learning-audit-v1冻结源码中harness/runtime.py的历史schema9–13包装分支，可以定位当时14缺tool_results；当前已改用显式输入能力和services/review_inputs.build，不把历史分支当现行源码。那个批次没有在当轮自动补后重跑，见第15章。



## 第一条路线：从提交到冻结答案



ApplicationService.submit验证配置、排队并保存TaskRequest。worker建立Bundle，调用OfflineHarness.run；runtime中invoke统一处理期限、使用量、执行问题和observer。问答先检索、Generation，已有回答直接冻结；提取服务输出claims，validate_extraction检查覆盖和绑定。



阅读任务：找到answer_id/version在哪里生成，找到substantive_answer=False为何绕过提取。若生成未成功，是否可能还有领域模型请求？按状态和usage回答，别只看函数名。



## 第二条路线：Evidence怎样变成typed basis



KnowledgeStore.evidence从固定版本片段构造原文对象；RetrievalSession保存命中与交付，quote_candidates提供字面候选，EvidenceScope为独立审核和每项原引用建立不同命名空间。解析器把合法选择映射到TextExcerpt或metadata/calculation等正式对象；core.typed_evidence负责类型义务。



阅读任务：一个quote属于当前原引用scope但text相同于另一scope，借用是否合法？答案是不合法，作用域是审核对象与交付身份，不仅文字。程序可验证这个关系，不用模型判断“看起来同源”。



## 第三条路线：政策与Revision



ProductAuditPolicy.decide_context读取执行、分类、支持、领域和引用结果。bounded_repair.eligible_repairs只允许存在原文绑定建议的faithful adverse对象。Revision不自行通过；runtime创建新版本后回到提取和双审。观察review_rounds和answer.versions而非只看usage中有没有revision组件。



阅读任务：为什么一个insufficient finding不必自动修订？因为可能是缺资料；没有已交付原文能支撑实质replacement时不能发明修复。反例中即使可修另一个错误，其他缺口也保留。



## 第四条路线：存储和只读恢复



RunStore.tx管理短写事务，index保存版本化对象，result经backend.presentation/serialization安全投影。GET result和NLI读取已存结果，不调用Harness。LocalNLI失败只产生diagnostic对象，主判断已结束，不反向进入Agent输入。



阅读任务：重启恢复时为什么queued/running变interrupted而不是继续worker？没有供应商幂等保证和完整续执行证明，自动重发会重复收费、改变历史。恢复不等于重新执行。



## 对每个函数问五个问题



- 输入来自用户、数据库、模型还是程序派生？信任边界不同。

- 输出是否绑定task、answer和knowledge版本？有没有跨版本缓存？

- 哪些非法字段会抛异常，哪些业务未知会合法返回？

- 函数是否改变状态/数据库，还是纯转换？

- 测试是否走真实生产调用路线，还是只手工构造内部对象？



例如strict_json拒绝重复键，避免模型输出两个status被普通json.loads静默保留后者。它能保证唯一键，不能保证status语义正确。source_identity生成稳定定位，不证明原来源权威。fuse_ranks融合排名，不执行事实核验。



## 面试阅读练习



练习1：注释掉某个validate_review会发生什么？参考：未知/错版本依据可能进入结果，影响政策和存储；不是“更宽容”而是失去边界。练习2：只删除旧协议文件能简化当前模型消息吗？不一定，应检查真正拼装模板与运行profile；清代码目录不等于减少输出字段。



面试说法：“我能从API沿submit/worker/Harness读到审核解析，解释每个边界可证明什么。代码摘录绑定实际版本和哈希，历史协议不冒充当前默认。”






::: answer 阅读练习：写出本章对象流
先沿本章正式请求表写出输入、输出与版本，再挑一个失败点找异常处理和测试入口。可用[第27章的接单与保存练习](27-service-storage.md)核对应用层对象。
:::

## 历史内容定位

整理前原文完整保留于[历史快照](../archives/14-code-tour.md)；这里只放一套旧定位。

::: answer 展开历史内容定位
<a id="v7只读标注源码路线"></a>

- [v7只读标注源码路线](../archives/14-code-tour.md#v7只读标注源码路线)

<a id="当前源码身份与读法2026-10-27维护同步"></a>

- [当前源码身份与读法（2026-10-27维护同步）](../archives/14-code-tour.md#当前源码身份与读法2026-10-27维护同步)

<a id="2026-10-24历史真实验证边界"></a>

- [2026-10-24历史真实验证边界](../archives/14-code-tour.md#2026-10-24历史真实验证边界)

<a id="2026-10-24-简化合同与投影的源码入口"></a>

- [2026-10-24 简化合同与投影的源码入口](../archives/14-code-tour.md#2026-10-24-简化合同与投影的源码入口)

<a id="2026-10-24-审核链v2实证更新"></a>

- [2026-10-24 审核链v2实证更新](../archives/14-code-tour.md#2026-10-24-审核链v2实证更新)

<a id="实际代码摘录本轮重新核对"></a>

- [实际代码摘录（本轮重新核对）](../archives/14-code-tour.md#实际代码摘录本轮重新核对)

<a id="既有源码练习历史题保留"></a>

- [既有源码练习（历史题保留）](../archives/14-code-tour.md#既有源码练习历史题保留)

<a id="schema13双通道候选的源码边界"></a>

- [schema13双通道候选的源码边界](../archives/14-code-tour.md#schema13双通道候选的源码边界)

<a id="2026-10-28-来源优先代码入口默认关闭"></a>

- [2026-10-28 来源优先代码入口（默认关闭）](../archives/14-code-tour.md#2026-10-28-来源优先代码入口默认关闭)

<a id="2026-10-28-v3真实入口与归档重读"></a>

- [2026-10-28 v3真实入口与归档重读](../archives/14-code-tour.md#2026-10-28-v3真实入口与归档重读)

<a id="2026-10-28-v4版本与入口身份"></a>

- [2026-10-28 v4版本与入口身份](../archives/14-code-tour.md#2026-10-28-v4版本与入口身份)

<a id="2026-10-28-v5隔离入口与冻结源码"></a>

- [2026-10-28 v5：隔离入口与冻结源码](../archives/14-code-tour.md#2026-10-28-v5隔离入口与冻结源码)

<a id="2026-10-28-v6独立版本与源码冻结"></a>

- [2026-10-28 v6：独立版本与源码冻结](../archives/14-code-tour.md#2026-10-28-v6独立版本与源码冻结)

<a id="2026-10-29-v7ab独立身份与默认关闭"></a>

- [2026-10-29 v7：A/B独立身份与默认关闭](../archives/14-code-tour.md#2026-10-29-v7ab独立身份与默认关闭)

<a id="boundedpairadaptercomplete"></a>

- [旧位置转到归档](../archives/14-code-tour.md#boundedpairadaptercomplete)

<a id="dosu修订上下文"></a>

- [旧位置转到归档](../archives/14-code-tour.md#dosu修订上下文)

<a id="rrf融合不保证支持"></a>

- [旧位置转到归档](../archives/14-code-tour.md#rrf融合不保证支持)

<a id="waves"></a>

- [旧位置转到归档](../archives/14-code-tour.md#waves)

<a id="一次有界审核批次"></a>

- [旧位置转到归档](../archives/14-code-tour.md#一次有界审核批次)

<a id="严格json只验证结构"></a>

- [旧位置转到归档](../archives/14-code-tour.md#严格json只验证结构)

<a id="修改授权与意见记账"></a>

- [旧位置转到归档](../archives/14-code-tour.md#修改授权与意见记账)

<a id="受预算约束的完整闭环"></a>

- [旧位置转到归档](../archives/14-code-tour.md#受预算约束的完整闭环)

<a id="固定证据生成诊断入口"></a>

- [旧位置转到归档](../archives/14-code-tour.md#固定证据生成诊断入口)

<a id="复用装配与固定evidence入口"></a>

- [旧位置转到归档](../archives/14-code-tour.md#复用装配与固定evidence入口)

<a id="恢复不自动续跑"></a>

- [旧位置转到归档](../archives/14-code-tour.md#恢复不自动续跑)

<a id="恢复实际输入与知识身份"></a>

- [旧位置转到归档](../archives/14-code-tour.md#恢复实际输入与知识身份)

<a id="来源身份不等于权威"></a>

- [旧位置转到归档](../archives/14-code-tour.md#来源身份不等于权威)

<a id="短事务边界"></a>

- [旧位置转到归档](../archives/14-code-tour.md#短事务边界)

<a id="确定性政策与执行完整性"></a>

- [旧位置转到归档](../archives/14-code-tour.md#确定性政策与执行完整性)

<a id="精确标注入口identity"></a>

- [旧位置转到归档](../archives/14-code-tour.md#精确标注入口identity)

<a id="精确标注入口locate"></a>

- [旧位置转到归档](../archives/14-code-tour.md#精确标注入口locate)

<a id="跨语言词项入口"></a>

- [旧位置转到归档](../archives/14-code-tour.md#跨语言词项入口)

:::
