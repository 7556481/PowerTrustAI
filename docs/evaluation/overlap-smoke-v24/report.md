# v24有限隔离产品烟测通过：建议有限启用，8765待审阅

2026-11-12，基于75cbbdd，同一8778/独立Store、同一冻结普通题、同一16次/30万可信token账本完成。初次自动浏览器认证被工具URL策略拒绝，用户后来手动完成官方单次文件认证；随后只提交一次自然题，没有换题或补跑。四项零付费夹具在认证等待期间已先执行，认证后从同服务历史逐条核验其页面；自然题结束后再选回rollback，没有重复发夹具任务。

**建议有限启用**仅指受管显式Factory的小范围启用方案，经本次结果审阅后执行；本轮未切换8765、未改默认Factory、未合并或部署。提速幅度仍引用v23七完整对中位早9.775秒/29.20%，不从本次单题推算提速。

## 浏览器自然题与三个时刻

|时刻（北京时间）|实际记录|
|---|---|
|点击提交|2026-11-12 09:01:23.900—09:01:24.553，点击工具调用窗口|
|首稿首次观测可见|09:01:46.994；前次未有稿观测约09:01:36.6|
|审核终态首次观测可见|09:02:26.875；前次仍审核中观测09:02:05.363|

点击起约23.1秒首次观察到首稿、约63.0秒首次观察到终态。这是工具采样观测的上侧时间，**不是精确首帧延迟**：首稿转换约落在点击后12.0—23.1秒，终态约40.8—63.0秒之间，另有捕获粒度误差。未安装DOM可见性连续打点，不能事后把服务端生成时间冒称用户可见时间。正式启动/全库来源封印与人工认证等待均在点击前，单独留服务日志，不计入这些点击后观察。

自然题自然生成76字；实际完整审核终态needs_information，页面“待补充”，执行错误0，不是执行未完成，也不是pass或工程认证。保持输送功率、功率因数与导线条件的比较限定均保留，初末答案/引用对象精确一致，业务修订0。局部“依据不足”意见中包括来源未明确导线条件，既有理由和正文均可查，没有为取得通过而删除正确限定或放宽合同。首稿/终态均由浏览器直接观察，不以API推算。

浏览器点击“查看依据[1]”后实际显示IndustryCorpus2来源原文、版本254a95020a635d32ec20b0cfb736306a437022fe38bed45a509d8a49f95c8bdb与shard/row/record/chars[0:559)定位；这是库内原文回查，不等于已独立核验行业来源权威。刷新后先回空问答页，再打开历史并重读90a0c3797bb14999ad06fa5898d4da49，正文、标注、待补充终态与三个引用均保持。

## 真实重叠与账本

事实最终Adapter调用在领域读取开始后0.352秒，实际HTTP工作线程在0.369秒进入；领域Adapter读取8.594秒返回。两点均明确早于读取返回，后续原validate/交付仍保留，排除了只创建async任务却被同步读取阻塞的情形。没有记录socket POST精确时刻，不把HTTP线程开始冒称该时刻。

6次deepseek-flash真实请求全部成功且有可信usage：生成1、提取1、独立事实1、原引用2、领域1；格式纠正0、Revision0，无重审触发。输入65906、输出4417、总70323 token，未知/在途/悬挂预留0，金额未知。16次/300000上限未越过，剩余额度不作新题或补跑授权。单题秒数仅为产品观察，沿用v23配对提速判据。

## 同服务零付费取消、故障和回退的页面验收

已从浏览器历史逐条打开，而不是只根据后台结果推定页面正确：

- cancel：页面“已取消”“审核未完成”，保留旧稿，取消按钮禁用；后台时间线证明事实已发出、领域仍读取时实际cancel API发生，随后事实等待释放，任务不误标完整。
- failure：页面“审核未完成”，未给绿标，后台RETRIEVAL_FAILURE保留；下一条recovery成功202接单并最终通过。
- recovery：页面“通过”、版本2、3kV合成修订稿，完整重提取/双审，故障后同服务可继续接单。
- rollback：实际ComponentFactory.create、overlap=False，页面“通过”、版本2；原准备顺序仍可用。自然题结束后再次选回该普通组合路径，无新增任务。

这些夹具没有真实HTTP模型调用，真实账本在其执行后仍为0；其usage=None不当作真实未知收费。自然题只在用户认证后执行一次，未把任何fixture混入真实计数。收尾health无active/queue，使用原session/stop优雅退出隔离服务，随后核对8778无监听、执行会话已结束；8765未操作。

## 浏览器证据与发布边界

私有data/runtime_local/overlap-smoke-v24保留draft-visible.png、terminal-visible.png、citation-visible.png、history-natural.png、cancel-page.png、failure-page.png、recovery-page.png、rollback-page.png、browser-times.json、natural-result/trace、各fixture结果、runs/*/events/messages/receipt、fixture-proof.json、final-smoke-proof.json及accounting账本。启动票据/认证文件与原文、真实输入输出均留忽略data，不提交Git。

受管显式--factory入口、普通回退与有限预算参数见release-plan.md，默认component，无生产环境变量开关。1项选择回归/py_compile/学习站20章88题检查通过；原75cbbdd引擎业务代码未修改，不重复原1465全回归。新的入口与文档由本提交CI核对。

---

## 4df512b阶段记录（历史阻断，已由用户手动认证解除）

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
