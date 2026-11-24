# 31 修订合同：一处改动、两条意见和新版重审

本页讲已发生的合同改造与教学重建，不声明个人当时如何参与。实际四例的输入、源码和结果见[固定报告](../../evaluation/local-revision-v2-flash-check-v1/report.md)；当前配置只看[当前状态](../../current-status.md)。下述D/O属于历史默认关闭的source_actions_v2候选，不能当正式默认修订协议。

## 先把错误放回一段完整回答
教学来源S0：`Under C, the permitted setting is 3 kV. It does not exceed 5 kV.`；来源S1：`The relay has two terminals.`。初稿U0写成：
```text
Under C, the permitted setting is 9 kV. The relay has two terminals.
```
第二段U1又写了一句正确的继电器事实。目标是改9为3，同时保留C条件、继电器事实、正确第二段及对应引用，不能把“纠错”变成重写整篇摘要。已确认的错误是数值，不是“继电器有两个端子”有错。

## 授权 D 与意见 O 如何分离
旧接口把关系角色、ID集合、替换正文和意见说明混在一次输出；第一阶段四次修订全部不合法。额外字段、缺失或串错ID、角色集合不闭合，都可能让内容看起来已改却无法应用。具体失败保留在[旧阶段报告](../../evaluation/literal-review-stage1-v1/report.md)，不能把离线重写的对象叫当时模型输出。

v2的plan把有来源绑定、能定位的数值缺陷做成D0；D0指向U0里的9 kV及S0支持范围。审核意见O0记录这个事实缺陷，领域意见O1指出同一设定表达过宽，但O1自身没有提供来源授权。O描述“谁提出什么意见”，D描述“允许改哪里、依据是什么”；一条O可以指向D，也可以没有D。

教学状态表：
|对象|内容|能否单独授权改稿|
|---|---|---|
|D0|U0数值错，S0证明C下应为3|可以在允许单元/来源范围内授权|
|O0|事实意见：9与来源不符，关联D0|通过D0，不是靠O身份|
|O1|领域意见：设定表述需收窄，无独立D|不可以；可记录同一编辑处理了它|
|S1|原正确继电器事实的prior_support|是可选依据范围，不自动证明新文都正确|

[local_revision_v2.system](../../../services/local_revision_v2.py)明确：
```text
authorization_refs selects D ONLY: concrete source-bound defects.
O opinions NEVER grant authority.
```
这里的“只能D”是程序角色约束，不证明D对应的自然语言判断绝对正确；D来源仍须人工/模型语义复核。

## 一次编辑怎样同时处理两条意见
```json
{
  "unit_ref": "U0",
  "authorization_refs": ["D0"],
  "text": "Under C, the permitted setting is 3 kV. The relay has two terminals.",
  "support_refs": ["S0", "S1"],
  "dependencies": []
}
```
此为完整edit子对象，完整根对象还需context_id、edits数组和opinion_actions。O0/O1分别记`modified, edit_indices=[0]`，两条意见都指向同一真实编辑，不能为每条意见重复改U0。解释应写这次编辑怎样回应意见，不把“已解决所有工程问题”当结论。

parse检查context、U/D/S角色、每个D的来源是否被选、编辑索引和意见全覆盖，然后仅替换选择的完整单元，未选择U1保持原文。若改成authorization_refs=[O1]，即使正文3 kV写对也拒绝；若只选S1，缺少D0的授权来源也拒绝。保留S1是为了正确继电器内容仍有依据，不是为了凑引用。

## 正确内容怎样留住，版本怎样继续走
程序重建未选单元并保留其引用，对选单元重建引用绑定，产生answer.version=2与preservation记录。[测试](../../../tests/test_local_revision_v2.py)逐字比较未选段、检查引用与动作集合；这能证明机械保留，不能机械证明选单元里的所有语义都保留。

Harness应用新版后，不把v1的claims/findings挂到v2。revise成功回extract_and_tools，新提取、新事实审核、新领域审核，再由政策决定交付；Store按answer_id/version保存两版及各自意见。资格和次数已耗尽仍有问题时，保留待复核，不进入第二轮业务修订。

真实四例合法应用、目标改对、正确/必答内容保留、重提取双审Store闭合均4/4，16次Flash/82465token。这是在已见固定合法初审之后验证修订后半链，不是系统从自然问题自主发现并修好4/4。第一阶段0/4、自然纠错收益未证保持。

::: answer 题31.1：O1没有D，为什么它可以记modified却不能放进authorization_refs？
先看编辑是否已由D0合法授权，再看O1是否确被该编辑回应。此例数值由9改3并保留C，已在授权范围；O1可以指向edit0记处理，但它不能凭自己要求把正确继电器段改掉。若O1要求增加现场投切结论，edit0没有解决它，应记unresolved或有理由的retained，不能因为同句发生改动就全部modified。程序检查关系闭合，是否真实解决仍需重审。
:::

::: answer 题31.2：若另有结论“设定超过5 kV”，应顺手删掉吗？
不能仅因为改了前提就任意编辑其他单元。需要定位该结论自己的错误/授权，并用依赖记录说明它怎样依赖U0。existing tests的dependent=True同时构造自身缺陷与依赖，它们不互斥；只报告依赖不能豁免来源授权。若没有合法依据，保留未解决并记录，而不是跨单元自动全局替换9。
:::
