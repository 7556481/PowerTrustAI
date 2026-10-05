# 可选本地NLI旁路诊断 v1

2026-10-05，接续1b7be0b6a91aaa57136e79e7457904307fd7cf22。本轮增加可选本地诊断，不替换Evidence Verification Agent，不赋最终审核权，不修改事实支持要求、Revision触发、工程规则、原业务决策或默认BM25/aggregate。NLI默认关闭；不训练/补标/换模型或调用DeepSeek。

## 先修正文说明，保留原实验

逐项核对expanded-v3/error-analysis.json/md，发现按家族套用的说明可将同家族错误理由写在正确/改善样本上。新error-analysis-corrected-v1.json/md按sample_id、真值、两模型预测和本项原文的收到复核理由重写33项；analysis-correction-list逐项保存旧/新说明、原报告SHA与状态。原label/logits/prediction/metric/task及历史报告不改变，修正文说明阶段不加载模型。

## 组件与权责

- services/local_nli.py：production_frames、frame、LocalNLI.start/diagnose/close。它只产生local-nli-sidecar-v1记录，不是第五Agent或新Harness。
- backend/nli_worker.py：独立CPU推理子进程，复用evaluation.support_nli.load_model、实际label mapping与support-nli-document-body-pair-v2。只读固定epoch1 checkpoint，验证profile中每个文件SHA/基座revision/adapter；完整头加载，无随机初始化/optimizer/train。
- backend/config.py：服务所有者配置，API任务不能指定模型位置/解释器。ApplicationService在生命周期启用时加载一份模型；后台诊断在原Harness终态已保存之后运行，输入只来自已完成结果，不返回任何Agent/Revision提示词。
- backend/store.py：同一objects记录机制追加kind=nli_diagnostic，独立UUID/回答版本/claim/component/input_id；严格绑定，不能覆盖已有对象或结果。GET /runs/{run_id}/nli只读历史，不补算。
- backend/static/index.html/app.js：独立本地NLI诊断区，模型三类、原事实判断、分歧、跳过/失败、原始logits和版本输入详情。原事实Agent未执行时明确未提供，开发回放的用户监督另列，不能冒称事实Agent判断。

输出字段nli_three_class_result与生产四类分开，record authority=diagnostic_only、affects_decision=false。raw logits只是模型未校准输出，本轮不展示softmax，不称事实可信概率。显示既有SSIAG实验4/23错误支持警示，NLI supported不表示整体pass或工程可靠。

## 输入边界与失败隔离

生产转换仅接受明确当前回答/version的asserted正文事实component：document_body/technical_content、核验阶段无执行问题、唯一per-component delivery映射且核验delivery_summary与原retrieval记录一致、固定knowledge版本以及verification中的whole_fragment候选必须逐字等于实际Evidence全文。取该组件delivered_evidence_ids的全部正文，不用finding/model选出的basis子集、不从全运行pool或当前索引拼接。保留原命题/原措辞/否定/单位数量/必要限定和适用范围，行政来源保留typed上下文但不进技术premise。

元数据、工具/数学关系、输入覆盖、recommendation工程前提、not_assessable、未实现立场、未证明输入/缺映射/核验交付快照/版本不符/无完整whole候选均明确skipped。aggregate旧记录通常缺可证明逐组件交付，启用NLI也不切换默认检索或猜测。完整tokenizer truncation=False，>512 skipped(over_context_no_truncation)，无静默摘要/截断。

项目.venv不安装训练框架。显式配置隔离训练Python启动一个服务拥有的持久子进程，通过UTF-8 JSON行传递实际语义输入。推理在子进程进行，不阻塞事件循环；本地并发1、无等待队列，busy仅当前诊断failed。模型启动限30秒，请求传输与推理合计默认5秒（验证配置10秒，必须大于0且不超过60秒）；超时终止自有推理进程、标记当前和后续model unavailable，需服务重启，不自动重试或重发历史。子进程崩溃/非有限logits/推理错误/转换或存储失败均只影响诊断，原运行status/decision/finding/Revision不改。若转换/存储失败未写入成功，当前进程仅保留错误码，重启后缺失记录不能当成功。worker监听服务与启动器的精确PID/创建时间，处理Windows虚拟环境重定向器子进程；父退出即自终止，生命周期只读烟测已确认模型PID消失。服务停止回收自有进程；未完成诊断不自动恢复，已保存记录仍可查。

## 明确配置后启用

默认无配置就是关闭、不创建模型进程。仅由本机所有者设置以下非凭据环境变量，保留原服务启动方式：

