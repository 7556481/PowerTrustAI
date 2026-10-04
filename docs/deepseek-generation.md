# DeepSeek 官方连接与仅生成试运行

## 实现与当前结果

2026-10-02：使用项目 `.venv`（Python 3.13.2）运行全部 100 项测试通过（26.539 秒，退出码 0），保留原有 89 项，新增 11 项连接器模拟测试。普通测试不读取真实密钥、不调用付费 API。未安装依赖，旧项目、BM25、PDF 切分及审核调度未改。

检查当前进程及当前用户范围的 **DEEPSEEK_API_KEY 是否存在**，两者均为 false；未输出值、未枚举其他凭据。实际运行官方资料入口在配置检查阶段退出，没有发起远程请求；另以连接专用入口核实 Python 原生退出码为 2，报错 `DeepSeek configuration missing/invalid; no remote requests made`。真实连接测试及五问尚未完成，没有真实回答、token 用量或实测费用；模拟测试不能替代这些结果。配置失败记录保存在被 Git 忽略的 `data/retrieval_local/deepseek/official-trial.json`。

另用同一项目解释器的 `-S` 模式验证无第三方 site-packages：100 项中 81 项通过、19 项可选 PDF 相关测试跳过（17.444 秒，退出码 0）。项目解释器启动经工具允许的审批机制执行，未改变权限或重建环境。旧项目 Git 工作区检查为空。

| 文件 | 职责 |
| --- | --- |
| `model_adapter/deepseek.py` | 官方 HTTPS 连接、JSON 模式、状态码映射、返回用量与价格快照 |
| `model_adapter/contracts.py` | 扩展错误分类、缓存 token 用量、独立费用估算记录，兼容已有默认值 |
| `model_adapter/runtime.py` | 复用实际调用预算和安全错误边界，保存服务用量及独立费用估算 |
| `harness/generation_demo.py` | 增加逐题保存回调及服务失败停止选项，默认行为兼容 |
| `harness/deepseek_trial.py` | 一次短连接测试后执行既有五问、逐题保存；复用 Generation Agent 与 Harness |
| `tests/test_deepseek.py` | 模拟 HTTP 状态、请求参数、预算、超时、成本与仅生成链路 |
| `docs/config/deepseek.example.json` | 不含密钥的配置参考，不自动读取 |

## 官方协议与价格快照

