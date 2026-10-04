# PowerTrustAI 本机辅助审核界面 v1

统一运行入口现为 [prototype-v0.1.md](prototype-v0.1.md)。2026-10-04 收尾：HTTPS来源按结构化URL投影，中文摘要与原始技术详情分开；30次预算早期预检停止后，用户撤销上限，另冻结并完成8请求的真实Revision链路；早期记录保留，详见统一入口。演示与真实结果分别统计。

本轮界面采用 backend 同源静态 HTML/CSS/JavaScript，无前端构建、CDN、Markdown 渲染库或新增结果数据库。任务与人工反馈继续使用现有 API、ApplicationService、OfflineHarness 和运行 SQLite。默认 BM25、固定知识版本、事实审核 schema12、政策和一次修订限制不变。

## 启动与令牌

```powershell
cd D:\PowerTrustAI
# 演示：不读 .env，不调用真实模型或真实检索
& .\.venv\Scripts\python.exe -m backend --demo --port 8765
# 真实：已有服务器配置；提交后会付费
& .\.venv\Scripts\python.exe -m backend --port 8765
```

两种模式均访问 `http://127.0.0.1:8765/`，只启一个服务进程。首次启动通过 `backend/local_access.py` 生成本机令牌，重启复用；服务器配置路径为 `data/runtime_local/access-token`。没有令牌环境变量入口。用户在自己的 PowerShell 中运行以下命令，用记事本本机查看后填写页面，不把内容发送到聊天或打印到日志：

```powershell
notepad.exe D:\PowerTrustAI\data\runtime_local\access-token
```

页面只输入令牌，不加 Bearer。令牌输入框在连接时清空，授权值仅存在 JavaScript 闭包内存；刷新需重填。令牌不写 URL/localStorage/sessionStorage，不出现在截图。DeepSeek 密钥由真实服务入口使用现有绝对项目根 .env 加载器读取，浏览器从不接收。

## 真实支持的交互

- 问答与已有回答审核：问题、已有回答（仅审核模式）、背景、最多十条回答要求、一个可选用户参考文本。参考不冒充官方来源。本界面不构造工程参数，未填写工程上下文时沿用服务语义。
- 提交后展示实际 run_id；查询状态、阶段事件和已保存有效部分结果；不提供百分比。queued/running 持续轮询，终态停止；网络查询失败暂停轮询，显示状态未知并保留最近确认结果。
- 原回答、当前回答和保存版本分别展示；修订动作可展开。业务结论、必需阶段完整性、必需检查是否评估与执行问题分开。
- 逐轮展示独立事实核验、原引用核验、领域模型判断、程序规则与工具。模型 origin、依据类型、原始字段保留；部分 supported 不表示整个回答正确，pass 不是工程安全认证。
- Evidence 回查仍由运行作用域接口授权，展示来源、原文、文件页、提取文本字符区间与质量告警。角色与 retrieval purpose 均保留；提取文本未核对 PDF 视觉原文。
- 人工反馈：确认、反对、待查、说明；按服务端实际保存的回答/finding/version 可选绑定；追加意见及来源，不覆盖模型判断。反馈失败保留输入，不显示保存成功；请求结果未知时先查已有反馈。
- 输入 run_id 或运行列表恢复查看。列表同时显示记录自身的 real/synthetic_fixture，不能把当前服务模式当作历史运行模式。

## 必要薄适配与安全边界

`GET /` 和 allowlist `GET /ui/{asset}` 提供页面；`GET /runs/page/{offset}` 受已有 Bearer 保护，固定每页20条，仅返回 ID、状态、时间、模式、profile，不返回输入或私有配置。使用路径分页以保留原“不接受 query 参数”规则。`feedback_targets` 是已有运行对象的精确关联投影；`original_citations` 补充未完成轮次的原引用结果。

所有动态内容使用 textContent/createElement，原文纯文本，不执行模型/证据/反馈 HTML。页面 CSP 限同源脚本、样式与连接，禁 inline 脚本、frame、外部加载；no-store、nosniff、no-referrer、DENY frame。POST 有 Origin 时必须严格同源；无 Origin 的授权本机客户端沿用原行为，不新增宽泛 CORS。Swagger 保持原框架页面，不沿用会阻断其脚本的界面 CSP。

服务保持验证和状态权威。401（令牌）、409（版本关联）、429（队列满）、422（输入）、503（缺配置/服务/存储）分别说明。重复点击在请求期间锁定；超时不自动重发 POST。若任务 POST 结果未知，再次提交锁定，用户重新连接后核对运行列表再决定。每次提交前查询实际服务模式，模式变化时停止本次提交并要求手动核对，避免演示页面连接变更后的真实服务时意外付费。

取消先显示已请求，等待实际终态；底层远程请求/线程不保证强制终止。无幂等键，用户主动再次提交仍是新运行。网络失败后无法凭空恢复未知 run_id，需通过受保护列表核对时间与模式。分页为 offset 形式，新提交可能移动页边界，恢复任务以精确 ID 为准。

结果投影修正：当前 v2 正在重审时，不能用 v1 的已完成 review_round 标记“必需阶段完整”。只调整展示完整性，未改政策、提示或运行调度。

## 验证与私有材料

