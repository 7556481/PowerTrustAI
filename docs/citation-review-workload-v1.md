# 引用审核工作量边界 v1

## 2026-10-04 schema13修正后接线回归（最新验证范围）

冻结代码fb235746a734edc94bd60a93988db15db473e884，经HTTP API原样复用前批问题、回答、两项引用及知识，唯一新run `b4ede2ab53f54ec396f6083e6113aa7c`。输入SHA、配置与提示版本一致，新目录/运行库；旧31459a失败保留。本节接续下文“修后未验证”的历史状态，不改写前批结果。

预期初审提取/独立事实/原引用组/领域各1请求。自然一次Revision后，实际提取2、独立事实2、原引用组2、领域2、Revision初始1+纠正1，共10。初次Revision没有实际修改，被business_revision_needs_an_actual_modification拒绝；既有一次纠正有效，再重提取/双审完成。按消息用途与响应逐项核验，不以总请求数代替完成证据。

独立消息73077/131623字符均实际发出且有效返回，超过原引用64000容量；原引用组10824/10593字符。v1两项绑定各自候选范围有效、均supported；v2自然合成1项、显式绑定2条Evidence，也supported，未跨项借用。Evidence回查一致、重启结果一致且10→10无重发；旧/新各自存储记录保留。

最终独立事实、原引用、领域均执行完成，execution_issues为空、required_stages_complete=true；all_required_checks_assessed=false、review_required。v2独立事实6 supported/2 not_assessable：索引元数据来源未经正文确认、复核建议不是可核实事实。领域缺engineering_context、完整单位检查及实际工程分析；无仿真。这些是业务无法评估/前提缺失，不是容量或结构失败，不宣称语义普遍正确。

输入129505/输出5756/总135261token，cache hit21248/miss108257；HTTP全程51.830秒，适配器2026-10-02价目估算USD0.019755894–0.039511788，非账单、未本轮重查价格。无运行代码/政策/检索变化，无浏览器交互/引用编辑器或PDF重生成，不重跑历史或离线测试，444项为既有证据。8766专用服务已停止。

材料：data/runtime_local/citation-review-workload-v1/schema13-final/reading-notes-final.md、verification-final.json及冻结计划/API结果/trace/逐请求响应SHA/Evidence回查/重启记录。仅相关非敏感文档独立本地提交，不推送、不启动新实验。

更新：2026-10-04。真实服务显式装配schema13 / evidence-verification-v9.5-bounded-citation-groups；schema12/v9.4保留，历史结果不迁移。继续使用原Harness、BM25、固定知识、模型、支持要求和有限修订政策。

## 诊断与实际调用

生成v3、Revision v2的带引用回答单元转成CitationBinding；一项可有多个Evidence，相同Evidence绑定不同正文区间仍是不同检查。没有把响应字符上限当成合理模型调用预算。

提取v7最多32个主张/64个非主张。独立事实请求集中审核全部可审核主张及组件，主张数影响消息/输出容量，不是每主张一次请求；领域另一个请求，两路并发共用ModelBudget。旧schema12每原引用绑定一请求，事实阶段共用最多一次纠正。

新事实阶段调用量：独立请求I（有可审核主张为1，否则0）+原引用分组G+阶段纠正F（0或1）。其他生成、提取、领域、Revision各有初始请求及至多一次纠正，最多一次Revision后重新提取、双审。给定两轮G时，完整问答结构上界为`16+G_v1+G_v2`，已有回答为`14+G_v1+G_v2`。这是条件表达，未来修订引用数量尚未知，不能称为提交前已证明的总最坏成本。

例如旧路径已有回答两轮各14个引用，允许各阶段纠正时结构上界42，可能提前耗尽默认40；新路径消息能容纳时两轮各1组，对应16。长Evidence或修订新增引用仍可能增加分组；运行40次保护不等于完整性保证。历史96014是临时异常验收配置和设计教训，原记录不改，不作为当前推荐。

## 分组、配置和失败边界

复用CandidateScope、joint.parse、fidelity、WireIsolation、structured_request。按citation_index稳定贪心分组，每项保留完整原绑定Evidence候选及回答区间。相同Evidence也因check_id生成不同命名空间；逐项严格解析，禁止跨项、独立或其他版本ID借用。错/重复ID被拒绝，有效同级结果保留；独立支持不能消除原引用不足。

| 启动环境变量 | 默认 | 依据与边界 |
|---|---:|---|
| POWERTRUST_CITATION_BATCH_ITEMS | 32 | 8000输出token按每项约250token的规划空间，与提取32项规模一致；不限制回答总引用数。不是保证所有语言/理由都装得下，35项回归分32+3。 |
| POWERTRUST_REVIEW_MESSAGE_CHARS | 64000 | 原引用组完整system+user序列化字符数，含候选、元数据、绑定正文；长片段使组变小，单项超出明确报错。字符数不等于token数或成本。 |
| POWERTRUST_REVIEW_CORRECTION_CHARS | 192000 | 原引用纠正完整消息容量；为64000初始+96000响应+诊断留空间。诊断仍可能超出，此时保留peer、不发纠正请求。 |

