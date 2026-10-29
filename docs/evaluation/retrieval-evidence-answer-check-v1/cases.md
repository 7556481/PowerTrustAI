# 全部16份实际回答与逐题判断

所有A/C均为本轮新生成；原始正文、assumptions、missing_information与引用绑定见cases.json。旧查询失败不回写。

## N1

NERC资料如何描述输电运营方TO与配电提供方DP边界负荷的建模，以及建模位置有哪些选择？

**增量：improved。** A按自身完整输入合理说明缺TO-DP建模资料；C正确保留通常性、MW/Mvar、两类位置及and/or。相关LPF补充有据。

### A 完整正文

所给NERC相关资料只涉及电网运行安全角色与要求（如电力传输运营商等责任实体），未描述TO与DP边界负荷的建模方法，也未列出建模位置选项，因此无法据此回答。

完整正确必答槽：0/2；状态：generated。

**assumptions**：无

**missing_information**：NERC相应标准或指南中关于TO与DP边界负荷建模的原文条款；边界负荷可选的建模位置清单

实际来源：dataset-record-eb646d26de0626d5f5609d11a1adc4ac5b93f5b0838fa0faed1eda141ef0ec03@e15146cdf439 / shard=chinese/middle/rank_00415.parquet;row=67967;record=397600026370;chars[2101:3158)；dataset-record-88a3b4e2204fa5c2677900cad27f6ec3e134a9ce9a15279e6430be8af64b0da5@b223f395d832 / shard=chinese/middle/rank_00417.parquet;row=314089;record=358800040502;chars[0:1144)；dataset-record-0e1f87cd860220c223302f8ccb6bd373fa519848be9993daf4d3cade9bd22c67@b6a5a2f9ede2 / shard=chinese/high/rank_00041.parquet;row=4086;record=598600026193;chars[0:1200)；dataset-record-eb646d26de0626d5f5609d11a1adc4ac5b93f5b0838fa0faed1eda141ef0ec03@e15146cdf439 / shard=chinese/middle/rank_00415.parquet;row=67967;record=397600026370;chars[1039:2101)；dataset-record-eb646d26de0626d5f5609d11a1adc4ac5b93f5b0838fa0faed1eda141ef0ec03@e15146cdf439 / shard=chinese/middle/rank_00415.parquet;row=67967;record=397600026370;chars[3158:4310)

### C 完整正文

NERC指南指出，TO与DP在潮流、稳定分析和实时运行中的边界通常用显式负荷（以MW和Mvar表示）定义。建模位置可选：直接放在母线/变电站高压侧，或放在降压变压器之后和/或等效配电阻抗之后。

跨边界建模的负荷功率因数（LPF）会影响BES的电压与无功表现；负荷不应过度依赖BES的无功支撑，BES也不应仅依赖负荷的无功支撑。

完整正确必答槽：2/2；状态：generated。

**assumptions**：无

**missing_information**：无

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=37;page_chars[1193:2392);page_lines[21:34]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=38;page_chars[1230:1503);page_lines[20:23]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=36;page_chars[1505:1568);page_lines[23:24]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=37;page_chars[2392:3587);page_lines[34:47]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=38;page_chars[656:1230);page_lines[13:19]

## N2

结合NERC资料，说明边界负荷功率因数、双方无功支撑关系与关键负荷水平下的协调如何联系起来。

**增量：mixed。** A合理缺目标段，保留一般无功备用/协调背景。C补LPF与双方支撑，但把is important / joint studies may be required强化为无条件双方需联合确定，新增关键要求强度错误。

### A 完整正文

所给NERC资料未涉及边界负荷功率因数、双方无功支撑关系或关键负荷水平下的协调，无法据此建立联系。

资料仅指出可靠性准则要求无功备用电据（含正常及事故情况下为保持电压水平的备用及其装设地点）与控制区内电压控制设备间的协调，这是最低运行要求。

