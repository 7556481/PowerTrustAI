# 真实服务可选语义检索 v1

2026-10-04，基于已推送0b7a071。服务复用原Harness、schema13、逐主张交付和原引用分组，新增服务器启动配置，未更换模型、切分、BM25或RRF参数、支持要求与政策。BM25/aggregate继续默认；下面对照不支持切换默认。

## 启动与配置

基础依赖使用requirements-api.lock.txt；只有Dense/Hybrid需要requirements-embedding.lock.txt。已有PDF知识索引的原文回查另需requirements-pdf.txt；本机环境已具备。已有模型与向量索引必须事先由管理员显式准备；普通启动、健康检查和提交不下载、不建索引。旧准备工具与模型许可见[语义检索历史说明](semantic-retrieval.md)。

```powershell
Set-Location D:\PowerTrustAI
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock.txt
# 仅语义模式需要；现有环境已安装时无需重复安装
& .\.venv\Scripts\python.exe -m pip install -r requirements-embedding.lock.txt
$env:POWERTRUST_RETRIEVAL_MODE='hybrid' # bm25 / dense / hybrid
$env:POWERTRUST_FACT_RETRIEVAL_STRATEGY='per_claim_v1' # 或aggregate
$env:POWERTRUST_EMBEDDING_MODEL_DIR='D:\PowerTrustAI\data\retrieval_local\semantic\e5-small'
$env:POWERTRUST_VECTOR_DB='D:\PowerTrustAI\data\retrieval_local\semantic\vectors.sqlite3'
& .\.venv\Scripts\python.exe -m backend --port 8765
```

页面http://127.0.0.1:8765/；停止用Ctrl+C。恢复默认可移除两个模式环境变量，或显式设bm25/aggregate。演示使用`-m backend --demo --port 8765`，不读根.env、不加载语义模型；运行配置标记actual mode为none、synthetic_fixture。访问令牌仅在页面内存输入，DeepSeek配置留服务端，普通请求不能指定任何模型/数据库路径。

index_db沿用现有固定知识索引，knowledge_version由POWERTRUST_KNOWLEDGE_VERSION选择；模型目录和向量库均为服务端配置。E5为multilingual-e5-small、固定revision614241f6…、384维FP32、CPU ONNX，完整profile来自现有编码器。启动核对模型文件SHA、profile、维度、知识快照、全文/索引表示指纹和向量集合；失败明确CONFIGURATION_UNAVAILABLE，绝不退回BM25。模型profile包含依赖版本与线程数，更改环境可能使已有索引不匹配，需要管理员另行显式准备，不自动修补。

## 生命周期、范围和开销

ComponentFactory持有一个服务生命周期的语义Retriever和编码器；每任务只借用，不重复加载模型。编码工作沿用单工作线程、无无界队列；ONNX内部沿用4线程配置。取消/超时停止等待，不保证底层立即终止，busy资源拒绝新请求。Bundle先drain，服务关闭等实际工作完成后关闭线程和编码器。BM25仍按原路径装配，不导入语义运行依赖。

validate_result仍重放完整检索，包括向量完整性、原文/定位/哈希、分数、排名和上下文链接；没有改成只比较ID。一次正常语义检索编码2次（检索＋重放）；跨版本缓存结果也要重放，复用查询不是零编码。MeteredEncoder计实际尝试与耗时，validation_replays单独统计；这些是服务生命周期诊断，不冒充重启后的历史计数。索引连接、向量加载和完整性检查仍重复，本轮只消除逐任务模型加载，没有做大规模性能改造。

查询缓存限定固定知识、模式/profile和查询设置；回答轮次的映射重新建立。每个组件保存当前answer_id/version、claim/component、检索ID、核心/邻接来源、实际交付、省略及allowed_quote_ids。相同Evidence可共享，但合并池不自动开放给全部组件。原引用只检查原绑定，独立检索不能补救它。空命中、检索失败/超时与容量省略继续分开，相关性分数不变成supported。运行manifest与页面详情展示保存的实际模式、事实策略、知识、profile和评分方法，历史运行不随当前配置改写。

## 固定小型对照

四组已有开发案例沿用相同回答、共享主张、冻结必要片段清单、知识版本k-182e01…385；全部per_claim_v1、top_k=3、邻接depth=1/6片段/2400字符/storage_order/允许跨页，每请求16000、累计160000字符。仅检索模式不同。不重新生成回答或补标；非清单候选仍保留实际位置，不能当负例或计算通用Hit/MRR。清单覆盖也不是语义准确率。

| 模式 | 必要核心命中/交付 | 四组检索/编码次数 | 独立进程冷初始化 | 单组暖流程 | 峰值工作集 |
|---|---|---|---|---|---|
| BM25 | 10/10，10/10 | 10 / 0 | 无编码器；约0秒 | 6.39–13.11秒 | 48.06 MiB |
| Dense | 4/10，4/10 | 10 / 20 | 4.92秒 | 6.81–14.18秒 | 1138.10 MiB |
| Hybrid | 7/10，9/10 | 10 / 20 | 4.57秒 | 6.57–13.64秒 | 1137.91 MiB |

冷初始化是新进程模型初始化，文件系统缓存未清空，包含模型哈希/加载与向量完整性预检；BM25数值不包含首次查询索引访问。暖流程包含全部查询、完整重放和Evidence/邻接回查，不是单次编码耗时。内存是每模式独立进程整个四案例的Windows峰值工作集；不是GPU显存。

