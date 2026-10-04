# PowerTrustAI

本机、单用户的电力知识问答与已有回答辅助审核原型。模型判断、程序规则、工具结果和人工意见分别保留；`pass` 是当前政策的业务结果，不是工程安全认证。微调尚未实现。

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

打开 <http://127.0.0.1:8765/>。服务生成本机访问令牌文件 `data/runtime_local/access-token`；用记事本在本机查看，手动填入页面后连接。令牌仅在页面内存，刷新后需重输，勿写入URL、聊天或截图。按Ctrl+C停止服务。演示显著标记 `synthetic_fixture`，不读取项目`.env`、不需要私有知识库、不调用付费API。

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

[当前状态](docs/current-status.md) · [公开复现报告](docs/public-reproducibility-v1.md) · [并发轨迹修复](docs/model-trace-attribution-v1.md) · [后续实施接入点](docs/implementation-roadmap.md) · [文档索引](docs/documentation-index.md)

中文学习与面试手册为[独立r1文档](docs/PowerTrustAI-project-study-interview-handbook-r1.md)，README不替代手册。本轮未重建PDF或改写历史验收。
