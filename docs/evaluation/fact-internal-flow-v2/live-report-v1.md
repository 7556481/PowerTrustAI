# v2固定参考真实复验：六项完成，语义仍有缺口

本批由用户接受v2实现及六项材料后授权，仅执行v2的F01、F02、F03、F04、F05、F08，各一个初始请求。起始HEAD `7ba2ca7c2f636e7f74c255dcd2c47cf89a519818`、工作区干净。[原对照提案](revalidation-plan-v1.md)原样保留，另存[实际执行计划](actual-execution-plan-v1.json)和[实际源码/消息冻结](execution-freeze-v1.json)。回答、题设、证据、参考及评分未改。

**6/6分支执行完整，7/7组件有合法最终结果；首次契约有效4/6。共8次调用（6初始＋2纠正）、18665 token。无最终执行失败、无未执行项。本批已结束，不追加、不补跑、不恢复，生产不变。** 本批是固定参考开发复验，历史v1仅描述性参考，不计算严格配对提升率；不能从执行完整推出语义全部正确。

材料：[全部必要响应原文（含两次无效初始）](live-predictions-v1.json)、[小统计](live-results-v1.json)、[私有归档身份](live-artifact-identities-v1.json)、[原输入及独立参考](inputs-and-reference-v1.json)。公开语义核对为AI辅助、用户监督，不称专家金标准或独立留出测试。

## 逐项核对

|案例|首次结构／最终执行|最终原始支持 → 有效支持|语义及依赖核对|
|---|---|---|---|
|F01规则与实例|有效／完整|规则supported→supported；应用supported→supported|分别为literature_rule、rule_application。规则只选S0B0；应用选S0B0＋P0年龄19，排除蓝卡P1。许可而非强制义务保留；应用条件片段确在同一答案段中。|
|F02错误实例|有效／完整|contradicted→contradicted|规则与8度题设均入选，识别8不满足不高于4度，并提出不可入库的修复文本。未实际调用Revision。条件字段另标缺失/空片段，但答案已提“不高于4度”，可能混淆条件出现与条件满足，不能把正确标签当全部字段可靠。|
|F03相关题设|有效／完整|supported→supported|选S0B0规则＋P0学分24；未选背包颜色P1、学生编号P2。条件载体“至少20学分的报名条件”可定位。|
|F04数值来源|初始无效、一次纠正有效／完整|supported→insufficient_evidence|两次都保留P0分数71与S0B0基准64，排除姓名P1；Decimal比较true。但条件判断未语义解决，详见下文。|
|F05分类故障|初始无效、一次纠正有效／完整|insufficient_evidence→not_assessable，review_required|最终有模型明确分类异议、fidelity faithful、origin model_judgment，不是失败占位，也未静默改类通过。但对象仍uncertain，内容支持未符合supported参考，仍选无关3页题设，不能整体算正确。|
|F08工程关系|有效／完整|insufficient_evidence→insufficient_evidence|明确资料未给寿命模型、温度或试验数据，不能由电流5安推寿命50年；comparison=null，未把标量能力当工程认证。正文与当前电流作为论述依据选入。|

### F04：来源保留，条件仍未解决

初始把正文片段“本表比较基准为64分”填入answer_quote并声明preserved=true；该片段属于来源正文，不在实际答案“题设分数71大于正文基准64。”中，程序拒绝`preserved_requires_literal_carrier`。唯一纠正保留两数值来源与supported，却将条件改为required=true、preserved=false、answer_quote为空；理由仍说“数值关系成立”。结构上已一致，程序据必要条件缺失降级insufficient_evidence。

因此“两来源与标量关系”已形成有效记录，“条件判断符合此题语义”没有通过：原答案已明确71与正文基准64，本题参考仍为supported。不能用有效不足代替所需判断，更不能将原始supported包装成最终通过。程序没有自动摘取片段、删除条件或补写解释；本批不在观察后再修改提示。

### F05：有效异议通路成立，规则语义仍错

初始object_kind=rule_application、classification_objection=null，与冻结input_evidence_coverage对象不一致，触发`changed_obligation_requires_explicit_objection`。初始将规则误读为必要条件，并称答案没有引用当前3页题设、把条件许可改成无条件许可；内容为insufficient_evidence。

