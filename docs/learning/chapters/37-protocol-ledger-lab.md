# 37 协议字段与预算状态实操

应用基线e4fb27e，当前配置见[当前状态](../../current-status.md)。本页补24/25章的字段阅读及状态演算；例子均为教学构造，不是真实模型输出。

## 先读哪一份合同

schema13并非一个孤立JSON Schema：Factory组合review_templates、support_relation版本和原引用分组，parser再校验ID与业务绑定。模板基础版本的注释不能覆盖Factory实际添加的instructions。先读[装配](../../../backend/assembly.py)，再读[Schema13分组](../../../agents/verification_contract_v10_batched.py)和[支持关系](../../../services/support_relation.py)。

|对象|需要读懂的字段|约束与典型失败|
|---|---|---|
|提取结果|answer_id、answer_version、claims、non_claims|身份必须是输入版，不能给新版本造主张|
|主张|quote、proposition、claim_type、qualifiers，必要时prefix/suffix|quote逐字锚定，qualifiers保留原句限定；原话与规范命题分别比较|
|事实finding|claim_id、rationale、applicability_conditions、bases、component_reviews|每个应审主张都有结果，不能多造ID；非空理由不等于理由成立|
|组件判断|component_index、status、basis_indexes、rationale、semantic_review|只覆盖程序允许的组件，不能输出程序拥有的缺失组件；索引不能越界|
|语义判断|fidelity、assertion_role、verification_obligation、rationale|忠实性、立场和义务是独立轴；分类争议不自动变成事实矛盾|
|原引用|citation_index与该项QUOTE_CANDIDATES|另一项候选即使同文字也不能借用；独立新证据不能治好原引用错误|
|修订结果|answer_units、assumptions、missing_information、finding_actions|只能有合同字段；改稿与动作解释分开|
|finding_action|finding_id、action、explanation|已冻结发现恰好一次，action仅modified/retained/unresolved，理由非空|

表为主路径字段导读，具体可选项和版本差异以parser为准，不能直接把它转成全套生产示例。领域对象的rule_ids、missing_prerequisites、basis_kind等见[领域合同](../../../agents/domain_contract_v3.py)；事实status枚举不能替代领域check_status。

## 正常和失败的提取例

```json
{
  "answer_id": "教学输入中的原ID",
  "answer_version": 1,
  "claims": [{
    "quote": "恒压条件下，装置A可以提供无功。",
    "proposition": "恒压条件下装置A可以提供无功。",
    "claim_type": "technical",
    "qualifiers": ["恒压条件下"]
  }],
  "non_claims": []
}
```

结构形状依据[ClaimExtractor](../../../services/claim_extractor.py)；具体身份要与输入一致。若quote改成“装置A总能提供无功”，已不逐字；若quote不变但proposition漏掉恒压，定位可能合格而语义不忠实。非法引用应由允许ID集合拒绝，不让模型自己解释新ID来源。

::: answer 题37.1：如何构造一个格式合格但语义错误的测试？
保留quote、版本、允许的依据ID和所有必需字段，只把规范命题从“when C then P”改成“only when C then P”。后者增加P→C，原句只给C→P。程序定位可通过，语义复核应发现推理方向新增；这是测试语义模型的难点，不能拿字段校验器保证。项目H3/N4保留这类漏检记录。继续追问：如果标签来自开发者已见题，不能称独立测试集表现。
:::

## 字符容量与请求费用不是同一个量

CitationWorkload默认最多32项、初检64000消息字符、纠正192000字符，见[citation_workload](../../../services/citation_workload.py)。pack按原顺序贪心分组，单项放不下要明确rejected，不截断Evidence后假装审核完整。messages_size是content字符求和，不是provider token数，也不包括所有HTTP信封开销。

::: answer 题37.2：40次调用与400万token能互相推出吗？
不能。ModelBudget.claim控制调用个数及deadline；一次长输入可能吃掉很多token。纠正追加旧输出和诊断，既增加调用也增加输入，不能假定每次成本一样。最终发送边界应分别记证据字符、完整消息字符、输出、usage与未知预留。程序返回业务非法也不能抹去已发生调用。继续追问：若无可靠完整计费上界估计，不能用字符数冒充可信token硬限。
:::

## 持久预留的可计算状态表

以下演示[历史候选Ledger](../../../evaluation/source_first_live_budget_v1.py)，该模块明确非生产sender，live_bound_unavailable默认拒绝真实发送；不把它宣传为现行通用预算装配。教学总上限10000，首次输入上界2000、输出上界1000，发送前持久reserve后charged=3000。

|状态|可信信息|charged如何变化|后续行为|
|---|---|---|---|
|发送前预留失败|没有获准发送|不产生新请求|停止，不补发|
|已预留且在途|结果未知|仍3000|不能释放|
|收到合法usage：输入1200、输出300、总1500|符合边界与加和|释放1500，剩1500|结算记录先持久化|
|usage缺失或加和不一致|不可信|仍3000|保留预留，不能填0|
|抛出异常、是否发送未知|可能受理|保留3000|GuardedAdapter记unknown_send并停|
|usage超预留|计费边界不成立|不按超界假定继续跑|停止并保留证据|
|同一记录二次settle|程序所有权错误|不得重复释放|停止|

锁保护entries/chains/charged的原子更新，fsync记录为持久边界；它没有自动恢复旧attempt，mkdir(exist_ok=False)正是拒绝把新尝试覆盖旧账本。正式使用哪份账本须按该批freeze与装配确认。

::: answer 题37.3：收到响应后parser失败应释放多少？
如果usage可信，模型已执行，按其真实1500计账；业务失败仍在失败分母。如果没有可信usage，保留3000上界。不能因未得到可展示回答把费用改0，也不能立即发相同请求再算“第一次成功”。继续追问：任务取消与HTTP线程终止不同，需drain完成后才说资源已释放；预算归属仍是原run/调用。
:::
