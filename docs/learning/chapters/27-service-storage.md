# 27 接单、存储、停服与旧版本读取

本专题绑定应用提交 `e4fb27e7c8893a5ad141ebef0ae5f32216648065`，2026-11-24离线核对。配置只看[当前状态](../../current-status.md)。数字分别标记真实实验与教学构造；以下问题不授权现场工程操作。

## 一个POST怎样变成可查询的任务
教学请求体是`{"question":"说明无功对电压的作用"}`，其余字段由[Submit](../../../backend/api.py)的默认与校验处理；不是客户端指定数据库、模型端点或Factory。RESTful在这里指用资源路径与HTTP方法区分操作，不是所有接口都必须CRUD齐全。

POST /runs通过鉴权、请求体大小与类型检查，body.task生成TaskRequest，再交ReviewService.submit。源码主干如下（省略NLI和既有引用解析）：
```python
async with self.lock:
    self.require_accepting()
    if self.queue.full(): raise QueueFullError('Waiting queue is full')
    rid = uuid4().hex
    self.store.create(rid, request, manifest)
    self.queue.put_nowait((rid, request, knowledge, requirements, indexed_ids))
```
lock防同一事件循环中并发提交穿过容量检查，不是数据库事务锁；store.create自己的BEGIN IMMEDIATE负责run行与对象索引原子保存。保存成功后放入内存queue，二者不是跨进程分布式事务。POST返回202与run_id仅表示已受理，不能读作模型已完成。响应里的queued也可能在浏览器收到时已经变running。

## 跟着一条run观察数据变化
|时刻|内存|runs行|objects/events|用户能确认什么|
|---|---|---|---|---|
|提交通过|queue含rid|queued、request、config|请求对象已索引|202返回后知道受理标识|
|worker取出|active=rid、Bundle归属rid|running、started|逐阶段追加|可GET状态，尚无完整答案|
|生成保存|execution持有v1|snapshot推进|Answer v1、Evidence、生成事件|result可读初稿，不等于审核完整|
|双审/修订|审核对象或v2|harness_state/checkpoint推进|意见与对应版本保存|必须显示所审版本|
|最终保存|result构造完成|mark终态及result|已有阶段对象不重写|已保存终态可查询|
|资源收尾|drain/close、task_done|可能另有生命周期故障|检索计时等收尾写入|保存答案与服务可接单分别确认|

GET /runs/{id}查状态，GET /result有answer时200、尚无时202；404是作用域对象不存在，409是绑定冲突；422表示输入/合同不合法，429队列满，503配置/生命周期/Store不可用。不同错误要保留机器code；不能一律自动重发POST。HTTP超时只代表客户端没及时得到响应，提交是否发生可能未知。

## 为什么用参数化SQL和短事务
[RunStore.create](../../../backend/store.py)使用`VALUES (?,?,?,?,?)`配参数tuple。用户问题是数据，不拼进SQL语法；这样也保留Unicode和引号。`with self.tx()`内部BEGIN IMMEDIATE，成功commit，异常rollback；没有跨云端等待持锁，避免几十秒HTTP把其他写入堵住。

SQLite连接默认归创建线程；event-loop Store由该线程访问。检索to_thread工作用自己的只读连接，不能随手传store.db进去。WAL改善读写共存但仍只有有限写入竞争；索引加快筛选/排序也有写入与磁盘成本。查询LIMIT不意味着不扫候选，见[检索SQL](23-search-boundaries.md)。

::: answer 题27.4：store.create已提交，但返回202的网络断开，用户能否认为任务没提交？
不能。按表任务可能仍在queue或running，响应丢失只让客户端确认失败。应保留未知提交状态，允许只读历史/查询，不自动创建第二条。若进程随后退出，recover把queued/running记interrupted，不透明续跑。验证分别注入API响应丢失、Store失败和worker关闭；它们不是同一种故障。入口[test_local_service](../../../tests/test_local_service.py)与[test_backend_lifecycle_api_v4](../../../tests/test_backend_lifecycle_api_v4.py)。
:::

## 从提交到持久化
[API](../../../backend/api.py)校验请求、会话和边界，[ReviewService.submit](../../../backend/service.py)核对接单与队列容量、建立run并入队，worker逐个执行；Factory每次构造运行资源，observer把阶段对象和checkpoint存入[RunStore](../../../backend/store.py)。queued/running/finished等运行状态与答案/审核对象分开保存。
事务是短SQLite BEGIN IMMEDIATE/commit/rollback；不要持有写事务跨云端等待。WAL允许读写更好共存，不使单连接可跨任意线程。RunStore设计为事件循环线程使用，检索线程要管理自己的连接。

::: answer 题27.1：POST断网能否重发？这是幂等问题吗？
幂等指同一意图重复执行不会产生额外效果；项目没有证实通用跨重启提交去重协议。响应丢失时客户端无法断言服务未建立任务，盲重发会多跑一次并付费。前端保留提交状态未知并停止自动POST重试，历史/health只读查询不等于补发。继续追问：若设计幂等键，需绑定请求内容、持久事务和相同响应，不能只在内存记录一个UUID。本段为扩展设计，非已实现能力。
:::

## 运行对象与旧历史
runs保存请求、配置、状态和snapshot/result；events按run与ordinal记录阶段；objects按kind、id、answer_id/version绑定；reviews追加反馈。旧历史读取走[serialization](../../../backend/serialization.py)和[presentation](../../../backend/presentation.py)兼容分支，不能借读历史重新调用模型或覆盖旧判断。证据回查同时核验run、证据ID及版本，知识库当前内容不能冒充旧回答当时证据。

::: answer 题27.2：重启能恢复到模型调用中间吗？
不能。RunStore.recover把queued/running记interrupted/PROCESS_INTERRUPTED，保存的版本与事件仍可读；不存在远端模型事务恢复或透明重放。已保存初稿与终态中断不冲突。Store写入失败另有StorageError和persistence_confirmed/pending状态，内存知道失败不代表已落库。继续追问：必须以实际GET和DB记录区分“已保存”与“界面已看到”，服务端时间不能替代浏览器观测。
:::

::: answer 题27.3：drain、worker与拒单怎样衔接？
ReviewService停止接单后处理取消/队列收尾，等待在途资源，关闭失败形成生命周期故障。health不只看端口监听，还涉及配置、Store和worker可接单状态；服务故障不应阻止仍可读历史。见[服务生命周期实现](../../../backend/service.py)、[API故障测试](../../../tests/test_backend_lifecycle_api_v4.py)。继续追问：队列满、配置失败和未知提交不是同一种错误，不能统一提示“再试一次”。
:::

## 本地访问的边界
[local_access](../../../backend/local_access.py)与[local_session](../../../backend/local_session.py)区分引导令牌、浏览器会话和本机访问范围；这些都不是模型API凭据。只展示脱敏配置字段，不把.env、请求头或会话写进截图和公开报告。无认证静态壳不代表运行API或私有知识库可公开访问。
