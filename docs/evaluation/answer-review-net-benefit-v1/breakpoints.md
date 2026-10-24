# 可回查闭环断点表

分析为AI辅助、用户监督；不是专家金标准、日常错误率或架构因果收益估计。先前选择规则见[selection.md](selection.md)，必要原文与逐轮字段见[archive-breakpoints.json](archive-breakpoints.json)。14槽=最近五完整分支+旧服务六槽（五未执行）+三历史记录；另只读核对旧首项封存后回收结果。未恢复attempt，未改旧输入/标签/身份。

## 当前生产相关记录（逐项，不混候选）

共同身份：schema13、product-decision-v1.5、deepseek-flash、lossless_v1、BM25/aggregate/topic_v4_subject_v1、知识kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e；服务执行冻结/源码efdb366749400d0fbef8198c5a904e9bb00652b1见[原报告](../langgraph-service-continuation-v1/results-v1.md)。原/图调用同一业务代码；旧行为没有采用事实联合v2、两阶段或business_v1。当前HEAD继承同修订v2正文提示与解析；本轮只加显式候选提示。

| 分支与run_id | 问题/必答点→证据→初稿 | 双审/资格→动作→新正文→重审→交付 | 成立性、收益/损害、归因及最小点 |
|---|---|---|---|
| LSI-01-G / caca725070144636872b4136f774fe84 | NWS可测降水阈值/原单位/定义范围；实际user参考明确≥0.01英寸及水当量；初稿均包含 | 两事实supported、领域范围适用；无Revision资格；无动作/新版本；最终pass | 必答点保留，正文不变有合理核验；未观察内容净改善。无须修复 |
| LSI-02-G / cedd45aa7a744061ad3a428caa6ce50c | 匿名厂站缺网络/运行点/限值能否定容量；实际无厂站数据；初稿说不能且列缺口 | 一聚合事实not_assessable、领域工程缺口；无来源绑定替换；不修订；review_required | 资料/工程前提不足合理，范围命题被质疑；具体技术必要性未独立全证，不能全部标误审。缺工程信息≠故障；不强迫删掉有用说明 |
| LSI-02-S / 70b7d70c72c648dfad789ed6b11bee19 | 同问题，独立自然初稿列网络/运行点/目标/限值 | 三个“缺X无法算容量”的关系被判insufficient；无合格修复；不修订；needs_information | 与G拆分/范围分歧，无法唯一归因于提取还是审核。无容量编造。没有依据为提高pass删缺口 |
| LSI-03-S / ea223d1f8c47483cb846ca7ed9dce238 | 明确要求纠正阈值；原文0.01、初稿0.1；范围只解释文献 | 阈值contradicted成立→一次修订；主事实/数值/范围modified，其余retained；新文0.01并技术对比“而非0.1”；完整提取双审supported→pass | 成功纠错，单位/范围保留；没有依赖工程结论需要更新。retained是保留，不代表自动解决。技术对比有源，不等同改动历史 |
| LSI-03-G / 1b41971b56a84f7aa55687eefeecd3de | 同阈值矛盾，当前生产相关完整两轮 | 成立矛盾→一次修订；阈值modified，范围retained；正文0.01却新增“原回答误作0.1英寸，已修正”；新值supported，历史叙述因缺旧回答快照insufficient→needs_information | **已证实：实质改对却新增过程主张，阻碍认可交付**。新增历史叙述本身真实可回查，但重审的实际输入没有相应旧正文；不能称全新值错误。修订输出/重审输入作用域共同断点；选择只改修订提示，将理由保存在finding_actions。不扩大证据、放宽审核或新增调用 |
| 旧LSI-01-S / a83c9966ad034532954127b6958b075b | 同NWS定义、初稿正确 | 服务原路径完成pass/5调用；收集器跨线程SQLite失败，封存后只读回收完整结果；其余五槽未执行 | 执行与收集故障，不是语义错误；既有独立显式关闭只读连接已修，本轮复用saved_result和run_fixed，不另建控制器。不把服务完成改写为旧批成功 |

## 明确版本不同的历史辅助记录

共同知识 k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55，limited-repair-policy-v1、提取atomic-v4、事实verification-v7.1、领域v1.3；不是当前schema13/product1.5表现，不能按当前输入补造历史。历史修订v1/v1.1与当前逐发现v2不同。

| 记录 | 链条与事实 | 分类/最小点/限制 |
|---|---|---|
| revision-constructed-v1 / f7972bbf9e62489bb47888b69f52876d | 问正常母线电压能否证明稳定；初稿说能且无需分析；原NERC有正常/故障及分析要求；发现成立→REVISE，但修订两次结构不合法/漏事实ID，只有旧正文，最终review_required | 错误未修、修订执行故障；历史记账问题已由当前v2逐ID显式动作覆盖，不重复实现；不能说当前v2仍漏ID |
| 同档 / 3666bcb1c09e4715bf099628447223ee | 合成设备数量/无功单位/同母线两电压一致性；初稿Q=30MW正确和230kV=230V明确有错，数量命题supported却与程序枚举告警并存；REVISE后结构失败未产新版本 | 审核漏判/程序告警/修订执行共同原因；不能将所有四设备枚举算可靠工程规则。无成功修复/依赖更新证据 |
| revision-normal-voltage-v2 / 90a74bd6c1174850adf262b67bfc7fe7 | 同正常电压错误，v1.1实际生成反对“正常即稳定”的完整新文、说明证据/缺输入/需故障与稳定分析；新版本事实最终结构失败，保留其他同伴结果，review_required | 错误结论被纠正但完整交付失败；重审错误作用域/执行故障，不把占位not_assessable当有效语义不足。长新答案存在未独立核实的额外范围解释，不能整篇认证；旧长答不是候选成绩 |

候选实验：事实内部v1/v2、two_stage_v1和领域business_v1仅作为方案比较背景，其原结果见各自归档，不进入此生产断点表或成绩。

## 原因边界与门禁核查

本选择没有证明来源本身错误或检索遗漏；未发现证据不能倒推库内没有。实际交付缺口在LSI-03-G是旧回答正文未交付给重审，不是NWS阈值漏检。LSI-02保留来源不足/工程前提/提取与审核范围分歧多种可能。最近五分支没有初稿正确后被迫改错的记录；LSI-02正文不变，03两条的初稿确有矛盾，因此“至少一项modified且正文改变”没有迫使本例错误改写的证据。候选保持门禁；离线反例仍拒全部retained及只记modified但正文不变。

源码链：agents/generation.py（实际材料生成）→services/claim_extractor.py→agents/evidence_verification.py / agents/power_domain_review.py→services/bounded_repair.py / harness/product_policy.py（资格/政策）→agents/revision_contract_v2.py（正文/动作）→harness/execution.py:revise与重新extract/prepare/review_pair→backend/store.py→backend/service.py/presentation.py。修复点仅revision_contract_v2的新增显式提示，通过ModelRevisionAgent和ComponentFactory/ServiceConfig接线。
