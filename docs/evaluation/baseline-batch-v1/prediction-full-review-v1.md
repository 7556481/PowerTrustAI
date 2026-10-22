# 24项最终预测完整字段复核：51覆盖槽＋58参考单元

2026-10-22。按本人明确授权，一次公开本批全部最终有效预测所选原文字段，方便整批核对。**不是二次运行或新预测，不改参考、标签、分数或对齐规则。** 原执行报告基线为`3d59cc46e7c94df617dce89565a57ec86d3bf753`。

## 阅读说明与完整性

- 覆盖：51槽逐项给出要求原文、已确认参考覆盖标签、模型原始`requirement_id/coverage/unit_ids/rationale`，不只列分歧。
- 支持：58参考逐项给出回答原句/区间、已确认参考标签及原参考理由、对应完整预测命题/类型/支持标签/依据ID/判断理由，并保留原单元理由。
- USGS-02-A03/U2与CDC-02-A03/U2仍为未对齐，全部拆分判断原样保留；不选有利子句，不合并改写标签。
- 24个总体理由也原样公开。下方JSON展示的是从最终有效响应解码得到的字段字符串；原始措辞、语言、标点和ID均保留，JSON转义仅用于可靠展示，不翻译/概括/补造理由。
- 来源选段与必要上下文在本文末尾只收录一份依据索引；题设前提在相应题卡下给出完整程序ID与原文，便于直接回查依据。
- 对齐状态和参考→预测比较来自先前AI建议，**尚待本人整批复核**；公开不等于本人验过本地响应/SHA，不称专家金标准或来源完全独立证明。

统计：24最终有效，51覆盖槽、58参考、66个唯一实际判断均收录；两个未对齐参考各含两个判断。CDC-02-A02只采用第17次调用的最终纠正响应，第16次初始无效JSON仍在忽略目录，不取其语义成绩。完整请求/响应封装、系统提示、请求头、凭据和原始档案不在本文件。

JSON块“模型原文”与“参考/程序元数据”明确分开。每个J地址为原unit_id加0起始judgment_index，不是新判断；多个同标签判断联合对应一个参考，只计一次参考，不冒充多次独立判断。

## 全部覆盖及预测原文

按题卡集中展示三份回答以便对照，原实际执行顺序不变。导航：[NWS-01](#h-bl-nws-01) · [NWS-02](#h-bl-nws-02) · [USGS-01](#h-bl-usgs-01) · [USGS-02](#h-bl-usgs-02) · [NASA-01](#h-bl-nasa-01) · [NASA-02](#h-bl-nasa-02) · [CDC-01](#h-bl-cdc-01) · [CDC-02](#h-bl-cdc-02)。

## H-BL-NWS-01

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "根据给定NWS页面解释PoP（降水概率）：它针对什么降水事件，概率适用于什么时间和空间范围，可测降水的阈值是什么？另说明本页通常采用多长时段，以及这个通常时段是否允许另有说明。不要求解释概率计算算法。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "解释PoP所针对的事件、可测阈值及概率的时空范围。"
    },
    {
      "requirement_id": "R2",
      "description": "说明本页通常时段及其例外限定。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": []
}
```

**完整交付的依据ID：** `NWS-X1`, `NWS-X2`；选段/上下文/官方定位见文末依据索引。

### H-BL-NWS-01-A01

最终有效调用：1；响应UTF-8 SHA256：`344b33b7605cd77e49fd3c6066e45ef039ca788867ce6bd185f9b173fcc04b12`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "PoP描述在指定时段内，预报区域任一点发生可测液态降水或冻结降水水当量的可能性。可测阈值是至少0.01英寸。本页通常采用12小时，但允许另有说明。"
}
```

#### 覆盖原文及理由

**R1** — 要求：解释PoP所针对的事件、可测阈值及概率的时空范围。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-f6e1121991430748ca5ba58e14bb85121660e8cf0b63584cd52e28db00262c51",
    "u-56ef61a12a9f2c583efe4ddfd8837192e00ccf1454744da16edcfc69f363cb42"
  ],
  "rationale": "答案界定了PoP针对的降水事件（可测液态降水或冻结降水的水当量），给出了可测阈值（至少0.01英寸），并说明了空间范围（预报区域任一点）和时间范围（指定时段内）。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-f6e1121991430748ca5ba58e14bb85121660e8cf0b63584cd52e28db00262c51",
    "text": "PoP描述在指定时段内，预报区域任一点发生可测液态降水或冻结降水水当量的可能性。",
    "start": 0,
    "end": 40
  },
  {
    "unit_id": "u-56ef61a12a9f2c583efe4ddfd8837192e00ccf1454744da16edcfc69f363cb42",
    "text": "可测阈值是至少0.01英寸。",
    "start": 40,
    "end": 54
  }
]
```

**R2** — 要求：说明本页通常时段及其例外限定。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-6c5de42948b3340aeae6ad4144caa5ee55aeeb715db4529c2ec58ced1b2beb68"
  ],
  "rationale": "答案指出本页通常采用12小时时段，并明确允许另有说明（但允许另有说明），同时满足了通常时段与例外限定两方面。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-6c5de42948b3340aeae6ad4144caa5ee55aeeb715db4529c2ec58ced1b2beb68",
    "text": "本页通常采用12小时，但允许另有说明。",
    "start": 54,
    "end": 73
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "PoP描述在指定时段内，预报区域任一点发生可测液态降水或冻结降水水当量的可能性。",
  "start": 0,
  "end": 40,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "保留事件、点空间和指定时段。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-f6e1121991430748ca5ba58e14bb85121660e8cf0b63584cd52e28db00262c51",
  "rationale": "该单元定义PoP为指定时段内预报区域任一点发生可测液态降水或冻结降水水当量的可能性，涵盖事件类型与时空范围，与文献定义一致；可与u-56…单元合并判定，但就本单元而言属于对定义的一般性或文献性陈述。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "PoP定义为在指定时段内，预报区域任一点发生可测液态降水或冻结降水水当量的可能性。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1明确将PoP定义为指定时段内预报区域任一点发生可测液态降水（或冻结降水水当量）的可能性（expressed as percent），与该命题一致。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "可测阈值是至少0.01英寸。",
  "start": 40,
  "end": 54,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "阈值含等号，合理中文表达。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-56ef61a12a9f2c583efe4ddfd8837192e00ccf1454744da16edcfc69f363cb42",
  "rationale": "该单元给出可测降水阈值至少0.01英寸，直接对应文献中的可测量标准。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "可测降水的阈值是至少0.01英寸。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1指出Measurable precipitation is equal to or greater than 0.01 inches，与本单元表述一致。"
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "本页通常采用12小时，但允许另有说明。",
  "start": 54,
  "end": 73,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "通常与例外都保留。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-6c5de42948b3340aeae6ad4144caa5ee55aeeb715db4529c2ec58ced1b2beb68",
  "rationale": "该单元说明通常时段为12小时并允许另有说明，完整反映文献中的默认时段与例外限定。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "本页通常采用12小时时段，但允许另有说明。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1说明Unless specified otherwise, the time period is normally 12 hours，与本单元通常12小时及允许另有说明的内容一致。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "答案完整覆盖两个要求：PoP的事件、时空范围与阈值，以及默认12小时时段和例外限定，且各陈述均与所给文献定义相符。"
}
```

### H-BL-NWS-01-A02

最终有效调用：9；响应UTF-8 SHA256：`d38233ac9e13b7710a950385263b5e67a7f9932851aa29e593c916a01a2f6893`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "该页的PoP谈的是液态降水或冻结降水水当量事件发生的可能性。材料还规定预报每六小时更新一次。"
}
```

#### 覆盖原文及理由

**R1** — 要求：解释PoP所针对的事件、可测阈值及概率的时空范围。

参考覆盖：`partially_covered`；模型覆盖：`partially_covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "partially_covered",
  "unit_ids": [
    "u-258e0551f4fcd571b9b25f333aa2dbd81a9a75c8f620cbd5cef3742c5c59d9f7"
  ],
  "rationale": "Unit u-...9f7 explains the event type (liquid precipitation or water equivalent of frozen precipitation), but it omits the measurable threshold (≥0.01 inches) and the spatial scope (any point in the forecast area) and the temporal scope (specified period). Only the event-type aspect is addressed."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-258e0551f4fcd571b9b25f333aa2dbd81a9a75c8f620cbd5cef3742c5c59d9f7",
    "text": "该页的PoP谈的是液态降水或冻结降水水当量事件发生的可能性。",
    "start": 0,
    "end": 30
  }
]
```

**R2** — 要求：说明本页通常时段及其例外限定。

参考覆盖：`missing`；模型覆盖：`missing`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "missing",
  "unit_ids": [],
  "rationale": "Neither unit addresses the normally 12-hour period nor the 'unless specified otherwise' exception clause. Unit u-...b9a9 instead asserts a six-hour update interval, which is a different claim and not a statement of the usual period or its exception."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "该页的PoP谈的是液态降水或冻结降水水当量事件发生的可能性。",
  "start": 0,
  "end": 30,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "只表事件，没有无条件地替代完整定义。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-258e0551f4fcd571b9b25f333aa2dbd81a9a75c8f620cbd5cef3742c5c59d9f7",
  "rationale": "Single proposition stating what PoP concerns: the likelihood of a liquid precipitation or frozen precipitation water-equivalent event. It does not mention threshold, time period, or areal scope."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "PoP refers to the likelihood of occurrence of a liquid precipitation or frozen precipitation water-equivalent event.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1 defines POP as the likelihood of occurrence of a measurable amount of liquid precipitation or the water equivalent of frozen precipitation, matching the proposition's event description within its definitional scope."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "材料还规定预报每六小时更新一次。",
  "start": 30,
  "end": 46,
  "expected_support": "insufficient_evidence",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "通常预报时段不是更新频率；未提供更新周期，不能推矛盾。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-00de528eb913f38c6f4c6c619682faf95ea4a35ea8fb21e67a85ccbcbf32b9a9",
  "rationale": "Single proposition asserting the material specifies forecasts update every six hours. No supplied evidence states a six-hour update interval."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "The supplied material specifies that forecasts are updated every six hours.",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1 states the time period is normally 12 hours; it says nothing about a six-hour update cadence. The only time figure given is 12 hours, which conflicts with a six-hour interval assertion attributed to the supplied material."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "The answer addresses the event type of PoP but omits the measurable threshold, temporal/spatial scope, and the usual 12-hour period with its exception; it also introduces an unsupported six-hour update claim."
}
```

### H-BL-NWS-01-A03

最终有效调用：18；响应UTF-8 SHA256：`45392e5d291528fccb716c8b5d43b309d81bf9eb7ff14d663921d90b8175964f`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "PoP指在指定时段内预报区任一点发生可测液态降水或冻结降水水当量的概率。这里的可测阈值为至少0.10英寸。本页时段固定为12小时，不允许另行指定。"
}
```

#### 覆盖原文及理由

**R1** — 要求：解释PoP所针对的事件、可测阈值及概率的时空范围。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-373f76ecd7a1c6ed610574d74fe426b006dd707dff3c0a55b8efad75bf96f95d",
    "u-b7cf952a38b62e5903d688c9a5d6a4788ba0cd40235a284f4bd5225fcc141470"
  ],
  "rationale": "The answer addresses the event (measurable liquid precipitation or water equivalent of frozen precipitation), the spatial range (any point in the forecast area), the temporal range (during a specified period of time), and the measurable threshold (at least 0.10 inches). All aspects of R1 are explicitly addressed, though the threshold value differs from the literature."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-373f76ecd7a1c6ed610574d74fe426b006dd707dff3c0a55b8efad75bf96f95d",
    "text": "PoP指在指定时段内预报区任一点发生可测液态降水或冻结降水水当量的概率。",
    "start": 0,
    "end": 36
  },
  {
    "unit_id": "u-b7cf952a38b62e5903d688c9a5d6a4788ba0cd40235a284f4bd5225fcc141470",
    "text": "这里的可测阈值为至少0.10英寸。",
    "start": 36,
    "end": 53
  }
]
```

**R2** — 要求：说明本页通常时段及其例外限定。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-cfbca8a61ebd0f639677bfe5792e59251c6d1280421e381ffd637cd4037f01ba"
  ],
  "rationale": "The answer states the usual time period is fixed at 12 hours and explicitly says another period may not be specified, addressing both the usual period and its exception qualification. The assertion contradicts the literature's 'unless specified otherwise' allowance, but it still addresses the aspect."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-cfbca8a61ebd0f639677bfe5792e59251c6d1280421e381ffd637cd4037f01ba",
    "text": "本页时段固定为12小时，不允许另行指定。",
    "start": 53,
    "end": 73
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "PoP指在指定时段内预报区任一点发生可测液态降水或冻结降水水当量的概率。",
  "start": 0,
  "end": 36,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "事件和时空范围完整。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-373f76ecd7a1c6ed610574d74fe426b006dd707dff3c0a55b8efad75bf96f95d",
  "rationale": "This unit defines PoP, covering the event type, spatial scope, and temporal scope. It does not state the measurable threshold, which is handled in the next unit."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "PoP is the probability of measurable liquid precipitation or water equivalent of frozen precipitation occurring during a specified period at any point in the forecast area.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1 defines POP as the likelihood of measurable liquid precipitation or water equivalent of frozen precipitation during a specified period at any given point in the forecast area, matching the unit's definition."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "这里的可测阈值为至少0.10英寸。",
  "start": 36,
  "end": 53,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "0.10与交付0.01定义阈值不一致。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-b7cf952a38b62e5903d688c9a5d6a4788ba0cd40235a284f4bd5225fcc141470",
  "rationale": "This unit asserts the measurable threshold is at least 0.10 inches. It is a single quantitative claim about threshold."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "The measurable precipitation threshold is at least 0.10 inches.",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1 states measurable precipitation is equal to or greater than 0.01 inches, directly contradicting the claimed 0.10-inch threshold."
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "本页时段固定为12小时，不允许另行指定。",
  "start": 53,
  "end": 73,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X1"
  ],
  "rationale": "明确否认原文允许另行说明的例外。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-cfbca8a61ebd0f639677bfe5792e59251c6d1280421e381ffd637cd4037f01ba",
  "rationale": "This unit asserts the page's period is fixed at 12 hours and that no other period may be specified, covering both the usual duration and the exception qualification."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "On this page the time period is fixed at 12 hours and no other period may be specified.",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "NWS-X1"
  ],
  "rationale": "NWS-X1 says the time period is normally 12 hours unless specified otherwise, which permits another specified period. The unit's 'not allowed to specify otherwise' contradicts this exception allowance, even though the 12-hour default is consistent."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "R1 and R2 are both addressed; the event and spatial/temporal scope match the literature, while the threshold (0.10 vs 0.01 inches) and the non-allowance of another period contradict the literature."
}
```

## H-BL-USGS-01

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "根据给定USGS资料，解释“百年洪水”与1%年超越概率的关系：1%针对怎样的事件和时间范围？平均100年重现期是否意味着相邻此类洪水必须相隔100年？不计算多年累计风险或任何具体河流流量。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "说明1%概率对应的洪水量级关系及年度范围。"
    },
    {
      "requirement_id": "R2",
      "description": "解释平均100年重现期与相邻洪水间隔的关系。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": []
}
```