必须是正整数，纠正容量不小于初始容量，配置写入manifest；API不可临时覆盖。只约束原引用组，独立事实消息保持既有行为。输出8000token/96000字符、模型90秒、单步110秒、总800秒、最多一次Revision与有限纠正均保留；截断响应不能通过，不关闭超时、不无限重试。

不删除引用、漏检查或截断证据后放行。单项容量无法处理时保留not_assessable占位和具体索引ExecutionIssue，不改成contradicted。提交时已知的已有回答单项容量错误先返回422；生成/修订后才知道的在对应事实阶段保存部分结果。

已知分组后比较剩余初始请求与共享预算剩余额度；不足记录REVIEW_WORKLOAD_BUDGET_SHORTFALL，继续完成可负担检查，额度耗尽停止。纠正和未来Revision由实际计数管理，不做未知成本的过度保守整批预检。默认日常主动真实提交无需逐批授权。

## API薄接线与复现

已有字段兼容。可选existing_citations仅用于真实assess_existing，每项start_offset/end_offset（Python Unicode字符索引，左闭右开）及fragment_ids。服务端KnowledgeStore从固定快照回查完整Evidence，建立CitationBinding，通过既有indexed_reference_ids交同一个Harness复验。未知片段、错误模式/区间返回422，不接受路径、客户端来源字段或外部下载。网页普通表单暂不编辑高级绑定，HTTP客户端可提交；结果、版本、Evidence与反馈结构不变。

```json
{"mode":"assess_existing","question":"概念审核","existing_answer":"待审正文。",
 "existing_citations":[{"start_offset":0,"end_offset":5,"fragment_ids":["快照内的实际fragment_id"]}]}
```

```powershell
cd D:\PowerTrustAI
& .\.venv\Scripts\python.exe -m backend --demo --port 8765
# 日常真实运行会产生实际模型费用
& .\.venv\Scripts\python.exe -m backend --port 8765
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

页面http://127.0.0.1:8765/，令牌及启停见[统一运行入口](prototype-v0.1.md)。资料页/字符定位是提取文本，不是已核对PDF视觉原文。API继续使用本机令牌；模型密钥仅服务端加载。本轮8766专用服务已停止，独立运行库和全部原始材料保留在忽略目录data/runtime_local/citation-review-workload-v1/，不覆盖旧运行库。

## 验证、真实失败与剩余限制

离线回归覆盖稳定分组、项级候选范围、跨引用借用、错/重复ID、有效同级保留、容量边界、修订新增引用/版本、阶段共用一次纠正、并发共享计数、schema12兼容、schema13装配、API输入拒绝与结果重启保存。数量证明工程行为，不证明语义正确。

最终完整离线444项通过，77.648秒；日志offline-tests-delivery.txt。原始3份消息与响应哈希及各项选择自己的候选ID核验见raw-archive-complete.json；早期核验脚本匹配错误的messages文件名而生成空请求清单，原文件保留，不把空清单称作验证完成。

一次真实API run `31459a713aaf47ff801b725b80335af7`：冻结构造概念回答，2项真实Evidence绑定、1组；两个原引用均supported。实际3调用（提取1、引用组1、领域1）、0纠正、0Revision。执行12.703秒，HTTP全程16.280秒。输入15002/输出793/总15795token，cache hit1408/miss13594。按适配器2026-10-02价目快照估算USD0.002519124–0.005038248；本轮未重新查价，非账单。Evidence回查一致，冻结版本重启后完整结果一致、调用仍3。

真实失败：冻结实现误把64000字符原引用组容量用于独立事实消息，正常独立请求被拦截，最终review_required，必需阶段未完整。两个supported原引用不证明全部事实已审。先重启核验、归档冻结源码，再将容量收窄到原引用并补大独立消息离线回归；没有修后重跑付费任务。最终源码与真实冻结源码SHA分别登记，不能当同一版本。修正后的完整真实双审尚未再验证，本轮真实验证范围仅新原引用分组/作用域接线及持久化。

其他真实失败与开发记录保留：测试曾错用ExecutionIssue.error_code、测试大响应先被旧默认响应容量拒绝；API接线漏schema13增强输入名单；私有脚本直接运行缺项目根模块路径、GBK输出数学字形失败；文档patch标题匹配原子失败。已对应修正，原测试日志及冻结失败不覆盖。

目标/fidelity混淆、缺工程前提、无仿真、客户端无服务端幂等仍保留；没有通用准确率或认证。手册Markdown仅补当前限制状态，旧PDF不重生成。本轮独立本地提交，不推送、不改写历史。
