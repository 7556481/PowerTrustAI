# 最小离线 Harness

## 运行

从 D:\PowerTrustAI 项目根目录运行，Python 3.11+，仅使用标准库，无须安装依赖：

```powershell
python -B -m harness.demo
python -B -m unittest discover -s tests -v
```

项目 .venv 解释器可以正常运行。受限沙箱执行身份无法访问其关联的基础 Python，
导致启动失败；这属于沙箱访问限制，不能据此判定环境损坏或基础 Python 缺失。
未激活环境也不影响通过绝对路径调用解释器。

项目解释器运行命令（工作目录为 D:\PowerTrustAI）：

```powershell
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -B -m harness.demo
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -B -m unittest discover -v
```

2026-10-02 验证记录：两条命令在受限沙箱中均返回退出码 101，原始报错分别为：

```text
Unable to create process using '"D:\PowerTrustAI\.venv\Scripts\python.exe" -B -m harness.demo': ?????
Unable to create process using '"D:\PowerTrustAI\.venv\Scripts\python.exe" -B -m unittest discover -v': ?????
```

其中问号为工具实际返回文本。通过工具审批机制提升权限后，使用同一项目解释器
重新执行成功，没有修改目录权限、删除或重建环境。

| 解释器与执行条件 | demo | unittest | 记录 |
| --- | --- | --- | --- |
| 项目 .venv，受限沙箱 | 启动失败，退出码 101 | 启动失败，退出码 101 | 2026-10-02 本次执行 |
| 项目 .venv，审批后提升权限 | 七个场景完成，退出码 0 | 根目录完整发现，16 项全部通过，退出码 0；耗时 1.405 秒 | 2026-10-02 本次执行 |
| Codex 随附解释器，受限沙箱 | 七个场景完成，退出码 0 | 使用 -s tests 发现，16 项全部通过，退出码 0；耗时 0.338 秒 | 此前离线 Harness 验证，不替代项目环境验证 |

项目解释器版本已确认是 Python 3.13.2。随附解释器此前验证所用命令：

```powershell
& 'C:/Users/37307/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -m harness.demo
& 'C:/Users/37307/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -m unittest discover -s tests -v
```

demo 输出七条 JSON 记录，包含审核决策、回答版本、问题代码、逐步状态、耗时和终止原因。
不会保存报告到磁盘，不访问网络。假证据明确标记为 synthetic_fixture。

## 实现边界

- core/validation.py 校验嵌套类型、不可变元组、枚举、非空字段、回答版本、
  文本区间、证据冲突、主张/发现唯一 ID、引用完整性及修订版本连续性。
- 用户输入和预算错误抛出 InputError，执行前停止，没有业务审核结论。
- 无效组件输出记为 OUTPUT_CONTRACT_ERROR；其他执行异常记为 EXECUTION_FAILURE；
  超时为 TIMEOUT。执行问题保存在 HarnessResult 和报告中，不等同于 contradicted。
- harness/runtime.py 支持问答和已有回答模式；retriever=None 时维持输入证据直接传递的离线路径。
  真实 Retriever 可选注入、固定版本和预算控制见 [harness-retrieval.md](harness-retrieval.md)。
- 两类审核并行调用，使用同一冻结回答和主张元组。单方失败只丢弃该方无效输出；
  另一方结果保留，最终要求人工审核。未完成检查不能放行。
- 修订保持回答 ID、版本加一。重新提取主张，两类审核完整重跑。
- 记录状态迁移、步骤、输入输出引用、回答版本、执行状态、耗时、修订说明和终止原因。
  最终报告只包含最后一版审核；历史版本通过轨迹引用追踪，尚无完整历史快照存储。
- 支持总运行时限、单步超时、Agent 调用上限和修订上限；支持运行取消。
  max_model_calls 在离线模式计数四类 Agent 调用，不计数主张提取服务。

## 确定性策略顺序

1. 任一审核有执行问题 → review_required。
2. 高风险领域发现或缺失工程前提 → review_required。
3. 任一主张证据不足或无法评估 → insufficient_evidence。
4. 存在事实冲突或低/中风险领域发现 → revise；达到修订上限则 review_required。
5. 全部主张有证据支持且领域审核无未解决问题 → pass。

pass 终止于 COMPLETED；证据不足与人工审核终止于 REVIEW_REQUIRED，但保留不同业务决策。
生成或主张提取失败终止于 FAILED；审核失败仍生成部分结果报告。
修订失败保留上一版报告和有效发现，终止于 REVIEW_REQUIRED。

## 假组件配置

agents/fakes.py 的 FakeConfig 可设置草稿、按调用次序变化的事实状态和领域严重度、
审核延迟、执行异常及无效证据/主张 ID。序列耗尽后沿用最后状态。
FakeClaimExtractor 把全文作为一个主张，可配置错误区间。
FakeRevisionAgent 仅执行确定性文字修改，不代表真实回答质量提高。
所有组件通过构造函数注入，后续实现应遵循既有 Protocol。

## 验证范围

tests/test_harness.py 验证：两模式通过、一次修订通过、证据不足、超时保留另一方、
执行失败保留另一方、修订上限、无效 ID、输入错误、错误区间、强制人工审核、
调用/时间预算、无效修订、取消、旧版本输出、无支持证据、重复发现 ID、
证据 ID 冲突、生成失败及修订引用错误。

## 尚未实现

真实模型、工程工具及旧审核器适配；HTTP API；运行持久化、恢复和完整历史快照；
工具预算与权限的实际执行；临时失败重试；场景注册表、规则和工具结果注册表；
外部知识权威性判断与领域校准。工具结果 ID 当前禁止使用，因为没有工具执行记录。
max_tool_calls、max_transient_retries 保留为接口字段，当前不会实际调用或重试这些能力。
max_retrieval_calls 和单次/累计证据字符预算在启用 Retriever 时实际执行。
单步计时限制的是合作式异步组件；不提供进程隔离，阻塞 Agent 代码可能阻塞事件循环。

独立 Markdown/SQLite/BM25 检索与 Evidence 回查已实现，运行及本轮 30 项回归结果见
[markdown-retrieval.md](markdown-retrieval.md)。Harness 的上述限制和调度保持不变。

文本型 PDF 入库及本轮 40 项回归结果见 [pdf-retrieval.md](pdf-retrieval.md)。
PDF 解析依赖只按需加载；关闭 site-packages 的 -S 模式下，原有 30 项测试及七个 demo 场景仍通过。

页内切分与相邻上下文阶段：项目 .venv 全部 51 项通过；-S 下 33 项及七个 demo 通过。
详见 [pdf-retrieval-quality.md](pdf-retrieval-quality.md)。Harness 调度和假 Agent 未改变。

Retriever 接入阶段：项目 .venv 全部 74 项通过（保留原有 51 项），-S 下 56 项中
55 项通过、1 项可选 PDF 样例跳过，七个原 demo 通过。新接口默认值兼容离线调用；
实际官方索引与模拟 Agent 的验证见 [harness-retrieval.md](harness-retrieval.md)。

结构化生成阶段增加可注入模型接口与 generation_only，未配置/验证真实供应商服务，
参见 [generation-agent.md](generation-agent.md)。原离线 demo 和默认审核路径保持兼容。
本阶段项目解释器完整回归 89 项通过（保留原有 74 项）；-S 回归 71 项中
70 项通过、1 项可选 PDF 样例跳过。模型测试均为模拟响应，不代表真实服务验证。
