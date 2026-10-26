# 新合同的三个端到端静态例与反例

**全部为本任务新手写合成例，不是真实模型交付，不是将旧8响应清洗得到。** [完整实际输入结构、拟输出、程序派生和后续检查](static-examples.json)使用同一个plan/parse实现；其中来源均为短小synthetic_fixture，不含旧真实来源全文。

## 各字段的职责

| 字段/目录 | 必要性 |
|---|---|
| context_id | 程序给出，绑定本任务/回答版本/来源及目录；模型原样选择，不计算身份 |
| U | 完整原文单元、真实锚点和范围；完整answer另供上下文理解 |
| D / authorization_refs | 来源绑定差异及纠正边界，唯一修改授权；不是领域意见集合 |
| O / opinion_ref | 事实/领域意见逐条处理，保留真实ID与来源；不授予证据 |
| S / support_refs | 完整实际来源一次供给；每U的合法保留来源及每D纠正来源分开列；模型明确选择新正文支持来源 |
| dependencies | 单独的其他U及非空理由，可与本单元自身D并存；不是程序证明的依赖关系 |
| edit_indices | modified意见指向实际编辑；事实O还必须指向使用自身D的编辑，领域O可回应同一编辑 |

## 1. 单一错误

初稿U0：“Under C, the permitted setting is 9 kV.”；U1：“The relay has two terminals.”。S0明确说C下允许3kV，D0定位9kV；O0是该缺陷，O1为领域意见。手写编辑只替换U0为3kV，选D0、S0；U1及其引用、分隔符原样保留，版本1→2。不是看见9/3就硬编码：解析器只校验位置、合法来源和动作，语义仍来自合成例已知条件。

## 2. 正确＋错误混合，兼顾领域意见

初稿U0：“Under C, the permitted setting is 9 kV. The relay has two terminals.”；U1同样正确解释继电器有两个端子。S0支持3kV，另一来源S1支持两个端子。D0只授权纠正setting，U0的prior_support保留合法S1。

拟输出结构（context_id的完整实际值见JSON）：

```json
{
  "context_id": "本例程序给定的revision-context摘要",
  "edits": [{
    "unit_ref": "U0",
    "authorization_refs": ["D0"],
    "text": "Under C, the permitted setting is 3 kV. The relay has two terminals.",
    "support_refs": ["S0", "S1"],
    "dependencies": []
  }],
  "opinion_actions": [
    {"opinion_ref":"O0","action":"modified","edit_indices":[0],"explanation":"Proposes correcting the sourced setting."},
    {"opinion_ref":"O1","action":"modified","edit_indices":[0],"explanation":"The same edit addresses this domain opinion; it grants no source authority."}
  ]
}
```

程序派生：D0确实属于当前U0、O0/O1均指向实际编辑0；新引用只绑定明确选中的S0/S1；未选U1文字和原引用按偏移保留。**程序不能据两个合法来源ID证明整句新正文正确**，也不能证明混合段所有正确内容都被保留。后续仍须正常重新提取和完整双审，再由Store保存/读取。

## 3. 有自身缺陷的结论，也依赖修正前提

U0的setting错误；U1另有自身错误“The permitted setting exceeds 5 kV.”，并依赖U0。两份D各有来源。手写一次编辑同时纠正U0和U1：U1引用自身D与U0的D，dependencies声明U0及具体理由，支持选实际来源。程序同时派生same_location和other_location，不要求二选一；其他正确U2保留。需要改一个前提和直接依赖结论，不等于建立新知识图谱或证明推理正确。

## 无依据反例与终止

将编辑授权填成领域O1，即使该O1确实存在、理由合理、另有可用S，也拒绝，报告legal_authorization_ref_required并保留角色合法集合。无依赖理由/不同时改前提的跨单元编辑也拒绝。非法响应不部分应用。

全部意见retained/unresolved、edits=[]则合法返回完整原answer对象，包括原引用顺序，消耗一次尝试后review_required；不递增版本、不重置预算、不自动pass或再次修订。静态可表达性和离线替身贯通不证明下次模型会照做。
