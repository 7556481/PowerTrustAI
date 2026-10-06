# 首版审核接口修复 v2

2026-10-06接续30e48a8，初始工作区干净、远端一致。只修审核接口与普通答案ID泄漏；检索、固定kc-5894部分快照、Agent数量、NLI默认关闭/门禁、训练及知识资料不变。

## 具体失败与修复

first-release-v1归档有23处literal_source_condition_required和5处冻结立场/义务冲突的派生状态重复要求。旧响应、旧协议、旧失败不修改。

source-condition-carriers-v1复用实际作用域quote_id，由程序给出条件载体ID及精确全文、字符区间、来源版本、知识版本和回答绑定。当前载体粒度是完整既有quote，不是自动检测的最短语义条件片段；模型判必要性、保留关系和因果方向，候选不足/不确定保留。正文原文仍在QUOTE_CANDIDATES，不重复拼证据、不模糊找旧条件文字、不借其他引用。新support-relation-v5/schema13 v9.11仅选择condition_id，不自由复写source_condition/source_excerpt。答案条件允许忠实同义表达，但必须绑定实际答案正文；必要条件检查不删除。修复建议也选同一选中依据子集的载体，原文由程序解析，而非模型编造。

independent-review-projection-v2分开保存raw_support_status、原始fidelity/stance/obligation及分类异议；先严格解析原始依据、ID、组件覆盖和类型，再计算有效not_assessable/review_required或条件未满足的insufficient_evidence。程序派生父主张合取；有异议不能用于通过。未知ID、缺项、跨作用域和错误依据类型仍契约失败，不因异议放行。product-decision-v1.4与旧v1.1/v1.2/v1.3均保留；新状态由程序计算，不要求模型重复输出同一派生状态。

answer-body-no-internal-evidence-ids-v1阻止内部e-哈希/user-UUID进入普通正文。完整响应拒绝后仅使用已有一次格式纠正，要求完整重写、保留技术内容与限定，ID留在evidence_ids/引用区域；不截断、字符串删除或前端隐藏。生成language-v8、日常Revision另版clean-body profile；旧Revision入口可明确不启用新profile。旧回答原文保留。

## 离线重放与回归

4份真实失败响应：按原显式quote_id映射同作用域完整载体，旧必要性标unknown，不从失败自由文本猜最短条件，也不重新判断历史语义。3份新接口可保存为有效复核结果，1份仍因遗漏必需主张拒绝。不能把协议投影称旧模型答对或重新通过。所有原文件SHA留在私有重放清单。

674完整离线回归通过；公开synthetic_fixture验证载体ID/range/version、原始支持与合法异议分离及真实政策review_required、必要条件缺失的有效不足、非法ID/错误依据仍拒绝、ID泄漏拒绝且不改原句。既有一次修订/重提取/双审回归保持。它们不替代本轮真实Revision验收。

## 固定真实结果（没有重跑）

原正常概念、原功率因数旧错误各一次；因ID校验确实影响此前184字符工程回答，再冻结同工程问题补验证一次。16请求、250033 token，全部完整执行、0执行问题，无新增总请求帽；原有限纠正、最多一次Revision、超时/异常停止不变。

| 运行 | 字符 / 请求 / 秒 | 实际处置 |
|---|---|---|
| 7da125…正常概念 | 192 / 6 / 46.974 | 当前任务通过，保留正弦稳态/理想元件/有功及电压条件，实际引用教材67/68页及行业正文 |
| 664d2f…原功率因数错误 | 原122 / 5 / 25.700 | 完整执行、人工复核；错误因果被指出，但模型把支持不足与忠实性不确定相混，且未给可用选中原文修复建议，0实际Revision |
| f2f7df…工程补验证 | 239 / 5 / 39.820 | 完整执行、人工复核；无内部ID，仍有多余控制背景/来源声明及归类疑点，不作设置值或保证 |

功率因数原答案和三个版本仍各v1：没有实际修订后答案/重审版本，不能伪造修订前后或强改字段触发Revision。cosφ正弦条件必要性也有未知；模型可能漏报、误判条件或把证据不足当归一化不忠实。这些是剩余语义/修订能力限制，不再当作模型输出契约崩溃，也不能宣称已自然完成真实修订。

程序有效判断与原始模型支持说明在结果页分开解释，避免正面原始理由掩盖未知条件；这里只读投影，不回填旧结论。浏览器已检查新回答/引用、旧错误复核说明及版本；重启6条新旧记录、请求数和证据严格回查相同。原生一键入口未改，当前浏览器自动会话复用，不再手输令牌；查询不重发。NLI仍仅诊断，不作为本轮收尾阻断，没有推理/训练实验。

## 知识库实际状态

原唯一逻辑写者在完成中文部分后已退出。实际日志KeyError:_id；首个待处理english/high/rank_00934.parquet元数据确无_id列（text及质量指标列），不是推测网络/磁盘原因。已提交7,373,300行断点保留，无重复下载、第二写者或自动切换/发布。按本轮“只报告进度”范围，不重复启动同一必失败命令，不悄悄编造原记录ID；英文记录身份/格式兼容及恢复待另行审阅。日常仍固定已验证的部分快照；完整库未完成/未发布，索引最终验收待完成。

日常双击start-powertrustai.cmd或项目Python -m backend --open，统一8765；空闲停止 -m backend --stop --port 8765。当前服务运行，构建不运行。剩余首版项：真实错误自动Revision未获成功、条件/忠实性识别仍可能不稳、工程回答仍有多余背景；不以一题通过宣布通用可靠性。停止新增实验，等待所有者试用。

源码入口：services/condition_candidates.py、support_relation_v5.py、review_fidelity.py、answer_body.py；agents/verification_contract_v10_batched.py、generation.py、revision_contract_v2.py；harness/product_policy.py；backend/assembly.py、presentation.py。Markdown＋本地学习站/PDF可选长期手册要求保留，仅记录“ID绑定与语义判断分离、原始/有效状态、历史协议重放、修订未触发、ID泄漏与异构语料断点”待补，不新建学习站/长手册。
