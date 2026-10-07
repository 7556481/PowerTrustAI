# 02 全系统架构和一次请求的数据流

## 是什么：把判断、流程和展示分开

一个可测试系统必须允许替换模型适配器，而不重新发明业务流程。PowerTrustAI的领域对象在core，Agent执行各自判断，Harness控制流程，Retriever交付证据，应用服务持久化，UI只展示和提交。这些模块依赖方向比“四个Agent”的名字更重要。

```diagram
{
  "title": "调用、证据交付与持久化分离",
  "width": 820,
  "height": 710,
  "nodes": [
    {
      "id": "api",
      "x": 20,
      "y": 20,
      "w": 170,
      "h": 60,
      "label": "API / Submit\n结构验证与任务身份"
    },
    {
      "id": "svc",
      "x": 300,
      "y": 20,
      "w": 170,
      "h": 60,
      "label": "ApplicationService\n保存 / 有界队列"
    },
    {
      "id": "worker",
      "x": 590,
      "y": 20,
      "w": 170,
      "h": 60,
      "label": "worker / Factory\n真实组件装配"
    },
    {
      "id": "h",
      "x": 590,
      "y": 150,
      "w": 170,
      "h": 75,
      "label": "OfflineHarness\n检索 / 生成 / 冻结\n控制状态与预算"
    },
    {
      "id": "extract",
      "x": 300,
      "y": 150,
      "w": 170,
      "h": 60,
      "label": "ClaimExtractor\n锚点 / 主张 / 组件"
    },
    {
      "id": "rag",
      "x": 20,
      "y": 300,
      "w": 145,
      "h": 60,
      "label": "Retriever / Evidence\n限定用途的交付"
    },
    {
      "id": "fact",
      "x": 230,
      "y": 300,
      "w": 145,
      "h": 60,
      "label": "事实审核\n独立核验 / 原引用"
    },
    {
      "id": "domain",
      "x": 440,
      "y": 300,
      "w": 145,
      "h": 60,
      "label": "领域审核\n输入 / 范围 / 前提"
    },
    {
      "id": "policy",
      "x": 590,
      "y": 420,
      "w": 170,
      "h": 60,
      "label": "确定性政策\n结束 / 一次修订"
    },
    {
      "id": "observer",
      "x": 300,
      "y": 510,
      "w": 170,
      "h": 60,
      "label": "observer\n阶段快照 / 事件"
    },
    {
      "id": "store",
      "x": 20,
      "y": 510,
      "w": 170,
      "h": 60,
      "label": "RunStore\n短事务 / 版本保存"
    },
    {
      "id": "ui",
      "x": 20,
      "y": 630,
      "w": 170,
      "h": 60,
      "label": "API结果投影 / UI\n只读回查"
    }
  ],
  "edges": [
    {
      "from": "api",
      "to": "svc",
      "kind": "control"
    },
    {
      "from": "svc",
      "to": "worker",
      "kind": "control"
    },
    {
      "from": "worker",
      "to": "h",
      "kind": "control"
    },
    {
      "from": "h",
      "to": "extract",
      "kind": "control",
      "points": [
        [
          590,
          177
        ],
        [
          470,
          177
        ]
      ]
    },
    {
      "from": "extract",
      "to": "fact",
      "kind": "data",
      "points": [
        [
          340,
          210
        ],
        [
          302,
          300
        ]
      ],
      "label": "同版主张",
      "label_at": [
        260,
        260
      ]
    },
    {
      "from": "extract",
      "to": "domain",
      "kind": "data",
      "points": [
        [
          425,
          210
        ],
        [
          510,
          300
        ]
      ]
    },
    {
      "from": "h",
      "to": "fact",
      "kind": "control",
      "points": [
        [
          590,
          215
        ],
        [
          615,
          270
        ],
        [
          385,
          270
        ],
        [
          385,
          330
        ],
        [
          375,
          330
        ]
      ]
    },
    {
      "from": "h",
      "to": "domain",
      "kind": "control",
      "points": [
        [
          650,
          225
        ],
        [
          650,
          330
        ],
        [
          585,
          330
        ]
      ]
    },
    {
      "from": "rag",
      "to": "fact",
      "kind": "data"
    },
    {
      "from": "rag",
      "to": "domain",
      "kind": "data",
      "points": [
        [
          92,
          360
        ],
        [
          92,
          385
        ],
        [
          510,
          385
        ],
        [
          510,
          360
        ]
      ]
    },
    {
      "from": "fact",
      "to": "policy",
      "kind": "data",
      "points": [
        [
          302,
          360
        ],
        [
          302,
          450
        ],
        [
          590,
          450
        ]
      ]
    },
    {
      "from": "domain",
      "to": "policy",
      "kind": "data",
      "points": [
        [
          585,
          340
        ],
        [
          630,
          340
        ],
        [
          630,
          420
        ]
      ]
    },
    {
      "from": "h",
      "to": "observer",
      "kind": "persist",
      "points": [
        [
          760,
          187
        ],
        [
          800,
          187
        ],
        [
          800,
          540
        ],
        [
          470,
          540
        ]
      ],
      "label": "阶段通知",
      "label_at": [
        707,
        520
      ]
    },
    {
      "from": "observer",
      "to": "store",
      "kind": "persist",
      "points": [
        [
          300,
          540
        ],
        [
          190,
          540
        ]
      ]
    },
    {
      "from": "store",
      "to": "ui",
      "kind": "data"
    },
    {
      "from": "h",
      "to": "policy",
      "kind": "control"
    }
  ]
}
```

