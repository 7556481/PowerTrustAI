# Generation Agent 与可替换模型边界

后续状态（2026-10-02）：已实现 DeepSeek 官方连接器及 11 项模拟测试，完整回归增至 100 项通过。当前本机未配置 DEEPSEEK_API_KEY，真实试运行未完成。下文的“没有供应商连接器”描述的是上一阶段状态；当前配置、价格快照、运行入口与错误映射以 [deepseek-generation.md](deepseek-generation.md) 为准。

再后续状态：已存在保存的真实五问生成记录，本轮保留该记录不重跑。新生成提示词改为 `evidence-bound-generation-v2-exact-quotes`，模型返回精确 quote（可附消歧 prefix/suffix），程序生成 CitationBinding 字符偏移；下文 v1 及模型直接计数描述仅代表旧实现。新主张提取与局部证据核验见 [evidence-verification.md](evidence-verification.md)。

本轮实现“问题 → 原 Retriever → 结构化回答草稿 → 原文回查引用”的程序链路。未安装依赖，未优化 BM25，未修改旧项目，没有真实审核、修订或仿真。

## 配置检查与真实运行状态

2026-10-02 检查项目根目录、当前框架源代码中的模型配置/连接引用，以及旧项目唯一相关的 `app.py` 模型加载代码。未发现当前框架可用的生成服务地址、模型标识或供应商适配器配置。旧项目使用 Hugging Face 的 NLI sequence classification，不是生成服务。未读取个人全局配置、无关配置文件或枚举环境变量；凭据相关行没有输出。

因此按用户要求，先实现可替换接口与模拟测试。**没有实现或选定某供应商的 HTTP/SDK 连接器，没有猜测 URL、模型或凭据。真实五问试运行尚未完成。** 实际执行官方索引 `--official-five` 无配置命令，CLI 明确返回退出码 2：`No generation service configured ... real trial not completed`。没有外部模型请求，也没有用模拟五问结果替代。

启动真实试运行最少需要：

1. 明确服务/API 协议或本地模型运行方式，以实现/指定对应适配器工厂 `module:factory(settings)`；工厂只构造适配器，不发起隐藏生成请求。
2. 准确模型 ID；远程服务的准确 endpoint（若需要），不得含凭据。
3. 鉴权方式和保存凭据的环境变量名称；匿名/本地服务可以不需要。通过安全的环境设置提供值，不把值贴进命令、项目文件、日志或测试。
4. 确认单次输出 token 上限、请求时间限制及调用预算。CLI 默认每题最多 2 次模型请求，最多一次格式纠正；五问最多 10 次，不保证每题都会发生调用。

有这些资料后再实现该协议的适配器。当前没有可直接调用真实服务的内置供应商工厂；接口不能被描述成已验证真实服务连接。

## 实现文件

| 文件 | 职责 |
| --- | --- |
| `model_adapter/contracts.py` | ModelAdapter.complete 接口、设置、文本请求/响应、服务用量、模型请求记录和错误分类 |
| `model_adapter/runtime.py` | 超时、输出限制、显式凭据环境变量读取辅助函数、请求预算和安全错误边界 |
| `model_adapter/fixtures.py` | 明确标为 synthetic_fixture 的模拟适配器，不代表真实回答能力 |
| `agents/generation.py` | 证据提示词、严格 JSON 解析、AnswerDraft/CitationBinding 校验、最多一次格式纠正 |
| `agents/contracts.py` | GenerationInput 增加回答要求；GenerationOutput 增加证据充分性自报、提示词版本和请求记录，默认兼容 |
| `harness/runtime.py`、`contracts.py`、`states.py` | 在原 Harness 增加 generation_only 和 generated 终态；共享实际模型调用预算和轨迹，不新增调度器 |
| `harness/generation_demo.py` | 检索后仅生成的 CLI、五问入口、引用原文对应关系、模拟/配置模型标记 |
| `tests/test_generation.py` | 模拟服务输出及真实 SQLite/BM25 的程序集成测试 |

GenerationOutput.answer 仍使用既有 AnswerDraft；引用仍使用既有 Evidence ID 和回答字符区间。没有另建 Evidence 或回答模型。GenerationInput.answer_requirements 接收显式回答要求。没有语义审核器、Planner、流式输出、工具调用或通用模型平台。