**完整交付的依据ID：** `USGS-X1`, `USGS-X2`, `USGS-X3`；选段/上下文/官方定位见文末依据索引。

### H-BL-USGS-01-A01

最终有效调用：2；响应UTF-8 SHA256：`0783f9f54cc03c0967f408caf61e55efc08ecf577f352516855a05a0d41d3764`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "所谓百年洪水，对应任一年达到或超过相应洪水量级的机会为百分之一。100年是长期平均重现期，并不安排两场洪水严格间隔100年；它们出现并不规则。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明1%概率对应的洪水量级关系及年度范围。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-98476611151a3ec02d1dd576998cc8605d1a0412457de85b17f7c23e3653a6da"
  ],
  "rationale": "答案明确指出百年洪水是在任一年达到或超过相应洪水量级的机会为百分之一，涵盖事件量级关系与年度时间范围。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-98476611151a3ec02d1dd576998cc8605d1a0412457de85b17f7c23e3653a6da",
    "text": "所谓百年洪水，对应任一年达到或超过相应洪水量级的机会为百分之一。",
    "start": 0,
    "end": 32
  }
]
```

**R2** — 要求：解释平均100年重现期与相邻洪水间隔的关系。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-c71619beb9809c8cbc1d96c45498ab4a3294063717e7724f70061ec61409301c"
  ],
  "rationale": "答案说明100年是长期平均重现期，并不保证两场洪水严格间隔100年，且洪水出现不规则，直接回应平均重现期与相邻间隔的关系。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-c71619beb9809c8cbc1d96c45498ab4a3294063717e7724f70061ec61409301c",
    "text": "100年是长期平均重现期，并不安排两场洪水严格间隔100年；它们出现并不规则。",
    "start": 32,
    "end": 71
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "所谓百年洪水，对应任一年达到或超过相应洪水量级的机会为百分之一。",
  "start": 0,
  "end": 32,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X1"
  ],
  "rationale": "年范围、概率及超越关系完整。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-98476611151a3ec02d1dd576998cc8605d1a0412457de85b17f7c23e3653a6da",
  "rationale": "该单元陈述百年洪水对应任一年达到或超过相应量级的概率为1%，覆盖事件量级与年度范围两个要素。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "百年洪水对应任一年达到或超过相应洪水量级的机会为百分之一。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X1"
  ],
  "rationale": "USGS-X1指出1%年超越概率洪水在任一年有百分之一机会被达到或超过，并因平均重现期100年而常称百年洪水，直接支持该命题。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "100年是长期平均重现期，并不安排两场洪水严格间隔100年；它们出现并不规则。",
  "start": 32,
  "end": 71,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X3"
  ],
  "rationale": "同义解释平均不等固定。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-c71619beb9809c8cbc1d96c45498ab4a3294063717e7724f70061ec61409301c",
  "rationale": "该单元包含两个断言：100年为长期平均重现期，且不意味着两场洪水严格间隔100年、出现并不规则。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "100年是长期平均重现期。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X1",
    "USGS-X3"
  ],
  "rationale": "USGS-X1称其平均重现期为100年，USGS-X3称百年洪水是长期平均重现期的估计，二者支持该断言。"
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "100年重现期并不安排两场洪水严格间隔100年；它们出现并不规则。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X3"
  ],
  "rationale": "USGS-X3明确说并不意味着每场达到或超过该量级的洪水之间真有100年间隔，洪水发生不规则，直接支持该断言。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "两个答案单元分别覆盖R1的1%年超越概率含义与R2的平均重现期间隔含义，均与USGS文献一致，未涉及多年累计风险或具体流量计算。"
}
```

### H-BL-USGS-01-A02

最终有效调用：10；响应UTF-8 SHA256：`3cbba341ddf995e9f798ef519c1745f24b2eb34efa4d1b9ab96fca1901ca5c89`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "任一年达到或超过百年洪水相应量级的概率是1%。材料指定这种洪水每次持续24小时。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明1%概率对应的洪水量级关系及年度范围。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-d48419a3edbc02abc68f7b335eee92fcc349229bb5cbf920f1444228e0d7e1b3"
  ],
  "rationale": "答案明确说明任一年达到或超过百年洪水相应量级的概率为1%，既涉及量级关系（达到或超过），也涉及年度时间范围（任一年）。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-d48419a3edbc02abc68f7b335eee92fcc349229bb5cbf920f1444228e0d7e1b3",
    "text": "任一年达到或超过百年洪水相应量级的概率是1%。",
    "start": 0,
    "end": 23
  }
]
```

**R2** — 要求：解释平均100年重现期与相邻洪水间隔的关系。

参考覆盖：`missing`；模型覆盖：`missing`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "missing",
  "unit_ids": [],
  "rationale": "答案未提及平均100年重现期，也未说明它是否意味着相邻此类洪水相隔100年，仅说明洪水持续24小时。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "任一年达到或超过百年洪水相应量级的概率是1%。",
  "start": 0,
  "end": 23,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X1"
  ],
  "rationale": "仅年概率，不自动补出间隔论述。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-d48419a3edbc02abc68f7b335eee92fcc349229bb5cbf920f1444228e0d7e1b3",
  "rationale": "该单元陈述任一年等于或超过百年洪水相应量级的概率为1%，对应R1的概率与时间范围，但未涉及重现期与间隔问题。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "任一年达到或超过百年洪水相应量级的概率是1%。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X1"
  ],
  "rationale": "USGS-X1说明1%年超越概率洪水在任一年有1/100的等于或超过几率，且常被称为百年洪水，与该陈述的量级关系及年度范围一致。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "材料指定这种洪水每次持续24小时。",
  "start": 23,
  "end": 40,
  "expected_support": "insufficient_evidence",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X1",
    "USGS-X2"
  ],
  "rationale": "未给百年洪水固定持续时间；一般差异陈述也不足以证明本具体时长矛盾。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-e0fc68daae42bcc82f5c689edfa5d32bc0d937cc1f6e199474782479c3021b8a",
  "rationale": "该单元声称材料指定这种洪水每次持续24小时；这是关于洪水持续时间的附加主张，与题目所问的概率/重现期关系不同。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "材料指定百年洪水每次持续24小时。",
  "claim_type": "external_claim",
  "support": "insufficient_evidence",
  "basis_ids": [
    "USGS-X1",
    "USGS-X2"
  ],
  "rationale": "所给文献说明1%年超越概率及洪水定义，但未提供任何材料指定此类洪水每次持续24小时的记录；该持续时间为实际材料属性断言，缺乏相应的实际记录支持。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "答案覆盖了1%年超越概率与百年洪水量级关系，但未解释平均100年重现期与相邻洪水间隔的关系，并包含文献未支持的24小时持续时间附加主张。"
}
```

### H-BL-USGS-01-A03

最终有效调用：19；响应UTF-8 SHA256：`61223cea1d6db041823af7c4e8ad7f85d87d5e7765920e32e31f57ed49a0bcc0`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "任一年达到或超过相应洪水量级的概率是1%。100年平均重现期意味着相邻两场此类洪水必须固定相隔100年。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明1%概率对应的洪水量级关系及年度范围。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-4a66d498f3d6ecb2a57266f1ffa644afb17443056ca5b9726a072633a2c2f75e"
  ],
  "rationale": "The answer states the 1% probability that in any year a flood reaches or exceeds the corresponding magnitude, addressing both the magnitude relation and the annual time frame."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-4a66d498f3d6ecb2a57266f1ffa644afb17443056ca5b9726a072633a2c2f75e",
    "text": "任一年达到或超过相应洪水量级的概率是1%。",
    "start": 0,
    "end": 21
  }
]
```

**R2** — 要求：解释平均100年重现期与相邻洪水间隔的关系。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-57c703899e42f2f20372f69f0c96a996b9e51fa628e4e84008914d080be62ac3"
  ],
  "rationale": "The answer explicitly claims a 100-year average recurrence interval means consecutive such floods must be exactly 100 years apart, directly addressing the relation (though contradicting the source)."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-57c703899e42f2f20372f69f0c96a996b9e51fa628e4e84008914d080be62ac3",
    "text": "100年平均重现期意味着相邻两场此类洪水必须固定相隔100年。",
    "start": 21,
    "end": 52
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "任一年达到或超过相应洪水量级的概率是1%。",
  "start": 0,
  "end": 21,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X1"
  ],
  "rationale": "正确的年度事件概率。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-4a66d498f3d6ecb2a57266f1ffa644afb17443056ca5b9726a072633a2c2f75e",
  "rationale": "Single assertion about annual exceedance probability and event magnitude; judged as a literature-based definition claim matching USGS-X1."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "In any given year, the probability of a flood equaling or exceeding the corresponding 100-year flood magnitude is 1%.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X1"
  ],
  "rationale": "USGS-X1 states the 1-percent AEP flood has a 1 in 100 chance of being equaled or exceeded in any 1 year, matching the assertion."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "100年平均重现期意味着相邻两场此类洪水必须固定相隔100年。",
  "start": 21,
  "end": 52,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X3"
  ],
  "rationale": "直接违背不固定且不规则的解释。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-57c703899e42f2f20372f69f0c96a996b9e51fa628e4e84008914d080be62ac3",
  "rationale": "Single assertion about mean recurrence interval implying fixed 100-year spacing; judged against USGS literature, which contradicts the fixed-spacing interpretation."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "A 100-year average recurrence interval means consecutive floods of that magnitude must be exactly 100 years apart.",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "USGS-X1",
    "USGS-X3"
  ],
  "rationale": "USGS-X3 explicitly states the 100-year flood estimate does not mean 100 years between each flood of greater or equal magnitude and that floods happen irregularly; USGS-X1 calls it an average recurrence interval, contradicting the asserted fixed 100-year spacing."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "R1 is correctly addressed and supported by literature; R2 is addressed but the fixed-spacing interpretation is contradicted by the USGS source, which describes irregular floods and a long-term average recurrence interval."
}
```

## H-BL-NASA-01

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "根据给定NASA资料，分别说明偏心率与倾角描述轨道的什么性质。解释低偏心率所能说明的形状，以及直接位于赤道上空的轨道所对应的倾角。不根据距离推导轨道类型，也不判断实际卫星。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "说明偏心率描述的性质与低偏心率对应的形状。"
    },
    {
      "requirement_id": "R2",
      "description": "说明倾角描述的参照关系及赤道上空轨道的倾角。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": []
}
```

**完整交付的依据ID：** `NASA-X1`, `NASA-X2`, `NASA-X3`, `NASA-X4`；选段/上下文/官方定位见文末依据索引。

### H-BL-NASA-01-A01

最终有效调用：3；响应UTF-8 SHA256：`85b87a3ffb0ee09881d64b63e559007207f60d9a55f0c28c8a666ea76f9e0e4b`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "偏心率描述轨道形状，偏心率低说明轨道近似圆形。倾角描述轨道相对于地球赤道的角度，直接位于赤道上空的轨道倾角为零。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明偏心率描述的性质与低偏心率对应的形状。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-384faa087b24bd9ffab8419bfae215d4c1e3307fddaccc7bbd7e9fe134c81b06"
  ],
  "rationale": "Unit states eccentricity describes orbit shape and low eccentricity means a near-circular orbit, addressing both parts of R1."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-384faa087b24bd9ffab8419bfae215d4c1e3307fddaccc7bbd7e9fe134c81b06",
    "text": "偏心率描述轨道形状，偏心率低说明轨道近似圆形。",
    "start": 0,
    "end": 23
  }
]
```

