# RC-001评测设计v4：仅离线

2026-10-20。落实已确认的评分边界、题设依据身份及结构派生，不新增真实调用。原协议与失败响应不改，旧预期不改，生产审核不改。[原结果与分歧](evidence-bound-rc001-evaluation-v1.md)，[离线小统计](evidence-bound-rc001-v4-offline-stats.json)。

## 协议差异

| 项目 | 已执行的v3 | 本轮离线v4 |
|---|---|---|
| R1 | 映射并保留外露 | 明确只评分定义映射及题设条件，不评分标志内容 |
| R2 | “该类别触发”的入口要求，容易重复要求映射 | 明确只评分入口、醒目标志、禁止不合格人员进入；R1缺失不得再次降R2 |
| 题设依据 | question中有事实，但没有可引用的独立身份 | scenario_premises独立于evidence；从原问题精确区间生成ID，标为本题假定、site_verified=false |
| 文献依据 | E1/E2及E2上位范围 | 正文和范围不变，原ID保留；不让评分条目或参考表述成为依据 |
| 支持判断 | supported/contradicted须引用文献ID | 按claim_type约束题设ID或文献ID；支持仍限本题或给定资料，不升级为现场核实 |
| composition | 模型声明single/multiple/uncertain，与数量可能冲突 | 模型不再声明该字段；程序对1项派生single、2项及以上派生multiple |
| 无法评估 | 可通过uncertain及not_assessable表示 | 每项not_assessable和理由继续保留，不用判断数量表示语义确定性 |

R1/R2仍由模型独立判covered/partially_covered/missing/uncertain。程序只严格验证、汇总，不因R1缺失自动改R2，也不把模型评审补出的映射写入待评回答。B的原预期继续是R1 missing、R2 covered、整体incomplete。v4不会把旧预测partially_covered修成covered，也不会根据样例ID强制新预测符合预期。边界提示能否改善真实判断尚未测量。

## 题设与文献的身份

两个题设前提分别是问题中“某房间属于1910.303(g)的适用范围”和“内有外露的已带电导电部件”，都由程序从原问题回切，ID绑定完整问题、位置和文本。没有加入live parts映射或标志结论作为题设。A/C的同一问题前提身份相同；回答单元ID继续按各自原文/位置绑定。

题设前提只表示本题允许假定成立，不表示已检查真实房间。E1定义、E2规则和对地标称600V及以下的附属范围保持原样，不要求模型重新核实已假定适用的电压。

每项判断新增claim_type，允许的依据类型如下。支持标签仍为supported、insufficient_evidence、contradicted、not_assessable，原标签含义不以是否覆盖要求替代。

| claim_type | 用途 | 依据限制 |
|---|---|---|
| premise_restatement | 复述题设假定 | 只能引用题设ID；supported/contradicted仍需非空依据，程序标为仅本题假设范围 |
| literature_statement | 陈述文献定义或规则 | 只能引用文献ID，不能用题设代替文献证明普遍规则 |
| scenario_application | 将规则应用于本题 | supported/contradicted必须同时有题设和文献依据；不证明其语义连接正确 |
| external_claim | 附加的题设外/资料外声明 | 不能引用题设ID作外部事实证明；不足或无法评估可无依据ID |

新解析器保留类型绑定及支持范围说明。旧严格结构验证器仅作为内部ID/字段检查复用；内部临时身份池不进入消息，不把题设改写成文献证据。字段、ID、重复/遗漏单元、空判断及支持无依据仍严格拒绝。模型返回composition或自报数量也拒绝，防止同时出现两套派生规则。

限制：claim_type、命题解释和支持仍由未来模型判断。程序能拒绝把显式题设ID当作外部核实依据，但不能仅凭合法ID证明一个自然语言断言确实是题设复述、规则连接正确或没有冒充现场结论。语义误分类仍需复核；未增加自动语义纠错或专家金标准。

## 程序派生的取舍

采用从非空judgments列表长度派生single/multiple，解决旧B“multiple但仅1项”的重复声明冲突。它只描述返回判断项数量，不证明一个单元实际含几个命题，也不检查模型是否遗漏、合并或重复表达了命题。无法可靠拆分时可保留not_assessable及理由，不强迫给出确定支持结论。

旧v3解析器仍拒绝multiple配1项，旧失败记录/费用均不变；本轮没有用新解析器重新解释历史响应。v4增加依据类型字段与说明，不据此宣称消息更短、费用下降或纠正率下降。

## 离线结果

27项通过：新协议16项、原v3严格解析8项、RC旧输入及覆盖/支持分离3项。全部为人工构造响应的离线程序检查，不是模型预测或语义正确率：

- B型R1缺失但R2覆盖仍独立保留，整体不完整；评审推导支持不补进回答位置。
- A/C型同一题设复述允许同一题设身份支持，程序范围均为hypothetical_question_only；拒绝把E2当作题设复述的唯一身份，也拒绝把题设用于外部事实或普遍规则。
- 1/2/3项判断分别正确派生数量分类；空列表、自报composition/数量严格拒绝，not_assessable保留。
- 类型冲突、跨问题题设ID、伪造原文/区间、非法单元/要求/依据ID均拒绝；文献声明、题设＋规则应用、附加寿命不足仍可表达。
- 旧multiple配1项继续被原解析器拒绝；原协议源码和历史输入/预期/响应/执行等20个文件SHA核对不变。

三份实际原回答仅制作新协议的离线输入预览，问题、回答、原文证据、上位范围和程序回答单元与原批次逐字一致；只独立版本化任务要求和新增题设身份。新预览不包含参考答案、预期标签、样例角色或修订理由，没有生成新的语义预测。

## 文件与复核方法

新增evaluation/premise_bound_review_v4.py与tests/test_premise_bound_review_v4.py，无真实执行/冻结付费批次入口，不加载凭据。项目解释器运行：

```text
python -m unittest tests.test_premise_bound_review_v4 tests.test_requirement_review_v3 tests.test_rule_chain_trial_v1 -v
```

私有RC-001.offline-card-v2.json从原确认卡另存，原样例预期继续沿用RC-001.synthetic-confirmed-v2.json，未重写。rc001-v4-offline-prepared保留小型输入预览、源码/输入SHA和离线审计；不是允许真实复验的批次。没有大包、数据库副本或付费请求。

下一步是否做一次冻结复验由本人决定；本轮不自动追加。真正错误连接两段规则的回答仍是未来待设计样例，现有合成解析测试不冒充已确认的新题或实际模型结果。RC-001仍是简单定义链开发家族，不宣称模型必须使用两段才能答对；本轮未提交推送。


后续状态：本人另行明确授权一次冻结复验，新增独立执行入口，未改本离线协议源码/提示。实际结果及停止边界见[唯一复验报告](evidence-bound-rc001-v4-recheck.md)；本文件0API/无执行入口指上述离线准备阶段，不代表后来未执行。
