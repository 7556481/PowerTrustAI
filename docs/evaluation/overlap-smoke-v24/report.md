# v24有限隔离产品烟测：浏览器认证阻断，尚未通过

2026-11-12，基于75cbbdd。**当前不能升级为“建议有限启用”。** 阻断是浏览器工具不能完成官方file://认证跳转，非已确认的产品审核故障。普通概念题尚未提交，没有点击/首稿可见/审核终态可见三时刻，也没有自然生成/审核的付费结果；不能拿v23的TestClient配对结果或本次后台夹具替代浏览器烟测。

独立8778、独立data/runtime_local/overlap-smoke-v24/baseline/runs.sqlite3，SQLite/schema13/Flash/serial_v1，显式OverlapFactory；真实账本硬限制16次/300000可信token，当前0次/0token，entries为空，无未决预留。单题及固定批次在私有freeze.json；不换题，不重置预算，不补跑。8765未操作。服务通过原create_app、uvicorn.loopback单worker、原open_local启动及单次会话协议，来源全库封印保留。

官方启动文件在私有baseline/local-session-bootstrap.html。IAB工具拒绝file://导航，明确禁止用其他浏览器/间接执行绕过；未将文件改为HTTP页面、未读取/显示认证令牌。HTTP正常页可打开，但AX明确“未连接”、提交按钮禁用。已请求用户手动完成官方文件认证；LocalSessions单次票据有效60秒，需在用户准备好时通过原open_local刷新，再由用户手动打开。用户完成认证后才能继续本次冻结的唯一自然题；不需要新增付费授权。浏览器证据在browser-block.json，不能冒称已检查引用、历史刷新或故障页面。

## 同一服务的零付费后台证明（不是页面验收）

固定cancel/failure/recovery/rollback批次各执行一次，模型由明确SyntheticProvider派生夹具替代，实际HTTP模型请求0；normal API/Factory/Harness/SQLite与同一Store不替代。

|夹具|后台实际结果|后续接单/释放|
|---|---|---|
|取消|核对领域读取开始 < 事实夹具已开始 < cancel API请求 < 领域读取退出；事实等待随后释放，Store状态cancelled，审核不完整|health无active/queue，下一条202|
|领域读取失败|RETRIEVAL_FAILURE保留，execution_incomplete，不被改为审核完整|下一条recovery被接受|
|恢复|OverlapFactory路径，完整审核、有据修订到v2、完整重审|health ready/idle|
|回退|调用普通ComponentFactory.create，overlap=False，v2完整重审|同服务仍可接单|

fixture-proof.json、各submission/result/trace/health、runs/*/events与receipt保留在私有data。真实账本未因夹具增长。夹具ModelUsage的usage=None代表没有真实提供商调用，不冒充真实可信usage或费用；真实预留账本仍为空。取消的后端API和等待释放已核实，取消按钮/错误页面视觉结果尚未核实。

## 交接状态

8778保持运行以等待用户手动连接，当前phase=rollback，即普通组合+明确零付费夹具；不自动向真实模型发请求。恢复浏览器验证时先核对health空闲、真实账本calls=0，再将同一phase文件切回real；Factory仍只接受冻结题一次。禁止重复初始化新目录/重新发批次。当前本地smoke执行器源代码另存私有source/，实际输入/响应与启动认证文件均不提交Git。

受管启动器、默认选择和一键回退代码在tools/managed_overlap.py、rollback-overlap.cmd；1项Factory选择回归通过，py_compile通过。尚无新的环境变量开关。发布操作方案见release-plan.md；在浏览器烟测完成前只作待审方案，不执行8765切换，不自动合并或部署。
