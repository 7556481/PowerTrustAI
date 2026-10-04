# 最小 Power Domain Review 与程序前提（v1）

此阶段使用真实模型做有限工程审阅，未运行仿真、未实现 Revision、未恢复旧六维分数。规则均为 PowerTrustAI 演示规则，不是官方操作规程或安全认证。文献支持、规则检查和实际计算必须分别表达；当前计算记录恒为空。

本轮早期 v7 和后续 v7.1 的程序前提/数量算法分别保留。离线历史重放依据归档提示词版本选择原行为；v7.1 的完整上下文要求、数量极性处理不自动改写旧响应或旧运行状态。

## 程序前提与历史兼容

证据审核 CLI 新运行采用 evidence-verification-output-v7 / evidence-verification-v7.1-full-input-preconditions。完整生成输入快照缺失时，程序移除模型待判清单中的 input_evidence_coverage 组成部分，保留原索引，不重新编号；用 MODEL_COMPONENT_INDEXES 明确剩余任务。程序合并固定 not_assessable、missing_input_snapshot、program_precondition 结果。模型返回这些部分即拒绝，不把它的 supported 自动改成 not_assessable。其余模型判断、原引用和引用范围仍按严格候选 ID 规则审核。

完整 full-input-v2 存在时仍由模型检查输入覆盖关系，快照存在本身不是支持。模型失败、预算/超时未完成时，缺失快照前提仍保存，其他未判部分标 execution_incomplete 并记录执行失败。部分有效结果保留，不宣布完成。历史 v4～v6 继续按历史契约重放，历史失败不升级为成功。

新生成使用 generation-full-input-v2：绑定全部 Evidence、来源绑定、问题、用户上下文、结构化工程输入、回答要求与提示词版本，统一哈希。generation-evidence-only-v1 保留历史证据集合但不是完整上下文快照；v7.1 将其输入覆盖组成部分也标为 missing_input_snapshot。历史快照不能追加后来发现的上下文。

配置私有诊断目录时，请求前还保存独立的完整生成输入及内容哈希，请求记录用 input_snapshot_path 回查。它是输入记录，不冒充生成成功后的回答快照。没有 API 成功返回或未通过契约也不会丢掉输入；不存模型设置、密钥或请求头。普通离线导入与未配置诊断时不产生该文件。

## 有限数量与单位检查

quantity-enumeration-v1.1 支持显式英文数字/数字单词的 rating 计数，匹配 dependent on/include 等引导的明确枚举；只有每个项目都有 rating 标签才计为额定值类别。有功输出没有该标签时不自动计入。重复/多个不同列表、共享尾词、歧义、未识别语法均 incomplete；没有识别到 rating 数量表达为 not_applicable，不能据此称完成所有数量检查。中文计数入口可识别，但中文列表尚不能可靠解析。

比较只绑定固定候选，保存原始 ID；解析内部空白归一化不写入原文。结果作为独立程序检查保留，不偷改模型的历史 supported。第 3 题真实漏检被保留为开发案例：原模型将“四个设备额定值”技术部分标 supported，源文明确列三个额定值加有功输出，程序观察 4 对 3。该开发案例不是独立验收集。

v1 在新场景中把否定/转述的 four equipment ratings 当成肯定计数，产生真实程序误报。v1.1 遇到否定或措辞归属表达时返回 count_assertion_polarity_or_attribution_unclear / incomplete，不把它判成数量错误。其余复杂语法仍可能漏识别，不能声称数量检查完备。

dimensional-input-v1 对结构化电压、有功、无功、视在功率检查单位维度与已定义的 SI 比例，同类型同参考对象可比较数值。MW 不作为无功单位，MVAr 与 MW 不直接转换。pu 缺少基准或未知单位保持未完成。此检查不计算潮流、稳定裕度或设备安全余量；同参考对象比较默认同一工况，若实际工况不同须调整 reference 并人工复核。自由文本数量与单位另由模型有限审阅，不能保证全部识别。

## 领域协议

ModelPowerDomainReviewAgent 复用 PowerDomainReviewInput/Output、共享主张、Retriever 与 ModelClient。每个 DomainRule 保存规则 ID、version、source、applicable_scope、description、demonstration_only。来源为本项目开发规格，不冒充 NERC 约束；本文是该注册演示规则集的出处。RULE_SET_VERSION 为 power-demo-rules-v1。

