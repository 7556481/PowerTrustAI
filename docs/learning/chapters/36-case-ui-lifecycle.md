# 36 前端与生命周期：迟到响应怎样不再改错任务

本页复用[2026-10-27维护证据](../../maintenance/product-polish-ui-code-hygiene-v1.md)及其验证清单。页面均为synthetic_fixture，未证明审核语义收益。配置统一见[当前状态](../../current-status.md)。

## 故障一：旧任务收尾时，新任务仍在读取
先做[第28章的返回顺序基础题](28-browser-consistency.md)，本章接着查异步操作的收尾。即使旧响应已经被 epoch 守卫丢弃，退出 `try` 后仍会执行 `finally`。如果它无条件把 `reading` 置为 false，就可能允许另一轮读取抢在当前读取之前启动。

[app.js](../../../backend/static/app.js) 的 `load` 给每次主读取建立独立 `owner`。返回值用 epoch 检查是否仍属于当前任务；清锁和安排下一次轮询则要求 `reading === owner`。旧连接返回的 401 也要匹配发出时的连接与 epoch，才可清除连接状态。

## 故障二：辅助请求一直没返回
假设trace GET一直挂起，state/result已经能读到首稿。若用一个Promise.all把它们绑在一起，正文就被trace卡住；“失败后暂停重试”也救不了尚未失败的请求。后续改为单一主state/result周期，trace/reviews/NLI各有独立slot、最多一个在途和有界补刷，切换任务取消旧读取。

这样主结果可以更新，辅助内容显示待查/失败而非阻塞正文。反馈提交后reviews revision推进，旧列表不能覆盖新追加；这仍是原有调度机制里的隔离，不另建第二套全局轮询器。POST提交不自动重试，受理未知锁不会因一次GET成功解开。

## 故障三：服务停止处理，但终态没写进去
教学注入：worker正在处理R，关闭/资源drain失败后内存知道R应中断，但Store.mark也失败。内存可有pending_terminal_status=interrupted，DB却仍running。若页面只显示“已中断并保存”，就把内存推断冒充持久化事实。

[service.py](../../../backend/service.py)保留volatile_errors/storage_fault及未确认状态；页面展示persistence_confirmed=false与pending终态，允许已保存答案仍可读。服务停止接新POST，health degraded；Store写失败不能靠前端改字变成落库成功。重启recover能将旧queued/running标PROCESS_INTERRUPTED，但没有断点续跑模型。

资源顺序也有边界：cancel请求→协程收尾→底层HTTP drain→close，之后queue.task_done和active清理各有finally职责。取消确认明确termination_guaranteed=false，因为远端可能已受理。任务业务失败但资源清理正常时，下一任务仍可执行；生命周期故障则需拒单，不能一律继续。

::: answer 题36.1：A的GET超时返回时，用户已切B；应给B显示“任务可能已受理”吗？
不应。先按epoch/读取归属丢弃A异常；其次GET是只读，失败不等于POST受理未知。只有发出的提交POST在未确认响应时才涉及重复受理风险。即使A是当前任务，也应提示读取失败，保留已保存内容，不引导自动重发模型请求。验证入口[异步探针](../../../tests/ui_async_probe.js)交换返回顺序，检查正文与锁，而不是只看最终一个截图。
:::

::: answer 题36.2：页面有初稿且pending interrupted，是否能计完整审核？
不能。初稿保存证明生成对象存在；pending且persistence_confirmed=false说明最终处理未确认落库；事实/领域是否完整还须看保存的阶段与报告。不能用可读正文替完整链计数。验证应同时注入Store失败与关闭失败，核对拒新单、旧历史仍可读、在途释放与下一任务策略；入口[test_backend_lifecycle_api_v4](../../../tests/test_backend_lifecycle_api_v4.py)。
:::

<a id="返回顺序演算先写四项结果"></a>

## 故障推演：旧锁、挂起辅助读取与未保存终态

|事件|诊断页观测|
|---|---|
|t0|任务 A 的主读取仍在途，持有 ownerA|
|t1|切到 B，B 的主读取取得 ownerB；旧 GET 的取消未及时生效|
|t2|A 的请求结束，进入 `finally`。B 的主读取仍未返回|
|t3|B 的 state/result 返回 `running` 和已保存初稿，B 的 trace GET 一直未返回|
|t4|下一轮主读取返回数据库状态 `running`，并带有 `pending_terminal_status=interrupted`、`persistence_confirmed=false` 与生命周期故障码|

分别写出 t2 的锁归属、t3 下一轮能否启动、t4 页面文案与轮询决定。已知本例没有启用 NLI 诊断。

::: answer 展开故障推演解析
1. t2 时 `reading` 仍是 ownerB。A 的 `finally` 因 `reading !== ownerA` 跳过清锁和调度。若无此检查，主读取的互斥条件会被提前解除。
2. t3 的 `load` 不等待 `requestAuxiliary('trace')`。B 自己的 `finally` 释放主锁后，`schedulePoll` 看到当前上下文仍在运行，安排下一次主读取。trace 持有自己的 `slot.inflight`，新一轮会跳过尚未完成的 trace。
3. t4 的 `pendingStopped` 成立，页面说明“已停止处理；中断状态尚未确认保存”，同时交代数据库原状态并保留可读初稿。主上下文不再按 `running` 持续轮询，可以手动查状态；生命周期故障关闭新任务提交。

可用[异步探针](../../../tests/ui_async_probe.js)核对旧请求清锁和慢辅助读取，用[生命周期 API 测试](../../../tests/test_backend_lifecycle_api_v4.py)核对终态未确认与拒单。
:::
