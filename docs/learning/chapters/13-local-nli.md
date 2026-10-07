# 13 本地NLI旁路：版本绑定、跳过与子进程

## 第二判断不是第二个最终裁判

本地MiniLM epoch1可以快速给三分类诊断，但实验出现4/23错误支持。它不覆盖生产not_assessable，也不做工程审核。LocalNLI不会进入Fact、Domain或Revision提示，不投票、不改通过条件；默认关闭时不加载模型、不执行推理。

页面只接受是否启用的布尔选择，模型位置、解释器和profile来自服务器。未配置或不可用应说明原因，不能让浏览器提交任意本机路径。模型revision、checkpoint哈希、适配器和输入身份随诊断保存。

## 转换器为什么经常跳过

production_frames需要证明这个核验组件实际交付了哪段完整正文。aggregate仅有全运行Evidence池，不一定有逐组件绑定，不能任选几段拼premise。混合主张的claim.text加component.proposition可能扩大对象；转换v2优先可靠唯一组件原文锚点，共享/混合缺独立span时跳过，不猜截取。

正文事实、适配器支持的立场才转换。元数据、工具、输入覆盖、工程不可评估、不支持立场或production not_assessable都记录skipped原因。未保存旧delivery_summary不能用现在检索补造历史，查询不触发补算。

## 完整token预检与身份

转换使用组件实际交付的全部正文，不按模型结论选依据；超512token跳过，不能静默截断。input_id绑定run_id、answer_id/version、claim/component、knowledge_version和实际语义文本对；相同文字在不同回答版本也保留各自关联。

诊断记录至少包含状态complete/skipped/failed、reason、绑定、模型身份、token长度、logits、三类结果和与原事实判断的分歧。softmax如展示，必须叫未校准模型分数，不称事实可信概率。

## 为什么用子进程

CPU推理不能阻塞服务事件循环。backend/nli_worker.py在独立解释器加载torch/transformers；LocalNLI按服务生命周期启动并复用，通过UTF-8 JSON行管道交换请求。受控并发锁避免多题交叉响应，超时或异常关闭失败worker并保存诊断失败，不阻断原审核结论。

教学构造：远程审核已结束，NLI worker超时，run业务处置仍是原值，只增加failed诊断。重启查询该run只读之前保存的failed，不因worker现在可用就重新推理。这样诊断失败隔离才有可检验含义。

## 实际验证与覆盖限制

local-nli-wiring-v2唯一官方正文已有回答run c6dfce…，显式per_claim_v1/top1配置，1组件282token，Fact和NLI都supported；本地0.118475秒，观测RSS约481MiB，4真实模型请求，原政策仍review_required。这是实际联动，不是NLI使产品自动通过。

另一次已见33条监督回放能重复logits/标签并保留4错误支持，但不等于同生产事实Agent绑定。first-release-v1的3组件都因门禁skipped，模型加载成功不能称联动推理成功。默认aggregate没有为了凑NLI覆盖切换策略。

## 回归和面试

测试从真实Harness synthetic输出经过production_frames、输入、保存、API，不手工造frame绕过转换。覆盖默认关闭、混合锚点、缺映射、超长、模型失败隔离、版本绑定和重启不補算。实际浏览器显示分歧和跳过，脚本GET不能冒充浏览器验收。

练习：事实Agentcontradicted、NLI supported，最终应如何处理？参考：保存分歧，原政策和发现不变；不能多数投票，也不把诊断supported提升为业务通过。

面试说法：“我把微调模型做生命周期复用的子进程旁路，严格依据组件交付转换，缺证明就跳过。结果版本化追加保存，失败只影响诊断，不回流主审核。”

## 三道自测：先作答，再展开

### 自测1：NLI supported能提升业务处置吗？

::: answer 展开参考答案1
不能；仅旁路诊断，不回流Agent/政策/Revision。
:::

### 自测2：没有组件交付证明能否拼全池？

::: answer 展开参考答案2
不能；明确跳过，不猜范围或补造历史。
:::

### 自测3：超长或worker失败怎么办？

::: answer 展开参考答案3
跳过/失败独立记录，不截断或改变原审核结论。
:::