以实际读取的官方文档为准，核实日期为 **2026-10-02**。当前模型列表包含 `deepseek-flash`（DeepSeek-V4.1-Flash）和 `deepseek-v4-pro`（DeepSeek-V4-Pro）。模型 ID 由 CLI 或 DEEPSEEK_MODEL_ID 传入，生成业务逻辑没有固定某个模型。服务实际返回的模型标识另行保存。[官方模型列表](https://api-docs.deepseek.com/api/list-models/)

连接为 `POST https://api.deepseek.com/chat/completions`，非流式，传入 `max_tokens`、`response_format: {"type":"json_object"}`，提示词包含 JSON 要求与输出结构。显式 `thinking: {"type":"disabled"}`，避免依赖默认思考设置。JSON 模式可能返回空内容，也不能保证 ID、版本或字符区间正确；仍通过既有严格解析器校验，最多一次格式纠正。[Chat API](https://api-docs.deepseek.com/api/create-chat-completion/)、[JSON 输出](https://api-docs.deepseek.com/guides/json_mode/)、[思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)

单位为 USD / 百万 token，以下为价格快照，不是账单：

| 模型 | 高峰输入缓存命中 | 高峰输入缓存未命中 | 高峰输出 | 非高峰 |
| --- | ---: | ---: | ---: | --- |
| deepseek-flash | 0.006 | 0.30 | 1.20 | 高峰价格的 50% |
| deepseek-v4-pro | 0.044 | 1.32 | 3.96 | 高峰价格的 50% |

官方高峰时段为周一至周五 UTC 01–04、06–10，排除中国公共假日，其余为非高峰。实现不自行判断一次请求最终适用哪个账单时段，因此保存非高峰至高峰的费用区间。仅当服务返回输入、缓存命中/未命中和输出 token 且计数一致时估算；未知模型或缺失字段标记 unavailable。服务未返回的 cost 不补造；估算另存 cost_estimate，汇总明确排除未知费用，并记录价格日期。价格可能变化，正式实验前需重新核对。[官方价格](https://api-docs.deepseek.com/quick_start/pricing/)

## 本机配置

DeepSeek 专用入口现在自动读取由 `harness/deepseek_trial.py` 的绝对路径确定的项目根目录 `.env`，不根据当前工作目录查找。无需安装 dotenv 依赖，也不影响普通离线导入。已有环境变量优先（包括已存在的空值），CLI `--model-id` 优先于环境中的模型 ID。

在本机将根目录 `.env.example` 复制为 `.env`，自行填入真实密钥；示例的密钥字段为空。`.gitignore` 继续忽略 `.env` 和 `.env.*`，只允许根目录 `.env.example` 提交。不要把真实密钥填进示例或发送到聊天中。

```text
DEEPSEEK_API_KEY=在本机填写
DEEPSEEK_MODEL_ID=deepseek-flash
```

只支持 UTF-8（可含 BOM）、空行、整行 `#` 注释和单行 `KEY=VALUE`。键符合环境变量标识符格式；值两端空白会去除，可用成对单/双引号包围。其余内容保持字面值，包括 `=`、`#`、`$()` 和 `${...}`；不执行、不插值、不解析转义、不支持 export 或多行值。重复键取第一项。无文件时继续使用原环境配置；读取失败或语法无效时安全报错，不输出值、不部分加载。

新增测试仅使用临时 `.env` 和虚构密钥，覆盖环境优先级、与工作目录无关、字面值、缺失/无效文件及 CLI 加载顺序。本次没有读取用户真实 `.env`，没有调用付费 API。

本次使用项目 `D:\PowerTrustAI\.venv\Scripts\python.exe` 执行 `-X utf8 -m unittest discover -q`：全部 **104 项通过**（20.138 秒，退出码 0），保留原有 100 项，新增 4 项 `.env` 测试；未安装依赖。

此连接器仅接受官方域名及可选 `/v1` 路径，只从 `DEEPSEEK_API_KEY` 取凭据。若充值的是第三方平台，需先确认该平台的 endpoint、模型 ID、鉴权和价格；当前连接器明确拒绝第三方 URL，不会把官方密钥发送给第三方。

在本机 PowerShell 中安全输入，**不要将密钥发送到聊天或写入下面的示例文件**：

```powershell
$secret = Read-Host 'DeepSeek API key (local only)' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
Remove-Variable secret
$env:DEEPSEEK_MODEL_ID = 'deepseek-flash'
```

上述环境变量只对该 PowerShell 及其子进程有效。在此窗口执行下方命令即可；不会自动传给已启动的 Codex/VS Code。若通过 Windows 用户环境变量界面设置，请重新启动需要继承配置的应用。无需激活、重建 `.venv`。不使用明文命令参数或日志保存密钥；也可以使用上述被忽略的本机 `.env`。

配置参考见 `docs/config/deepseek.example.json`，只展示非敏感设置。CLI 不自动加载该 JSON；参数和环境变量是实际配置入口。

## 一次连接测试后五问

从项目根目录运行这一个入口；它已经包含短连接测试，不需要先运行另一个入口重复测试：

本机 `.env` 填好后，下面命令无需手动设置密钥或模型环境变量。

```powershell
$py = 'D:\PowerTrustAI\.venv\Scripts\python.exe'
$comparison = Get-Content data/retrieval_local/pdf-quality/comparison.json -Raw -Encoding UTF8 | ConvertFrom-Json
$kv = $comparison.documents[0].derived.knowledge_version
$db = 'data/retrieval_local/pdf-quality/nerc-reactive-planning-2016.sqlite3'
& $py -X utf8 -m harness.deepseek_trial --db $db --knowledge-version $kv --output data/retrieval_local/deepseek/official-trial.json
$LASTEXITCODE
```

短测试最大输出 48 token；草稿默认最大输出 1800 token，可用 `--draft-max-tokens` 配置。单次模型等待默认 45 秒（`--model-timeout`）；每题原 Harness 总时限 180 秒。固定知识版本贯穿五问。最多一次连接请求、五次初始生成、每题一次格式纠正，总计最多 11 次 POST；格式纠正计入每题原有两个调用槽。空证据的确定性不足回答可能不调用模型。需要只检查连接时可单独使用 `--connection-only`，它不会生成五问。

五问复用既有问题集：dynamic reactive reserve/STATCOM、QV 局限、generator capability、正常母线电压是否足以证明电压稳定、中国某省/某电厂现行限值的覆盖不足。服务故障会停止后续题目；无效结构最多纠正一次，不进行第三次请求。CLI 不自动回退为模拟模型或其他模型。

逐题 JSON 保留实际模型 ID、提示词版本、耗时、服务 token、结束原因、回答、Evidence、质量告警、引用字符区间与原文定位、固定知识版本及 Harness 轨迹。输出只允许保存在被 Git 忽略的 data/retrieval_local；遵循原官方资料再分发约束。真实回答即使结构有效，最终也仅为 **generated**、report=null，没有事实核验或领域审核 pass。

## 错误与取消限制

| 情况 | 记录代码 |
| --- | --- |
| 本机缺失/无效配置 | 在发请求前退出；配置记录 remote_requests=0 |
| 网络连接失败 | MODEL_CONNECTION_FAILED |
| 401 / 403 鉴权失败 | MODEL_AUTHENTICATION_FAILED |
| 402 余额不足 | MODEL_INSUFFICIENT_BALANCE |
| 429 限流 | MODEL_RATE_LIMITED |
| 400 / 422 / 其他非成功状态 | MODEL_REQUEST_REJECTED |
| 5xx 服务异常 | MODEL_SERVICE_UNAVAILABLE |
| 请求超时 | MODEL_TIMEOUT；更短的 Harness 超时另记 TIMEOUT |
| 无效 envelope / 正文结构 / 超长输出 | MODEL_OUTPUT_ERROR 或现有生成结构错误 |
| 调用预算不足 | MODEL_CALL_BUDGET_EXHAUSTED |

状态含义依据[官方错误说明](https://api-docs.deepseek.com/quick_start/error_codes/)。不转发服务错误 body、异常原文或 Authorization 头。没有 SDK、隐式重试、重定向、备用模型或自动重连；每次 complete 至多一个 POST。

同步 HTTPS 在单工作线程运行，不阻塞异步调度。超时取消等待者不能强制杀死该线程；未结束的请求仍可能收费，且实际 token 暂时未知。线程忙时拒绝新请求，不无限排队。socket 超时限制底层阻塞操作，但不是强制进程终止保证；close(wait=False) 也不能中止正在执行的 HTTP。没有实际连接前，TLS、网络可达性、账号权限及真实模型行为仍未验证。

## 验证命令与复核范围

```powershell
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -X utf8 -m unittest tests.test_deepseek -v
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -X utf8 -m unittest discover -v
```

新增模拟测试覆盖请求参数/可配置模型、401/402/429/5xx 等分类、不重试和敏感错误隔离、未知用量、无效响应、缓存价格计算、超时后线程仍忙、一次短测试失败即停止，以及五题各最多一次纠正、引用回查、仅 generated 的完整程序集成。这不能证明真实模型抗资料指令注入或事实正确。真实运行后仍需人工核对引用支持关系、否定和限定条件、地区时效与 PDF 质量告警。
