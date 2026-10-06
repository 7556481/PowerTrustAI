# 审核共同根因与中文学习站 v1

接续6108030，先完成20章学习站，再诊断用户run4df8007cf39f4f1e8082c17b92193f14并实现紧凑协议原型。**审核真实验收失败，不能上线schema14。** 日常已恢复schema13，原模型契约与语义不稳定仍在；没有修复后自动重跑。

## 实际共同诊断

原run是变压器kVA/kW概念题。初次响应8,862字符，JSON在7526处缺合法分隔；纠正后8,859字符，8个source_kind输出explanation，这是authority_scope的合法值而非source_kind值。原响应和失败状态保持。进一步离线精确投影还发现“100kVA对应100kW只在功率因数1时”选择calculation basis，但该冻结技术对象只允许正文，未猜测替换或把旧响应改合法。

实际归档47个带validation_error的响应，来自多轮且含纠正，不能当47独立题或整体失败率。按每响应去重的约束出现次数：精确来源条件8、authority_scope枚举5、非法JSON4、局部basis IDs3、提取异议与支持冲突3、分类目标一致性3、答案字符约束3、计算输入绑定2。完整逐文件SHA和校验字段在私有failure-history。source_kind新失败在一个响应中影响多个组件；根诊断与子错误不重复数成独立请求。

| 层次 | 已核实原因 | 处理边界 |
|---|---|---|
| 程序接线/投影 | 独立模板继承联合根、Domain输入包装遗漏、字段路径过度隐藏、本轮schema14包装遗漏 | 修程序，但本轮批次后不继续修重跑 |
| 输出协议复杂度 | parent/组件结论、bases/indexes/quote_ids、来源类型与authority_scope、条件和fidelity派生重复 | 程序管理身份/定位/类型/派生，模型输出减少 |
| 模型语义错误 | 思考题当支持、删必要条件、反向因果、原引用误判、证据不支持当提取异议 | 不能靠放宽parser或合法JSON宣称解决 |
| 执行控制 | 本轮客户端只识别若干网络/配置码，遗漏共享EXECUTION_FAILURE | 已记录停止条件未及时实施，未自动改执行器再跑 |

## schema14紧凑原型

agents/verification_contract_v14.py复用候选scope、typed parser、WireIsolation、CitationWorkload和structured_request，不新增Agent/Harness。模型root只含judgments，每目标8字段：target_id、status、basis_ids、reason、conditions、objection、repair、requires_authoritative_source。身份、版本、区间、类型、父结论和basis索引由程序绑定/聚合，不让模型重复source_kind/authority_scope枚举。

条件选当前已选正文basis，required/preserved为布尔或真正未知null，answer_quote必须在实际答案正文；程序绑定全文/区间/版本。objection=null显式表示模型比较答案与目标后判断忠实；真实异议合法保留并派生复核。原始支持先用共同typed校验，再计算更保守有效状态。未知ID、错类型、跨scope、缺项、非法字段拒绝，合法peer保留。来源未核实不能独自批准规范/设定/保证；没有减弱正文/条件/因果义务。

旧schema13按旧契约和归档解释。内部共同对象保持类型结构，新增compact marker保存原始与有效判断，修复建议仍绑定当前原文且需全重审。公开直接组件回归通过，不代表实际Harness接线成功。

## 固定12题：未达到最低目标

运行前冻结输入、预期、代码SHA、知识/配置，预期没有送模型。Q01取实际新用户问题，其他是普通构造开发问题，错误回答/缺参数明确synthetic_fixture。六概念题有实际预检命中；全批不换题、不改代码，单题未重发。

真实Harness门控仍只在schema9–13时构造ReliabilityVerificationInput，schema14得到基础EvidenceVerificationInput，缺tool_results。Fact在发模型前失败。客户端误将EXECUTION_FAILURE看成单题问题，12题已完成后才人工识别共享缺陷，停止操作没有再发新任务。**这是本轮实现和执行器的遗漏，不归咎模型。** 后续未修Harness或重新提交；仅恢复日常默认13，防未验收原型成为默认。

| 项目 | 实际 |
|---|---|
| 完整执行 | 0/12，目标至少11/12，未达 |
| 业务通过/拒绝 | 0/0；12执行未完成，不算成功拒绝 |
| 已确认错误放行 | 0，但源于失败阻断，不能推断语义可靠 |
| Fact模型请求/初次结构成功率 | 0 / 无分母，不是100% |
| 模型请求 | Generation8、Extractor12、Domain12，共32 |
| 已记录token | 304,657 |
| 每题端到端 | 5.80–15.09秒，中位12.49秒；累计131.31秒 |
| Revision/新版本/完整重审 | 0 / 0 / 0，不伪造after |

逐题问题、答案、理由、阶段、调用和AI初评在私有batch-evaluation。Q02/Q04/Q06超180字；Q06“正弦稳态且已有谐波”等条件表达有疑点；Q05附未要求追问；工程回答仍有额外理论。事实与原引用均未完成，不能把文字初评当准确率。评价使用AI辅助、用户监督流程，逐题初评待所有者确认，非专家标准。

新增known-gap回归用实际Harness离线路线复现字段遗漏并断言失败阻断，明确是已知失败复现而非schema14验收。批次前689测试通过的证据保留；最终离线数量以verification-final为准，不以数量宣布产品稳定。

## 学习站

docs/learning/chapters有18个主题章和术语/工作坊两附录，正文Markdown唯一维护。公式手算、源码输入输出/异常、监督与训练、失败及边界均有实质内容；旧30/38页PDF仅参考且保持原文件。首页、目录、搜索、章节导航、代码高亮及本地启动已实际浏览器检查。

双击start-learning.cmd，或项目Python -m tools.learning_site serve --open --port 8770；也可直接打开docs/learning/site/index.html。构建用 -m tools.learning_site build，只依赖标准库。学习静态服务不读模型配置、令牌或运行DB，不中断8765和唯一语料写者。待补清单在questions-for-chatgpt.md，已有内容不等待补充。详细数字及代码核对见documentation-verification/source-check。

## 交付与下一步边界

本轮停止新增开发与模型调用，交所有者及ChatGPT审阅。schema14缺实际输入包装和共享停止条件，不能正式启用；原schema13仍可能发生契约失败。下一轮需明确授权后先贯通真实Harness离线输出，再决定新固定批次，不沿本轮题目刷成功。

语料原唯一写者继续，无新增下载/训练/Agent/排名实验，不自动切换日常快照。完整库进度是带时点记录，不冒称已完整发布。统一私有ZIP无凭据、完整数据库、官方全文、原始全文库或权重。
