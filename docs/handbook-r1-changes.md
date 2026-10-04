# 《PowerTrustAI项目学习与面试手册》r1修改清单

日期：2026-10-04。对旧31页版定向修订，不改应用功能、协议、检索或政策，不调用API、模型，不重跑历史实验，不自动提交或推送。

## 版本与保留

- 当前代码提交仍是master上的 `3d5e0cd842a1039731aafb209fb5444bd1905622`；本轮核对只有一个提交，没有基线后的文档提交。128个应用源码/资源与HEAD一致。
- 保留旧 `PowerTrustAI-project-study-interview-handbook.md`、旧31页PDF、旧图源和旧构建器，旧正文/PDF SHA前后核对一致。
- 新源：[PowerTrustAI-project-study-interview-handbook-r1.md](PowerTrustAI-project-study-interview-handbook-r1.md)。新PDF：output/pdf/PowerTrustAI_Project_Study_Interview_Handbook_v0.1-r1.pdf。应用仍是v0.1，r1只是手册修订号。
- 新图源：[handbook-diagrams-r1.md](handbook-diagrams-r1.md)；独立构建器：tools/build_handbook_pdf_r1.py。

## 六项定向修正

| 项目 | 修订内容 | 对应依据 |
|---|---|---|
| BM25排序 | 分数降序主排序；平分按document_id/version/ordinal/fragment_id升序，不依赖SQL或插入顺序 | rag/retriever.py、rag/bm25.py |
| 架构关系 | 实线控制、蓝虚线数据访问、橙点线observer；知识库与运行库分开，Harness不直接写运行库 | backend/service.py、assembly.py、store.py、harness/runtime.py |
| 96014历史预算 | 标明临时异常验收配置，非推荐；默认40一直保留。引用单元成本缺少小型硬界限，当前协议尚未修复 | backend/config.py、services/answer_units.py、agents/revision_contract_v2.py、历史冻结计划 |
| 日常真实/实验 | 日常主动提交使用默认预算，不要求每次实验授权；对照/验收实验才另冻结输入配置和停止条件 | 当前UI/API行为、用户本轮明确要求 |
| 否定比较 | “并非230 V”数学上成立；insufficient_evidence是当轮模型审核行为及绑定限制，不是数学争议 | 既有真实修订归档及标量换算关系 |
| Git/网络时效 | 无基线后文档提交；网络重置为2026-10-04前轮记录，本轮未查询，不能宣称永久不可达 | 本轮本地git log/status；历史网络记录 |

## 新增学习内容

1. 第5章：BM25公式、TF饱和、positive IDF、token长度归一化、四片段排序和平分例。
2. 第5章：E5 query/passage前缀、mask均值、窗口均值后L2、二维余弦手算；纠正旧版容易误读的窗口归一化顺序。
3. 第5章：RRF公式和两路名次手算；top-k融合使必要组合由2/2退至1/2的构造例，非历史重跑。
4. 第13章：unknown保留名次时Hit/MRR数学界限；实际评测器含unknown返回None的保守行为另列；必要组覆盖例与有效分母。
5. 第18章：五段实际源码——装配、并行审核、政策、检查点持久化、页面提交。仅去公共缩进，逐段校对路径、行号和SHA，解释输入、输出、错误边界与依赖。
6. 第16章：不用LangChain的现有工程取舍；受控工作流/自治、async/线程取消、WAL/单worker、客户端锁/服务端幂等。

## 验证与真实限制

本轮仅执行文档构建、教学算术复核、源码比对和PDF检查。没有API/模型调用，没有历史指标重算或项目测试重跑，不把既有428项日志称为本轮测试。

最终PDF为38页，所有页面重新渲染并检查18个目录书签/页码、中文嵌入字体、三类箭头、表格、公式、长代码换行及裁切。代码在语法边界优先换行，显示续行标记不进入Markdown源码。页数、SHA、5段摘录和55个路径核验在data/runtime_local/handbook-r1/verification.json；旧版保留证明在original-hashes.json，精确摘录在code-excerpts.json。

发现并修正的文档问题：旧版BM25身份排序表述不清；旧矢量图让Harness看似直接写库；旧预算段容易被当成建议；新章目录文字替换曾同时落入第17章正文，已改为仅匹配目录区域。均为文档或图示修订，没有偷偷修协议、重审模型或美化历史失败。

尚未修复：引用单元数与最坏成本契约缺口、客户端无服务端幂等协议、既有目标/fidelity语义局限。旧模型insufficient标签仍保留，同时解释其不代表数学疑问。未声明通用准确率、专家金标准或工程认证。
