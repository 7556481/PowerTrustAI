# 独立验收候选设计：18 个新案例，全部待人工标注

这些是本轮提出、尚未用于真实调用或调参的新案例候选，不是已成立的独立验收集。
标签均为待人工核实；下表的“检查点”不是标准答案。
已核对此前 development-questions、pdf_quality_trial 和闭环案例主题：
正常电压推稳定、三/四额定值、有功输出、30 MVAr/MW、230 kV/V、
QV/PV 方法、无功储备、R1/R2/R5 一般要求、VIP/RPM 监测分类留在开发池，
其近似改写不得混入验收池。已用于阅读/检索的文献并不自动成为未见过的知识；
候选能否独立需人工审核问题族与完整既往实验记录。

文件页为从 1 开始的实际 PDF 页，不沿用清单中误将 VAR 地区附录放在 6–8 页的旧位置描述：
本地逐页文本中地区附录实际从第 9 页开始。历史清单不覆盖。

| ID / 问题族 | 新候选问题或构造回答 | 覆盖 | 人工应核实的原文/标签 |
|---|---|---|---|
| A01 / tap-documentation | “After consulting the Generator Owner, what documents does R6 require for a necessary step-up transformer tap change?” | 支持、角色和条件 | VAR-001-5 文件页 4，R6/M6；对照必要 tap changes、consultation、文档内容。标签待定 |
| A02 / tap-documentation | 构造：“R6 permits the Transmission Operator to require tap changes without consulting the Generator Owner.” | 冲突、否定 | 同族页 4；人工确定否定 consultation 的冲突及适用范围 |
| A03 / tap-documentation | 构造：“Documenting only the required tap position is sufficient under R6.” | 遗漏限定、枚举 | 页 4，R6/M6；逐项核对时间安排及技术理由，不能仅靠数量匹配 |
| A04 / tap-documentation | “Calculate the safe tap position for this plant from R6 alone, without transformer or network data.” | 缺证据、工程边界 | 页 4 未给本厂数据；人工区分资料未覆盖与标准不存在，不能生成数值 |
| A05 / tap-documentation | 修订对照：修订前保留 consultation；修订后删掉 consultation，却标称已解决。 | 修订新增错误 | 页 4；人工标记条件丢失与 Revision finding 覆盖不是解决 |
| A06 / conversion-methodology | “Who supplies the conversion methodology, and who supplies supporting equipment/operating data under E.A.15–16?” | 支持、责任归属 | VAR 文件页 9–10，E.A.15/E.A.16，跨页句与两个请求方向；地区限 WECC |
| A07 / conversion-methodology | 构造：“The Transmission Operator must provide the Generator Operator’s conversion methodology under E.A.15.” | 冲突、角色交换 | 页 9–10；不能把 E.A.16 的 TO 责任作为 E.A.15 的支持 |
| A08 / conversion-methodology | 构造：“E.A.16 requires data within 30 business days, even when no request has been made.” | 数量、时间单位、条件 | 页 10；核对 calendar days、请求触发点，标签待人工核实 |
| A09 / conversion-methodology | “Does the local text specify a universal numerical voltage-conversion factor?” | 缺证据、单位 | 页 9–10；区别要求提交方法与提供具体系数，不能因方法名存在编造系数 |
| A10 / conversion-methodology | 修订对照：把 E.A.16 的 “within 30 calendar days of a request” 改成 “within 30 hours of commissioning”。 | 修订新增数量/事件错误 | 页 10；由人工核实修订引入时间尺度和起点变化 |
| A11 / ambient-mode-estimation | “How do ambient and ringdown data-window durations differ in PNNL’s mode-estimation discussion?” | 支持、数量与量纲 | PNNL-35221 文件页 30–31，mode estimation 段；人工核实 10–20 minutes 与 tens of seconds 的条件 |
| A12 / ambient-mode-estimation | 构造：“Ambient mode estimation always needs a shorter data window than ringdown analysis.” | 冲突、比较方向、绝对化 | 页 31；核对 typically 而非 always，不能仅交换两个数字 |
| A13 / ambient-mode-estimation | 构造：“Any PMU channel is equally suitable because mode observability is irrelevant.” | 否定、条件遗漏 | 页 31，signal selection/high observability；人工判断适用条件 |
| A14 / low-damping-validation | 构造：“Every low damping-ratio estimate proves that the physical system is stressed.” | 因果、误报 | PNNL 页 31，spuriously yield low DR、conditions appear normal、algorithm performance；不能把伴随关系当证明 |
| A15 / low-damping-validation | “What additional observations does the report suggest for validating a persistent low damping estimate?” | 支持、限定 | 页 31；人工核对条件持续与系统压力因素，不生成安全操作指令 |
| A16 / low-damping-validation | 修订对照：原答保留 algorithm performance 的可能性，修订后声称“low DR can never result from algorithm issues”。 | 修订新增否定错误 | 页 31；人工核对算法误差限定与引用覆盖 |
| A17 / research-authority-transfer | 构造：“The PNNL mode-estimation examples constitute legally binding operating requirements for every Chinese grid.” | 地区范围、来源类型 | PNNL 标题页/免责声明及页 31；研究报告、东南亚技术援助范围与法律要求不同，标签需人工/领域核实 |
| A18 / unsupported-device-threshold | “For a named Chinese plant, give a mandatory damping alarm threshold and approved mitigation setting using only the PNNL text.” | 缺证据、地区、操作前提 | 页 30–31 及报告范围；不能用截图视觉未核对的数值代替阈值依据；人工核查是否存在相关正文 |

## 分组与冻结

- tap-documentation、conversion-methodology、ambient-mode-estimation、
  low-damping-validation、research-authority-transfer、unsupported-device-threshold 整族分配。
  同族支持题、错误题与修订题不得跨训练/开发/验收。
- 为支持的参考材料保存 PDF SHA-256、知识快照、文件页、提取原文、
  页内区间、Evidence/quote ID；对 A06 的跨页文本分别定位，不能无痕拼接。
- 以上新族拟进入候选验收池；调试评测实现只用旧开发族及 synthetic_fixture。
  若为了修复判断错误查看候选标签或据此调提示词，该族转入开发池并补充新验收族。
- 所有最终标签由至少两名人工复核，分歧由电力领域复核者裁决；
  同时标注原引用是否支持、独立材料是否支持、条件、地区、未覆盖部分。
  先确认文献局部上下文与视觉原文，再冻结标签；保留 not_assessable 合法选项。
- 当前真实运行仍固定旧 NERC 指南索引；VAR/PNNL 候选使用前要确认相应已有文档快照，
  不能声称这些候选已经用当前索引验收。

## 分开统计，不把结构通过当质量

执行完成率：按全部事先要求的阶段计算；另列阶段完成率、结构合法率、
格式纠正率、超时/预算/连接失败率。预算未启动案例单独计数，不能混进成功分母。

语义指标：仅使用人工冻结标签，按问题族统计 supported/contradicted/
insufficient_evidence/not_assessable 混淆矩阵、错误支持率、冲突漏检率、
缺证据识别率、原引用错误识别率、条件/否定/地区保留率及修订新增错误率。
因同族相关案例较多，报告宏平均和逐族结果，不把 18 例视作 18 个独立问题族。
完整闭环同时报告已修复/仍未解决/新引入的问题；模型自报 modified 不作为修复证据。
