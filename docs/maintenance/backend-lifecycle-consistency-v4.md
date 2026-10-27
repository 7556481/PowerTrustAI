# 后端生命周期与结果状态一致性 v4 · 2026-10-27

基于e5360c3fb0d839533817a372d0a174adf4140cde，独立codex/backend-lifecycle-consistency-v4。项目模型/token/费用0，不加载根.env、不调用真实适配器/NLI/大索引、不读写或哈希生产运行库。schema13/生产配置/默认检索/提示/政策/合同和历史分数保持。只用原解释器、既有Fake/Harness/Factory/Store、临时小SQLite及8766；无自动worker重启、任务重放、缓存/框架/新调度器或新能力实验。

## 修前与修后证据

正式回归先跑旧基线：2项均失败，0.651秒。close RuntimeError后worker_done=true、active_stale=true、storage_fault=false、queue=1，新任务仍被接收；无实质回答finished/needs_information/decision完整，却required_stages_complete=false、rounds=0。另见旧计时ContextVar被垃圾回收跨Context退出的异常；修复后用真实capture_timing包装验证进入/退出在同一worker Task，收尾一次，不依赖GC。修前源码、有限输出及全部日志留Git忽略data/maintenance_local/backend-lifecycle-v4。

工作循环仍用原单worker/队列；分出单任务_run_one和受控生命周期状态，不另建调度器。资源清理、计时退出/落库与active/queue.task_done各自收尾；Bundle逐项尝试close，聚合受控原异常类别，不输出消息/堆栈/请求内容。drain未证实完成则保留bundle，不执行close；stop可重试安全drain，仍不确认就保留并推迟共享资源关闭。启动失败、重复停止、当前任务取消、排队取消及非预期worker取消分别处理，已显式取消的单任务不使worker假崩溃。

health新增service_lifecycle，ready需配置/存储及可接单worker同时成立；未启动或worker已退出立即拒单。API在索引解析等准备前检查，Service在输入准备前、可等待准备后、入队锁内再核对。故障新POST返回503/SERVICE_UNAVAILABLE；不通过重启或补跑掩盖。已存答案/report/版本/发现不因收尾故障重写，业务完成和服务可接单分开报告，历史GET和追加反馈仍可使用。

|故障/动作|当前已保存任务|等待项/接单|资源及故障分类|
|---|---|---|---|
|正常结果后的close RuntimeError|finished及原raw结果/审核/版本/发现逐项相等|interrupted / SERVICE_LIFECYCLE_FAILED；新503|尝试全部资源，独立RESOURCE_CLOSE_FAILED；不是存储故障|
|drain抛错|原业务结果不动|等待项明确中断；新503|RESOURCE_DRAIN_FAILED；不强关仍可能使用的资源，保留未确认句柄|
|计时落库StorageError|已存result仍存在/相等，元数据保存未确认|可写等待项interrupted / RUN_STORAGE_FAILED；新503|storage_fault独立，不能全归生命周期故障或抹掉业务结果|
|等待终态写入也失败|已完成结果不动|原存储可仍queued，但persistence_confirmed=false、pending_terminal_status=interrupted，队列记账释放；新503|不谎称落库。显式重新打开Store/新Service启动后按原恢复变interrupted，无执行/重放|
|worker非预期退出/取消|若未完成保留有效部分；Harness已产生取消结果时保留该结果|等待项interrupted；新503|WORKER_UNEXPECTED_EXIT，不自动重启|
|普通单组件失败且清理正常|保留同伴和原不完整处置|下一任务正常可执行|不无故停全服务|
|正常活动/排队取消或服务关闭|已有草稿/发现保留，取消或关闭中断状态明确|排队取消cancelled；正常关闭等待项interrupted / PROCESS_INTERRUPTED|不标成worker崩溃；重复正常stop不重复释放|
|部分装配资源清理失败|当前未开始Harness的任务执行失败，不伪造答案|等待项中断、新拒单|追加复现后修复：close_resources失败上抛为生命周期故障，不能吞成普通配置/组件失败|

最后一行是直接关联边界追加发现，先跑单测失败（仍接单），再修复；最终32项影响范围测试10.618秒通过，含实际ASGI的health degraded、新POST503、等待项和原结果可读/反馈绑定。故障时活动及等待同时存在，组件创建仅活动任务一次，queue.join完成；没有用清空active_bundle的测试技巧修产品。

## 无实质回答的判定表与投影

