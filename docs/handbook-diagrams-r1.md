# 学习手册r1图源与关系说明

日期：2026-10-04；源码基线3d5e0cd，未修改应用。保留旧handbook-diagrams.md；新PDF使用build_handbook_pdf_r1.py的矢量图。

## 架构图

```mermaid
flowchart TD
 UI[中文Web页面] -->|控制请求| API[API]
 API -->|控制调用| APP[ApplicationService / Factory]
 APP -->|创建并运行| H[OfflineHarness]
 H -->|受控调用| AG[四Agent / Extractor / Tool / Adapter]
 H -->|受控调用| RET[Retriever]
 RET -.->|固定快照只读| KDB[知识SQLite]
 APP -.->|数据访问| RS[RunStore]
 RS -.->|短事务| RDB[运行SQLite / 结果 / 意见]
 H -.->|snapshot observer| APP
 linkStyle 0,1,2,3,4 stroke:#19324B,stroke-width:1.5px
 linkStyle 5,6,7 stroke:#2676AD,stroke-dasharray:7 3
 linkStyle 8 stroke:#B96A20,stroke-dasharray:2 3
```

实线=控制调用；蓝色长虚线=数据访问；橙色点线=持久化观察回调。Factory构造时接收应用服务注册的observer，Harness并不直接写运行库。颜色之外同时使用线型和说明，黑白打印仍可读。

## 运行流程

```mermaid
flowchart TD
 API[API提交 / run_id] --> MODE{模式}
 MODE -->|问答| GEN[Generation]
 MODE -->|已有回答| V1[冻结v1]
 GEN --> V1
 V1 --> EX[ClaimExtractor]
 EX --> FACT[事实审核]
 EX --> DOMAIN[领域审核]
 FACT --> POLICY[确定性政策]
 DOMAIN --> POLICY
 POLICY -->|最多一次| REV[Revision v2]
 REV --> REEX[重新提取 + 双重审]
 REEX --> END[结果 / 人工复核]
 POLICY -->|终止| END
```

流程图的箭头表示阶段顺序，不等同于架构图中的数据访问。异常可提前终止并保存有效部分，观察回调不在此图重复画出。