**R2** — 要求：说明倾角描述的参照关系及赤道上空轨道的倾角。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-4681addd9f0ae6a0415e931899241f2e555c0be6899636a9fdf8273e462950e7"
  ],
  "rationale": "Unit states inclination is the orbit angle relative to Earth's equator and that an orbit directly over the equator has zero inclination, addressing both parts of R2."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-4681addd9f0ae6a0415e931899241f2e555c0be6899636a9fdf8273e462950e7",
    "text": "倾角描述轨道相对于地球赤道的角度，直接位于赤道上空的轨道倾角为零。",
    "start": 23,
    "end": 56
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "偏心率描述轨道形状，偏心率低说明轨道近似圆形。",
  "start": 0,
  "end": 23,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X1"
  ],
  "rationale": "近圆不改成零。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-384faa087b24bd9ffab8419bfae215d4c1e3307fddaccc7bbd7e9fe134c81b06",
  "rationale": "Single sentence with two assertions: eccentricity describes orbit shape, and low eccentricity implies near-circular shape. Both are general definitions/rules restating literature."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Eccentricity describes the shape of the orbit.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X1"
  ],
  "rationale": "NASA-X1 states eccentricity refers to the shape of the orbit, matching the proposition within the literature scope."
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "A low eccentricity indicates a near-circular orbit.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X1"
  ],
  "rationale": "NASA-X1 states a satellite with low eccentricity moves in a near circle around Earth, matching the proposition."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "倾角描述轨道相对于地球赤道的角度，直接位于赤道上空的轨道倾角为零。",
  "start": 23,
  "end": 56,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X2"
  ],
  "rationale": "参照和赤道情形完整。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-4681addd9f0ae6a0415e931899241f2e555c0be6899636a9fdf8273e462950e7",
  "rationale": "Single sentence with two assertions: inclination is the orbit's angle relative to Earth's equator, and an orbit directly over the equator has zero inclination. Both are general definitions restating literature."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Inclination describes the angle of the orbit relative to Earth's equator.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X2"
  ],
  "rationale": "NASA-X2 states inclination is the angle of the orbit in relation to Earth's equator, matching the proposition."
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "An orbit directly over the equator has zero inclination.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X2"
  ],
  "rationale": "NASA-X2 states a satellite orbiting directly above the equator has zero inclination, matching the proposition."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "Both requirements are covered by the answer's two units, each assertion consistent with the supplied literature definitions. No distance-based orbit-type inference or actual-satellite judgment appears, consistent with the question's constraints."
}
```

### H-BL-NASA-01-A02

最终有效调用：11；响应UTF-8 SHA256：`305ddb858ded0c6d5b166fe7bd84e8d5f6f1e8bbcbd80bf9364a241d7a64ca51`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "偏心率描述轨道的形状。倾角衡量轨道与地球赤道的夹角，直接在赤道上空的轨道倾角为零。资料还给出了低偏心率判定的统一上限0.05。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明偏心率描述的性质与低偏心率对应的形状。

参考覆盖：`partially_covered`；模型覆盖：`partially_covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "partially_covered",
  "unit_ids": [
    "u-b9c694a5e96d6e541d6a3ce481f2892433a0609be79609192d41924bb1e4545a"
  ],
  "rationale": "The answer states that eccentricity describes the shape of the orbit, but it does not explain what shape a low eccentricity indicates (e.g., near circular)."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-b9c694a5e96d6e541d6a3ce481f2892433a0609be79609192d41924bb1e4545a",
    "text": "偏心率描述轨道的形状。",
    "start": 0,
    "end": 11
  }
]
```

**R2** — 要求：说明倾角描述的参照关系及赤道上空轨道的倾角。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-3275fd9bd80eb9518781f862ae64304990cfd9c9d1b2ea3324f29959a14dd50f"
  ],
  "rationale": "The answer states that inclination measures the angle between the orbit and Earth's equator, and that an orbit directly above the equator has zero inclination."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-3275fd9bd80eb9518781f862ae64304990cfd9c9d1b2ea3324f29959a14dd50f",
    "text": "倾角衡量轨道与地球赤道的夹角，直接在赤道上空的轨道倾角为零。",
    "start": 11,
    "end": 41
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "偏心率描述轨道的形状。",
  "start": 0,
  "end": 11,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X1"
  ],
  "rationale": "只给性质，没有低偏心率形状关系。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-b9c694a5e96d6e541d6a3ce481f2892433a0609be79609192d41924bb1e4545a",
  "rationale": "This unit asserts only that eccentricity describes orbital shape; it does not address the shape associated with low eccentricity."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Eccentricity describes the shape of the orbit.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X1"
  ],
  "rationale": "NASA-X1 states that eccentricity refers to the shape of the orbit."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "倾角衡量轨道与地球赤道的夹角，直接在赤道上空的轨道倾角为零。",
  "start": 11,
  "end": 41,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X2"
  ],
  "rationale": "R2完整，不受R1缺失影响。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-3275fd9bd80eb9518781f862ae64304990cfd9c9d1b2ea3324f29959a14dd50f",
  "rationale": "This unit gives the definition of inclination and the zero-inclination case for an equatorial orbit."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Inclination measures the angle between the orbit and Earth's equator.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X2"
  ],
  "rationale": "NASA-X2 defines inclination as the angle of the orbit in relation to Earth's equator."
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "An orbit directly above the equator has an inclination of zero.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X2"
  ],
  "rationale": "NASA-X2 states that a satellite that orbits directly above the equator has zero inclination."
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "资料还给出了低偏心率判定的统一上限0.05。",
  "start": 41,
  "end": 63,
  "expected_support": "insufficient_evidence",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X1"
  ],
  "rationale": "未提供低偏心率数值上限。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-2f665b16394f99124fa30422181a03c71498388bc193a7e2bc3d11804b1cde30",
  "rationale": "This unit claims that the provided material gives a uniform upper limit of 0.05 for low eccentricity, but no evidence supports this assertion."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "The provided material gives a uniform upper limit of 0.05 for low eccentricity determination.",
  "claim_type": "literature_statement",
  "support": "insufficient_evidence",
  "basis_ids": [],
  "rationale": "None of the supplied evidence (NASA-X1 through NASA-X4) mentions any numerical threshold for low eccentricity."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "The answer correctly identifies eccentricity with orbital shape and defines inclination with respect to the equator, but it omits the near-circular shape of low-eccentricity orbits and introduces an unsupported threshold of 0.05."
}
```

### H-BL-NASA-01-A03

最终有效调用：20；响应UTF-8 SHA256：`cce523b2ff2eabf637cd70447f742621f8c44f0bc09d8b2102ba1be64f8fa456`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "偏心率描述轨道形状。低偏心率对应近似圆形。材料保证所有低偏心率轨道的偏心率都不超过0.02。倾角是轨道相对地球赤道的角度。直接在赤道上空的轨道倾角为90度。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明偏心率描述的性质与低偏心率对应的形状。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-15b48b7d206f1f7501931983335639ef8c39795955cd75f4d91e84e54246a1c4",
    "u-75a494550d7d052a8d86b2d663745fd84fc35abdcdd6c8634872168e5a273b6e"
  ],
  "rationale": "The answer states eccentricity describes orbit shape (u-15b...) and that low eccentricity corresponds to a near-circular shape (u-75a...), addressing both parts of R1."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-15b48b7d206f1f7501931983335639ef8c39795955cd75f4d91e84e54246a1c4",
    "text": "偏心率描述轨道形状。",
    "start": 0,
    "end": 10
  },
  {
    "unit_id": "u-75a494550d7d052a8d86b2d663745fd84fc35abdcdd6c8634872168e5a273b6e",
    "text": "低偏心率对应近似圆形。",
    "start": 10,
    "end": 21
  }
]
```

**R2** — 要求：说明倾角描述的参照关系及赤道上空轨道的倾角。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-89ea7485bdafcec77159c7808a7fe2eae27ef81aeb5ff6a39cfc655b828378d9",
    "u-6eb5b18325e1af129bf89853481bd1695bb80e4664f731f15b7b9aa15ad114c6"
  ],
  "rationale": "The answer states inclination is the angle relative to Earth's equator (u-89e...) and states a directly-above-equator orbit has 90 degrees inclination (u-6eb...), explicitly addressing both the reference relation and the equatorial inclination value."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-89ea7485bdafcec77159c7808a7fe2eae27ef81aeb5ff6a39cfc655b828378d9",
    "text": "倾角是轨道相对地球赤道的角度。",
    "start": 46,
    "end": 61
  },
  {
    "unit_id": "u-6eb5b18325e1af129bf89853481bd1695bb80e4664f731f15b7b9aa15ad114c6",
    "text": "直接在赤道上空的轨道倾角为90度。",
    "start": 61,
    "end": 78
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "偏心率描述轨道形状。",
  "start": 0,
  "end": 10,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X1"
  ],
  "rationale": "性质描述沿用原U1。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-15b48b7d206f1f7501931983335639ef8c39795955cd75f4d91e84e54246a1c4",
  "rationale": "Single assertion that eccentricity describes orbit shape; matches the general literature definition without site observation."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Eccentricity describes the shape of an orbit.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X1"
  ],
  "rationale": "NASA-X1 states eccentricity refers to the shape of the orbit, directly supporting this general definition."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "低偏心率对应近似圆形。",
  "start": 10,
  "end": 21,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X1"
  ],
  "rationale": "保留near circle，只陈述有据近圆，不推出精确圆形。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-75a494550d7d052a8d86b2d663745fd84fc35abdcdd6c8634872168e5a273b6e",
  "rationale": "Single assertion linking low eccentricity to a near-circular shape; matches literature."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "A low eccentricity orbit corresponds to a near-circle shape.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X1"
  ],
  "rationale": "NASA-X1 states a satellite with low eccentricity moves in a near circle around Earth, supporting this general statement."
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "材料保证所有低偏心率轨道的偏心率都不超过0.02。",
  "start": 21,
  "end": 46,
  "expected_support": "insufficient_evidence",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X1"
  ],
  "rationale": "选段没有给出低偏心率的统一数值上限，也没有这种保证；仅缺依据，不假定该上限在物理上必错或与近圆直接矛盾。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-928372853a51f9f5adbece0371ed798f46dacf5f5576cf572df04195eee6c039",
  "rationale": "Assertion attributed to '材料' (the material) that a guarantee caps eccentricity of all low-eccentricity orbits at 0.02; no supplied literature or premise contains this numeric guarantee, and it is not a site claim but a material-content claim lacking support."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "The material guarantees that all low-eccentricity orbits have eccentricity not exceeding 0.02.",
  "claim_type": "literature_statement",
  "support": "insufficient_evidence",
  "basis_ids": [],
  "rationale": "No supplied literature evidence states a 0.02 eccentricity threshold or such a guarantee; the numeric bound and guarantee are absent from all evidence IDs, so this material-content claim cannot be supported."
}
```

**U4** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U4",
  "exact_text": "倾角是轨道相对地球赤道的角度。",
  "start": 46,
  "end": 61,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X2"
  ],
  "rationale": "沿用原U3的赤道参照描述。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-89ea7485bdafcec77159c7808a7fe2eae27ef81aeb5ff6a39cfc655b828378d9",
  "rationale": "Single assertion defining inclination as the angle relative to Earth's equator; matches literature."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Inclination is the angle of the orbit relative to Earth's equator.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NASA-X2"
  ],
  "rationale": "NASA-X2 states inclination is the angle of the orbit in relation to Earth's equator, matching the definition."
}
```

**U5** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U5",
  "exact_text": "直接在赤道上空的轨道倾角为90度。",
  "start": 61,
  "end": 78,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X2"
  ],
  "rationale": "沿用原U4，原文明示赤道上空零倾角，90度是极地情形。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-6eb5b18325e1af129bf89853481bd1695bb80e4664f731f15b7b9aa15ad114c6",
  "rationale": "Single assertion that a directly-above-equator orbit has 90 degrees inclination. This is a value claim that is actually opposite to the literature, which assigns zero inclination to directly-above-equator orbits; coverage of R2 is maintained but correctness is contradicted."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "An orbit directly above the equator has an inclination of 90 degrees.",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "NASA-X2"
  ],
  "rationale": "NASA-X2 states a satellite orbiting directly above the equator has zero inclination, and 90 degrees applies to a pole-to-pole orbit; the asserted 90-degree value is therefore contradicted."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "R1 and R2 are both addressed (R1 correctly on shape and low-eccentricity near-circle; R2 defines inclination correctly but gives the wrong equatorial value). The 0.02 guarantee claim lacks any supporting evidence."
}
```

## H-BL-CDC-01

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "根据给定CDC资料，仅说明清水达到翻滚沸腾后的通常煮沸时间及海拔例外。仅作假定：没有安全瓶装水可用，准备处理的是清水，地点海拔为7000英尺，且水已达到翻滚沸腾。应用本页计时规则说明该假定下应采用哪一时长。本题只问时间规则，不要求复述准备、冷却或储存步骤，不判断任何现场水源是否安全。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "说明翻滚沸腾后的通常计时规则及海拔例外条件和时长。"
    },
    {
      "requirement_id": "R2",
      "description": "把计时规则应用到题设7000英尺且已翻滚沸腾的情形。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": [
    {
      "premise_id": "p-5b7fd7111a5fb98822915b809315650891d7305ff50e11cd90b7f64c72552fa7",
      "text": "没有安全瓶装水可用，准备处理的是清水，地点海拔为7000英尺，且水已达到翻滚沸腾。",
      "start": 40,
      "end": 81,
      "origin": "question",
      "status": "assumed_for_this_question_only",
      "site_verified": false
    }
  ]
}
```

**完整交付的依据ID：** `CDC-X1`, `CDC-X2`, `CDC-X3`；选段/上下文/官方定位见文末依据索引。

### H-BL-CDC-01-A01

最终有效调用：4；响应UTF-8 SHA256：`12c293fa063f1b13a927930ad8ee6a8f839cae46fc32357c32a1bba242eb37ba`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "清水达到翻滚沸腾后，通常应持续1分钟。海拔严格高于6500英尺时，改用3分钟。题设7000英尺且水已翻滚沸腾，因此采用3分钟。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明翻滚沸腾后的通常计时规则及海拔例外条件和时长。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-ae03e4706e519657b27296be9795a93209ba34fad697089022ff72a7e043eaf0",
    "u-8a5d61dd9bc423957a7605248c3ffa9c7d9c1e22c85cad35228b6df5aa9874b8"
  ],
  "rationale": "第一个单元给出通常1分钟规则，第二个单元给出严格高于6500英尺时改为3分钟的例外条件与时长，两项共同覆盖要求。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-ae03e4706e519657b27296be9795a93209ba34fad697089022ff72a7e043eaf0",
    "text": "清水达到翻滚沸腾后，通常应持续1分钟。",
    "start": 0,
    "end": 19
  },
  {
    "unit_id": "u-8a5d61dd9bc423957a7605248c3ffa9c7d9c1e22c85cad35228b6df5aa9874b8",
    "text": "海拔严格高于6500英尺时，改用3分钟。",
    "start": 19,
    "end": 39
  }
]
```