只修当前GET投影，不修改已存report/decision/原对象。必须是question_answer、finished、最终result已存、Harness实际needs_information、无生成/汇总执行错误、明确NO_SUBSTANTIVE_ANSWER且原处置完整，才认适用生成流程完整。不是对no_answer=true作宽泛OR。提取/事实/领域未调用，all_required_checks_assessed=false；新增substantive_audit_status=not_applicable，仍needs_information且answer_adoption.approved=false，无虚构审核轮次或pass。未完成的无实质回答展示“执行未完成，已有生成记录保留”。

|场景（两条路径相同）|运行终态|required_stages_complete|all_required_checks_assessed|实质审核状态|原处置|
|---|---|---|---|---|---|
|合法无实质回答|finished|true|false|not_applicable|needs_information|
|生成失败|failed|false|false|not_completed|execution_incomplete|
|生成后取消/中断|interrupted|false|false|not_completed|needs_information|
|仅有快照，观察持久化失败|interrupted|false|false|not_completed|needs_information|
|普通完整双审|finished|true|true|completed|pass|
|部分审核失败|finished|false|false|not_completed|review_required|

表中12格由实际sequential和既有langgraph_v1分别跑6场景产生，不是人工拼最终API对象。反例快照里的原needs_information/完整处置保持冻结；运行中断及最终持久化不完整由执行字段说明，不重写业务为事实错误。API两条路径另验，普通完整双审/部分失败沿原义。前端资料不足保持待补充、不适用，不称审核认可；旧UI夹具同步修正语义并保留中断反例。

## 验证范围、失败修正与限制

生命周期/原服务28专项6.191秒、无实质回答3专项（含12格/两路径API）4.248秒通过；最终构造清理边界修正后，相关32项10.618秒通过。实际JS20组（含新正常/未完成资料不足）、原慢辅助12组及POST/安全探针通过。

首次完整离线1359项/390.789秒有1失败：旧ui_render_probe将“正常无实质回答”硬设required_stages_complete=false，预期又要求不显示未完成。已改为正常true，并新增false中断反例，不删除覆盖，单项0.094秒通过。由于还补了共享后端装配清理分支，在稳定最终源码再次全套：**1360项通过，363.080秒**。两次日志均保留，不把旧1340或首次失败称本轮最终通过，也不是为测试数量补跑。冻结源码对应最终提交902cf65a350383f9d524a7a34ea5728173b93701。

实际8766浏览器用tools.ui_lifecycle_fixture_v4：先正常无实质回答，见“资料不足/后续审核不适用/待补充”，无审核认可；普通历史v1/v2、复制v1、offline-e1原文及反馈绑定通过。仅CLI预设下一任务close故障，实际保存结果后health文字degraded，下一UI提交明确“服务当前不接受任务”；再选原资料不足历史仍可读。无JS控制台错误，截图留忽略目录no-answer-browser.png、fault-browser.png。drain/存储不可写/构造故障及等待项由API/异步回归验证，不冒称全部视觉注入；最后构造异常修正不改UI。

drain对底层工作仍是合作等待：可能一直等待或继续失败，本轮没有超时硬杀、强关活资源或远端取消保证。状态里的未确认资源不会伪装成已关闭。真正存储不可写时持久化未确认；只有将来用户显式正常启动才按原recover处理，当前没有自动重启/重放。合成故障验证的是异常路径，不宣称生产曾发生该事故或提升模型正确率。

学习站仅更新10/14/18章相关生命周期、故障与API含义，源码身份及14份实际AST摘录位置/哈希；20章88题、构建/链接通过，受影响页面抽查，非全站浏览器重验。配置和两个启动器哈希保持；生产运行库本轮完全不打开/查询/哈希，以隔离而非扫库保护历史。原研究/论文/设计复核与任务书未全量暂存。自启8766/8770均释放，8765仍停服。

普通演示启动：`.venv\Scripts\python.exe -m tools.ui_fixture --port 8766`，打开`http://127.0.0.1:8766/fixture/connect`。本轮故障复验入口为显式CLI `python -m tools.ui_lifecycle_fixture_v4 --cleanup-fault-on-next`（同一隔离端口，下一新合成任务保存后close故障）；正式API无故障注入参数。完成后本轮不再启动或测量。

源码可回退提交：

- d6739a812b0b9cef3561efd019b96e58fc58c057 Fail closed on worker lifecycle faults and finalize queued work safely
- 2a4c3ea949fb9afe6f5acc62f094d4d9be7d7a70 Project no-answer stage completion without claiming substantive audit
- 902cf65a350383f9d524a7a34ea5728173b93701 Treat partial construction cleanup faults as service lifecycle failures

最后文档提交完整SHA见Git与最终答复。普通分支定向推送、远端ref与关键blob核对，不合并/强推/切生产。至此停止，不开启下一轮。
