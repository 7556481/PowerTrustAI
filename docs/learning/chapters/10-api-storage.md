# 10 API、UI、队列、SQLite与本机会话

## 2026-10-27反馈归属与读取容错补记

反馈正文、动作、来源和版本/finding绑定只在页面Map里按run_id保存，切换后恢复前再次核对；失效绑定要求重选，不存浏览器长期记忆。成功只清除提交以来未改变的那份草稿，受理未知保留且不重发。主state/result与辅助NLI/trace/reviews分开处理；某辅助项失败后本任务自动暂停该项，主运行仍轮询，手动“查询状态”恢复。相同回答视图和反馈选项不重复构建，避免轮询打断操作。

Store.require_run只检查存在，state_row只读元数据/config及结果存在标志，get仍用于完整对象恢复；无迁移、缓存或历史重写。固定约4.06MiB临时数据库、正常及约1MiB正文/依据结果，预热1次/测量5次：大样本state中位11.755→0.064ms，result77.004→21.067ms，trace12.415→0.026ms，reviews13.123→0.024ms；SQL次数仍1/8/2/2，JSON解析4/22/4/4→1/7/0/0。小样本state0.126→0.169ms无提速，不掩盖；这些不是模型或检索的速度结论。详见docs/maintenance/read-path-feedback-polish-v2.md。

## 2026-10-27工程维护补记

本轮工程维护只为鉴权后的历史列表增加question_summary（压空白、最多120字符），不返回完整request/config、不改Store schema或旧对象。旧服务没有此字段时客户端回退到模式名。UI读取按任务epoch与请求身份丢弃过期结果，不重发POST；这不提高事实判断能力。

## 工具参数的原义与审计

标准库HTTP先解析响应信封，保留arguments字符串，既有strict_json再检查参数中的重复键。不得让SDK提前解析成字典后只剩最后一个同名键。严格Schema文档未列null，本轮只在objection/repair使用__NULL__传输标记并精确还原业务None；unknown、布尔和对象不改。可识别原参数、调用ID、结束和用量保留；无法安全识别时明确记缺口，不保存完整失败响应作为兜底。

## 2026-10-24 新wire与旧投影的语义兼容

【真实失败】scope_v2的A2关系模型判断保留，但source_condition与answer_condition均空、required=true，旧投影按“必要条件没有正文”降级。它把主语—结论关系误装成必要条件义务。新合同需单独表达无额外条件，且新投影绕开旧空引用路径；不能仅修改提示后继续调用旧派生规则。原始、有效和最终处置都保存，旧记录不迁移。

【真实失败的教学变体】源文说双方不应过度依赖，回答忠实复述。没有条件短语，是否应为了通过旧门禁填入一个相近的条件？

::: answer 展开新增练习解析
不应。那会补造语义或依据。模型应明确判断是否无额外条件，程序按独立的新投影处理；若三维声明冲突，应记录原因并保留复核，不能借保守降级掩盖合同不兼容。
:::

## 2026-10-24 审核链v2实证更新