**R2** — 要求：把计时规则应用到题设7000英尺且已翻滚沸腾的情形。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-9357c0e88ad5c1acd43d55ed86842eedaf4fb643a701fbbb92ab167e35fde106"
  ],
  "rationale": "该单元明确将7000英尺且已翻滚沸腾的题设情形与3分钟时长联系起来，完成了规则应用。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-9357c0e88ad5c1acd43d55ed86842eedaf4fb643a701fbbb92ab167e35fde106",
    "text": "题设7000英尺且水已翻滚沸腾，因此采用3分钟。",
    "start": 39,
    "end": 63
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "清水达到翻滚沸腾后，通常应持续1分钟。",
  "start": 0,
  "end": 19,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X2"
  ],
  "rationale": "只叙述通常计时。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-ae03e4706e519657b27296be9795a93209ba34fad697089022ff72a7e043eaf0",
  "rationale": "该单元陈述清水翻滚沸腾后通常持续1分钟，是计时规则的一般部分，无额外边界扩展。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "清水达到翻滚沸腾后通常应持续煮沸1分钟。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "CDC-X2"
  ],
  "rationale": "CDC-X2明确写明“Bring clear water to a rolling boil for 1 minute”，与本单元通常时长一致。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "海拔严格高于6500英尺时，改用3分钟。",
  "start": 19,
  "end": 39,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X2"
  ],
  "rationale": "above的严格方向与例外时长。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-8a5d61dd9bc423957a7605248c3ffa9c7d9c1e22c85cad35228b6df5aa9874b8",
  "rationale": "该单元陈述海拔例外：严格高于6500英尺时改用3分钟，对应规则中的海拔条件与时长。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "海拔严格高于6500英尺时，翻滚沸腾后的煮沸时间改为3分钟。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "CDC-X2"
  ],
  "rationale": "CDC-X2括号内写明“at elevations above 6,500 feet, boil for 3 minutes”，支持该海拔例外规则。"
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "题设7000英尺且水已翻滚沸腾，因此采用3分钟。",
  "start": 39,
  "end": 63,
  "expected_support": "supported",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-5b7fd7111a5fb98822915b809315650891d7305ff50e11cd90b7f64c72552fa7",
    "CDC-X2"
  ],
  "rationale": "假定与规则联合应用，不认证水安全。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-9357c0e88ad5c1acd43d55ed86842eedaf4fb643a701fbbb92ab167e35fde106",
  "rationale": "该单元将题设条件（7000英尺、已翻滚沸腾）与3分钟时长结合，是该假定情形的结论。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "在题设海拔7000英尺且水已达到翻滚沸腾的假定情形下，应采用3分钟煮沸时长。",
  "claim_type": "scenario_application",
  "support": "supported",
  "basis_ids": [
    "p-5b7fd7111a5fb98822915b809315650891d7305ff50e11cd90b7f64c72552fa7",
    "CDC-X2"
  ],
  "rationale": "题设给出7000英尺且水已翻滚沸腾（高于6500英尺），CDC-X2规定高于6500英尺时煮沸3分钟，故应用该规则得出3分钟。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "答案完整给出通常1分钟规则与高于6500英尺改用3分钟的例外，并将题设7000英尺情形正确应用为3分钟，未涉及准备、冷却或储存等额外步骤。"
}
```

### H-BL-CDC-01-A02

最终有效调用：12；响应UTF-8 SHA256：`0a981e2494fe752f5791bad6c53dc5790bac6e3cfd4a71e3c2430f386fd568e7`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "清水达到翻滚沸腾后通常持续1分钟。题设7000英尺的清水应从已翻滚沸腾时起持续3分钟。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明翻滚沸腾后的通常计时规则及海拔例外条件和时长。

参考覆盖：`partially_covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-21d24156ecbc80fcce8220d3115d865dc194eb0a1d40af026261f23181379cf9",
    "u-18d094f06448eb81ae4826271d89e281a589a1a07a66e2614030076a3cb19d12"
  ],
  "rationale": "The answer states the usual 1-minute rolling-boil duration and the high-altitude 3-minute duration for the 7000 ft case, implicitly addressing the elevation exception condition and duration."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-21d24156ecbc80fcce8220d3115d865dc194eb0a1d40af026261f23181379cf9",
    "text": "清水达到翻滚沸腾后通常持续1分钟。",
    "start": 0,
    "end": 17
  },
  {
    "unit_id": "u-18d094f06448eb81ae4826271d89e281a589a1a07a66e2614030076a3cb19d12",
    "text": "题设7000英尺的清水应从已翻滚沸腾时起持续3分钟。",
    "start": 17,
    "end": 43
  }
]
```

**R2** — 要求：把计时规则应用到题设7000英尺且已翻滚沸腾的情形。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-18d094f06448eb81ae4826271d89e281a589a1a07a66e2614030076a3cb19d12"
  ],
  "rationale": "The second unit applies the timing rule to the stipulated 7000 ft clear water already at rolling boil and concludes 3 minutes."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-18d094f06448eb81ae4826271d89e281a589a1a07a66e2614030076a3cb19d12",
    "text": "题设7000英尺的清水应从已翻滚沸腾时起持续3分钟。",
    "start": 17,
    "end": 43
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "清水达到翻滚沸腾后通常持续1分钟。",
  "start": 0,
  "end": 17,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X2"
  ],
  "rationale": "通常规则完整但未给通用海拔例外阈值。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-21d24156ecbc80fcce8220d3115d865dc194eb0a1d40af026261f23181379cf9",
  "rationale": "States the general timing rule of 1 minute after rolling boil for clear water, without separately spelling out the elevation threshold, though the exception duration appears in the next unit."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Clear water should be boiled for 1 minute after reaching a rolling boil under usual conditions.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "CDC-X2"
  ],
  "rationale": "CDC-X2 states to bring clear water to a rolling boil for 1 minute, with the 3-minute exception at elevations above 6,500 feet."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "题设7000英尺的清水应从已翻滚沸腾时起持续3分钟。",
  "start": 17,
  "end": 43,
  "expected_support": "supported",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-5b7fd7111a5fb98822915b809315650891d7305ff50e11cd90b7f64c72552fa7",
    "CDC-X2"
  ],
  "rationale": "应用正确，3分钟已出现但不能由此补造6500阈值。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-18d094f06448eb81ae4826271d89e281a589a1a07a66e2614030076a3cb19d12",
  "rationale": "Applies the timing rule to the hypothetical 7000 ft clear-water case and states 3 minutes from rolling boil."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "For the hypothetical clear water at 7000 ft that has reached a rolling boil, the boiling should last 3 minutes from that point.",
  "claim_type": "scenario_application",
  "support": "supported",
  "basis_ids": [
    "p-5b7fd7111a5fb98822915b809315650891d7305ff50e11cd90b7f64c72552fa7",
    "CDC-X2"
  ],
  "rationale": "The premise stipulates 7000 ft (above 6,500 feet) and rolling boil; CDC-X2's rule requires 3 minutes at elevations above 6,500 feet, so the application is supported."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "The answer covers both the general 1-minute rule and the 3-minute high-elevation application to the stipulated 7000 ft clear water; it correctly relies on the CDC boiling-time rule."
}
```

### H-BL-CDC-01-A03

最终有效调用：21；响应UTF-8 SHA256：`dc46d434e78dda24e0e2be86684e0029569d8b572e79c9eb557cdc0baf9d102a`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "清水翻滚沸腾后通常持续1分钟。只有海拔低于6500英尺才改用3分钟。题设7000英尺不触发这一例外，因此只需1分钟。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明翻滚沸腾后的通常计时规则及海拔例外条件和时长。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-3b057fdecacec5b8677fb6cb7afe2bede1dc6588619138f8340afabd76bb01de",
    "u-227315740b248e2c8cdc3033602e0c9fc580ca17287bc7bfb2632a5f223cc000"
  ],
  "rationale": "第一句给出通常1分钟规则，第二句给出海拔例外条件（低于6500英尺时3分钟）；两者共同涵盖通常计时规则及海拔例外的条件和时长。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-3b057fdecacec5b8677fb6cb7afe2bede1dc6588619138f8340afabd76bb01de",
    "text": "清水翻滚沸腾后通常持续1分钟。",
    "start": 0,
    "end": 15
  },
  {
    "unit_id": "u-227315740b248e2c8cdc3033602e0c9fc580ca17287bc7bfb2632a5f223cc000",
    "text": "只有海拔低于6500英尺才改用3分钟。",
    "start": 15,
    "end": 34
  }
]
```

**R2** — 要求：把计时规则应用到题设7000英尺且已翻滚沸腾的情形。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-b0e08cf3456531072e7607fc6ca52bfbcf88ff16c5377a78fcc19d3b690b1ca3",
    "u-3b057fdecacec5b8677fb6cb7afe2bede1dc6588619138f8340afabd76bb01de"
  ],
  "rationale": "第三句把7000英尺题设判定为不触发例外并得出1分钟，第二句给出例外门槛；但“低于6500英尺”的表述方向与CDC“高于6500英尺”要求相反，属正确性缺陷而非覆盖缺失。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-b0e08cf3456531072e7607fc6ca52bfbcf88ff16c5377a78fcc19d3b690b1ca3",
    "text": "题设7000英尺不触发这一例外，因此只需1分钟。",
    "start": 34,
    "end": 58
  },
  {
    "unit_id": "u-3b057fdecacec5b8677fb6cb7afe2bede1dc6588619138f8340afabd76bb01de",
    "text": "清水翻滚沸腾后通常持续1分钟。",
    "start": 0,
    "end": 15
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "清水翻滚沸腾后通常持续1分钟。",
  "start": 0,
  "end": 15,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X2"
  ],
  "rationale": "正常规则有据。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-3b057fdecacec5b8677fb6cb7afe2bede1dc6588619138f8340afabd76bb01de",
  "rationale": "该单元陈述清水达到翻滚沸腾后的通常煮沸时长为1分钟，作为一般计时规则陈述；未涉及其它步骤或现场安全判断。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "清水达到翻滚沸腾后通常应持续煮沸1分钟。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "CDC-X2"
  ],
  "rationale": "CDC-X2明确写“Bring clear water to a rolling boil for 1 minute”，与本单元通常时长陈述一致。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "只有海拔低于6500英尺才改用3分钟。",
  "start": 15,
  "end": 34,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X2"
  ],
  "rationale": "方向说反且only排除实际above条件；不是没提条件。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-227315740b248e2c8cdc3033602e0c9fc580ca17287bc7bfb2632a5f223cc000",
  "rationale": "该单元试图陈述海拔例外条件和时长，但把触发方向写反：声称只有海拔低于6500英尺才改用3分钟。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "只有海拔低于6500英尺时才改用3分钟煮沸时间。",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "CDC-X2"
  ],
  "rationale": "CDC-X2说明海拔高于6,500英尺时煮沸3分钟，方向与“低于”相反；虽3分钟时长正确，但例外条件被颠倒。"
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "题设7000英尺不触发这一例外，因此只需1分钟。",
  "start": 34,
  "end": 58,
  "expected_support": "contradicted",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-5b7fd7111a5fb98822915b809315650891d7305ff50e11cd90b7f64c72552fa7",
    "CDC-X2"
  ],
  "rationale": "明确映射题设但结果与above情形3分钟相反。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-b0e08cf3456531072e7607fc6ca52bfbcf88ff16c5377a78fcc19d3b690b1ca3",
  "rationale": "该单元把题设7000英尺应用于其（错误表述的）例外规则，并得出只需1分钟；这是对假设计时规则的场景应用。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "题设海拔7000英尺不触发（低于6500英尺的）3分钟例外，因此应采用1分钟。",
  "claim_type": "scenario_application",
  "support": "contradicted",
  "basis_ids": [
    "p-5b7fd7111a5fb98822915b809315650891d7305ff50e11cd90b7f64c72552fa7",
    "CDC-X2"
  ],
  "rationale": "题设确实为7000英尺且已翻滚沸腾；但CDC-X2要求海拔高于6,500英尺时煮沸3分钟，故7000英尺应触发3分钟例外，而非1分钟。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "答案覆盖了通常规则与海拔例外两个要求方面，也把规则应用于题设场景；但海拔例外方向写反（应为高于而非低于6500英尺），导致7000英尺情形下得出的1分钟结论与CDC规则相反。"
}
```

## H-BL-NWS-02

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "根据给定NWS页面，说明什么条件下预报可以省略天空状况，以及原文对省略的许可强度。仅作假定：某份预报预计的降水概率为60%。将本页规则应用到这一假定，说明该条件是否达到、是否允许省略，以及是否必须省略。无需解释天气实况。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "说明省略天空状况的概率条件及许可强度。"
    },
    {
      "requirement_id": "R2",
      "description": "把规则应用到给定60%假定，说明条件是否达到、能否省略及是否必须省略。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": [
    {
      "premise_id": "p-ad7e6ff8cd5a353f85d0fbae8819462cdbd6a6b5549e501e8692794efb95aabb",
      "text": "某份预报预计的降水概率为60%。",
      "start": 46,
      "end": 62,
      "origin": "question",
      "status": "assumed_for_this_question_only",
      "site_verified": false
    }
  ]
}
```

**完整交付的依据ID：** `NWS-X1`, `NWS-X2`；选段/上下文/官方定位见文末依据索引。

### H-BL-NWS-02-A01

最终有效调用：5；响应UTF-8 SHA256：`c88ede3a207132b16f09ac07da8d5991a76d33e6138c580bb81521cec344684e`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "预期降水概率达到60%或更高时，可以不写天空状况，但并非必须省略。题设的60%恰好达到该条件，所以允许省略，仍不要求一定省略。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明省略天空状况的概率条件及许可强度。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-9801c0139fc8487e589e32c05f635129d55d9689b9e65e87eb32f5a970da3c40"
  ],
  "rationale": "首句明确给出条件（预期降水概率达到60%或更高）和许可强度（可以不写但并非必须省略），覆盖了条件与许可强度两个方面。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-9801c0139fc8487e589e32c05f635129d55d9689b9e65e87eb32f5a970da3c40",
    "text": "预期降水概率达到60%或更高时，可以不写天空状况，但并非必须省略。",
    "start": 0,
    "end": 33
  }
]
```

**R2** — 要求：把规则应用到给定60%假定，说明条件是否达到、能否省略及是否必须省略。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-d6913768b41e391b82ae5e2ec58369917cfd64b29a179fb5e4170b073fe9e8ed"
  ],
  "rationale": "第二句把60%假定代入规则，说明恰好达到条件、允许省略且仍不要求一定省略，覆盖了条件达成、可否省略和是否必须省略三点。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-d6913768b41e391b82ae5e2ec58369917cfd64b29a179fb5e4170b073fe9e8ed",
    "text": "题设的60%恰好达到该条件，所以允许省略，仍不要求一定省略。",
    "start": 33,
    "end": 63
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "预期降水概率达到60%或更高时，可以不写天空状况，但并非必须省略。",
  "start": 0,
  "end": 33,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X2"
  ],
  "rationale": "阈值含等号，may保留许可而非强制。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-9801c0139fc8487e589e32c05f635129d55d9689b9e65e87eb32f5a970da3c40",
  "rationale": "该单元陈述省略天空状况的概率阈值及'可以但不强制'的许可强度，属于对NWS规则的一般性说明。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "当预期降水概率达到60%或更高时，天空状况可以被省略，但并非必须省略。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X2"
  ],
  "rationale": "NWS-X2原文规定降水概率60%或以上时天空状况'may be omitted'，即许可而非强制，与命题一致。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "题设的60%恰好达到该条件，所以允许省略，仍不要求一定省略。",
  "start": 33,
  "end": 63,
  "expected_support": "supported",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-ad7e6ff8cd5a353f85d0fbae8819462cdbd6a6b5549e501e8692794efb95aabb",
    "NWS-X2"
  ],
  "rationale": "题设与文献阈值联合应用。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-d6913768b41e391b82ae5e2ec58369917cfd64b29a179fb5e4170b073fe9e8ed",
  "rationale": "该单元将阈值规则应用于60%假定，判断条件达成、允许省略且不强制省略。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "假定预报的降水概率为60%，恰好达到60%或更高的阈值，因此允许省略天空状况，但仍不要求一定省略。",
  "claim_type": "scenario_application",
  "support": "supported",
  "basis_ids": [
    "p-ad7e6ff8cd5a353f85d0fbae8819462cdbd6a6b5549e501e8692794efb95aabb",
    "NWS-X2"
  ],
  "rationale": "假定给出60%，恰好满足NWS-X2的'60% or greater'条件；原文用'may be omitted'，故允许而非强制，命题正确。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "答案完整覆盖两项要求：首句给出规则条件与许可强度，第二句将其应用于60%假定并说明达到条件、允许省略而不强制省略，均有文献与原假定支持。"
}
```

### H-BL-NWS-02-A02

最终有效调用：13；响应UTF-8 SHA256：`07b701d98f6dd24ec4f1e4f84adcfe96e07d839fca56ea1cb63615ddc36e2c6d`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "降水概率达到60%及以上时，规则允许省略天空状况，并非强制。该页还要求每份此类预报保留五年。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明省略天空状况的概率条件及许可强度。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-0dcb4dce0384ea3e0f45ffa294fb71f4549c8de3b7f4255a1d533621c734e890"
  ],
  "rationale": "The unit states the probability condition (60% or greater) and the permission strength (may omit, not mandatory), addressing both the condition and the permission strength requested."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-0dcb4dce0384ea3e0f45ffa294fb71f4549c8de3b7f4255a1d533621c734e890",
    "text": "降水概率达到60%及以上时，规则允许省略天空状况，并非强制。",
    "start": 0,
    "end": 30
  }
]
```

