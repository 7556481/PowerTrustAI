# PowerTrustAI

本机、单用户的电力知识问答与已有回答辅助审核原型。模型判断、程序规则、工具结果和人工意见分别保留；`pass` 是当前政策的业务结果，不是工程安全认证。已有CPU微调与可选本地NLI诊断；NLI默认关闭且没有审核决策权。

## 产品试用 v1

日常服务显式使用版本化`product-decision-v1`：检查完整、主张支持且无阻断发现可自动通过；定位明确的普通错误最多一次修订并完整重审；仍错误不通过，证据/工程输入不足待补充，判断争议人工复核，执行失败独立显示。演示规则不构成权威高风险判据；当前没有注册生产高风险认证规则。通过不代表工程安全认证。

先运行下方`--demo`，连接后尝试问答与已有回答审核；演示模拟判断，仅验证交互。再由本机配置`.env`的`DEEPSEEK_API_KEY`与`DEEPSEEK_MODEL_ID`，启动真实服务：

```powershell
Set-Location D:\PowerTrustAI
& .\.venv\Scripts\python.exe -m backend --port 8765
```

页面选择概念/资料或工程范围；工程范围与实际主张同时审查，选择概念不能让性能承诺绕过technical_truth。工程结构化输入、量纲换算及固定原引用可用现有API字段，详见[产品处置与试用指南](docs/product-improvement-v1.md)。页面优先展示最终回答、处置、风险/未知、问题解决程度；版本、证据与原始详情保留。Ctrl+C停止；重启查询不自动重发。以前记忆8768地址的用户可用`--port 8768`复用该origin。

需要复现历史政策时，当前终端设置`$env:POWERTRUST_DECISION_POLICY="legacy-v1"`；日常默认`product-v1`，不回填旧结论。可用`POWERTRUST_RUN_DB`指定独立运行库；固定令牌路径不变，NLI保持默认关闭。

## 最短离线入口

已验证 Python **3.13.2**（Windows）。核心离线 Harness 无第三方依赖；在独立克隆中执行：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m harness.demo
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

普通测试不调用模型。未安装可选依赖时，API/PDF检查明确跳过；私有历史响应不随仓库分发，对应历史重放缺文件时跳过。公开synthetic_fixture回归仍执行。完整公开API/PDF回归：

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock.txt -r requirements-pdf.txt
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 本机网页演示

```powershell
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock.txt
& .\.venv\Scripts\python.exe -m backend --demo --port 8765
```

打开 <http://127.0.0.1:8765/>。服务生成本机访问令牌文件 `data/runtime_local/access-token`；用记事本在本机查看，手动填入页面后连接。固定令牌存在即复用，普通重启及模型切换不轮换。默认仅页面内存；主动勾选“记住本机连接”后在当前浏览器/地址保存，支持忘记及401清除。勿写入URL、聊天或截图。按Ctrl+C停止服务。演示显著标记 `synthetic_fixture`，不读取项目`.env`、不需要私有知识库、不调用付费API。

另一终端可执行 `& .\.venv\Scripts\python.exe -m backend.http_demo --port 8765`：先核验演示模式，再检查两种提交、Evidence回查、反馈、错误版本409和无令牌401；运行材料留在本机忽略目录。

真实模式参见[统一运行说明](docs/prototype-v0.1.md)：准备获准使用的固定知识快照和服务端DeepSeek配置后，以 `python -m backend --port 8765` 启动。DeepSeek密钥用于服务端模型连接，本机令牌用于本地API访问，二者不同。真实资料、模型、`.env`、数据库和实际请求响应不在公开仓库；公共克隆可复现离线/演示工程行为，不能直接重放私有真实验收。

## 当前架构

可选[逐主张事实检索与交付v1](docs/per-claim-fact-retrieval-v1.md)已实现；aggregate仍为默认，生成/领域检索及BM25排名不变。新策略通过服务端 `POWERTRUST_FACT_RETRIEVAL_STRATEGY=per_claim_v1` 启用，提供逐组件查询/候选映射；[固定对照](docs/per-claim-fact-comparison-v1.md)同时报告覆盖和额外成本，不据少量案例切换默认。

同源HTML/CSS/JavaScript → HTTP API → `ApplicationService`（单进程、一个活动任务、两个等待位置）→ `ComponentFactory` → 现有 `OfflineHarness`。问答生成或接收已有回答后，提取主张；事实审核与领域审核并行；确定性政策决定最多一次Revision，再完整重提取和双重审。SQLite保存阶段检查点、结果和追加人工反馈；重启将未完成运行标记interrupted，不自动重发。

- **默认检索：BM25**，固定知识版本、Evidence原文定位与ID作用域校验。
- **Dense/RRF：已接入真实服务可选配置，BM25仍默认**；使用 `POWERTRUST_RETRIEVAL_MODE=dense` 或 `hybrid`，需预备匹配的固定模型与向量索引；见[启动、固定对照与资源边界](docs/semantic-service-v1.md)。事实策略aggregate/per_claim_v1独立选择，启动不下载或建索引。
- **真实服务事实审核：显式schema13**，独立事实请求与按原绑定作用域分组的引用检查；领域协议4、Revision协议2。旧schema与历史结果保留原解释。
- 执行失败、证据不足和工程前提缺失分别报告；阶段完成与检查无法评估可以同时成立。程序规则仍为演示规则，反馈来源为AI辅助、用户监督。
- 调用清单按实际请求计数；并行轨迹使用请求编号与阶段调用标识绑定，超时/取消/格式失败也保留记录。
- [支持判断数据准备与未微调基线](docs/support-judgment-dataset-v1.md)已有可运行命令与待监督复核包；已有监督与CPU微调实验，生产审核器未被本地NLI替换。pending 不计算语义正确率，真实基线结构失败后保留部分预测并停止。

[当前状态](docs/current-status.md) · [公开复现报告](docs/public-reproducibility-v1.md) · [并发轨迹修复](docs/model-trace-attribution-v1.md) · [后续实施接入点](docs/implementation-roadmap.md) · [文档索引](docs/documentation-index.md)

中文学习与面试手册为[独立r1文档](docs/PowerTrustAI-project-study-interview-handbook-r1.md)，README不替代手册。本轮未重建PDF或改写历史验收。
