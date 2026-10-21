# v6十二参考单元：预测原文复核表

2026-10-21。按本人要求只读已有最终有效响应，原样提取以下五类预测字段，不重调模型、不修改原记录。正文为模型输出原文，未翻译、改写或修补理由；表格只做Markdown显示转义。便于逐字核对的[原字符串JSON](reviewer-v6-prediction-excerpts-v1.json)含预测ID、判断索引、最终调用号及响应UTF-8 SHA。

本人已逐项复核公开参考与映射结构；本表供下一步预测原文验真，**尚不记为全部预测语义对齐最终确认**。依据ID匹配本身不证明支持正确。模型理由中的推论或复述不升级为资料事实。

EIA-A01/U1、U2有意重复同一条合并命题及理由，表示两个参考映射到同一判断，并非模型输出两次。EIA-A04完整错误定义和NRC-A03整句否定均保留原作用域。NRC-A04/U2继续保留“参考证据不足、模型矛盾”的分歧，不更改标签。完整ID前缀为H-EIA-001/H-NRC-001。

|参考单元ID|预测命题原文|预测标签|所选依据ID|判断理由|单元级理由|
|---|---|---|---|---|---|
|EIA-A01/U1|Noncoincident demand is the sum of the demands of at least two individual systems, where these demands do not occur in the same demand interval.|supported|CAND2-EIA-GLOSSARY-X1|The EIA glossary defines noncoincident demand as the sum of two or more demands on individual systems that do not occur in the same demand interval; the answer matches both elements without adding maximum demand, metering intervals or examples.|The single answer unit gives one definitional statement covering both required aspects.|
|EIA-A01/U2|Noncoincident demand is the sum of the demands of at least two individual systems, where these demands do not occur in the same demand interval.|supported|CAND2-EIA-GLOSSARY-X1|The EIA glossary defines noncoincident demand as the sum of two or more demands on individual systems that do not occur in the same demand interval; the answer matches both elements without adding maximum demand, metering intervals or examples.|The single answer unit gives one definitional statement covering both required aspects.|
|NRC-A01/U1|For a particular radioactive substance, the time required for half of its atoms to transform into another nuclear form is the physical half-life.|supported|CAND2-NRC-GLOSSARY-X1|The NRC glossary defines half-life as the time in which one half of the atoms of a particular radioactive substance disintegrate into another nuclear form, and notes it is also called physical half-life; the answer matches this definition.|Single sentence unit asserting the definition of physical half-life.|
|EIA-A02/U1|非同时需量涉及来自两个或更多个别系统的需量求和。|supported|CAND2-EIA-GLOSSARY-X1|EIA术语将非同时需量定义为两个或更多个别系统需量之和，与断言一致。|单一断言单元，涵盖构成来源但省略区间限定。|
|NRC-A02/U1|半衰期涉及特定放射性物质中一半原子转变为另一核形态。|supported|CAND2-NRC-GLOSSARY-X1|NRC词汇表定义称半衰期是特定放射性物质一半原子衰变为另一核形态的时间；答案复述了物质、比例和转化内容，但未包含时间要素。|单一单元同时陈述物质、原子比例与核形态转变；时间含义未明确表达。|
|EIA-A03/U1|非同时需量涉及来自两个或更多个别系统的需量求和。|supported|CAND2-EIA-GLOSSARY-X1|EIA词条定义其为来自两个或更多个别系统的需量之和，与此陈述一致。|单个句子，陈述需量来源与求和；属一般文献定义复述。|
|EIA-A03/U2|这些需量发生在同一需量区间。|contradicted|CAND2-EIA-GLOSSARY-X1|EIA词条明确这些需量不发生（do not occur）在同一需量区间，故该断言与文献相矛盾。|单个句子，陈述区间限定；与文献定义相反。|
|NRC-A03/U1|物理半衰期并非特定放射性物质的一半原子转变为另一核形态所需的时间。|contradicted|CAND2-NRC-GLOSSARY-X1|NRC资料将该表述定义为半衰期本身（亦称物理或放射学半衰期），即一半原子转变为另一核形态所需的时间；答案把定义内容否定为“不是”，与文献相反。|单一否定句，针对物理半衰期定义作出相反陈述。|
|EIA-A04/U1|非同时需量的定义是取来自两个或更多个别系统的需量的平均值，而不是求和。|contradicted|CAND2-EIA-GLOSSARY-X1|文献说明非同时需量为两个或更多个别系统需量之和，答案称取平均值而非求和，与文献相反。|单一陈述句，给出构成关系但将其错误表述为平均值而非求和。|
|EIA-A04/U2|这些需量不在同一需量区间发生。|supported|CAND2-EIA-GLOSSARY-X1|文献说明这些需量不在同一需量区间发生，与该句一致。|单一陈述句，表述区间限定，与文献一致。|
|NRC-A04/U1|某种放射性物质的物理半衰期是半数原子转为另一核形态所需的时间。|supported|CAND2-NRC-GLOSSARY-X1|NRC词汇表将半衰期定义为特定放射性物质半数原子衰变为另一核形态所需的时间；答案复述了这一定义并冠以物理半衰期，与范围上下文所称物理或放射学半衰期一致。|第一个单元复述了NRC给出的物理半衰期定义。|
|NRC-A04/U2|经过一个半衰期，该物质的放射性危害就完全消失。|contradicted|CAND2-NRC-GLOSSARY-X1|给出的NRC定义只说明经过一个半衰期后半数原子衰变为另一核形态，并未支持放射性或放射性危害完全消失的说法；按该定义，仍会有一半原始原子留存，因此该附加断言与定义范围相矛盾。|第二个单元提出了定义之外的危害完全消失主张。|


仅发布本人要求的所选字段，不发布完整请求/响应、官方资料全文或凭据；原始记录仍留忽略目录。12行来自11个独立预测判断（A01两参考共享一个判断），覆盖全部12个既定参考单元；不以预测数量重算分母。[原统计](reviewer-v6-development-recheck-results-v1.json)、历史标签和成绩均未改，0新API，生产继续冻结。