完整正确必答槽：0/3；状态：generated。

**assumptions**：问题为概念性解释，未指定具体电网模型或运行点。

**missing_information**：边界负荷功率因数的定义与取值；双方无功支撑关系的具体机制；关键负荷水平的界定及其协调规则

实际来源：dataset-record-5bd52bd6ebbc91adc209add1a72fff37a599418aa5759c0df0569a3ab12f929c@7739d519837e / shard=chinese/high/rank_00041.parquet;row=4195;record=598600033938;chars[0:1200)；dataset-record-727a59bd4e3d14c8effb23cc666620e6fc9f031e7ec2c0973072db9bbf739e3d@f098f0c74219 / shard=chinese/high/rank_00038.parquet;row=144142;record=1164700002921;chars[2312:3411)；dataset-record-4ff54fb78f15fb9e3b7c75397073972b69452cd5f058d5518aef807ef3af7e74@a33155566225 / shard=chinese/middle/rank_00418.parquet;row=27508;record=602400030103;chars[0:1153)；dataset-record-5bd52bd6ebbc91adc209add1a72fff37a599418aa5759c0df0569a3ab12f929c@7739d519837e / shard=chinese/high/rank_00041.parquet;row=4195;record=598600033938;chars[1200:1344)；dataset-record-727a59bd4e3d14c8effb23cc666620e6fc9f031e7ec2c0973072db9bbf739e3d@f098f0c74219 / shard=chinese/high/rank_00038.parquet;row=144142;record=1164700002921;chars[1132:2312)

### C 完整正文

NERC指南将三者联系在TO与DP的边界协调上：边界负荷功率因数（LPF）影响BES的电压与无功表现，负荷不应过度依赖BES的滞后或超前无功支撑，BES也不应单独依赖负荷提供无功。

因此双方需联合确定临界负荷水平（如峰荷与轻荷）下商定的LPF最小/最大带宽，并明确计入边界两侧的无功补偿与相关故障情景；超出带宽时由DP在其无功计划中纠正。

完整正确必答槽：2/3；状态：generated。

**assumptions**：按概念性说明处理，不涉及具体电网参数或运行点。

**missing_information**：无

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=37;page_chars[1193:2392);page_lines[21:34]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=43;page_chars[3716:4786);page_lines[43:54]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=36;page_chars[1505:1568);page_lines[23:24]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=37;page_chars[2392:3587);page_lines[34:47]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=43;page_chars[3054:3716);page_lines[36:42]

## N3

NERC事故分析段落如何描述失去一个元件后的系统表现？请交代适用的分析类型和负荷条件。

**增量：improved。** A无原NERC段，其不足成立；二手华东运行例不可全算错，但正常裕度不足是必要前提超出情景来源。C补N-1主体/双分析/负荷端点，扰动后保持没有明确反转立即性，但立即/始终表达不充分；属残余遗漏，净改善未完整答对。

### A 完整正文

资料未给出NERC“事故分析段落”原文，仅有准则要求：应在最严重的单一故障和多重故障下不发生失去稳定、不可控解列或连锁反应导致的大面积停电，其分析属可靠性/安全性准则层面；文中未交代负荷水平与故障后具体系统响应。

相关实证来自华东电网：高峰时段受入7200 MW，任一外区直流故障将引发频率大幅下降，扰动初期（2 min内）恢复依赖一次、二次频率调节和AGC，但这是特定大功率缺失场景，不能直接推为NERC的一般描述。

此外，动态ACE触发可能使部分联络线超稳定极限跳闸，加剧功率缺额并引发连锁跳闸；正常裕度不足是必要前提。

完整正确必答槽：0/3；状态：generated。

**assumptions**：“失去一个元件”按NERC准则中的单一故障（N-1）理解。；所引内容为未核实来源的行业语料，仅作概念性说明。

**missing_information**：NERC事故分析段落原文及其对应的分析类型（如稳定分析）与负荷条件。

