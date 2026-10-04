# PowerTrustAI 闭环验收准备基线

本轮不扩展模型输出契约、不新增 Agent、不调整 BM25，也不更改旧项目或历史记录。
验收准备脚本只协调实验阶段，所有审核与重审复用现有 Harness，Revision 调用现有 Agent。
分阶段保存并非新增产品调度器；缺少任何阶段不得标记完整闭环。

## 版本固定与真实成功版本

当前代码以 acceptance-baseline-v1.json 的逐文件 SHA-256 和集合指纹固定。
新项目根目录没有 Git 提交可用，不编造 commit。旧原型 Git 版本不能充当新项目版本。
历史试运行没有完整代码快照，无法从提示词标签精确恢复所有历史源代码。

历史真实完整链路为 stability-minimal-v2 的首轮审核/Revision
加 stability-minimal-v3-rereview 的新重提取与双重审，通过源文件 SHA 链接。
契约为 evidence-verification-output-v8.2、power-domain-review-output-v2、
revision-output-v2；主张提示词 atomic-claims-v4-explicit-components；
生成提示词 evidence-bound-generation-v3-answer-units；领域规则 power-demo-rules-v1。
历史首轮证据审核采用 v8.1，最后成功重审采用 v8.2，不能将前者改写成 v8.2。
旧归档中的 checker_version 仍沿用严格解析器 v7.1 的标记；
实际请求契约/提示词以 model_records 和原始响应归档为准，不能只看 checker_version。

当前基线比历史成功试运行多了一项领域交付收紧：
只交付本轮领域检索与显式用户材料，保存回答附带的旧索引材料不自动并入。
提示词标签相同不意味着运行代码相同；以 harness/runtime.py 文件 SHA 区分。

本轮第一批真实验证 acceptance-real-v1 使用上述冻结基线，19 次请求：
领域交付验证通过、两个构造场景首轮完成，工程场景重审的两个混合 finding
因缺少显式快照依据及引用空 bases 的索引而拒绝。
用户随后授权追加请求。追加运行前保存 acceptance-baseline-v2.json，
证据输出契约仍为 v8.2，提示词改为
evidence-verification-v8.2.1-complete-basis-examples：
仅补充既有类型的合法例子和零基局部索引说明，并增强具体错误反馈。
没有新增依据类型、字段、状态或 Agent，不自动补造依据；
真实历史初次与纠正响应重放仍失败，且字段路径/约束一致。
追加实验只重新审查保存的工程修订和修订/重审已完成首轮的数量单位场景。

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m evaluation.acceptance_trial --live --max-requests 30 --baseline acceptance-baseline-v2.json --continue-from D:\PowerTrustAI\data\retrieval_local\deepseek\acceptance-real-v1.json --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 --output D:\PowerTrustAI\data\retrieval_local\deepseek\acceptance-real-v2.json

这里 30 是此次追加实验自行设置的硬上限；不将旧 19 次混为新请求。
所有阶段继续检查最坏请求数；历史请求与失败状态保持不变。

追加 v2 实验实际 12 次：工程闭环完成，数量/单位重审发现上游把输入描述
冻结为 technical_fact、下游却选择快照依据的问题。v3 基线保持原契约，
提示词 evidence-verification-v8.2.2-frozen-category-boundaries 明确示例：
对冻结分类有异议只能显式 classification_issue + not_assessable，
不得自动改类别，也不得用快照支持技术事实，连 insufficient_evidence
状态也不能携带非法快照索引。离线归档仍按原失败保留。
continuation 跳过已完整工程闭环，仅对保存的数量/单位修订做完整重提取与双重审。
这次按两条实际引用预留最多 10 次；若同一针对性错误仍重复，停止该场景。

v3 的重新提取两次响应均失败，未执行新审核。再次追加实验使用显式
--reuse-frozen-extraction，仅复用 v2 中同一回答 ID/版本/完整正文及引用、
同一知识版本的真实已接受提取结果；SHA 校验私有归档祖先链，重新运行双审核。
它是验收实验有效阶段的复用，不是新 Agent、产品缓存或新提取成功。
不得把 v3 的失败记录改写为成功；完整链路报告需明确指出提取来自 v2。

知识固定为：

    k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55

规则保留演示标记、来源、版本及适用范围，无实际工程仿真和安全认证。

## 预算与真实试运行

运行前先保存离线基线及历史逐发现对照；任何工具不读取 .env。
仅显式 --live 实验入口允许程序加载 .env 鉴权，不输出密钥或请求头。

已冻结回答的单轮重提取与双审核最坏请求数：

    2 × (主张提取 1 + 独立证据审核 1 + 领域审核 1 + 原引用绑定数)

每项包含一次格式纠正；原引用按实际绑定数分别请求。
已保存最小回答有一个绑定，首个调整验证预留 8 次。
随后两个构造错误回答均无伪造原引用，各自首轮预留 6 次。
Revision 本身预留 2 次；其返回的实际引用数只有冻结输出后才能知道，
因此重审必须再次按实际引用数做最坏预算检查。
不能假定提示词建议的短回答一定只有一个引用，不能用预计平均请求数冒充上界。
25 次是整个新实验的硬上限；若不足，保留已执行阶段，明确未启动/未完成部分。

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m evaluation.acceptance_preparation
    & D:\PowerTrustAI\.venv\Scripts\python.exe -m evaluation.acceptance_trial --live --max-requests 25 --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 --output D:\PowerTrustAI\data\retrieval_local\deepseek\acceptance-real-v1.json

命令仅适用于首次创建这些新文件；再次试验必须用新版本文件名及重新授权的预算。
普通 unittest 不发起付费请求。

## 后续正式路线，本轮不实现

1. 可替换 Embedding 适配层、模型版本/维度/归一化记录及向量索引派生版本；
   不把新向量版本覆盖现有固定 BM25 快照。
2. 混合检索：分别保存关键词与向量排名、融合方法及版本，
   用独立人工检索标注验证，再评估是否接入 Harness。
3. 证据支持判断微调：基于人工核对的支持、冲突、缺证据、
   条件/否定/地区边界与错误原引用数据；严格区分训练、开发、独立验收问题族。
   不以当前模型标签自动生成“正确答案”，不因微调降低 ID/原文/版本约束。
4. 在现有闭环验收之后再讨论演示规则如何转成有来源的生产领域审核规则；
   不恢复旧六维评分、默认参考文本或未经审查的阈值。
