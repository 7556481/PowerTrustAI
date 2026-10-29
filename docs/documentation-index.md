# 文档索引

## 2026-10-29 生产合同取证解耦已比较：不有限发布

16链一次执行完、0补跑。基线完整7/8、候选8/8；7完整对34.633→27.701秒，20.016%/6.932秒，未达30%门槛。90 Flash/1216184可信token，未知/在途0，费用未知；未启动产品4链或烟测。S6候选一次改对“所有电厂必须额装”并完整双审；S4/S5共同漏检、S1基线无关载体supported和事实载体不足均保留。失败主因速度不足，非取证不能解耦；不改合同、不另批。

应用42448b9完整1462/276.424秒OK（80私有历史材料缺失跳过），后续只有评测封印计时与文档，应用身份未变；旧1457结果仅对应初版。比较进程实际exit0，无遗留批次/测试，8765仍原PID19116/ready、active=false、queue0，未重启/切换。远端候选codex/production-evidence-decoupling-v1与[草稿PR #4](https://github.com/7556481/PowerTrustAI/pull/4)归档审阅，不合入master；[完整报告](evaluation/production-evidence-decoupling-v1/report.md)含逐对质量、分段时间、取证实际减少与保留。

## 2026-10-29 生产合同取证解耦：付费前冻结

最终应用42448b9已通过1462项/276.424秒离线回归（80私有历史材料缺失跳过），48组准备计时完成。唯一16链真实比较即将执行，默认关闭、8765保持。见[本轮报告](evaluation/production-evidence-decoupling-v1/report.md)。原1457结果仅属于初版，不重复冒充最终身份。

## 2026-10-29 发布后分支与候选处置

远端新核验后28→2，26历史分支先归档SHA再原子删除；本地安全删除27支，master安全快进。候选代码保留且不开启；rank/MATCH当前实现结束，只建议保留v6来源模态忠实与完整修订交付研究（不执行）。8765 PID19116/ready及源码/受管配置未变，0模型、无重启、不重跑1454。见[清单](maintenance/post-release-disposition-v1/report.md)、[完整SHA](maintenance/post-release-disposition-v1/branches-before.json)及[回执](maintenance/post-release-disposition-v1/cleanup-result.json)。

## 2026-10-29 最终工程整合准入

十题与UI补验完成，默认分支文档冲突已实际解决，应用源码未变、实验关闭；PR #2等待本HEAD的CI成功后才合并和正常启动8765。已有1454复用，不重复本地回归。实际远端/本机身份及配置备份/回退见data/runtime_local/stable-product-ten-v1/release-receipt.json及最终聊天回执，不根据本段猜测已发布。详见[发布报告](maintenance/stable-product-baseline-v1.md)与[十题结果](evaluation/stable-product-baseline-v1/report.md)。

## 2026-10-29 十题产品基线与UI补验

- [十题真实结果及逐题复核](evaluation/stable-product-baseline-v1/report.md)：正式API、6/10审核完整、61Flash/887560token、0修订；分列内容收益、关键条件漏检及诚实但无用的不足。
- [接续启动发布报告](maintenance/stable-product-baseline-v1.md)：200.492秒启动、UI四缺项补验及代理/CI。


## 2026-10-29 稳定产品候选（待验收）

- [候选验收报告](maintenance/stable-product-baseline-v1.md)：分支关系、实际配置、1454离线通过、正式启动及UI工具故障；未发布、十题未发送。
- [从启动到退出清单](stable-operation-checklist.md)：原脚本显式--demo路径及正式服务、故障与退出边界。


## 2026-10-29 rank执行与审核引用v7（完成，两项未启用）

- [独立验收报告](evaluation/retrieval-rank-and-audit-reference-v7/report.md)：A显式LIMIT固定三轮无稳定收益，不构造/部署第三路径；B全10链形状失败、0/5修复，不启用/不烟测/不补批。
- [SQL全数值表及计划](evaluation/retrieval-rank-and-audit-reference-v7/sql-summary.json)：18排名/3限定COUNT，原请求/评分/K不变；最慢中位24.127→28.809秒，旧4096回退是否触发不可证。
- [审核统计](evaluation/retrieval-rank-and-audit-reference-v7/audit-summary.json)：30 Flash/643777token、无新增未决；领域10完整不能替代事实0完整，原SQL/旧pending10保持。B18d4f67、报告ec9c7df，1448离线及35专项、十路径/实际读取和学习站源码同步通过。

## 2026-10-28 来源模态忠实性与候选发布v6（完成，未启用）

- [完整报告](evaluation/source-first-modality-release-v6/report.md)：唯一v3逐字来源关系、事前10材料/14槽、候选6/10完整及严格2/5修复；S2/S10未修、S3后审失败、S4执行失败，不启用/不烟测/不补批。
- [脱敏统计](evaluation/source-first-modality-release-v6/summary.json)：64 Flash/1275546token，无新增未决、旧pending10保留；新候选绝对门槛与旧四对门槛分开，失败不剔除，费用未知。
- 实现98de208、报告c789577；1433离线496.107秒、22专项10.112秒、实际库10路径/10读取和实际14归档读取通过。实际UI回放保留复制往返未独立确认及两次夹具404边界，学习站五章与源身份同步。

## 2026-10-28 来源优先修订完成发布v5（完成，未启用）

- [完整报告](evaluation/source-first-revision-completion-release-v5/report.md)：194秒未知项、物理释放隔离、12槽11完整/1局部失败；真实修复3/4，S2未修，三有效对不能判四对速度，不启用/不烟测/不补批。
- [机械摘要](evaluation/source-first-revision-completion-release-v5/summary.json)：50 Flash、960147token、无新增未决，旧v4 pending10不改，实际金额未知；实际修订及普通接口重读保留完整状态。
- 实现c2ecddf，报告归档adc1227；1425离线503.019秒、17专项及实际库8路径/8读取，12实际归档读取通过；学习站相关五章和源码身份同步，v4 UI证据与旧失败保持。

## 2026-10-28 来源优先质量/UI与有条件启用v4（完成，未启用）

- [唯一候选、真实停止及UI报告](evaluation/source-first-quality-ui-release-v4/report.md)：12槽仅2完整/1未完整/9未执行；S2有限纠正后触发修订但超时且usage未决，门槛失败，不切本机、不烟测、不第二批。
- [机械统计](evaluation/source-first-quality-ui-release-v4/summary.json)：10发送边界，9可信usage已知212444token，pending10不可当0，实际总token/金额未知；仅S1一对48.370→5.934秒，无总体中位数。
- 实现2e99786；1420离线/446.890秒、实际库8路径和普通重读、20项UI/API专项、桌面/390真实归档回放。学习站相关章节与源码身份同步，旧v3成绩及失败保留。

## 2026-10-28 来源优先真实路径验收v3（完成）

- [真实路径修复、唯一四对及质量复核](evaluation/source-first-real-path-acceptance-v3/report.md)：8/8合法、29Flash/669718token，中位提速82.678%；两目标漏检0/2修复，质量门槛失败，不采用不部署。
- [逐槽/模型/FTS父子阶段统计](evaluation/source-first-real-path-acceptance-v3/summary.json)：正常封印与整链分账，私有正文/SQL/响应留忽略data，旧v2失败不覆盖。
- 学习站04/08/14/16及source-check/source-version同步实现f69a412；1414项离线通过，8条普通接口归档重读，隔离固定响应桌面/390复核。用户服务不动，无第二批。

## 2026-10-28 真实验证v2完成一次后共享工程故障停止

唯一8槽固定批次实际执行S1 A/B，6次Flash、输入117702/输出3891/总121593token，usage齐全、未决0、阈值越过0；原70GB正常字节封印189.037秒单列。A执行完整review_required/43.722秒；B两模型完成后报告校验invalid evidence origin失败/5.836秒，余6槽未执行，不把早停当提速。根因为冻结候选新增邻接绑定index_context不在严格白名单；不修业务、不恢复或第二批。两路正文完全未改，S1原文有据，其余错误/缺口未验证，四对门槛不满足、不采用不部署。7专项/5.931秒只证合成接线，未覆盖新增邻接冲突；旧1405不当本轮结果。源码b3078cd，原v1.1材料/业务不变，生产/8765/master/README未动。见[报告](evaluation/source-first-audit-live-validation-v2/report.md)与[统计](evaluation/source-first-audit-live-validation-v2/summary.json)。本轮停止交设计审阅。

## 2026-10-28 来源优先真实验证：上界依据缺失，入口仍未验收

预算新增逐请求持久化原子预留与可信usage结算，缓存不重复、未知发送/usage不释放、超额与落库异常停全局，禁止恢复；4项专项/0.083秒通过。官方资料未建立完整Hosted Chat信封计费token上界，不再以任意2048或96槽乘首审作硬保证。原v1.1材料身份保持，正常初审24调用，条件性纠正/补检/修订载荷未知。8槽全部未执行、0真实请求/0token/未加载.env/未读真实大库，完整真实入口未验收；不是120万必然不足，也无速度或纠错收益。不切生产/8765/master/README，不补跑。见[新报告](evaluation/source-first-audit-live-validation-v1/report.md)，到此停止。

## 2026-10-28 来源优先审核候选与预算停止交付

[唯一报告](evaluation/source-first-audit-redesign-v1/report.md)、[保守预算预检](evaluation/source-first-audit-redesign-v1/preflight.json)、[公开历史正文引用](evaluation/source-first-audit-redesign-v1/cases.json)、[验证与边界](evaluation/source-first-audit-redesign-v1/verification.json)：固定来源邻接/最多三缺口查询/完整修订重审，默认关闭。四对真实链因保守预算准入失败未启动，0请求；无速度或纠错收益结论，不建议采用，不恢复第二批。学习站04/08/14/16及实际源码身份同步；原输入/提取/来源全文/wire留忽略data。

## 2026-10-28 审核检索最终诊断完成

[报告](maintenance/audit-retrieval-final-optimization-v1.md)、[验证](maintenance/audit-retrieval-final-optimization-v1-verification.json)：固定3组8查询，分解/身份及预算保持，FTS主导、连接毫秒，无安全可达门槛候选，0配对/0模型；102专项通过。生产执行不改，源码身份与16章必要同步，完成推送/CI后停止。

## 2026-10-27 schema13有界并发候选

[短报告与真实验证方案](maintenance/schema13-bounded-concurrency-v1.md)、[离线验证](maintenance/schema13-bounded-concurrency-v1-verification.json)：五条白名单元数据、独立依赖、双HTTP通道、索引确定性纠正、取消drain、完整发现/引用/正文/修订对照及模拟收益边界。默认关闭、0新增模型、未动8765/master；学习站14/16必要同步。

## 2026-10-27 正文审核标注v7交付

[报告](maintenance/answer-inline-review-marking-v7.md)及[验证](maintenance/answer-inline-review-marking-v7-verification.json)：安全原文/身份定位、同句合并/重叠分段、未定位回退、当前/历史版本隔离、明确未修改与已有修订，0模型；包含离线/API/浏览器及失败修正边界。仅同步学习站10/14，不更新README或master，不重跑用户问题。

## 2026-10-27 产品首页与CI最终交付v6

[用户UI、README与CI报告](maintenance/user-ui-readme-final-delivery-v6.md)：模块去留、审核时序边界、历史README迁移、实际GitHub失败日志、逐项CI修复、验证失败及修正；最终远端ref/提交CI以收尾Actions为准。新版默认问答与独立诊断，模型0，不恢复付费批次。README仅产品总览，后续维护进交接和专题报告。

## 2026-10-27 服务状态恢复UI v5（已执行）

- [维护报告](maintenance/service-status-recovery-ui-v5.md)：修前失败、接单与读取分离、待中断未确认、只读检查、轮询停止与兼容边界。
- [机器验证](maintenance/service-status-recovery-ui-v5-verification.json)：最终11专项、26/20/12客户端组、真实隔离API/浏览器、v4全套复用及0模型保护。
- 学习站10/18与源码身份同步；保留已存业务结论，无自动重启/重放，完成停止。

## 2026-10-27 后端生命周期一致性v4（已执行）

- [维护报告](maintenance/backend-lifecycle-consistency-v4.md)：修前/修后、故障处置、原结果保护、两执行路径无实质回答表、停止边界。
- [机器验证](maintenance/backend-lifecycle-consistency-v4-verification.json)：最终全套1360、首次失败与修正、32影响范围专项、真实API/浏览器及0模型隔离证据。
- 学习站10/14/18与源码身份同步；无生产库读取/改写、无自动worker重启或重放，完成后停止。

## 2026-10-27 慢辅助隔离与页面性能v3（已执行）

- [维护短报告](maintenance/slow-auxiliary-page-performance-v3.md)：修前挂起/回读重叠、有限slot生命周期、固定非空样本各层性能、渲染去重及未改善项。
- [验证机器记录](maintenance/slow-auxiliary-page-performance-v3-verification.json)：前后14输出SHA、5次HTTP/实际浏览器原值、12新/19旧探针、专项错误及修正、复用1340边界。
- 学习站仅10/14/16与源码身份；项目模型0，生产/历史保持，自启服务已释放，完成后停止。

## 2026-10-27 反馈归属与读取容错v2（已执行）

- [短报告](maintenance/read-path-feedback-polish-v2.md)：修前失败断言、局部修复、同样本性能前后表、跳过项与浏览器范围。
- [机器可读验证](maintenance/read-path-feedback-polish-v2-verification.json)：19组真实JS探针、1340全套、2条合成Store测量与8份输出SHA等价、生产保护及源码身份。
- 学习站10/14章已同步，20章88题保持；项目模型0，辅助故障以探针验证，8766/8770验收后停服，完成即停止。

## 2026-10-27 业务UI与有限清理（已执行）

- [维护说明与合成UI前后图](maintenance/product-polish-ui-code-hygiene-v1.md)：五项异步/错误提示复现修复、版本选择/对应正文复制、证据直达、历史摘要、有限依赖清理及必须保留的旧代码。
- [验证与提交身份](maintenance/product-polish-ui-code-hygiene-v1-verification.json)：1337全套399.514秒，合成8766桌面/窄屏/反馈/取消/分页/安全渲染，0项目模型；学习站源码同步、20章88题保持。
- [隔离业务UI入口](../tools/ui_fixture.py)：原环境`python -m tools.ui_fixture --port 8766`，不读.env/生产库/大索引；不同于8770学习站和真实8765入口。封版6534126及历史收益/失败不改，不新启旧能力任务。

## 2026-10-27 阶段封版交付（已执行）

[当前README](../README.md) · [阶段清单/能力边界/分批用量/入口](project-status-20261027.md) · [学习站演示路线](learning/index.md) · [17章求职表述](learning/chapters/17-interview.md) · [本次验证范围](learning/closeout-20261027-verification.json)。20章88题保持，新增项目请求0；本轮非全套/全站重验，旧v6记录明确复用。阶段可展示不等于审核研究目标完成。

### 当前任务入口状态（下方历史交办不再作当前待办）

|入口|当前状态|
|---|---|
|literal-stage1、offline-redesign、revision-v2、natural-v3|已执行封存，各自失败及回放边界保持|
|retrieval-delivery-repair、chinese-first、retrieval-evidence-answer-check、natural-draft-audit|已执行封存；旧条件槽未启动不恢复，N6旧gate=false保持|
|source-comparison-review-v2-task-v1|已被检索定位任务替代，未执行，不恢复为待办|
|answer-review-improvement-checklist-v1、论文清单/综合等未跟踪材料|暂存设计/研究，非新执行授权，未删除或擅自提交|
|project-closeout-20261027|本次已执行阶段收尾；无待运行批次，完成远端核对即停止|

## 2026-10-26 自然同稿审核与学习站完整同步

- [固定自然稿审核报告](evaluation/natural-draft-audit-v1/report.md)：8链32请求，N2/N4识别失败，N8边界改写争议，N5执行失败；初末全文/原预测含无效/冻结/用量/独立复核/Store齐全。
- [学习站v6同步与真实浏览器验收](learning/sync-v6.md)：20章88题，N1/N4/A3完整案例、14处实际源码摘录及分批元数据，桌面/窄屏/搜索/导航/解析验证。
- [学习站首页正文](learning/index.md)、[源码与批次身份](learning/source-version.json)、[浏览器记录](learning/browser-acceptance.json)。start-learning.cmd可重开8770；当前生产8765停服，schema13不变。

## 2026-10-26 固定证据回答诊断封存（已执行）

[报告](evaluation/retrieval-evidence-answer-check-v1/report.md) · [16完整正文](evaluation/retrieval-evidence-answer-check-v1/cases.md) / [三分层结果与完整对象](evaluation/retrieval-evidence-answer-check-v1/cases.json) · [输入恢复](evaluation/retrieval-evidence-answer-check-v1/input-recovery.json) · [独立文本复核](evaluation/retrieval-evidence-answer-check-v1/text-review.md) · [16预测](evaluation/retrieval-evidence-answer-check-v1/predictions.json) · [统计](evaluation/retrieval-evidence-answer-check-v1/statistics.json) · [验证](evaluation/retrieval-evidence-answer-check-v1/verification.json)。全部8题5改善/3混合，忠实7题5改善/2混合，N6混合且未出现调试退役；旧转换失败不回写。16Flash/147049token、金额未知，0新检索/转换/审核/Revision，旧8转换不重计。N2模态/N4排他/N6规划范围新错使整组门槛未达，不采用。10专项及复用旧1324全套、Store/消息/快照核查齐全，下方“尚未执行”保留任务编写时状态，以本封存为准。

## 2026-10-26 中文主线跨语言检索封存（已执行）

[报告](evaluation/chinese-first-cross-language-retrieval-v1/report.md) · [三路36槽](evaluation/chinese-first-cross-language-retrieval-v1/retrieval-results.json) · [语言依据](evaluation/chinese-first-cross-language-retrieval-v1/language-audit.json) · [8条转换原预测](evaluation/chinese-first-cross-language-retrieval-v1/predictions.json) · [门槛](evaluation/chinese-first-cross-language-retrieval-v1/evidence-gate.json) · [独立源/翻译复核](evaluation/chinese-first-cross-language-retrieval-v1/independent-source-review.md) · [成本延迟](evaluation/chinese-first-cross-language-retrieval-v1/statistics.json) · [验证](evaluation/chinese-first-cross-language-retrieval-v1/verification.json)。A/B/C所问原文槽实际覆盖0/6/25（总25），C的N6转换实质换义失败单列；有效C>A7/8、C>B5/8，门槛未全满足，回答阶段未启动。8Flash/1359token、金额未知；每触发题+1请求、C-B均值+1.748秒。1324最终离线通过，默认关闭、无生产切换/第二批。下方“尚未执行”保留任务编写时状态，以本封存记录为准。

## 2026-10-26 检索交付定位封存（本轮已执行）

[检索交付修复v1报告](evaluation/retrieval-delivery-repair-v1/report.md) · [逐题MATCH与实际交付](evaluation/retrieval-delivery-repair-v1/diagnosis.json) · [原文身份与计时](evaluation/retrieval-delivery-repair-v1/identity-check.json) · [独立复核](evaluation/retrieval-delivery-repair-v1/independent-review.md) · [验证及停止](evaluation/retrieval-delivery-repair-v1/verification.json)。正确版本268片段已参与native FTS，八题参考段实际MATCH全0，六题去主题仍无词项；不能归因未向量化。依任务第3节停止分支，无候选/最终检索对照/付费批，改善未测得、回答收益未证明，新请求0。下方“下一轮/尚未执行”保留任务编写时状态，以本封存记录为准；被替代审核重构未执行。

## 2026-10-26 自然答案改善v3结果

[完整报告与全部初末全文](evaluation/natural-answer-benefit-v3/report.md) · [遮蔽复核及双轴判断](evaluation/natural-answer-benefit-v3/text-review.md) · [49次实际预测](evaluation/natural-answer-benefit-v3/predictions.json) · [用量分账](evaluation/natural-answer-benefit-v3/statistics.json)。N0改善/0恶化/8相当，8题目标源未交付；N4有据可修的“大”限定漏检。H0改善/3相当/1执行不可评价，H3 when→only误认仍在。49新Flash、579,406token、实际金额未知，12链无Revision触发；不达门槛、不生产采用，不改旧0/4与固定初审4/4。26专项及复用1305全套、Store/冻结/328历史文件和生产保留证据齐全，停止交设计审阅。

## 2026-10-26 修订v2四例真实验证结果

[完整报告及四例初末全文](evaluation/local-revision-v2-flash-check-v1/report.md)：合法应用/目标改对/正确内容保留/真实重审Store闭合均4/4；固定历史首轮免费回放，16次新Flash、82,465token，金额未知。附冻结、全部实际预测、逐请求费用状态、独立文本复核、9专项/1305全套及生产/历史保留证据。A2排他误读风险和未验证复杂依赖保持；不推自然收益、不改旧0/4、不生产采用，停止交设计审阅。

## 2026-10-25 局部修订离线整改结果

[短报告](evaluation/local-revision-offline-redesign-v1/report.md) · [实现前职责表](evaluation/local-revision-offline-redesign-v1/design.md) · [8旧拒绝核查](evaluation/local-revision-offline-redesign-v1/historical-contract-audit.json) · [真实投影统计](evaluation/local-revision-offline-redesign-v1/projection-verification.json) · [三个静态例/反例](evaluation/local-revision-offline-redesign-v1/static-examples.md) · [验证](evaluation/local-revision-offline-redesign-v1/verification.json)。D/O分责、非互斥依赖、来源供给和一次聚合纠正的新接口默认关闭；22专项/1296完整离线通过，项目模型0、不加载根.env。旧8响应拒绝和阶段0/4保持，新合同不兼容不算恢复成绩。只建议设计审阅后另行决定小范围验证；不自动付费/采用，不扩学习站。

## 2026-10-25 原文审核第一阶段结果

[完整报告](evaluation/literal-review-stage1-v1/report.md) · [实现/预算/故障边界](evaluation/literal-review-stage1-v1/implementation.md) · [全部28槽前后文本](evaluation/literal-review-stage1-v1/cases.md) · [131份必要预测](evaluation/literal-review-stage1-v1/predictions.json) · [实际用量](evaluation/literal-review-stage1-v1/statistics.json) · [独立文本复核](evaluation/literal-review-stage1-v1/text-review.json)。代码c098b5d，1285离线通过；唯一28槽131Flash请求，费用金额未知。候选0/4实质修复（四次Revision均非法），三正确稿保护、不足稿执行失败；生产A2改对/A4 mixed，自然无正文变化且保留“仅用于”无据认可。候选不采用，阶段封存，无第二批或生产切换。学习站04章定向失败案例/源码导读与两道练习，实际工程贯通不冒充模型成功。

## 2026-10-25 自然问答审核接缝与交付

[结论与全部材料](evaluation/natural-review-seam-v1/report.md)：统一提取消息而不改合同；旧稿6链/28Flash调用、候选N-2错挂认可触发新主题准入停止，不采用。

- [旧B1—B3断点与选项比较](evaluation/natural-review-seam-v1/diagnosis.md)、[完整原批断点表与勘误](evaluation/natural-review-seam-v1/previous-breakpoints.json)。
- [真实原始参数和失效尝试](evaluation/natural-review-seam-v1/predictions.json)、[逐目标与最终答案](evaluation/natural-review-seam-v1/results.json)、[统计及计划分母](evaluation/natural-review-seam-v1/statistics.json)。
- [冻结](evaluation/natural-review-seam-v1/freeze.json)、[准入](evaluation/natural-review-seam-v1/line1-admission.json)、[控制记录口径](evaluation/natural-review-seam-v1/control-records.json)、[离线](evaluation/natural-review-seam-v1/offline-verification.json)、[服务](evaluation/natural-review-seam-v1/service-status.json)。

## 2026-10-25 审核误拦修复与回答交付

[完整报告、56旧目标根因表、唯一合同/投影变化、56份新输出、逐题交付、预算限制及成本](evaluation/review-delivery-unblock-v1/report.md)：统一Flash，Pro新增0调用。只移除候选conditions.answer_ids，由程序绑定当前目标范围；条件三维、来源、gap、异议与危险门禁不变，显式simple_bound_v1/投影v1.2，生产不切换。1268完整离线通过；固定A8+G3+B6全部执行56调用、688531token。A候选4/4完整、原版1/4，保护反例未错误支持；自然两路均0通过、1复核/2执行不完整，正文不变、无Revision/重审，未证明产品交付净收益，保留候选、不进生产验收。 批后检索额度缺口与离线修补单列；学习站20章75解析题，生产保持停服，浏览器未新增验收。

## 2026-10-25 事实审核模型适配性对照v1

[选型、配置差异、参考、顺序、41原始参数、逐目标理由及成本](evaluation/fact-review-model-fit-v1/report.md)：同一simple_v1修补合同/投影及Beta工具路径，固定8组×Flash/Pro各一次，16任务全部执行、41请求（32初始/9纠正）196986token。Pro执行完整8/8、Flash3/8；Pro减少结构失败且部分不足判断改善，但有据目标11/18不必要降级，范围不足仍误判矛盾，费用未知。两种实验配置均不适合直接承担此负担；保留生产现状、Pro仅实验候选，不进服务验收，不加第三模型或新合同。 45付费前/47批后相关离线通过；付费源码与批后停止修补身份单列。生产保持原停服，学习站20章73题，无新增浏览器验收。

## 2026-10-24 严格输出接口一致性排查

[报告、四种Schema、19份原参数、逐目标理由、用量及旧验证集复用表](evaluation/strict-interface-consistency-v1/report.md)：8项合成HTTP对照全部合法、四对实际发送正文相同，接口准入通过；旧材料4项回归仅2项执行完整，复杂参数出现4次额外字段、2次来源ID违规（1次重合，共5次无效请求）。19调用61872token，账单未知；不足仍误判矛盾，不采用、不进完整服务验收。生产schema13/production/json未切、8765保持停服，四表104/2278/2999/8；无常驻候选。44相关离线通过18.821秒，20章71道解析题及构建/引用/链接/HTML检查；浏览器未新增验收。 分类4：基础结构有效，仅复杂业务失败；不能归因客户端或宣称独立成绩。

## 2026-10-24 严格结构化输出接入与审核验证

[完整报告、官方核对、Schema、3份原始工具参数与28槽](evaluation/strict-review-tool-v1/report.md)：只新增strict-review-tool-v1载体，simple_v1业务/投影v1.1不改。按官方文档走deepseek-flash非思考/Beta/单一具名strict工具，nullable两字段用__NULL__双向映射；原始arguments不经SDK丢键，既有重复键/ID/作用域/投影检查保留。1247全套离线通过242.530秒。唯一28槽批次先A1/A3；A1三次都返回指定单工具/tool_calls，但参数2次重复键、1次多闭合括号，0/3合法，接入门禁停止余27槽。3调用（2初始/1纠正）14879token，费用账单未知；自然线未执行，不能评价业务净收益。不采用、不继续服务验收，不换参数/接口或补跑。 393源码冻结一致、旧67私有文件不变；生产默认schema13/production/json不切，8765仍停服，四表104/2278/2999/8不变，无常驻候选。学习站20章69题，构建/引用/链接/HTML检查通过，浏览器未新增验收，已有研究/论文未提交。

## 2026-10-24 simple_v1修补版真实接入

[完整报告、3预测与全部28比较槽](evaluation/review-simple-patch-v1/report.md)：simple_v1沿用v9.22.1提示/投影v1.1，无新语义字段；公共适配器对实际消息做JSON检查，运行预算保留致命请求故障，HTTP错误限长/白名单/安全说明及关联ID脱敏保存。1234全套离线通过236.359秒。新批27槽先候选A1/A2，旧原版A1仅历史参考；A1事实两条有效supported，但原引用初始/唯一纠正均重复JSON键，按接入门禁停止。3调用（2初始/1纠正）、12682token，0请求拒绝，26槽未发送，自然线完全未运行。费用账单未知。未证明整体稳定性/语义提升或自然净收益，不采用、不进生产验收；不补跑、不改提示/标签。 387冻结源码一致、旧simple批42私有文件不变；生产schema13/production配置不切，8765仍停服、四表104/2278/2999/8不变，无常驻候选。学习站20章67题，源码/构建/链接/HTML检查通过，浏览器未新增验收。已有研究/论文未提交。

## 2026-10-24 审核合同简化与条件投影修复

[完整报告与复核入口](evaluation/review-contract-simple-v1/report.md)：显式simple_v1把精确转录交给程序、模型只选作用域内ID并作三维条件判断。付费前1222离线通过；唯一计划A16/G4/B8，只执行A1原/候两个本地运行，5次请求中原版3次返回、候选2次请求拒绝，剩26槽未执行。无纠正/Revision/重审，自然线完全未发送。已知15868token只来自原版，拒绝请求用量和账单未知。不补跑、不恢复attempt；不能证明稳定性、语义或自然净收益，明确不采用、不进生产验收。 已付费版本f08b672bc24fe01aa804d74afbc7140f6e833c13漏JSON模式json字样，且拒绝后同分支又发送引用组。停止后修补提示v9.22.1、候选拒绝即停止和条件/实例独立投影v1.1（88281c910403e69be71963e0b1e3d39d4e70e253）；仅离线，最终1224通过234.165秒。冻结与四份原字节源码可回查，不将修补版冒充真实验证。 学习站20章66题，生产默认不变且服务仍停服。

## 2026-10-24 生产审核链收敛与净收益验证v2

[完整报告、全部预测及成本](evaluation/production-review-net-benefit-v2/report.md)关联旧批根约束诊断、新合同/配置与回退、379源码冻结、1209离线证据、34槽及116原始响应。1209项完整离线回归通过（228.595秒）。唯一固定批次A16+G6+B12共34槽，32实际执行、2因共享初稿生成失败而未执行；116调用（96初始含1次Revision、20纠正），47次无效尝试，1,013,267 token，账单费用未知。候选A八路、自然五条实际审核路均执行不完整，无自然修订收益，明确不采用、不进入生产验收。原版B5一次澄清不计入候选。生产仍schema13/原事实领域修订与政策，8765未监听、保持原停服；无常驻候选。无重发、补跑或新批。 学习站保留20章60自测，旧归档身份不变。

## 2026-10-24 回答与双审核闭环净收益改进v1

[完整报告](evaluation/answer-review-net-benefit-v1/report.md)统一链接事前规则、归档断点、选择与唯一修订提示候选、固定题目参考、375源码冻结、1197离线证据、20槽完整结果、106原始预测含17无效尝试及分线成本。A8+G4+B8唯一批次，5条执行不完整、0未执行/重发/补跑；1126972token。候选未证明净收益，不采用生产；自然线正文不变和N-1/N-2条件疑点保留，不能按pass率评价。生产8765实际停服，配置不切、无常驻候选。学习站20章60自测更新，浏览器未新增验收。既有研究草稿/论文保持未提交。

## 2026-10-24 领域业务候选与事实收尾

事实两阶段未证明收益、暂不采用，保留研究代码与旧归档，不改事实政策。新增domain_internal_flow=business_v1开发装配，生产仍langgraph_v1/production/schema13；一次领域调用按范围/输入/能力/约束组织，无新增规划模型、调用或纠正额度。1187全套离线通过193.070秒；六类12分支唯一真实对照全部首次有效完成，12调用0纠正45814token，无共享故障或重跑，语义未证明提升。两项服务验收随后在受理前因冻结文件名与复用采集器不一致失败，受理0/调用0，按共享程序故障停止，不补跑；修复未来冻结命名后4专项通过7.142秒，原冻结/响应保持。未完成服务真实验收，不采用生产。正常生产服务已恢复并按授权空闲重启；状态和历史SHA核对见最终报告。工具浏览器未登录，合并一次人工清单。生成/修订盘点确认现有公共模块已复用，不强行封装丢失参数。学习站20章60自测、构建/源码/链接通过；无ZIP/数据库副本/重建索引/环境。详见[evaluation/domain-business-v1/report.md](evaluation/domain-business-v1/report.md)、predictions.json、statistics.json、fact-closeout.md及generation-revision-audit.md。


## 2026-10-24 当前两阶段开发对照

- [完整报告与边界](evaluation/fact-two-stage-v1/report.md)：唯一16分支、27调用、原始/有效参考差异、继续候选建议。
- [全部必要预测和无效尝试](evaluation/fact-two-stage-v1/predictions.json)、[逐项结果](evaluation/fact-two-stage-v1/results.json)、[小统计](evaluation/fact-two-stage-v1/statistics.json)、[冻结](evaluation/fact-two-stage-v1/freeze.json)。
- [内部盘点与有限整理](evaluation/fact-two-stage-v1/engineering-review.md)：新增、复用、暂留和领域→生成→修订优先级。


## 2026-10-24 归档续办

[v2真实复验报告](evaluation/fact-internal-flow-v2/live-report-v1.md)已完成归档核对；本次仅解除上次审批用量限制后的提交阻断，不新增模型执行，原结果与参考不变。

## 2026-10-23 最新v2固定参考真实复验

- [本批真实短报告](evaluation/fact-internal-flow-v2/live-report-v1.md)、[必要响应原文](evaluation/fact-internal-flow-v2/live-predictions-v1.json)、[小统计](evaluation/fact-internal-flow-v2/live-results-v1.json)：仅v2六项，6完整、首次4/6、8调用含2纠正；F04有效不足、F05合法异议但内容仍错，生产不变，不自动新批。
- [实际单臂执行计划](evaluation/fact-internal-flow-v2/actual-execution-plan-v1.json)、[155文件冻结](evaluation/fact-internal-flow-v2/execution-freeze-v1.json)：原v1/v2提案保留，历史v1仅描述参考，无严格配对提升率。

## 2026-10-23 最新事实审核契约审计

- [v2审计、设计比较及实现边界](evaluation/fact-internal-flow-v2/README.md)：联合判断与独立义务确认成本比较；统一字段规范，保留独立异议，不做关键词分类或语义补造。
- [6项复验计划](evaluation/fact-internal-flow-v2/revalidation-plan-v1.md)、[完整输入/参考](evaluation/fact-internal-flow-v2/inputs-and-reference-v1.json)、[实际准备消息身份](evaluation/fact-internal-flow-v2/preparation-v1.json)、[离线结果](evaluation/fact-internal-flow-v2/results-v1.json)：0真实调用，旧批封存，生产不变。

## 2026-10-23 事实审核内部候选首真实对照停止封存

用户接受8合成材料并授权本批费用；起始b44271d27231f758306d3ba84ca5da83b88cc2f1。先补F05内容supported/有效复核双层及共同6案例7组件分母，原输入标签不改。新最小事实接口执行入口，6门禁+14候选共20离线通过3.941秒；诊断目录初误拒0发送，修到既有允许路径。实际冻结后一次执行：F01–04两版8分支完整，F05原版已知缺快照继续，F05候选唯一纠正后仍缺合法题设依赖最终失败，后6分支不发送。12请求/3纠正/38822token；首次6/9（原4/4、候选2/5）。共同完成4对5组件/版，有效参考对齐原3/5候4/5，另2组件/版未执行，不当整体正确率。候选F03相关题设选择有利但需纠正，F04两来源/标量true仍因空条件载体有效不足，F05未形成有效异议。全部必要原文含无效尝试公开；原始data、attempt保留，不恢复不补跑，生产不变，暂不接入。见[evaluation/fact-internal-flow-v1/live-report-v1.md](evaluation/fact-internal-flow-v1/live-report-v1.md)、live-results-v1.json、live-predictions-v1.json。结果AI辅助分析、用户监督，待整批统一复核，不自动新批。


- **事实审核内部流程候选交付：[报告与回退](evaluation/fact-internal-flow-v1/README.md)**：明确开发开关、实际内部图、独立分类异议与忠实性、相关题设子集、数字两来源及工程限制；复用原Factory/Harness/Store/API，生产未切。附[验证统计](evaluation/fact-internal-flow-v1/results-v1.json)、[完整固定输入与参考](evaluation/fact-internal-flow-v1/inputs-and-reference-v1.json)、[对照计划和理由](evaluation/fact-internal-flow-v1/comparison-plan-v1.md)、[首消息身份](evaluation/fact-internal-flow-v1/preparation-v1.json)、[节点图](evaluation/fact-internal-flow-v1/node-graph-v1.md)。0真实请求，旧批次不恢复，学习站20章60题更新。

## 2026-10-23 剩余五项完成，本机默认LangGraph

用户新授权仅旧计划未发送五项及达标切换，起始2c75ba0/工作区干净；旧首项不重发、旧失败/attempt不改。新后续入口复用正常Factory/worker/API及独立显式关闭只读收集；7项收集门禁13.849秒及1项清单门禁0.048秒通过，未重复全套。准备曾误拒上轮UI哈希变化，0发送，独立修正工程清单比较；Agent/提示/模型/政策/证据/预算/任务仍与旧冻一致。五项均完成、5个唯一受理、32调用含1纠正，输入399128/输出13890/总413018token，0失败/未执行。三图必需阶段完整；两诊断各一次实际修订和完整重审，图最终待补充、原最终通过，保留语义差异不归因编排。实际本机受管默认已langgraph_v1，正常入口启动ready；四表104/2278/2999/8及全行哈希前后完全相同，环境原编排回退有效。源码无配置回退仍sequential，A/B未采用、不清理候选/历史。实际页面入口已验，工具浏览器未登录，自动连接及登录后引用/版本/失败展示待用户一次清单确认，不绕过file限制。学习站20章60自测由Markdown同步。[短报告](evaluation/langgraph-service-continuation-v1/results-v1.md)、[统计](evaluation/langgraph-service-continuation-v1/results-v1.json)、[必要预测](evaluation/langgraph-service-continuation-v1/predictions-review-v1.json)、[切换核对](evaluation/langgraph-service-continuation-v1/switch-verification-v1.json)。到此停止，不自动新实验。

## 2026-10-22 LangGraph服务集成收尾，默认保持原编排

起始aa033532b4d41fbb71645ea745d300cf423f4ee5、工作区干净。用户授权六次固定服务验收及达标后的默认切换，不授权补跑。正常ServiceConfig/Factory/worker/持久化/API传execution_path，后端配置/回退明确，图实际复用七阶段、原四Agent/schema13/flash/lossless/BM25 aggregate/topic_v4/完整知识版本/政策1.5/原计数不改，A/B未接入。66相关及24保存响应双路径回放通过；旧回放live门禁拒绝当前backend/config与runtime演进，新只读配置显式记录两处变化，旧冻结不动。首次全套1135通过173.146秒；真实首项原编排服务完成pass、5调用55821token，但收集器跨线程读取worker SQLite触发StorageError，停剩5项（图0运行/诊断未执行/Revision未触发）。只读回收25事件和完整结果，不改原summary、不恢复attempt；收集器修复为独立显式关闭只读连接并补成功六项替身，收集修复后全套1136通过162.582秒；最终展示边界补查13项、全套1136通过158.902秒。服务与收集失败分开，默认未切、不冒称图真实验收。当前8765正常服务ready/空闲/sequential，生产历史104运行/2278事件/2999对象/8反馈行哈希冷启动一致，验收库另1项。UI默认问答、折叠诊断、阶段/草稿/认可区分；实际浏览器验证入口/模式文案，file启动页被安全策略阻止，自动连接及登录后引用/版本/失败展示未验收，无绕过。学习站20章60自测由Markdown同步。有限清理合并新回放重复实现，删除227/增26行；A/B/历史协议及原驱动有引用，保留，私有资源不删。见[集成报告](evaluation/langgraph-service-integration-v1/results-v1.md)、[小统计](evaluation/langgraph-service-integration-v1/results-v1.json)、[必要预测](evaluation/langgraph-service-integration-v1/predictions-review-v1.json)、[清理回退](evaluation/langgraph-service-integration-v1/cleanup-and-rollback-v1.json)。本轮到交付停止，不自动语义优化或新付费；未来新批须独立授权，不恢复本批。

## 2026-10-22 OB2真实复验首最终审核失败，已封存

用户整批接受c59badb并授权本批费用，仅修01长度。独立inputs-r1把未识别的220个Unicode字符改为220字符，提示/程序严格220、建议165，220接受221拒绝；其他输入/参考/提示/停止不改。新最小入口复用Harness/run_fixed，6新专项与相关28离线通过2.893秒，冻结107文件后一次执行01→02→03；01生成首次有效103字但两段，R1/R2 covered、R3同段要求partial。规则复述保持literature空题设，数值比较71≥64被列应用、事实两次仅选71题设，缺正文触发最终契约失败；保留8命题/9组件supported、1执行占位，不当语义不足或合法对象异议。02/03未执行，分类异议与错误应用效果未知，不补跑。8调用（6初始2纠正）53617token，最终保存31.711秒非首绘，实际费用未知，预算非不足；领域无纠正、串账未触发。见[短报告](evaluation/public-review-object-v2-live-v1/results-v1.md)、[必要预测原文](evaluation/public-review-object-v2-live-v1/predictions-review-v1.json)、[小统计](evaluation/public-review-object-v2-live-v1/results-v1.json)、[执行冻结](evaluation/public-review-object-v2-live-v1/execution-freeze-v1.json)。62私有JSON/8消息及旧A/B88产物哈希核对，attempt保留，旧入口/生产不变。可进入独立LangGraph真实服务集成验收阶段，只切编排、固定Agent提示政策、比较失败和部分结果，不要求语义全无错；本轮未启图真实运行/新付费批次、不自动开语义支线或清理候选，后续独立范围与授权。AI辅助分析、用户监督运行，未称用户已确认预测。

## 2026-10-22 v2三重点真实复验材料已准备，未执行

用户接受v2离线候选，明确后续图真实集成可独立推进、暂不清理兼容入口。新增[三分支完整复验材料](evaluation/public-review-object-v2-live-v1/README.md)及输入/独立评分/冻结提案：01自然生成同段规则应用，02固定错误应用，03确定性注入错误分类验证真实异议通路。fidelity文字忠实与对象异议分轴解释，03不作自然分类成绩；中性任务ID不泄漏角色，题设71与无关蓝色分开。拟原40共享预算、有限纠正/首最终失败停止；未实现入口、未授权本批费用、无attempt/模型/安装/旧回放。材料身份与注入解析离线核对；旧A/B封存、生产不变。先供整批确认，不自动付费或切图；切换验收后再集中清理。

## 最新离线候选

规则/实例对象边界v2，合法同类别对象异议进入复核，严格联合依据门禁保持；7专项与相关53离线通过，0真实模型，生产不变。 见[交付报告](evaluation/public-review-object-v2/README.md)及[源码身份](evaluation/public-review-object-v2/results-v1.json)。

- **最新B真实验证已停止封存：[短报告](evaluation/public-review-validation-v1/results-v1.md)**（[统计](evaluation/public-review-validation-v1/results-v1.json)、[必要预测原文](evaluation/public-review-validation-v1/predictions-review-v1.json)、[实际冻结](evaluation/public-review-validation-v1/execution-freeze-v1.json)、[私有产物身份](evaluation/public-review-validation-v1/artifact-identities-v1.json)）：60离线检查通过后执行一次；首01QA生成有效、审核最终失败，另3主线及1固定错误诊断未执行。6调用/36804token，非强制规则的应用对象分类与题设依据约束冲突保留；5有效supported与1执行占位分开，不称B修复。生产不变，不恢复A/B或补跑。下列待授权文字为历史准备状态。

- **当前待整批复核：[B有限真实验证4例完整材料与调用计划](evaluation/public-review-validation-v1/README.md)**（[输入](evaluation/public-review-validation-v1/tasks-v1.json)、[独立复核边界](evaluation/public-review-validation-v1/review-criteria-v1.json)、[合成来源身份](evaluation/public-review-validation-v1/source-manifest-v1.json)、[冻结提案](evaluation/public-review-validation-v1/freeze-plan-v1.json)）：4原生成器+B主线＋1固定错误诊断，共5分支；12主线/3诊断要求槽，三组合成开发来源非独立保留集。诊断输入74/答案88，无快照/原引用不补造；主线未触发错误不算检出。计数修复独立记录，拟原40共享保护/有限纠正/首最终执行失败停止，无旧审核真实对照。6项纯离线材料检查与身份核对通过，入口待新授权后实现并门禁；0模型、无attempt，生产和A封存保持。

- **最新B候选实现：[题设独立依据与公共审核接线](evaluation/public-review-premise-candidate-v1/README.md)**（[身份/离线检查](evaluation/public-review-premise-candidate-v1/results-v1.json)）：当前任务独立目录、程序定位、专门TaskPremiseBasis，规则应用联合正文+题设；两种输入共用验证，无快照诊断不补造。原Harness/schema13阶段内可选注入，不加规划/调度节点；候选计数独立启用，生产仍原默认。25专项、一次全套1081离线通过，原/候选及顺序/图差分；错误替身也可合法pass，明确不能证明真实模型语义已修好。0真实调用/旧响应回放/安装，A批次封存，下一次真实验证需另冻结授权。

- **当前B源码核对与工程候选：[公共审核题设/规则/应用边界](evaluation/public-review-boundaries-v1/README.md)**（[范围与离线结果](evaluation/public-review-boundaries-v1/results-v1.json)）：归档用户对A的有范围复核，候选生成合法，停止是公共审核失败，未执行能力未知。语义最小规格尚未接线，题设引用与正文规则分离，应用联合核对，不放宽旧快照门禁。纠正计数可选invocation_scoped_v1已实现，8专项/相关68离线通过；原共享预算与一次事实纠正不变，默认shared_slice_v1/schema13/原顺序路径保留。0真实调用/旧回放/安装，不恢复A实验。

- **最新已授权实跑收尾：[固定证据生成对照结果](evaluation/generation-mapping-comparison-v1/results-v1.md)**（[实际答案/审核及统计](evaluation/generation-mapping-comparison-v1/results-v1.json)、[真实执行冻结](evaluation/generation-mapping-comparison-v1/execution-freeze-v1.json)、[私有产物身份](evaluation/generation-mapping-comparison-v1/artifact-identities-v1.json)）：原40次分支保护、无新增批次帽，99文件/21发送前消息核对；65相关离线通过。实跑2完成/1必需审核失败/5未执行，1完整对，21调用/101712 token；3份答案首次有效、2映射有效，事实2纠正后在GEC-02候选依据类型门禁最终失败即停。9实际槽回应/15未执行不是准确率，01候选附加说明与non_claim疑点保留；未见足够答案收益，暂不采用。新结果AI辅助、用户监督，未称本人逐项确认；禁止恢复或补跑，生产不变。

- **当前整批复核：[4组固定证据生成对照材料与冻结计划v1](evaluation/generation-mapping-comparison-v1/README.md)**：完整问题／要求／6选段及评分边界集中展示；[模型输入](evaluation/generation-mapping-comparison-v1/tasks-v1.json)、[独立评分](evaluation/generation-mapping-comparison-v1/rubric-v1.json)、[来源谱系](evaluation/generation-mapping-comparison-v1/source-lineage-v1.json)、[冻结提案与8组消息身份](evaluation/generation-mapping-comparison-v1/freeze-plan-v1.json)。4任务、8初始生成、12要求／24计划观察；复用3个旧来源为后续开发，非独立验证。固定证据＋相同原审核链，修订0；含审核及纠正预算提案≤128，不是8次总调用。A离线已获用户认可，本材料与新付费授权尚待确认；入口未实现／未执行，0模型，生产不变。

- **当前A离线交付：[最小可选生成映射候选v1](evaluation/generation-mapping-v1/README.md)**（[分层失败、验证与身份](evaluation/generation-mapping-v1/results-v1.json)）：开发入口可选，复用原答案结构／候选／完整快照，一次生成＋最多一次格式纠正；仅映射失败与答案失败独立记，严格候选无效不放行。20专项及相关共139离线通过，未映射新增断言进入全文提取／双审，映射不传审核、不作评分要求。原生产schema13／顺序路径及检索审核修订UI不变，0真实调用；语义收益尚未验证，下一步另冻结真实对照，不自动执行。

- **当前统一设计：[唯一产品主线与四层判定设计v1](unified-business-judgment-design-v1.md)**（[源码身份及检查清单](unified-business-judgment-design-v1.json)）：设计建议，尚未实施。回答＋审核为唯一产品主线，已有回答保留诊断／回归兼容；核对入口、状态、验收，再提出A生成／B公共审核／C局部修订／D展示的最小改动。区分生产文本覆盖、评测任务覆盖与候选能力，保留默认schema13／顺序路径；合成示例、契约关联、部分失败／回退及政策取舍集中说明。0业务改动／安装／模型调用，不自动启动实施。

- **当前业务优化方案：[短概念问答的证据约束生成](concept-evidence-generation-plan-v1.md)**：优先解决已交付证据的使用，拟另版单次生成与诊断映射；首轮固定证据，只比较生成，审核仍独立检查实际全文，映射不是审核真值。直接回答/条件/无据附加/审核/开销分报；本轮仅方案，无实现或新调用，局部修订及其他方向另定。

- **最新用户确认：[第二阶段离线迁移收尾](evaluation/langgraph-adapter-v1/owner-offline-closeout-v1.md)**：用户已读6a70f496交付报告，认可达到离线目标；限定于编排与行为保持，24份回放不算新语义成绩，不记用户本地测试／SHA验真。不切生产、不追加真实调用，默认原路径/schema13不变；后续先讨论一项Agent业务问题再决定定制，尚未启动新实现。

- **当前交付：[可选LangGraph适配v1第二阶段](evaluation/langgraph-adapter-v1/README.md)**（[分项结果与身份](evaluation/langgraph-adapter-v1/results-v1.json)、[实际节点图](evaluation/langgraph-adapter-v1/node-graphs-v1.md)）：7共享阶段由图控制路由，开发开关、原路径默认，38项哈希依赖锁；原19包不升级，无云服务/恢复/额外重试。29项新门禁及全套1016离线通过；25历史响应/每路径1纠正，24预测与原一致，不是新模型成绩，真实API0。开销、首次回放启动失败和回退边界完整保留。学习站相关章节及当前/历史源码身份同步，生产schema13、原标签/分歧不改；第二阶段收尾，后续事项另行决定。

- **当前阶段：[共享阶段抽取v1与离线差分](harness-shared-stages-v1.md)**（[身份/验证记录](harness-shared-stages-v1.json)）：原Harness接口与顺序驱动、7共享阶段，前后相关76项通过、新增11差分通过、全套987离线通过；三处测试夹具问题留痕，未发现未解释行为差异。仅第一阶段，不安装图依赖/新工具、不真实调用或切生产；含Agent/工具定制说明。[schema13生产基线确认](schema13-production-baseline-confirmation-v1.md)单独提交，取代AGENTS过时schema12说明，旧方案待确认文字保留历史。

- **当前方案：[LangGraph迁移方案v1](langgraph-migration-plan-v1.md)**（[代码身份与范围](langgraph-migration-plan-v1.json)）：业务四Agent与独立v7组件分开验证；同一Harness共享阶段、可选图路径，明确节点/状态/接口/预算/取消/存储、离线差分和组件回归。原默认路径、生产、提示及基线不改，首版无图层重试或自动恢复；已记录schema12要求与代码13/14差异。仅方案待确认，0安装/实现/模型调用，不沿用付费授权。

- **最新收尾状态：[整批文本复核与用户确认](evaluation/baseline-batch-v1/owner-text-review-closeout-v1.md)**（[范围、原统计及文件身份](evaluation/baseline-batch-v1/owner-text-review-closeout-v1.json)）：51槽、58参考及66预测判断连同两级理由、依据索引全部公开文本复核完成；ChatGPT复核、用户本人确认，AI辅助用户监督。原5覆盖分歧、2支持分歧、56对齐/2无法对齐及理由问题保留，标签/成绩不改。小规模组件基线收尾，非生产或普遍可靠性证明，0新调用/补跑。下方旧“待复核”表述保留为历史阶段，当前以此记录为准；非本人本地原始响应或SHA验真。

- **整批原文复核入口：[51槽覆盖＋58参考对应全部预测字段](evaluation/baseline-batch-v1/prediction-full-review-v1.md)**：单个轻量Markdown含51覆盖对象原文及理由、66唯一判断、原单元/24总体理由；两个混合未对齐全部拆分，附问题/要求/回答/前提/12依据索引。与最终有效响应字段逐字核对，原报告/分数不改，0新增调用；本人整批复核待后续，不记raw/SHA验真。

- **当前结果：[四来源24回答评审组件冻结批次v1](evaluation/baseline-batch-v1/README.md)**：24最终有效、23首次、25调用/1纠正/86646token；覆盖46/51一致，支持56/58建议对齐、54一致2分歧、2混合未对齐，F双分母0/18及0/38、错误拒支持0/38。对象类型/理由疑点及AI对齐待本人复核，非全面验收；[脱敏统计](evaluation/baseline-batch-v1/results-v1.json)、[理由摘要](evaluation/baseline-batch-v1/reason-quality-review-v1.json)、[事前冻结](evaluation/baseline-batch-v1/execution-freeze-v1.json)、[匹配规则](evaluation/baseline-batch-v1/matching-rules-v1.json)、[本人确认及本批授权](evaluation/baseline-batch-v1/owner-confirmation-authorization-v1.json)、[25实际调用SHA](evaluation/baseline-batch-v1/actual-call-hashes-v1.json)。已结束不追加/恢复，原始data忽略、生产不变。

- **当前待复核改动：[NASA歧义预测前修订v2及原整批复核](evaluation/baseline-answer-drafts-v2/README.md)**：原24回答文本复核归档，原NASA01A03U2不足/矛盾分歧保留；[v2回答](evaluation/baseline-answer-drafts-v2/answers-v2.json)、[v2标签](evaluation/baseline-answer-drafts-v2/expected-labels-v2.json)、[差异与统计](evaluation/baseline-answer-drafts-v2/revision-v2.json)、[原逐项文本复核](evaluation/baseline-answer-drafts-v2/user-text-review-v1.json)、[身份/检查](evaluation/baseline-answer-drafts-v2/manifest-v2.json)。只改1回答，23保持；24回答/51覆盖/58参考，新句与映射待确认，0模型调用，旧v1保留。

- **当前整批复核：[24回答、参考单元与预期标签v1](evaluation/baseline-answer-drafts-v1/README.md)**：4组8家族，51覆盖槽/57参考单元；[回答](evaluation/baseline-answer-drafts-v1/answers-v1.json)、[参考标签](evaluation/baseline-answer-drafts-v1/expected-labels-v1.json)、[组成项](evaluation/baseline-answer-drafts-v1/requirement-components-v1.json)、[题卡文本v2](evaluation/baseline-answer-drafts-v1/reviewed-cards-v2.json)、[AI辅助用户文本设计确认](evaluation/baseline-answer-drafts-v1/question-owner-confirmation-v1.json)、[身份/检查](evaluation/baseline-answer-drafts-v1/manifest-v1.json)。新回答与标签均待确认；NASA题面仅换内部定位措辞，通用协议不变，0预测/调用/训练。

- **当前复核入口：[8张问题卡与明确评分要求v1](evaluation/baseline-question-cards-v1/README.md)**：4组各2卡、17要求、3显式假定；[题卡](evaluation/baseline-question-cards-v1/cards-v1.json)、[评测侧评分解释](evaluation/baseline-question-cards-v1/evaluator-rubric-v1.json)、[来源本人限定确认](evaluation/baseline-question-cards-v1/source-owner-confirmation-v1.json)、[身份/检查](evaluation/baseline-question-cards-v1/manifest-v1.json)。来源已确认，新卡片/要求待本人复核；证据背景非自动必答，NASA用途收窄，0回答/标签/预测/调用，通用提示不改。

- **可直接在GitHub阅读：[四组来源完整选段复核正文](evaluation/baseline-source-review-v1/review.md)**（[原选段JSON](evaluation/baseline-source-review-v1/selected-source-excerpts-v1.json)）：本人授权公开12完整选段及必要上下文/定位/SHA，JSON与私有原件逐字节一致；整份原文快照仍留忽略data。以后复核材料默认提交推送并给远端链接。

- **来源筛选入口：[四组新来源、各两方向](reviewer-baseline-source-screening-v1.md)**（[身份与精确定位清单](reviewer-baseline-source-screening-v1.json)）：NWS/USGS/NASA/CDC，12完整选段及上下文在忽略data/evaluation_local/source-screening-baseline-v1/candidate-originals-review-v1.md，待本人原文范围确认。472文本/518旧PDF页有限审计，快照与原文回切验证；0回答/标签/模型调用，提示不改。

- **当前准备依据：[小规模组件基线正式规格v1](reviewer-component-baseline-spec-v1.md)**（[机器清单与冻结候选身份](reviewer-component-baseline-spec-v1.json)）：本人确认4新来源组/8问题家族/24回答、v7提示＋v6严格解析；取消拟议百分比和未对齐零门槛，实验有效性与能力成绩分开。下一步来源筛选，非最终批次冻结/付费授权；本轮0新来源/题目/调用。
- 原[门槛草案](reviewer-validation-gates-draft-v1.md)保留为历史；其95%/90%及无法对齐为0建议未采用，当前以正式规格为准。

- [v7格式实验本人限定复核](reviewer-v7-owner-review-v1.md)：有限正向证据、保留候选且生产不接入；非全部8份理由原文或本地SHA验真，原结果保留，不补跑或叠提示。
- [下一阶段验证能力与验收门槛草案v1](reviewer-validation-gates-draft-v1.md)：执行/覆盖/支持/类型/拆分/理由分别列建议门槛；数值待本人确认，先规格与规模再新来源，非批次冻结或付费授权。

- [四对v6/v7格式实验结果](evaluation/format-stability-v1/results-v1.md)（[统计](evaluation/format-stability-v1/results-v1.json)、[理由质量意见](evaluation/format-stability-v1/rationale-quality-review-v1.json)、[执行冻结](evaluation/format-stability-v1/execution-freeze-v1.json)）：8最终有效，9调用；v6首次3/4、1纠正，v7首次4/4、无纠正；初始token7628/8736、v6纠正3030。理由语义问题及分类疑点单列，意见待本人，4对不证总体提升；本批结束生产不改。

- [格式实验首次字段完整统计澄清r1](evaluation/format-stability-v1/metrics-clarification-r1.md)（[ID与绑定清单](evaluation/format-stability-v1/metrics-clarification-r1.json)）：按预期要求/单元ID存在唯一无遗漏，不依赖数组顺序；空白理由/非法枚举另由契约处理。原输入/冻结不覆盖，不改提示，0API，非付费授权。

- [四对v6/v7格式稳定性离线材料](evaluation/format-stability-v1/README.md)：[完整输入](evaluation/format-stability-v1/inputs.json)、[复核/理由质量表](evaluation/format-stability-v1/review-checklist.md)、[冻结清单](evaluation/format-stability-v1/freeze.json)。跨4主题、两对各先v6/v7，任务/解析一致，字段/契约/理由质量与初始/纠正token分开；6离线门禁通过，0API，待本人复核非付费授权。

- [v7提示布局候选冻结](reviewer-v7-candidate-freeze-v1.md)（[冻结身份及未来实验边界](reviewer-v7-candidate-freeze-v1.json)）：本人接受工程实现，真实改善未知，停止叠加提示；后续同批跨主题开发输入对照v6/v7，格式与独立语义评测分开。当前未制作输入/未冻结付费批次，0API、生产不接入。

- [评审理由字段v7离线候选](reviewer-rationale-layout-v7-offline.md)（[审计/身份/检查](reviewer-rationale-layout-v7-offline.json)）：4原响应共7处单元理由遗漏，提示/纠正接线已送达；保留全部理由字段，明确层级职责并后置唯一结构示例，严格复用v6解析。12新合成及67合计离线通过，0真实调用；稳定性收益未实测，不接生产、不重跑旧题。

- [v6全部12单元本人最终对齐确认](reviewer-v6-alignment-owner-confirmation-v1.md)（[逐项确认与身份](reviewer-v6-alignment-owner-confirmation-v1.json)）：12参考均可对齐、11支持标签符合参考，NRC-A04/U2分歧保留；合并预测只算一个实际判断，旧批规则/成绩不改。公开字段语义复核，不称本人本地raw/SHA验真。v6继续归档、生产不接入，0新调用。

- [v6十二参考单元预测原文表](reviewer-v6-prediction-excerpts-v1.md)（[原字符串与响应SHA](reviewer-v6-prediction-excerpts-v1.json)）：按本人授权公开所选命题、标签、依据及两级理由；12映射行对应11预测判断，已对照最终有效响应。本人随后已完成全部12参考最终对齐确认，详见上方新增确认；0新API，原数据不改。

- [v6评审候选归档](reviewer-v6-candidate-closeout-v1.md)（[复核范围及身份](reviewer-v6-candidate-closeout-v1.json)）：本人报告复核，已见开发改善但语义/结构限制仍存，暂不接生产；EIA-A04本次可对齐及旧记录保留，NRC-A04分歧保留；归档时待确认的12单元现已另立最终确认记录。0新调用、不再改到全对。

- [v6八例开发复验结果](reviewer-v6-development-recheck-results-v1.md)（[统计/对齐ID](reviewer-v6-development-recheck-results-v1.json)、[执行冻结](reviewer-v6-development-recheck-freeze-v1.json)）：8最终有效、4首次有效，12调用/4纠正/28391token/28.659秒；覆盖16/16一致，支持12参考对齐已获本人后续确认（独立确认记录见上）；NRC-A04不足→矛盾分歧保留，稳定性/费用无改善声明。原规则/标签/成绩及生产不改，本批结束不恢复。

- [v6有限开发复验计划v1](reviewer-v6-development-recheck-plan-v1.md)（[机器计划](reviewer-v6-development-recheck-plan-v1.json)）：原8例、顺序/标签/匹配不变；8消息离线核对，0API，最多16调用为拟定上界。待确认及本次付费授权，非最终执行冻结或新独立成绩。

- [评审组件v6离线修订](reviewer-component-v6-offline.md)（[身份与检查清单](reviewer-component-v6-offline.json)）：覆盖与正确性分离、文献/实际对象区分、实际记录溯源门禁；17新合成及51合计离线通过，0API，未验证模型语义改善。生产/旧v5候选/旧成绩/匹配规则不变；EIA/NRC已登记后续开发，下一次复验待本人决定。

- [EIA/NRC冻结批次v1结果](reviewer-eia-nrc-batch-v1.md)：本人已读报告复核，8有效、10调用18145token、2纠正；三类问题分别保留：覆盖口径未遵循/定义任务身份误判/复合参考按冻结规则未对齐，原预期不改；[冻结](evaluation/eia-nrc-answer-drafts-v1/batch-freeze-v1.json)、[统计](evaluation/eia-nrc-answer-drafts-v1/batch-results-v1.json)，本轮结束不重跑。

- [EIA/NRC公开回答与标签复核表](evaluation/eia-nrc-answer-drafts-v1/evaluator-only/review-table.md)：本人授权公开8回答/16coverage槽/12参考单元，8例标签内容已获本人确认；[JSON与用途隔离说明](evaluation/eia-nrc-answer-drafts-v1/README.md)，不含证据全文或模型运行数据，0API。

- [EIA/NRC八回答与预期草案](reviewer-eia-nrc-answer-drafts-v1.md)：各4样例、16coverage槽/12参考单元，完整回答/标签后经本人授权公开供复核（原件仍留忽略目录），8例内容已获本人确认；离线白名单核对通过，0模型调用，非执行冻结、协议不改。

- [EIA/NRC两题卡草案](reviewer-eia-nrc-question-cards-v1.md)：H-EIA-001构成/区间、H-NRC-001对象比例/过程时间，各两项独立要求；本人复核修改已落实：系统数量明确、NRC负面说明归支持边界，非最终批次冻结；无回答/标签/预测，固定协议不改。

- [新保留来源筛选v2](reviewer-holdout-source-screening-v2.md)：EIA非同时需量完整定义段、NRC半衰期首句及上下文；官方HTML快照/SHA、有限谱系与近重复核查，选段及边界已获本人确认，NRC经官方检索交叉核对、非本人快照SHA验真；来源仍候选；两卡草案另列待复核，未预测、协议不改。

- **下一阶段固定候选：[独立评测通用协议v1](reviewer-independent-protocol-candidate-v1.md)**（[机器清单](reviewer-independent-protocol-candidate-v1.json)）：本人已采纳，非最终批次；映射须原定义依据、混合/歧义不自动转换，顺序事前固定并报告停止实际覆盖；v5与coverage v2及映射显式绑定，已知缺陷不隐藏；未选新来源、未冻结批次、0API。

当前交付按本人授权在本地提交后普通推送；不纳入data或恢复模型实验。

- **当前阶段入口：[评审开发阶段收尾v2](reviewer-development-closeout-v2.md)**：三批记录分开、未整批验收，33离线通过、停止追加；MIT/BIPM均后续开发，独立评测未完成。以下早期“待确认/待批准”等条目为各自时点记录，最新状态以收尾与交接首条为准。

- [9支持单元文本对齐确认与映射溯源](reviewer-remaining8-v5-results.md)：本人确认文本对齐，标签/理由张力及SI例外边界保留；找到旧批冻结映射，本批未显式绑定的记录限制另列，0API。

- [剩余8项文本复核与只读失败核对](reviewer-remaining8-v5-results.md)：本人仅复核报告文本；助手核对7响应哈希与两结构原因，9有效支持单元复核表留忽略目录待本人确认，0API、不恢复执行。

- [剩余8项v5开发结果](reviewer-remaining8-v5-results.md)：7调用14258token，4有效/1失败/3未执行；MIT覆盖混入正确性、SI省例外错误支持、SI-A03契约失败均保留；[统计](reviewer-remaining8-v5-results-stats.json)，不补跑。

- [剩余8项v5开发计划](reviewer-remaining8-v5-plan.md)：22coverage槽、20支持单元；最多16调用计划/匹配停止规则及执行门禁离线就绪，待明确批准，0API。

- [开发侧覆盖定义v2：30槽文本确认完成](reviewer-coverage-definition-v2.md)：两轮合计23covered/5missing/2partial，仅改两处理由；原参考不覆盖，未确认JSON/SHA、未冻结或授权执行，0API。

- 覆盖定义v2其余25槽复核材料：忽略目录coverage-definition-v2-review-remaining25中的review-table.md供本人逐项复核，含完整构造回答不公开；25槽全部待确认，0API。背景见[定义v2](reviewer-coverage-definition-v2.md)。

- [开发侧覆盖定义v2与五项文本确认](reviewer-coverage-definition-v2.md)：四covered、一partial；非原标签等价改名，25槽/JSON/SHA未本人确认，未冻结或授权调用。

- [覆盖参考v2草案](reviewer-coverage-reference-v2-draft.md)：30槽另存覆盖建议，5个not_met逐项复核、SI-A04范围边界重点待确认；旧标签不改，0API，不启动剩余8项。

- [A04 v5单项开发复验](reviewer-a04-v5-recheck.md)：原输入一次，1调用1732token、2.589秒、零纠正，覆盖与支持主要判断符合参考；没有验证纠正路径，不补8项；[统计](reviewer-a04-v5-recheck-stats.json)。

- [v5开发侧精确字段诊断](reviewer-field-diagnostics-v5-offline.md)：缺unit理由明确定位；30项离线通过、0API、不补跑；MIT/BIPM关联组转后续开发，历史结果保留，生产不变。

- [两题固定评测v1](reviewer-fixed-batch-v1.md)：恢复授权后6调用10495token，3有效、1契约失败、8未执行；缺unit理由纠正仍失败即停止，非独立成绩；[统计](reviewer-fixed-batch-v1-stats.json)。

- [开发侧评分定义统一](reviewer-coverage-semantics-development-v1.md)：本人暂停12项执行；分开覆盖、证据支持和正确作答要求满足度，16项既有离线回归通过；保留题hold，0API。

- 执行准备状态：人工not_met与现有coverage口径冲突，待明确处理方式；见[交接](handoff.md)。尚未调用或冻结可执行批次。

- [两题回答与预期审核确认](reviewer-holdout-question-cards-v1.md)：用户确认外部包12回答/27参考单元；哈希与原文绑定核对，忽略目录保留标签；最终匹配及执行协议待冻结，0预测。

- [两题初步复核及BIPM措辞修订](reviewer-holdout-question-cards-v1.md)：MIT设计保留，BIPM评分范围不变、题目采用本人建议；旧卡保留，无样例或预测，非执行冻结。

- [保留来源候选正式登记与两张待复核题卡](reviewer-holdout-question-cards-v1.md)：本人确认建设规则及MIT/BIPM选段/范围；类别关系与单位符号书写题卡草案，要求独立评分，非最终协议/批次；0预测、不改生产。

- [MIT/BIPM候选选段复核](reviewer-holdout-excerpt-review-v1.md)：MIT热敏电阻定义与BIPM单位符号书写完整规则；范围/原页/区间及有限重合审计，不出题不预测，待本人确认、不正式入组。

- [保留来源两候选与谱系初核](reviewer-holdout-source-selection-v1.md)：MIT6.002 2007转录及BIPM SI9 V4.01；官方快照/SHA与范围内开发使用记录核对，待本人及选段复核。只选来源、不出题/预测，不证明训练未见。

- [评审组件保留集建设规格v1（建设规则）](reviewer-holdout-spec-v1.md)与[来源分组清单草案](reviewer-holdout-source-groups-v1.md)：仅评审组件，按原文档/谱系隔离开发与保留，全计划报告失败，结果驱动改协议后转开发；补充推导调用上界、错误支持双分母及训练污染限制；仅来源候选，最终协议未冻结、无预测。

- [CT/TR/SW/RC四个开发家族汇总](evidence-bound-development-summary-v2.md)：测试目的、协议、实际有效结果与未决项分开；RC三类结论保留，暂停调用，不合并准确率或把离线检查数量当语义能力。错误映射/规则连接仅未来覆盖项。

- [RC-001 v4一次冻结复验及收尾](evidence-bound-rc001-v4-recheck.md)：31离线后5调用13421token/2纠正；B独立评分、A前提身份观察符合预期，C缺unit理由导致最终契约失败，语义未全验收；停止追加、关闭本轮。[小统计](evidence-bound-rc001-v4-recheck-stats.json)。

- [RC-001评测设计v4仅离线](evidence-bound-rc001-protocol-v4-offline.md)：独立R1/R2、题设/文献类型身份、程序派生数量分类；27离线通过，原记录不改，0API，无付费入口。[小统计](evidence-bound-rc001-v4-offline-stats.json)。

- [RC-001真实开发检查与分歧](evidence-bound-rc001-evaluation-v1.md)：15离线后原A/B/修订C各一次，4调用7400token/1结构纠正；B的R2部分覆盖及题设外露依据处理不一致保留，不宣称全语义通过。[小统计](evidence-bound-rc001-stats-v1.json)。

- [显式规则链资料候选RC-001](evidence-bound-rule-chain-candidate-v1.md)：OSHA完整术语定义＋入口标志规则、同域及去段检查；简单定义链有词义先验捷径限制；题卡/R1/R2/参考已确认，A/B预期已接受，C改为用户指定十年寿命保证；旧C歧义及撤回唯一标签留痕，E2附带600V范围，0API。

- [SW-002候选去段检查](evidence-bound-sw002-source-audit-v1.md)：两完整定义身份核对；单段可有限回答核心非全称结论，双段补足说明但不证明必要组合推理。暂不冻结，同ABB关联组、0API。

- [SW-001中文同义改写单项检查](evidence-bound-sw001-synonym-v1.md)：D及预期明确确认、18离线通过后一次执行，R1/R2覆盖且两项有据；1调用2085token/零纠正，原提示不变、A/B/C未重测。结果已接受并归档，停止SW变体；仅同家族开发检查，不推普遍同义理解，不加入双段证据。[小统计](evidence-bound-sw001-D-stats-v1.json)。

- [证据绑定开发评测阶段收尾](evidence-bound-development-closeout-v1.md)：CT协议失败/评分要求缺失、TR/SW主要模式成功分开保留，不合并准确率；核对会话接受与AI建议的监督来源边界，下一阶段同义/双段证据仅候选。

- [SW-001一次开发评测](evidence-bound-sw001-evaluation-v1.md)：15离线后A/B/C各一次，完整性与条件支持分开；主要预期一致，3调用6261token/零纠正，单已见开发家族。[小统计](evidence-bound-sw001-stats-v1.json)。

- [SW-001来源、已确认题卡与样例草案](evidence-bound-sw001-source-v1.md)：ABB同一手册低压定义、印刷25/26精确选段及开断条件；R1隔离/R2有界电流开断，区分disconnector与switch-disconnector，不预置全称禁断或无限故障保证。R2不强制额定参数解释，附加能力保证另受条件支持边界约束；题卡设计已确认、本人未独立验真，A/B/C标签已确认并执行，实际结果见一次开发评测。

- [TR-001逐项要求协议v3与真实开发测试](evidence-bound-tr001-protocol-v3.md)：12离线后原A/B/C各一次，实际消息明确含R1/R2；A齐全有据、B缺R2但已有结论有据、C要点齐全但附加保证无据，主要模式与标签一致。3调用4824token/零纠正，单家族非独立成绩、非CT严格A/B。[小统计](evidence-bound-tr001-v3-stats.json)。

- [TR-001教材来源与题卡](evidence-bound-tr001-source-v1.md)：问题、R1/R2、三个synthetic判断及允许表达已获本人确认，来源身份固定；印刷10/PDF18、PDF身份和乱码转录边界保留。实际测试见协议v3，非独立成绩；下一题检查必答点实质区别、合理同义/合并表达与证据不足边界。

- [指定文本开发评测v2](evidence-bound-evaluation-v2.md)：程序单元/多判断、coverage/support分离，结构3/3。实际消息未交付两项必答清单/逐项覆盖，B保留为分歧＋设计缺口，不能只归模型能力；C理由“供电”偏移留痕。3调用3654token，非独立成绩。[小统计](evidence-bound-evaluation-ct001-v2-stats.json)、[只读消息核对](evidence-bound-evaluation-ct001-input-audit.json)。

- CT-001首次冻结开发评测结果见[逐题报告](evidence-bound-evaluation-v1.md)：S1位置越界、一次纠正后失败停止，后2未发；2调用1938token，有效0/3、语义指标未知。[小统计](evidence-bound-evaluation-ct001-v1-stats.json)。下列逐步建设状态按历史记录解释。

- [小型证据绑定评测集逐题建设](evidence-bound-evaluation-v1.md)：CT-001及3项synthetic判断已获本人确认，绑定要点/错误位置；指定文本用途理解开发题、出处未核实，无支持不等于错误。未来付费已授权，批次尚未冻结/执行。私有绑定留在data，不以历史pass/supported作标准答案。

- [第二版冻结与验收](release-freeze-v2.md)：严格长度规划与一次纠正，最终v4/lossless两题完整执行/长度通过/程序pass，内容语义与浏览器项目未全部通过，限定原型冻结；[新电脑独立学习站同步清单](learning-site-sync-v2.md)，20章/60自测及标准库独立读站。


- [检索与审核消息优化v2](retrieval-message-optimization-v2.md)：六主题首次/重复及覆盖、lossless完整正文包装、JSON嵌套原因、两题四run真实速度/失败/纠正与token；v5非默认，继保候选生成超限失败保留，整体未达标。附[小统计](retrieval-message-optimization-v2-stats.json)。


- [本人新主题修复v1](owner-trial-fix-v1.md)：主体约束BM25、严格引用输出投影、任务范围与页面修复；一次同题API13.709秒/总60.154秒、完整执行但review_required，内容及10秒目标未全面满足。附[小统计](owner-trial-fix-v1-stats.json)。

- [实际检索优化v1](retrieval-optimization-v1.md)：topic_v3_rank_v1落地、6请求覆盖/分段/重复、原两题真实前后22调用388790token、PF有效提速及FLUX未达目标/条件呈现限制、空间与回退。附[小统计](retrieval-optimization-v1-stats.json)。

- [离线检索诊断v1](retrieval-performance-diagnosis-v1.md)：原4请求缺数量/上下文参数，0重放；可选内部单调计时/31离线、SQL仅规划与嵌套计数口径纠正、真实分段和波动未知。附[脱敏小统计](retrieval-performance-diagnosis-v1-stats.json)。

- [第二阶段性能粗测v1](performance-profile-v1.md)：首版保持，唯一e141cf2b…后台151.643秒/4检索137.742秒，5调用86222token；检索瓶颈与未知FTS/持久化/首绘分列，只读导出/11项离线及建议未实施。附[小型脱敏统计](performance-profile-v1-stats.json)，无答案/证据全文或ZIP。

## 当前：2026-10-08 首版冻结

- [首版验收](release-freeze-v1.md)：最后本人run、已验证/未通过/限制、完整FTS与性能范围、停止边界。
- [只读迁回准备](return-migration-preparation-v1.md)：旧manifest之后新增材料、空间、SQLite一致性备份与恢复顺序。

以下“当前/最新”按历史阶段解释。

## 2026-10-06 审核接口 v2（最新）

[audit-interface-v2](audit-interface-v2.md)：来源条件载体ID/严格绑定、原始与有效判断、旧失败协议投影、新3真实完整执行与修订未触发、ID拒绝/浏览器/重启及构建已停止。源码condition_candidates/support_relation_v5/review_fidelity/answer_body及既有Harness/政策。私有统一包data/runtime_local/audit-interface-v2，不公开真实输入/响应。


## 2026-10-06 首版收尾（最新）

[first-release-v1](first-release-v1.md)：任务范围缺口/部分可修复项、条件同义与精确摘录、protocol5接线失败及修复、实际未完成项、逐任务NLI与跳过/重启、后台构建和覆盖核算。私有统一包在data/runtime_local/first-release-v1；真实数据不入Git。源码policy/runtime、domain/generation/support_relation、backend服务/API/开关和corpus_build。


- [电力大语料、中文FTS与整句支持 v1](industry-corpus-v1.md)：完整字节下载、3片格式缺口、可恢复构建/明确部分快照、固定真实对照与剩余语义限制。

## 2026-10-06 基础概念覆盖（当前）

[basic-coverage-v1](basic-coverage-v1.md)：BAAI有限抽样与未采用理由、TUP正文/源定位/排版归一快照、source-support-relation-v1与schema13日常配置、两题真实引用及剩余问题。源码services/support_relation.py、agents/verification_contract_v10_batched.py、backend/assembly.py；原件/逐字映射/输入响应/审阅包留在data/runtime_local/basic-coverage-v1与data/retrieval_local/basic-coverage-v1。

## 2026-10-05 无功试用定向修复（当前）

[qa-targeted-v2](qa-targeted-v2.md)：267字符原回答、事实第9项冻结立场失败、明确长度与schema13提示修复、618回归、唯一140字符真实验证仍待补充及浏览器证据。源码services/answer_constraints.py、review_fidelity.py，agents/generation.py、verification_contract_v10_batched.py、revision_contract_v2.py；私有冻结/原新消息/短ZIP在data/runtime_local/qa-targeted-v2。

## 2026-10-05 中文日常使用收尾 v1（当前）

[zh-daily-v1](zh-daily-v1.md)：一键日常入口、会话/停机、网络诊断、3来源和复用库调查、固定真实验收、未达概念质量目标。源码backend/local_session.py、launcher.py、api.py、config.py；daily生成/提取提示及静态页面；611回归。私有reading-notes、verification-final、真实输入/响应、耗时、浏览器/重启和审阅ZIP位于data/runtime_local/zh-daily-v1。长期手册保持原要求，只追加本輪知识点。

## 2026-10-05 中文问答与展示 v1（最新）

[qa-usability-v1](qa-usability-v1.md)：有限跨语言补检、无回答待补充/不适用、中文生成提示、答案引用/默认折叠；唯一真实运行连接失败与未完成范围。私有qa-usability-v1保留冻结/原始运行/实际浏览器/测试/哈希/审阅包，历史不回填。

## 2026-10-05 产品逻辑与性能改进 v1（最新）

- [产品处置、适用范围、真实失败、性能与试用](product-improvement-v1.md)：原v1四真实结果、新v1.1离线修复、直接AI失败和未完成检查分开报告。
- harness/product_policy.py与原runtime/states；core产品合同；backend日常装配/页面；generation可选提示；只读PDF校验缓存及tests/test_product_policy.py。
- 忽略product-improvement-v1：修改前源码诊断、冻结预期/配置、原真实/合成结果、政策重放、性能/资源缺口、浏览器/重启/测试和ZIP；无凭据/DB/权重。长期学习内容暂停，仅记录后续知识点。

## 2026-10-05 连续连接体验（最新）

- [固定令牌路径、浏览器主动记忆、401与验证](connection-memory-v1.md)：不同验证目录是不同服务身份，日常固定文件复用，579回归/实际浏览器通过。
- backend/static/connection_memory.js及app.js/页面，backend/api静态白名单；tests/test_connection_memory.py和ui_connection_memory_probe.js执行实际脚本，不导出令牌。
- 忽略connection-memory-v1仅保存路径/stat/布尔验证/截图/测试/verification-final，真实值和浏览器存储不归档。

## 2026-10-05 NLI真实接线v2（最新）

- [类型/组件范围修复与一次真实验证](local-nli-wiring-v2.md)：575离线，1实际组件、Fact/NLI同supported，业务仍review_required，4真实请求；浏览器/重启/停止已验证。
- services/local_nli.py的production_frames_v1保留及默认转换v2；evaluation/support_nli.py处理合法空provenance；tests/test_local_nli_wiring.py真实Harness schema13 synthetic贯通，不绕过转换。
- 忽略data/runtime_local/local-nli-wiring-v2：提交前request/source/config/preview/源码SHA、一次正常真实run及nli/trace/实际身份/全文token、只读历史类型对照、浏览器/重启hash、原记录不改/默认不变、ZIP与verification-final。DB/权重/令牌不打包，不重放run-id标记。

## 2026-10-05 本地NLI可选旁路（最新）

- [职责/配置/实际回放/浏览器/限制](local-nli-diagnostic-v1.md)：默认关闭、无最终审核权，固定epoch1，严格交付范围，不改原政策。
- services/local_nli.py、backend/nli_worker.py及backend服务记录/API/独立页面；tests/test_local_nli.py公开synthetic回归。
- 忽略data/runtime_local/local-nli-diagnostic-v1：错误说明修正及清单、profile/源码校验、初始失败、33+2已见诊断回放/原logits/输入、只读历史缺口、HTTP/浏览器截图/重启记录/资源、ZIP/verification-final。新回放数据库留本机，不打包，令牌不读/不输出/不打包。

## 2026-10-05 扩大微调与SSIAG文档留出实际结果（最新）

- [一次实际训练/留出/风险与运行](support-nli-expanded-v3.md)：69明确确认另版，43/12/33；epoch1，macro-F1提高但错误supported4/23，不接生产。
- evaluation/support_nli_expanded.py与tests/test_support_nli_expanded.py：确认子集、冻结SHA、开发/文档隔离、train/heldout阶段seal与排他输出、双分母/三类矩阵。
- 忽略data/runtime_local/support-nli-expanded-v3：confirmation-event/confirmed69/监督78视图、55开发/33留出、固定分配/输入/token/有效集合/config/源码模型SHA、独立环境、run-v1四epoch/selection-seal/两逐项logits/指标、错误分析/保留性检查、ZIP/verification-final。权重留本机不入ZIP/Git，原pending和历史保持。

## 2026-10-05 78项复核与扩大开发计划（最新）

- [复核接收/69pending/合并家族/SSIAG留出/适配器v2](support-nli-review-v2.md)：55开发→13家族→43训练/12验证，33文档留出，仅准备0训练/预测。
- evaluation/support_nli_review.py（read_review_archive/receive_pending/merge_groups/propose_split）、support_nli.py（v1保留、v2正文路由、pending训练前置拒绝）及公开合成测试。
- 忽略data/runtime_local/support-nli-review-v2：received原包/成员SHA、quality-version、69/6/3分流、三修改理由、69模板/清单、原划分/关联边/新划分、55合并与33留出、token预检、固定官方基座计划、验证/失败及审阅ZIP。原78/19/历史报告不覆盖。

## 2026-10-05 NLI实际比较、训练与新候选（最新）

- [NLI完整结果与限制](support-nli-v1.md)：两个预训练NLI头、事前验证/资源选型、唯一4epoch领域微调、5项开发对照、78pending候选与未来文档隔离。
- evaluation/support_nli.py、support_nli_candidates.py及对应合成测试；生产默认保持。
- 忽略data/runtime_local/support-nli-v1：模型来源/实际revision/冻结配置、comparison两报告、training-run-v1实际输入/前后预测/逐类指标、78候选/标签模板/来源/未来划分/审阅HTML、失败说明、ZIP与verification-final.json。权重/PDF/私有监督保持本机，不公开。
- 最终手册要求Markdown＋本地文档站/PDF可选；已追加NLI知识点与源码入口，本轮未建站或重写手册。

## 2026-10-05 新机上下文与长期手册要求

- [最终手册要求](final-handbook-requirements.md)：最新采用Markdown＋本地文档网站，PDF可选；38页r1为阶段版。本轮只维护要求，不建站或重写正文。
- [最新交接](handoff.md)：核对基线27ec898、当前生产配置、源码入口、已完成首次训练和待补NLI章节；具体NLI任务说明待补充。
- 本机恢复报告与验证：忽略`data/runtime_local/new-machine-restoration/new-machine-restoration.md`、`verification.json`、`browser-verification.json`。恢复已完成，不重复迁移/监督确认/首次训练；不把前轮536测试当本轮重跑。
- 当前训练结论仍以[support-finetune-v1](support-finetune-v1.md)及实际report为准；下面按日期保留历史素材，旧“未训练”不代表当前状态。

## 2026-10-05 监督74、独立基线与首次三类CPU微调

- [实际监督/材料许可/硬件/运行/结果与限制](support-finetune-v1.md)：74confirmed，71辅助hold未确认；79新请求/69有效/5作用域失败；同BERT基座实际一次微调，11训练/3验证/5测试，不接生产。
- evaluation/support_baseline.py执行v2；evaluation/support_training.py的模板确认、许可筛选、家族划分、完整文本投影及独立CPU训练；requirements-training-v1.txt只隔离环境；tests/test_support_independent.py、test_support_training.py公开synthetic_fixture。
- 忽略data/runtime_local/support-finetune-v1：confirmation-event/confirmed-primary/source-filter/partition-plan/training-config/model-revision/训练环境lock；deepseek-baseline-v3原冻结/预测/指标/checkpoint；training-run-v1初始模型/验证最优检查点/前后预测/report；reading-notes、final-report、verification-final、监督对照ZIP与失败日志。实际79响应在忽略retrieval_local/support-baseline-v2/full74-v1，逐SHA核对。
- 保留旧145、原91/48/6/旧预测、历史网络与PDF，不改写为新监督或成功结果。


## 2026-10-05 54复核接收与74候选基线准备

- [合并/依据子集修复/准备范围](support-review-merge-v1.md)：全145保留，74主候选仍pending，尚未运行基线。
- evaluation/support_review_merge.py及tests/test_support_review_merge.py：无API接收/合并/逐样本冻结；support_review_quality仅保留实际依据子集。
- 忽略data/runtime_local/review-expansion-54-v1/：received、merged-v1清单/分流/共享关系/请求冻结、合并报告、ZIP、reading-notes/verification与离线日志。原资料及任务保持，不重建PDF。


## 2026-10-05 91监督审阅接收与新增质量检查

最终本机入口：quality-supplement-v3.zip、expansion-quality-dataset-v1.json及import-pending-v2；hold/辅助实际从主任务eligibility排除，48原task保持、6修订仍pending。旧补充版本留存。

- [选择性监督、实际48项质量检查及新任务身份](support-review-quality-v1.md)：91分流33/29/29，新增48为36/1/11，另建6pending任务；不整包确认或沿parent搬旧预测。
- evaluation/support_review_quality.py；公开tests/test_support_review_quality.py（synthetic_fixture）。运行仅离线，不改生产协议。
- 忽略data/runtime_local/support-review-quality-v1/：import-pending-v1三个分流、源审阅报告、expansion-quality-review-48.md/json、amended-tasks-v1/v2及review、priority-confirmation-template-33、hold-repair-requirements-29、quality-supplement-v2.zip、prediction-scope-check、reading-notes.md、verification.json及测试。附件原pending字段与用户当前监督声明分别保留。
- 来源PDF/私有任务/标签不公开，最终r1手册不改。确认范围和Git/远端证据以本机verification为准。

## 2026-10-04 知识库与支持判断样本扩充 v1

- [实际官方来源/覆盖缺口、入库快照、pending样本与隔离](knowledge-support-expansion-v1.md)：新4PDF（3开发＋1预留）、48新候选/16家族；不覆盖旧91或重跑基线。
- evaluation/knowledge_support_expansion.py：离线复制知识历史、来源锚定、原文定位及复用候选/复核出口；tests/test_knowledge_support_expansion.py：公开临时synthetic_fixture。
- 私有data/runtime_local/knowledge-support-expansion-v1/：source-manifest/acquisition、development.sqlite3/reserved-evaluation.sqlite3、ingestion、parse-summary、curated-families、candidates-v1/v2、support-review-expansion-v1.zip、reading-notes.md、verification.json、offline-tests与选页PNG。全文/候选不入Git，预留文档不进开发库。
- 最终r1手册继续保留，未扩写或重建PDF。pending不能替代用户监督或独立金标准。

## 2026-10-04 证据支持判断数据集与未微调基线 v1

- [任务/标签、实际候选/划分、运行命令与失败基线](support-judgment-dataset-v1.md)：未训练、未改生产审核；pending不计算语义指标。
- evaluation/support_dataset.py：提取/校验/去重/家族分组/AI辅助复核导出与监督合并；evaluation/support_baseline.py：现有连接器基线、离线四分类指标、仅确认标签JSONL出口。
- 公开tests/test_support_dataset.py、test_support_baseline.py；实际页面脚本tests/ui_render_probe.js及test_ui_render.py。数据/原文/实际响应不入Git。
- 本机data/runtime_local/support-dataset-v1/：reading-notes.md、verification.json、prepared-review-v2/、support-review-package-v1.zip、baseline-frozen-v1/、offline-review-v2-metrics.json、offline-tests日志和browser-verification.json。91项全pending，2请求后结构失败停止，仅5有效部分预测；0确认，不宣称语义正确率或完成整批。
- 来源与划分报告保留22片段跨集合共享、274缺冻结请求跳过；既有私有历史不覆盖，r1/PDF不重建。当前状态与路线已区分数据准备已实现、训练尚未启动。


## 2026-10-04 真实服务可选语义检索 v1

- [运行、配置、生命周期、三模式固定对照与真实结果](semantic-service-v1.md)。bm25默认、事实策略独立；不下载/建索引/退回默认，完整重放开销明确。
- 服务backend/config.py、assembly.py、service.py、api.py；rag/semantic.py、embedding.py、harness/retrieval.py；安全页面详情backend/static/app.js。公开固定对照入口evaluation/semantic_service_comparison.py、七项公开tests/test_semantic_service.py。
- 本机data/runtime_local/semantic-service-v1/：reading-notes.md、verification.json、comparison*.json、resource-*.txt、冻结计划、475项根/干净测试日志、real-summary.json、real-verification.json、Evidence和restart-verification.json。run4676b27e：11请求、一次自然Revision、必需阶段完整/0执行问题，业务仍review_required。实际输入/响应/模型/库保持忽略。
- 旧手册/PDF、semantic历史报告保留。真实HTTP检查不替代浏览器检查；消息投影不冒充已发送/已验证，计数与资源测量口径见说明。当前提交/普通推送回查在本机verification.json及Git日志。

## 2026-10-04 逐主张事实检索与证据交付 v1

- 实现提交02c71bd已普通推送master并回查远端同哈希；最终交付说明提交及回查记录在本机verification.json。使用命令级127.0.0.1:7890代理，未改全局代理或SSL。

- [实现与运行](per-claim-fact-retrieval-v1.md)：可选策略、事实对象/依据分流、查询缓存、显式版本/范围、失败与容量、schema13输入v1、预算及安全页面详情。
- [固定对照](per-claim-fact-comparison-v1.md)：四组相同回答/主张/知识/BM25，目标命中与交付、持平/增益及额外资源/延迟；保留aggregate默认。
- 源码：harness/fact_retrieval.py、services/fact_delivery.py、evaluation/fact_retrieval_comparison.py；13项新公开synthetic_fixture测试test_fact_retrieval_v1.py。
- 本机data/runtime_local/per-claim-fact-v1/：comparison-frozen.json、comparison-results.json、comparison-final.json；frozen-real-plan.json、api-result.json、api-trace.json、real-summary.json、real-verification.json、evidence-roundtrip.json、restart-verification.json、offline-tests-delivery.txt、reading-notes.md、verification.json。真实请求/响应仍在data/retrieval_local/service_private/53613803b0a248819bf3d063ce41d5c8。
- 自然一次Revision，10模型/7检索/1纠正，最终无执行问题、必需阶段完整但业务review_required；重启相等无重发。官方资料/实际响应不入Git；PDF未重建，旧30题未重标。

## 2026-10-04 最新公开复现与并行轨迹修复

- 代码提交97e3523最终独立克隆455项通过；final-stdlib-tests.txt、final-locked-tests.txt、final-harness-demo.txt、final-http-demo.txt保存实际提交验证。普通push因github.com:443连接失败未成功，最新提交与待推送范围见verification.json，不能以旧origin/master冒充远端同步。

- [README](../README.md)：当前架构、标准库/锁定API测试、本机synthetic_fixture演示最短入口。
- [当前状态](current-status.md)：schema13真实基线与本轮无付费范围，BM25默认/Dense-RRF非默认/微调未实现；网络状态按日期记录。
- [公开复现](public-reproducibility-v1.md)：干净克隆、依赖、基线8错误、修复测试/跳过项、原Harness及HTTP演示证据。
- [并发轨迹](model-trace-attribution-v1.md)：稳定请求归属、共享预算、纠正/超时/取消与旧记录兼容。
- [实施接入点](implementation-roadmap.md)：逐主张证据、可选语义装配、支持判断微调数据与独立评测，均未在本轮实现。
- 本机材料：data/runtime_local/public-repro-v1/reading-notes.md、verification.json；baseline-*、candidate-*日志、dependency-install.txt、git-audit.json，隔离检出不复制原私有data/.env。
- 长期偏好见handoff最新节：用户授权检查提交后默认普通推送至核实origin和当前分支；旧不推送/网络失败记录保留历史含义。r1手册及PDF本轮不重建。

更新：2026-10-04。路径相对本文；data 下材料仅本机可用且被 Git 忽略。历史文档保留当时版本，不覆盖；其旧测试数、默认 schema、知识版本或“未实现”描述不代表当前状态。

## 本轮界面 v1 与真实 API 验证素材

| 入口 | 用途与实际边界 |
|---|---|
| [local-review-ui-v1.md](local-review-ui-v1.md) | 同源中文界面、令牌本机操作、字段/错误交互、修改职责、验证分层和已知问题 |
| `backend/static/index.html`、`style.css`、`app.js` | 静态界面、响应式布局、安全纯文本、内存令牌、单次POST、状态轮询/版本/证据/反馈 |
| `backend/api.py`、`store.py`、`service.py`、`assembly.py` | 静态路由/CSP与同源、受保护分页、实际反馈绑定和未完成原引用投影、当前版本完整性、资产哈希 |
| `tests/test_local_ui.py`、`tests/ui_client_checks.js` | 4项新增离线API测试；客户端DOM double验证未知POST/重复/409/文本安全，不当作真实浏览器 |
| [ui-v1-offline-final-tests.txt](../data/runtime_local/ui-v1-offline-final-tests.txt)、[ui-v1-client-checks.txt](../data/runtime_local/ui-v1-client-checks.txt) | 421项通过/57.127秒及客户端检查；零付费，保留最初420项阶段日志 |
| [ui-v1-demo-scenarios.json](../data/runtime_local/ui-v1-demo-scenarios.json) | 7条通过既有假组件服务生成的修订/部分失败/取消/执行失败/文本安全/中断场景 |
| [ui-v1-browser-checks.json](../data/runtime_local/ui-v1-browser-checks.json)、[截图目录](../data/runtime_local/ui-v1-screenshots/) | 实际内置浏览器两提交、排队/429、取消、恢复、证据、反馈、401、网络未知、文本安全；不含令牌/路径 |
| [ui-v1-delivery.json](../data/runtime_local/ui-v1-delivery.json) | 本轮文件SHA、验证摘要、14条演示/2条真实分别统计与归档完整性 |
| [冻结计划](../data/runtime_local/ui-v1-real-validation/plan-v1.json) | 两输入、原装配、schema12、知识/源码/模板哈希、每运行40上界/合计80硬界、停止条件；实际9次，无提额 |
| [真实问答](../data/runtime_local/ui-v1-real-validation/8f378eec606e4808b7319c6c8d4e274f.json)、[真实已有回答](../data/runtime_local/ui-v1-real-validation/c08a5ddcae4a46148a2a512100148731.json) | 浏览器POST经真实服务装配执行；6/3请求，均review_required，阶段完成、检查未全评估，均无Revision |
| [重启前结果/反馈](../data/runtime_local/ui-v1-real-validation/pre-restart-v1.json)、[重启对照](../data/runtime_local/ui-v1-real-validation/restart-verification-v1.json) | 两结果和最新反馈逐字段一致，无POST/无模型重发；用量与9个原始响应仍保留 |
| `tests/ui_real_validation.py`、`data/retrieval_local/service_private/{run_id}` | 授权真实入口预检/冻结与只读API采集；原消息、响应、格式失败、候选和快照由原组件归档，不复制全文 |

真实问答格式失败 `basis_indexes` 越界、一次纠正及原引用coverage告警见其run JSON和原始诊断；既有URL安全投影误隐藏官方HTTPS地址记为未解决，不因两运行完成改写为安全或语义认证。本轮最终手册仍未编写。

## 当前入口和实现说明

最终学习与面试手册要求见 [final-handbook-requirements.md](final-handbook-requirements.md)，目前未编写。下面的主题索引用于逐轮积累素材，不能作为已交付手册。

| 文档 | 地位与阅读用途 |
|---|---|
| [handoff.md](handoff.md) | 当前状态、装配、限制、验证与未提交工作 |
| [design-decisions.md](design-decisions.md) | 重要决策及代码/归档依据 |
| [local-review-service-v1.md](local-review-service-v1.md) | 当前应用服务/API、存储、令牌、安装、演示与反馈示例 |
| [fact-rereview-v3.md](fact-rereview-v3.md) | 最新真实事实阶段验证/schema12；不是新完整闭环 |
| [python-architecture.md](python-architecture.md) | 初始 Python 分层设计；具体实现以现有代码和服务装配为准 |
| [offline-harness.md](offline-harness.md) | 离线 Harness 与环境说明；旧测试数量为阶段记录 |
| [markdown-retrieval.md](markdown-retrieval.md) | Markdown/SQLite/BM25/Evidence 基础链路 |
| [pdf-retrieval.md](pdf-retrieval.md)、[pdf-retrieval-quality.md](pdf-retrieval-quality.md) | PDF 提取、页内切分、定位/邻接和解析风险 |
| [harness-retrieval.md](harness-retrieval.md) | Retriever 注入、冻结版本、预算和失败处理 |
| [generation-agent.md](generation-agent.md)、[deepseek-generation.md](deepseek-generation.md) | 生成/连接器基础说明；引用现使用 answer units/schema3，旧偏移协议非最新 |
| [evidence-verification.md](evidence-verification.md)、[power-domain-review.md](power-domain-review.md)、[bounded-revision.md](bounded-revision.md) | 各能力实现阶段说明；最新协议以 handoff/assembly 为准，领域规则仍为演示 |
| [semantic-retrieval.md](semantic-retrieval.md) | 已有可选 Dense/RRF；初始评测阶段的未标注状态已过时，不是默认服务配置 |
| [legacy-migration-principles.md](legacy-migration-principles.md) | 旧算法不得作为生产规范；其当时未实现能力声明不代表今天 |
| [知识来源 README](knowledge-sources/README.md)、[manifest.json](knowledge-sources/manifest.json) | 三份实际官方资料来源、哈希、版权/适用范围及获取失败记录 |
| [development-questions.json](knowledge-sources/development-questions.json) | 官方资料阅读开发问题，非专家标注验收集 |
| [deepseek.example.json](config/deepseek.example.json)、[.env.example](../.env.example) | 非敏感配置示例；不读取真实 .env |

## 历史协议修复与闭环准备

| 实际路径 | 状态 |
|---|---|
| [claim-extractor-diagnosis.md](claim-extractor-diagnosis.md)、[verification-contract-diagnosis.md](verification-contract-diagnosis.md) | 历史失败诊断，保持原失败状态 |
| [q1-review-boundaries.md](q1-review-boundaries.md) | 原引用、独立支持与输入覆盖边界 |
| [verification-output-v4.md](verification-output-v4.md)、[q2-v4-preflight.md](q2-v4-preflight.md)、[verification-output-v5.md](verification-output-v5.md)、[verification-output-v6.md](verification-output-v6.md) | 旧契约演化；不作为当前 schema12 请求模板 |
| [protocol-stability.md](protocol-stability.md) | 旧闭环执行稳定性修复与部分结果隔离 |
| [acceptance-preparation.md](acceptance-preparation.md)、[acceptance-candidates-v1.md](acceptance-candidates-v1.md) | 旧基线/候选验收设计；候选未经确认不称人工标准答案 |
| [evidence-delivery-trial.md](evidence-delivery-trial.md) | 六场景88响应交付对照；cross_page_next_first 未采用 |
| [review-reliability-v1.md](review-reliability-v1.md)、[review-reliability-v2.md](review-reliability-v2.md) | 历史真实性、单位、快照和模板失败，不因新代码改写为成功 |

## 本机归档：当前验证和关键失败

| 路径 | 含义 |
|---|---|
| [service-delivery-v1.json](../data/runtime_local/service-delivery-v1.json) | 服务v1初交付逐文件SHA、417测试、当时零付费、历史保护检查 |
| [http-demo-bab0e40a44814ec8925ab29baaf8f225.json](../data/runtime_local/http-demo-bab0e40a44814ec8925ab29baaf8f225.json)、[http-restart-verification-v1.json](../data/runtime_local/http-restart-verification-v1.json) | 实际 HTTP/重启演示，仅 synthetic_fixture |
| [fact-rereview-v3/full-report-v3.md](../data/retrieval_local/deepseek/fact-rereview-v3/full-report-v3.md) | 两场景与12数量组件逐条真实结果、语义疑点 |
| [plan-v3.json](../data/retrieval_local/deepseek/fact-rereview-v3/plan-v3.json)、[actual-failure-matrix-v3.json](../data/retrieval_local/deepseek/fact-rereview-v3/actual-failure-matrix-v3.json) | 冻结版本/哈希、实际结构错误与纠正 |
| [reliability-v2/reading-notes-v2.md](../data/retrieval_local/deepseek/reliability-v2/reading-notes-v2.md)、[full-report-v2.md](../data/retrieval_local/deepseek/reliability-v2/full-report-v2.md) | v2 实际失败阅读与逐阶段报告 |
| [official-trial-review.md](../data/retrieval_local/deepseek/official-trial-review.md) | 五问生成对照，引用可回查不等于支持 |
| [revision-summary-v1.md](../data/retrieval_local/deepseek/revision-summary-v1.md)、[protocol-failure-matrix-v1.md](../data/retrieval_local/deepseek/protocol-failure-matrix-v1.md) | 旧修订/重审实际契约失败 |
| [stability-minimal-v2.md](../data/retrieval_local/deepseek/stability-minimal-v2.md)、[stability-minimal-v3-rereview.md](../data/retrieval_local/deepseek/stability-minimal-v3-rereview.md) | 旧版本初审修订及重审；不能拼为最新服务协议完整成功 |

更多早期事实审核按实际文件名保存在 `data/retrieval_local/deepseek/evidence-review-*.json/.md`；原始响应在该目录的 `response-diagnostics/` 及各版本批次目录。服务未来归档在 `data/retrieval_local/service_private/{run_id}`；API不返回其本机绝对路径或整段原始响应。运行数据库和令牌为私有设施，不上传或打印。

## 检索与监督标注实验（已结束，不自动重跑）

| 路径 | 状态/结论 |
|---|---|
| [dataset-v1.json](../data/retrieval_local/semantic/dataset-v1.json)、[comparison-v2.md](../data/retrieval_local/semantic/comparison-v2.md) | 原30问题/三方法阶段比较；自然问题、关键词和家族要分开 |
| [盲审包 README](../data/retrieval_local/semantic/blind-review/README.md) | 盲审材料；mapping 与盲审正文分离，候选池有覆盖限制 |
| [supervised-v3-eval-v3/evaluation.md](../data/retrieval_local/semantic/annotations/supervised-v3-eval-v3/evaluation.md) | AI辅助、用户监督标注评测；不是独立专家全语料金标准 |
| [body-priority-v1/report.md](../data/retrieval_local/semantic/body-priority-v1/report.md)、[audit-supplement.md](../data/retrieval_local/semantic/body-priority-v1/audit-supplement.md) | 正文优先/编码核查历史实验；读取补充审计，不按标题推断收益 |
| [term-expansion-v1/development-v2/report.md](../data/retrieval_local/semantic/term-expansion-v1/development-v2/report.md) | 单变量术语扩展实验及一次有界补标准备 |
| [term-expansion-27-final-v1/report.md](../data/retrieval_local/semantic/annotations/term-expansion-27-final-v1/report.md) | 27补标合并、对称回算；BM25局部收益未改善最终完整依据，保留基线 |
| [reranker-v1/report-v2.md](../data/retrieval_local/semantic/reranker-v1/report-v2.md)、[truncation-review.json](../data/retrieval_local/semantic/reranker-v1/truncation-review.json) | 单模型固定池实验；局部改善/组合退步，不采用；关键已标退步不能归因截断 |
| [reranker-v1/pool-hash.json](../data/retrieval_local/semantic/reranker-v1/pool-hash.json)、[resource-record.json](../data/retrieval_local/semantic/reranker-v1/resource-record.json) | 候选/配置哈希、耗时/内存测量，不是事实支持分数 |

原 PDF：`data/knowledge_local/nerc-guideline.pdf`、`nerc-var-001-5.pdf`、`pnnl-35221.pdf`。AEMO未成功获取，不作为现有语料。原全文和复核派生包未明确允许公开再分发，留在忽略目录，不提交Git。

## 最终手册主题素材索引

代码路径相对项目根。以下入口均已核实存在；大型归档只索引，不复制。当前协议为真实服务装配的schema12及其配套版本，完整版本表见handoff；旧契约代码保留兼容，不意味着服务采用它们。

| 主题 | 实际代码阅读入口 | 说明/实验/归档与状态 |
|---|---|---|
| 目标、架构、边界、旧项目迁移 | `backend/assembly.py`、`harness/runtime.py`、`agents/contracts.py` | 当前handoff/design-decisions；python-architecture为初始设计；legacy-migration-principles为历史迁移原则 |
| 四Agent/Extractor/Harness完整流程 | `agents/generation.py`、`agents/evidence_verification.py`、`agents/power_domain_review.py`、`agents/revision.py`、`services/claim_extractor.py`、`harness/states.py`、`harness/policy.py` | 当前服务说明；旧bounded-revision/protocol-stability报告；真实闭环与最新事实阶段必须分别引用 |
| 入库、切分、存储、溯源 | `rag/markdown.py`、`rag/pdf.py`、`rag/pdf_chunks.py`、`rag/storage.py`、`rag/context.py`、`rag/contracts.py` | markdown/pdf-retrieval及pdf-retrieval-quality；官方来源manifest；原PDF仅本机data/knowledge_local |
| BM25/Dense/RRF与实验取舍 | `rag/bm25.py`、`rag/embedding.py`、`rag/semantic.py`、`rag/retriever.py`、`rag/query_terms.py`、`rag/reranker.py` | semantic-retrieval；body-priority、term-expansion-27-final、reranker-v1报告（上表）；服务当前只默认BM25，实验无模型事实审核含义 |
| 契约、引用、版本、快照 | `core/models.py`、`core/typed_evidence.py`、`core/validation.py`、`services/answer_units.py`、`services/answer_anchors.py`、`services/quote_candidates.py`、`services/evidence_scope.py` | generation/旧v4-v6说明属协议历史；当前独立模板 `agents/review_templates_v3.py` 和 `agents/verification_contract_v9_scoped.py` schema12 |
| 工具、预算、超时、取消、隔离 | `tools/contracts.py`、`tools/unit_conversion.py`、`tools/scalar_numbers.py`、`harness/contracts.py`、`harness/retrieval.py`、`model_adapter/runtime.py`、`services/review_isolation.py` | harness-retrieval/服务说明；SI工具v2、阶段预算、底层取消限制；工具不证明稳定/物理类别 |
| 修订与完整重审 | `agents/revision.py`、`agents/revision_contract_v2.py`、`harness/runtime.py`、`harness/policy.py` | 旧revision-summary-v1/stability-minimal系列真实归档；fact-rereview-v3只有事实阶段，不是最新全闭环 |
| API、持久化、人工反馈、未来界面 | `backend/api.py`、`backend/service.py`、`backend/store.py`、`backend/serialization.py`、`backend/local_access.py` | 当前local-review-service-v1；service-delivery/HTTP重启报告为synthetic_fixture真实HTTP，不是付费模型演示；界面本轮已实现，见local-review-ui-v1和本轮索引 |
| 模型连接与配置排错 | `model_adapter/contracts.py`、`model_adapter/deepseek.py`、`harness/deepseek_trial.py`、`backend/config.py`、`backend/__main__.py` | deepseek-generation/服务说明、requirements-api.lock.txt；只使用无密钥示例，真实.env不作为文档素材 |
| 真实失败、修复、未解决问题 | `services/review_fidelity.py`、`services/claim_obligations.py`、`services/quantity_checks.py`、`services/validation_diagnostics.py`、`services/response_diagnostics.py` | reliability-v1/v2、fact-rereview-v3报告及其实际failure-matrix；N10/N11/N12保留结果，不能用规则替代模型识别 |
| 测试、指标、标注、结论限制 | `tests/`、`evaluation/supervised_retrieval.py`、`evaluation/term_supervised_final.py`、`evaluation/reranker_report.py`、`evaluation/report_fact_rereview_v3.py` | 初交付417项见service-delivery；最新421项见本轮离线日志；监督标注eval-v3/27-final来源明确；12数量例是开发组件测试，非独立专家验收 |
| 面试代码阅读路径 | `backend/assembly.py → harness/runtime.py → agents/contracts.py → core/models.py`，再按RAG/依据/工具/API分支阅读 | 本表提供当前入口；最终需解释设计追问、失败与取舍，不提前编造最终面试回答 |
| 后续微调/采用条件 | 当前没有事实支持判断微调训练管线 | design-decisions及fact-rereview-v3语义漏检是需求依据；人工反馈和监督标签不能未经核实直接当训练金标准，具体方案待后续授权设计 |

初期学习手册参考：`C:\Users\37307\Desktop\PowerTrustAI_Project_Study_Handbook_20261003.pdf`，2026-10-04确认存在，284440字节。本轮未读正文、未复制到项目；是历史形式参考，不是当前有效版本的实现报告。

## 2026-10-04 新会话素材维护记录

本轮已读五份基线/交付规则文档，并只读核对 backend/assembly.py 的 BM25、OfflineHarness 和显式 schema12 装配。无新增实验、失败或测试结果；当前任务等待用户提供具体内容。最终中文手册仍未编写，既有主题素材索引继续保留，历史记录与默认检索不变。


## v0.1收尾素材（2026-10-04）

- [prototype-v0.1.md](prototype-v0.1.md)：统一运行、令牌/密钥区别、中文结果解释、版本/证据/反馈、错误与重启；明确完整验收未完成。
- [验收结论](../data/runtime_local/v0.1-acceptance/reading-notes.md)、[修订预检审阅](../data/runtime_local/v0.1-acceptance/revision-review.md)、[机器验证记录](../data/runtime_local/v0.1-acceptance/verification.json)：本轮修改、零新增模型调用、真实/演示分层、Git限制。
- [最终冻结预检](../data/runtime_local/v0.1-acceptance/frozen-plan-final.json)：构造输入、知识与源码配置哈希、14+C2预算证明缺口；未提交模型批次。
- [最终测试](../data/runtime_local/v0.1-acceptance/offline-tests-final.txt)、[客户端检查](../data/runtime_local/v0.1-acceptance/client-checks.txt)：427项离线通过及链接/恶意文本/重复POST等客户端检查。
- [重启对照](../data/runtime_local/v0.1-acceptance/restart-verification.json)：两旧真实结果和演示v2反馈一致，无重发；旧9次调用不计为新增验证。
- [中文摘要截图](../data/runtime_local/v0.1-acceptance/chinese-summary.jpg)、[来源截图](../data/runtime_local/v0.1-acceptance/source-links.jpg)、[演示修订截图](../data/runtime_local/v0.1-acceptance/demo-revision.jpg)：实际内置浏览器，无令牌。
- backend/presentation.py、serialization.py、static/app.js 与 tests/test_v01_presentation.py：确定性中文解释和结构化来源处理；最终手册的重要架构/失败素材，当前不编写手册。
- [源码快照](../data/runtime_local/v0.1-acceptance/source-snapshot-v0.1.zip)、[路径哈希清单](../data/runtime_local/v0.1-acceptance/source-snapshot-manifest.json)：本机文件恢复材料；Git身份缺失未提交，不冒充Git可回退基线。

### 用户撤销30上限后的真实修订素材

- [新授权冻结计划](../data/runtime_local/v0.1-acceptance/frozen-plan-authorized.json)：单一构造输入、独立预算、默认配置保持；早期停止记录不覆盖。
- [实际真实运行](../data/runtime_local/v0.1-acceptance/e1c6bc1336cd4c89acee8bd2795a0ebb.json)：浏览器唯一API POST；v1 contradicted→一次Revision→v2重提取/双审；8请求、最终review_required。
- [原响应和消息核验](../data/runtime_local/v0.1-acceptance/raw-archive-verification.json)：8份原响应SHA与消息路径；实际消息/响应留data/retrieval_local/service_private对应run，不进Git。
- [真实重启核验](../data/runtime_local/v0.1-acceptance/real-restart-verification.json)：具体v2 finding反馈与完整结果一致，8→8、无POST重发。
- [真实修订截图](../data/runtime_local/v0.1-acceptance/real-revision.jpg)、[反馈截图](../data/runtime_local/v0.1-acceptance/real-feedback.jpg)、[重启截图](../data/runtime_local/v0.1-acceptance/real-restart.jpg)、[最终摘要](../data/runtime_local/v0.1-acceptance/real-final-summary.jpg)：实际内置浏览器，无凭据。
- [批次后最终测试](../data/runtime_local/v0.1-acceptance/offline-tests-post-batch.txt)：428项通过，45.986秒；修复JSON诊断位置后离线验证，无新模型调用。
- [冻结真实源码](../data/runtime_local/v0.1-acceptance/frozen-real-runtime-source.zip)：保存已执行批次的manifest源码；最终源码另存快照，二者投影差异明确，不能混为同一版本。
- reading-notes-preauthorization.md、revision-review-preauthorization.md及早期冻结预检：真实保留预算停止与后续授权历史，当前结论以reading-notes.md/revision-review.md为准。

## GitHub新项目基线上传素材（2026-10-04）

用户指定新仓库 https://github.com/7556481/PowerTrustAI.git；仅D:/PowerTrustAI，旧独立项目不操作。检查基线明确清单、暂存/历史blob、远端引用和推送回查证据将保存在 data/runtime_local/github-baseline/，不含凭据。提交/推送不会改变最终中文学习与面试手册要求，不替代手册交付。

### 最新本地基线与手册交付

- 本地基线：master / `3d5e0cd842a1039731aafb209fb5444bd1905622`，218个文件；candidate-audit.json、staged-audit.json、history-audit.json证明明确路径和历史blob核对。旧段落的未提交/身份缺失为当时状态，最新提交覆盖其当前状态。
- [GitHub网络诊断与修复步骤](github-upload-troubleshooting.md)：只读连接重置、未到登录、未推送，代理凭据不输出；远端历史仍未知。
- [中文项目学习与面试手册源](PowerTrustAI-project-study-interview-handbook.md)：17章，实际代码、真实失败、指标分母与面试追问；README不替代。
- [图源](handbook-diagrams.md)、`tools/build_handbook_pdf.py`：可编辑Mermaid与PDF矢量图/分页/目录生成。文档工具不修改项目模型/服务环境。
- `output/pdf/PowerTrustAI_Project_Study_Interview_Handbook_v0.1.pdf`：31页最终交付，中文嵌入字体、目录书签、分页；全部页面实际渲染。
- `data/runtime_local/final-handbook/build.json`、`pdf-verification.json`、联系表与页面PNG：SHA/页数/55个代码路径/视觉检查。旧桌面PDF正文未读，自动审批拒绝记录见handoff。
- 本轮新增付费请求0，未重跑历史检索实验；现有428项最终测试证据不宣称本轮重新执行。Git基线之后的手册及交接资料仍未提交，精确清单见github-baseline/final-delivery.json。

### 2026-10-04 学习手册定向修订r1（当前阅读入口）

- [r1可编辑手册](PowerTrustAI-project-study-interview-handbook-r1.md)：六项定向纠正、BM25/E5/RRF与unknown算例、必要组合、5段真实短代码、面试追问。应用仍v0.1，文档r1。
- [r1修改清单](handbook-r1-changes.md)：逐项依据、实际职责、未修复限制与旧版保留。
- [r1图源](handbook-diagrams-r1.md)、tools/build_handbook_pdf_r1.py：控制/数据/observer关系，独立构建不覆盖旧文件。
- output/pdf/PowerTrustAI_Project_Study_Interview_Handbook_v0.1-r1.pdf：38页新PDF，18个目录书签，全部页面重新渲染复核；旧31页PDF保持不变。
- data/runtime_local/handbook-r1/original-hashes.json、code-excerpts.json、build.json、verification.json：旧SHA、源码行号/摘录SHA、当前HEAD、源码比对、教学算术、全页渲染和排版核验。
- 当前本地历史仍仅3d5e0cd/master，无基线后文档提交；128个应用源/资源未变。本轮API/模型/历史实验/网络查询/提交/推送均0。前轮网络重置为2026-10-04记录，不作永久现状。旧索引的“当前手册31页”以本节r1入口接续。

### 2026-10-04 手册r1独立本地文档提交

按后续授权提交15个明确文档交付路径，包含旧版与r1源/PDF/图源/构建器、修改清单及相关说明；应用代码不变，不推送。data/runtime_local/handbook-r1/document-commit.json记录实际提交哈希、父提交、逐文件SHA与最终工作区状态。前节无文档提交为修订完成时的历史状态；引用工作量修复尚未开始，本轮不扩写手册、不调用API。

### 2026-10-04 引用工作量边界v1

- [诊断、配置与复现](citation-review-workload-v1.md)：schema13/v9.5稳定有界分组、项级作用域、调用结构、API薄接线与容量失败。
- data/runtime_local/citation-review-workload-v1/reading-notes.md、verification.json：最终离线、真实范围、冻结/最终源码SHA与本地提交；全部私有，不进Git。
- frozen-plan.json、frozen-runtime-source.zip、api-result.json、api-trace.json、real-summary.json、raw-archive-verification.json、evidence-roundtrip.json、restart-verification.json：唯一真实2引用/1组/3调用；执行未完整的真实失败保留，修后未重跑。
- offline-tests*.txt、targeted*.txt、api-debug.txt：早期失败、schema13输入接线与容量范围修复、最终回归；不以测试数量代替语义正确。
- 用户手动推送后fetch成功，origin/master核实526bdee；本轮新提交仅本地，不覆盖历史网络记录。手册r1 Markdown只补状态，不重生成PDF。


### 2026-10-04 schema13最终接线回归

- citation-review-workload-v1.md最新小节：fb235746真实初审→自然一次Revision→重提取/双审；三审核阶段完成，业务未全部可评估。
- data/runtime_local/citation-review-workload-v1/schema13-final/reading-notes-final.md、verification-final.json：新run b4ede2ab、10请求/1纠正、逐目的请求/消息容量/每项绑定范围、用量、Git文档提交。
- 同目录frozen-plan.json、api-result.json、api-trace.json、evidence-roundtrip.json、restart-verification.json：原样输入与固定知识，旧31459a原档SHA不变，新旧独立库存在，重启相等无新增调用；实际消息/响应留service_private对应run并核对SHA。
- 仅HTTP接线验证，无浏览器检查或PDF重生成；上一批真实失败保持原结果，最新回归独立解释。

- [日常收尾验收v1](final-acceptance-v1.md)：最新实现、未通过的真实验收、一次修订门控、固定部分库与统一入口。

## 最新收尾

- [英文身份与忠实性收尾 v1](identity-fidelity-v1.md)：稳定内部身份、唯一续建、实际0Revision与首版未验收能力。

## 正式学习站与审核共同诊断

- [学习站Markdown首页](learning/index.md)，静态入口learning/site/index.html；20章节源在learning/chapters，待补questions-for-chatgpt，源码核对source-check、documentation-verification。tools/learning_site.py和start-learning.cmd负责纯本地构建/阅读。
- [本轮诊断与未通过验收](audit-stability-learning-v1.md)：47实际诊断、compact14未验收、固定12题0完成及停止遗漏，私有learning-audit-v1保留全部原结果/冻结/审阅包。日常恢复13；无新训练/排名/Agent。

- [集成与学习站定向修订v2](integration-learning-v2.md)：真实接线/烟测失败、20章修订和浏览器缺口。
- [逐章核对](learning/revision-v2-checklist.md)，[待ChatGPT补充](learning/questions-for-chatgpt.md)。

- [schema13/14对照与公开收尾](schema-choice-v1.md)：逐项分母、实际Revision、准备失败、日常13及CI/浏览器限制。
- [公开Portfolio](../portfolio/README.md)，[旧README完整工程日志](engineering-readme-history.md)，[旧状态完整工程日志](engineering-status-history.md)。

- [共同作者v1定向补充与事实核对](learning/coauthor-v1-changes.md)：16章合并、最新局部Revision/原PF限制、工具/语义/FTS边界及个人待确认。

- [最后学习站勘误](learning/final-errata-v1.md)：6项范围/时效纠正，保留布局与历史。
- [本人最终验收清单与3题](owner-acceptance-v1.md)：当前日常配置、已有证据和待试用分开，无自动模型提交。

- [核心审核修复v1与一次4例未通过项](core-audit-fix-v1.md)：历史根因、原领域有源安全判断、主体补检边界、真实危险识别与普通阻断。

- [普通问答／纠错共同链路v2](ordinary-chain-v2.md)：前置主体交付、忠实提取、显式长度、修复空值、一次真实修订及未完成项，库续建分列。

## 2026-10-08 完整FTS库日常接入

[完整库接入v1](full-corpus-adoption-v1.md)：完整manifest/成功记录及新进程字节SHA核对；8765显式切完整kc-c25c9521…，旧prefix及全部历史不改写。每次新进程约44–52秒SHA，发布字节一致后复用完整性检查，不重扫SQL；同进程封印缓存/逐命中严格回查保持。一次电动机问答5调用全阶段完成但因现有工程输入适用性待补充，不回退库、不修协议、不重跑。749离线/81历史重启哈希/API与新旧Evidence/实际浏览器通过，私有统一包在full-corpus-adoption-v1；日常运行，独立8771已停止。长期中文学习站要求保留，本轮仅更新规模、启动检查与限制，未扩写整站。

## 2026-10-08 首版审核收尾v1

[审核收尾](audit-closeout-v1.md)：代码bd8e803；schema13+source-support-v6/program局部选择/输出v9.12，Domainv3.4同次analysis_scope实际范围；缺goal不默认，conceptual不能豁免工程承诺。旧c47/v5错误及baf输入覆盖未评估原样。4冻结题4/4阶段完整，概念pass/工程复核/数值不足/危险high-reject；16请求259734token，0纠正/0Revision，无新增批次。773离线/浏览器/全表重启哈希和Evidence/反馈通过，日常完整库与原配置不变、8765仍运行。限定个人最终试用可开始；工程长回答/语义复核未达简洁路由目标、旧输入快照缺口及模型局限待试用认可，不能说已接受/全面稳定。私有统一审阅包audit-closeout-v1；学习站仅同步相关行为/源码，不重写布局、20章/60题/旧手册保留。


## 2026-10-08 本人试用与性能核对（最新）

接续4887c375，实现0f0553e。三题唯一ID只读：熔断器346.649秒/泛化未通过；异步机250.605秒/一次实质修订及完整重审、限定通过；容量225.400秒/不猜容量、待补充。检索累计均约204–208秒，未发现每任务重复全SHA，重复FTS排名校验是真实瓶颈。仅移除刚完成同请求的重复排名，seal/全文区间/hash回查与范围仍严格。四条同查询排名正文身份一致、验证约7–12ms；rank SQL替代无优势未采用。

唯一新主题75字、API12.942秒可见/48.501秒完成、5请求87900token/完整pass，不能称同题端到端A/B或普遍性能。通用性能量值适用提示另版v9/v9.18，原熔断器不重跑/旧pass不改，语义对应复验仍缺，内容错误放行风险不能宣布解除。796完整回归＋之后4项相关检查；实际浏览器/自动连接/回查和全表重启不变。完整库、schema13/flash/product1.5/BM25aggregate/NLIoff保持，8765运行。见[报告](performance-closeout-v1.md)，私有审阅包performance-closeout-v1。停止追加，速度与剩余内容风险等待共同确认。

- [事实审核内部流程候选启动草案（未实施）](fact-internal-flow-candidate-v1.md)：初步职责、源码问题与未完成项；无验证成绩。

## 2026-10-29 selective MATCH v1：固定验证失败，候选关闭

唯一候选实现308a4b8f010d6b9fbeb6c031d2258f9b89ee5eea。24 DF/6消融及12查询×两路×三轮72组完成；执行753.581秒、封印206.044秒另列，0模型。Q1/Q2中位27.244→26.961、20.405→18.965秒，仅1.0%/7.1%，未达50%且5秒；Q3/Q6/Q11/Q12重复回退。性能门槛失败，不建议进入回答验证，未部署、未烟测、不补跑。质量门槛未取得完整逐目标人工通过证据，不得称召回无损。Q11候选引入气候模型/材料学等无关正文，虚构现场容量仍未知；Q9旧参考快照成员边界和所有启动失败保留。当前生产schema13/baseline、topic_v4_subject_v1不变。

报告：[选择性MATCH验收](evaluation/selective-match-retrieval-v1/report.md)。原文和完整输出留忽略data。学习站同步性能失败边界，下一后端原型须独立授权、公平同子集验证，本轮没有迁移/重建。原未提交研究材料保留。

## 默认分支独立发布记录（整合时保留历史）

README重写并迁出本分支旧全文，新增合成UI截图；新版业务代码位于codex/user-ui-readme-final-delivery-v6，未合并实验/维护代码。必要CI修复：匹配图依赖、完整Git历史、忽略目录测试前提、逐方法私有归档缺失标注，公开断言不变。已读取09c6b987/99b93497失败日志，红叉不等于push失败。模型0；[完整跨分支交付报告](https://github.com/7556481/PowerTrustAI/blob/codex/user-ui-readme-final-delivery-v6/docs/maintenance/user-ui-readme-final-delivery-v6.md)，最终CI看本提交Actions。以后维护记录进交接/报告，不堆README。
