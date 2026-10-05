# 产品逻辑与性能改进 v1（2026-10-05）

本轮从76641c715c965dc191818b2bf0cc233db896e191接续，旧政策与归档不回填。日常真实装配当前product-decision-v1.1，原四Agent、OfflineHarness、schema13/领域4/Revision2、BM25/aggregate、固定知识版本保持；NLI默认关闭，仅独立诊断。学习站、长手册、训练、扩充和检索调参暂停。

## 修改前诊断

LimitedRepairPolicy在最终阶段强制review_required；Harness的真实模型gate再次将pass转为复核。旧DecisionKind/RunState没有“不通过”终态。schema13已有逐组件technical_truth、正文/元数据/输入/计算/范围分离；领域演示规则不能证明权威工程风险。默认工程scope缺失时要求补前提，概念用户需明确请求范围；页面现在提供范围选择，实际主张仍独立审核，选择概念不能豁免性能承诺。

## 处置表与适用范围

| 条件/代码 | 处置 | 依据与限制 |
|---|---|---|
| ALL_REQUIRED_CHECKS_COMPLETE | 通过，限定低风险 | 非空逐主张/组件审核、引用独立检查、领域适用检查完整；无执行/支持/分类/缺前提问题 |
| REPAIRABLE_ERROR | 最多一次Revision，重新提取并完整双审 | 定位明确的事实或原引用矛盾；其他缺口保留，不因修订直接通过 |
| UNRESOLVED_ORDINARY_ERROR | 不通过，中风险 | 有依据的普通矛盾经一次修订仍未解决；不机械称高风险 |
| REVIEWED_HIGH_RISK_RULE | 不通过，不自动修订 | 经审阅的非演示规则注册、当前主张ID及逐字正文依据；生产注册目前为空，机制只用synthetic_fixture验证 |
| UNVALIDATED_HIGH_SEVERITY / DOMAIN_JUDGMENT_DISPUTE | 人工复核，风险未知 | 模型high、题目风险、demo告警本身不能证明高风险回答 |
| FACT_BASIS_MISSING / REQUIRED_INPUT_MISSING | 待补充，风险未知 | 缺依据/必需工程输入/分析；不是事实矛盾 |
| REQUIRED_EXECUTION_FAILED / EMPTY_OR_MISSING_REVIEW / UNCOVERED_ANSWER | 执行未完成 | 超时、输出契约、漏检查或空审核，不自动当业务错误 |
| COMPONENT_CLASSIFICATION_UNCERTAIN / NONCLAIM_CLASSIFICATION_UNCERTAIN | 人工复核 | 分类、立场/原文fidelity及未审核文本不能绕过technical_truth |
| REGISTERED_CALCULATION_REQUIRED | 待补充 | 数学关系需要匹配的成功注册工具记录；现有工具只支持有限标量SI换算 |

执行完整性、风险严重度、最终处置、问题解决程度分字段。resolution来自已审核回答与missing_information，不能当独立的语义回答完整性测量。概念/资料正文由既有组件basis_target与assertion_role记录分类依据及不确定性；数学、元数据、输入快照、范围/建议各保持原义务。地区设定和工程性能不能仅凭文学支持通过，没有做工程仿真。示例领域规则全部仍为demo；量纲/枚举程序只在有限语法适用，未知不伪造无问题；领域建议不升级权威标准。

## 实现入口

- harness/product_policy.py：新处置与原因代码；harness/policy.py原政策保留。
- core/models.py、core/validation.py：新增ProductDecision/处置字段、通过防空/完整性合同。
- harness/runtime.py、states.py：新政策独立分支及终态；每次修订完整重审，各review_round独立报告。
- backend/config.py、assembly.py：普通服务显式新政策；legacy-v1可复现旧行为，manifest保存源码/配置。
- agents/generation.py：独立product-v1提示后缀，正文与索引行政声明明确归属，尊重简短要求，不减少必要限定/审核。
- backend/service.py、presentation.py、static：持久化/API/独立版本处置、最终回答优先；失败投影不回填原报告，固定令牌/连接记忆保留。
- rag/storage.py、retriever.py：只读连接内已验证PDF抽取缓存，data_version/total_changes及文档版本/哈希身份；外部提交使缓存失效，完整BM25排名重放与原文/ID/范围校验保留。不缓存业务判断。
- tests/test_product_policy.py：公开机制、真实schema13/领域4合成贯通、缺检查拒过、修订重审、high规则机制、工具缺口、缓存篡改失效。

## 固定验证与真实结果

