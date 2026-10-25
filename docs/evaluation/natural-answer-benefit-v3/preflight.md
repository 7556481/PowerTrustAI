# 自然答案改善v3：批前核查

2026-10-26。业务冻结基线73c25ca0af9ba9fd5143527c6341aae52170fffd中的literal_v1＋source_actions_v2。只新增评测入口、参考冻结及离线验证；shared.batch增加默认关闭的independent_audit_budget选项，显式独立生成/审核预算并使用真实snapshot知识身份。未修改Factory、Harness、Store、提示、模型参数、解析门禁、来源资格、政策或检索排序。本轮专项数量/耗时见verification.json，复用上轮1305全套通过348.209秒，不冒称本轮重跑全套。

## 事前材料与实际路径

[8新题/4旧稿参考](materials-reference.json)在任何新预测前固定。四家族各direct＋linked，问题不诱错、不暗示漏限定；required/critical仅作离线评价，参考源全文留data。TaskRequest只取问题与统一概念性上下文，没有答案范文或评分字段。资料家族已见，称开发评估而非独立保留集。

顺序N1G→N1审核，依次到N8，再H1—H4，共20槽。N生成使用生产默认RAG/Generation，审核固定该次实际初稿/Evidence/引用和生成快照。审核Factory使用现有fixed_evidence_only避免二次打开大库或补检索，初次提取/事实/领域全是真实新调用；不继承上一轮回放适配器。生成和审核拆分是同稿评测接缝，不能说成在线一体检索性能验收。

H恢复原G1—G4及B1—B4 input.json，交叉核对原DB/summary、完整初稿/引用、Evidence和snapshot。证据数7/7/6/6；snapshot均generation-full-input-v2，原知识版本kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e。原生成bindings的index_core_hit/index_adjacent_context及retrieval_id由snapshot保留；普通固定Evidence审核的当前bindings为user_reference，两者不混称。只恢复生成产物，旧提取/审核/政策一概不回放，旧生成model_records清空且历史费用单列背景。H4完整来源可恢复，没有替换旧稿。

## 预算与停止

生成每槽2新请求，审核每链24，总304；各槽800秒，全批首次发送起7200秒，Flash/非思考/输出8000；业务修订一次，原格式纠正规则不变。独立审核预算不扣新G或历史G次数/时间，H采用原snapshot知识身份。全局独占发送账本不按槽重置，源代码未提交或运行目录已存在即拒绝。动态消息发送前保存真实哈希，不预造。

普通最终模型非法/语义失败/无修改/明确槽额度耗尽封存继续；生成失败则对应审核未执行但N分母保留8。共享程序、身份、库不可用、存储、认证、余额、网络、服务、超时或受理未知停止全批，不补跑/续跑/第二批。正常检索空结果按证据不足记录，不等同共享崩溃。批前普通离线未加载根.env、未发项目请求；只有唯一run入口调用已有配置加载器。

## 独立只读审阅

子Agent只读核查H四份原始身份、快照、bindings、计费及接线，并审阅八题无诱错/参考泄漏，未发现确定阻断。建议显式冻结H旧requirements，已纳入materials-reference；没有更改旧参考。独立文本评价在批后尽量提供隐藏先后/系统处置的成对正文，记录实际遮蔽程度，最后才对照系统发现；AI辅助、用户监督，非专家金标准，无在线裁判。

本轮不生产采用、不扩学习站、不加练习、不自动后续实验。保留全部N8/H4分母，先评实际Evidence支持，再评冻结来源下正确与覆盖；关键误改/新增错误/删失不能用改对数抵消。收敛条件严格沿任务文件。
