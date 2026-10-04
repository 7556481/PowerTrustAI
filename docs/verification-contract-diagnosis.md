# 审核器契约失败诊断与可观测性修复

本轮仅离线诊断。未读取真实 `.env`、未调用 API、未覆盖任何试运行结果。

## 历史记录与诊断边界

检查 `data/retrieval_local/deepseek/evidence-review-q1-fixed.json` 和同名 Markdown。
主张提取成功，两次 `evidence-verification-v1` 请求分别耗时 27,959 和 21,887 ms，
均服务 succeeded、finish=stop，但结构校验失败。
JSON 的 model_records、嵌入 JSON 轨迹及 Markdown 均未保存两次响应正文；
没有诊断文件引用，verification_output 为空。因此无法重放历史审核响应，
也无法确定当时实际失败字段。模型服务正常返回不代表应用契约满足。

确认的代码问题是：审核解析器用普通 ContractError/ValueError 表达具体失败，
共享包装器只保留 StructuredValidationError 的诊断，其余全部变成
`contract_validation: $: structured_contract_violation`。格式纠正因此收不到实际原因。
这解释了诊断为何丢失，不能证明历史响应具体违反了哪项规则。

## 提示词与契约对照

| 内容 | 原解析器/core 要求 | v1 提示词问题及修复 |
| --- | --- | --- |
| 顶层 | 冻结 ID、整数版本，四个必填键且无额外键 | v2 明确整数类型及复制绑定 |
| 独立 findings | 每个输入主张恰好一次；只用独立证据 | 保持；补充缺证据仍须输出、不增加模型生成字段 |
| checked_dimensions | 五个固定名称的字符串数组，各一次 | v1 没有明确数组形状；v2 明确禁止对象 |
| citation_reviews | 每个原引用的零基整数 index 恰好一次 | v2 明确类型、完整覆盖及原绑定 ID 范围 |
| excerpts | 0..16 个；supported/contradicted 至少一个 | v1 未写 16 上限；v2 与校验一致 |
| quote | 精确唯一匹配，允许紧邻上下文消歧，不能切入英文词内 | v2 明确；证据摘录保持允许非整句，与主张锚点不同 |
| rationale/conditions | 非空字符串/非空字符串数组元素，conditions 可以空数组 | v2 明确类型；不补造缺失适用条件 |
| 核心审核约束 | 不改冻结主张；证据 ID/摘录/原引用/覆盖/交叠对应一致 | 全部保留，未降级 |

响应提示词版本升级为 `evidence-verification-v2-diagnostics`，提供独立判断和原引用
判断的 JSON 形状。判断语义、核验方法标识及 Harness 调度保持不变。

## 具体诊断与纠正

审核解析器逐字段报告 stage、field_path、constraint，例如：

```json
{"stage":"evidence_verification","field_path":"$.findings[0].checked_dimensions","constraint":"expected_array"}
```

原引用替换独立证据 ID 会定位到 `$.citation_reviews[0].excerpts[0].evidence_id`；
改写的引文定位到对应 `.quote`；core 摘录不符定位到 `.excerpts[0].text`。
诊断不回显响应值、未知字段名称或任意服务错误体。

core ContractError 增加兼容的 diagnostic 属性，require 可指定字段路径；
类型校验记录索引路径，审核关键约束与摘录校验保留具体原因。
共享包装器保留异常的结构化诊断，不再覆盖为根路径泛化错误。
格式纠正收到实际 validation_error，仍最多一次且计入实际调用预算。
其他未改造旧解析器的非结构化异常仍有安全兜底；不能据此声称所有组件均有逐字段诊断。

## 私有响应归档

人工入口 `python -m harness.evidence_review_demo` 后续自动归档提取和审核的结构化响应，
路径为 `data/retrieval_local/deepseek/response-diagnostics/response-<随机ID>.json`。
文件包含响应正文、提示词版本、请求序号、是否纠正、返回模型标识、finish、
响应 SHA-256、具体校验错误（合法响应则为空）。每次响应创建新文件，不覆盖。

归档仅允许项目已 Git 忽略的 `data/retrieval_local` 下路径；不保存请求、密钥、
请求头、配置对象或网络错误体。正文可能含私有回答与资料，不能随意公开。
普通 ModelCallRecord、Harness 轨迹、Markdown 只含诊断路径和安全错误，不附完整正文。
直接构造服务时可用 `diagnostic_dir` 显式启用；默认关闭，普通离线模式无需磁盘归档。

归档失败会明确失败并保留已有校验诊断，不再额外请求、不静默吞掉保存错误。
本轮尚未真实调用，因此该目录没有新增真实响应。只有可控模拟测试曾归档至临时子目录，
测试结束移除自己的临时文件。对网络未返回正文、适配层先拒绝的超长/截断响应，不宣称
存在可回放归档；本次归档覆盖已返回到结构化解析层的响应。

## 离线回归与运行方式

新增 `tests/test_verification_diagnostics.py`，明确使用 synthetic_fixture，不能称为历史实际
失败的复现。覆盖字段类型、状态、版本、独立/原引用来源隔离、精确摘录、覆盖、
core 字段路径、具体格式纠正、两次响应归档及逐字离线重放、成功归档、
禁止覆盖、归档失败和路径限制。既有真实性与完整性测试保留。

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

原 fixed JSON SHA-256：
`bc086e34999898962ab1ca9b36300a11cc859a3a5fa4f85db2fb76f577df3b97`。
本轮真实请求数 0，无新付费 token、真实审核结论或整体 pass。

验证结果：使用 `D:\PowerTrustAI\.venv\Scripts\python.exe` 经工具允许的审批机制
运行全部 unittest，**154 项通过**（原 142 项 + 新增 12 项），20.892 秒，退出码 0。
未安装依赖、重建环境或修改权限。fixed JSON 验证后哈希与上文一致，
同名 Markdown 哈希为 `5398d4388467288ac56e54766e242b07e9009b722c907d72962027cbda43943a`，
检查与验证期间未变；旧项目 Git 工作区无变动。
