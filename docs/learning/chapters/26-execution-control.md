# 26 图编排、关键路径与资源所有权

本专题绑定应用提交 `e4fb27e7c8893a5ad141ebef0ae5f32216648065`，2026-11-24离线核对。配置只看[当前状态](../../current-status.md)。数字分别标记真实实验与教学构造；以下问题不授权现场工程操作。

## 先区分图、业务对象与线程
LangGraph是阶段路由器；Harness与RunExecution持有单次业务运行、预算、证据及取消控制。线程是能执行同步HTTP或数据库工作的执行单元；asyncio任务是协作调度的协程，创建task不等于HTTP已在另一线程发出。
[graph_runtime_v1](../../../harness/graph_runtime_v1.py)的FlowState只有business_state、last_stage、next_stage；大业务对象在runtime context的execution里。七阶段复用RunExecution，checkpointer=None，禁远程tracing，不应宣称LangGraph提供业务持久恢复。

## 一次请求的边
validate_saved_inputs→generate或extract_and_tools；生成后提取/工具→prepare_review→review_pair→merge_and_decide；有资格才revise，新版回extract_and_tools。图不为业务节点自动重试，防止重复付费。[顺序驱动](../../../harness/execution.py)保留相同阶段，供兼容/离线对照；切换必须显式配置，图依赖失败不会偷偷降级。

::: answer 题26.1：overlap提前了什么？事实输入依赖领域材料吗？
prepare_review先完成事实目的检索，然后冻结事实证据、原引用和绑定，满足开关/模式/调用余量条件才创建早期事实审核。随后领域目的检索继续，review_pair复用早期事实任务并与领域审核汇合。事实证据不会被后续领域结果扩大，事实内部仍serial_v1。相关代码在[prepare_review/review_pair](../../../harness/execution.py)，受管开关见[managed](../../../backend/managed.py)。继续追问：只看create_task不足，须核对事实HTTP工作线程启动早于领域读取结束，旧真实轨迹与[test_fact_domain_overlap_v23](../../../tests/test_fact_domain_overlap_v23.py)分别提供真实与离线层证据。
:::

::: answer 题26.2：领域检索失败时已经发送的事实请求怎么办？
异常分支取消early task并gather等待协程收尾；底层HTTP执行可能仍在进行，Bundle.drain观察资源_active直到完成，再close。完成、取消与释放不是同一个时刻。运行不能因事实部分结果有效就标完整审核。[资源装配](../../../backend/assembly.py)、[execution.run](../../../harness/execution.py)及[生命周期测试](../../../tests/test_backend_lifecycle_v4.py)应一起读。继续追问：吞掉CancelledError会破坏取消语义；但立即关资源也可能破坏结算，因此清理需有明确所有权。
:::

::: answer 题26.3：两个10秒为什么不是20秒？
关键路径是决定最终结束时间的最长依赖路径。教学：事实输入t=2齐、HTTP持续10秒到12；领域读取2→6、审核6→11，则终态12；读取瞬间完成后仍由事实12决定，终态不变。若原先事实要到6才发，原终态16，提前可省4秒。必须在同一次运行的依赖图推导，不能把角色耗时相加。继续追问：预算不足、用户取消、阶段超时分别有不同原因记录；节省模型调用之外的检索并不必然缩短终态。
:::