| 案例 | BM25核心/上下文/交付字符 | Dense核心/上下文/交付字符 | Hybrid核心/上下文/交付字符 |
|---|---|---|---|
| 0 | 5776 / 3912 / 9688 | 5082 / 3621 / 8703 | 5497 / 3013 / 8510 |
| 1 | 4788 / 4653 / 9441 | 2621 / 3177 / 5798 | 3644 / 3014 / 6658 |
| 2 | 3804 / 3859 / 7663 | 3025 / 3802 / 6827 | 2415 / 4463 / 6878 |
| 3 | 7816 / 7429 / 15245 | 6288 / 5604 / 11892 | 6702 / 5335 / 12037 |

原引用与用户资料未混入此独立检索对照。核心/上下文按去重后实际交付来源计；某Evidence同时是核心与邻接时归核心。Hybrid案例0退步2/2→1/2；案例2一个必要片段通过上下文而非核心交付；案例3必要核心3/4、交付4/4。因此Hybrid并非必然优于BM25。

schema13输入投影字符（系统＋用户JSON，四例顺序）为BM25：150573/142307/138872/270803；Dense：125001/121118/99261/195519；Hybrid：117214/107486/122302/196118。它们是相同冻结检索主张的消息投影估算，未发送：旧检索夹具缺answer stance，不能冒充已通过审核输入校验。包括候选定位/元数据/映射等，不只原文长度。真实链路的实际发送消息字符另按归档测量。

公开复现入口不依赖这些私有案例：tests/test_semantic_service.py用临时synthetic_fixture/假编码器验证；evaluation/semantic_service_comparison.py接受管理员已有冻结案例文件，同一文件分别运行三次，不联网/不读.env：

```powershell
& .\.venv\Scripts\python.exe -m evaluation.semantic_service_comparison --mode hybrid `
  --index data/retrieval_local/semantic/corpus.sqlite3 --vectors data/retrieval_local/semantic/vectors.sqlite3 `
  --model-dir data/retrieval_local/semantic/e5-small `
  --plan data/runtime_local/per-claim-fact-v1/comparison-frozen.json `
  --cases data/runtime_local/per-claim-fact-v1/comparison-final.json `
  --output data/runtime_local/semantic-service-v1/comparison-reproduced-hybrid.json
```

已有对照计划的model/revision字段属于不调用模型的检索夹具，不是推荐服务配置；服务仍最多一次Revision、有限阶段纠正、总/单步超时和实际40次运行保护。

## 单次真实链路与公开检查

真实run4676b27e75ad4defbc53cfeb4a2f83f8，Hybrid＋per_claim_v1，冻结简短发电机概念/标量换算回答及两项原引用。11次模型请求：提取2、独立事实3、原引用分组2、领域2、Revision2；Revision阶段2请求包含一次格式纠正，只有一次修订轮次，另一纠正在初审独立事实。v1/v2完整双重审，最终执行问题0、必需阶段完整；业务review_required、必需检查未均可评估，事实2 supported/3证据不足/1无法评估，最终原引用证据不足。

实际检索5次，无缓存重放记录；依据冻结代码与成功检索记录推导编码10次（含5重放），未保留原运行进程计数器快照，明确不是独立实测。检索记录耗时3.373/3.507/3.499/3.765/4.065秒；服务观测总54.308秒。输入200624/输出6365/总206989 token，缓存命中69248，费用估算USD0.023733144–0.047466288。每阶段消息/响应、用量和范围都在忽略的本机归档。Evidence逐项GET完全相等，重启后结果完全相等、模型11→11，无再次POST。重启服务进程峰值1214169088字节，这不是原任务期间峰值。

项目Python3.13.2完整475项离线回归；干净检出使用锁定API/PDF依赖、无.env/私有data/语义运行依赖，475项、27项可选依赖/私有历史重放明确跳过。七项新增公开接线回归覆盖三模式×两策略、profile/快照失败、组件范围、复用、取消/关闭和重启；原索引维度/完整性/原引用隔离回归保留。原离线Harness demo与JavaScript语法检查通过。本轮真实由HTTP客户端提交，没有声称新增浏览器交互检查或截图；页面配置详情仍需人工浏览器核查。

本机材料统一在data/runtime_local/semantic-service-v1：reading-notes.md、verification.json、冻结计划、comparison*.json、资源测量、测试日志、实际API结果/阶段核对/Evidence及重启记录。真实请求/响应在data/retrieval_local/service_private/4676b27e75ad4defbc53cfeb4a2f83f8；不进入公开提交。准备中的参数类型错误、对照归档元组恢复/缺stance失败均保留，未导致付费重跑。

## 剩余限制与微调准备接入点

本机人工辅助可以选择语义模式，但不能据此认定支持判断改善。完整回查仍占主要暖查询时间，模型启动与索引验证约5秒、语义内存约1.1 GiB；取消底层ONNX是等待完成而不是硬终止。当前单进程/一个活动任务限制保留。

下一阶段从ResponseDiagnostics保存的请求/候选目录/响应、FactRetrievalBinding和Evidence定位建立样本，先区分检索未交付、原引用不足、模型支持错误与工程前提缺失。无证据但直接断言、错误作用域和否定/单位混淆可形成待人工审核样本；本次insufficient/not_assessable只是候选，不能直接当金标准。沿用backend/store.py.RunStore.add_review与实际run/answer_version/finding关联，保留user或ai_assisted_user_supervised来源、操作者和时间，不覆盖模型判断。

训练/验证按问题家族（设备额定值、短路比、单位/否定等）、文档及回答谱系分组，原回答/修订/近重复及相同引用材料必须同组；先冻结分组规则和独立评测，再谈训练。接入点仍为agents/review_templates_v3.py、schema13解析与services/fact_delivery.py范围校验、services/validation_diagnostics.py；没有训练流水线或微调模型，本轮未训练、未重标旧30题、未重建PDF。
