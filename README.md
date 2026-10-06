# PowerTrustAI

## 2026-10-06 正式学习站与审核共同诊断（最新）

先交付docs/learning：18主题章＋术语/工作坊两附录，Markdown唯一正文，标准库静态构建，8770独立学习入口start-learning.cmd，目录/搜索/代码高亮/导航；旧30/38页PDF仅参考、保留。源码摘录/公式/真实训练检索/NLI失败及待补清单核对，实际浏览器阅读验证。

新用户4df8…非法JSON后source_kind混成explanation；47个历史诊断响应汇总，程序接线、协议负担和语义错分开。实现schema14紧凑target原型，但真实Harness仍只包装schema9–13扩展输入，缺tool_results，Fact前失败。固定12题同源码配置、无预期泄漏、无重发：0/12完整，32请求304657token，0Fact请求/无结构成功率分母，0Revision，0pass。客户端遗漏共享EXECUTION_FAILURE停止条件，12已结束才人工发现，明确保留，没有自动修复重跑。只恢复日常默认13；14不启用/未验收，原13仍可能契约失败。详见[audit-stability-learning-v1](docs/audit-stability-learning-v1.md)。原唯一语料写者继续、日常固定部分快照不切换。停止追加开发，待所有者和ChatGPT审阅。


## 2026-10-06 英文身份与忠实性收尾 v1（最新）

接续a898e34，51片可读英文无_id，使用固定revision/分片/原始绝对行号的命名空间内部身份，另存正文SHA与缺失标记；中文7,373,300行、去重与断点不变。唯一逻辑写者已安全续建，完整库尚未发布，不切换日常kc-5894部分库。

事实提示v9.12明确忠实性只比回答与提取目标，证据不支持属于事实判断；schema13/输出v9.11/support-v5/派生v2/一次Revision门控不改。678离线回归。原功率因数一次新run ab338c35…4请求50716token18.089秒，完整执行；因果组件faithful/证据不足，但repair=null，原引用条件仍未知，人工复核/部分，0Revision。自动修订仍未验收，不继续刷题。浏览器自动连接、原句与引用、旧新两结果重启零重发通过。详见[本轮说明](docs/identity-fidelity-v1.md)及忽略目录identity-fidelity-v1审阅包。日常8765与后台构建继续；停止新增开发交所有者试用。


## 2026-10-06 审核接口 v2（当前）

日常一键入口/8765不变。新来源条件只选择程序候选ID，原文/区间/版本由程序绑定；合法分类异议保存为完整复核结果，不再要求模型重复派生状态。普通新答案禁止内部Evidence ID，通过引用区域回查。674离线回归；真实三题均完整执行，正常概念192字符通过，功率因数旧错误/工程补验证人工复核，0实际Revision，仍有语义限制。详见[audit-interface-v2](docs/audit-interface-v2.md)。完整库已在英文分片缺_id列处退出，断点7,373,300行保留，未自动恢复、发布或更换日常快照。本轮停止新增实验等待试用。


## 2026-10-06 首版收尾当前状态

日常入口仍是双击 `start-powertrustai.cmd`，统一8765自动连接；关闭用项目Python `-m backend --stop --port 8765`。可中文问答、已有回答审核、查原句/引用/历史版本。新增可选“本地NLI第二判断”默认关闭，只有服务端配置可用才可选择，仍仅诊断；aggregate缺逐组件交付证明会跳过，不更改检索或业务判断。

本轮工程缺资料问得到184字符中文回答、完整审核后待补充；正常概念与原错误题仍事实契约失败，没有实际Revision成功。NLI加载/开关/记录及重启验证完成，实际3组件全部跳过，不能称真实推理完成。首版最终验收仍有阻断，详情、配置与限制见 [first-release-v1](docs/first-release-v1.md)。后台原库唯一写者续建，完整库未完成且未发布；日常保持原固定部分快照。旧报告及失败不改写。本轮停止新增实验，待共同验收。


本机、单用户的电力知识问答与已有回答辅助审核原型。模型判断、程序规则、工具结果和人工意见分别保留；`pass` 是当前政策的业务结果，不是工程安全认证。已有CPU微调与可选本地NLI诊断；NLI默认关闭且没有审核决策权。

## 2026-10-06 收尾验收状态（最新）

