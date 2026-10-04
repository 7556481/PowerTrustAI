# 并发模型轨迹归属修复 v1

2026-10-04，复核当前e1042cdb/fb235746，而非526bdee。共享ModelBudget的计数本身正确，但 `OfflineHarness.invoke` 用 `records[before:]` 收集记录，两条并行审核的时间窗重叠。公开探针在基线得到2次实际请求、3条model_request轨迹；不是新增付费请求，而是观察归属重复。

`services/structured_model.py` 同样使用列表切片返回阶段记录，因此一并修复。现在：

1. 每次Harness阶段调用生成独立 `invocation_id`，通过ContextVar传递 `component` 和 `answer_version`；`asyncio.wait_for`及子任务继承该上下文。
2. ModelClient在请求开始捕获归属，在finally保存ModelCallRecord；共享预算的实际 `call_number`、用量与失败状态不改变。
3. Harness仅为本次invocation记录生成轨迹；引用为 `run_id:model:call_number`。同阶段纠正请求属于同一invocation但不同call_number。
4. structured_request按本次实际请求编号返回记录；输出失败诊断也根据异常携带的安全请求编号寻找对应记录，而非取共享列表末项。

新增三个可选字段 `invocation_id/component/answer_version` 均默认None，旧记录可恢复，不补造旧归属，不迁移或重写旧响应。API JSON属于增量元数据，现有页面读取原字段兼容。失败、取消和超时仍写入调用清单，不过滤轨迹来制造一致性。

公开回归：

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_model_trace_attribution -v
```

同提示版本并发审核、一次格式纠正及初始无效记录、模型超时、Harness阶段超时造成的transport取消、运行取消、旧记录兼容分别断言：实际调用数=轨迹条数；编号集合一致；引用唯一；归属与回答版本正确；阶段返回记录不跨路混入。记录顺序反映实际完成顺序，不要求并行请求按编号完成。

这是工程观察准确性修复，不修改事实支持标准、检索排名或政策；本轮无付费运行。验证证据位于忽略目录 `data/runtime_local/public-repro-v1/`，基线失败日志与修复日志分别保留。