实际来源：dataset-record-5bd52bd6ebbc91adc209add1a72fff37a599418aa5759c0df0569a3ab12f929c@7739d519837e / shard=chinese/high/rank_00041.parquet;row=4195;record=598600033938;chars[0:1200)；dataset-record-00c2de5f3f6d01ee96a5915ef4b2f176a5623c51b1d65787eefe9cd784f99c50@70e4d4886495 / shard=chinese/high/rank_00037.parquet;row=112780;record=418800015203;chars[2187:3243)；dataset-record-eb646d26de0626d5f5609d11a1adc4ac5b93f5b0838fa0faed1eda141ef0ec03@e15146cdf439 / shard=chinese/middle/rank_00415.parquet;row=67967;record=397600026370;chars[2101:3158)；dataset-record-5bd52bd6ebbc91adc209add1a72fff37a599418aa5759c0df0569a3ab12f929c@7739d519837e / shard=chinese/high/rank_00041.parquet;row=4195;record=598600033938;chars[1200:1344)；dataset-record-00c2de5f3f6d01ee96a5915ef4b2f176a5623c51b1d65787eefe9cd784f99c50@70e4d4886495 / shard=chinese/high/rank_00037.parquet;row=112780;record=418800015203;chars[1193:2187)；dataset-record-00c2de5f3f6d01ee96a5915ef4b2f176a5623c51b1d65787eefe9cd784f99c50@70e4d4886495 / shard=chinese/high/rank_00037.parquet;row=112780;record=418800015203;chars[3243:4413)

### C 完整正文

该段落属“Contingency Analysis”（N-1）：在失去一个元件的扰动后、无操作员干预情况下，系统应保持在紧急热额定值和电压限值内，兼具稳态与稳定要求。

系统应在最小和最大预测负荷条件下均具备这一表现；电压准则同时检查电压跌落与扰动后绝对电压限值。

完整正确必答槽：1/3；状态：generated。

**assumptions**：所给资料为该NERC导则的抽取段落，具体区域限值取值由区域/公用事业确定。

**missing_information**：无

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=42;page_chars[1192:2391);page_lines[37:51]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=49;page_chars[2136:3326);page_lines[29:41]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=21;page_chars[43:292);page_lines[4:7]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=21;page_chars[1326:1907);page_lines[20:26]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=42;page_chars[0:1192);page_lines[1:37]

## N4

按NERC资料比较正常运行、单一故障、选定N-2及极端扰动的描述，说明它们在热额定值、电压限值与稳定性讨论中分别处于什么位置。

**增量：mixed。** A二手正常/N-1概述有据，缺N-2/极端扰动合理。C补3完整槽，却将when确定稳定极限改为并非用于热额定值考核而是稳定限制；末尾未说明热考核不撤回前述排他断言，新增关键范围错误。

### A 完整正文

所给资料只完整覆盖两类运行方式：无故障正常方式下，设备功率与电压须在额定范围内，对应热约束与电压约束；单一设备（线路、变压器或发电机）停运的N-1条件下，系统须能吸收动态功率振荡以维持稳定，且振荡平息、调度调整前设备功率与电压须在紧急额定范围内。

资料未给出选定N-2与极端扰动在热额定值、电压限值和稳定性讨论中的具体定位（如是否属规划或运行标准），无法补足。

完整正确必答槽：1/4；状态：generated。

**assumptions**：问题中的“选定N-2”与“极端扰动”指NERC相关分类标准，但所给资料未直接述及。

**missing_information**：NERC对选定N-2事件与极端扰动的定义、所属类别及其与热额定值、电压限值和稳定性判据的对应关系。

