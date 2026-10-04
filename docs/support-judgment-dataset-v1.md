# 证据支持判断数据集与未微调基线 v1

记录日期：2026-10-04；接续已推送 `8adc7cb`。这是可运行的私有数据准备与评测入口，未训练模型、未替换生产审核器。BM25 默认、schema13、检索参数、原引用分组、支持要求及最终政策均不变，PDF 未重建。

## 任务与标签

任务版本 `support-judgment-task-v1`：判断**当前核验对象与实际交付依据**的关系，四类为 `supported`、`contradicted`、`insufficient_evidence`、`not_assessable`。支持需覆盖原对象、立场和必要限定；矛盾须有实际相冲突的依据；缺证据不等于事实错误或全语料不存在依据；无法评估与缺必需工程前提、对象不适用分开说明。没有仿真、输入错误和 JSON/ID 失败不能自动标事实矛盾。

每项保存原主张与 component proposition、立场、限定、依据目标、回答片段、完整交付 quote、SHA256、来源版本、定位及适用范围。工具结果、输入快照、回答文本明确使用不同依据类型。原引用任务仅接受原绑定引用，不能借用独立检索或工具结果。程序所掌握的输入/元数据、标量计算、工程前提与正文事实、原引用任务分别标注，不能混称同一事实支持能力。

提取忠实性保存为独立 observation，不能把模型转述后的新命题当原命题。原模型状态/理由/选中依据、程序 validation_error、人工反馈事件、AI 建议和最终监督标签分层保存。人工反馈的 confirm 也不直接转换四类标签；必须针对冻结 task 的原文、立场和作用域另行确认。反馈来源保留 `user` / `ai_assisted_user_supervised`，不写成专家金标准。

## 可运行入口

使用项目解释器，以下普通准备、复核、指标和导出命令不调用 API：

```powershell
# --model-id 是显式归档来源筛选；公开夹具使用 synthetic_fixture
& .\.venv\Scripts\python.exe -m evaluation.support_dataset build `
  --archives data/retrieval_local --model-id deepseek-flash `
  --output data/runtime_local/support-dataset-v1/new-preparation --per-topic 4 `
  --feedback-db data/runtime_local/runs.sqlite3
& .\.venv\Scripts\python.exe -m evaluation.support_dataset validate `
  --dataset data/runtime_local/support-dataset-v1/prepared-review-v2/dataset.json
# 可重复给 build 添加 --feedback-db、--result，以保存其他库反馈及修订谱系
# 用户编辑复核包 review-labels.json 后：
& .\.venv\Scripts\python.exe -m evaluation.support_dataset review `
  --dataset data/runtime_local/support-dataset-v1/prepared-review-v2/dataset.json `
  --reviews data/runtime_local/support-dataset-v1/my-reviewed-labels.json `
  --output data/runtime_local/support-dataset-v1/reviewed-dataset.json
& .\.venv\Scripts\python.exe -m evaluation.support_baseline metrics `
  --dataset data/runtime_local/support-dataset-v1/reviewed-dataset.json `
  --predictions data/runtime_local/support-dataset-v1/baseline-frozen-v1/predictions.json `
  --output data/runtime_local/support-dataset-v1/reviewed-metrics.json
& .\.venv\Scripts\python.exe -m evaluation.support_baseline training-export `
  --dataset data/runtime_local/support-dataset-v1/reviewed-dataset.json `
  --output data/runtime_local/support-dataset-v1/supervised-export
```

输出采用新路径、拒绝覆盖既有文件；不会自动追踪或上传私有材料。数据准备读取显式 archive root 内的冻结请求，核对原响应哈希，缺冻结请求不能猜测还原。反馈 SQLite 只读访问，不改历史。`--result` 关联原回答/修订谱系和 finding ID。公开测试用临时目录、明确 synthetic_fixture，无模型/私有 data 依赖。正常 Python 解释器运行这些校验命令，不使用关闭断言的 `-O`。