普通测试用假组件，无 .env/付费模型请求：

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& 'C:\Users\37307\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' tests/ui_client_checks.js
```

`tests/test_local_ui.py` 覆盖页面和作用域安全、分页、旧回答版本反馈以及当前版本未完成重审。`tests/ui_client_checks.js` 使用真实客户端代码与最小 DOM double 检查重复提交、网络未知、409保留输入、401/429/422/503和字面文本；它不是浏览器验证的替代品。

`tests/ui_demo_scenarios.py` 在服务停止时使用现有运行库和现有假组件创建7条明确 synthetic_fixture 记录：v1/v2 修订、同级有效部分、取消、执行失败、恶意文本、活动中断、排队中断。它不重跑历史实验，不含真实模型组件；需避免重复覆盖其私有报告。浏览器实际验证可以另注入带延时假组件，不把其结果归为模型表现。

验证材料逐项更新至 `data/runtime_local/ui-v1-*`；原始真实消息/响应继续由既有组件保存至 `data/retrieval_local/service_private/{run_id}`。这些材料全部 Git 忽略，无密钥/令牌/请求头。真实两场景冻结计划与验证记录在 `data/runtime_local/ui-v1-real-validation/`。测试、浏览器与真实运行结果必须分别报告，未完成项不能称已验证。

最终中文《PowerTrustAI 项目学习与面试手册》仍未编写；此文仅是本轮界面运行说明和后续素材，不能替代最终手册。

## 本轮实际验证结果与修改职责

421项离线测试通过（57.127秒），Node客户端检查及pip check通过。实际内置浏览器通过两模式、v1/v2、排队/运行/结束/失败/中断、运行中有效同级结果、两种取消、Evidence回查、追加反馈、401、GET断开状态未知和字面HTML安全检查。浏览器使用既有假组件注入3/30/90秒延迟，零真实模型请求；14条新增synthetic_fixture记录与真实结果分开。反馈错误版本409和POST未知不重发由离线HTTP/DOM double验证，未在浏览器伪造这些错误。

| 文件 | 本轮职责 |
|---|---|
| `backend/static/index.html` | 中文表单、模式/历史/状态/回答/发现/证据/反馈布局 |
| `backend/static/style.css` | 本机演示视觉、窄窗口响应式与可读原文 |
| `backend/static/app.js` | 内存令牌、输入验证、单次POST、未知锁定、轮询、文本渲染、版本绑定、恢复/反馈 |
| `backend/api.py` | 页面/资产allowlist、CSP等安全头、POST同源、受保护分页 |
| `backend/store.py` | 复用原运行表的分页摘要，无schema/数据库新增 |
| `backend/service.py` | 反馈目标/原引用薄投影、当前版本阶段完整性修正 |
| `backend/assembly.py` | 原manifest新增静态资产哈希；真实装配仍schema12 |
| `tests/test_local_ui.py`、`tests/ui_client_checks.js` | 4项API回归与客户端错误/安全行为检查 |
| `tests/ui_demo_scenarios.py`、`tests/ui_real_validation.py` | 显式演示场景准备、授权真实冻结/只读HTTP归档，不加入生产调度 |
| `docs/handoff.md`、`documentation-index.md`、`design-decisions.md`、`local-review-service-v1.md`、本文 | 当前状态、素材、取舍、运行说明与真实失败边界 |

两个真实场景均从页面提交，通过实际API/真实装配，默认BM25、固定知识版本、schema12不变。两个结果均在页面查看和Evidence回查；全部25条Evidence经只读API回查文本一致，第二运行新增一条来源明确的AI辅助待查反馈。进程重启后两个结果和最新反馈逐字段相等，没有模型重发。

| 真实场景 | 生成 | 提取 | 独立事实核验/纠正/原引用 | 领域 | Revision | 实际请求 | 结果 |
|---|---:|---:|---|---:|---:|---:|---|
| 问答 `8f378eec606e4808b7319c6c8d4e274f` | 1 | 1 | 1 / 1 / 1 | 1 | 0 | 6 | finished、v1、review_required |
| 已有回答 `c08a5ddcae4a46148a2a512100148731` | 0 | 1 | 1 / 0 / 0（无原引用） | 1 | 0 | 3 | finished、v1、review_required |

两者必需阶段完整，但必需检查未全评估：缺工程上下文/单位输入、无已验证工程仿真。事实部分supported不消除这些限制。本轮没有触发真实Revision，不把演示v2分支称为真实模型修订验证。

问答首次事实响应的`$.findings[4].component_reviews[0].basis_indexes`越界，`existing_integer_basis_indexes_required`失败和同级保留证据均归档，一次纠正后结构通过。原引用supported仍保留`independent_support_uses_unbound_evidence_not_original_citation_support`告警，不等于所有依据关系已由人工确认。未修协议或重跑来追求pass。

总输入129886/输出4545/total134431 tokens，cache hit38784/miss91102，9请求全部有用量。问答USD0.011996604–0.023993208、已有回答USD0.004512048–0.009024096，合计USD0.016508652–0.033017304；依据2026-10-04核对的[DeepSeek官方价格](https://api-docs.deepseek.com/quick_start/pricing/)，保留高低费率估算范围，非提供商账单。冻结计划保留既有40/运行预算、合计80硬上界和40内目标；实际9，没有提额或重跑。

已知问题：既有safe序列化把部分官方HTTPS来源URI误识别为Windows路径而隐藏；源ID、版本、页码、正文仍回查。为保持本批冻结源码未临时改投影；下一步建议独立修该误判，并明确`partial_only=false`只代表已存终态结果而不代表检查完整。界面首版仅纯文本、无文件上传/多用户/任意路径输入；known模型语义局限和PDF视觉核对缺口仍保留。

当前真实服务在127.0.0.1:8765运行、队列空；不再提交新模型任务。截图在`data/runtime_local/ui-v1-screenshots/`，已检查无令牌、密钥或敏感本机路径；API/浏览器/重启证据见文档索引。
