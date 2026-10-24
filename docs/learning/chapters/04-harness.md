# 04 Harness：状态机、并发、有限纠正与完整重审

本轮实际结果：A8/G4/B8固定批次106请求、1126972token，5条审核执行不完整；候选仅A4进入新修订提示，原版也纠正且没有目标历史叙述，自然8路正文不变。未证明候选净收益，不采用生产；N-1/N-2条件外推和原引用跨单元缺口疑点保留。实际8765保持原停服，无常驻候选。

## 2026-10-24 一次修订与交付净收益

候选复用原Factory、OfflineHarness、四职责、双审核和共享阶段。revision-output-v2的逐ID动作与“至少一项modified且正文改变”门禁没有放宽：归档两条实际Revision都有成立的阈值错误，不能只看条件存在便声称迫使错误改写。modified只是提议改动，retained解释保留，unresolved说明无法解决；任何动作都不代替新版本重新提取与完整双审。

开发入口revision_answer_delivery=answer_only_v1仅改变修订提示，默认production；回退选择production即可，原输出与旧记录兼容。完整离线1197项通过197.256秒，仅证明程序行为。新批使用已有run_fixed、RunStore与独立关闭的只读采集器；单例最终结构失败继续，共享/未知故障停止，已受理不重复提交。真实语义、成本和未执行槽见[本轮报告](https://github.com/7556481/PowerTrustAI/blob/master/docs/evaluation/answer-review-net-benefit-v1/report.md)。

## 2026-10-23 契约审计与v2离线候选

首真实内部候选对照已按F05最终失败停止：12调用、3纠正，后6分支未发送，生产未切。审计实际消息发现旧objection字段要求与新字段禁止并存，以及必填repair缺失、纠正提示禁止复制文本与字面quote字段的歧义。v2使用唯一字段规范供初始/纠正消息共用；程序检查preserved=true必须有回答原片段，并拒绝技术对象以ordinary静默绕过义务；明确异议后ordinary仍可合法转复核。程序不猜分类、不补理由或条件片段。

v2仍一次联合判断，没有额外规划调用。独立对象/义务确认可能减少耦合，但每事实组增加一次初始调用，并可能将分类错误传给支持阶段，当前无证据证明值得。结构接线和完整离线回归通过不代表语义改善；下一次6项开发复验材料仅准备、0真实发送。v2仅显式开发create_agent入口，原Factory/生产默认不变。见[审计与设计比较](https://github.com/7556481/PowerTrustAI/blob/master/docs/evaluation/fact-internal-flow-v2/README.md)。旧段落中的“本轮0调用”为其历史轮次。


## 2026-10-23 事实审核内部流程候选

外层七共享阶段继续管理检索、并发领域审核、预算和修订；内层prepare→review→gap→summarize管理合法目标、一次语义判断及保守汇总。内部没有检索循环和图层重发。gap返回既有共享阶段，不虚构工具。修订仍重新提取、完整双审并保存新版本。

完整材料见[候选报告](https://github.com/7556481/PowerTrustAI/blob/master/docs/evaluation/fact-internal-flow-v1/README.md)。生产未切换，本轮0真实调用。

2026-10-23当前补记：剩余五项固定服务验收完成，本机受管默认已为langgraph_v1，正常服务ready；无配置源码fallback仍sequential。新批32调用、413018token、0失败/未执行；两项诊断实际一次修订和完整重审，但图最终待补充保留，不冒称全部答案认可。四Agent、schema13、七共享阶段及预算/政策不变，A/B未采用。历史104运行/2278事件/2999版本证据对象/8反馈及SHA启动前后相同；原编排可正常停服改受管配置回退。工具浏览器入口已验、登录后视图待一次用户清单，不绕本地文件限制。详见[后续验收](https://github.com/7556481/PowerTrustAI/blob/master/docs/evaluation/langgraph-service-continuation-v1/results-v1.md)。下文2026-10-22及更早状态保留历史含义，以本补记为当前。

## 状态机是什么

状态机把“现在做到哪一步”和“允许下一步做什么”显式化。harness/states.py列举状态及转移集合；2026-10-22抽取后，runtime.py保留入口和任务注册，execution.py的每运行上下文执行转移并记录Trace。显式状态能拒绝“审核未完成就直接completed”的非法路径。终态包括通过、拒绝、待补充、执行未完成、复核、失败和取消。

```diagram
{
  "title": "状态与有界修订：对象重建而非原地抹错",
  "width": 780,
  "height": 670,
  "nodes": [
    {
      "id": "start",
      "x": 30,
      "y": 20,
      "w": 280,
      "h": 60,
      "label": "接收 / 验证\n问答检索生成或已有回答冻结"
    },
    {
      "id": "extract",
      "x": 30,
      "y": 145,
      "w": 280,
      "h": 60,
      "label": "提取主张与真实标量工具\n当前answer_id / version"
    },
    {
      "id": "review",
      "x": 30,
      "y": 270,
      "w": 280,
      "h": 60,
      "label": "并发事实 + 领域审核\n同版本目标 / 各自实际交付"
    },
    {
      "id": "decide",
      "x": 30,
      "y": 395,
      "w": 280,
      "h": 60,
      "label": "政策决策\n执行、发现、解决程度分开"
    },
    {
      "id": "rev",
      "x": 470,
      "y": 395,
      "w": 255,
      "h": 60,
      "label": "最多一次Revision\n新版本 + 完整重提取双审"
    },
    {
      "id": "end",
      "x": 30,
      "y": 535,
      "w": 360,
      "h": 80,
      "label": "终态：通过 / 不通过 / 待补充\n人工复核 / 执行未完成\n失败或取消另记"
    },
    {
      "id": "obs",
      "x": 470,
      "y": 535,
      "w": 255,
      "h": 80,
      "label": "每个阶段observer保存\n旧版 + 新版 / Trace\n网络等待不占长写事务"
    }
  ],
  "edges": [
    {
      "from": "start",
      "to": "extract",
      "kind": "control"
    },
    {
      "from": "extract",
      "to": "review",
      "kind": "control"
    },
    {
      "from": "review",
      "to": "decide",
      "kind": "control"
    },
    {
      "from": "decide",
      "to": "rev",
      "kind": "control",
      "label": "有依据可修复",
      "label_at": [
        328,
        423
      ]
    },
    {
      "from": "rev",
      "to": "extract",
      "kind": "control",
      "points": [
        [
          598,
          395
        ],
        [
          598,
          173
        ],
        [
          310,
          173
        ]
      ],
      "label": "重建当前对象",
      "label_at": [
        405,
        156
      ]
    },
    {
      "from": "decide",
      "to": "end",
      "kind": "control",
      "points": [
        [
          170,
          455
        ],
        [
          170,
          535
        ]
      ]
    },
    {
      "from": "review",
      "to": "obs",
      "kind": "persist",
      "points": [
        [
          310,
          300
        ],
        [
          405,
          300
        ],
        [
          405,
          575
        ],
        [
          470,
          575
        ]
      ],
      "label": "事件/快照",
      "label_at": [
        411,
        553
      ]
    }
  ]
}
```

已有回答入口从validated进入提取，跳过生成。没有实质回答时进入needs_information而非把模板当成功答案。中断、失败与业务不足是不同终态，实际归档保存终止原因。

## 冻结与并发：共享什么，不共享什么

提取完成后，两审核收到同一不可变答案及claim tuple。事实和领域用途检索可以顺序组织，模型审核再并发。asyncio并发适合等待网络，不等于CPU并行，也不意味着请求成本减半。如果一个耗时20秒、另一个15秒，双审墙钟近似较慢者加开销，但仍有两笔请求。

两审核不把对方输出放进首轮提示，避免“事实Agent说对所以领域也说对”。并发失败不能使另一份有效结果消失。保存部分结果时仍标明哪些必需步骤缺失，政策不能以存在一份结果证明全执行完成。

## 有限格式纠正与Revision不是一回事

services/structured_model.py对一条结构请求最多一次有限纠正。它处理JSON、漏字段、错ID等输出合同问题；纠正后仍非法就记录失败，不静默填充。业务Revision则是在已完成的审核发现基础上改答案，需要新回答版本、重新提取和双审。前者不应计为“答案已改正”，后者不应只计一次模型调用成功。

教学算例：初次Fact漏一个组件→一次纠正补齐→Fact阶段合法。这只是结构恢复。如果合法结果指出错误，再Revision把错误改正并全重审，才形成实质业务闭环。结构纠正、业务修订、通过三个计数要分别记。

## 预算、超时和停止

RunBudget控制每运行的模型、工具、检索和修订资源，ModelBudget实际记调用号与deadline。保留有限纠正、最多一次Revision及超时，不为一批开发题临时设任意总帽来掩盖设计问题。结构上引用分组可能增加调用，预算须与完整覆盖兼容；耗尽时保存执行缺口，不减少必需检查假装完成。

取消是合作式的：协程取消不能保证底层线程或网络对端立即停止。后台编码/检索资源需要drain后才能复用或关闭。操作系统线程CPU计算不会因await被自动打断，因此本地模型采用受控工作线程或子进程。

## 一次Revision的门控与记录

ProductAuditPolicy检查真实执行、适用义务和发现，不给模型最终通过权。明确可修复普通错误可以一次Revision；缺证据并非一律可修复。services/bounded_repair.py要求实质replacement与当前选中原文绑定，faithful adverse component可作为局部修复入口，其他缺口不必先消失，但也不能被删除。

修订后answer_version增加。旧finding仍指v1，v2必须重新提取对象和按新版本构建检索绑定。新答案引入的新主张同样审核，不能只检查修复摘要。未解决发现、执行问题及问题解决程度独立保留。

格式纠正只要求模型按原冻结对象输出合法结构，不得偷偷改事实命题；业务Revision改的是用户答案，创建新版本后重提取、双审和原引用检查。一次限制使版本/调用有界，防“改到看起来通过”，不是一次必定够用。失败停止属于执行控制，不等于业务拒绝；完整执行也可以合理待补充。最新真实局部修订闭环见第01/15章，不能用一次调用成功替代闭环验收。

## 如何验证完整闭环

测试需要验证状态序列和对象关系：v1错→Revision→v2新claims→双重审→政策；不是只断言Revision被调用。反例：把v1 claims原样塞给v2审核，可能审核了旧错误而不是新答案。另一个反例：只重跑Fact没重跑Domain，新增工程承诺没有被审。

历史阶段：早期e1c6…运行自然一次Revision及8请求、最终复核；identity-fidelity-v1的ab338原功率因数题仍无修复建议、0Revision。后续schema-choice-v1的schema13实际运行f61a804c…自然将2ω纠正为ω，保留线性时不变、正弦激励、暂态消失，2版本/2轮，完成重提取、双审和原引用检查。该局部闭环已真实验证，原PF失败不改；结构机制验证与通用修订能力仍需分别判断。

## 2026-10-22：7共享阶段接成可选图

`harness/execution.py`的RunExecution持有一次运行的数据和资源引用。`run_stages()`保留原顺序驱动；选择图时，`harness/graph_runtime_v1.py`建立7个真实阶段节点并通过条件边控制下一步，外层`RunExecution.run(driver=...)`仍处理失败、取消、注册清理和结果组装。

```diagram
{
  "title": "可选图实际控制7阶段，Harness保留执行约束",
  "width": 900,
  "height": 760,
  "nodes": [
    {"id":"validate","x":40,"y":20,"w":260,"h":55,"label":"validate_saved_inputs\n固定身份与原索引校验"},
    {"id":"generate","x":40,"y":120,"w":260,"h":55,"label":"generate\n问答检索与生成"},
    {"id":"extract","x":350,"y":120,"w":260,"h":55,"label":"extract_and_tools\n当前版本提取及工具"},
    {"id":"prepare","x":350,"y":230,"w":260,"h":55,"label":"prepare_review\n分别交付两用途证据"},
    {"id":"review","x":350,"y":340,"w":260,"h":55,"label":"review_pair\n节点内部保留双审并发"},
    {"id":"decide","x":350,"y":450,"w":260,"h":55,"label":"merge_and_decide\n原合并与确定性政策"},
    {"id":"revise","x":40,"y":450,"w":260,"h":55,"label":"revise\n有限修订并推进版本"},
    {"id":"end","x":650,"y":450,"w":220,"h":55,"label":"END → Harness\n终止记录及结果组装"}
  ],
  "edges": [
    {"from":"validate","to":"generate","kind":"control","label":"问答","label_at":[185,100]},
    {"from":"validate","to":"extract","kind":"control","points":[[300,47],[480,47],[480,120]],"label":"已有回答","label_at":[355,36]},
    {"from":"generate","to":"extract","kind":"control","label":"审核","label_at":[305,139]},
    {"from":"extract","to":"prepare","kind":"control"},
    {"from":"prepare","to":"review","kind":"control"},
    {"from":"review","to":"decide","kind":"control"},
    {"from":"decide","to":"revise","kind":"control","points":[[350,478],[300,478]],"label":"修订","label_at":[304,465]},
    {"from":"revise","to":"extract","kind":"control","points":[[170,450],[170,410],[325,410],[325,148],[350,148]],"label":"完整重审","label_at":[185,400]},
    {"from":"decide","to":"end","kind":"control","label":"终止","label_at":[610,439]},
    {"from":"review","to":"end","kind":"control","points":[[610,367],[760,367],[760,450]],"label":"仅证据审核","label_at":[650,351]},
    {"from":"generate","to":"end","kind":"control","points":[[40,148],[16,148],[16,715],[760,715],[760,505]],"label":"仅生成或无实质回答","label_at":[320,704]}
  ]
}
```

图中END不是业务pass。失败、取消、observer异常在各阶段退出，仍由原Harness边界处理；未解释差异必须保留并停止推进。图的递归上限按修订预算派生，只防编排失控，不代替模型/工具/检索调用预算。

开发合成示例（不会访问真实模型）：

```python
from agents.fakes import make_fake_harness

harness = make_fake_harness()
assert harness.execution_path == "sequential"
harness.execution_path = "langgraph_v1"  # 安装可选依赖后，仅开发验证
```

直接构造OfflineHarness也可传`execution_path="langgraph_v1"`。该开关不在API任务载荷里，生产组装仍选默认路径。回退是下次开发运行明确选择`sequential`；发生失败的图运行不会自动执行旧驱动再发请求。

## 图适配的验证与开销边界

依赖锁为`requirements-langgraph.lock.txt`：LangGraph 1.2.16，Windows/Python3.13精确轮子哈希。原19个包版本未变，新增依赖包含SDK/checkpoint/追踪库，但没有启用相关服务。图不启用checkpointer、store、cache或RetryPolicy；显式关闭云追踪，即使外层打开追踪也通过无网络替身检查。

业务差分使用同一输入、假模型和合成SQLite快照，比较结果、阶段输入、observer快照、调用归属、消息内容、修订重审和终态；只规范化时钟观测并固定新生成ID序列。独立评审组件另用历史25份响应回放，两路径最终24份预测均与原记录相同；不是重新生成、重评标签或新的语义成绩。原5覆盖分歧、2支持分歧及2未对齐继续保留。

本机无observer、假Agent的30对交错暖运行：无修订中位数原路径2.68ms、图15.99ms；一次修订原路径6.08ms、图22.47ms。单次冷启动原路径4.95ms、图923.16ms，图包含首次依赖导入及编译。这说明编排引入开销，不说明真实服务延迟、费用或准确率变化。

回放工具首次把网络禁用检查放在事件循环创建外，拦住Windows内部socketpair，0次适配器回放、未重建预测。失败目录保留，改为循环已创建、回放开始前禁止连接；最终回放无网络。这个故障不属于原付费批次，更未删除其attempt或补跑模型。

价值是流程更明确、分支更可测试、后续扩展更可控。图不会替我们设计正确的语义边界；真实验证、生产切换和Agent进一步定制留作后续独立决定。

## 练习与面试

练习：Generation调用成功但返回没有引用的拒答，应该进入哪个路径？参考：结合substantive_answer与实际Evidence判断无实质回答，后续提取双审不适用，待补充；若连接失败则执行未完成，不能说证据在全库不存在。

追问：为什么一次而非多次Revision？参考：控制成本、避免模型把问题删到通过、保留未解决限制。一轮是当前有界产品选择，不是理论最优；扩大必须另行评测，不能在看到题目失败后循环刷成功。

面试可说：“Harness管理显式状态和有界资源。两审核并发但共享冻结对象；格式纠正与业务Revision分开，Revision后完整重提取双审，历史版本不可覆盖。”

## 2026-10-22 服务编排配置与失败

服务端通过POWERTRUST_EXECUTION_PATH选择sequential或langgraph_v1；受管orchestration.json只保留版本和合法枚举，环境变量优先。API提交不允许路径字段，用户不用选择内部编排。图依赖缺失或执行失败不自动改回原路径重发；没有图重试、checkpointer、自动恢复。既有共享预算、90秒请求/110秒步骤/800秒运行及一次Revision保持，预算不保证任意输出均能完成审核。

离线固定响应差分是编排等价的主要证据；真实两版回答不同不能直接归因为图。真实运行分别报告必需执行、语义处置、修订是否触发、用量和持久化。首最终执行或存储故障停止后续付费，仍保留已完成同伴和草稿。明确的证据不足或合法复核结论不是编排失败。

当前验收状态：正常服务默认sequential，图已接线但未完成真实服务验收；本批首项原路径服务完成、收集失败后停止，五项未执行。不能称默认切换成功。详见[本轮集成报告](https://github.com/7556481/PowerTrustAI/blob/master/docs/evaluation/langgraph-service-integration-v1/results-v1.md)。

## 三道自测：先作答，再展开

### 自测1：纠正与Revision是否同一事？

::: answer 展开参考答案1
不是；前者恢复输出合同，后者产生新答案并需完整重审。
:::

### 自测2：并发双审是否减少请求数？

::: answer 展开参考答案2
不减少，只可能缩短等待关键路径。
:::

### 自测3：修订后能否沿用旧claims？

::: answer 展开参考答案3
不能；重新提取并重建当前版本对象和两审核。
:::


## 2026-10-24 两阶段事实审核开发候选

生产仍使用原事实审核配置和外层 LangGraph。开发配置 `POWERTRUST_FACT_INTERNAL_FLOW=joint_v2` 选择联合 v2，`two_stage_v1` 选择对象依赖→支持条件两阶段，`production` 回退原入口。两阶段复用原 Catalog、适配器、共享预算、一次纠正、内部子图和完整重审链；没有新增 Master 或 Harness。

阶段一选择每个命题实际依赖的正文与题设；阶段二仍接收实际回答与全部合法正文，能反对阶段一。条件在答案中出现、实例满足条件、完整结论受支持分别记录。数值来源不是额外适用条件，标量排序不认证工程关系。分类冲突和 unknown 进入复核，不静默通过。每事实组多一次初始请求；两个阶段共用一次纠正，原引用不增加规划调用。固定 F01—F08 是已见开发材料，F05 是预置分类诊断，不能称独立测试或从单次随机输出推断架构优势。

实现入口：`services/fact_two_stage_v1.py`；共享请求循环：`services/scoped_fact_execution.py`；固定批控制器：`evaluation/fact_two_stage_trial_v1.py`。结果与必要预测见 `docs/evaluation/fact-two-stage-v1/`。离线通过只证明工程契约，不证明语义正确，也不是工程安全认证。


## 2026-10-24 Agent业务收敛

事实两阶段未证明收益，暂不采用，研究实现与历史响应保留。事实支持、原文忠实性、分类义务、工程前提和程序失败分别解释；组件有效支持还不是整机最终政策处置。

领域开发候选 `POWERTRUST_DOMAIN_INTERNAL_FLOW=business_v1`，回退 `production` 或移除变量。生产仍langgraph_v1/production/schema13。内部流程先绑定实际工具能力，再用原一次领域调用按范围→必需输入→分析能力→适用约束/来源危险→汇总输出业务记录，最后交既有政策。无新增规划模型/调用/纠正额度。模型负责相关性和领域语义；程序约束身份、工具记录和流程。概念不机械要求厂站参数，缺输入不自动升级高风险，事实supported不证明现场安全；引用反驳危险建议不能按词触发。成功标量计算也不是工程仿真。

生成与修订已共享answer_units、answer_constraints、make_snapshot和structured_request；当前未新增伪公共封装，不改提示或政策。固定六类12分支及两项服务任务属于已见开发/集成材料，不作独立语义成绩。完整报告：docs/evaluation/domain-business-v1/。