```powershell
$env:POWERTRUST_LOCAL_NLI_ENABLED='1'
$env:POWERTRUST_LOCAL_NLI_PYTHON='D:\PowerTrustAI\data\runtime_local\new-machine-restoration\training-env\Scripts\python.exe'
$env:POWERTRUST_LOCAL_NLI_CHECKPOINT='D:\PowerTrustAI\data\runtime_local\support-nli-expanded-v3\run-v1\best-checkpoint'
$env:POWERTRUST_LOCAL_NLI_PROFILE='D:\PowerTrustAI\data\runtime_local\local-nli-diagnostic-v1\model-profile.json'
$env:POWERTRUST_LOCAL_NLI_TIMEOUT_SECONDS='5'
```

关闭：设置POWERTRUST_LOCAL_NLI_ENABLED=0后重启。profile固定基座revision b95119ce93d3e065de6214e38cd4a97b0f2f2c6d、epoch1和权重SHA c49122c7c07ae56c7381d014ddffa46dfae373cf63265657284a51fbcf24a358；模型映射0contradicted/1supported/2insufficient。profile由已封存检查点清单生成，不自行指向另一个模型。凭据仍由原服务机制本机管理，本轮没有读取/输出密钥或令牌。

本轮独立已见回放启动命令：

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe D:\PowerTrustAI\data\runtime_local\local-nli-diagnostic-v1\serve-replay.py
```

只监听127.0.0.1:8767、synthetic_fixture演示页面，0付费调用；新run是冻结开发材料的诊断回放，不是真实生产审核。令牌只由所有者本机查看/填写，不发送聊天。服务进程PID在忽略service-pid.json；停止时回收该服务及自有模型子进程，最终实际状态见verification-final.json。

## 实际验证与明确缺口

公开synthetic_fixture覆盖输入池隔离/不按判断选Evidence、版本/映射/类型/立场跳过、默认关闭不加载、失败隔离/终态pass不变、busy/timeout终止、超长无截断、追加版本绑定/重启持久化和UTF-8精确传输。最终完整571项测试通过（具体耗时与日志见verification-final）；Harness原demo保留。

初次私人验证启动脚本使用旧startup事件，在既有lifespan下未运行回放；改为包装原lifespan，不改公共启动逻辑。初次回放另发现Windows默认文本管道编码造成3请求失败，保留原35诊断及first-*记录；worker改为stdin.buffer显式UTF-8解码，加公共Unicode回归，新v2回放另存，不覆盖失败或针对具体样本加规则。

修复后33正文完成/2辅助skipped/0failed，所有33分类及logits与原冻结结果完全一致，最大logit差0；支持、必要条件删除、顺序颠倒及类型跳过均包含。原4错误supported继续输出supported并展示与已有监督分歧，没有纠正模型或换标签。总正文推理2.8942秒，加载约0.1590秒，观测模型RSS最大500,064,256字节≈477MiB（记录点观测，不等于精确瞬时峰值）；无GPU框架/驱动变更。

实际浏览器由用户仅本机输入访问令牌后检查：35诊断卡、6处用户监督分歧、2处skipped、4/23风险提示、明确事实Agent未执行、展开版本/logits/输入详情。服务重启后实际点击查询状态，仍35同UUID记录、0新增模型预测；browser-verification与两截图在私人包。脚本HTTP检查与实际浏览器证据分开，不混称。

旧服务历史仅只读核对16终态记录，生产转换0：3无明确component，其余至少12记录有不支持basis类型，2缺明确组件交付映射（记录可同时含多种缺口）。没有凭当前检索补历史，也没有写旧数据库。当前真实事实Agent与NLI联动尚无可安全转换的既有实际记录，本轮验证是已见开发输入＋公开synthetic作用域测试，不作为新准确率/真实付费端到端验收；不扩大为训练或付费批次。

## 交付与教学

私有审阅ZIP含修正版及修改清单、model profile/检查点SHA、旁路记录/输入/logits、首次失败、新回放/只读历史缺口、HTTP/真实浏览器/重启/资源/测试/保留性及文件SHA；不含凭据、完整数据库/PDF/权重。公开代码/测试/说明独立提交普通推送，实际哈希与远端回查见verification-final。原事实协议/schema13与Harness/Agent/检索算法/政策源文件核对基线不变，业务默认配置也不切换。

长期中文手册补职责分离、逐组件交付的来源证明、行政正文边界、未校准logits、错误支持两分母、async/进程生命周期/并发超时/失败隔离、append-only版本绑定和旧记录不能补造、UTF-8故障与真实浏览器证据。本轮不重建整本手册/PDF/文档站，不自动开始下一轮训练。
