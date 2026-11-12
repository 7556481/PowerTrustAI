# 本机8765有限启用：事实审核与领域检索重叠 v25

2026-11-12，用户明确批准本机8765有限启用。正式起点是远端master 3cb0535；根目录原02f85c9与它源码树一致。PR #6保留研究沿革，本次独立PR只选择已验收的v23 Harness调度、受管Factory及回退，不引入Tantivy或任何审核合同/提示/政策改动。

## 发布边界与入口

通用ComponentFactory及无本机配置时的日常入口均使用普通Factory。仅本机忽略data/runtime_local/managed-service.json选择overlap。日常双击D:\PowerTrustAI\start-powertrustai.cmd；同路径rollback-overlap.cmd优雅停止空闲服务、把同一个配置的factory改为component，并以同端口/Store/认证路径重新启动。不强杀任务，不复制示例8779路径到正式配置。

正式SQLite BM25/topic_v4_subject_v1、schema13、deepseek-flash、事实serial_v1、baseline审核、原production生成/修订/双审政策均保留。受管orchestration仍langgraph_v1。正式Store为D:/PowerTrustAI/data/runtime_local/runs.sqlite3，诊断及调用usage在D:/PowerTrustAI/data/retrieval_local/service_private。正式起点没有全局FullBudget批次门禁：原每任务RunBudget及Store snapshot/result预算账本原样保留，不把v24的16/30万实验账本套给日常问答。

## 生效与下一条自然任务

/health.managed_factory包含selection、启动时实际Factory零模型调用探针的enabled、启动源码commit及Store绝对路径。startup_probe只创建/关闭实际组件，不提交任务，不发HTTP模型请求；模型合同不变。元数据日志managed-overlap-events.jsonl记录fact_http_worker_begin与领域retrieval_start/return，不记录原文、密钥或请求头。第一条事实HTTP线程进入领域读取窗口的自然任务会写overlap-first-natural-observation.json；线程进入不等于精确socket POST。

发布回执必须区分configuration_effective与first_natural_task_observed。本轮不自动提出付费问题，不把启动探针或旧烟测冒称首次生产自然任务。下一条用户日常提问会自动记录，无需修改启动方式。

## 切换前证据

开始时8765无监听、health不可用、无backend/uvicorn进程；Store状态99 finished/4 failed/3 cancelled/4 interrupted，无queued/running。SQLite在线备份与原启动脚本/非密钥受管配置/三份未提交文档备份在私有data/runtime_local/overlap-release-v25/before。原文档曾因Git换行转换改变字节，已按备份恢复并核对原文本一致。保留stash安全副本，不提交原研究材料。

原Store逐表基准：110 runs、2454 events、3286 objects、8 reviews；按rowid序列化全部行SHA核对，包含历史预算usage，不只比较UI列表。隔离8779使用在线备份的副本，验证后正式8765必须指向原路径。

## 验收进度

首轮6项、停机竞态修复后7项确定性专项通过，覆盖源绑定修订/v2/重提取完整双审/Store、领域失败、用户取消、显式Factory、未配置默认及首次观察元数据。完整离线1460项/319.436秒通过，跳过80私有历史；其后仅修改启动器连接关闭处理，7专项复验及eac94b7 CI通过。隔离8779两次正式启动分别实际overlap=True、component=False，重启后110条历史和四张历史/usage表逐行hash完全相同，旧答案API重读成功，均0模型请求。实际输入响应、Store、预算与配置回执留忽略data，不提交Git。


## 实际失败与纠正保留

隔离回退本身ready/实际component/同历史通过，随后stop轮询碰到已接收健康连接关闭，RemoteDisconnected被原health_at漏接，旧cmd出现pause。修复仅在受管启动器把该异常解释为服务已断开，新增确定性测试；不吞掉stop的busy/认证失败、不强杀。一次向旧终端发送回车被自动审批拒绝，未执行；旧命令后来未收到输入也自行推进，不能以磁盘代码身份代替实际进程身份。

首次正式进程8956实际载入172bb07，虽ready、实际overlap及原历史/usage均通过，但与预期修复版不同。发现后明确纠正，空闲/队列0下用eac94b7优雅停止成功、确认旧进程退出；再单独用日常脚本重新启动，不恢复被拒绝的旧终端命令。保留first-production-runtime-172bb07.json、runtime-version-correction.json与各次验证回执。本轮没有用户在途任务、强杀或新模型请求。


## 最终运行回执

正式8765以日常脚本启动，实际加载代码eac94b7（启动器停机修复），Harness与已验收75cbbdd对应文件文本完全一致。正式Store的110 runs/2454 events/3286 objects/8 reviews及usage逐表hash不变，旧完成答案从正式API可读；再次调用日常脚本只复用同一实例，不创建新任务。最终正式ready、actual enabled=True、source_commit=eac94b7、pid=9904已从/health与启动回执交叉核实；私有release-receipt.json逐项记录。

- 配置已生效：以正式/health的selection=overlap、startup_factory_probe_enabled=True及原Store路径共同核验。
- 首次自然任务已观察：否，待用户下一次日常提问。启动探针、隔离检查和v24旧烟测均不算。本轮真实模型调用0，不制造新题验证。

日常命令：`D:\PowerTrustAI\start-powertrustai.cmd`。本机8765一键回退：`D:\PowerTrustAI\rollback-overlap.cmd`，使用data/runtime_local/managed-service.json中的8765及原正式Store/认证路径；无需带8779或隔离参数。任务忙时原stop返回SERVICE_BUSY并保留overlap配置，不强制停机；待任务终态且排空后再执行。回退不删除历史、不重放POST、不重置预算。当前服务保持运行供用户日常使用。

配置不进Git，正式Store与在线备份、预算usage、历史API响应、所有校验SHA与服务回执均留D:/PowerTrustAI/data/runtime_local/overlap-release-v25。代码独立PR #7针对master；PR #6仍为实验沿革草稿，不合并它发布。下一次自然任务使用同一原Factory/Harness入口，其事实HTTP线程和领域读取轨迹保存在正式Store旁managed-overlap-events.jsonl；若初稿不触发事实审核，或失败/输入不足等导致无法比较，须如实记未知，不把配置开关等同真实重叠。
