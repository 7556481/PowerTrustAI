# 学习手册图源

2026-10-04，对应本机原型v0.1。PDF中的矢量图由 `tools/build_handbook_pdf.py` 绘制；下列Mermaid保留可编辑关系源。模块独立指职责分离，不表示模型统计独立。

## 架构

```mermaid
flowchart TD
  UI[同源中文Web界面] --> API[API：鉴权/校验/作用域]
  API --> APP[ApplicationService：队列/状态]
  APP --> STORE[SQLite：检查点/事件/反馈]
  APP --> FACTORY[ComponentFactory：真实/演示装配]
  FACTORY --> H[OfflineHarness：预算/流程/政策]
  H --> AG[四Agent + ClaimExtractor服务]
  AG --> ADAPTER[受控模型适配器]
  H --> RAG[Retriever + Evidence]
  H --> TOOLS[有限SI工具 + 程序规则]
```

## 运行流程

```mermaid
flowchart TD
  API[API提交/生成run_id] --> MODE{模式}
  MODE -->|问答| GEN[Generation]
  MODE -->|已有回答| FREEZE[冻结回答v1]
  GEN --> FREEZE
  FREEZE --> EX[ClaimExtractor]
  EX --> FACT[事实审核]
  EX --> DOMAIN[领域审核]
  FACT --> POLICY[确定性政策]
  DOMAIN --> POLICY
  POLICY -->|最多一次| REV[Revision v2 / 逐finding动作]
  REV --> REEX[重新提取 + 双重审]
  REEX --> END[保存结果 / 人工复核]
  POLICY -->|结束| END
```

图中省略异常边和每阶段持久化以便阅读；取消、预算耗尽、执行失败均可提前终止并保存有效部分。Revision由现有政策决定，并非每次必经阶段。