**R2** — 要求：把规则应用到给定60%假定，说明条件是否达到、能否省略及是否必须省略。

参考覆盖：`missing`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-0dcb4dce0384ea3e0f45ffa294fb71f4549c8de3b7f4255a1d533621c734e890"
  ],
  "rationale": "The unit applies the 60% threshold generally and clarifies that omission is allowed but not required; for a forecast at exactly 60%, this states the condition is met and that omission is permitted rather than mandatory, thus addressing whether the condition is reached, whether omission is allowed, and whether it is required."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-0dcb4dce0384ea3e0f45ffa294fb71f4549c8de3b7f4255a1d533621c734e890",
    "text": "降水概率达到60%及以上时，规则允许省略天空状况，并非强制。",
    "start": 0,
    "end": 30
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "降水概率达到60%及以上时，规则允许省略天空状况，并非强制。",
  "start": 0,
  "end": 30,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X2"
  ],
  "rationale": "通用规则正确，尚未映射具体题设。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-0dcb4dce0384ea3e0f45ffa294fb71f4549c8de3b7f4255a1d533621c734e890",
  "rationale": "The unit asserts that when precipitation probability reaches 60% or above, the rule permits omitting sky condition and does not mandate it, covering both the threshold condition and permission strength."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "When the probability of precipitation is 60% or greater, the sky condition may be omitted.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X2"
  ],
  "rationale": "NWS-X2 states that if a high probability of precipitation (60% or greater) is expected, then the sky condition may be omitted since it is inferred from the precipitation forecast, which directly supports the permissive rule."
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Omitting the sky condition at 60% or greater precipitation probability is not mandatory.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "NWS-X2"
  ],
  "rationale": "NWS-X2 uses the permissive 'may be omitted,' not a mandatory requirement, so the claim that omission is not mandatory is supported by the same literature statement."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "该页还要求每份此类预报保留五年。",
  "start": 30,
  "end": 46,
  "expected_support": "insufficient_evidence",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X2"
  ],
  "rationale": "选段没有档案保存期限；缺依据不判矛盾。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-9fd91156e2c28ffc51d9da0f16e1d780207d55f8616759d48a2c2828da26fe56",
  "rationale": "The unit asserts that the page additionally requires each such forecast to be retained for five years; no supplied evidence mentions any retention period, so this is an unsupported extra assertion."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "The page requires that each such forecast be retained for five years.",
  "claim_type": "external_claim",
  "support": "insufficient_evidence",
  "basis_ids": [],
  "rationale": "None of the supplied literature evidence (NWS-X1, NWS-X2) mentions any retention requirement or five-year period, and no actual record is supplied; therefore this assertion about the page's content cannot be verified."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "R1 and R2 are addressed by the first unit, which states the 60%-or-greater threshold and the permissive ('may,' not 'must') omission. The second unit adds an unsupported retention claim not found in the supplied evidence; this extra does not undermine the addressed requirements but cannot be verified."
}
```

### H-BL-NWS-02-A03

最终有效调用：22；响应UTF-8 SHA256：`8a9263b47c7d31627ce04c015ea7f6f784851e504a50128acc2b2a402f7a48d1`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "降水概率为60%及以上时，规则要求必须省略天空状况。题设预报的60%达到该条件，因此必须省略，不可保留天空状况。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明省略天空状况的概率条件及许可强度。

参考覆盖：`covered`；模型覆盖：`partially_covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "partially_covered",
  "unit_ids": [
    "u-360eeee269bdc7d74e82c65ec00dd94edc8153810f4759ecc4afbc3c82a46bb2"
  ],
  "rationale": "Answer states the 60%+ probability condition but characterizes the permission as a mandatory requirement ('规则要求必须省略'), which misstates the original permissive strength ('may be omitted'); the condition is addressed but the permission-modality aspect is not accurately addressed."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-360eeee269bdc7d74e82c65ec00dd94edc8153810f4759ecc4afbc3c82a46bb2",
    "text": "降水概率为60%及以上时，规则要求必须省略天空状况。",
    "start": 0,
    "end": 26
  }
]
```

**R2** — 要求：把规则应用到给定60%假定，说明条件是否达到、能否省略及是否必须省略。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-b7597c5fdef4a1693928f933850a3ce96f9432472390ca856126aa36d7ca9e97"
  ],
  "rationale": "Answer applies the rule to the assumed 60% case, stating the threshold is met and concluding sky condition must be omitted and cannot be retained, addressing condition-met and can/cannot/should-omit aspects (though the 'must' strength is wrong versus 'may')."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-b7597c5fdef4a1693928f933850a3ce96f9432472390ca856126aa36d7ca9e97",
    "text": "题设预报的60%达到该条件，因此必须省略，不可保留天空状况。",
    "start": 26,
    "end": 56
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "降水概率为60%及以上时，规则要求必须省略天空状况。",
  "start": 0,
  "end": 26,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NWS-X2"
  ],
  "rationale": "把may许可改成强制义务。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-360eeee269bdc7d74e82c65ec00dd94edc8153810f4759ecc4afbc3c82a46bb2",
  "rationale": "Single assertion combining the 60%+ trigger with a claim that the rule requires mandatory omission of sky condition."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "When precipitation probability is 60% or greater, the rule requires that sky condition must be omitted.",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "NWS-X2"
  ],
  "rationale": "NWS-X2 states that if 60%+ POP is expected the sky condition MAY be omitted since it is inferred; it is permissive, not mandatory. The answer's 'must omit' reverses the modality direction, so the literature statement is contradicted by scope."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "题设预报的60%达到该条件，因此必须省略，不可保留天空状况。",
  "start": 26,
  "end": 56,
  "expected_support": "contradicted",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-ad7e6ff8cd5a353f85d0fbae8819462cdbd6a6b5549e501e8692794efb95aabb",
    "NWS-X2"
  ],
  "rationale": "承认60%匹配，但推成必须且不可保留，违反许可边界。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-b7597c5fdef4a1693928f933850a3ce96f9432472390ca856126aa36d7ca9e97",
  "rationale": "Applies the rule to the stipulated 60% forecast, claiming the threshold is met and that omission is mandatory and retention not allowed."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "The assumed forecast's 60% reaches the 60%-or-greater condition, so sky condition must be omitted and cannot be retained.",
  "claim_type": "scenario_application",
  "support": "insufficient_evidence",
  "basis_ids": [
    "p-ad7e6ff8cd5a353f85d0fbae8819462cdbd6a6b5549e501e8692794efb95aabb",
    "NWS-X2"
  ],
  "rationale": "The premise establishes 60% POP, and NWS-X2 would support that omission is permitted; however the answer asserts mandatory omission and prohibition of retention, which NWS-X2 does not support (it says 'may be omitted'). The threshold-meeting part is supported, but the mandatory/not-allowed conclusion is unsupported, so overall insufficient_evidence."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "R1 is partially covered because the 60%+ condition is stated but the permissive strength is mischaracterized; R2 is covered for condition-met and omission decision but carries the same 'must' error. The answer's core error is turning the literature's permissive 'may be omitted' into a mandatory requirement."
}
```

## H-BL-USGS-02

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "根据给定USGS资料，说明这里如何界定洪水；列举文中的两种可能成因，并说明它们是否必须在每场洪水中共同出现；再说明不同洪水在量级、持续时间和影响上是否必然相同。不分析任何真实地区事件。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "说明资料对洪水的流量与河岸关系的界定。"
    },
    {
      "requirement_id": "R2",
      "description": "列举两种资料中的可能成因，并说明是否必须共同出现。"
    },
    {
      "requirement_id": "R3",
      "description": "说明不同洪水的量级、持续时间和影响是否必然相同。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": []
}
```

**完整交付的依据ID：** `USGS-X1`, `USGS-X2`, `USGS-X3`；选段/上下文/官方定位见文末依据索引。

### H-BL-USGS-02-A01

最终有效调用：6；响应UTF-8 SHA256：`3829e0d9b45d78c29faa17f98350c312d4afdf903545249a45ecc65f7d4b8bc4`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "这里洪水指相对较高的河流流量漫过一段河道的自然或人工河岸。持续性大范围降雨和局地强雷暴降雨都是可能成因，不要求二者共同发生。不同洪水的量级、持续时间和影响不必相同。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明资料对洪水的流量与河岸关系的界定。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-12ca1175ba79c3f485c4b63b787b37d97915417fb39fce72070347b299e45264"
  ],
  "rationale": "The unit explicitly defines flood as relatively high streamflow overtopping natural or artificial banks of a stream reach, addressing the requested flow-bank relationship."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-12ca1175ba79c3f485c4b63b787b37d97915417fb39fce72070347b299e45264",
    "text": "这里洪水指相对较高的河流流量漫过一段河道的自然或人工河岸。",
    "start": 0,
    "end": 29
  }
]
```

**R2** — 要求：列举两种资料中的可能成因，并说明是否必须共同出现。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-473bd0f941dda08641b391e6bfc2305885a3c8a398917d439af69503b4d231d4"
  ],
  "rationale": "The unit lists long-lasting broad-area rainfall and locally intense thunderstorm rainfall as possible causes and states they are not required to co-occur."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-473bd0f941dda08641b391e6bfc2305885a3c8a398917d439af69503b4d231d4",
    "text": "持续性大范围降雨和局地强雷暴降雨都是可能成因，不要求二者共同发生。",
    "start": 29,
    "end": 62
  }
]
```

**R3** — 要求：说明不同洪水的量级、持续时间和影响是否必然相同。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R3",
  "coverage": "covered",
  "unit_ids": [
    "u-a9a8be3f01ec62c0f8b3bed1fded88dbba16475df1ad848a0babc8ebf23f48a5"
  ],
  "rationale": "The unit explicitly states different floods need not have the same magnitude, duration, or effect, addressing all three named aspects."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-a9a8be3f01ec62c0f8b3bed1fded88dbba16475df1ad848a0babc8ebf23f48a5",
    "text": "不同洪水的量级、持续时间和影响不必相同。",
    "start": 62,
    "end": 82
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "这里洪水指相对较高的河流流量漫过一段河道的自然或人工河岸。",
  "start": 0,
  "end": 29,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "定义的流量与漫岸关系。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-12ca1175ba79c3f485c4b63b787b37d97915417fb39fce72070347b299e45264",
  "rationale": "The unit is a definitional statement about what 'flood' means here, asserting relatively high streamflow overtopping natural or artificial banks in any stream reach."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "A flood is defined as any relatively high streamflow overtopping the natural or artificial banks in any reach of a stream.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2 states exactly this definition of flood within its scope context, so the paraphrase is supported as a literature restatement."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "持续性大范围降雨和局地强雷暴降雨都是可能成因，不要求二者共同发生。",
  "start": 29,
  "end": 62,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "两种例示原因及备选关系。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-473bd0f941dda08641b391e6bfc2305885a3c8a398917d439af69503b4d231d4",
  "rationale": "The unit names two possible causes (persistent broad-area rainfall and locally intense thunderstorm rainfall) and negates any requirement that both occur together in every flood."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Long-lasting rainfall over a broad area and locally intense thunderstorm-generated rainfall are both possible causes of floods, and they need not co-occur.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2 lists both long-lasting broad-area rainfall and locally intense thunderstorm-generated rainfall among 'many reasons' floods occur, implying neither is required alongside the other; the co-occurrence negation is a reasonable reading of 'many reasons, such as'."
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "不同洪水的量级、持续时间和影响不必相同。",
  "start": 62,
  "end": 82,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "三个维度的差异均保留。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-a9a8be3f01ec62c0f8b3bed1fded88dbba16475df1ad848a0babc8ebf23f48a5",
  "rationale": "The unit asserts that different floods need not be equal in magnitude, duration, or effect, matching all three requested dimensions."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Not all floods are equal in magnitude, duration, or effect.",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2 states 'not all floods are equal in magnitude, duration, or effect,' which directly supports the paraphrase."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "The answer defines flood via streamflow overtopping banks, lists two possible causes without requiring co-occurrence, and denies that all floods share magnitude/duration/effect, matching all three requirements. Each unit is a literature restatement supported by USGS-X2; no site-specific claims are made."
}
```

### H-BL-USGS-02-A02

最终有效调用：14；响应UTF-8 SHA256：`6f0ec3379c6b64ddebe6c00f181825a29487864088eb57c6bc67944d2b547b4e`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "洪水是相对较高的河流流量漫过自然或人工河岸。可列举的一个原因是大范围长时间降雨，但不要求所有例示原因在每场洪水中同时发生。不同洪水在量级、持续时间和影响上不必相同。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明资料对洪水的流量与河岸关系的界定。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-e8e0254eaab4b99178a60cd2141eb13aec83f1f2bbfda4d440969ffedc22c7f7"
  ],
  "rationale": "单位明确给出洪水为相对较高的河流流量漫过自然或人工河岸，涵盖了对洪水界定中流量与河岸关系的说明。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-e8e0254eaab4b99178a60cd2141eb13aec83f1f2bbfda4d440969ffedc22c7f7",
    "text": "洪水是相对较高的河流流量漫过自然或人工河岸。",
    "start": 0,
    "end": 22
  }
]
```

**R2** — 要求：列举两种资料中的可能成因，并说明是否必须共同出现。

参考覆盖：`partially_covered`；模型覆盖：`partially_covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "partially_covered",
  "unit_ids": [
    "u-a425690ce80911a8b6accace7465a23ddc84fde17bd60b2d794bd82226cddde9"
  ],
  "rationale": "单位只列举了一种成因（大范围长时间降雨），并说明所有例示原因不必同时发生，但未按资料列举第二种成因（如局地强雷暴降雨或融雪），缺少第二成因这一必需内容。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-a425690ce80911a8b6accace7465a23ddc84fde17bd60b2d794bd82226cddde9",
    "text": "可列举的一个原因是大范围长时间降雨，但不要求所有例示原因在每场洪水中同时发生。",
    "start": 22,
    "end": 61
  }
]
```

**R3** — 要求：说明不同洪水的量级、持续时间和影响是否必然相同。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R3",
  "coverage": "covered",
  "unit_ids": [
    "u-e32f8f9f61aaeec0cc9ad2b9bc1119dd9bb2315d3cc3134148091c19846289da"
  ],
  "rationale": "单位明确说明不同洪水在量级、持续时间和影响上不必相同，回应了是否必然相同的问题。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-e32f8f9f61aaeec0cc9ad2b9bc1119dd9bb2315d3cc3134148091c19846289da",
    "text": "不同洪水在量级、持续时间和影响上不必相同。",
    "start": 61,
    "end": 82
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "洪水是相对较高的河流流量漫过自然或人工河岸。",
  "start": 0,
  "end": 22,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "定义完整。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-e8e0254eaab4b99178a60cd2141eb13aec83f1f2bbfda4d440969ffedc22c7f7",
  "rationale": "该单位定义洪水，断言是相对较高的河流流量漫过自然或人工河岸，属于对文献定义的转述。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "洪水是相对较高的河流流量漫过自然或人工河岸。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2 明确将洪水定义为 any relatively high streamflow overtopping the natural or artificial banks，与命题一致。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "可列举的一个原因是大范围长时间降雨，但不要求所有例示原因在每场洪水中同时发生。",
  "start": 22,
  "end": 61,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "一个原因和非共同必要关系都有据，缺第二原因是覆盖缺口。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-a425690ce80911a8b6accace7465a23ddc84fde17bd60b2d794bd82226cddde9",
  "rationale": "该单位列举大范围长时间降雨作为成因之一，并加上不要求所有例示原因同时发生的限定；未列举第二种成因。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "大范围长时间降雨是可列举的洪水成因之一。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2 列举了 long-lasting rainfall over a broad area 作为洪水成因，支持这一成因。"
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "所有例示原因不要求在每场洪水中同时发生。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2 说明洪水成因众多（如列举的几类），并非要求全部同时出现，因此这一限定与资料一致。"
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "不同洪水在量级、持续时间和影响上不必相同。",
  "start": 61,
  "end": 82,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "R3独立完整，不因R2遗漏受罚。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-e32f8f9f61aaeec0cc9ad2b9bc1119dd9bb2315d3cc3134148091c19846289da",
  "rationale": "该单位断言不同洪水在量级、持续时间和影响上不必相同，对应文献关于不同洪水并不相等的陈述。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "不同洪水在量级、持续时间和影响上不必相同。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2 指出 not all floods are equal in magnitude, duration, or effect，支持该否定必然相同的命题。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "R1 与 R3 已被完整回应；R2 仅列举一种成因且未列出第二种，故为部分覆盖。各单位判断均基于 USGS-X2 的定义与成因陈述，无场景前提或真实地区事件需要核实。"
}
```