中文问答、已有回答审核、原文回查、历史/反馈与一键自动连接可使用。日常双击`start-powertrustai.cmd`，固定8765；停止用项目Python `-m backend --stop --port 8765`。新政策只对有既有原文修复依据的定位缺陷允许一次修订，修订后完整重审；真正缺资料或输入不靠删问题通过。页面直接显示未解决原句与原因。

**最终真实验收未通过**：概念问完整审核但仍有不必要的缺口声明，原功率因数失败回放未实际修订，工程资料不足案例仍有审核契约失败；不宣称自动审核已稳定可用。日常固定部分快照而非完整库；后台可恢复构建独立继续。实际结果、限制与源码入口见[收尾验收记录](docs/final-acceptance-v1.md)。以下历史阶段说明保留供回查，以本节最新状态为准。

## 产品试用 v1

2026-10-06：[基础概念覆盖与引用支持](docs/basic-coverage-v1.md)新增出版社教材正文和可追溯小节摘录；日常schema13启用版本化支持关系说明，区分未回答思考题、术语表头、实际数据表与解释正文。原无功题完整审核仍待补充，并联电容题限定通过；理想模型条件和部分引用解释局限保留，不以引用数量宣称正确率。启动入口及界面不变。

本机日常入口：双击 `start-powertrustai.cmd`，自动打开 <http://127.0.0.1:8765/> 并建立本机会话，无需复制令牌。普通刷新、重启复用会话，已有服务不重复启动。命令入口为 `& .\.venv\Scripts\python.exe -m backend --open --port 8765`；空闲正常停止为 `& .\.venv\Scripts\python.exe -m backend --stop --port 8765`，或启动终端Ctrl+C。高级手动连接和访问保护保留。真实模式需已有服务端模型配置和私有知识库；先试 `--demo --open` 可离线体验界面。

少量中文教学/官方管理办法/论文正文已建立独立知识快照，默认BM25、aggregate、NLI关闭不变。已真实完成中文法规问答与完整审核；概念回答仍有偏题、冗余，不以测试通过宣称全部验收。查看[本轮启动、资料来源、真实结果与限制](docs/zh-daily-v1.md)。详情默认折叠，答案和实际引用优先。

中文原BM25成功空命中且固定英文语料明确时，最多一次英文查询转换补检；仍无依据以中文待补充返回，不审核程序拒答模板。转换失败独立为执行未完成。生成跟随提问语言；答案与原因优先，审核/证据/NLI/反馈折叠，来源只显示实际引用。详见[中文问答与展示](docs/qa-usability-v1.md)，真实连接失败与未验证范围保留。

日常服务显式使用版本化`product-decision-v1`：检查完整、主张支持且无阻断发现可自动通过；定位明确的普通错误最多一次修订并完整重审；仍错误不通过，证据/工程输入不足待补充，判断争议人工复核，执行失败独立显示。演示规则不构成权威高风险判据；当前没有注册生产高风险认证规则。通过不代表工程安全认证。

先运行下方`--demo`，连接后尝试问答与已有回答审核；演示模拟判断，仅验证交互。再由本机配置`.env`的`DEEPSEEK_API_KEY`与`DEEPSEEK_MODEL_ID`，启动真实服务：

```powershell
Set-Location D:\PowerTrustAI
& .\.venv\Scripts\python.exe -m backend --port 8765
```

页面选择概念/资料或工程范围；工程范围与实际主张同时审查，选择概念不能让性能承诺绕过technical_truth。工程结构化输入、量纲换算及固定原引用可用现有API字段，详见[产品处置与试用指南](docs/product-improvement-v1.md)。页面优先展示最终回答、处置、风险/未知、问题解决程度；版本、证据与原始详情保留。Ctrl+C停止；重启查询不自动重发。日常统一8765，临时验证服务另设目录和端口，不作为日常入口。

需要复现历史政策时，当前终端设置`$env:POWERTRUST_DECISION_POLICY="legacy-v1"`；日常默认`product-v1`，不回填旧结论。可用`POWERTRUST_RUN_DB`指定独立运行库；固定令牌路径不变，NLI保持默认关闭。

## 最短离线入口

已验证 Python **3.13.2**（Windows）。核心离线 Harness 无第三方依赖；在独立克隆中执行：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m harness.demo
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

