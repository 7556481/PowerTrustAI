# 内部职责与有限整理

新增 services/fact_two_stage_v1.py（两阶段契约）、evaluation/fact_two_stage_trial_v1.py（本次专属冻结与归档）、tests/test_fact_two_stage_v1.py（实际适配器边界与停止门禁）。复用 FactFlowAgent、Catalog v2/v1、scoped_fact_execution、structured_request、ModelBudget、原 Factory/Harness/Store/API。替代仅为显式开发配置的构造选择；生产和旧协议、历史驱动、失败归档全部暂留。未复制项目、语料、模型或环境。

生成 Agent：generation.run 将证据组装为 answer_units，严格解析后保存 generation_snapshot；无证据有显式不足出口，共用一次结构纠正。主要缺口是短答案下条件与任务要求的语义覆盖，格式有效不证明覆盖。优先级二：单次生成输出的要求覆盖审计，先制定固定验证而不增加规划器。

领域 Agent：power_domain_review.run 的生产 protocol 5 转入 domain_contract_v3，程序规则与模型检查并存，包含作用域、适用性、保护功能完整性；缺真实分析工具不能凭事实 supported 视为安全。与事实 Agent 在条件和依据上有交叠但判定责任不同。优先级一：把工程前提缺失和语义反对分项展示、验证实际工具能力边界，保留独立判断，不同时重写。

修订 Agent：revision.run 的生产 protocol 2 转入 revision_contract_v2，限定允许证据和可修复问题，记录修订及未解决项；外层重新提取并完整双审，保存历史版本。与生成器重复的是回答单位、约束解析和快照职责，现已复用公共服务。优先级三：验证多缺陷修订覆盖及未解决项不丢失，不能把一次修订可执行当修订成功。

本轮沙箱 asyncio socketpair 阻塞，faulthandler 定位至 Python 内部 accept；按项目规则审批运行离线测试，未重建环境或改权限。初版测试发现结构请求返回 tuple 需解包、协议需沿用 v9 家族，以及独占写入不能覆盖 checkpoint，均在付费前修正并保留此失败说明。
