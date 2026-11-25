# 36 前端与生命周期：迟到响应怎样不再改错任务

本页复用[2026-10-27维护证据](../../maintenance/product-polish-ui-code-hygiene-v1.md)及其验证清单。页面均为synthetic_fixture，未证明审核语义收益。配置统一见[当前状态](../../current-status.md)。

## 故障一：旧A响应覆盖新B
教学时序：t0选择A并发GET；t1切到B，epoch递增；t2 B先返回并展示；t3 A迟到。如果回调只写全局result，用户看到标题B却是A的答案/引用。仅禁用选择按钮会把用户困在慢A，不能解决归属。

[app.js](../../../backend/static/app.js)在请求发出时捕获任务/连接epoch与读取身份，返回及finally均检查是否仍属于当前选择。A迟到既不能写正文，也不能让旧finally释放B的新请求锁。Abort旧GET减少浪费，但取消可能发生在响应已送达之后，所以仍需要归属守卫。

|事件|当前选择|回调归属|允许动作|
|---|---|---|---|
|A发送|A|epoch1/A|等待|
|切B|B|epoch2/B|建立B读取|
|B返回|B|epoch2/B|绘制B及其版本|
|A迟到|B|epoch1/A|丢弃，不写正文、不清B锁|

同一连接令牌也有epoch问题：旧401不能注销后来成功建立的新连接。归属不只是run_id，还包括连接生命周期。

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

## 返回顺序演算（先写四项结果）

教学日志：t0打开A，epoch=7，发GET A；t1切B，epoch=8，发GET B；t2 B返回并保存正文B；t3 A返回。请写出t3对象归属、最终页面、Abort失败的影响、复制来源。

::: answer 展开返回顺序解析
A响应属于发送时A/epoch7，当前选择是B/epoch8，不能写回视图或释放B的新读取锁。页面继续显示B；Abort只是减少无用工作，归属检查负责正确性。复制从当前所选版本保存的text取，不从带标注卡的DOM取。这里epoch数字是教学构造，实际守卫见backend/static/app.js的请求身份与选择归属，以及inline_review.js的版本核对；GET失败不能显示POST受理未知。
:::
