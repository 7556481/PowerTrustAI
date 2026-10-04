# PowerTrustAI 会话交接

更新：2026-10-04。本机辅助审核界面 v1 已完成，并按用户本轮授权完成两个真实 API 运行，共9次模型请求。当前真实服务在127.0.0.1:8765运行，队列空，不再提交新模型任务。阅读入口见 [文档索引](documentation-index.md)，设计依据见 [设计决策](design-decisions.md)。

## 本轮：本机辅助审核界面 v1

- 用户指定五份文档及design-decisions均存在，已读；检查Git状态与API实际响应。项目仍整体未跟踪，无add/commit/push，旧仓库仍忽略。未重跑历史实验，未编写最终手册。
- 同源纯HTML/CSS/JavaScript：两模式提交、状态/阶段/取消、有效部分结果、原/当前/历史回答、逐轮事实与原引用审核、领域模型/程序规则/工具、Evidence回查、精确版本/finding人工反馈。无新Harness、政策或数据库。令牌用户输入，仅页面内存，连接后清空输入框。
- 薄适配：受保护路径分页 `/runs/page/{offset}`，每页20条摘要；结果新增 `feedback_targets` 与 `findings.original_citations`。修正v2正在重审却沿用v1标完整的展示投影，未改政策。静态allowlist、页面CSP、无缓存、POST同源Origin检查，保留Bearer与作用域。
- 最新421项离线测试通过，57.127秒；Node客户端检查、pip check通过。沙箱拒绝解释器启动后按AGENTS使用工具审批，未重建环境/改权限。进程元信息Get-CimInstance被拒，改用既有启动记录与health确认；未读取凭据内容。
- 实际内置浏览器验证两提交模式、双击只建一任务、v1/v2、运行中同级有效部分、排队/429、活动与排队取消、失败/中断恢复、Evidence回查、反馈、401、GET断开显示未知、恶意HTML文字。POST未知锁定与反馈409保留输入由离线客户端/HTTP测试验证，未在浏览器伪造版本或拦截真实请求。刷新无令牌页后提交禁用，授权主页面通过run_id恢复真实结果。
- 新增14条明确synthetic_fixture记录（7条离线演示场景、7条浏览器任务），模型请求0，不用于模型质量指标。历史记录未覆盖。两个真实运行均由浏览器POST `/runs` 经真实装配执行；固定知识版本、默认BM25/schema12不变，无evaluation CLI付费运行。
- 问答 `8f378eec606e4808b7319c6c8d4e274f`：生成1、提取1、领域1、事实3（独立初始+一次格式纠正+原引用），合计6；已有回答 `c08a5ddcae4a46148a2a512100148731`：提取1、领域1、事实1，合计3。均v1、无Revision，finished / review_required；阶段完整、必需检查未全评估。后者无原citation，不伪称完成原引用审核；真实Revision分支本轮未触发。
- 两真实结果均在浏览器查看并Evidence回查；全部25条Evidence经只读API回查一致。第二次追加1条AI辅助、用户监督待查意见，非专家标签。重启后两结果及最新反馈逐字段相等，模型记录仍6/3，无自动重发，health模型请求0。
- 总输入129886、输出4545、total134431 tokens，cache hit38784/miss91102；9条记录全部有用量及费用估算。按2026-10-04官方价核对，约USD0.016508652–0.033017304，非账单。冻结原每运行40请求上界（合计硬上界80、实际目标40内），没有提额。
- 真实失败保留：问答初始事实核验 `$.findings[4].component_reviews[0].basis_indexes` 违反 `existing_integer_basis_indexes_required`，一次纠正后通过，同级有效条目保留。原引用虽supported仍保留 `independent_support_uses_unbound_evidence_not_original_citation_support` 告警，不以它证明忠实支持或安全。程序规则保留engineering_context、unit_check_incomplete、executed_and_validated_engineering_analysis缺失。
- 既有safe投影会把部分官方https来源URI误识别为Windows路径并隐藏；源ID/版本/页/原文仍可回查，本轮未在冻结批次中修改序列化或重跑，后续应单独修复。`partial_only=false`仅表示有终态存档，不代表全部检查完整。