### H-BL-USGS-02-A03

最终有效调用：23；响应UTF-8 SHA256：`fcbfba4bc254622906cbcf8f66cd2fc8450a7753202ee8f6a7e893d25021d00b`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "洪水是较高河流流量漫过自然或人工河岸。大范围长时间降雨与大积雪快速融化必须在每场洪水中共同出现，缺一不可。所有洪水的量级、持续时间和影响都必然完全相同。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明资料对洪水的流量与河岸关系的界定。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-0788ebc61d8614338b56612a94de90d67ff594d45a66de592544f94eae775a39"
  ],
  "rationale": "首句明确界定洪水为较高河流流量漫过自然或人工河岸，涵盖流量与河岸关系。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-0788ebc61d8614338b56612a94de90d67ff594d45a66de592544f94eae775a39",
    "text": "洪水是较高河流流量漫过自然或人工河岸。",
    "start": 0,
    "end": 19
  }
]
```

**R2** — 要求：列举两种资料中的可能成因，并说明是否必须共同出现。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-166de8020f7ce902ae5317f34512a039928fcc68c48950b626ec0fd8454b8b99"
  ],
  "rationale": "列举了大范围长时间降雨与大积雪快速融化两种成因，并明确断言二者必须在每场洪水中共同出现、缺一不可。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-166de8020f7ce902ae5317f34512a039928fcc68c48950b626ec0fd8454b8b99",
    "text": "大范围长时间降雨与大积雪快速融化必须在每场洪水中共同出现，缺一不可。",
    "start": 19,
    "end": 53
  }
]
```

**R3** — 要求：说明不同洪水的量级、持续时间和影响是否必然相同。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R3",
  "coverage": "covered",
  "unit_ids": [
    "u-625ee8208ae719c6c4480778aca43543952c623d4ce07692487f18921d1570e1"
  ],
  "rationale": "明确说明所有洪水在量级、持续时间和影响上必然完全相同，覆盖了该方面（虽与资料相反）。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-625ee8208ae719c6c4480778aca43543952c623d4ce07692487f18921d1570e1",
    "text": "所有洪水的量级、持续时间和影响都必然完全相同。",
    "start": 53,
    "end": 76
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "洪水是较高河流流量漫过自然或人工河岸。",
  "start": 0,
  "end": 19,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "定义仍有据。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-0788ebc61d8614338b56612a94de90d67ff594d45a66de592544f94eae775a39",
  "rationale": "单句给出洪水定义，将较高河流流量漫过自然或人工河岸作为界定，与USGS-X2的界定一致。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "洪水是较高河流流量漫过自然或人工河岸。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2明确将洪水界定为任一河段上相对较高流量漫过自然或人工河岸，与该定义一致。"
}
```

**U2** — 未对齐：混合标签，全部拆分判断保留

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "大范围长时间降雨与大积雪快速融化必须在每场洪水中共同出现，缺一不可。",
  "start": 19,
  "end": 53,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "两种原因均已列出，但必须共同发生的断言与原文融雪可不伴降雨直接冲突。"
}
```

未对齐说明（原AI审阅摘要，非模型理由）：U2拆为两可能成因S＋必须共同发生C，混合标签，按事前规则无法对齐，不挑C子句。

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-166de8020f7ce902ae5317f34512a039928fcc68c48950b626ec0fd8454b8b99",
  "rationale": "该句断言两种特定成因（大范围长时间降雨与大积雪快速融化）必须在每场洪水中共同出现、缺一不可；前半列举成因对应资料，但“必须共同出现”与资料列出的多种独立原因相悖。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "大范围长时间降雨与大积雪快速融化是洪水的两种可能成因。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2列举长时大范围降雨与大雪堆快速融化（可伴随或不伴随降雨）等成因，支持这两种作为可能成因。"
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "大范围长时间降雨与大积雪快速融化必须在每场洪水中共同出现，缺一不可。",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2称洪水由许多不同情形造成，成因是“如”列举的多种之一，并非要求两种必须同时出现，故该必要性断言与资料相悖。"
}
```

**U3** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U3",
  "exact_text": "所有洪水的量级、持续时间和影响都必然完全相同。",
  "start": 53,
  "end": 76,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "USGS-X2"
  ],
  "rationale": "与not all floods are equal直接冲突。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-625ee8208ae719c6c4480778aca43543952c623d4ce07692487f18921d1570e1",
  "rationale": "该句断言所有洪水在量级、持续时间和影响上必然完全相同，直接与资料“并非所有洪水在量级、持续时间或影响上相同”的陈述相反。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "所有洪水的量级、持续时间和影响都必然完全相同。",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "USGS-X2"
  ],
  "rationale": "USGS-X2明确指出并非所有洪水在量级、持续时间或影响上相同，与该断言相反。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "三个要求均被原答案单元明确涉及；定义部分与USGS-X2一致，而“两种成因必须共同出现”和“所有洪水必然完全相同”与USGS-X2明确矛盾。"
}
```

## H-BL-NASA-02

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "仅作假定：卫星S处在地球同步轨道，该轨道为圆形且直接位于赤道上空。根据给定NASA文字，判断在这一假定下轨道可归为哪一类，并说明其相对于地面的运动及地表对应位置。不根据给定材料中的距离描述或same speed措辞作数值、任意位置或运动方向推导，也不评估真实卫星。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "将资料规则应用于题设的三项轨道前提，说明轨道类别。"
    },
    {
      "requirement_id": "R2",
      "description": "说明该假定轨道相对于地面的运动与地表对应位置。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": [
    {
      "premise_id": "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
      "text": "卫星S处在地球同步轨道，该轨道为圆形且直接位于赤道上空。",
      "start": 5,
      "end": 33,
      "origin": "question",
      "status": "assumed_for_this_question_only",
      "site_verified": false
    }
  ]
}
```

**完整交付的依据ID：** `NASA-X1`, `NASA-X2`, `NASA-X3`, `NASA-X4`；选段/上下文/官方定位见文末依据索引。

### H-BL-NASA-02-A01

最终有效调用：7；响应UTF-8 SHA256：`f6e03a1970a17f2a3e0f3c93ebb16f28efc8afeda0fcd85a57052d8737fd16f6`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "在题设的联合假定下，这属于地球静止轨道。在这一假定下，它相对地面不移动，始终在同一地表地点上方。"
}
```

#### 覆盖原文及理由

**R1** — 要求：将资料规则应用于题设的三项轨道前提，说明轨道类别。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-ef8f21a2ca73ef2cee29e2ee9ff1fd4e490317f2a7ae2edad5711434bb8e7b59"
  ],
  "rationale": "The unit explicitly classifies the orbit under the joint premises as geostationary (地球静止轨道), addressing the category requirement applied to the premise case."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-ef8f21a2ca73ef2cee29e2ee9ff1fd4e490317f2a7ae2edad5711434bb8e7b59",
    "text": "在题设的联合假定下，这属于地球静止轨道。",
    "start": 0,
    "end": 20
  }
]
```

**R2** — 要求：说明该假定轨道相对于地面的运动与地表对应位置。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-3b83a8f74e41fd6d0fa047c401ad4100cc0f09b0b0af9e8b62267c968fa2662e"
  ],
  "rationale": "The unit states that relative to the ground it does not move and stays above the same surface location, covering both the relative motion and the surface correspondence aspects."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-3b83a8f74e41fd6d0fa047c401ad4100cc0f09b0b0af9e8b62267c968fa2662e",
    "text": "在这一假定下，它相对地面不移动，始终在同一地表地点上方。",
    "start": 20,
    "end": 48
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "在题设的联合假定下，这属于地球静止轨道。",
  "start": 0,
  "end": 20,
  "expected_support": "supported",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "联合给定同步、圆形、赤道上空后应用文献。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-ef8f21a2ca73ef2cee29e2ee9ff1fd4e490317f2a7ae2edad5711434bb8e7b59",
  "rationale": "Single assertion applying the literature geostationary classification to the stipulated hypothetical case; no extra decomposition needed."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Under the joint premises (geosynchronous, circular, directly over the equator), the orbit is classified as geostationary (地球静止轨道).",
  "claim_type": "scenario_application",
  "support": "supported",
  "basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "The premise stipulates geosynchronous, circular, equatorial conditions, and NASA-X4 states such a circular geosynchronous orbit directly over the equator (eccentricity and inclination zero) is geostationary, so the application is supported without real-site verification."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "在这一假定下，它相对地面不移动，始终在同一地表地点上方。",
  "start": 20,
  "end": 48,
  "expected_support": "supported",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "只按假定描述相对运动，不推现场认证。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-3b83a8f74e41fd6d0fa047c401ad4100cc0f09b0b0af9e8b62267c968fa2662e",
  "rationale": "Single assertion stating relative ground motion and surface position under the premise case; directly maps the literature's geostationary description."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Under this premise, the satellite does not move relative to the ground and remains continuously above the same location on Earth's surface.",
  "claim_type": "scenario_application",
  "support": "supported",
  "basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "NASA-X4 states a geostationary orbit does not move at all relative to the ground and is always directly over the same place on Earth's surface, and the premise establishes the geostationary case, so the application is supported."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "Both answer units apply NASA-X4's rule to the stipulated hypothetical case, covering the classification and the relative-motion/surface-position aspects; no site verification or distance/speed derivation is claimed."
}
```

### H-BL-NASA-02-A02

最终有效调用：15；响应UTF-8 SHA256：`534f905b9379bf149af1656d48b0e22b3bee5db4179ef9282399766ba25a9cf8`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "在题设的联合假定下，它属于地球静止轨道。资料还保证这种轨道中的卫星至少工作20年。"
}
```

#### 覆盖原文及理由

**R1** — 要求：将资料规则应用于题设的三项轨道前提，说明轨道类别。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-8521079f9fb9e064ff18c984889ffff6428008e350ab9c2a70c233ebba8c42fa"
  ],
  "rationale": "The answer classifies the orbit under the stipulated premises as geostationary, applying the literature rule to the three orbital conditions."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-8521079f9fb9e064ff18c984889ffff6428008e350ab9c2a70c233ebba8c42fa",
    "text": "在题设的联合假定下，它属于地球静止轨道。",
    "start": 0,
    "end": 20
  }
]
```

**R2** — 要求：说明该假定轨道相对于地面的运动与地表对应位置。

参考覆盖：`missing`；模型覆盖：`missing`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "missing",
  "unit_ids": [],
  "rationale": "The answer does not state the satellite's motion relative to the ground nor its surface correspondence point."
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "在题设的联合假定下，它属于地球静止轨道。",
  "start": 0,
  "end": 20,
  "expected_support": "supported",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "类别有据。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-8521079f9fb9e064ff18c984889ffff6428008e350ab9c2a70c233ebba8c42fa",
  "rationale": "This unit classifies the hypothetical orbit as geostationary under the combined assumed premises; it does not discuss relative ground motion or surface location, which are separate requirements."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "Under the assumed premises (geosynchronous, circular, directly over the equator), the orbit is classified as geostationary.",
  "claim_type": "scenario_application",
  "support": "supported",
  "basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "NASA-X4 states that a circular geosynchronous orbit directly over the equator with zero eccentricity and inclination is geostationary; the premise supplies exactly those hypothetical properties, so the scenario application holds without any real satellite verification."
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "资料还保证这种轨道中的卫星至少工作20年。",
  "start": 20,
  "end": 41,
  "expected_support": "insufficient_evidence",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "NASA-X4"
  ],
  "rationale": "文献没有寿命保证；是对文献规则的无据解释，不是已命名真实卫星的现场核验。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-f7e35bff6112aaadddfd06a8c7f9866a806467266efcc80028274c64a3ba4111",
  "rationale": "This unit asserts that the material guarantees satellites in this orbit operate at least 20 years. It is an unsupported extra claim not present in the supplied NASA excerpts and not part of the stipulated premises."
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "The supplied material guarantees that satellites in this orbit operate for at least 20 years.",
  "claim_type": "external_claim",
  "support": "insufficient_evidence",
  "basis_ids": [],
  "rationale": "The supplied NASA excerpts concern eccentricity, inclination, geosynchronous and geostationary definitions; none mentions a 20-year operational lifetime, so this general claim is unsupported by the delivered literature and cannot be verified."
}
```

#### 模型总体理由原文

```json
{
  "rationale": "The answer correctly derives the geostationary classification from the hypothetical premises and NASA-X4, but omits the required relative motion and surface correspondence, and adds an unsupported 20-year lifetime guarantee absent from the literature."
}
```

### H-BL-NASA-02-A03

最终有效调用：24；响应UTF-8 SHA256：`6e408f96ce8414c75bca3fd1bff13588a81a9052a87452aa9ee26dd344a9b780`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "在题设的联合假定下，它不属于地球静止轨道。在这一假定下，它相对地面持续移动，并不保持在同一地表位置上方。"
}
```

#### 覆盖原文及理由

**R1** — 要求：将资料规则应用于题设的三项轨道前提，说明轨道类别。

