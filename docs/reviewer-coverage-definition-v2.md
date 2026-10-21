# 开发侧覆盖定义v2：五项文本复核记录

## 后续：其余25槽文本复核完成

2026-10-21，本人逐槽阅读后同意其余25槽拟coverage：19 covered、5 missing、1 partially_covered。与此前四covered、一partial合并，**30槽文本参考共23 covered、5 missing、2 partially_covered**。此前五槽本轮未重新复核，沿用原确认；这是两轮确认合并，不是原完整性标签等价改名。

仅修正MIT-A01/R2与MIT-A03/R2的理由，删除不存在的“附加方向断言不抹去覆盖”说明；该说明只保留在MIT-A04/R2。MIT-A03/R1仍missing，不凭名称或具有阻值补出类别关系；SI-A02/R1仍partial，MIT-A06两槽仍missing。所有拟标签不变，原支持性参考、原标签及失败记录不改。

新确认汇总在忽略目录`data/evaluation_local/holdout-source-selection-v1/coverage-definition-v2-text-confirmed-r2/`，含coverage-reference.json、review-summary.md及manifest；旧草案/旧复核表保留。上述文件由程序写入并检查，**不记录为本人核验JSON或SHA**。本次只完成coverage文本意见，未重审支持性、未冻结执行、未授权付费。0API，未提交推送。下文“25槽尚未复核”保留为第一轮历史状态，以此段为当前状态。

2026-10-21。本人接受将“是否涉及所要求方面”与“结论有无证据支持”分开。**这是开发侧覆盖定义v2，不是原完整性标签的等价改名**；不转换或覆盖旧标签，不重算历史成绩，不变更通用提示、解析器或生产审核。

完整覆盖需表达所问方面及题卡要求保留的必要限定。明确反向结论可以覆盖该方面，其正确性另评；但遗漏或替换必要例外、范围时仍可为部分覆盖。不能因禁令更强就视为完整覆盖。

| 项目 | 本人文本复核意见 | 支持性参考 |
|---|---|---|
| MIT-A05/R2 | covered：明确回答温度与阻值关系，虽结论相反 | 原contradicted保留 |
| SI-A03/R2 | covered：明确说符号不用复数；扩大到名称另评 | 原not_supported保留 |
| SI-A04/R3 | partially_covered：涉及是否同时使用，但把同一表达式换成整篇文档，缺必要范围表达 | 原not_supported保留 |
| SI-A06/R2 | covered：明确回答复数方面，反向不等于遗漏 | 原contradicted保留 |
| SI-A06/R3 | covered：明确回答同表达式混用方面，反向不等于遗漏 | 原contradicted保留 |

题号使用原H-MIT-001/H-SI-001前缀。SI-A02省略句末例外可用于解释同类边界，但不因本次意见自动获得逐槽确认。

## 确认范围

只确认上表五项文本意见。其余25槽本人尚未逐槽核验；本人尚未读取JSON或核验SHA，**整个30槽文件未确认**。程序生成文件及哈希检查只属于助手的工程核对，不能记为本人验真，也不称专家金标准。

原草案及原始标签不覆盖；新记录位于忽略目录`data/evaluation_local/holdout-source-selection-v1/coverage-definition-v2-text-review-r1/coverage-reference.json`。新记录明确五槽user_text_review_confirmed_only、25槽pending_owner_slot_review，绑定原草案SHA，不改变支持性参考及失败记录。

当前没有执行冻结或付费调用授权，不准备或运行剩余8项。下一步仅整理其余25槽供逐项复核，不能用已有预测结果决定新参考；复合单元匹配和最终执行口径仍须另行确定。0API，未提交推送。