程序检查工程输入 presence、结构化单位、可识别枚举和 simulation_not_run；plant_assessment 需要 network_model、operating_point、limits、contingencies 标识，presence 齐全也不能证明输入质量充分。conceptual 问答不强制要求完整电网数据，但整体工程可行性仍未评估。

模型独立完成 answer_units、analysis_scope、operating_prerequisites 三个检查。输入是问题、冻结回答、共享主张、工程输入、规则、程序候选；不包含 Evidence Verification 结论。

模型根对象为 checks，每项仅包含 check_id/status/claim_ids/quote_ids/basis_kind/rationale/missing_prerequisites。程序绑定规则、版本、回答版本、严重性与摘录。literature 类型完成判断必须选择正文候选；engineering_rule 可以依据未核实输入或缺失前提不选择正文。没有 calculation 类型。未知 ID、额外摘录/偏移、未覆盖必需检查严格拒绝。no_issue 只是有限检查没发现问题，not_assessable 不可放行；未执行分析恒由程序保留。

领域提示词当前为 power-domain-review-v1.2-scoped-json-id-bases。v1.1 根据 [DeepSeek 官方 JSON 模式说明](https://api-docs.deepseek.com/guides/json_mode/) 补明确 JSON 声明；v1.2 区分实际越界结论、操作指令和概念说明/未来分析建议，避免单纯因为没仿真就把限定充分的概念回答报为越界。实际准确性仍须人工复核。

现有 Harness 仍先完成三种用途检索，再用 asyncio.gather 独立执行两类审核；共享相同 answer/claims，两方不读对方结果。单方失败保留另一方与本方程序检查。兼容追加 domain_output，以便在汇总之外保存详细规则、依据、检查状态及响应归档。领域未完成、数量告警/未完成或覆盖缺口将阻止通过。真实/演示混合链路始终有非认证门控，不输出整体真实 pass。

DeepSeek 连接器每个实例单个 HTTP 工作线程；双审核使用两个独立实例，最多两个模型请求在途，共用原 Harness 请求预算。同步 SQLite 在其所属线程运行；超时不强制终止底层 HTTP/SQLite 线程，服务/工作线程时限仍生效。无隐式重试、无无限并发。

## 新鲜场景演示

三个场景为正常电压与稳定性、缺失工程数据、故意不一致的合成工程输入；后两者的数据不是实际电厂测量值。沿用真实官方索引，本轮不更改检索/分词/切分。复用当前 generate 入口先生成并保存快照，再用 Harness assess_existing 双审核。生成仍为 generated，审核输出均为局部发现/人工复核状态。

用项目根目录 PowerShell 运行（付费，新输出路径）：

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m harness.power_review_demo --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 --knowledge-version k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55 --cases 1,2,3 --max-requests 20 --output D:\PowerTrustAI\data\retrieval_local\deepseek\power-review-new-run.json

默认只运行场景 1。--max-requests 范围 1..20，是本次 CLI 的所有生成、提取、审核及纠正请求总额；跨多条命令时操作者仍须累计。每个生成最多两次，每个审核阶段最多一次格式纠正，共享每题审核最多五次预算。不足以启动三项初始审核时提前停；相同校验约束在一次纠正后重复则停止当前批次。服务失败也停止批次。程序只为鉴权加载根目录 .env，不打印内容。诊断和模型原文保存在 Git 忽略目录，不覆盖已有输出。

离线验证：

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m unittest discover -s tests -q

测试响应是 synthetic_fixture；测试数量仅说明程序回归通过，不说明领域审核准确率。真实报告必须逐条核对语义漏检、误报与输入覆盖，不把结构合法当成判断正确。

本轮实际记录在 data/retrieval_local/deepseek/power-review-summary-20261003.md：17 次新增请求后停止；场景 2 精确引用定位错误在一次具体纠正后重复。场景 1/3 有效回答当时保存证据集合与分离的上下文，但未统一绑定 v2；最后一次场景 2 生成失败。本轮没有已接受的真实 full-input-v2 回答，v2 与请求前输入归档目前仅有离线验证，不把后来实施的保存机制回填为历史事实。
