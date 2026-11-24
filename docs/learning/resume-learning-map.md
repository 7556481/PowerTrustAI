# 最终交付能力学习索引

按2026-11-24学习需求组织，不复制简历或联系方式，不认证个人参与程度。配置见[当前状态](../current-status.md)。每项先读正文的输入、源码、状态变化、异常与验证，再做题。

|能力|完整正文|实现入口|练习|
|---|---|---|---|
|Python、LangGraph、协程/线程|[26章](chapters/26-execution-control.md)|[harness/graph_runtime_v1.py](../../harness/graph_runtime_v1.py)|题26.4|
|大模型API、Prompt、结构校验|[24章](chapters/24-model-wire.md)|[model_adapter/deepseek.py](../../model_adapter/deepseek.py)|题24.4|
|FTS5、BM25、来源/范围|[23章](chapters/23-search-boundaries.md)|[rag/corpus_index.py](../../rag/corpus_index.py)|题23.1—23.3|
|提取、事实/领域、修订资格|[25章](chapters/25-agents-semantics.md)|[services/claim_obligations.py](../../services/claim_obligations.py)|题25.4/31.1|
|FastAPI、REST、后台任务|[27章](chapters/27-service-storage.md)|[backend/api.py](../../backend/api.py)|题27.4|
|SQLite版本、轨迹、反馈|[27章](chapters/27-service-storage.md)|[backend/store.py](../../backend/store.py)|题27.2/36.2|
|预算、超时、取消、重审|[37章](chapters/37-protocol-ledger-lab.md)|[model_adapter/runtime.py](../../model_adapter/runtime.py)|题37.2—37.4|
|并行与性能定位|[35章](chapters/35-case-overlap.md)|[harness/execution.py](../../harness/execution.py)|题35.1/35.2|
|回归、固定样本、漏检|[29章](chapters/29-evaluation-math.md)|[tools/public_checks.py](../../tools/public_checks.py)|题29.4|
|Git、PR、CI与维护|[30章](chapters/30-maintenance-practice.md)|[tools/learning_checks.py](../../tools/learning_checks.py)|题30.4|

## 首读顺序与自检

24模型请求→25审核对象→26执行控制→27任务与Store→31修订授权→35时间线→37正式解析样例。每项需回答使用位置、输入输出、代码运行、选择理由、失败处理、验证及限制。遇到题号跨章时按相应案例阅读。

D/O是历史候选，不是正式默认；overlap理想计算有资源不变假设；旧历史重启只标中断，不透明重跑模型。主路径已补连续讲解，所有历史schema和动态实验开关仍不是穷举范围。

## 历史、进阶和其他经历

[Dense/RRF](chapters/06-retrieval-math.md)、[训练/Transformers](chapters/12-training-nli.md)、[NLI](chapters/13-local-nli.md)保留历史与进阶身份，不作为最终系统首读要求。

[其他前端与数据基础](chapters/38-adjacent-foundations.md)只讲技术原理与教学练习，不把React/TypeScript/Pandas写成PowerTrustAI实际运行栈。其他项目的功能和个人职责按本机简历自述，团队分支、冲突、覆盖率、实习操作细节仍需本人记录；公开手册不复制个人经历材料。