参考覆盖：`covered`；模型覆盖：`partially_covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "partially_covered",
  "unit_ids": [
    "u-0b04d09a40a27e8373d334dd150827377a29ef5620602bf1584cd0917055c9ee"
  ],
  "rationale": "答案明确作出分类判断（不属于地球静止轨道），但没有正面给出应归为“地球静止轨道”这一类别；对题设圆形、赤道正上方条件如何导致该分类未展开，类别结论与题设前提的对应关系仅部分交代。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-0b04d09a40a27e8373d334dd150827377a29ef5620602bf1584cd0917055c9ee",
    "text": "在题设的联合假定下，它不属于地球静止轨道。",
    "start": 0,
    "end": 21
  }
]
```

**R2** — 要求：说明该假定轨道相对于地面的运动与地表对应位置。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-ad8ad8a77045ad98ab71c2590c8e9dfdee12a3fb574e20410ec68b95f0ee7dc9"
  ],
  "rationale": "明确陈述该假定下卫星相对地面持续移动，且不保持在同一地表位置上方，运动与地表对应位置两方面均有涉及。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-ad8ad8a77045ad98ab71c2590c8e9dfdee12a3fb574e20410ec68b95f0ee7dc9",
    "text": "在这一假定下，它相对地面持续移动，并不保持在同一地表位置上方。",
    "start": 21,
    "end": 52
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "在题设的联合假定下，它不属于地球静止轨道。",
  "start": 0,
  "end": 21,
  "expected_support": "contradicted",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "与联合条件对应的明确类别冲突。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-0b04d09a40a27e8373d334dd150827377a29ef5620602bf1584cd0917055c9ee",
  "rationale": "该单元就题设假定下的轨道类别给出结论（不属于地球静止轨道），属于对分类问题的直接回答，但结论与文献规则相反，且未说明应归为地球静止轨道。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "在题设的地球同步、圆形且赤道正上方这一联合假定下，该轨道不属于地球静止轨道。",
  "claim_type": "scenario_application",
  "support": "contradicted",
  "basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "文献NASA-X4指出圆形地球同步轨道且直接位于赤道正上方（偏心率和倾角为零）即构成地球静止轨道；题设前提恰好满足这些条件，因此该否定分类与规则相反。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "在这一假定下，它相对地面持续移动，并不保持在同一地表位置上方。",
  "start": 21,
  "end": 52,
  "expected_support": "contradicted",
  "expected_claim_type": "scenario_application",
  "selected_basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "与relative to ground和same place冲突。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-ad8ad8a77045ad98ab71c2590c8e9dfdee12a3fb574e20410ec68b95f0ee7dc9",
  "rationale": "该单元陈述该假定下卫星相对地面持续移动、不保持在同一地表位置上方，直接回应相对地面运动与地表对应位置，但方向与文献规则相反。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "在题设假定下，卫星相对地面持续移动，并不保持在同一地表位置上方。",
  "claim_type": "scenario_application",
  "support": "contradicted",
  "basis_ids": [
    "p-84341698b6ff2df34a1b56b36f0959096e0ef8c2c21823700e252b8c4db22cdc",
    "NASA-X4"
  ],
  "rationale": "NASA-X4说明圆形地球同步轨道直接位于赤道正上方时不会相对地面移动，始终位于同一地表位置上方；题设满足该条件，故持续移动且不固定于同一位置的断言与规则相反。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "答案对题设假定作出分类与运动/位置判断，但两处实质结论均与NASA-X4的地球静止轨道规则相反；分类方面也未正面给出正确类别，故R1仅部分覆盖、R2覆盖但判断被反驳。"
}
```

## H-BL-CDC-02

**问题原文（本家族三份回答共用）：**

```json
{
  "question": "根据给定CDC资料，说明含燃料、有毒化学品或放射性材料的水，能否靠煮沸或消毒使其安全。再解释为什么关于杀灭病菌的规则不能直接作为这些污染已被处理、或现场水源绝对安全的保证。不提供实际水源诊断或其他净化方案。"
}
```

**明确要求原文：**

```json
{
  "requirements": [
    {
      "requirement_id": "R1",
      "description": "说明资料对三类污染水使用煮沸或消毒的适用边界。"
    },
    {
      "requirement_id": "R2",
      "description": "解释杀菌规则与污染已处理或现场绝对安全保证之间的关系。"
    }
  ]
}
```

**题设前提（程序绑定，非现场已核实）：**

```json
{
  "scenario_premises": []
}
```

**完整交付的依据ID：** `CDC-X1`, `CDC-X2`, `CDC-X3`；选段/上下文/官方定位见文末依据索引。

### H-BL-CDC-02-A01

最终有效调用：8；响应UTF-8 SHA256：`4bfce679b5db892475a38dc762c89196f1e0e52e2fe48e514bc104137147735f`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "燃料、有毒化学品或放射性材料污染的水，不能靠煮沸或消毒变得安全。杀菌规则不能推翻这些明确列出的污染限制，因此不能据此保证现场水源绝对安全。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明资料对三类污染水使用煮沸或消毒的适用边界。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-335d5e0391c350dbca24d6369db2de75b06df25f3d11f3713294020b64929787"
  ],
  "rationale": "第一句明确说明含燃料、有毒化学品或放射性材料的水不能靠煮沸或消毒变得安全，直接回应了这三类污染水的适用边界。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-335d5e0391c350dbca24d6369db2de75b06df25f3d11f3713294020b64929787",
    "text": "燃料、有毒化学品或放射性材料污染的水，不能靠煮沸或消毒变得安全。",
    "start": 0,
    "end": 32
  }
]
```

**R2** — 要求：解释杀菌规则与污染已处理或现场绝对安全保证之间的关系。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-731d40ad47efece6c13f9f893869a35d7f46baae3d210ad54c080712aacc8a46"
  ],
  "rationale": "第二句说明杀菌规则不能推翻所列污染限制，因此不能保证现场水源绝对安全，解释了杀菌规则与安全保证之间不能直接划等号的关系。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-731d40ad47efece6c13f9f893869a35d7f46baae3d210ad54c080712aacc8a46",
    "text": "杀菌规则不能推翻这些明确列出的污染限制，因此不能据此保证现场水源绝对安全。",
    "start": 32,
    "end": 69
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "燃料、有毒化学品或放射性材料污染的水，不能靠煮沸或消毒变得安全。",
  "start": 0,
  "end": 32,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X1"
  ],
  "rationale": "三类污染及处理限制完整。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-335d5e0391c350dbca24d6369db2de75b06df25f3d11f3713294020b64929787",
  "rationale": "该单元陈述三类污染水不能靠煮沸或消毒变安全，涵盖对象、处理方式和否定结论，与文献规则一致，无额外诊断或方案。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "含燃料、有毒化学品或放射性材料的水，不能通过煮沸或消毒使其安全。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "CDC-X1"
  ],
  "rationale": "CDC-X1明确写明含燃料、有毒化学品或放射性材料的水不能靠煮沸或消毒变得安全，直接支撑该命题。"
}
```

**U2** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "杀菌规则不能推翻这些明确列出的污染限制，因此不能据此保证现场水源绝对安全。",
  "start": 32,
  "end": 69,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X1",
    "CDC-X2"
  ],
  "rationale": "已足够解释限制关系，无需化学去除机理或检测清单。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-731d40ad47efece6c13f9f893869a35d7f46baae3d210ad54c080712aacc8a46",
  "rationale": "该单元指出杀菌规则不能推翻明确列出的污染限制，并据此否定对现场水源绝对安全的保证，覆盖了规则与安全保证之间的限定关系。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "杀灭病菌的规则不能推翻燃料、有毒化学品或放射性材料的污染限制，因此不能据此保证现场水源绝对安全。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "CDC-X1",
    "CDC-X2"
  ],
  "rationale": "CDC-X1的污染限制明确排除了煮沸或消毒对这类污染水的安全性，CDC-X2的煮沸杀菌步骤仅针对杀灭病菌，不能覆盖污染限制，因而不能将杀菌规则直接作为绝对安全保证。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "回答直接引用并应用CDC关于污染水不可靠煮沸消毒变安全的规则，同时区分了杀菌规则与污染处理/绝对安全保证，完整回应两项要求。"
}
```

### H-BL-CDC-02-A02

最终有效调用：17；响应UTF-8 SHA256：`093099f380e8717d31abad13b6079cdc44bb3d2da103533b08229b6a52fc2a4d`。本项使用一次纠正后的最终响应。

**待评回答原文：**

```json
{
  "answer": "资料列举的污染类型包括燃料、有毒化学品和放射性材料。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明资料对三类污染水使用煮沸或消毒的适用边界。

参考覆盖：`partially_covered`；模型覆盖：`missing`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "missing",
  "unit_ids": [],
  "rationale": "回答仅列举了燃料、有毒化学品和放射性材料三类污染物，未说明对含此类污染的水煮沸或消毒的适用边界（即煮沸/消毒不能使其安全）。该边界内容缺失。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[]
```

**R2** — 要求：解释杀菌规则与污染已处理或现场绝对安全保证之间的关系。

参考覆盖：`missing`；模型覆盖：`missing`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "missing",
  "unit_ids": [],
  "rationale": "回答未涉及杀菌规则与污染已处理或现场水源绝对安全保证之间关系的解释，完全缺失。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "资料列举的污染类型包括燃料、有毒化学品和放射性材料。",
  "start": 0,
  "end": 26,
  "expected_support": "supported",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X1"
  ],
  "rationale": "仅列三类污染类型，没有回应处理限制或杀菌规则的关系。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-04081ef8cfdee2f264af5b581902b89cd54f2280c08751782b2cede73226d40c",
  "rationale": "该单元断言资料列举的污染类型包括燃料、有毒化学品和放射性材料。它仅复述来源的污染类别，未涉及煮沸/消毒限制或杀菌与安全保证的关系。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "资料将污染类型列举为包括燃料、有毒化学品和放射性材料。",
  "claim_type": "literature_statement",
  "support": "supported",
  "basis_ids": [
    "CDC-X1"
  ],
  "rationale": "CDC-X1开篇句明确指出含燃料、有毒化学品或放射性材料的水，与所断言的列举一致；这是对来源污染类别的复述，不涉及实际现场应用。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "回答仅列举来源中的污染类型，未涉及两项要求：煮沸/消毒对污染水不适用的边界（R1），以及杀菌规则与污染已处理/绝对安全保证之间的区分（R2）。"
}
```

### H-BL-CDC-02-A03

最终有效调用：25；响应UTF-8 SHA256：`14679ee8c753f60e69944c5a7a1e7ca7c6d95948a105b31a305e7064c41c1c5e`。本项初始即有效。

**待评回答原文：**

```json
{
  "answer": "含燃料、有毒化学品或放射性材料的水，煮沸或消毒后都能变得安全。杀菌规则因此足以推翻这些污染限制，并保证现场水源绝对安全。"
}
```

#### 覆盖原文及理由

**R1** — 要求：说明资料对三类污染水使用煮沸或消毒的适用边界。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R1",
  "coverage": "covered",
  "unit_ids": [
    "u-60b2afc1ba5753230fdce2549654c3076254973742f8b32fe2cfcdb525ef8c14"
  ],
  "rationale": "该单元明确就含燃料、有毒化学品或放射性材料的水煮沸或消毒的适用性作出结论，直接回应了三类污染和两种处理方式的边界问题（尽管结论与资料相反）。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-60b2afc1ba5753230fdce2549654c3076254973742f8b32fe2cfcdb525ef8c14",
    "text": "含燃料、有毒化学品或放射性材料的水，煮沸或消毒后都能变得安全。",
    "start": 0,
    "end": 31
  }
]
```

**R2** — 要求：解释杀菌规则与污染已处理或现场绝对安全保证之间的关系。

参考覆盖：`covered`；模型覆盖：`covered`。

**模型原文：**

```json
{
  "requirement_id": "R2",
  "coverage": "covered",
  "unit_ids": [
    "u-2a8f7f10549a8ed0539a818eb1c34b68f7091890bcfae9f0c6c10f4b140e67db"
  ],
  "rationale": "该单元用'因此足以推翻这些污染限制'和'保证现场水源绝对安全'把杀菌规则与污染是否已处理、现场是否绝对安全联系起来，明确给出两者关系（尽管结论与资料相反）。"
}
```

**上述模型unit_ids所指回答原文与程序区间：**

```json
[
  {
    "unit_id": "u-2a8f7f10549a8ed0539a818eb1c34b68f7091890bcfae9f0c6c10f4b140e67db",
    "text": "杀菌规则因此足以推翻这些污染限制，并保证现场水源绝对安全。",
    "start": 31,
    "end": 60
  }
]
```

#### 参考单元对应的全部预测判断

**U1** — AI建议可对齐，待本人复核

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U1",
  "exact_text": "含燃料、有毒化学品或放射性材料的水，煮沸或消毒后都能变得安全。",
  "start": 0,
  "end": 31,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X1"
  ],
  "rationale": "与cannot make safe直接冲突。"
}
```

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-60b2afc1ba5753230fdce2549654c3076254973742f8b32fe2cfcdb525ef8c14",
  "rationale": "该单元陈述含燃料、有毒化学品或放射性材料的水经煮沸或消毒'都能变得安全'，涵盖三类污染物和两种处理方式，结论为肯定；与CDC-X1明确相反。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "含燃料、有毒化学品或放射性材料的水经煮沸或消毒后都能变得安全。",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "CDC-X1"
  ],
  "rationale": "CDC-X1明确规定：不能通过煮沸或消毒使含燃料、有毒化学品或放射性材料的水变得安全，与该普遍肯定性陈述直接矛盾。"
}
```

**U2** — 未对齐：混合标签，全部拆分判断保留

**参考/程序元数据（不是模型输出）：**

```json
{
  "reference_unit_id": "U2",
  "exact_text": "杀菌规则因此足以推翻这些污染限制，并保证现场水源绝对安全。",
  "start": 31,
  "end": 60,
  "expected_support": "contradicted",
  "expected_claim_type": "literature_statement",
  "selected_basis_ids": [
    "CDC-X1",
    "CDC-X2"
  ],
  "rationale": "把一般杀菌作用推成对已明确排除污染的安全保证，非真实现场实例核验问题。"
}
```

未对齐说明（原AI审阅摘要，非模型理由）：U2拆为推翻限制C＋保证现场安全I，混合标签，按事前规则无法对齐。

**原模型单元及单元理由：**

```json
{
  "unit_id": "u-2a8f7f10549a8ed0539a818eb1c34b68f7091890bcfae9f0c6c10f4b140e67db",
  "rationale": "该单元断言杀菌规则足以推翻污染限制并保证现场水源绝对安全，包含'推翻限制'和'绝对安全保证'两项关联主张；未提供实际现场记录。"
}
```

