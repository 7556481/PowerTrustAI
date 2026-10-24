# 官方兼容核对与本地义务

2026-10-24核对：[工具调用指南](https://api-docs.deepseek.com/guides/tool_calls/)、[Chat Completion API](https://api-docs.deepseek.com/api/create-chat-completion/)。前者明确strict需Beta且函数strict=true，支持对象/字符串/数值/布尔/数组/枚举/anyOf；对象属性全部必填且禁止额外属性，字符串长度和数组数量限制未支持。后者列出deepseek-flash、显式非思考及具名工具选择，定义工具结束状态与参数为字符串。使用/beta/chat/completions、thinking disabled和具名submit_review_result；不发送未列出的parallel_tool_calls参数。实际服务器接受仍由正式A1/A3验证，不用付费探针。

指南支持列表未列null，不能推断nullable union必受支持。因此另立strict-review-tool-v1传输：objection/repair的业务null精确编码为字符串__NULL__，其对象分支原样传输，用anyOf表达；解码精确还原None。原unknown、false、空数组及合法对象不变，不变成空对象，不补缺字段。裸null在新载体中不算合法成功。有效业务域上encode/decode双向往返测试通过。

## 实际字段对应

| 原业务字段 | 请求声明的Schema约束（非实测保证） | 本地保留 |
|---|---|---|
| judgments | 数组、对象字段 | 顺序、目标数量/覆盖、绑定与合法同伴 |
| status | 四种支持状态枚举 | 原始/有效区分、投影与事实依据 |
| basis_ids | 字符串数组 | 去重检查、合法类型/ID/作用域，程序不补选 |
| reason | 字符串 | 非空、保留理由；不靠关键词改标签 |
| gap_answer_ids | 字符串数组 | 当前答案单元绑定、引用隔离 |
| conditions | 六属性全部必填、三维枚举和ID数组 | 条件/实例独立、归属/来源绑定、不确定和冲突投影 |
| inference | preserved/unsupported/uncertain | 同既有投影，无关键词重分类 |
| objection | __NULL__或kind/reason对象，原枚举 | None或合法异议的原义和保守处置 |
| repair | __NULL__或basis_id/replacement对象 | 选中正文支持、修订资格及完整重审 |
| requires_authoritative_source | 布尔 | 既有权限/来源规则 |

每层对象additionalProperties=false且required完整。没有用Schema替代理由非空、合法ID、数组去重或数量；没有移除任一业务字段。Schema不证明支持/条件/结论正确。

## 输出信封与审计

本地要求一个choice、一个function调用、非空调用ID、固定函数名、原始arguments字符串及finish_reason=tool_calls。检查实际普通content，允许null/空白但拒绝非空文本与参数混载；不从冲突结果中挑一个。错误工具、无工具、多工具和异常结束不能成功。截断沿原有最终输出失败行为，其他可定位合同失败按原有限纠正；纠正仍发送同一Schema/工具，不追加总结。

使用标准库HTTP，不用SDK解析参数。外层信封解析保留arguments字符串，既有strict_json随后检查重复键，再作__NULL__映射及原业务解析。保留可识别原参数、调用ID、结束原因、用量、本地请求关联；无法安全解码的信封只记诊断缺口，不保存整段原始错误或Base64。一次完整失败响应兜底方案被自动审批拒绝（可能保存敏感回显），已删除，未绕过该限制。HTTP非成功诊断继续使用既有白名单、限长、安全说明与ID哈希，不记录请求头或凭据。

实际Schema见[result-tool.json](result-tool.json)，逐行传输差异见[prompt-transport.diff](prompt-transport.diff)。业务合同fact-review-simple-v1、目标/目录、来源和答案单元、投影simple-condition-projection-v1.1及政策不改。ToolCatalog只是载体映射，非新Agent/审核阶段；结果函数不执行外部动作。

## 本批实测边界

三次请求未被拒绝，工具名称/数量/结束均符合本地信封要求，原始参数均可回查；但两次参数重复键、一次额外闭合括号，0份通过本地严格JSON。不能把官方文档的保证当成本次已经观察到的保证，服务端如何执行strict的内部原因未知；未尝试替代接口/参数。见[完整结果](report.md)。
