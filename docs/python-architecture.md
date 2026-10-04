# PowerTrustAI Python 项目架构

历史原型不构成生产算法兼容规范；迁移决策及已检查的实际依赖见
[legacy-migration-principles.md](legacy-migration-principles.md)。

## 范围

项目包含标准库数据结构、Protocol 接口、状态图及兼容离线模式的 Harness。
运行方式、校验与测试见 [offline-harness.md](offline-harness.md)。已有真实模型适配与局部
生成/证据核验能力，真实工程审核、真实修订及 HTTP 路由仍未实现。已增加 Markdown/SQLite/BM25 检索实现，
见 [markdown-retrieval.md](markdown-retrieval.md)。真实 Retriever 已通过可选注入接入原 Harness，
固定版本、来源标记和预算控制见 [harness-retrieval.md](harness-retrieval.md)。
文本型 PDF 使用同一存储/检索链路，见 [pdf-retrieval.md](pdf-retrieval.md)；pypdf 为可选入库依赖。
生成模型接口、结构化草稿和仅生成状态见 [generation-agent.md](generation-agent.md)；
DeepSeek 连接与归档试运行见 [deepseek-generation.md](deepseek-generation.md)、
[evidence-verification.md](evidence-verification.md)；普通模型测试仍使用模拟响应。
建议运行环境为 Python 3.11 及以上。旧项目保持原样，作为迁移与实验基线。

## 模块组织

| 模块 | 职责 |
| --- | --- |
| core/models.py | 请求、回答、主张、证据、审核发现、决策、报告和轨迹 |
| agents/contracts.py | 四个 Agent 的独立输入输出与异步接口 |
| rag/contracts.py | 按检索目的区分的共享检索接口 |
| tools/contracts.py | 工具描述、输入输出 Schema、授权角色及执行状态 |
| harness/states.py | 状态、普通迁移关系、终止状态和中断目标 |
| harness/contracts.py | 调度、主张提取、审核策略、预算和轨迹存储接口 |
| backend/ | 后续 API 适配层，调用 Harness |
| evaluation/ | 后续离线评测和消融实验 |
| power-system-hallucination-risk-assessor/ | 原审核原型，当前不迁移 |

依赖方向：backend → harness → agents；agents → core。
rag 和 tools 依赖 core；Harness 已通过注入的 Retriever 向 Agent 提供对应目的的检索证据，工具尚未接入。
core 不依赖 Streamlit、模型库、API 框架或其他项目模块。
当前平铺布局应从项目根目录导入；未来需要安装分发时再统一包装为
powertrustai 包，避免通过 sys.path 修改或工作目录切换解决导入问题。

## 数据约束（待实现校验）

- TaskRequest.question 在问答模式必填；审核模式允许为空，但 existing_answer 必填。
- Claim 的位置为 Python 字符串的零起始半开区间 [start_offset, end_offset)。
- 每个主张绑定 answer_id 与 answer_version；两个审核输出必须对应同一版本。
- Evidence 具有来源、版本、定位和适用范围；证据 ID 在一次运行内唯一。
- CitationBinding 绑定回答片段与证据，不需要生成 Agent 提前创造主张 ID。
- VerificationFinding 引用主张 ID；DomainFinding 可关联多个主张或全文。
- supported 必须有支持证据；未发现规则告警不等于 supported。
- 执行异常与事实判断分别记录；超时不等于 contradicted。
- 修订保持 answer_id，增加 version，并记录对应的 finding_ids。
- AuditReport 汇集两类审核及修订新增证据，并校验所有 ID 引用完整。
- frozen dataclass 防止字段重赋值；Mapping 的深层不可变性与 JSON 序列化尚未实现。

## Agent 输入输出

Generation：请求与初始证据 → 回答草稿、假设、缺失信息、引用映射。

Evidence Verification：请求、固定版本回答、共享主张、初始证据 → 主张、逐主张判断、
独立检索证据及执行问题。

Power Domain Review：请求、同版本回答、共享主张、证据、规则版本 → 工程与
安全发现、缺失前提、新增证据及执行问题。

Revision：请求、回答、两类审核、允许的证据与修订要求 → 新版本回答、修改记录、
未解决发现和新增证据。修订不直接改变审核结论。

## 主张提取与并行验证

Harness 在 EXTRACTING_CLAIMS 调用 ClaimExtractor（服务接口，不是第五个 Agent）。
首次可由 Evidence Verification 的实现提供该服务；得到唯一主张列表后，将其
交给两类审核，Evidence Verification 输出应保持这些主张 ID。
EvidenceVerificationInput 和 PowerDomainReviewInput 均接收共享主张；
禁止两个审核器各自生成不一致的主张 ID。提取器的具体实现留待后续。

## 状态流

问答模式：RECEIVED → VALIDATED → RETRIEVING → GENERATING →
EXTRACTING_CLAIMS → VERIFYING → DECIDING。

审核模式：RECEIVED → VALIDATED → EXTRACTING_CLAIMS → VERIFYING → DECIDING。

VERIFYING 并行调度证据验证与电力审核；同一回答版本冻结不变。
DECIDING 由确定性 AuditPolicy 进行决策，不设额外裁决 Agent，也不采用多数投票。

- PASS → COMPLETED。
- REVISE 且预算允许 → REVISING → EXTRACTING_CLAIMS → VERIFYING。
- INSUFFICIENT_EVIDENCE 或 REVIEW_REQUIRED → REVIEW_REQUIRED。
- 达到修订轮数或其他预算 → REVIEW_REQUIRED，记录未完成审核。
- 不可恢复执行错误 → FAILED；用户取消 → CANCELLED。

所有非终止状态允许中断到 FAILED、CANCELLED 或 REVIEW_REQUIRED。
状态图仅声明合法边；任务模式、预算和决策对应的迁移守卫未实现。
初期每次修订重新审核完整回答，不采用尚未验证的局部审核优化。

## RAG 与工具权限

Generation 使用生成检索；Evidence Verification 允许独立支持/反证检索；
Power Domain Review 检索标准、约束及规程；Revision 仅围绕审核缺口检索。
每次检索与工具执行均经过 Harness 提供的受控适配器，累计预算和记录轨迹。

证据验证可用引用核验、引用支持匹配和 NLI；电力审核可用单位/数值检查、
安全规则、约束验证及具备输入条件的工程仿真；生成和修订仅获得必要的
基础计算与有限检索权限。当前 ToolSpec.read_only 默认 True，未提供生产控制工具。
工程输入不足时返回 not_assessable 或缺失前提，不声称工程验证已完成。

## 迁移路线

1. 在这些接口后实现旧审核器适配，固定样例，保留原行为作为基线。
2. 单独修正句级证据归属、数值解析、引用失败状态和安全规则问题。
3. 实现 Harness 和审核已有回答的 API，再接 RAG 与 Generation。
4. 加入 Revision 和有限循环，保存全流程版本及轨迹。
5. 在 evaluation 对比旧系统、RAG、协同审核和完整框架。

当前可运行假 Agent 的离线流程，但没有真实可信问答服务；预算默认值须经实测校准。
