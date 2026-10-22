# 4组固定证据生成对照：整批材料与冻结计划v1

**当前状态：用户已确认材料并明确授权本批付费执行，实际执行已停止收尾，见[结果报告](results-v1.md)。有效预算为每分支原40次共享保护、无新增整批调用帽，以下历史提案的16/128及整批截止建议均不再适用。** 真实身份以[execution-freeze-v1](execution-freeze-v1.json)为准；以下准备阶段描述保留来历，不再表示当前待授权或未实现状态。任务/评分/旧freeze-plan文件原字节保留。

2026-10-22。**待用户整批复核，不是执行授权或最终执行冻结。** 用户已接受A的开发与离线接线；本轮只准备4组、原生成器／候选各一次，计划8次初始生成。没有生成待评答案、预测或新模型调用。

材料：[模型输入任务](tasks-v1.json)、[独立评分组成项](rubric-v1.json)、[来源谱系及旧快照身份](source-lineage-v1.json)、[执行冻结计划](freeze-plan-v1.json)。下面一次展示全部问题、要求和完整交付选段；不需要逐题确认。

## 比较范围

复用已公开的NWS、USGS、NASA三个来源谱系，共六个选段，组成四个任务组；不是四个新来源或独立保留集。原[组件基线与确认](../baseline-batch-v1/owner-text-review-closeout-v1.md)全部保留，本次登记为后续生成开发材料，不拿历史成绩证明新生成可靠，也不据此宣称电力业务端到端提升。没有重新下载网页、读取旧原始响应或验证本地官方全文快照；快照身份沿用原公开记录，仅机械核对本次选段逐字相同。

两版共用相同问题、原要求、题设、证据ID、回答ID与完整输入。归档request_id区分分支，不插入问题或证据；只在系统提示／候选目录及响应契约上有预定差异。候选映射不传审核，也不作为评分要求。模型审核仍保留真实生成快照，包括提示版本，因此不声称审核器对分支身份完全盲化。

共同回答要求：中文、直接、完整正文不超过220字，计标点／空白／单元分隔；仅按交付资料与明确题设作答，有据部分照答，具体保留未解决部分。没有要求把全文背景、每个术语或所有来源细节都重复到答案。

## GEC-01：定义直接有据

**问题：** 根据给定页面解释PoP（降水概率）的含义、可测降水阈值和时空范围，并说明本页通常时段及例外。无需解释概率计算算法。

**题设／背景：** 仅解释本页归档定义，不判断真实天气。

**模型可见要求：**

- R1：解释PoP对应何种降水事件及概率含义。
- R2：给出可测降水的阈值，并保留原单位。
- R3：说明概率的时间、空间范围，以及本页通常时段是否允许另有说明。

**完整固定证据：**

### GEC-01-E1（沿用NWS-X1）