本批真实运行通过隔离小型SQLite及现有Store/Factory执行，未启动生产或常驻候选服务。8765前后未监听，不能报告ready。生产历史四表104/2278/2999/8不变，379冻结源码及旧212消息响应身份核对通过；新版、原版、有效同伴与无效尝试均保留。离线API贯通与真实HTTP验收必须分开。 [完整预测、理由和成本](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/production-review-net-benefit-v2/report.md#)。

本轮实际结果：A8/G4/B8固定批次106请求、1126972token，5条审核执行不完整；候选仅A4进入新修订提示，原版也纠正且没有目标历史叙述，自然8路正文不变。未证明候选净收益，不采用生产；N-1/N-2条件外推和原引用跨单元缺口疑点保留。实际8765保持原停服，无常驻候选。

## 2026-10-24 候选配置与采集边界

ServiceConfig.revision_answer_delivery和Factory清单显式记录修订正文提示候选，旧记录不迁移；页面仍按已保存版本、完整阶段及政策处置展示，不因候选提示或modified动作把未认可草稿显示为通过。候选的真实Factory/图路径/Store/API离线夹具验证包含两版本与失败；本轮未重新设计UI，也不把离线/API检查说成新浏览器验收。

本批使用独立小型运行库，SQLite连接在所属事件循环创建、使用、关闭；复用saved_result另开显式关闭只读连接收集，Windows临时文件释放及响应/最终存储失败后停止已演练。旧生产库/历史attempt不修改、不复制。实际服务状态以[本轮报告](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/answer-review-net-benefit-v1/report.md#)为准，旧章节ready是当时状态。

## 2026-10-23 事实审核内部流程候选

候选服务使用原Factory、worker、Store和API；新增受服务配置控制的premise_declarations，声明只能精确绑定当前question/user_context。FactFlowOutput单独保存object_reviews与flow_trace，API的fact_internal_flow展示两轴异议和节点诊断。旧记录继续可读。服务manifest记录实际候选prompt/contract，不把schema13数字等同本次实际协议。

完整材料见[候选报告](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/fact-internal-flow-v1/README.md#)。生产未切换，本轮0真实调用。

2026-10-23当前补记：剩余五项固定服务验收完成，本机受管默认已为langgraph_v1，正常服务ready；无配置源码fallback仍sequential。新批32调用、413018token、0失败/未执行；两项诊断实际一次修订和完整重审，但图最终待补充保留，不冒称全部答案认可。四Agent、schema13、七共享阶段及预算/政策不变，A/B未采用。历史104运行/2278事件/2999版本证据对象/8反馈及SHA启动前后相同；原编排可正常停服改受管配置回退。工具浏览器入口已验、登录后视图待一次用户清单，不绕本地文件限制。详见[后续验收](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/langgraph-service-continuation-v1/results-v1.md#)。下文2026-10-22及更早状态保留历史含义，以本补记为当前。

## 服务与浏览器的分工

浏览器提交普通问题和配置选择，不能传入模型本机路径或DeepSeek密钥。API验证结构、同源和身份，ApplicationService创建run并排队，UI读取状态、答案与详情。模型profile、解释器和固定知识库只由服务端配置。页面不自行拼接另一个调度器。

日常统一python -m backend和start-powertrustai.cmd，默认8765。临时验证端口与独立数据库属于不同服务，浏览器记忆按origin隔离；历史反复手输令牌曾因验证目录各生不同令牌和内存连接刷新丢失，不是固定文件每次重启都轮换。

## 队列和单活动运行

ApplicationService.submit先保存请求/config，有限等待队列由worker逐运行执行。这样单运行的预算和模型生命周期可管理；队列满明确返回错误。收到run_id说明接受任务，不说明模型已经成功。轮询GET不会自动重复POST。

客户端“POST已发出但响应丢失”是未知提交状态。不能自动重发，因为服务可能已接收并产生付费请求。前端防重复提交是当前页保护，不是通用服务端幂等键。历史查询、刷新和重启不补算旧诊断或重发模型请求。

## 两类SQLite和WAL

运行库存请求、配置、stage_output、对象、结果和追加反馈；知识库存原文、文档版本、知识成员和片段；全文构建库独立处理大语料。不要把所有DB都叫“知识库”，更不能让审阅ZIP带完整运行库。

RunStore.tx用BEGIN IMMEDIATE、commit/rollback短事务。HTTP/模型等待发生在事务外，observer完成一个事件后保存。WAL允许读者读取一致快照并协调单写者，不等于多写者并行。WAL/SHM是运行中辅助文件，迁移不直接复制旧WAL代替一致备份。

```python
# 教学构造：请求期间不占长写事务
with transaction():
    save_accepted_request()
result = await remote_model_call()
with transaction():
    save_stage_result(result)
```

真正实现看backend/store.py和service.py。异常持久化需要记录RUN_STORAGE_FAILED，不能在内存算完就谎称已保存。对象索引绑定run_id/answer_id/version，反馈追加而不覆盖旧结果。

## 取消和重启

排队任务取消与活动任务取消不同。活动任务合作式中断、等待底层资源drain；不能通过UI显示“已取消”保证网络对端不收费。RunStore.recover把上次queued/running变interrupted，不自动重新执行。服务重启后查询同run_id应返回原结果及调用量，历史Evidence按原知识版本回查。

测试时比较原结果和快照哈希、诊断ID/输入/结果、请求数及引用文本，排除只比较页面标签的假恢复。展示投影可以另版改善中文说明，但不能回填旧语义判断。

## 访问令牌与本机会话

本机访问令牌控制API，DeepSeek密钥控制远程模型，二者不同。固定令牌文件存在复用，普通重启和模型配置切换不轮换。一次性引导机制让本机启动器兑换HttpOnly会话，长期令牌不进入URL；引导票据短期/单次，与长期密钥分开。普通刷新/重启复用会话；高级手动连接及主动记忆保留。

原连接记忆默认不勾选，选择后按当前origin保存本机令牌，取消或忘记清除；401使失效记忆和连接失效，不自动重发真实任务。自动会话与旧主动记忆是迁移兼容，不叠加两套互相冲突的授权。浏览器永远不保存DeepSeek密钥。

## 安全显示不是隐藏业务错误

UI使用textContent和安全链接投影，原文中<script>不能执行。长ID、轨迹、NLI和JSON折叠，答案、处置和关键原因先显示。字段路径是JSON诊断位置，不能误当本机私有路径删除；真正凭据、请求头和私有文件路径应隔离。

不同claim/answer版本不能合并“最终supported数量”当正确率。NLI只显示旁路诊断，logits/softmax不升级主结论。用户反馈绑定具体对象、来源保留AI辅助用户监督，不自动训练。

## 验证与面试追问

练习：为一次模型等待30秒设计存储事务。参考：接收短事务→异步执行→阶段短事务，别BEGIN后等30秒。追问：WAL能解决所有锁吗？不能，仍单写者；长事务、多个进程和读后升级会锁冲突。

面试可说：“API只接收任务，服务管理队列和生命周期，observer短事务持久化。重启中断不自动重发，GET历史只读。我保留同源鉴权，通过本机会话改善体验，没有删掉访问保护。”

## 核心审核修复v1的当前边界

已有回答未认可时显示原回答/待审核原文，危险建议显示禁止采用和来源警告；原值不删，不将最后版本默认叫审核认可。GET旧记录不补算新版安全判断。

## 2026-10-22 编排身份与历史兼容

Factory manifest、状态/API保存execution_path合法枚举；它是运行时选择，不是本地文件路径，也不公开诊断文件或凭据。新增配置不迁移旧结果、Evidence、版本和反馈，旧记录按既有原编排解释。重启恢复只把未完成任务标中断，不重新入队。小型验收运行库与日常库分开，二者复用同一不可变知识库，不复制70.8GB发布库。

## 三道自测：先作答，再展开

### 自测1：页面按钮锁等于服务端幂等吗？

::: answer 展开参考答案1
不等；多页或响应丢失仍可能重复提交，所以不自动重POST。
:::

### 自测2：WAL允许多个同时写事务吗？

::: answer 展开参考答案2
不允许；仍需单写者/短事务协调。
:::

### 自测3：重启查询是否重发模型？

::: answer 展开参考答案3
不；读原记录，未完任务标interrupted。
:::
