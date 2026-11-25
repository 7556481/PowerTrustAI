# 28 初稿、异步读取与字符标注

本专题绑定应用提交 `e4fb27e7c8893a5ad141ebef0ae5f32216648065`，2026-11-24离线核对。配置只看[当前状态](../../current-status.md)。数字分别标记真实实验与教学构造；以下问题不授权现场工程操作。

## 一次页面更新有两个身份
任务ID说明读哪次run，answer_id/version说明看哪版正文。先保存初稿可降低开始阅读的等待，但审核未完不能先上通过色。前端[app.js](../../../backend/static/app.js)以epoch及读取归属处理切换任务、版本和旧请求，不凭“最后返回”覆盖当前页面。
主state/result决定主要内容；trace/reviews/NLI等辅助读取各有在途slot和有界收敛。慢辅助请求不应阻塞主轮询；取消旧GET不等于取消服务任务，取消任务需要显式API动作。

::: answer 题28.1：旧任务的慢响应为什么不能写回新页面？
教学：A请求发出后切到B，B先返回，A最后返回。若只用一个全局result，页面回到A。应用应在发送时捕获epoch/任务/版本，返回时再比较；旧归属丢弃。反馈回读还要考虑reviews revision，避免旧列表覆盖新反馈。看[主读取](../../../backend/static/app.js)、[前端检查](../../../tests/ui_client_checks.js)。继续追问：仅AbortController不够，取消可能晚于响应，所以归属检查仍必要。
:::

## 字符范围为什么会错
Python按Unicode码点索引，JavaScript字符串索引是UTF-16 code unit。教学“电😀压”在Python长度3，在JS.length为4；Array.from得到3个码点。后端[answer_annotations](../../../backend/answer_annotations.py)验证版本、范围和逐字原句，前端[inline_review](../../../backend/static/inline_review.js)按码点核对并绘制。

::: answer 题28.2：同句多意见、重叠区间和找不到原句怎样处理？
同区间汇聚多个意见入口、理由分别保留；交叠范围分段为非嵌套mark；没有可靠定位的工程意见保留未定位摘要。旧数据只有原句时要求唯一逐字匹配，错误offset不能退回模糊搜索。不能高亮提取器的改述命题作为原正文。继续追问：颜色表示审核判断而非真伪，没高亮也不等于全正确。
:::

::: answer 题28.3：为什么复制应取保存的原文？
DOM含mark、意见卡、状态和辅助文本；复制DOM会把解释混入正文，或受布局空白影响。应取所选保存版本text，并检查当前版本归属。历史版本不能叠最新意见，反馈也绑定对应对象。离线夹具能验证交互与竞态，不能证明审核语义正确。见[原文标注夹具](../../../tools/ui_inline_fixture_v7.py)。继续追问：重试辅助GET与重试提交POST后果不同，前者只读，后者可能建立新付费任务。
:::

## 返回顺序演算（先写四项结果）

教学日志：t0打开A，epoch=7，发GET A；t1切B，epoch=8，发GET B；t2 B返回并保存正文B；t3 A返回。请写出t3对象归属、最终页面、Abort失败的影响、复制来源。

::: answer 展开返回顺序解析
A响应属于发送时A/epoch7，当前选择是B/epoch8，不能写回视图或释放B的新读取锁。页面继续显示B；Abort只是减少无用工作，归属检查负责正确性。复制从当前所选版本保存的text取，不从带标注卡的DOM取。这里epoch数字是教学构造，实际守卫见backend/static/app.js的请求身份与选择归属，以及inline_review.js的版本核对；GET失败不能显示POST受理未知。
:::
