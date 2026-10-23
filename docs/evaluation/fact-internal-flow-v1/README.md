# 事实审核内部流程 v1：候选交付与对照材料

状态：离线候选；生产未切换，真实模型调用为0。不是 A 生成映射、B 提取器或评测侧 v7 的生产接入。起始 HEAD `efbc2840938f26ac006b88a098d5214ba9e69f8e`，保留此前三个未提交文档。

## 实际基线与问题纠正

只读 `/health` 核对本机服务 ready、空闲、外层 langgraph_v1、BM25/aggregate、知识版本 `kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e`。受管 orchestration.json 与健康接口一致。源码 Factory 生产入口为 ModelEvidenceVerificationAgent/schema13、生成schema3、提取protocol7（生产提取器，不是评测侧v7）、领域5、修订2、product-decision-v1.5；fallback sequential。未加载 .env、读取凭据或重启生产。只读生产运行库白名单字段确认最新保存配置为deepseek-flash、schema13、product-decision-v1.5、v9.20提示；该历史记录无execution_path字段，当前外层路径以健康接口为准。当前生产四表计数为104/2278/2999/8。健康接口不暴露模型／schema字段，故不把保存配置冒称实时进程内省。后续对照固定deepseek-flash。

B 的 `validate_selected` 实际有三个集合：任务目录 catalog；提取器的 component_premise_ids；审核 bases 中选中的题设 IDs。门禁要求审核集合属于当前组件集合，确定性结论进一步要求两者相等，**不是要求所有任务登记题设**。旧草案概括已纠正。B v1非强制规则被归应用、v2数值比较仅选题设的失败均保留，不恢复批次。独立24回答评审组件的完成率不替代生产事实审核，也不作为本候选语义成绩。

## 实现及实际内部决策

输入仍是 ReliabilityVerificationInput。程序生成当前回答/版本/组件目标和合法依据目录，题设使用原有精确位置/上下文哈希绑定；不修改生成、提取、领域或修订Agent。新 FactFlowOutput 保留独立 object_reviews、flow_trace，原输出历史读取继续；Store按既有数据类序列化，API提供 fact_internal_flow 诊断。

|节点|输入／输出与责任|模型调用|
|---|---|---|
|prepare|实际对象、Evidence、题设→局部target/basis IDs；版本、位置、作用域合法性|0|
|review|合法目录→对象分类、实际依赖子集、支持关系、条件、忠实性和分类异议|独立事实1次；原引用按既有容量分组|
|gap|失败／不足／工程限制→返回既有共享阶段；不新增工具或循环|0|
|summarize|保留合法同伴、未执行占位及原始语义，交既有政策|0|

[节点图](node-graph-v1.md)。图实际控制上述节点，retry_policy为空、无checkpoint/自动恢复、关闭远程追踪；外层共享阶段仍拥有已有有限补检和修订重审。没有额外规划调用。只有出现新的合法依据、且既有外层规则和预算允许时，才会再次审核；不搜索到通过。

新版本 `fact-internal-flow-v1` / `evidence-verification-v9.30-fact-internal-flow-v1-dev`：模型选 target_id/basis_ids，不复述父身份、类型、偏移、版本和派生状态。object_kind、classification_objection 与 fidelity/fidelity_reason 分轴；跨提取类别改变义务必须显式异议，异议不能直接pass。错误回答可以忠实提取；支持与分类分开。规则复述不借当前题设；实例应用要求实际选择的相关规则正文和 stipulated 题设，不要求全集，无关题设是否相关仍由模型判断。

numeric_comparison 明确两个操作数的 value/quote/basis_id 和比较符。程序核对字面来源、合法局部ID与有限十进制标量关系；可以分别来自题设和正文。数值来源不因简单比较而丢失。单位同一性、语义对应、模型是否遗漏必要依赖仍依赖语义判断。工程关系输出明确没有工程计算器；既有标量换算结果不成为设备寿命或工程公式认证。原引用只能在自己的原始正文范围选依据，不能借独立依据或题设。