实际来源：dataset-record-d4b189885b19b3643aac90cf7a42e008b0f91f857b048a767eaceb0e9e4712e1@36bbe4a715bd / shard=chinese/middle/rank_00411.parquet;row=94416;record=400500011218;chars[0:463)；dataset-record-832e15ad194077de2b57f901a56f345281c37bc34688426f204c51200d14b7d8@a7ea0807c628 / shard=chinese/high/rank_00041.parquet;row=48296;record=91100000152;chars[1200:2225)；dataset-record-ae0d379bb13aa5b498b787fe3ea2a4c92d4844f84fc1ee4723f409d8a4394226@458cdbf566f0 / shard=chinese/high/rank_00040.parquet;row=77784;record=546800029753;chars[0:1116)；dataset-record-832e15ad194077de2b57f901a56f345281c37bc34688426f204c51200d14b7d8@a7ea0807c628 / shard=chinese/high/rank_00041.parquet;row=48296;record=91100000152;chars[0:1200)

### C 完整正文

NERC指南将四种情形分层：正常运行须使全部计划元件在役时满足设备正常热额定值与系统电压限值；单一故障（N-1）须在无人工干预下立即满足应急热额定值与电压限值，且同时适用于稳态与稳定性要求。

部分选定N-2并非用于热额定值考核，而是用于确定稳定性限制；更严重但概率更低的极端扰动则要求不出现电压崩溃、级联或失稳。

电压准则检验通常同时考核电压跌落准则与故障后绝对电压上下限，后者示例为0.95 pu与1.05 pu；正常与应急电压限值示例见分时段限值表。

资料未给出各情形下具体的热额定值数值，也未说明N-2热额定值考核要求。

完整正确必答槽：3/4；状态：generated。

**assumptions**：按NERC 2016无功规划指南的概念框架作一般性比较，不涉及具体电网或运行点。

**missing_information**：各情形的具体热额定值数值及N-2热额定值考核要求未在资料中给出。

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=34;page_chars[0:1198);page_lines[1:73]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=28;page_chars[945:1440);page_lines[14:19]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=33;page_chars[1193:1256);page_lines[19:20]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=34;page_chars[1198:2397);page_lines[73:87]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=21;page_chars[43:292);page_lines[4:7]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=21;page_chars[1326:1907);page_lines[20:26]

## N5

NERC资料中的动态无功资源怎样随电网电压变化调整输出？这种资源的电压控制运行方式有哪些？

**增量：improved。** A设备例子在自身资料有据，自动跟踪为部分信息，缺NERC带宽/完整自动实时连续及两模式。C完整3槽，附加具体设备参数缺口提示略泛但非关键错误。

### A 完整正文

所给资料未标注来自NERC，且无NERC关于动态无功资源的原文，以下仅为概念性解释。

资料以同步调相机为例：过励磁运行时向系统供给感性无功、提高系统电压；欠励磁运行时从系统吸收感性无功、降低系统电压。

静止无功补偿器输出随系统特定控制参数变化，可按系统无功需求或电压变化自动跟踪补偿；统一潮流控制器可连续改变输出电压幅值和相位并控制线路无功、有功潮流。

具体控制律、电压设定点及死区、增益等运行参数资料未给出。

完整正确必答槽：0/3；状态：generated。

**assumptions**：将“动态无功资源”按资料中的同步调相机、静止无功补偿器和统一潮流控制器作概念性理解。

**missing_information**：所给资料无NERC文件原文，未给出具体控制律、电压设定点、死区与增益等运行参数。

实际来源：dataset-record-246b586bce2567d228a5d25d4b391573fc54196d95f61c26afbe09f9c82492c2@c8eb1548a932 / shard=chinese/high/rank_00041.parquet;row=51732;record=866800041405;chars[0:1134)；dataset-record-5d0c8313e4c8a02dea5cc15cb43000e9b8bf73de24f65b35baaa9d49da16777b@0eee612dbac8 / shard=chinese/high/rank_00037.parquet;row=126360;record=1796300014052;chars[1139:2268)；dataset-record-f28d1c18c9a4a5643012bee632ab3eb56f77441827a9e3de606b36d11c73b9aa@e04875698ceb / shard=chinese/middle/rank_00420.parquet;row=64097;record=247600027071;chars[2400:3527)；dataset-record-246b586bce2567d228a5d25d4b391573fc54196d95f61c26afbe09f9c82492c2@c8eb1548a932 / shard=chinese/high/rank_00041.parquet;row=51732;record=866800041405;chars[1134:1327)；dataset-record-5d0c8313e4c8a02dea5cc15cb43000e9b8bf73de24f65b35baaa9d49da16777b@0eee612dbac8 / shard=chinese/high/rank_00037.parquet;row=126360;record=1796300014052;chars[0:1139)

