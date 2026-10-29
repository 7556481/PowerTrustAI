# 反馈归属与读取容错维护 v2 · 2026-10-27

基于4a5f728435b8771c7072b71edcdda6c22381892c，独立分支codex/read-path-feedback-polish-v2。项目模型请求/费用0；不加载根.env、真实适配器、NLI或大索引。生产schema13、默认检索、模型/提示/合同/政策、历史成绩及6534126封版均保持。原生产库/编排/知识配置及两个启动器与上一轮冻结哈希一致，8765停服。没有新增能力实验或下一轮任务。

## 修前证据与局部修改

真实app.js延迟DOM探针先运行旧源码：原6组通过，新增7组失败（草稿串任务、A反馈回读异常覆盖B提示、切走后A成功仍留旧草稿、trace及reviews各自故障阻断主轮询、相同结果刷新重建控件、旧提交失败锁住新连接）。原始记录在Git忽略的data/maintenance_local/read-path-v2/async-before.log，修前app/store/service另存该目录。不是只检按钮文字：探针断言实际POST地址/payload的answer_id、version、note、action及请求次数。

反馈正文/动作/来源/版本/finding按run_id存页面Map；切换B重置，返回A恢复并核对实际版本及finding，失效绑定明确提示且禁止保存直到重选。复核者身份声明仍全局。成功仅清除提交以来所有草稿字段未变的那份；即使已切B也可清除原A，而不动B。未知保存保留输入，不自动重发。单个写锁延续，未建队列、localStorage草稿或后端表。

追加探针又证明旧注销响应可清掉新连接、pagehide后延迟主结果仍渲染；已补epoch检查与离页失效。失效finding恢复需明确重选也加入测试。最后延迟探针发现新草稿恢复若等辅助读取结束会覆盖期间编辑，已将恢复移到主结果/选项就绪处，独立dc1db15修正；不是把后续发现伪称成首轮基线全部复现。提交以来只改变action而正文相同也保留；反馈回读成功/失败和旧提交异常均按epoch隔离。

主state/result成功即可展示；NLI、trace、reviews各自捕获异常、清除旧详情并显示局部失败。一项失败后该任务暂停该项自动读取，仍用原唯一计时器观察运行到完成；手动“查询状态”或新任务恢复。主读取失败仍停轮询，401仍断连；所有返回紧邻检查归属，不重试POST。未凭本次未选NLI跳过已有诊断。收尾探针另复现仅用量更新也会重建版本控件；80ca34d将用量面板更新与回答视图区分，19组最终通过。相同回答视图和相同反馈选项不重建，保留所选版本、控件身份与焦点；发生业务变化时正常更新。无渲染框架重写。

## 同样本前后读取测量

现有tools.read_path_benchmark入口，固定2条合成运行，数据库合计4255744bytes（约4.06MiB）；normal正文/依据各约2KiB，large正文/依据各524286 UTF8 bytes，raw约1MiB，snapshot重复该结构，另有索引对象。trace/reviews为空，专门暴露存在性检查成本；非空内容、顺序与绑定另用专项等价测试。每端点预热1次、计时5次取中位，解析/SQL计数独立于计时；无生产扫描、HTTP或模型等待。大字段计数阈值>500000bytes。原始5次值、解码bytes和输出SHA见[机器记录](read-path-feedback-polish-v2-verification.json)。

|样本/读取|SQL前→后|JSON解析前→后（其中大字段）|中位ms前→后|输出bytes（相同）|
|---|---|---|---|---|
|normal/state|1→1|4→1（0→0）|0.126→0.169|437|
|normal/result|8→8|22→7（0→0）|0.694→0.494|8826|
|normal/trace|2→2|4→0（0→0）|0.090→0.025|2|
|normal/reviews|2→2|4→0（0→0）|0.098→0.024|2|
|large/state|1→1|4→1（2→0）|11.755→0.064|436|
|large/result|8→8|22→7（12→4）|77.004→21.067|1575542|
|large/trace|2→2|4→0（2→0）|12.415→0.026|2|
|large/reviews|2→2|4→0（2→0）|13.123→0.024|2|

重复解码确认后，只加require_run轻量存在性检查供events/objects/evidence/reviews调用，以及state_row读取状态必要列/config和结果存在标志。get完整恢复仍在；state响应等价，缺run仍KeyError/404、存储错误仍StorageError，排序/不可变对象及旧库重开兼容保留。没有缓存、迁移、索引或新聚合API，也未改写历史。SQL次数没有减少，收益来自少搬运和少解码大字段。8份输出逐字序列化SHA相同。

小样本state0.126→0.169ms无收益，不隐去；其额外固定成本在这5次样本无法归因，保留原值。大样本result约72.6%读耗时下降，只代表本合成服务投影，不能声称模型、检索或完整问答提速。跳过并发辅助GET、多计时器重试、缓存和更多性能改造：现有串行有界失败已满足复现目标，无额外收益证据。

## 验证与运行

10项定向unittest通过（10.155s），覆盖Store空/部分/终态及volatile投影与旧get等价、非空事件顺序/反馈/证据、非法版本/对象不可变、旧库重开、缺run和关闭库错误，以及旧UI API/隔离工具。共享Store修改后唯一完整离线unittest **1340项通过，372.516秒**；最后前端恢复时序修正另跑真实app.js19组探针与原POST/纯文本安全探针通过，未为数字重跑全套。全套日志里历史评测替身输出calls/sent不是实际项目模型调用。

实际8766浏览器：反馈A→B空表单→返回A恢复版本1/domain-v1/动作/来源→保存并核对落库回读绑定；返回B草稿保留。v1正文复制成功、offline-e1原文与版本回查，合成新任务从running到finished可见。桌面1280与390窄屏文档宽分别1265/1265、375/375，无全局横溢。最终dc1db15再抽查切换/返回/保存，控制台无JS错误。浏览器未提供网络拦截能力，故辅助失败到主完成、失败后手动恢复、旧401/注销/离页/未知写及焦点控件身份只用真实JS探针验证，不冒称浏览器注入成功。截图留在忽略目录final-feedback.png（合成材料）。

学习站只同步10/14章讲解及实际源码身份80ca34d7e096fc9759cc5482b0d4c26001d67b47，14处AST实际摘录/哈希、构建/链接校验通过；20章88题保持，8770只抽查受影响10/14页，没有全站浏览器重验。未提交研究/论文/任务书与原交接修改保持。所有自启8766/8770已释放，8765仍无监听。

隔离启动：`.venv\Scripts\python.exe -m tools.ui_fixture --port 8766`，打开`http://127.0.0.1:8766/fixture/connect`。学习站仍用`start-learning.cmd`；测量复现用`python -m tools.read_path_benchmark --output data/maintenance_local/read-path-v2/manual-measure.json`（本轮不再重跑）。

## 可回退源码提交

- c00a89233e9c038c00b7d5a889bb07bc3442397f Bind in-page feedback drafts and stale write responses to their run
- 489a210c2e90920a73d9e7ef1cdaec56650f9f1c Isolate auxiliary read failures and preserve in-progress UI controls
- 43cb051df16d5e4a4bde1f93dfe5288ae2d23403 Avoid full result decoding for existence and state reads
- dc1db15a3fce764dd37ab29a0b30232c0fa0c24e Restore feedback before auxiliary waits can overwrite new edits
- 80ca34d7e096fc9759cc5482b0d4c26001d67b47 Keep answer controls stable when only usage records change

最后文档提交由Git及最终答复记录完整SHA；普通分支推送、远端ref与关键blob复核，不合并、不强推、不切生产。完成即停止。