**J0（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "杀菌规则足以推翻关于燃料、有毒化学品或放射性材料的污染限制。",
  "claim_type": "literature_statement",
  "support": "contradicted",
  "basis_ids": [
    "CDC-X1"
  ],
  "rationale": "CDC-X1指出此类污染不能靠煮沸或消毒去除，并建议改用瓶装水或其他水源、联系卫生部门，因此杀菌规则并不推翻污染限制，该主张与其相反。"
}
```

**J1（原judgments数组0起始下标）— 模型命题／标签／依据／理由原文：**

```json
{
  "proposition": "杀菌规则能保证现场水源绝对安全。",
  "claim_type": "external_claim",
  "support": "insufficient_evidence",
  "basis_ids": [
    "CDC-X1"
  ],
  "rationale": "'现场水源绝对安全'是对特定现场安全状态的断言；所给资料为一般性规则，不构成对任何实际现场的诊断或验证记录，故支持不足。"
}
```

#### 模型总体理由原文

```json
{
  "rationale": "两个要求均被回答以明确（虽与资料相反）的结论覆盖；两个答案单元分别涉及处理适用边界和杀菌规则与安全保证的关系，支持判定按CDC-X1及相关范围处理。"
}
```

## 依据索引：12个完整选段及必要上下文

仅重复已获授权公开的候选选段/必要上下文，不复制整份官方文档。每条text与本批交付evidence文本相同，scope_context与冻结任务一致；所有evidence均为literature。题设p-ID原文见各家族题设块。

### NWS-X1

```json
{
  "text": "The probability of precipitation (POP), is defined as the likelihood of occurrence (expressed as a percent) of a measurable amount of liquid precipitation (or the water equivalent of frozen precipitation) during a specified period of time at any given point in the forecast area. Measurable precipitation is equal to or greater than 0.01 inches. Unless specified otherwise, the time period is normally 12 hours. NWS forecasts use such categorical terms as occasional, intermittent, or periods of to describe a precipitation event that has a high probability of occurrence (80%+), but is expected to be of an \"on and off\" nature.",
  "url": "https://www.weather.gov/ppg/forecast_terms",
  "locator": "Precipitation Probability heading; complete body paragraph including following on/off sentence",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "NWS-X1",
  "scope_context": [
    {
      "text": "The probability of precipitation (POP), is defined as the likelihood of occurrence (expressed as a percent) of a measurable amount of liquid precipitation (or the water equivalent of frozen precipitation) during a specified period of time at any given point in the forecast area. Measurable precipitation is equal to or greater than 0.01 inches. Unless specified otherwise, the time period is normally 12 hours. NWS forecasts use such categorical terms as occasional, intermittent, or periods of to describe a precipitation event that has a high probability of occurrence (80%+), but is expected to be of an \"on and off\" nature.",
      "url": "https://www.weather.gov/ppg/forecast_terms",
      "locator": "Precipitation Probability heading; complete body paragraph including following on/off sentence; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### NWS-X2

```json
{
  "text": "The sky condition describes the predominant/average sky cover based on percent of the sky covered by opaque (not transparent) clouds. If a high probability of precipitation (60% or greater) is expected, then the sky condition may be omitted since it is inferred from the precipitation forecast.",
  "url": "https://www.weather.gov/ppg/forecast_terms",
  "locator": "Sky Condition heading; complete opening paragraph, no table rows needed for this direction",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "NWS-X2",
  "scope_context": [
    {
      "text": "The sky condition describes the predominant/average sky cover based on percent of the sky covered by opaque (not transparent) clouds. If a high probability of precipitation (60% or greater) is expected, then the sky condition may be omitted since it is inferred from the precipitation forecast.",
      "url": "https://www.weather.gov/ppg/forecast_terms",
      "locator": "Sky Condition heading; complete opening paragraph, no table rows needed for this direction; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### USGS-X1

```json
{
  "text": "In the 1960’s, the United States government \ndecided to use the 1-percent annual \nexceedance probability (AEP) flood as \nthe basis for the National Flood Insurance \nProgram. The 1-percent AEP flood was \nthought to be a fair balance between \nprotecting the public and overly stringent \nregulation.  Because the 1-percent AEP flood \nhas a 1 in 100 chance of being equaled or \nexceeded in any 1 year, and it has an average \nrecurrence interval of 100 years, it often is referred to as the “100-year flood”.",
  "url": "https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf",
  "locator": "PDF page 1, left column: So what is a 100-year flood and how is it determined?, complete first paragraph",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "USGS-X1",
  "scope_context": [
    {
      "text": "In the 1960’s, the United States government \ndecided to use the 1-percent annual \nexceedance probability (AEP) flood as \nthe basis for the National Flood Insurance \nProgram. The 1-percent AEP flood was \nthought to be a fair balance between \nprotecting the public and overly stringent \nregulation.  Because the 1-percent AEP flood \nhas a 1 in 100 chance of being equaled or \nexceeded in any 1 year, and it has an average \nrecurrence interval of 100 years, it often is referred to as the “100-year flood”.",
      "url": "https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf",
      "locator": "PDF page 1, left column: So what is a 100-year flood and how is it determined?, complete first paragraph; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### USGS-X2

```json
{
  "text": "A flood is any relatively high streamflow \novertopping the natural or artificial banks in \nany reach of a stream. Floods occur for many \nreasons, such as long-lasting rainfall over a broad \narea, locally intense thunderstorm-generated \nrainfall, or rapid melting of a large snow pack \nwith or without accompanying rainfall.  Because \nfloods result from many different circumstances, \nnot all floods are equal in magnitude, duration, or \neffect.   Placing floods in context allows society to address such issues as the risk to life and \nproperty, and to study and understand the environmental benefits of floods. Trying to place \ncontextual framework around floods is where such terms as “100-year flood” came into \nbeing.",
  "url": "https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf",
  "locator": "PDF page 1, left top: What is a Flood?, complete body paragraph; extraction order differs from visual order",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "USGS-X2",
  "scope_context": [
    {
      "text": "A flood is any relatively high streamflow \novertopping the natural or artificial banks in \nany reach of a stream. Floods occur for many \nreasons, such as long-lasting rainfall over a broad \narea, locally intense thunderstorm-generated \nrainfall, or rapid melting of a large snow pack \nwith or without accompanying rainfall.  Because \nfloods result from many different circumstances, \nnot all floods are equal in magnitude, duration, or \neffect.   Placing floods in context allows society to address such issues as the risk to life and \nproperty, and to study and understand the environmental benefits of floods. Trying to place \ncontextual framework around floods is where such terms as “100-year flood” came into \nbeing.",
      "url": "https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf",
      "locator": "PDF page 1, left top: What is a Flood?, complete body paragraph; extraction order differs from visual order; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### USGS-X3

```json
{
  "text": "The “100-year \nflood” is an \nestimate of the \nlong-term average \nrecurrence interval, \nwhich does not \nmean that we really \nhave 100 years \nbetween each flood \nof greater or equal \nmagnitude. Floods \nhappen irregularly.",
  "url": "https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf",
  "locator": "PDF page 1, middle panel: On the river near me..., complete first paragraph; graph is not needed for this paragraph",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "USGS-X3",
  "scope_context": [
    {
      "text": "The “100-year \nflood” is an \nestimate of the \nlong-term average \nrecurrence interval, \nwhich does not \nmean that we really \nhave 100 years \nbetween each flood \nof greater or equal \nmagnitude. Floods \nhappen irregularly.",
      "url": "https://pubs.usgs.gov/gip/106/pdf/100-year-flood_041210web.pdf",
      "locator": "PDF page 1, middle panel: On the river near me..., complete first paragraph; graph is not needed for this paragraph; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### NASA-X1

```json
{
  "text": "In addition to height, eccentricity and inclination also shape a satellite’s orbit. Eccentricity refers to the shape of the orbit. A satellite with a low eccentricity orbit moves in a near circle around the Earth. An eccentric orbit is elliptical, with the satellite’s distance from Earth changing depending on where it is in its orbit.",
  "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
  "locator": "Body before Three Classes of Orbit, complete eccentricity paragraph",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "NASA-X1",
  "scope_context": [
    {
      "text": "In addition to height, eccentricity and inclination also shape a satellite’s orbit. Eccentricity refers to the shape of the orbit. A satellite with a low eccentricity orbit moves in a near circle around the Earth. An eccentric orbit is elliptical, with the satellite’s distance from Earth changing depending on where it is in its orbit.",
      "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
      "locator": "Body before Three Classes of Orbit, complete eccentricity paragraph; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### NASA-X2

```json
{
  "text": "Inclination is the angle of the orbit in relation to Earth’s equator. A satellite that orbits directly above the equator has zero inclination. If a satellite orbits from the north pole (geographic, not magnetic) to the south pole, its inclination is 90 degrees.",
  "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
  "locator": "Body before Three Classes of Orbit, complete inclination paragraph",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "NASA-X2",
  "scope_context": [
    {
      "text": "Inclination is the angle of the orbit in relation to Earth’s equator. A satellite that orbits directly above the equator has zero inclination. If a satellite orbits from the north pole (geographic, not magnetic) to the south pole, its inclination is 90 degrees.",
      "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
      "locator": "Body before Three Classes of Orbit, complete inclination paragraph; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### NASA-X3

```json
{
  "text": "When a satellite reaches exactly 42,164 kilometers from the center of the Earth (about 36,000 kilometers from Earth’s surface), it enters a sort of “sweet spot” in which its orbit matches Earth’s rotation. Because the satellite orbits at the same speed that the Earth is turning, the satellite seems to stay in place over a single longitude, though it may drift north to south. This special, high Earth orbit is called geosynchronous.",
  "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
  "locator": "High Earth Orbit, complete first paragraph",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "NASA-X3",
  "scope_context": [
    {
      "text": "When a satellite reaches exactly 42,164 kilometers from the center of the Earth (about 36,000 kilometers from Earth’s surface), it enters a sort of “sweet spot” in which its orbit matches Earth’s rotation. Because the satellite orbits at the same speed that the Earth is turning, the satellite seems to stay in place over a single longitude, though it may drift north to south. This special, high Earth orbit is called geosynchronous.",
      "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
      "locator": "High Earth Orbit, complete first paragraph; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### NASA-X4

```json
{
  "text": "A satellite in a circular geosynchronous orbit directly over the equator (eccentricity and inclination at zero) will have a geostationary orbit that does not move at all relative to the ground. It is always directly over the same place on the Earth’s surface.",
  "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
  "locator": "High Earth Orbit, complete second paragraph",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "NASA-X4",
  "scope_context": [
    {
      "text": "When a satellite reaches exactly 42,164 kilometers from the center of the Earth (about 36,000 kilometers from Earth’s surface), it enters a sort of “sweet spot” in which its orbit matches Earth’s rotation. Because the satellite orbits at the same speed that the Earth is turning, the satellite seems to stay in place over a single longitude, though it may drift north to south. This special, high Earth orbit is called geosynchronous.\nA satellite in a circular geosynchronous orbit directly over the equator (eccentricity and inclination at zero) will have a geostationary orbit that does not move at all relative to the ground. It is always directly over the same place on the Earth’s surface.",
      "url": "https://science.nasa.gov/earth/earth-observatory/catalog-of-earth-satellite-orbits/",
      "locator": "High Earth Orbit, complete second paragraph; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### CDC-X1

```json
{
  "text": "You cannot make water containing fuel, toxic chemicals, or radioactive materials safe by boiling or disinfecting it. If you know or suspect your water contains fuel or toxic chemicals: 1) Use bottled water or a different source of water 2) Contact your health department for specific advice.",
  "url": "https://www.cdc.gov/water-emergency/about/",
  "locator": "Overview > Water with fuel or toxic chemicals in it, complete paragraph",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "CDC-X1",
  "scope_context": [
    {
      "text": "You cannot make water containing fuel, toxic chemicals, or radioactive materials safe by boiling or disinfecting it. If you know or suspect your water contains fuel or toxic chemicals: 1) Use bottled water or a different source of water 2) Contact your health department for specific advice.",
      "url": "https://www.cdc.gov/water-emergency/about/",
      "locator": "Overview > Water with fuel or toxic chemicals in it, complete paragraph; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### CDC-X2

```json
{
  "text": "If the water is cloudy, first filter it through a clean cloth, paper towel, or coffee filter. Another option is to let it settle. Then, draw off the clear water and follow the steps below.\nBring clear water to a rolling boil for 1 minute (at elevations above 6,500 feet, boil for 3 minutes).\nLet the boiled water cool.\nStore the boiled water in clean, sanitized containers with tight covers.",
  "url": "https://www.cdc.gov/water-emergency/about/",
  "locator": "Boil > Steps for boiling water, complete preparation paragraph and all three list items",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "CDC-X2",
  "scope_context": [
    {
      "text": "If you don’t have safe bottled water, boil your water to make it safe to drink.\nBoiling is the best way to kill germs in water.\nSteps for boiling water\nIf the water is cloudy, first filter it through a clean cloth, paper towel, or coffee filter. Another option is to let it settle. Then, draw off the clear water and follow the steps below.\nBring clear water to a rolling boil for 1 minute (at elevations above 6,500 feet, boil for 3 minutes).\nLet the boiled water cool.\nStore the boiled water in clean, sanitized containers with tight covers.",
      "url": "https://www.cdc.gov/water-emergency/about/",
      "locator": "Boil > Steps for boiling water, complete preparation paragraph and all three list items; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

### CDC-X3

```json
{
  "text": "Instead, use bottled, boiled, or treated water for drinking, cooking, and personal hygiene. Follow recommendations from your health department for boiling or treating your water.",
  "url": "https://www.cdc.gov/water-emergency/about/",
  "locator": "Overview, complete paragraph specifying health-department recommendations",
  "text_basis": "unchanged confirmed source excerpt; saved extraction Unicode span",
  "evidence_id": "CDC-X3",
  "scope_context": [
    {
      "text": "Instead, use bottled, boiled, or treated water for drinking, cooking, and personal hygiene. Follow recommendations from your health department for boiling or treating your water.",
      "url": "https://www.cdc.gov/water-emergency/about/",
      "locator": "Overview, complete paragraph specifying health-department recommendations; necessary context",
      "text_basis": "unchanged saved source context"
    }
  ],
  "source_role": "literature"
}
```

## 字段核对与范围留痕

程序已核对58个参考映射与既有公开对齐记录一致；51个覆盖对象、66个唯一判断与24个总体理由均与24份最终有效响应JSON解码值逐字段一致；所有最终响应SHA与已公开调用哈希清单一致。两个混合未对齐项各两个判断均保留。原参考、匹配规则、原结果及分数未改。

本文件是本人2026-10-22明确授权发布的所选字段投影，不能代替完整原始响应档案，也不将助手工程SHA检查登记为本人验真。本轮0新增模型调用、0补跑，不改提示/解析器/生产。后续若发现字段展示或语义审阅问题，另版保留修订，不能回改本批原预测或预期标签。

原结果JSON字节SHA256：`4ad50d85e7fd60ce5bfeddb27d3db45d2e3859ec0ad5cc4bbde46fbd29cd7afd`；原实际调用哈希清单字节SHA256：`b6cec44ddce6f35994c005759a894f1b1e6dfa9aa8fc8d9d922ae928d810ca73`。