运行说明：[local-review-ui-v1.md](local-review-ui-v1.md)。私有证据在 `data/runtime_local/ui-v1-*`：离线日志、客户端检查、演示场景、浏览器检查、delivery、screenshots及real-validation下冻结计划/两run JSON/重启前后对照。原始消息/响应仍在 `data/retrieval_local/service_private/{run_id}`，均Git忽略，无密钥/令牌/请求头。最终手册要求继续保留，这些素材不可替代手册。

以下服务v1初交付的验证和交接记录保留为阶段背景；涉及“尚无界面/真实API验证”的描述以本轮上节为准。

## 目标与实际架构

面向电力系统 LLM 的可信增强原型：可追溯 RAG、独立事实与领域审核、有限修订、预算控制及人工复核。目前不是工程安全认证系统。

`backend.api → ApplicationService → ComponentFactory → OfflineHarness`。Harness 调用 Generation、Evidence Verification、Power Domain Review、Revision 四 Agent；ClaimExtractor 是服务，单位换算是工具。问题生成或已有回答 → 冻结回答/共享主张 → 独立双审核 → 原政策决策 → 必要时一次修订 → 完整重提取和双重审。SQLite 知识库是证据权威；运行 SQLite 独立保存阶段、对象、预算与追加反馈。服务没有依赖 evaluation 实验 CLI。

## 当前完成范围与装配

- Markdown、文本型 PDF、版本化 SQLite、BM25、Evidence 回查及独立相邻上下文已实现。PDF 区间对应提取文本，不承诺等于视觉原文；无 OCR/可靠公式表格理解。
- Dense/RRF 和可选 reranker 已实现为检索/实验能力；**当前真实服务默认 BM25**，保持原 RetrievalSettings 和 `storage_order` 上下文。不采用术语扩展默认切换、reranker 或 `cross_page_next_first`。
- DeepSeek 适配、程序绑定生成引用、真实提取/双审核/有限修订、SI 标量工具已实现；领域规则仍是演示规则，没有仿真。
- 本机 HTTP：提交后202；单活动运行、有限等待队列（默认2）；查询状态/结果/轨迹/证据，取消及追加人工反馈。仅127.0.0.1、单进程、本地 Bearer 令牌，无宽泛 CORS。
- 真实配置缺失明确报错，不回退假 Agent；`--demo` 是显式 synthetic_fixture，零真实检索/模型。

实际配置权威为 `backend/config.py`、`backend/assembly.py`，不可从旧实验文档复制默认值。

| 组件 | 当前真实装配 |
|---|---|
| Generation | schema3；evidence-bound-generation-v3-answer-units / generation-output-v3 |
| ClaimExtractor | protocol7；atomic-claims-v7-obligations / atomic-claims-v7 |
| Evidence Verification | **schema12**；evidence-verification-v9.4-standalone-templates / evidence-verification-output-v9.4 |
| Power Domain Review | protocol4；power-domain-review-v3.1-applicability / power-domain-review-output-v3.1 |
| Revision | protocol2；bounded-revision-v2-per-finding-actions / revision-output-v2 |
| 规则/工具/政策 | power-demo-rules-v1.1 / scalar-si-conversion-v2 / limited-repair-policy-v1 |
| 运行存储 | local-review-service-v1；显式 JSON，不使用 pickle |

知识库：`D:\PowerTrustAI\data\retrieval_local\semantic\corpus.sqlite3`。固定默认知识版本：

`k-182e01fab54ebfada841fb108061c127273e9cfcd551b6f5a8888a769215e385`

每次运行固定版本；修订不改版本。模型 ID 来自服务器环境，不写死业务逻辑；真实入口从绝对项目根加载 `.env`，不查看其内容。90秒模型超时、8000输出tokens、96000输出字符；服务预算40模型调用、最多一次业务修订、800秒总限、110秒步骤限，无瞬态自动重试。其余预算以 RunBudget 和存储的 manifest 为准。

## 版本与真实验证边界

最新服务代码 SHA 和验证证据：[service-delivery-v1.json](../data/runtime_local/service-delivery-v1.json)；每运行 manifest 另存实际代码/模板/配置/协议哈希。没有 Git commit 可引用。