## 提示词与输出约束

提示词版本为 `evidence-bound-generation-v1`。系统消息只包含固定生成规则；用户问题、回答要求和上下文放在单独的用户 JSON；检索原文和来源标记放在 `DOCUMENT_DATA_UNTRUSTED` 用户 JSON。资料中的“忽略规则”、伪造 system 标签、分隔符等只保留为资料数据，不升级为系统要求。无凭据、endpoint 或模型客户端配置进入提示词。

模型返回一个严格 JSON 对象：answer_id、version、text、citations、assumptions、missing_information、evidence_sufficient。正文、假设和缺失信息进入 AnswerDraft；证据充分性为模型自报，不能当成审核结论。answer_id 固定为 task_id + `-answer`，首次版本只能为整数 1。

引用是正文的 Python Unicode 字符半开区间 `[start_offset,end_offset)`，只能包含输入 Evidence ID。使用已有 validate_answer 检查范围、类型、版本和 ID 引用；拒绝重复 JSON key、多余字段、错误类型、未知 ID、空支持引用和越界区间。不接受 Markdown 代码围栏，不自动推断引用、偏移或页码。页码/原文由索引 Evidence 提供，不信任模型自行编造的来源字段。

输入没有任何证据时，确定性返回明确不足的草稿和缺失信息，不调用模型、不创造引用。资料存在但覆盖不足时，提示模型明确说明不足并填 missing_information；解析器要求不足标记有缺失信息，但无法语义验证模型确实识别了不足。真实模型可能把不相关命中误当支持，本轮没有 NLI 或领域审核。

格式错误最多纠正一次。把错误响应作为低优先级、明确不可信的纠正数据传回同一模型，保持原系统要求和原证据不变。记录初次 `invalid_structure` 和纠正后的状态；没有第三次请求，没有静默本地补造引用，也没有审核记录可被改写。连接失败、限流、超时、输出截断和输出长度超限不触发自动重试。

## 调用预算、超时与记录

真实生成 Agent 标记 uses_model_adapter，Harness 不再将一次 Agent 调用当成一次模型请求；ModelClient 在每个实际请求前向本次运行预算预留调用，格式纠正也预留。一次初始请求加一次纠正消耗 2 次；预算只剩 1 次时，第二次不会发出。纯离线假 Agent 保持原来的调用槽计数以兼容旧测试；混合程序测试也验证两次格式请求会消耗原 Harness 两个槽。

ModelSettings 提供单次 timeout_seconds、max_output_tokens 和独立 max_response_chars。token 上限传给显式适配器；有服务返回 output_tokens 时检查超限，finish_reason 为 length/max_tokens 则拒绝截断输出。未知 token 使用量时不会用字符数估计 token；字符帽只限制响应大小，不声称等于 token 限制。适配器必须真正传递供应商输出限制、实现非阻塞 complete 和底层传输超时。

记录每次请求的配置模型 ID、服务返回模型 ID（若有）、提示词版本、调用序号、是否格式纠正、耗时、执行状态、输出结构状态、服务 token/cost 使用量和结束原因。未提供的字段保留 null，表示未知；不计算供应商价格，不推算账单。错误/取消尝试也计入实际调用预算，不能把无法取得用量当成零消费。

| 错误类别 | 代码 |
| --- | --- |
| 连接/未分类服务失败 | MODEL_CONNECTION_FAILED |
| 适配层超时 | MODEL_TIMEOUT |
| 限流 | MODEL_RATE_LIMITED |
| 无效输出或超限 | MODEL_OUTPUT_ERROR |
| 请求预算耗尽 | MODEL_CALL_BUDGET_EXHAUSTED |
| 外层 Harness 更短的步骤超时 | TIMEOUT，内部请求可能记录 cancelled |

供应商适配器须将协议/SDK 的连接、429 和超时异常转换成对应类型；当前只用模拟异常验证这些边界，没有验证真实 HTTP 状态映射。未经分类的异常消息可能含敏感信息，ModelClient 不把原始异常字符串、请求头或返回 body 放进记录。模型响应正文和原证据只在用户要求的草稿/本地引用文件中保留；配置凭据不进入日志、Git、报告或测试样例。

超时仍是合作式异步取消。不能强制终止忽略取消的供应商客户端、同步 SDK 或线程；本轮没有进程隔离或硬终止保证。Harness 总时限涵盖检索和模型等待，但 CLI 序列化不属于模型生成工作。