### C 完整正文

按NERC指南，动态无功资源在规定的电压区间内随电网电压变化，于连续范围内实时自动调节无功输出；运行方式为维持设定点电压，或运行于电压下垂模式。

具体要求哪种资源类型（如STATCOM）在给定电网条件下的调节特性，需补充装置模型与运行点。

完整正确必答槽：3/3；状态：generated。

**assumptions**：无

**missing_information**：具体装置类型及其控制参数（电压区间、整定值、下垂系数）在资料片段中未给出。

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=18;page_chars[1457:1542);page_lines[19:20]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[2398:3166);page_lines[38:48]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=8;page_chars[1200:2381);page_lines[16:29]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=18;page_chars[263:1457);page_lines[7:19]

## N6

按NERC资料，从接入后的输出特性与投入退出操作看，动态和静态无功资源有什么不同？额定电压在这种比较中有什么意义？

**增量：mixed。** A投切/控制说明有二手来源、缺目标比较合理。C正确额定电压与平方依赖、手动自动投切，没有引入调试/退役；但未明确动态自动和按日常系统条件投切，并把规划研究事故前投入安排以因此接到一般日常定义后，保守记新增关键范围泛化。

### A 完整正文

所给资料均非NERC文献，无法按NERC资料作比较。

资料仅提到：静止补偿器可按母线电压高低自动控制可调电抗器吸收的感性无功，从而稳定电压。

投切式低压电容器组随用电设备同时投入、停运而退出；高压电容器组按无功潮流变化操作。

未给出动态与静态资源的输出特性对比，也未说明额定电压的作用。

完整正确必答槽：0/3；状态：generated。

**assumptions**：无

**missing_information**：NERC关于动态与静态无功资源输出特性及投入退出操作的原文，以及额定电压在该比较中的说明。

实际来源：dataset-record-1e494242600f338c5b169159139f5458455dfc3f2e80d5fd960b105b059753d0@fe9b69df5c81 / shard=chinese/high/rank_00038.parquet;row=80333;record=1557800010583;chars[1032:2158)；dataset-record-f306a7e415cee65e74fb2dc4cad24af4d8e2ebd8f863e8a6620e24b8e7791c49@30b342f2af8a / shard=chinese/middle/rank_00411.parquet;row=25277;record=1248700011977;chars[0:641)；dataset-record-f66886d92d290663acbe3632ddec86539fdef0ca06b0bc7e37d30cbd8b060c80@0efcb5585e3e / shard=chinese/middle/rank_00418.parquet;row=427909;record=204600023930;chars[3377:4564)；dataset-record-1e494242600f338c5b169159139f5458455dfc3f2e80d5fd960b105b059753d0@fe9b69df5c81 / shard=chinese/high/rank_00038.parquet;row=80333;record=1557800010583;chars[0:1032)；dataset-record-f66886d92d290663acbe3632ddec86539fdef0ca06b0bc7e37d30cbd8b060c80@0efcb5585e3e / shard=chinese/middle/rank_00418.parquet;row=427909;record=204600023930;chars[2346:3377)

### C 完整正文

NERC按并网后无功输出的可控性区分动静资源：动态资源在指定电压带宽内实时连续调节无功以维持电压或功率设定值（或电压下垂模式），部分电力电子型可在数个周波内响应；静态资源并网后提供固定额定贡献，其能力随电压平方变化，靠投切（手动或自动）改变。因此静态资源在预想事故前投入，过度依赖可能造成事故后电压不可接受。