事实重审 v3：两场景独立核验2/2、原引用4/4完成；23请求。只复用冻结修订回答做事实阶段重审，**没有运行新生成、Revision、领域审核或完整闭环**。12例数量组件11/12结构完成，且没有完整提取链路，不能据此评价提取能力。

旧 `stability-minimal-v2` 与 `stability-minimal-v3-rereview` 是旧协议的初审修订/重审结果，不是 schema12 全闭环成功。服务v1初交付时HTTP仅验证synthetic_fixture；本轮两个真实模型API服务端到端结果见上节，未触发Revision分支。

服务v1初交付时417项离线测试通过（55.679秒）；新增19项服务/API测试。项目 Python3.13.2，pip check通过。实际 HTTP 演示、进程重启后结果与反馈保留均成功，本轮付费调用0：

- [HTTP 演示](../data/runtime_local/http-demo-bab0e40a44814ec8925ab29baaf8f225.json)
- [重启验证](../data/runtime_local/http-restart-verification-v1.json)

## 已知语义与执行限制

- 核验对象转换仍未解决：N12 将认可“四类”的技术断言改为“回答写了四类”，answer_scope supported 仅证明文字存在，不证明技术正确。
- N10 真实资料“三类 rating + active power output”仍存在忠实性与来源支持混淆，模型无法评估不是正确发现错误。N11纠正后仍返回非法 category_membership，属执行失败，不是合法语义无法评估。
- 分类/立场/忠实性由模型判断，程序不证明语义等价；显式异议能阻止 supported，但不能保证模型主动提出异议。规则告警、工具结果与模型判断分开。
- 证据不足、工程输入缺失、未执行仿真仍须保留；概念解释与厂站操作/安全承诺的规则适用范围不同。
- 同级有效输出保留；必需检查未完成不能整体放行。正文、元数据、输入快照和计算依据不可互相替代；仅哈希/元数据不证明完整正文覆盖。
- 同步检索/远程请求取消不能强制终止底层工作；服务会等待底层资源结束再启动下一运行。
- 重启将 queued/running 标为 interrupted，不自动恢复或重发模型。SQLite 不可写时不能保证新错误本身持久化；明确报告未保存，停止接受运行。
- 单用户令牌不是专家身份认证；无多worker、公网部署、自动恢复、历史实验批量导入或训练反馈管线；UI本轮已实现。

## 验证与启动命令

从项目根运行；以下测试和显式演示不付费，也不读取真实 `.env`：

```powershell
cd D:\PowerTrustAI
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m pip check
# 仅在依赖缺失时安装，不是每次运行所需
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock.txt
& .\.venv\Scripts\python.exe -m backend --demo --port 8765
# 另一个窗口，先确认 synthetic_fixture，再提交演示
& .\.venv\Scripts\python.exe -m backend.http_demo --port 8765
```

真实服务启动入口为 `python -m backend --port 8765`；本次交接不执行。真实提交会付费，须按新会话用户任务控制。配置、令牌本机使用方式、HTTP请求与人工反馈示例见 [服务说明](local-review-service-v1.md)。不把访问令牌放 URL、日志、归档或聊天。API依赖按需导入，纯 Harness 不依赖 FastAPI。

## 工作区与私有资料

新 Git 根 `D:\PowerTrustAI` 已建立，尚未 add/commit；所有新项目目录在 status 中为未跟踪，不能当作只属于本轮的差异。服务改动文件及职责见服务说明和 service-delivery-v1 哈希清单。当前交接仅新增 AGENTS.md 与 handoff、documentation-index、design-decisions 三份文档，不改业务代码/历史报告。

历史嵌套仓库 `D:\PowerTrustAI\power-system-hallucination-risk-assessor` 被整个忽略，未修改；父目录不是仓库。新仓库无已跟踪凭据；未读取密钥。必要时使用命令级 `git -c safe.directory=D:/PowerTrustAI status --short`，不改全局设置。

`.env`、整个data、模型、数据库、原文PDF、实际消息/响应、运行输出及旧仓库均忽略，`.env.example`允许提交。运行库 `data/runtime_local/runs.sqlite3`，未来真实服务归档 `data/retrieval_local/service_private/{run_id}`；均私有，不经API暴露绝对路径。旧报告保留当时版本与结论，即使其中“无Git/领域未实现/尚无标签”等陈述已过时。