## 仅生成 CLI

`generation_only=True` 只执行既有 Harness 的检索和生成阶段，终态为 generated。result.answer / generation_output 提供草稿和模型记录，report 为 null；不提取审核主张，不调用两类审核或 Revision，没有 pass 决策。generated 表示草稿生成，不表示可信审核通过。CLI 默认不会自动退回模拟模型。

从项目根目录运行：

```powershell
$py = 'D:\PowerTrustAI\.venv\Scripts\python.exe'
$trial = Get-Content data/retrieval_local/pdf-quality/comparison.json -Raw -Encoding UTF8 | ConvertFrom-Json
$kv = $trial.documents[0].derived.knowledge_version
$db = 'data/retrieval_local/pdf-quality/nerc-reactive-planning-2016.sqlite3'

# 当前无配置：明确拒绝，退出码 2，没有生成真实答案
& $py -X utf8 -m harness.generation_demo --db $db --knowledge-version $kv --official-five

# 在获得配置并实现对应工厂后运行；以下变量须由用户显式提供，没有默认值
& $py -X utf8 -m harness.generation_demo --db $db --knowledge-version $kv --adapter-factory $adapterFactory --model-id $modelId --endpoint $endpoint --credential-env $credentialEnvironmentName --official-five --output data/retrieval_local/generation/official-five.json

& $py -m unittest tests.test_generation -v
& $py -m unittest discover -v
```

五问固定包含：dynamic reactive reserve/STATCOM 短时过载、QV 局限、同步发电机能力条件、正常母线电压是否足以证明电压稳定，以及中国某省/某电厂现行强制限值的资料覆盖不足。最后一问用于检查不足说明，不能因为检索有命中就声称找到了中国规范。真实五问目前全部待运行。

`--question` 与 `--official-five` 二选一；`--requirement` 可重复指定回答要求。若只验证程序，可显式加 `--simulate-fixture`，不与真实配置混用，输出 SIMULATED_MODEL_INTEGRATION_ONLY、real_trial=false。该模拟仅引用输入 ID 并生成测试文字，绝不能替代真实答案。

CLI 展示正文、引用区间、Evidence ID、来源页码/定位、适用地区和质量告警。完整 UTF-8 JSON 保存每题实际 Evidence、模型请求元数据、完整 Harness 轨迹，以及 citation_map 中回答文字与对应英文原文。所有保存仍限制在被 Git 忽略的 data/retrieval_local；原文件再分发规则不变。null 用量/费用不是零消费。

## 验证与限制

使用项目 `D:\PowerTrustAI\.venv\Scripts\python.exe`（Python 3.13.2）验证，经工具审批处理沙箱启动限制；没有重建环境或修改权限：

- 新增 15 项生成测试通过（1.475 秒）。
- 完整回归 89 项通过（18.238 秒、退出码 0），保留原有 74 项。
- `-S` 模式回归 71 项中 70 项通过、1 项可选 PDF 样例跳过（11.809 秒、退出码 0）。
- 无配置的官方五问 CLI 退出码 2，没有外部模型请求、没有真实答案输出。
- 本地 synthetic_fixture CLI 保存/展示测试退出码 0，生成终态 generated，report=null，1 个模拟请求，usage=null；原文引用对照保存为 `data/retrieval_local/generation/synthetic-demo.json`，明确 `real_trial=false`。

模拟测试验证正常输出、无证据、资料不足、未知引用、无效区间/版本/结构、重复 JSON key、Unicode 偏移、一次纠正与上限、适配层及 Harness 超时、限流/连接错误、实际调用预算、输出长度、未知使用量、安全错误边界、提示词资料注入，以及真实索引到模拟模型的引用回查。注入测试只证明程序的消息边界和拒绝未知引用，不能证明真实模型抗提示词注入能力。

没有真实服务调用，所以没有实测真实 token、费用或真实回答质量。无证据的确定性不足说明也不是一次真实模型回答。下一步需要用户提供最少服务配置，实现并验证指定协议的适配器，再运行五问并逐条人工核对：引用是否真正支持句子、否定/限定条件是否保留、地区与时效性是否正确、公式表格等告警是否被说明。结构校验和可回查引用不等于事实正确。