箭头既有控制调用也有数据交付；数据库不是第五个Agent，observer不是另一个调度器。事实和领域审核收到同一版本答案和同一主张集合，但独立的用途检索证据。第一次审核不读取对方结论，避免直接迎合。

## 目录职责：从入口沿依赖读

| 目录 | 主要职责 | 不应承担 |
|---|---|---|
| core | 冻结数据类、类型依据、校验、报告 | 网络请求和网页展示 |
| model_adapter | 供应商调用、使用量、超时、调用归属 | 业务自动通过 |
| agents | Generation、Evidence、Domain、Revision | 复制主调度流程 |
| services | 提取、锚点、候选、严格解析、NLI转换 | 随意补非法模型字段 |
| harness | 状态转换、预算、检索组织、双审、政策 | UI读取私有密钥 |
| rag | 入库、版本、检索、定位、索引 | 根据监督标签挑模型证据 |
| backend | 单服务生命周期、API、队列、运行存储 | 重发历史任务 |
| evaluation | 冻结数据与实验评测、训练入口 | 把实验默认变生产默认 |
| tests | 离线synthetic和契约回归 | 默认付费请求 |
| data | 私有全文、模型、DB、实际运行 | 自动提交到Git |

tools同时包含有限工具和文档构建器，具体入口按文件区分。旧独立仓库power-system-hallucination-risk-assessor保留历史，不成为新审核规则权威。

## 一次请求：对象怎样诞生

API接收普通输入，程序建立task_id/run_id并保存请求配置。Harness验证任务与预算，检索当前固定knowledge_version。Generation得到实际Evidence及绑定，不只得到候选标题。回答的answer_id/version由程序建立，引用区间对应实际正文。ClaimExtractor据冻结原文锚点生成规范命题和组件，程序检查覆盖、ID与类型。

随后系统为事实/领域用途检索并保存交付记录。审核结果不能自行铸造原文或索引来源。Program检查typed bases属于正确作用域、字面摘录存在、数量关系可由真实工具验证。政策读取结果与执行问题，而不是再问一个模型“到底能不能通过”。修订若发生则创建新回答版本，重新提取和双审；observer每个阶段用短事务归档。

## 身份层次：为什么不能只存一段字符串

文档ID回答“哪份文档”；文档版本回答“哪次原件/解析”；片段ID回答“哪个字符区间”；知识版本回答“哪些文档版本的集合”；Evidence身份包含其快照归属；answer_id/version回答“哪版答案”；claim/component回答“哪个对象”；finding回答“哪条判断”。同样文字在两个来源中不自动共用出版身份，同样命题在两个回答版本中不共用审核结论。

哈希用于内容身份，不是质量分数。若text_hash一致，只能说明字节相同，不能说明来源可信。若knowledge_version变了，同一查询的缓存不能直接复用；如果回答版本变了，检索交付的组件绑定需要重建。

## 依赖注入：为什么值得学

ComponentFactory构造真实模型/检索/工具，传给OfflineHarness。离线测试可传入假适配器，仍走相同校验和状态机。测试换的是外部不确定性，不是绕过生产转换。相反，手工造一个NLI frame跳过Harness输出，会验证错误路径。

这不是为了“用了设计模式”。收益是能区分：业务流程bug、网络故障、模型非法输出和语义判断错。代价是数据契约必须清楚，过多模型字段会增加失败；第08章会讨论本轮接口简化。

## 自有Harness的收益与代价

**记录事实**：现有ComponentFactory/OfflineHarness组织明确契约、状态、并行双审和有限修订，没有通过LangChain或LangGraph搭建全部Agent。**共同复盘**：领域对象先明确，才能回查每步实际材料、离线替换不确定的模型适配器；代价是自行维护生命周期、协议迁移和包装接线。schema14漏包装恰好说明自有运行时也会犯集成错误。

这不证明框架不适合，更不证明当时实测过多个框架。LangGraph Adapter只是后来讨论的可选对照，未实现。关于本人当时评估过什么、为什么偏好某方案，仍列个人待确认。

## 验证、坑与面试

验证架构时，给synthetic任务注入ModelResponse，观察实际状态和保存对象，不只单独测函数。检查两个审核输入的answer_version一致、第一次消息不含另一Agent结论、修订后claim重新生成。用失败适配器确认执行未完成，不能把异常变成contradicted。

练习：API收到任务后立刻返回run_id，为什么不是同步返回审核结果？参考：实际生成/双审耗时较长，服务通过有界队列执行并保存状态；UI能读进度和取消，网络短暂中断不会要求重新POST。仍需承认服务没有通用提交幂等保证。

面试说法：“我复用一个Harness，把供应商、检索和持久化作为可替换组件。程序管理身份/定位/处置，模型承担语义。observer只记录事实，不自行发起新Agent。”

## 三道自测：先作答，再展开

### 自测1：observer为何不是调度器？

::: answer 展开参考答案1
它记录阶段快照/事件并持久化，不发起Agent行动。
:::

### 自测2：回答版本与知识版本有什么区别？

::: answer 展开参考答案2
前者标哪版答案，后者标哪组资料版本，二者都必须绑定。
:::

### 自测3：为什么数据库不是事实裁判？

::: answer 展开参考答案3
数据库保存可回查内容，支持关系仍需语义核验。
:::