## 复用、增长与回退

新增：agents/fact_flow_v1.py（图入口）；services/fact_flow_protocol_v1.py（候选语义契约）；services/scoped_fact_execution.py（抽取共用的有界请求循环）；evaluation/fact_internal_flow_materials_v1.py（纯离线固定材料）；tests/test_fact_flow_v1.py（专项）。

复用：现有适配器、structured_request、WireIsolation、Evidence候选和typed parser、题设精确绑定、条件/修复绑定、预算/诊断、Harness、Retriever、政策与Store。历史compact目录/绑定/保守投影作为可复用实现；其旧请求循环被抽出共享，旧schema14入口仍保持原协议，不切生产14。只复用B的题设身份绑定函数，不采用B的提取器、对象义务或门禁。新增结构类型仅在明确候选输出中允许。

共同接口新增 ServiceConfig.fact_internal_flow；默认 production。开发显式 `fact_internal_flow='langgraph_candidate_v1'`，或仅进程环境 `POWERTRUST_FACT_INTERNAL_FLOW=langgraph_candidate_v1`。仍要求schema13生产基线与真实Factory装配；可以选择外层 sequential 或 langgraph_v1。API增加显式 premise_declarations，仅候选允许，文本必须精确出现在当前question/user_context中。回退恢复 production／移除该进程环境变量，正常重启对应开发服务；本轮没有操作生产切换。服务清单保存实际候选prompt/contract，不能只看数字13识别候选。

保留旧schema13入口、旧schema14、B、A、评测v7、私有历史及冻结文件。没有ZIP、数据库、模型、环境或项目副本。普通版本提交另附完整哈希。

## 离线证据与限制

专项覆盖8主题固定材料，双输入模式真实Factory/worker/外层图/内部图/Domain/Policy/Store/API；实际消息检查契约、合法目录与题设到达；修订后两个版本、两次提取、完整重审。非法ID同伴保留、跨作用域、单次纠正、预算、超时、取消、失败工具不进入成功依据均有测试。替身故意给出判断，只验证程序行为，不能声称分类或支持准确率。

开发失败：Windows沙箱socketpair启动阻塞，工具审批后离线运行；编辑脚本默认GBK读取中文文件失败，改显式UTF-8；新输出未列入严格类型扩展白名单，加入准确类型；取消被LangGraph包装为NodeCancelledError，恢复取消语义并保留部分；测试误从core导入ToolResult，修正真实模块；首轮全套1158项/180.749秒有2项历史冻结检查失败，旧门禁正确拒绝当前源码。测试改用明确冻结夹具验证旧工程变化规则，并单独断言真实旧材料门禁继续拒绝；不改旧freeze或放宽真实执行。

最终完整回归与学习站检查见 [验证统计](results-v1.json)。零真实请求、零语义收益声明。

## 整批真实对照准备，未授权执行

[全部问题／题设／正文／回答／参考标签](inputs-and-reference-v1.json) · [实际离线消息身份与顺序](preparation-v1.json) · [拟执行源码身份](source-manifest-v1.json) · [参考理由与统计口径](comparison-plan-v1.md)。8合成开发案例、16分支，不称独立留出。F05是预置分类故障，单列诊断；没有生成或提取调用，固定实际对象只比较事实审核。原版没有单独题设审核能力，F05/F07缺生成快照将出现程序预条件，必须计入未评估，不能把零调用当性能收益。

本轮只准备；真实执行还需用户整批费用授权及执行时新冻结。禁止恢复任何旧attempt、修改旧标签、为了完成率减少检查或把占位当语义不足。


## 提交身份与实现版本

实现完整提交：`c81c8c5fe2fe3b92c78d212dd76d873f55c5a7c8`。首次提交因未配置Git作者而失败；用户随后明确授权沿用仓库近期本人身份，只读核对最近8次一致后采用命令级配置，未修改全局或仓库设置。文档材料随后单独提交；最终远端哈希见交付消息。