## 后续工作（待新任务授权）

最终中文《PowerTrustAI 项目学习与面试手册》**尚未完成**，属于项目最终交付。要求见 [final-handbook-requirements.md](final-handbook-requirements.md)，主题素材见文档索引。后续会话不得将 README、运行说明或本交接视为满足该要求；本轮仅保存要求和素材索引，未编写最终手册。原初期 PDF 保留为学习深度/形式参考，不是当前实现依据；最终页数随有效内容确定，可超过100页，但不得重复凑页。

最小本机界面已接入，两个真实API小场景已验证（见本轮上节）。下一步优先独立修复HTTPS来源URI投影误判，必要时再设计真实Revision或语义人工复核验证；任何新增付费批次仍待用户授权，不自动开启六场景、新修复或模型实验。语义支持判断微调、证据组装、向量/混合检索生产接入是后续议题，不是已完成能力。

## 2026-10-04 新会话基线确认

已阅读 AGENTS.md、本交接、documentation-index.md、design-decisions.md 和 final-handbook-requirements.md；用户再次指定本机辅助审核服务 v1 与显式 schema12 装配为当前基线。只读核对 backend/assembly.py：真实装配使用 AsyncSQLiteBM25Retriever、OfflineHarness 及 schema_version=12 的事实审核 Agent。具体新任务尚未提供，本轮未开发、未启动服务或实验、未调用模型、未编写最终手册；仅更新交接和素材索引。未运行测试，既有417项通过记录仍属于此前服务交付验证，本轮不将其称为重新验证。



## 2026-10-04 v0.1收尾验收（未完成完整验收）

统一入口：[prototype-v0.1.md](prototype-v0.1.md)。本轮实际代码修改仅 backend/serialization.py、presentation.py（新增）、service.py、static/app.js、tests/test_v01_presentation.py（新增）、tests/ui_client_checks.js；相关说明更新 prototype、UI、handoff、索引和设计决策。全部新项目未跟踪文件不等于本轮差异。

修复HTTPS URI被盘符正则误伤：URL字段结构化解析，公开HTTPS、不含凭据/敏感查询/fragment/本机主机，不合适来源置空；路径诊断整体隐藏，归档路径继续摘要引用，原文保持纯文本。前端外链 noreferrer/no-referrer/noopener，不附令牌、不由服务抓取。中文主区分开运行结束、阶段完成、检查评估及决策；确定性摘要区分执行、矛盾、缺证据和工程前提，原始原因保留详情。检索、协议、政策、默认预算、模型及旧仓库未改变。

427项离线测试通过（最终48.149秒），客户端重复点击/未知POST/409保留输入/字面恶意文本/外链检查通过。实际内置浏览器：旧真实问答摘要、官方HTTPS链接属性、Evidence回查；已有synthetic_fixture修订v1/v2/动作及v2反馈追加；重启后反馈可见。截图和JSON见 data/runtime_local/v0.1-acceptance/。新真实请求0，不混入旧9次调用；两旧真实结果及反馈、演示反馈重启前后逐字段一致，模型记录6/3/0，无POST重发。

真实Revision预检停止：冻结构造回答“230 kV equals 230 V.”，非厂站数据；完整结构最坏14+C1+C2，C1=0，合同没有修订引用数量硬上限，不能证明C2≤16，故30预算不足以覆盖完整最坏情况。不能把30次硬截断当作审核完整性证明。未提交真实API任务、未删审核、未改协议、未换题重跑。frozen-plan-final.json保存最终源码/配置/知识哈希和输入；早期预检保留。直接执行data脚本曾因模块路径产生ModuleNotFoundError，后由项目根runpy入口完成零调用预检，保留失败说明。

Git路径级候选、忽略规则已检查；.env、data（包括令牌/DB/全文/请求响应）、模型和历史独立仓库均排除。user.name/email未配置，停止暂存/提交，未设置身份；无提交哈希、标签或推送。代码快照ZIP作为本机文件恢复材料，不能宣称Git基线。当前服务为8765演示模式，无付费任务；不自动开启下一轮。