额定电压的意义在于：静态资源标称无功对应其额定电压，而实际输出随电压平方变化，故不能把铭牌值当作任意电压下的输出；动态资源则在此带宽内连续调节。具体数值依设备型号与运行条件而异。

完整正确必答槽：1/3；状态：generated。

**assumptions**：比较限于所给NERC 2016年《Reactive Power Planning》指南中的概念性定义，未涉及具体电厂参数。

**missing_information**：所给资料未给出各类资源的具体响应时间、电压带宽、投切阈值等数值，也未说明额定电压“平方律”条件之外的适用范围。；所给文本为PDF抽取，公式与表格结构未解释，若需定量关系需核对原文。

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[2398:3166);page_lines[38:48]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=31;page_chars[2524:3574);page_lines[33:44]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=32;page_chars[209:1404);page_lines[6:16]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]

## N7

请用文字解释NERC资料所列短输电线路无功传输式的模型假设与各符号含义，不作数值计算。

**增量：improved。** A确无公式，合理不足；C完整短线忽略R/B、Vs/Vr/X/δ及无功传输，未做数值计算。Qr受端意义为符号合理推释，非新增保证。

### A 完整正文

所给资料均为电工图形与文字符号说明，未包含NERC短输电线路无功传输式，因此无法解释其模型假设与各符号含义。

完整正确必答槽：0/3；状态：generated。

**assumptions**：无

**missing_information**：NERC资料中短输电线路无功传输公式的原文及其模型假设、符号定义。

实际来源：dataset-record-3f319bb1673e6992db5948d9b4f434fb519dddba80d90a1416e6a177f8520b36@a5c75b6fe523 / shard=chinese/middle/rank_00414.parquet;row=16158;record=777300016324;chars[2010:2946)；dataset-record-7953534c4f46eb58ca9eea52cfd48e89c6ef525138094eabb03aacc341fccb54@da6b01849a71 / shard=chinese/high/rank_00037.parquet;row=190752;record=1664600017518;chars[0:1156)；dataset-record-3f319bb1673e6992db5948d9b4f434fb519dddba80d90a1416e6a177f8520b36@a5c75b6fe523 / shard=chinese/middle/rank_00414.parquet;row=16158;record=777300016324;chars[0:990)；dataset-record-3f319bb1673e6992db5948d9b4f434fb519dddba80d90a1416e6a177f8520b36@a5c75b6fe523 / shard=chinese/middle/rank_00414.parquet;row=16158;record=777300016324;chars[990:2010)；dataset-record-7953534c4f46eb58ca9eea52cfd48e89c6ef525138094eabb03aacc341fccb54@da6b01849a71 / shard=chinese/high/rank_00037.parquet;row=190752;record=1664600017518;chars[1156:2219)

### C 完整正文

NERC资料给出的短输电线路无功传输式为 Qr = (Vr/X)(Vs·cosδ − Vr)。其假设是忽略线路电阻R和电容B，故仅以线路电抗X建模。

符号含义：Vs、Vr分别为送端与受端电压幅值；X为线路电抗；δ为两端相角差（即“功角”，图中记作φ1−φ2）；Qr为受端无功功率。

原文据此指出无功取决于电压差、角差与阻抗，其中角差影响相对较小，电压差与阻抗是更强的因素。该式属理想化近似模型，不等同于实际设备。

完整正确必答槽：3/3；状态：generated。

**assumptions**：按NERC 2016年《Reactive Power Planning》指南中的概念性说明解释，不作数值计算。

**missing_information**：无

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=14;page_chars[2449:3649);page_lines[34:47]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=15;page_chars[2633:3736);page_lines[39:52]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[0:1199);page_lines[1:19]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[2398:3166);page_lines[38:48]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=14;page_chars[3649:3681);page_lines[47:48]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=15;page_chars[2330:2633);page_lines[34:38]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=16;page_chars[0:60);page_lines[1:4]

