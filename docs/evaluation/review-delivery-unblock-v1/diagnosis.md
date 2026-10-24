# 既有响应误拦与保护性目标核查

只读核查上一批41请求/实际消息，涵盖Flash28目标与Pro28目标。Pro只作历史辅助；本轮新增请求统一Flash。完整理由、条件/缺口/异议、原文位置与版本见[逐项JSON](diagnosis.json)；下表不把原始supported或旧参考当作充分证据。

分类：1真实遗漏/错挂/扩展；2理由与声明冲突；3重复答案定位未填写；4条件维度合同冲突；5不必要不确定/额外义务；6来源或参考争议未定；7不足误判矛盾。空项表示未定位该类问题，执行占位不评分。源文相对支持已复核，未发现本轮必须改旧参考的事项；不是工程真值认证。

|旧运行/接口/单元|实际表述|来源位置|参考 / raw / effective|根因分类|核查意见及处理|
|---|---|---|---|---|---|
|A1-flash/fact/0|动态无功资源在规定电压带宽内随电网电压变化自动实时连续调节输出，可维持电压设定点或按电压下垂模式运行。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A1-flash/fact/1|静态无功资源在额定电压下输出固定，其能力随电压平方变化，并可按系统条件手动或自动投切。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A1-flash/citation/0|动态无功资源在规定电压带宽内随电网电压变化自动实时连续调节输出，可维持电压设定点或按电压下垂模式运行。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A1-flash/citation/1|静态无功资源在额定电压下输出固定，其能力随电压平方变化，并可按系统条件手动或自动投切。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A1-pro/fact/0|动态无功资源在规定电压带宽内随电网电压变化自动实时连续调节输出，可维持电压设定点或按电压下垂模式运行。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / not_assessable|[3]|程序已有完整目标绑定；只移除重复定位，不补语义。|
|A1-pro/fact/1|静态无功资源在额定电压下输出固定，其能力随电压平方变化，并可按系统条件手动或自动投切。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / not_assessable|[3]|程序已有完整目标绑定；只移除重复定位，不补语义。|
|A1-pro/citation/0|动态无功资源在规定电压带宽内随电网电压变化自动实时连续调节输出，可维持电压设定点或按电压下垂模式运行。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / insufficient_evidence|[2]|保留真实冲突；不能因理由有据就抹掉缺口。|
|A1-pro/citation/1|静态无功资源在额定电压下输出固定，其能力随电压平方变化，并可按系统条件手动或自动投切。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / insufficient_evidence|[2]|保留真实冲突；不能因理由有据就抹掉缺口。|
|A2-pro/fact/0|资料将输配边界负荷显式建模为MW和Mvar，可放在母线高压侧，也可放在降压变压器或等效配电阻抗之后。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A2-pro/fact/1|资料指出负荷不应过度依赖大电力系统的无功支撑，反过来大电力系统也不应单纯依赖负荷的无功支撑。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A2-pro/citation/0|资料将输配边界负荷显式建模为MW和Mvar，可放在母线高压侧，也可放在降压变压器或等效配电阻抗之后。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A2-pro/citation/1|资料指出负荷不应过度依赖大电力系统的无功支撑，反过来大电力系统也不应单纯依赖负荷的无功支撑。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A2-flash/fact/0|资料将输配边界负荷显式建模为MW和Mvar，可放在母线高压侧，也可放在降压变压器或等效配电阻抗之后。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / 执行占位 / not_assessable|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A2-flash/fact/1|资料指出负荷不应过度依赖大电力系统的无功支撑，反过来大电力系统也不应单纯依赖负荷的无功支撑。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A2-flash/citation/0|资料将输配边界负荷显式建模为MW和Mvar，可放在母线高压侧，也可放在降压变压器或等效配电阻抗之后。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A2-flash/citation/1|资料指出负荷不应过度依赖大电力系统的无功支撑，反过来大电力系统也不应单纯依赖负荷的无功支撑。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A3-flash/fact/0|资料对单一N-1故障要求系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A3-flash/fact/1|资料明确要求所有选定N-2故障也必须在无操作员干预下立即满足相同限值。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|insufficient_evidence / contradicted / not_assessable|[1, 7]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A3-flash/citation/0|资料对单一N-1故障要求系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / 执行占位 / not_assessable|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A3-flash/citation/1|资料明确要求所有选定N-2故障也必须在无操作员干预下立即满足相同限值。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|insufficient_evidence / 执行占位 / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A3-pro/fact/0|资料对单一N-1故障要求系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / supported / not_assessable|[5]|额外不确定/义务未证实必要，保留模型局限。|
|A3-pro/fact/1|资料明确要求所有选定N-2故障也必须在无操作员干预下立即满足相同限值。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|insufficient_evidence / insufficient_evidence / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A3-pro/citation/0|资料对单一N-1故障要求系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A3-pro/citation/1|资料明确要求所有选定N-2故障也必须在无操作员干预下立即满足相同限值。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|insufficient_evidence / contradicted / contradicted|[1, 7]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-pro/fact/0|给定资料的无功传输表达式明确保留了线路电阻R和电容B。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|contradicted / contradicted / contradicted|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-pro/fact/1|资料明确声明该表达式适用于任意长度的所有输电线路。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|insufficient_evidence / contradicted / not_assessable|[1, 7]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-pro/citation/0|给定资料的无功传输表达式明确保留了线路电阻R和电容B。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|contradicted / contradicted / contradicted|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-pro/citation/1|资料明确声明该表达式适用于任意长度的所有输电线路。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|insufficient_evidence / contradicted / contradicted|[1, 7]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-flash/fact/0|给定资料的无功传输表达式明确保留了线路电阻R和电容B。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|contradicted / 执行占位 / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-flash/fact/1|资料明确声明该表达式适用于任意长度的所有输电线路。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|insufficient_evidence / 执行占位 / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-flash/citation/0|给定资料的无功传输表达式明确保留了线路电阻R和电容B。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|contradicted / 执行占位 / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A4-flash/citation/1|资料明确声明该表达式适用于任意长度的所有输电线路。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|insufficient_evidence / 执行占位 / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A5-flash/fact/0|资料要求N-1失去一个元件后，系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内，且N-1条件适用于稳态与稳定要求。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / supported / not_assessable|[3]|程序已有完整目标绑定；只移除重复定位，不补语义。|
|A5-flash/citation/0|资料要求N-1失去一个元件后，系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内，且N-1条件适用于稳态与稳定要求。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A5-pro/fact/0|资料要求N-1失去一个元件后，系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内，且N-1条件适用于稳态与稳定要求。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / supported / not_assessable|[3]|程序已有完整目标绑定；只移除重复定位，不补语义。|
|A5-pro/citation/0|资料要求N-1失去一个元件后，系统在扰动后立即、无操作员干预下保持在紧急热额定值和电压限值内，且N-1条件适用于稳态与稳定要求。|pdf_extracted_text:file_page=21;page_chars[292:1326);page_lines[8:19]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A6-pro/fact/0|在忽略线路电阻R和电容B的短输电线路模型中，资料把无功传输表示为两端电压、相角差与线路电抗相关的关系。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|supported / supported / not_assessable|[3]|程序已有完整目标绑定；只移除重复定位，不补语义。|
|A6-pro/citation/0|在忽略线路电阻R和电容B的短输电线路模型中，资料把无功传输表示为两端电压、相角差与线路电抗相关的关系。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|supported / supported / not_assessable|[5]|额外不确定/义务未证实必要，保留模型局限。|
|A6-flash/fact/0|在忽略线路电阻R和电容B的短输电线路模型中，资料把无功传输表示为两端电压、相角差与线路电抗相关的关系。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A6-flash/citation/0|在忽略线路电阻R和电容B的短输电线路模型中，资料把无功传输表示为两端电压、相角差与线路电抗相关的关系。|pdf_extracted_text:file_page=7;page_chars[1199:2398);page_lines[19:38]|supported / 执行占位 / not_assessable|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A7-flash/fact/0|资料中的动态无功资源可在规定电压带宽内随电网电压变化自动实时连续调节。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / not_assessable|[4]|none/preserved维度冲突，本轮不一并放宽。|
|A7-flash/fact/1|因此匿名厂站只要采用动态无功资源，就能保证所有故障后电压稳定。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|insufficient_evidence / contradicted / not_assessable|[1, 7]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A7-flash/citation/0|资料中的动态无功资源可在规定电压带宽内随电网电压变化自动实时连续调节。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / not_assessable|[4]|none/preserved维度冲突，本轮不一并放宽。|
|A7-flash/citation/1|因此匿名厂站只要采用动态无功资源，就能保证所有故障后电压稳定。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|insufficient_evidence / contradicted / not_assessable|[1, 7]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A7-pro/fact/0|资料中的动态无功资源可在规定电压带宽内随电网电压变化自动实时连续调节。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / not_assessable|[3]|程序已有完整目标绑定；只移除重复定位，不补语义。|
|A7-pro/fact/1|因此匿名厂站只要采用动态无功资源，就能保证所有故障后电压稳定。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|insufficient_evidence / insufficient_evidence / insufficient_evidence|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A7-pro/citation/0|资料中的动态无功资源可在规定电压带宽内随电网电压变化自动实时连续调节。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|supported / supported / not_assessable|[3]|程序已有完整目标绑定；只移除重复定位，不补语义。|
|A7-pro/citation/1|因此匿名厂站只要采用动态无功资源，就能保证所有故障后电压稳定。|pdf_extracted_text:file_page=8;page_chars[0:1200);page_lines[1:16]|insufficient_evidence / insufficient_evidence / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A8-pro/fact/0|输配边界负荷在资料中显式建模为MW与Mvar。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / supported|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A8-pro/fact/1|因此该匿名变压器的实际额定容量确定为100MVA。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|insufficient_evidence / insufficient_evidence / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A8-pro/citation/0|输配边界负荷在资料中显式建模为MW与Mvar。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / supported / insufficient_evidence|[2]|保留真实冲突；不能因理由有据就抹掉缺口。|
|A8-pro/citation/1|因此该匿名变压器的实际额定容量确定为100MVA。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|insufficient_evidence / insufficient_evidence / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A8-flash/fact/0|输配边界负荷在资料中显式建模为MW与Mvar。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / 执行占位 / not_assessable|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A8-flash/fact/1|因此该匿名变压器的实际额定容量确定为100MVA。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|insufficient_evidence / 执行占位 / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|
|A8-flash/citation/0|输配边界负荷在资料中显式建模为MW与Mvar。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|supported / 执行占位 / not_assessable|[]|原文支持；无此类误拦，或执行失败不能归因语义。|
|A8-flash/citation/1|因此该匿名变压器的实际额定容量确定为100MVA。|pdf_extracted_text:file_page=37;page_chars[0:1193);page_lines[1:21]|insufficient_evidence / 执行占位 / not_assessable|[1]|原文不支持该扩展/保证或直接冲突，保护门禁不动。|

## 唯一选择

Flash A5 fact明确复现：条件present/preserved、合法source_ids、inference preserved、无gap/objection，实际正文已含N-1/立即/无操作员干预/限值/稳态稳定；唯一新增投影原因是answer_ids为空。选择移除conditions.answer_ids，由程序绑定当前完整目标范围。现有来源与五项条件语义声明保留，源码另立simple_bound_v1；程序绑定不声称定位了语义条件。

比较：Flash A7的none/preserved冲突影响2个有据目标，但改变条件维度含义风险较大；Pro/Flash理由与gap冲突不能用raw supported覆盖；未知适用性涉及语义判断，缺少确定程序修复边界。本轮只处理已在Flash证实的重复定位，不因Pro11项误拦扩大合同。

旧响应不转换为候选模型成绩。新增替身只证明程序行为；付费前已有1268全套通过，真实收益以本轮固定材料和回答交付另报。