未微调基线是独立**评测任务格式**，复用现有 DeepSeek 连接器、ModelClient、共享调用记录、structured_request 与 ResponseDiagnostics；不会新增生产 Harness 或修改审核协议。

```powershell
# 仅明确需要新一轮基线时使用；本轮已运行并停止，不要重复本轮输出
& .\.venv\Scripts\python.exe -m evaluation.support_baseline run `
  --dataset <冻结数据集.json> --output <新的忽略目录> `
  --message-chars 240000 --max-items 8 --total-timeout 1800
```

`run` 才通过已有 ServiceConfig 环境入口加载配置，环境变量优先；仅归档 allowlist 设置、不保存凭据或请求头。提示 `support-judgment-baseline-v1`，模型输入严格只有 sample_id 与 task，不包含预期标签、AI 建议、旧模型理由、监督结果或受控变体标签。每批最多一次格式纠正；90 秒请求超时、1800 秒总超时、一次批次失败停止，保留有效同级预测和失败调用。请求上界由冻结分组数 × 2 推导，不另设任意付费批次上限。

24 万字符是此评测的可配置**完整消息容量**，不是生产原引用容量，也不推导事实判断成本。此次最大单项 86979 字符、最大初始批次 237393；每批最多 8 项控制输出 ID/理由容量，8000 output token。纠正完整消息上限 72 万字符，不截断原文；超容量项单独记录 excluded，无四类事实判决，不默默丢样本。

## 本轮实际样本与划分

463 份既有真实模型诊断均记录 deepseek-flash；274 份旧诊断未存冻结请求指针，明确跳过，不能凭响应补造输入。其余有冻结请求的生产独立/原引用审核形成 679 条原始组件候选，去重 425 条；30 条只有无效结构、不进入基线。其他类型诊断不冒充事实支持样本。实际服务运行、历史开发构造问题与本轮受控变体都是开发材料，不能称真实厂站数据。

按任务类型 × 第一议题每组最多 4 项选取，优先有效结构、反馈关联、显式 delivery 映射、最后稳定 task SHA，不按 supported 或错误标签选取：68 条归档样本 + 23 条受控变体，共 91 条。任务分布：正文事实 51、输入/元数据 23、工程前提 8、原引用 5、标量计算 4。数量、单位、类别、否定、范围扩展、条件删除的修改保留 before/after 与 parent ID，synthetic=true；未补造来源出版信息。不是为凑数量反复改写。

8 条人工反馈来源事件原样保存，3 处 observation 有关联。全部 91 条监督状态为 pending、label=null。每项已有建议、建议方法与待核对列表；旧模型缺分类时使用明确的 `target_type_triage_ai_suggestion_no_model_label` 初步待审建议，不能理解为模型已核验。原选中依据只能在当前 canonical task 范围内成为 suggestion_basis_ids；跨请求 quote ID 不自动借用或迁移。受控变化的建议也须先核实原命题真正被交付证据支持。

分组版本 `lineage-question-nearduplicate-union-v1` 使用同原回答、run/answer 谱系、原回答 SHA、问题家族、受控 parent、同任务类型 token Jaccard≥0.9 的并集；否定与数字保留。去重保留完整 proposition/限定/证据原文 SHA/元数据/依据类型/知识版本，忽略请求内临时 ID，但保存全部原来源和原输出，不能将旧输出的 ID 当当前输入 ID。

11 个关联家族预分 train 3 家族/16 项、validation 5/44、test 3/31；全家族同集合。划分为成员列表稳定哈希，追加数据需另冻版本，不能当作旧划分保持不变。**22 个相同证据片段跨集合共享**，完整列表在 source-split-report.json。因此这里只有同资料内开发预分，不能宣称无泄漏、跨文档泛化或独立测试；11 个关联家族也不等于 11 个独立验收问题。训练前须另建立有明确许可和监督标签、足够独立问题/文档的评测集。