## N8

为什么NERC资料在讨论无功传输时把电压控制与无功控制联系起来？请结合短线路模型中各驱动量的相对作用解释，并交代模型适用条件。

**增量：improved。** A一般Q-V联系有二手出处，不把其R/X/I文字歧义判确定错误；C完整边界/驱动/强弱/耦合4槽，没有互为因果强化。正弦稳态/对地电容为模型解释补充，未由片段逐字说明，保留界限。

### A 完整正文

所给资料未出现NERC资料，也未给出短线路模型各驱动量的公式或相对作用，因此无法基于这些证据解释NERC为何把电压控制与无功控制联系起来，也无法按要求结合短线路模型。

只能确认一般性联系：线路和变压器电抗需要无功，感性负荷吸收无功、电容器发出无功；提高功率因数可减少线路上传输的无功Q，在R、X、I为定值时，Q越小电压损失越小，从而改善电压质量。

该解释属于源文未核验的通用说明，其条件为定值R、X、I并保持有功不变；不适用于替代NERC原文结论或短线路模型的具体分析。

完整正确必答槽：0/4；状态：generated。

**assumptions**：问题所问的NERC资料应指北美电力可靠性公司（NERC）的相关文件。；短线路模型应指以串联阻抗为主的简化交流线路模型。

**missing_information**：NERC讨论无功传输与电压控制的原文章节或段落。；短线路模型的具体表达式及各驱动量的相对作用说明。

实际来源：dataset-record-741f3cf5bd55e8339ef7a6a1bed5982e3c6e7ba1f8cac8d7b983cb67ca0af0ef@f2827bb9bf5b / shard=chinese/high/rank_00038.parquet;row=116438;record=1816800003164;chars[0:1120)；dataset-record-08e977c4ab4be6c59d7f869a8f761285681433151dec35a3b6bf2bf3360ee494@ae138146151b / shard=chinese/high/rank_00037.parquet;row=200076;record=1531200006747;chars[0:1145)；dataset-record-adbfc50bdd65b7db079a030d121ff38286274cf02a48344279cb78fb16e60a14@5529b96f9f55 / shard=chinese/high/rank_00038.parquet;row=80344;record=1557800010596;chars[0:1190)；dataset-record-741f3cf5bd55e8339ef7a6a1bed5982e3c6e7ba1f8cac8d7b983cb67ca0af0ef@f2827bb9bf5b / shard=chinese/high/rank_00038.parquet;row=116438;record=1816800003164;chars[1120:1816)；dataset-record-08e977c4ab4be6c59d7f869a8f761285681433151dec35a3b6bf2bf3360ee494@ae138146151b / shard=chinese/high/rank_00037.parquet;row=200076;record=1531200006747;chars[1145:1879)

### C 完整正文

在忽略线路电阻R和电容B的短线路模型中，Qr=(Vr/X)(Vs·cosδ−Vr)。因此无功传输受电压差、功角差和阻抗影响，但NERC指出功角差影响相对小，电压差与阻抗是强得多的驱动量，所以电压控制与无功控制紧密耦合。

该式基于正弦稳态短线路近似（R、B可忽略），且为概念性关系，不适用于长线路或需计电阻、对地电容的场合。

完整正确必答槽：4/4；状态：generated。

**assumptions**：按所给资料作概念性解释，不针对具体电网或运行点。

**missing_information**：无

实际来源：nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=8;page_chars[1200:2381);page_lines[16:29]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=50;page_chars[2084:2681);page_lines[30:37]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[0:1199);page_lines[1:19]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=7;page_chars[2398:3166);page_lines[38:48]；nerc-reactive-planning-2016@dbf1bc7c3e57 / pdf_extracted_text:file_page=51;page_chars[0:63);page_lines[1:3]