普通测试不调用模型。未安装可选依赖时，API/PDF检查明确跳过；私有历史响应不随仓库分发，对应历史重放缺文件时跳过。公开synthetic_fixture回归仍执行。完整公开API/PDF回归：

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock.txt -r requirements-pdf.txt
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 本机网页演示

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock.txt
& .\.venv\Scripts\python.exe -m backend --demo --port 8765
```

也可加 `--open` 自动建立本机会话；不用复制令牌。服务固定令牌文件 `data/runtime_local/access-token` 存在即复用，普通重启及模型切换不轮换。高级手动连接默认仅内存，主动记忆可迁移到HttpOnly会话；“忘记连接”注销会话并删除旧记忆，401清理失效连接。勿将任何令牌放入URL、聊天或截图。按Ctrl+C停止服务。演示显著标记 `synthetic_fixture`，不读取项目`.env`、不需要私有知识库、不调用付费API。

另一终端可执行 `& .\.venv\Scripts\python.exe -m backend.http_demo --port 8765`：先核验演示模式，再检查两种提交、Evidence回查、反馈、错误版本409和无令牌401；运行材料留在本机忽略目录。

真实模式参见[统一运行说明](docs/prototype-v0.1.md)：准备获准使用的固定知识快照和服务端DeepSeek配置后，以 `python -m backend --port 8765` 启动。DeepSeek密钥用于服务端模型连接，本机令牌用于本地API访问，二者不同。真实资料、模型、`.env`、数据库和实际请求响应不在公开仓库；公共克隆可复现离线/演示工程行为，不能直接重放私有真实验收。

## 当前架构

可选[逐主张事实检索与交付v1](docs/per-claim-fact-retrieval-v1.md)已实现；aggregate仍为默认，生成/领域检索及BM25排名不变。新策略通过服务端 `POWERTRUST_FACT_RETRIEVAL_STRATEGY=per_claim_v1` 启用，提供逐组件查询/候选映射；[固定对照](docs/per-claim-fact-comparison-v1.md)同时报告覆盖和额外成本，不据少量案例切换默认。

同源HTML/CSS/JavaScript → HTTP API → `ApplicationService`（单进程、一个活动任务、两个等待位置）→ `ComponentFactory` → 现有 `OfflineHarness`。问答生成或接收已有回答后，提取主张；事实审核与领域审核并行；确定性政策决定最多一次Revision，再完整重提取和双重审。SQLite保存阶段检查点、结果和追加人工反馈；重启将未完成运行标记interrupted，不自动重发。

- **默认检索：BM25**，固定知识版本、Evidence原文定位与ID作用域校验。
- **Dense/RRF：已接入真实服务可选配置，BM25仍默认**；使用 `POWERTRUST_RETRIEVAL_MODE=dense` 或 `hybrid`，需预备匹配的固定模型与向量索引；见[启动、固定对照与资源边界](docs/semantic-service-v1.md)。事实策略aggregate/per_claim_v1独立选择，启动不下载或建索引。
- **真实服务事实审核：显式schema13**，独立事实请求与按原绑定作用域分组的引用检查；领域协议4、Revision协议2。旧schema与历史结果保留原解释。
- 执行失败、证据不足和工程前提缺失分别报告；阶段完成与检查无法评估可以同时成立。程序规则仍为演示规则，反馈来源为AI辅助、用户监督。
- 调用清单按实际请求计数；并行轨迹使用请求编号与阶段调用标识绑定，超时/取消/格式失败也保留记录。
- [支持判断数据准备与未微调基线](docs/support-judgment-dataset-v1.md)已有可运行命令与待监督复核包；已有监督与CPU微调实验，生产审核器未被本地NLI替换。pending 不计算语义正确率，真实基线结构失败后保留部分预测并停止。

[当前状态](docs/current-status.md) · [公开复现报告](docs/public-reproducibility-v1.md) · [并发轨迹修复](docs/model-trace-attribution-v1.md) · [后续实施接入点](docs/implementation-roadmap.md) · [文档索引](docs/documentation-index.md)

中文学习与面试手册为[独立r1文档](docs/PowerTrustAI-project-study-interview-handbook-r1.md)，README不替代手册。本轮未重建PDF或改写历史验收。
# 电力大语料接入与当前覆盖

本机可选中文全文索引、来源层级与固定真实对照见 [industry-corpus-v1](docs/industry-corpus-v1.md)。73分片已取得；3个发布文件缺Parquet尾部，完整处理仍在继续。日常目前使用显式部分快照，不能称完整库。旧小库、知识版本和运行保留；启动入口、自动连接、政策与NLI默认关闭不变。可选CPU依赖在 `requirements-corpus.txt`；完整原文只留本机data。
