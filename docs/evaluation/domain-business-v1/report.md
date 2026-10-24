# Agent业务收敛与领域候选

建议：保留领域候选，不切换生产。一次模型调用按业务记录拆清范围、输入、能力和约束；本轮没有增加初始或纠正调用。不能从6个已见类别的单次随机输出宣称语义提升。事实两阶段登记为未证明收益、暂不采用，见fact-closeout.md/json。

固定六类明确合成开发材料，12分支两版顺序交替，问题/回答/证据/工具相同，领域接口原本不读取事实Agent判断，两版均没有收到其他审核预测；未重跑事实或生成。参考在freeze.json inputs中先固定，固定输入构造只使用问题和回答，不把参考scope/capability/hazard字段送给模型。原危险来源复用现有operational_safety注册，不下载新资料。两个版本使用相同共享预算40和每分支最多一次纠正，12初始/最多12纠正由流程推导，没有新增节点额度。

全部12分支首次有效、最终完成，12调用、0纠正，无共享故障、无失败重跑。完整必要消息/响应在predictions.json，每项模型/程序派生、原文、输入缺口、工具判断、来源绑定及理由见results.json；不删不利类型分歧。

|分支|派生实际范围|范围检查原始状态|危险判断|分支秒|
|---|---|---|---|---|
|D01-baseline|conceptual|no_issue|not_applicable|2.092|
|D01-candidate|conceptual|no_issue|not_dangerous|3.17|
|D02-candidate|engineering|no_issue|not_dangerous|2.937|
|D02-baseline|engineering|no_issue|not_applicable|1.957|
|D03-baseline|engineering|warning|uncertain|3.168|
|D03-candidate|engineering|warning|uncertain|4.21|
|D04-candidate|engineering|warning|not_applicable|4.411|
|D04-baseline|engineering|warning|not_applicable|2.772|
|D05-baseline|engineering|warning|dangerous|2.764|
|D05-candidate|engineering|warning|dangerous|4.481|
|D06-candidate|conceptual|no_issue|not_dangerous|3.473|
|D06-baseline|conceptual|no_issue|not_dangerous|2.035|

D01/D06均为conceptual，未机械要求厂站参数；D02/D03/D04/D05均engineering。D02答复主动指出必需输入缺口，所以模型对答复的analysis_scope可no_issue，但程序工程输入/仿真门控仍未完成，不能解释为工程结论通过。D03表面概念中的保证被两版识别为engineering/warning。D04缺寿命模型和工具，两版警告，未冒充计算。D05两版来源有界dangerous，D06否定反驳均not_dangerous，没有危险误报警。D01/D02候选用not_dangerous、原版not_applicable，属于类型差异，不能称改善。候选工具能力D01/D06 not_needed，其余insufficient，与固定参考相符。这里没有实际工具成功/失败输入变体，能力边界的这部分依赖既有离线回归，不能报告为真实工具验收。

原始check_status进入原task_applicability.bind及program_findings，再交既有政策；业务记录是模型解释，不替代事实支持或形成新安全认证。12个组件分支没有运行外层事实/领域合并政策，因此不编造完整服务decision；服务任务另表记录。

实现：services/domain_business_v1.py；共用agents/domain_contract_v3.py的原调用/解析/隔离/一次纠正。业务记录绑定analysis_scope单元，非法记录不能丢弃后通过，有效同伴由原WireIsolation保留。内部图三步分别实际执行工具能力绑定、原领域调用和既有政策交付，不为五项业务名目增加五个空节点。显式配置POWERTRUST_DOMAIN_INTERNAL_FLOW=business_v1；回退production/移除变量，生产始终不变。独立领域运行/服务控制器不修改旧事实批次文件。

完整离线1187项通过193.070秒；新增3专项覆盖六类实际适配器消息、单例继续/共享停止、Factory/外层图/Store/API/修订重审。最后manifest版本元数据修正后相关3项再通过6.743秒，未重复全套。既有套件覆盖工具、危险否定/引用、来源范围、超时/取消/预算/存储及历史。候选专属组合未逐一另写测试，保留覆盖边界，不把复用套件写成全部候选组合已独立验收。

生成/修订实际路线及保留公共实现的理由见generation-revision-audit.md。学习站20章/60自测，构建/源码身份/链接通过；旧PDF、协议、回退、知识、数据库和历史批次不删除，无ZIP或全项目复制。

## 小统计

```json
{
  "baseline": {
    "planned": 6,
    "complete": 6,
    "first_valid": 6,
    "calls": 6,
    "corrections": 0,
    "usage": {
      "input_tokens": 19100,
      "output_tokens": 2188,
      "total_tokens": 21288,
      "cache_hit_tokens": 7680,
      "cache_miss_tokens": 11420
    },
    "model_seconds": 14.619,
    "branch_seconds": 14.78688990000228,
    "cost": "unknown"
  },
  "candidate": {
    "planned": 6,
    "complete": 6,
    "first_valid": 6,
    "calls": 6,
    "corrections": 0,
    "usage": {
      "input_tokens": 21098,
      "output_tokens": 3428,
      "total_tokens": 24526,
      "cache_hit_tokens": 8832,
      "cache_miss_tokens": 12266
    },
    "model_seconds": 22.375,
    "branch_seconds": 22.681298799987417,
    "cost": "unknown"
  }
}
```

## 服务验收与运行状态

两项服务验收：计划2，受理0，模型调用0，均未执行。独立入口的service-freeze.json已冻结，但复用采集器还直接读取execution-freeze-v1.json的字节；别名缺失在attempt创建、API受理和模型发送前触发FileNotFoundError。属于共享程序故障，立即停止本批服务任务，没有重试或补跑。不是模型结构失败或语义不足。候选服务真实端到端验收未完成，不能用离线Factory测试代替。

修复仅使未来新freeze同时写入采集器规范文件名，旧冻结/输入/响应不覆盖；新增离线文件名一致性门禁通过，最终4专项通过7.142秒，没有重新冻结或启动本批服务。当前交付源码与实跑冻结的差异登记delivery-source-delta.json。未来验证须新批授权，不恢复本轮。

生产服务从无监听且无重复后端进程状态正常启动，既有知识校验后ready/空闲/0健康模型请求；验收停止后按授权正常停服重启，仍production/schema13/langgraph_v1，未切候选。生产历史行数与哈希前后核对另见production-history-before/after。浏览器实际入口ready，但工具浏览器未登录，提交/历史按钮禁用；未绕过会话或本地文件限制。一次人工清单：通过日常start-powertrustai.cmd正常连接后，查看已有任务的回答、引用原文、版本和失败草稿；不要为页面检查额外提交付费任务。

最终限制：领域候选真实组件对照完成，但完整服务真实验收被程序门禁阻断；工具成功/失败和取消等候选专属组合未逐项形成独立真实证明。继续保留开发候选，不采用生产。费用未知。全部组件12调用，总45814token；未因服务失败追加题目或调用。

生产历史复核：meta 1、runs 104、events 2278、objects 2999、reviews 8，逐表SHA前后完全一致；没有请求重发、补算或历史迁移。模型deepseek-flash，完整知识版本kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e，BM25/aggregate/topic_v4_subject_v1保留。

最终重启确认：生产ready、空闲、storage_healthy=true、health_model_requests=0，8765仅新进程11956监听。见production-health-after.json。