纠正后模型明确写出：

> 所给类别为input_evidence_coverage/input_provided，但命题是对档案规则内容的复述，证据是对规则文本的覆盖，不是对输入证据是否提供的判断；宜按可评估的规则内容判断，而非输入提供覆盖。

该异议来自模型原文；程序只提示声明矛盾，不替它改分类。最终object_kind=uncertain、fidelity=faithful、review_required，满足“有效异议处置”层预期，且不是首次自发完整识别。内容层仍为insufficient_evidence而非参考supported；dependencies仍有P0“本次记录有3页”。最终reason称“未保留条件/许可方向”，conditions却对“至少2页”声明required=true、preserved=true，理由与条件记录仍有语义张力。程序无法仅凭字面布尔关系裁决这类语义矛盾，不能悄悄修正。

## 分母、结构与开销

- 全部计划：6案例、7组件；6分支完整、0失败、0未执行。初始有效4/6（F01/F02/F03/F08）；F04/F05各一次结构纠正，最终有效6/6。共8份模型响应，其中2份初始无效、6份有效。
- 最终原始支持：supported 4、contradicted 1、insufficient_evidence 2。最终有效支持：supported 3、contradicted 1、insufficient_evidence 2、not_assessable 1。分别统计，不能混合。
- 常规固定参考集合F01/F02/F03/F04/F08共5案例6组件，全部已执行：raw标签对齐6/6，effective标签对齐5/6（F04未对齐）。这是本组开发材料的标签对齐，不是通用正确率；理由及条件仍需逐项复核。
- F05另列预置故障诊断：首次有效异议0/1，纠正后有效异议1/1；有效处置符合参考，但内容支持0/1符合参考，规则种类与无关题设仍有错误。不以额外无法评估宣称语义改善。
- 三个实际规则应用（F01应用、F02、F03）均选相关规则＋目标题设，未混入无关题设；两个规则复述观察中，F01正确，F05仍未解决。F04两来源正确，不代表条件判断正确。未检查的F06/F07不计为本批通过。
- 输入16920、输出1745、总18665 token；缓存命中5248、未命中11672。模型时长合计14432ms，分支时长合计15.068秒，不是首绘时长或计费账单。实际账单金额未知。不计算与历史v1的配对提升率、提速率或省费率。

## 程序、模型与留存边界

程序控制独占attempt、固定顺序、v2-only门禁、发送前消息SHA、ID/来源/版本绑定、预算与超时、最多一次纠正、字段一致性、标量比较、失败停止和保存。对象分类、相关依赖、必要条件、许可/因果方向、完整支持及异议理由仍由模型判断。实际所有初始请求匹配接受的v2准备消息；纠正消息随响应生成并在发送前保存，未带参考标签。无新增检索或工具调用，也未执行生成、领域、修订或服务候选验收。

最小入口`evaluation/fact_internal_flow_trial_v2.py`复用旧顺序归档循环，只以参数注入v2构造器、12次硬帽和新批次身份；共享循环另保存取消时的部分结果。模型/提示/解析/政策未改。实际冻结155文件，允许的唯一旧文件演进为该归档循环参数化，其他已接受源码哈希必须一致。

23项相关离线检查通过4.402秒（7新批次门禁、6旧批次门禁、10 v2契约专项）：成功六项持久化、一次纠正、合法同伴、发送前/响应后/输出存储失败停止、超时/取消停止、v1或乱序/消息哈希拒绝、attempt及源码变动拒绝。上轮1174完整回归保留，本轮仅执行入口/门禁/归档材料改动，未重复整套；离线替身不当语义分数。

原始输入/消息/响应/输出均留Git忽略的data/retrieval_local/fact-internal-flow-live-v2，attempt保留禁止恢复。根.env仅由既有授权运行入口加载，未读取或归档凭据/请求头。公开必要预测、短报告、小统计及冻结身份，不复制数据库/模型/项目、不制作大包。旧批归档与原提案/参考保持不变。

本批有完整执行和有效异议通路的观察，但F04条件、F05规则语义与无关题设仍是明确限制。整批由用户复核后，再决定是否进入服务候选验收；本轮不自动开启优化、新付费批次或生产切换。