运行前冻结7类开发预期，官方资料判断来源AI辅助用户监督，不称专家金标准。高严重度没有可靠当前生产判据，用明确synthetic_fixture证明规则机制，不宣称模型真实识别能力。额外合成案例检查未经核实high只复核。合成API检查保存版本/反馈；真实schema13/领域4合成贯通证明新政策可自动通过。

真实4案例各只运行一次，14请求、输入148836/输出5340 tokens，无格式纠正、无实际Revision；执行完整4/4，冻结业务预期一致2/4，错误通过0、错误拒绝0，两个预期未解决。均待补充：

| 案例 | 秒 | 真实发现 |
|---|---:|---|
| 概念问答 | 21.54 | 两个核心技术命题supported；生成额外地域/自愿性声明被提取成正文事实，正文不支持，未达到预期pass |
| 明确否定 | 11.95 | Fact正确contradicted；领域另有缺前提，最初v1优先待补充，未自然Revision |
| 虚构资料不覆盖 | 14.74 | 证据不足；标量转换不能证明不存在的规范内容，符合预期待补充 |
| 缺厂站数据的性能保证 | 15.81 | 三个主张缺证据、缺工程输入/分析，符合预期；不把高风险话题机械标高 |

保留最初v1源码、冻结配置与全部原结果。根据本轮诊断新增v1.1：定位明确矛盾可有限修订，其他缺口仍在完整重审中阻断通过；保存原发现的政策重放变为revise，不是新Agent判断/真实Revision。新版生成提示及真实Revision本轮没有再请求模型验证，不能以离线回归代替。不得重跑直到满意。

直接AI对照先发生一次MODEL_REQUEST_REJECTED（原适配器JSON输出参数与自由文本提示不匹配）。保留失败，用户随后授权只继续4项审核，未重跑对照。没有有效直接AI响应，因此不能交付质量/速度对照结论。计划的证据输入亦不同（直接AI无检索，系统有），即使成功也只能比较整套方案。

性能同配置/同完整结果哈希3次局部对照：检索＋验证重放中位1.213→1.144秒，约5.7%；保留24→1次PDF抽取验证、其余23命中，原文完整与排名哈希一致。不能推为系统总体提速。真实不同query/资料池耗时更高；逐阶段、请求token、消息/证据重复统计在私有metrics-final.json。没有降低必需覆盖、截断正文或修改默认检索；原引用已批量32，不新建Agent/调度器。第一概念客户端首反馈时间在验证驱动归档错误中未保留；其余已有回答首保存时间不等于生成首反馈。真实实验进程峰值RSS未及时保留；普通CLI浏览器验收峰值约61.2MiB另列，不混充真实训练/推理资源。4个异质案例不报告稳定P95承诺。

浏览器实际检查通过、不通过、待补充、复核、执行未完成、版本、反馈和NLI关闭；重启11运行/事件/对象/反馈整体哈希不变。已有记忆自动鉴权，未要求重输。无鉴权访问保护保留；查询不重发模型。

## 所有者试用

先用普通入口演示，不会加载.env或付费模型：

```powershell
Set-Location D:\PowerTrustAI
& .\.venv\Scripts\python.exe -m backend --demo --port 8765
```

本机记事本查看data/runtime_local/access-token（勿发聊天），主动选择记忆后同浏览器/地址复用；忘记清除，401清除，普通重启不轮换。页面问答/已有回答选择请求范围，查看最终回答/处置，再展开依据、原回答、版本和反馈。演示是模拟判断，不能评价语义正确率。

真实模式使用同一入口，项目本机.env配置DEEPSEEK_API_KEY、DEEPSEEK_MODEL_ID，值不放Git/浏览器。具备已有固定知识库及锁定API依赖：

```powershell
& .\.venv\Scripts\python.exe -m backend --port 8765
```

保留默认BM25/aggregate、40单运行保护、有限纠正、一次Revision/超时。真实提交会付费；重复点击被防护，但不会自动重发未知状态任务。工程数据/工具换算/固定原引用可使用/docs现有POST /runs的engineering_context、quantities、existing_citations字段；界面不虚构工程参数。按Ctrl+C停止；重新启动保留历史。POWERTRUST_DECISION_POLICY=legacy-v1只在明确复现旧政策时使用；默认product-v1。POWERTRUST_RUN_DB可选择独立运行库，日常固定token不随库/模型变。

审阅ZIP/verification-final在忽略data/runtime_local/product-improvement-v1。包含诊断、冻结输入/预期、原结果、政策重放、阶段/性能记录、截图/重启/测试/哈希；不含凭据、完整PDF、数据库或权重。新版真实生成与Revision、直接AI对照及生产高风险语义能力仍待共同验收。当前可试用不等于项目全部完成；本轮停止，不自动开启新实验。