本机人工辅助使用可行，但完整v0.1冻结条件未满足：缺真实Revision实证和Git基线提交。模型目标/fidelity混淆、未执行仿真、未核对PDF视觉原文仍保留。最终中文学习与面试手册未写，要求继续见 final-handbook-requirements.md；本轮素材为URI错误、中文解释、严格预算预检、重启验证和基线限制。

## 2026-10-04 后续授权与真实Revision完成（覆盖本轮早期停止结论）

用户随后明确“预算无上限，你尽管验证”。早期30预算预检未提交任务，原计划及reading-notes/revision-review的preauthorization副本保留。新独立冻结 frozen-plan-authorized.json：完整结构14+C2，保守C2≤单响应96000字符，独立调用预算96014，默认服务40未改；仍最多一次Revision、每阶段一次格式纠正、默认知识/检索/政策/协议，其余时间/工具等限制保留。

实际内置浏览器唯一API POST run e1c6bc1336cd4c89acee8bd2795a0ebb。先由演示→真实模式保护阻止旧页面首次点击；自动审批曾拒绝紧接着的点击（重复付费风险），只读确认模式保护已结束及运行列表无新增后才唯一提交，无绕过或重复请求。初审contradicted + domain-answer_units warning，原LimitedRepairPolicy自主revise；一次Revision把230 kV=230 V改为230000 V，重提取、事实与领域重审完成。总8请求（extract2/domain2/fact3含一次纠正/revision1），运行38.787秒。v2事实5 supported、1 insufficient_evidence，工程输入/单位检查/仿真边界仍未评估，最终review_required，执行阶段完整、检查未全部评估；非pass，无安全认证。

保留真实失败：重审call6把另一主张的工具计算作为basis，合同拒绝“calculation belongs to another frozen claim”，保留5条有效peer；call8一次格式纠正有效。7条Evidence/7个SI工具结果回查。全部8个响应及原消息存在、响应哈希核验；输入130256/输出4168/合计134424 token，缓存hit40064/miss90192；估算USD0.016149792–0.032299584，2026-10-04官方价目复核，非账单。旧9请求独立统计，不混入本轮。

浏览器核对真实v1/v2/修订动作/摘要/工具/Evidence；v2 finding-claim-0ff6075a3e8bae05955f9458追加待查意见，AI辅助用户监督，不覆盖模型、不改为专家金标准。冻结真实服务重启：结果及最新反馈逐字段一致，8→8，无重发，real-restart-verification.json记录。

真实批次全程源码不改；完成和重启验证后保存frozen-real-runtime-source.zip，逐manifest SHA核对，再独立修复投影把JSON field_path误隐藏的问题（未进行模型语义修复）。最终428项离线/45.986秒通过，保留批次前427项日志；最终默认演示服务8765已恢复、页面令牌清空，不留下大预算真实服务，不自动下一轮。Git身份仍缺，未暂存/提交，源码ZIP恢复材料不等于Git基线。技术原型可冻结、本机人工辅助可用；Git提交步骤仍阻止完整基线交付。最终长手册仍未写，要求继续保留。

## 2026-10-04 GitHub基线上传授权与准备

用户明确授权检查后创建本地基线并推送到 https://github.com/7556481/PowerTrustAI.git，覆盖默认不自动提交/推送规则，仅限新项目。已确认Git根D:/PowerTrustAI、当前分支master；初始没有提交、没有remote，Git user.name/email现已由本机配置（不修改或输出身份值）。仅明确白名单源码、测试、依赖、公开元数据和非敏感文档进入拟提交清单；.env/data/令牌/密钥/模型/全文/运行库/真实请求响应/私有归档及旧独立项目排除。将逐暂存blob及提交历史检查，忽略规则不代替已跟踪检查；不强推、不改分支、不改仓库可见性、不打发布标签。实际推送结果与哈希记在本轮忽略的GitHub交付记录并在完成后补交接。

此上传不启动付费批次，也不改变最终中文手册要求或既有写作授权；此前最终手册尚未交付，不以本次上传、README或运行说明替代。
