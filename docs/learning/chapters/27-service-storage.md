# 27 接单、存储、停服与旧版本读取

本专题绑定应用提交 `e4fb27e7c8893a5ad141ebef0ae5f32216648065`，2026-11-24离线核对。配置只看[当前状态](../../current-status.md)。数字分别标记真实实验与教学构造；以下问题不授权现场工程操作。

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
