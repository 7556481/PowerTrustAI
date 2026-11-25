# 37 协议字段与预算状态实操

应用基线e4fb27e，当前配置见[当前状态](../../current-status.md)。本页补24/25章的字段阅读及状态演算；例子均为教学构造，不是真实模型输出。

## 正式主路径的可执行样例
先看[formal-path-v37.json](../examples/formal-path-v37.json)，它全是合成数据。generation根对象交给`agents.generation.parse_units`；extraction_v7交给`services.claim_obligations.parse`，输入AnswerDraft必须与文件中的ID、version和text一致。锚点由anchors计算后冻结，模型不抄版本、quote或offset。

```python
answer = AnswerDraft(data['answer']['id'], data['answer']['version'],
                     data['answer']['text'])
out = parse(data['extraction_v7'], answer)  # claim_obligations.parse
```
输出Claim的quote和范围由程序恢复，本例只有一个段落，start=0、end=len(text)；component_basis_targets是document_body，component_obligations是technical_truth。这两个字段使“原文是否证明事实”与“输入里有没有出现过句子”不能互换。用bool冒充version的旧形状问题与v7现有anchor问题不同，不能把所有测试都叫schema13测试。

|一次改动|预期|原因|
|---|---|---|
|原始合成generation及v7对象|接受|给定证据ID、锚点、类别和义务相容|
|generation引用换成unknown|拒绝|不在输入Evidence集合|
|v7义务改成answer_scope|拒绝|document_body需要technical_truth|
|同一对象换AnswerDraft.version=2再解析|拒绝|旧anchor不在新版目录|
|命题改成only under C，保留合法字段|可能仍结构接受|语义新增P→C，不由parser证明|

离线测试见[test_handbook_examples_v37](../../../tests/test_handbook_examples_v37.py)。测试还通过注入DeepSeek exchange走正式ModelClient与structured_request，首答非法、纠正合法，断言确有两份payload和两条调用记录。注入的是网络边界，不另造业务解析器；它证明接线与拒绝规则，不证明真实Flash会判断正确。

::: answer 题37.4：为何旧v4示例能parse，不代表正式提取消息能用它？
Factory的提取协议为v7，ClaimExtractor会选claim_obligations.parse，不走最下层parse_extraction入口。版本选择改变根形状和字段职责；绕过上层直接测旧parser，会造成“样例合法”但正式入口不能用。应同时固定实际路由、完整payload和版本绑定对象。继续追问：嵌套字段合法仍不证明提取忠实，only反例必须留给语义评测。
:::

## 完整正式v7教学输出

与teaching-answer/v1原文一起解析，锚点由程序产生，不由模型计算hash。
```json
{
  "claims": [
    {
      "anchor_id": "answer-anchor-c1abb2ec0c600d4a36bac7ff",
      "proposition": "Under C, device A supplies reactive power.",
      "claim_type": "technical",
      "assertion_role": "conditional",
      "semantic_qualifiers": [
        "Under C"
      ],
      "components": [
        {
          "category": "technical_fact",
          "proposition": "Under C, device A supplies reactive power.",
          "basis_target": "document_body",
          "verification_obligation": "technical_truth"
        }
      ]
    }
  ],
  "non_claims": []
}
```

## 先读哪一份合同

schema13并非一个孤立JSON Schema：Factory组合review_templates、support_relation版本和原引用分组，parser再校验ID与业务绑定。模板基础版本的注释不能覆盖Factory实际添加的instructions。先读[装配](../../../backend/assembly.py)，再读[Schema13分组](../../../agents/verification_contract_v10_batched.py)和[支持关系](../../../services/support_relation.py)。

|对象|需要读懂的字段|约束与典型失败|
|---|---|---|
|正式v7模型提取根|claims、non_claims|不由模型返回answer_id、answer_version、quote或offset|
|正式v7模型主张|anchor_id、proposition、claim_type、components、assertion_role、semantic_qualifiers|选程序提供的锚点；组件须含category、proposition、basis_target、verification_obligation|
|正式v7模型non_claims项|anchor_id、reason|只选完整非事实段，不能与claims共用同一锚点|
|事实finding|claim_id、rationale、applicability_conditions、bases、component_reviews|每个应审主张都有结果，不能多造ID；非空理由不等于理由成立|
|组件判断|component_index、status、basis_indexes、rationale、semantic_review|只覆盖程序允许的组件，不能输出程序拥有的缺失组件；索引不能越界|
|语义判断|fidelity、assertion_role、verification_obligation、rationale|忠实性、立场和义务是独立轴；分类争议不自动变成事实矛盾|
|原引用|citation_index与该项QUOTE_CANDIDATES|另一项候选即使同文字也不能借用；独立新证据不能治好原引用错误|
|修订结果|answer_units、assumptions、missing_information、finding_actions|只能有合同字段；改稿与动作解释分开|
|finding_action|finding_id、action、explanation|已冻结发现恰好一次，action仅modified/retained/unresolved，理由非空|

表中提取行只描述正式v7模型输出；其他审核/修订行按各自合同阅读。表为主路径字段导读，具体可选项和版本差异以parser为准，不能直接把它转成全套生产示例。领域对象的rule_ids、missing_prerequisites、basis_kind等见[领域合同](../../../agents/domain_contract_v3.py)；事实status枚举不能替代领域check_status。

## 程序恢复后的内部字段（不是v7模型输出）

模型返回anchor_id后，程序按当前AnswerDraft的锚点目录查找原段，恢复quote及start/end，绑定answer_id和answer_version，再构造Claim。主张ID由程序计算；v7的basis_target和verification_obligation进一步保存为component_basis_targets/component_obligations。

|归属|字段|来源与边界|
|---|---|---|
|输入AnswerDraft|answer_id、version、text|已保存的回答版本，不允许模型另造|
|内部Claim|answer_id、answer_version、text、start_offset、end_offset、claim_id|程序从冻结回答及锚点恢复；text保存原quote|
|内部语义信息|proposition、assertion_role、semantic_qualifiers等|来自模型的语义判断，程序可核对结构但不证明等价|
|内部qualifiers|qualifiers|v7锚点转换中设为空tuple；不要将其与模型semantic_qualifiers混同|

调用链是claim_obligations.parse→answer_basis_targets.parse→answer_anchors.parse→parse_extraction。最后一层能接受旧形状，并不意味着正式模型要输出那种形状。内部定位和语义忠实是两道问题。

## 历史v4模型字段（不是正式v7）

历史v4由模型返回answer_id、answer_version，以及claims中的quote、proposition、claim_type、qualifiers，可选prefix/suffix；组件模式另有components。下面仅展示旧基础形状，用于解释历史parser，不应照抄到正式v7请求。

## 历史v4形状的提取例（不作为正式v7请求）

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
