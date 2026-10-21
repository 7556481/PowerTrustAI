# v6有限开发复验结果v1

2026-10-21。本人确认[八例计划](reviewer-v6-development-recheck-plan-v1.md)，并明确授权向api.deepseek.com发送两题、要求、证据上下文及8回答，使用deepseek-flash，最多16调用、失败即停、不追加/恢复。本批已结束，无后续自动调用。生产协议、原v5成绩/标签及EIA-A04匹配规则不变。这是已见开发材料的协议复验，不是独立保留集成绩。

## 执行与逐项结果

8/8最终有效，0最终失败、0未执行；**首次结构有效4/8，12调用、4纠正，28.659秒**。输入23115、输出5276，共28391 token。API未返回实际费用金额，不将适配器费用估算当账单。

|固定顺序|样例|最终执行|调用/纠正|秒|覆盖R1/R2|对齐后支持标签|
|---:|---|---|---:|---:|---|---|
|1|EIA-A01|有效|2/1|3.710|covered/covered|U1、U2 supported|
|2|NRC-A01|有效|1/0|2.170|covered/covered|U1 supported|
|3|EIA-A02|有效|1/0|1.966|covered/missing|U1 supported|
|4|NRC-A02|有效|1/0|2.310|covered/partial|U1 supported|
|5|EIA-A03|有效|2/1|5.118|covered/covered|U1 supported；U2 contradicted|
|6|NRC-A03|有效|1/0|2.284|covered/covered|U1 contradicted|
|7|EIA-A04|有效|2/1|5.293|covered/covered|U1 contradicted；U2 supported|
|8|NRC-A04|有效，有语义分歧|2/1|5.753|covered/covered|U1 supported；U2 contradicted（参考insufficient_evidence）|

ID完整前缀为H-EIA-001/H-NRC-001。两来源各4例均完成；完整/遗漏、反向关系/运算/否定定义及无据附加各计划项均交代，只有2题/2来源组，不能称8独立问题或普遍四分类验证。

四次初始无效（EIA-A01/A03/A04、NRC-A04）均缺unit级rationale；A01缺units[0]，后三例缺units[0]和units[1]。都经一次精确字段纠正成为结构有效，初始无效响应不计语义成绩，响应与费用保留。诊断stage显示复用v5校验器；实际请求prompt_version与response_contract_version均v6，不表示误用了旧提示。

## 覆盖与支持分别核对

16覆盖槽全部有效、16与冻结参考一致：14 covered、1 missing、1 partially_covered。EIA-A03/R2和EIA-A04/R1均不再因结论相反而降覆盖；NRC-A02仍因缺时间含义判partial，EIA-A02仍缺区间要求。这是本次结果的正向证据，不能证明通用语义问题解决。

12参考单元均可对齐，0无法对齐/冲突/失败/未执行，无额外未匹配预测；对齐为AI辅助建议，尚待本人逐单元确认，不称专家金标准。

- **EIA-A01合并表达**：一个预测命题明确包含求和及非同区间两断言，均为supported。按事前等价合并允许规则映射至U1/U2，每参考计一次，不按返回判断数建立分母。
- **EIA-A04匹配规则没有改变**：本次U1只有一个完整的“平均而非求和”contradicted命题，没有旧批另拆出的supported数量子判断；U2独立supported，故U1可对齐。旧批的混合标签无法对齐项仍原样保留，不事后给旧批改分。
- **NRC-A01**：本次识别为literature_statement，对照给定定义/别名上下文判supported，没有引入实际现场核验义务；只是该例修复目标出现正向结果，不证明所有现场/定义边界可靠。8例均无真实现场实例断言，不能验证真实设备语义核验能力。
- **NRC-A04/U2新分歧**：参考为insufficient_evidence，本次判contradicted。模型理由从“仍有一半原始原子”进一步推向危害消失结论矛盾；证据未直接给出危害与原子数量之间的完整关系，按冻结边界不能用这种推论将不足自动升级为矛盾。不改参考、不挑理由中的“未支持”替换模型标签，不重跑。

支持混淆为supported→supported 8、contradicted→contradicted 3、insufficient_evidence→contradicted 1。错误拒支持0，错误支持F=0，**F/A_NS=0/4、F/A_SP=0/8**。分母沿用冻结native-reference-policy的参考对齐口径；EIA-A01虽只有一个合并预测判断，但显式对应两个参考断言，分别计其参考单元，不能把原始判断数与该分母混用。两个零分子不代表全部支持标签正确，更不能证明普遍可靠；本批仍有一项非支持类别分歧，且无not_assessable参考。

## 与历史v5并列观察

|项目|历史v5冻结批|本次v6开发复验|
|---|---:|---:|
|最终有效|8/8|8/8|
|首次结构有效|6/8|4/8|
|覆盖一致|14/16|16/16|
|参考对齐|11/12|12/12|
|错误拒支持|1|0|
|调用/纠正|10/2|12/4|
|输入/输出token|13376/4769|23115/5276|
|总秒数|24.696|28.659|

覆盖及定义对象判断在这些已见例中改善，但首次结构有效、纠正数、调用/token和总耗时没有改善；不能宣称输出稳定性或费用下降。v6提示更长、纠正更多；服务与采样时点不同，未重新跑v5，不是严格受控A/B。原v5的NRC-A01分歧、EIA-A04未对齐及全部历史记录保留。

## 身份、审计与复现边界

执行前[冻结清单](reviewer-v6-development-recheck-freeze-v1.json)绑定985f8e3完整计划提交及新增入口/测试源码SHA；当时新入口未提交，身份由文件哈希明确绑定，不伪称运行于后续交付提交。旧8任务先做原preflight，再仅添加literature角色，逐项校验已确认计划内任务与消息SHA。55项必要离线回归通过（含4项新入口门禁），不是语义成绩。

实际12请求的首两消息逐项等于冻结白名单消息；纠正仅追加现有结构纠正数据，不送参考标签、理由、人工参考切分或角色。12响应SHA及原冻结preflight回查通过。原始请求/响应与执行结果保留忽略目录data/evaluation_local/holdout-source-selection-v2/v6-development-recheck-v1及data/retrieval_local/v6-development-trial-v1；不公开正文或完整响应。公开[小统计和逐单元对齐ID](reviewer-v6-development-recheck-results-v1.json)可核对全部分母与计划状态。

离线核对入口为现有环境执行模块evaluation.v6_development_trial_v1并提供本批目录，不加--run只检查。带--run会被已存在的attempt.json拒绝，不能自动恢复；本轮不得删除标记或换目录重发。后续先复核本次对齐与新分歧，不继续围绕这些题修改到全对，不新选来源或触发模型实验。生产继续冻结。
