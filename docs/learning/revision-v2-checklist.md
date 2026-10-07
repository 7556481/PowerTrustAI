# 逐章修订与源码核对

正文绑定提交见source-version.json；源码路径、范围、SHA见source-check.json。旧手册完整保留。

- docs/learning/chapters/01-product.md: 本轮加入三道折叠自测；正文2122字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/02-architecture.md: 本轮加入三道折叠自测；正文7306字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/03-agents.md: 本轮加入三道折叠自测；正文2573字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/04-harness.md: 本轮加入三道折叠自测；正文4663字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/05-rag.md: 本轮加入三道折叠自测；正文3440字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/06-retrieval-math.md: 本轮加入三道折叠自测；正文4706字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/07-corpus.md: 本轮加入三道折叠自测；正文3262字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/08-verification.md: 本轮加入三道折叠自测；正文3735字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/09-engineering-tools.md: 本轮加入三道折叠自测；正文2628字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/10-api-storage.md: 本轮加入三道折叠自测；正文2281字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/11-supervision-metrics.md: 本轮加入三道折叠自测；正文3500字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/12-training-nli.md: 本轮加入三道折叠自测；正文6214字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/13-local-nli.md: 本轮加入三道折叠自测；正文1998字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/14-code-tour.md: 本轮加入三道折叠自测；正文29803字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/15-failures.md: 本轮加入三道折叠自测；正文4034字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/16-performance.md: 本轮加入三道折叠自测；正文2979字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/17-interview.md: 本轮加入三道折叠自测；正文2977字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/18-operations.md: 本轮加入三道折叠自测；正文2712字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/19-glossary.md: 本轮加入三道折叠自测；正文4198字符。专项修订见integration-learning-v2及对应章新增段落。
- docs/learning/chapters/20-workshops.md: 本轮加入三道折叠自测；正文3162字符。专项修订见integration-learning-v2及对应章新增段落。

第14章核对实际函数调用与摘录；省略代码均有说明。个人历史取舍无法确认的部分留在questions-for-chatgpt.md，不编造。最终页面补验缺口见报告。

## 专项修改对应

- 01：保持两种入口/处置边界，补学习自测。
- 02：架构图增加控制、交付、持久化图例和Harness到政策控制边。
- 03：独立审核仅判断实际交付，非穷尽知识库。
- 04：状态机图及有限纠正、修订自测。
- 05：Dense不匹配拒绝与显式BM25配置；四种真实缓存对象/键/失效。
- 06：检索公式保留，手算与实验分开、自测补充。
- 07：流式构建与身份/断点自测，未冒称发布完成。
- 08：条件充分/必要反例、交付范围、新烟测失败边界。
- 09：SI/功率公式/额定/用户参数边界表；正弦与工程约束。
- 10：持久化、重启、凭据自测。
- 11：实验版本与有效分母，0/23不等于零风险。
- 12：Tiny/MiniLM/RoBERTa实际起点、许可、选择及样本；领域分类适配。
- 13：NLI无决策权、跳过、自测。
- 14：实际接收到UI路线、合成对象、源码摘录、包装遗漏、observer/事务、修订重建。
- 15：目标变化、旧评分、严格协议负担、单题补丁/测试数量/早收尾教训。
- 16：真实缓存与拒绝行为核查，未实现优化只作为建议。
- 17/18/19：面试、运维、术语自测；所有者贡献不夸大。
- 20：工作坊四纠正逻辑与两个反例，不把缺论证判为矛盾。

首页新增渐进路线；20章各三道自测，答案默认折叠；源码对应应用提交见source-version.json，逐函数行号/SHA见source-check.json。源码真实性与语义教学需分别复核，不以文件存在等同理解正确。