交付状态另列：71 项历史输入没有逐组件 mapping（实际候选仍已冻结）、9 项 hits、6 项已有依据类型、5 项原绑定。无命中/检索失败/容量未交付与材料已交付但模型证据不足分别保留；结构失败或检索未完成不混入支持语义训练。此次没有需要截断或排除的容量项。

## 一次实际基线结果与限制

冻结 91 项、12 批，推导最多 24 次请求；实际**第一批失败后停止**：初始与一次纠正各返回 6 项，其中 1 个错 sample ID、3 个预期 ID 缺失。保留 5 项有效同级输出；86 项未完成，其中第一批 3 项缺失/无效、后续 83 项未执行。不将全体 91 项称为完成预测，未因失败更换输入或重跑。

实际 2 次请求、1 次纠正，6.715 秒，input 136926 / output 1415 / total 138341 token，cache hit 67968 / miss 68958；现有连接器价格快照估算 USD 0.011396604–0.022793208，非账单。调用级结构成功 0/2，有效部分样本 5/91，成功完整批次 0/12。错误 ID/漏项是结构契约失败，不作为数学结论争议、事实矛盾或语义正确率。

0 个监督确认标签，因此 semantic_metrics=null；只提供预测/未完成状态及待复核包。用户确认后可**离线**复用 task-hash 相同的预测，输出四分类混淆矩阵、各类 precision/recall/F1、四类 macro-F1、错误 supported 数量及非 supported 真值分母/全部 supported 预测分母，同时报告确认但无预测项。无分母类 P/R/F1 按 0 定义并明示；四分类标签不解释为概率置信度。无法从这 5 项推断通用准确率。

冻结版本与后续复核完善分开：baseline-frozen-v1 保留原输入、dataset SHA、提示/源码哈希和冻结源码；prepared-review-v2 只补原判断依据建议、监督依据校验与旧请求缺失原因，91 个 task 和 ID 不变，离线 metrics 已核对冻结任务相同。没有批次中改代码再继续调用。

## 复核包与下一轮输入

本机 `data/runtime_local/support-dataset-v1/prepared-review-v2/review-package/` 有 review.md、review-samples.json、review-labels.json；汇总 ZIP 为 `support-review-package-v1.zip`。不要默认发布这些官方提取文本或实际响应。用户在 labels 中确认 status/label、自己的 reviewer_id、note、实际 basis_ids；suggestion 字段只是辅助。ID、task SHA、依据作用域均检查，来源记录保留，不覆盖旧数据。

训练出口输出带 messages、group_id、split、supervision 和 origins 的 JSONL，**仅 confirmed 且结构/交付有效的样本**可进入；支持/矛盾必须有用户确认的作用域内依据。目前 pending 导出 0 行是正确行为，尚无可直接训练的监督集。下一轮先训练支持判断组件，与同任务/同分组的未微调预测比较，再单独评估生产 schema13 适配、提取忠实性及原引用/工程前提任务；不把外部评测提示直接替换生产审核器。补足独立问题家族和跨文档评测、确认发布/使用许可、冻结模型/训练参数与标签版本后才训练。本轮未下载训练模型或安装训练框架。

## 验证材料与页面修复

公开测试覆盖冻结原文/哈希、作用域错 ID/版本/知识、原引用不借工具、模型判断与反馈不升格标签、谱系/变体分组、重复来源、待审导出、格式纠正/超时停止/失败留档、无预期标签泄漏、离线指标与训练出口。全套结果及干净检出跳过项见本机 reading-notes.md / verification.json。

本轮浏览器核查发现已保存检索详情渲染函数在 IIFE 外，引用私有辅助函数导致 ReferenceError，被误显示为网络未知并中断后续渲染。只把 renderFactDelivery 移入原闭包，实际脚本的公开 DOM probe 验证配置/字面脚本文字及后续反馈渲染，无新任务 POST。不更改后台模型或审核。真实浏览器是否完成修复后验证，以本机 browser-verification.json 为准；不能用此 DOM probe 替代真实浏览器。
