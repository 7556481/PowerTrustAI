# schema13/14可靠性对照与公开收尾 v1

2026-10-07，接续fcb58e7，工作区初始干净、远端核对一致；不迁移、重训、换模型或排名实验。

## 具体故障与最小修复

上一634a22烟测的F2C0是answer_text假设，只能选A90。模型把技术正文S0B条件挂在它上面，纠正仍跨目标选正文ID；接线已修复，无tool_results缺失。新提示evidence-verification-v9.14-explicit-target-basis-scope保留输出schema14及全部字段，只增加程序生成的target basis_types、condition_basis_ids、repair_basis_ids；纠正提供该目标合法ID/已选合法正文ID，无模型状态建议或非法ID替换。条件与repair仍须属于当前已选正文，不截断、不放宽；原引用隔离和有效同级保留。

新增真实Factory→Harness→Agent→parser→Store/API合成回归覆盖两入口、计算、引用分组、异议、非法ID部分结果、一次实质Revision与完整双审、13兼容及共享停止。采集回调失败现返回已受理ID/有效部分，立即停止、不重发；这项边界是对照结束后定向离线修复，未混入对照模型结果。

## 固定主契约对照

8题同模型、日常kc-5894固定快照、同回答/主张/全部交付/工具输入，只改Fact契约。题目与预期调用前冻结，预期不进模型消息；原题开发主题和新变体明确，非独立专家集。主对照只有事实/原引用契约，不冒充完整服务或Revision。

|版本|初次契约完整（案例）|纠正后完整（案例）|实际请求|已保存token|Fact端到端累计秒|
|---|---|---|---|---|---|
|13|7/8|7/8|14|79677＋3请求未知|37.811|
|14|6/8|8/8|15|29798|23.840|

分母8是冻结案例；目标为8个Fact组件＋5个原引用检查，共13。schema14全部目标返回合法结果；schema13正常题2目标在有限纠正后仍未完整，其余11目标完整（语义not_assessable不等于执行失败）。案例初次完整要求其全部初始请求结构合法。单位案例工具在准备时以v1形状调用v2失败，仍是合法的失败工具输入；不能评价成功计算语义，语义有效分母最多7，不补跑或更改旧输入。

首题13已发3响应后，私人采集误把model_scope返回值当预算而抛AttributeError，共享停止；原响应已离线恢复，没有再发。用户随后授权仅继续未发项，15对照项原源码/配置/预期不变。最初3请求token原诊断不含usage、未成功保存，明确未知；不是模型失败/工具包装缺失，不估算补齐。完整服务采集又有提交前键错误和接受后回调错误，均保留；首任务从唯一运行库ID恢复，不重发。

正常14 raw supported但条件answer_quote空/ preserved=true，被保守降级；13在条件删除项判contradicted，选中来源仅给带条件论述、没有明确反例，这个反驳仍有疑点。其余多个任务语义未知/不足，不能以合法JSON称语义正确。7个可评价冻结案例未确认错误支持放行，缺项/未知不算正确。主要结果逐项见私有comparison.csv/json与原输出；预期来源AI辅助用户监督，不标专家标准。

**日常保留13**：14结构完成改善，但正常支持可靠性和重要语义退步尚未充分排除；13也不稳定，不能宣布稳定交付。不是按pass数量挑选。有限纠正/一次Revision/超时/异常停止不变，没有新付费总请求帽。

## 完整服务与Revision另列

- 正常：run f5ec1575155c4cce8eae6bfc20c9b05c，1版本/1轮，完整通过，5请求60330token；无Revision必要性。
- 局部错误：run f61a804c41054092a3b31d496c541c78，原2ω错误→新ω，保留线性时不变/正弦/暂态消失与同一概念，未删除子问题；自然1次Revision，2版本/2轮，重提取与双审/原引用均完整，9请求105075token，最终通过。原错误版保留。
- 工程项：冻结goal=engineering非法（实际允许conceptual/plant_assessment），HTTP422未受理，0模型请求，停止；不改输入刷结果。该项是准备缺陷，不能算产品缺输入判断完成。本轮完整服务2/3，受理后完成2/2；工程不足能力只能引用已有历史有效记录，本轮不伪称验收。

完整服务14请求165405token；主要Fact29请求，累计本轮43请求、已记录274880token＋最早3请求未知。阶段ModelCall component/answer_version、usage、duration_ms与API端到端保存；Fact-only时间不与完整流程混算，快速失败不称优化。Revision资格、自然触发、实质修改、重审完成与问题解决分开留档。本次只一个实质局部错误，不能称普遍修订成功。

正常停机/重启8772后2个结果、版本和5/9请求量HTTP哈希一致，GET没有重发。浏览器工具重试/重置后仍setup refresh helper_unknown_error，架构/状态/公式/代码/搜索/折叠/窄屏最终实际补验未完成；已有真实截图明确历史范围，不以脚本代替浏览器。

## 公开交付

README改为定位→架构→能力→真实历史demo/学习截图→技术→验证→启动→限制，一个当前状态。旧README/状态全文移至工程日志保留；私有批次不公开。Portfolio8条synthetic_fixture是工程验证入口，不是语义benchmark，无参考池不报Recall。

公开CI：public-offline.yml在无密钥/官方原文/训练权重环境装公开依赖，必需回归/演示/学习构建缺失失败；私有历史明确跳过。本机712离线全部通过；无私有克隆712项、27跳过，必需模块均安装。GitHub运行状态推送后单独回查，不能用本机结果冒充远端。

GitHub About建议：Local-first power knowledge QA and evidence-bound answer auditing prototype. Offline demo, reproducible contract checks, versioned RAG and Chinese learning site. Not engineering certification.
Topics建议：python, fastapi, rag, evidence-verification, electrical-engineering, sqlite, bm25, nli, human-in-the-loop, local-first。未发现可用gh/授权连接工具，提供所有者填写，不声称已改About。

## 语料与阅读入口

2026-10-07T09:34:20.034831+00:00断点12,371,999行。原停止原因未知、无终止错误日志；确认没有写者且OS锁可得后沿原断点唯一续建，未下载/清空。5条已提交正文哈希只读抽检通过。完整覆盖/去重/排除/全库索引与原文核验须等原wrapper完成后独立发布；当前尚未发布、不切日常。窗口中的两个Python父子是一个逻辑写者，不另起。

学习站20章Markdown源，start-learning.cmd/8770独立；第14章新增一页对象流并链接深读，08/16补协议作用域/对照/分母/耗时解释。旧手册完整保留，个人设计动机/面试贡献留给ChatGPT共同补充。最终已验收和仅离线项分别标明。

阻断/未验收：两版真实语义稳定性、工程项本轮无效准备、最终浏览器补验。已接受限制：小样本开发评价、AI辅助监督、NLI仅诊断、固定部分快照、未获得工程认证。停止自动追加修复/实验；背景唯一构建可继续。
