# 当前状态（2026-10-23，LangGraph主线集成验收）

## 2026-10-24 领域业务候选与事实收尾

事实两阶段未证明收益、暂不采用，保留研究代码与旧归档，不改事实政策。新增domain_internal_flow=business_v1开发装配，生产仍langgraph_v1/production/schema13；一次领域调用按范围/输入/能力/约束组织，无新增规划模型、调用或纠正额度。1187全套离线通过193.070秒；六类12分支唯一真实对照全部首次有效完成，12调用0纠正45814token，无共享故障或重跑，语义未证明提升。两项服务验收随后在受理前因冻结文件名与复用采集器不一致失败，受理0/调用0，按共享程序故障停止，不补跑；修复未来冻结命名后4专项通过7.142秒，原冻结/响应保持。未完成服务真实验收，不采用生产。正常生产服务已恢复并按授权空闲重启；状态和历史SHA核对见最终报告。工具浏览器未登录，合并一次人工清单。生成/修订盘点确认现有公共模块已复用，不强行封装丢失参数。学习站20章60自测、构建/源码/链接通过；无ZIP/数据库副本/重建索引/环境。详见[evaluation/domain-business-v1/report.md](evaluation/domain-business-v1/report.md)、predictions.json、statistics.json、fact-closeout.md及generation-revision-audit.md。


本机受管默认已为 **langgraph_v1**，正常Factory/worker/API服务ready；公开源码无配置回退仍sequential，环境变量优先。旧首项不重发，新关联批仅执行原未发送五项，全部执行、保存和收集完整：32调用含1纠正，413,018 token，0失败／未执行。三图必需阶段完整，两项诊断实际一次Revision及完整重审；图修订后待补充、原路径通过的语义差异保留，不归因编排或改变标签。固定响应差分仍是编排等价依据。

正常启动前后日常104请求、2278事件、2999版本／Evidence对象、8反馈及全行SHA一致；旧27私有产物身份一致。原编排保留回退，A映射与B对象边界未采用，四Agent/schema13/flash/完整知识库/检索/政策不变。收集7项与清单1项离线通过，未重复上轮全套；学习站20章60自测构建检查通过。工具浏览器验证默认问答及折叠诊断，自动连接、登录后引用／版本／失败草稿尚待一次用户人工检查，不绕过本地文件限制。

见[短报告与回退](evaluation/langgraph-service-continuation-v1/results-v1.md)、[小统计](evaluation/langgraph-service-continuation-v1/results-v1.json)、[实际切换核对](evaluation/langgraph-service-continuation-v1/switch-verification-v1.json)。本轮到交付停止，不继续删除候选／历史协议，不自动新付费或语义优化。

## 2026-10-09 第二版限定原型冻结（历史）

当前：第二版已按限定范围性能改进原型冻结；最终v4＋lossless两题均120字内、完整执行、程序pass，但公式适用范围语义疑点与浏览器自动连接/答案核查仍未全部通过。实测首次API14.923/3.204秒、总44.454/28.068秒，不承诺全部10秒或费用/纠正率下降。schema13/flash/政策1.5/完整库/BM25 aggregate/NLI关闭，v5仍可选；首版与旧失败保留。见[第二版冻结与验收](release-freeze-v2.md)及[独立学习站同步清单](learning-site-sync-v2.md)。

源码修复04ec59b；两题源码冻结064e1d6、预期不进模型。840完整及最后43必要回归通过；11调用125538token、0纠正/0Revision。声明冻结但验收未全部通过，不改旧pass/失败或专家标签。交付后停止自动开发、训练、优化与模型实验。最终提交以冻结引用release-v2-20261009及最终回复回查。
