# 首版收尾 v1：实际交付与未通过项

2026-10-06接续863e47c，初始工作区干净、远端一致。必要实现已完成，**首版真实验收尚未全部通过**；不以离线测试替代模型语义、真实修订或NLI推理验收。私有统一包位于data/runtime_local/first-release-v1。

## 产品改动

product-decision-v1.3不再把missing_information非空机械当阻断。既有领域Agent另版v3.2逐项记录required、scope_note、unrequested_extension、uncertain及任务范围理由；必需缺口仍待补充，不确定仍复核，无完整适用性审核不能通过。独立事实、引用、工程输入和执行检查继续优先。新增协议5复用原ReliabilityDomainInput；首轮漏接工具/交付分支的AttributeError保留，已修复并补真实Harness synthetic贯通回归。

一个有选中原文、实质修复建议且对象忠实的明确缺陷，可触发一次Revision，不要求其他缺口同时可修。其他无法评估、缺证据/工程输入不因此解决；执行失败仍不能修订，严重度及分类不确定不升级为通过。修订后原Harness完整重提取、双审核，原版本保留。旧v1.1/v1.2可显式使用，历史不重写。

support-relation-v4/schema13 v9.10允许忠实同义条件表达；来源与答案各自仍必须是对应作用域中的精确摘录。新增preserved/missing/uncertain及对应理由，不强制两段字面重合；不确定、因果主体/方向改变不能supported。模型仍可能漏列条件、伪造摘录或误判语义，这些字段不是程序真值证明。

生成language-v7紧扣问题，工程缺输入时简洁说明不能确定什么及最少缺口，不复制无关控制门限、延时或操作建议。中文默认完整300字符上限，明确用户上限优先；超长整份有限纠正，不截断。来源未知说明独立呈现在引用区域，正文仍保留技术限定。此次工程回答仍夹带原Evidence ID和资料说明，作为已知展示/生成限制保留。

## 可选本地NLI

页面“本地NLI第二判断”默认不勾选。服务端仅在已配置解释器、固定checkpoint/profile时提供可用入口；浏览器只能传布尔选择，不能提交路径。选择另版local-nli-task-selection-v1保存在运行配置。关闭不推理，默认不加载；首次选择加载并按服务生命周期复用。模型加载/推理失败隔离于原审核，加载失败状态保存，未配置的选择不能冒充可用。

复用LocalNLI、epoch1原权重、转换v2、正文适配器v2，保留4/23错误支持风险。不替代事实Agent、政策或Revision，不投票，不把logits称可信概率。aggregate缺逐组件交付时跳过；混合/共享锚点、未支持类型、超长等门禁不变。日常保持aggregate，不为NLI覆盖修改检索。诊断异步处理中可只读轮询，刷新/重启不补算。

服务端可在忽略的data/runtime_local/local-nli-config.json配置，环境变量仍优先；此文件不含API密钥：

```json
{"version":"local-nli-server-config-v1","python":"D:/PowerTrustAI/data/runtime_local/new-machine-restoration/training-env/Scripts/python.exe","checkpoint":"D:/PowerTrustAI/data/runtime_local/support-nli-expanded-v3/run-v1/best-checkpoint","profile":"D:/PowerTrustAI/data/runtime_local/local-nli-diagnostic-v1/model-profile.json"}
```

## 固定真实验收与停止

原三题各执行一次；受限服务首先出现WinError10013/TLS权限失败，停止并留记录，经工具审批宿主启动后执行相同三题。上述领域v5接线缺陷定向修复后，仅对相同三题各验证一次。最后一次短官方NLI任务复用此前per_claim/top1/无相邻片段的独立验证配置，非日常默认；结束正常恢复日常配置。

| 最后定向结果 | 字符/请求/秒 | 实际状态 |
|---|---|---|
| 并联电容概念 b35352c… | 245 / 6 / 46.160 | 事实契约失败，执行未完成 |
| 原功率因数错误 d055da… | 122 / 5 / 29.219 | 事实契约失败，未进入实际Revision |
| 缺型号/线路/测量设定 e16dc9… | 184 / 6 / 18.047 | 完整执行，待补充，未给无依据设置值 |
| NERC短正文/NLI f3a146… | 原133英文字符 / 5 / 21.215 | 事实审核执行未完成；3组件跳过，0推理完成/0模型推理失败，不能比较分歧 |

共8运行、36请求记录、528804已记录token；含1连接失败、usage未知。0业务Revision。模型仍出现不精确来源条件摘录、原文角色/义务不一致和其他契约失败，不改状态或删检查取得通过；不再提交任务。NLI官方头/epoch1正常加载（无缺失/额外/形状冲突权重），模型加载内部0.183秒，记录RSS约290MiB，观察峰值约339MiB；**没有本轮真实推理耗时或准确率结果**。

## 已验证与阻断

668完整离线回归通过。synthetic_fixture验证范围缺口分类、忠实条件改写/未知拒绝、部分缺陷一次修订及完整重审、剩余工程缺口、默认关闭/逐任务选择/故障隔离及不可提交模型路径。它们不是实际模型修订成功。

实际浏览器验证自动连接、默认开关/勾选清除、184字符中文回答、来源区域、NLI三条跳过及重启展示。9条新旧运行的结果/请求数/诊断ID及输入/记录哈希重启相同，证据回查严格复验；查询没有重发或补算。一键入口未改，普通浏览器双击启动沿用此前所有者确认，本轮重验同地址自动会话。

**真实剩余阻断**：正常概念和明确错误的事实契约不稳定，尚无本轮实际Revision＋完整重审成功；本轮NLI可用加载/选择/保存验证完成，但真实三类推理未完成，不能宣称日常覆盖已验收。

**已知限制**：模型语义/分类/条件识别仍可能错；行业语料出处未知不能单独认证规范、设定或保证；答案可能带长ID或多余资料说明；部分审核理由为英文；小样本AI辅助用户观察非专家金标准；无工程仿真、通用准确率或安全认证。

## 日常入口与后台库

双击D:\PowerTrustAI\start-powertrustai.cmd，统一http://127.0.0.1:8765自动连接；正常入口python -m backend --open。演示加--demo；真实提交会调用付费API。空闲停止：python -m backend --stop --port 8765。日常仍固定kc-5894…/published-prefix-v2（153088输入行、143053唯一正文、326565片段），不自动切换完整库。

原构建进程不存在且无退出日志结论，确认无写者后仅恢复原库断点。一个逻辑写者有Windows venv父/子进程，不等于两个构建；日志/已提交行持续增长、磁盘余量充足。全部73片已下载；70片可读14,336,177元数据行，3片原发布字节尾部损坏保留/排除。完整库未完成，未发布新完整快照。本轮修复未来发布的覆盖核算：有效分片完成＋已核验不可读排除的所有清单项均交代，明确exclusions/coverage_definition；全坏或未处理不能称完整。合成验证不可变发布、索引/原文回查，不冒称实际完整库已验证。

恢复/发布命令见industry-corpus-v1.md；已有写者时不得另起。完成后仍需完整去重/索引/原文回查和独立不可变发布验收；无自动切换日常库。最终进度/资源以私有verification-final.json时间点为准。

源码入口：harness/product_policy.py、runtime.py；agents/domain_contract_v3.py、generation.py；services/support_relation.py、bounded_repair.py；backend/service.py、config.py、api.py、static/app.js；rag/corpus_build.py。长期中文学习/面试手册仍采用Markdown＋本地学习站、PDF可选，保留失败/设计决策与实际版本；本轮只记录待补点，不训练/扩新资料/新Agent/排序实验/建设手册网站。