来源：[NOAA National Weather Service, Weather Forecast Office Pago Pago · Forecast Terms](https://www.weather.gov/ppg/forecast_terms)；版本：Unnumbered live page; no content-specific publication/update date identified; snapshot 2026-10-21。

定位：Precipitation Probability heading; complete body paragraph including following on/off sentence；旧提取文本区间 [3119, 3747]，0-based Unicode code points, end exclusive, in named saved extraction; not raw bytes。

选段UTF-8 SHA256：`320dd854bee60780ed75175abb41bdc17da331064461519596817cc660440694`。

```text
The probability of precipitation (POP), is defined as the likelihood of occurrence (expressed as a percent) of a measurable amount of liquid precipitation (or the water equivalent of frozen precipitation) during a specified period of time at any given point in the forecast area. Measurable precipitation is equal to or greater than 0.01 inches. Unless specified otherwise, the time period is normally 12 hours. NWS forecasts use such categorical terms as occasional, intermittent, or periods of to describe a precipitation event that has a high probability of occurrence (80%+), but is expected to be of an "on and off" nature.
```

**评测侧组成项与边界（不传模型）：**

- R1：likelihood expressed as a percent；measurable liquid precipitation or water equivalent of frozen precipitation。
- R2：equal to or greater than 0.01；inches。
- R3：specified time period；any given point in forecast area；normally 12 hours unless otherwise specified。

必须保留事件、阈值单位与时间／空间范围。把概率写成面积或时长比例，只有实际写出时才另记错误；80%及on/off等背景不是本题新增必答义务。

## GEC-02：条件关系与边界应用

**问题：** 根据给定材料，为什么某些降水预报可以省略天空状况？说明适用条件及是否强制省略，并对题设中恰好60%的情况作判断。

**题设／背景：** 题设仅作假设：某份预报的预期降水概率恰好为60%。这不是对真实天气的观测或预报。

**模型可见要求：**

- R1：说明允许省略所需的预报条件及许可强度。
- R2：解释材料给出的省略理由，不扩大为其他因果或天气保证。
- R3：明确将条件应用于预期概率恰好60%的题设，说明是否允许省略及是否必须省略。

**完整固定证据：**

### GEC-02-E1（沿用NWS-X2）

来源：[NOAA National Weather Service, Weather Forecast Office Pago Pago · Forecast Terms](https://www.weather.gov/ppg/forecast_terms)；版本：Unnumbered live page; no content-specific publication/update date identified; snapshot 2026-10-21。

定位：Sky Condition heading; complete opening paragraph, no table rows needed for this direction；旧提取文本区间 [2182, 2476]，0-based Unicode code points, end exclusive, in named saved extraction; not raw bytes。

选段UTF-8 SHA256：`d71c65d90b9b4dd852d94834b306d3a6c962305d35319978deb8158d088c2b78`。

```text
The sky condition describes the predominant/average sky cover based on percent of the sky covered by opaque (not transparent) clouds. If a high probability of precipitation (60% or greater) is expected, then the sky condition may be omitted since it is inferred from the precipitation forecast.
```

**评测侧组成项与边界（不传模型）：**

- R1：expected precipitation probability 60% or greater；omission is permitted, not mandatory。
- R2：sky condition is inferred from precipitation forecast。
- R3：explicit application to stipulated exactly 60%；allowed omission does not require omission。

60%及以上含边界，may不是must；明确说反仍可能covered，支持性错误另记。只讲一般规则而不应用题设，R3仍缺失；条件只写进旁录不算实际答案保留。

## GEC-03：多子问题仅部分有据

**问题：** 请解释给定材料中1%年超越概率洪水的含义，并说明平均重现期100年是否表示固定相隔100年。另外，这些材料能否确定一次此类洪水通常持续多少小时？有依据的部分要回答，缺依据的部分请具体指出。

**题设／背景：** 仅解释给定文献，不评价任何实际地点的洪水风险。

**模型可见要求：**

- R1：解释1%年超越概率的时间基准以及达到或超过相应洪水量级的含义。
- R2：说明平均重现期100年与固定间隔的区别。
- R3：保留单次洪水持续小时数这个子问题，明确给定材料能否提供定量回答；不把其他时间概念当成持续时间。

**完整固定证据：**

### GEC-03-E1（沿用USGS-X1）

来源：[USGS; Robert R. Holmes, Jr. and Karen Dinicola · 100-Year Flood—It’s All About Chance: Haven’t we already had one this century?](https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf)；版本：General Information Product 106, April 2010; DOI 10.3133/gip106; 1-page poster。

定位：PDF page 1, left column: So what is a 100-year flood and how is it determined?, complete first paragraph；旧提取文本区间 [136, 639]，0-based Unicode code points, end exclusive, in named saved extraction; not raw bytes。

选段UTF-8 SHA256：`64484e5160384a33fd3ea9d5da08dcffa723569ebe515f7995965b53ec8ec48f`。

以下以JSON字符串无损展示，保留原提取文本的换行及行尾空格；解码后即为完整交付原文。

```json
"In the 1960’s, the United States government \ndecided to use the 1-percent annual \nexceedance probability (AEP) flood as \nthe basis for the National Flood Insurance \nProgram. The 1-percent AEP flood was \nthought to be a fair balance between \nprotecting the public and overly stringent \nregulation.  Because the 1-percent AEP flood \nhas a 1 in 100 chance of being equaled or \nexceeded in any 1 year, and it has an average \nrecurrence interval of 100 years, it often is referred to as the “100-year flood”."
```

### GEC-03-E2（沿用USGS-X3）

来源：[USGS; Robert R. Holmes, Jr. and Karen Dinicola · 100-Year Flood—It’s All About Chance: Haven’t we already had one this century?](https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf)；版本：General Information Product 106, April 2010; DOI 10.3133/gip106; 1-page poster。

定位：PDF page 1, middle panel: On the river near me..., complete first paragraph; graph is not needed for this paragraph；旧提取文本区间 [2843, 3062]，0-based Unicode code points, end exclusive, in named saved extraction; not raw bytes。

选段UTF-8 SHA256：`64dba6138583108b74d09b39a75aa75ab3de8c0c4b01f250bb014fb4dd632e65`。

以下以JSON字符串无损展示，保留原提取文本的换行及行尾空格；解码后即为完整交付原文。

```json
"The “100-year \nflood” is an \nestimate of the \nlong-term average \nrecurrence interval, \nwhich does not \nmean that we really \nhave 100 years \nbetween each flood \nof greater or equal \nmagnitude. Floods \nhappen irregularly."
```

**评测侧组成项与边界（不传模型）：**

- R1：1 in 100 in any one year；equaling or exceeding the corresponding flood magnitude。
- R2：100 years is a long-term average recurrence interval；not a fixed interval between floods; occurrence irregular。
- R3：retain the single-flood duration-in-hours subquestion；explicitly state the delivered excerpts do not supply its quantitative duration。

R1、R2有据仍须回答。R3应具体说明给定选段未给单次持续小时数；这可以回应子问题，但定量目标仍未解决，不能因covered宣称完全解决。不得用一年或100年补成持续时间，也不能笼统拒答整个问题。

## GEC-04：术语／数字相关不等于关系有据

**问题：** 仅凭给定材料中的低偏心率和零倾角，能否推出卫星必然与地球自转同步？先回答能否据此推出，再解释材料实际说明了什么，以及所问关系还缺少什么依据。

**题设／背景：** 仅讨论这两份给定选段是否支持所问关系，不提供任何实际卫星的观测记录，也不要求数值推导。

**模型可见要求：**

- R1：明确判断给定材料是否足以建立所问的必然同步关系。
- R2：准确解释给定材料中低偏心率与零倾角各自的含义，保留限定。
- R3：说明已有几何性质与所问同步关系在材料中是否有充分连接；缺依据时指出范围，不能以术语或数字替代关系依据。

**完整固定证据：**

### GEC-04-E1（沿用NASA-X1）

来源：[NASA Earth Observatory; story by Holli Riebeek, design by Robert Simmon · Catalog of Earth Satellite Orbits](https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/)；版本：Article Sep 04, 2009; page last updated Nov 14, 2025; no numbered edition。

定位：Body before Three Classes of Orbit, complete eccentricity paragraph；旧提取文本区间 [9408, 9744]，0-based Unicode code points, end exclusive, in named saved extraction; not raw bytes。

选段UTF-8 SHA256：`4a8712f267248db1cd243771d8465b046ac1718b414a0adf2cf4026ef41163bf`。

```text
In addition to height, eccentricity and inclination also shape a satellite’s orbit. Eccentricity refers to the shape of the orbit. A satellite with a low eccentricity orbit moves in a near circle around the Earth. An eccentric orbit is elliptical, with the satellite’s distance from Earth changing depending on where it is in its orbit.
```

### GEC-04-E2（沿用NASA-X2）

来源：[NASA Earth Observatory; story by Holli Riebeek, design by Robert Simmon · Catalog of Earth Satellite Orbits](https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/)；版本：Article Sep 04, 2009; page last updated Nov 14, 2025; no numbered edition。

定位：Body before Three Classes of Orbit, complete inclination paragraph；旧提取文本区间 [10087, 10348]，0-based Unicode code points, end exclusive, in named saved extraction; not raw bytes。

选段UTF-8 SHA256：`110db3b02e55085eea3dd1dd230beaa6f076b1ed9ea347b7b6c04d329d8a866c`。

```text
Inclination is the angle of the orbit in relation to Earth’s equator. A satellite that orbits directly above the equator has zero inclination. If a satellite orbits from the north pole (geographic, not magnetic) to the south pole, its inclination is 90 degrees.
```

**评测侧组成项与边界（不传模型）：**

- R1：explicit verdict on whether these excerpts establish necessary synchronism。
- R2：low eccentricity means near-circular, not necessarily exactly zero；zero inclination describes an orbit directly above the equator。
- R3：identify absence of a source relation connecting these geometric descriptions to matching Earth's rotation。

低偏心率只支持近圆，不自动等于零；零倾角描述轨道相对赤道的几何关系及赤道上空的位置。本任务没有交付NASA-X3／X4，不据其距离或same speed简化语句出题。只说给定两选段缺少同步关系依据，不说NASA全页没有说明，也不据不足反推该轨道一定不可能同步。

## 顺序与相同原审核链

固定顺序：GEC-01 原→候选；GEC-02 候选→原；GEC-03 原→候选；GEC-04 候选→原。每个分支先生成，契约最终有效且按原机制产生实质回答时，进入相同原提取、标量工具、事实schema13及领域schema5双审、product-decision-v1.5政策，再开始下一分支。格式纠正仍属原分支，不算新的独立生成样本。

实验使用原OfflineHarness顺序路径，retriever=None，知识版本null；每组全部固定资料作为provided_evidence交付，来源绑定为user_reference，不伪称已在知识索引中验证。审核仍获得完整固定资料与真实生成快照，绝不只给映射选中的子集。本轮固定资料实验不测在线检索；没有改变生产BM25或其默认配置。

原领域审核仍使用既有电力演示规则及任务适用性判断。这里测试跨题材的文献证据使用，不证明电力领域能力；如果原审核误要求厂站数据或漏判实际问题，照实记录，不改审核器来凑通过。

实验修订预算为0，复用原政策对预算的既有处理，不改政策也不生成第二版实质答案。这样比较的是首次答案，而不是修订后的结果。所有合法答案仍可能有语义错误；仅映射最终失败也按候选契约失败，不把其结构有效的答案偷偷送审核。原无实质回答机制若触发，审核标不适用，并分别列出，不能计成完成。政策needs_information／review_required／reject本身不是调用失败。

## 模型、费用上界与停止计划

以下为**供复核的设置提案**，尚非费用授权：两版及全部审核阶段共同使用deepseek-flash、https://api.deepseek.com、90秒请求超时、8000输出token上限、96000响应字符上限；沿原连接器JSON输出、thinking关闭、非流式，不增加规划请求。model_id沿用既有公开实验的明确身份，不声称已核实当前可用性或账户配置。原连接器未设置temperature或seed，服务默认、缓存、采样和负载波动未消除。

|项目|提案与含义|
|---|---|
|初始生成|4组×2版＝8次|
|生成格式纠正|每分支最多1次，所以生成调用最多16次|
|原审核|每个有效分支还需提取、独立事实审核、领域审核及每条原引用核对；schema13当前逐引用请求，调用数随实际引用数变化|
|每分支模型预算|16次，包含生成、纠正和全部审核，不是另加16次审核|
|整批调用硬上界|8×16＝128次，不代表计划一定发128次；无任何额外评分模型调用|
|上界推导|若原引用数为C，完整一轮最多C+8：生成≤2，提取≤2，独立事实＋C引用＋事实阶段总共≤1纠正，领域≤2；若实际工作量超过16，不提高上限或重跑|
|其他限制|修订0，瞬时重试0，检索0，工具最多40／分支；步骤110秒、分支800秒，整批调用准入截止6400秒。不是含在途HTTP／存储的严格墙钟保证|

实际价格和账单金额未知，不凭旧估价填费用；按实际调用、输入／输出及缓存token分开报告。候选多映射的费用、附加引用引起的审核开销和格式纠正开销分开，不以总请求数不同直接宣称长期更便宜。

首个分支最终执行失败（格式纠正耗尽、超时、预算、必需审核／存储等失败）后，保存原输出、部分有效同级结果与在途调用归属，不开始下一计划分支；不删attempt、不换目录补跑、不自动恢复或失败回退。语义分歧、合理不足和政策拒绝照实报告，不为好结果重跑。每个未执行分支保留原因，缺失输出不虚构支持标签。

## 冻结身份与执行前剩余门禁

本轮纯离线生成了8组初始消息身份，同一任务两版GenerationInput哈希完全相同。完整初始消息仅留忽略目录data/evaluation_local/generation-mapping-comparison-v1/preparation-v1，标PREPARATION_ONLY_NOT_SENT；未创建付费批次attempt或发送标记。公开冻结计划列输入／消息SHA、字符数及源码／材料身份；字符数不当token或费用。

尚无真实执行入口，不能称计划已经可直接运行。后续入口必须复用原Harness与批次控制，先离线证明“任何最终执行失败停止后续分支”，再冻结入口及测试身份。既有run_fixed仅自动停止共享故障，不保证每种局部失败停批；不能直接沿用并冒称已覆盖。可由新入口在保存实际失败结果后发出明确的批次停止信号，保留真实原因，不假标配置不符；不得改旧批规则或另建Harness。

审核及纠正消息依赖未来答案／响应，不能现在伪造其SHA。先绑定原消息构造／解析／控制代码；未来每次实际发送前保存完整作用域和消息哈希，保证不泄漏评测侧组成项、预期边界、人工判断或候选映射。真实生成快照中的原提示身份和实际答案差异保留，不伪称两版审核消息逐字相同。

执行前还需：用户整批认可本材料与预算设置；新的载荷／费用授权；真实入口、私有存储／停止门禁离线通过；最终执行冻结及新attempt一次性绑定。只有材料确认不等于授权付费，本轮不会自动继续。

## 逐对比较与结论边界

12个原要求×2版＝24个计划覆盖观察槽，由独立原要求／组成项固定，不从模型映射生成分母；不预制待评答案或预测标签。覆盖、实际断言支持／条件、执行与政策分别报告，明确说反仍可能covered，缺证据不是矛盾，评审理由不补回答。按完整实际语义接受同义表达，一句可回应多个要求、一个要求可由多句完成；不要求重复关键词或额外逐句否认未作出的保证。全部8计划分支列出首次／最终合同、映射单独失败、答案失败、纠正、审核完成／未适用／未完成、停止和未执行。

质量审阅先看实际正文：必答点是否答到、必要条件是否在原句、无据附加是否出现、是否用少答或笼统拒答逃避。正确限制与缺失有据内容分别记录。再看映射与依据关系是否吻合；有丰富映射但答案未改善不能算收益。原审核结果和后续AI辅助、用户监督的文本复核分别保存，具体列实际问题被发现、漏掉或误报，不把政策pass当参考真值。

耗时分别记录初始答案首次保存、最终契约有效答案保存、审核结束和存储确认；初始仅映射失败的正文可供之后诊断观察，但仍不是可放行答案。初始与纠正、生成与审核的token／等待分别报告。没有自造加权总分、准确率门槛或“全部正确”字段。

若只是增加映射、未见正文改善，或更易失败却没有清楚的补偿收益，保留实验并不采用；即使4对表现有利，也只作为小规模开发观察，不证明总体提升或生产准入，不自动改提示、政策或启用图路径。当前尚无结果，4组及8分支均未执行。
