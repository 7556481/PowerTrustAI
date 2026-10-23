# 两阶段与联合v2：固定开发对照

建议：继续候选，不采用为生产默认。常规9组件/版原始支持均9/9对齐参考，有效支持v2为6/9、两阶段5/9；没有证据表明多一次初始调用值得。单次随机输出、协议中间信息差异与开发材料重复使用，不支持架构因果归因。F05单列诊断，两版内容supported且有效复核；v2最终仍把规则称为应用，两阶段改为规则但明确反对阶段一。

全部16分支完成，计划分母不缩减。初始24、纠正3、实际27；无执行失败、未执行、重发或恢复。费用未知。完整消息、全部响应及无效初始尝试见 [predictions.json](predictions.json)，每组件理由、条件摘录、依据、阶段一和二输出见 [results.json](results.json)。两阶段第二阶段收到实际回答、原文目录及第一阶段判断；联合版无中间判断。

|分支|初始/纠正|秒|原始→有效支持（按组件）|
|---|---|---|---|
|F01-v2|1/0|2.107|supported→supported；supported→supported|
|F01-two_stage|2/0|4.017|supported→not_assessable；supported→supported|
|F02-two_stage|2/0|3.613|contradicted→contradicted|
|F02-v2|1/0|1.576|contradicted→contradicted|
|F03-v2|1/0|1.361|supported→supported|
|F03-two_stage|2/0|3.07|supported→supported|
|F04-two_stage|2/0|2.759|supported→supported|
|F04-v2|1/0|1.675|supported→supported|
|F05-v2|1/1|3.295|supported→not_assessable|
|F05-two_stage|2/0|4.1|supported→not_assessable|
|F06-two_stage|2/0|3.752|insufficient_evidence→not_assessable|
|F06-v2|1/0|1.975|insufficient_evidence→not_assessable|
|F07-v2|1/1|4.151|supported→not_assessable；contradicted→not_assessable|
|F07-two_stage|2/1|6.599|supported→supported；contradicted→not_assessable|
|F08-two_stage|2/0|3.899|insufficient_evidence→not_assessable|
|F08-v2|1/0|1.899|insufficient_evidence→insufficient_evidence|

## 分项复核

F01：联合版规则和应用分别依赖正文、正文＋P0。两阶段阶段一错分规则为应用，阶段二纠正分类并明确冲突，因此规则进入复核，应用受支持。F02：两阶段明确条件已表达 yes、实例满足 no、结论 no，判矛盾，未把条件出现当满足。F03：两版只用相关P0和正文，无关P1/P2不成为义务。F04：两版保留71与64的来源及标量结果，两阶段不额外创造条件。

F06：两版原始证据不足；联合版给分类异议、两阶段最终uncertain及冲突，均有效无法评估。模型仍选无关颜色题设，说明依赖判断未解决。F07：联合版两个原始判断正确但不必要分类异议使两项复核；两阶段正确转述获支持，错误转述虽被判矛盾，阶段二反对阶段一的外部事实分类而复核。F08：两版原始不足；联合版保留engineering_relation及有效不足，两阶段uncertain且条件未知，有效无法评估。缺寿命模型属于证据和工程能力缺口，不是执行失败。

常规有效无法评估：v2为3/9，两阶段4/9；受支持参考项被延后：v2为F07正确转述，两阶段为F01规则复述。没有参考矛盾/不足项被有效错误支持；没有supported被错误contradicted。无法评估、错误拒支持与执行失败分开，不把延后复核算正确拒绝。最终对象类型：按原开发参考v2为9/10、两阶段8/10；不当独立分类准确率，F05为预置故障诊断。两阶段显式冲突4组件（F01规则、F05、F06、F07错误转述），全部保留。原文忠实性、分类异议、内容支持均见逐项原记录；这些模型声明不是程序语义认证。

## 工程验证与限制

完整回归1184项通过，218.463秒；新专项3项包含八例实际适配器消息、单例最终失败继续和共享连接故障停止。学习站20章/60自测、构建、源码身份和链接通过。旧测试覆盖原引用隔离、取消、超时、预算、持久化失败、修订完整重审及历史保存；本轮新增两阶段专属测试没有为这些组合逐一增加覆盖，不能声称所有两阶段服务组合均有独立验收。候选服务Factory/API配置已接线；本轮付费比较是事实接口，不是完整问答服务端到端真实验收。8765拒绝连接，未启动服务；只读配置仍langgraph_v1/production/schema13。

内部计时：model_records保留每请求duration_ms（阶段一/二按实际发送顺序，correction字段区分纠正）；object_reviews.stage_one_seconds记录第一阶段含纠正耗时，分支seconds包含图及归档。第二阶段内部时间未单独作为墙钟字段保存，只能报告对应请求模型时间，不能将相减值当精确阶段耗时。

回退：开发环境移除POWERTRUST_FACT_INTERNAL_FLOW或设production；joint_v2仍为比较基线。未修改生产配置或外层图，不自动切换。新增/复用/暂留清单及其他Agent优先级见 [engineering-review.md](engineering-review.md)。

## 小统计

```json
{
  "v2": {
    "planned_branches": 8,
    "complete": 8,
    "first_contract_valid": 6,
    "initial_calls": 8,
    "correction_calls": 2,
    "usage": {
      "input_tokens": 20795,
      "output_tokens": 2310,
      "total_tokens": 23105,
      "cache_hit_tokens": 13691,
      "cache_miss_tokens": 7104
    },
    "model_seconds": 17.374,
    "branch_seconds": 18.038540800014744,
    "raw_reference_matches": 9,
    "effective_reference_matches": 6,
    "regular_components": 9,
    "false_supported": 0,
    "false_contradicted": 0,
    "execution_failed": 0,
    "unexecuted": 0
  },
  "two_stage": {
    "planned_branches": 8,
    "complete": 8,
    "first_contract_valid": 7,
    "initial_calls": 16,
    "correction_calls": 1,
    "usage": {
      "input_tokens": 28053,
      "output_tokens": 4099,
      "total_tokens": 32152,
      "cache_hit_tokens": 6144,
      "cache_miss_tokens": 21909
    },
    "model_seconds": 31.08,
    "branch_seconds": 31.80981969999266,
    "raw_reference_matches": 9,
    "effective_reference_matches": 5,
    "regular_components": 9,
    "false_supported": 0,
    "false_contradicted": 0,
    "execution_failed": 0,
    "unexecuted": 0
  }
}
```
