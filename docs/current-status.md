# 当前状态

截至2026-11-13的发布配置与能力说明。本页是唯一当前状态正文，不是实时服务探针。

## 现在交付什么

单用户本机电力资料问答与自动审核原型：有依据的回答、句旁审核意见、绑定回答版本的引用和原文回查。公开仓库提供合成演示与独立学习站。

## 怎样启动

- **公开克隆**：按[演示教程](demo.md)安装，再运行 `start-powertrustai.cmd --demo`；合成数据，无需私有库或密钥，不发模型请求。
- **已有本机部署**：双击 `start-powertrustai.cmd`；私有SQLite、历史Store、预算和DeepSeek配置留在本机，真实提问使用付费Flash。回退用 `rollback-overlap.cmd`，见[运维](learning/chapters/18-operations.md)。
- **学习**：[学习首页](learning/index.md)，或 `start-learning.cmd`；学习站与8765分离。

## 实际使用什么配置

本机受管配置：**SQLite全文检索、LangGraph编排、schema13、DeepSeek Flash（deepseek-flash）**，显式 `overlap` 让事实审核与领域检索重叠；事实内部 `serial_v1`。Harness管预算、取消和停止。有据且符合资格时最多修订一次，再重新提取并完整双审。

公开克隆不带私有资料、历史或受管设置；演示用合成Factory。通用未配置入口仍为 `component` Factory、`sequential` 驱动，不等于本机受管配置。Tantivy实验资产已退役，日常用SQLite。

## 已知边界与实时状态

引用可查、审核完整或pass不等于语义正确或工程安全。自动审核会漏条件，领域审核不能替代现场输入与电网分析。[十道真实问题](evaluation/stable-product-baseline-v1/report.md)中六道审核完整，该批无有据修订；历史错误稿的局部修订不证明自然问答自主纠错收益。性能按批次及计时起点看[第16章](learning/chapters/16-performance.md)。

**8765是否正在监听**：只读本机 `http://127.0.0.1:8765/health`，核对status、可接单生命周期、实际Factory探针与Store；不可达就如实记录。旧ready／停服仅是报告日期的观察，不能推出现在可用；配置说明可长期查，进程状态须实时查。

[历史索引](history-index.md) · [2026-10-25原状态全文](current-status-2026-10-25.md) · [开发索引](documentation-index.md)

<!-- 兼容旧状态页锚点：旧内容请进入上方有日期的原文。 -->
<a id="当前状态2026-10-25自然问答审核接缝封存"></a>
<a id="本轮消息一致性已修未证明产品净收益不采用"></a>
<a id="最新程序绑定目标产品净收益仍未成立"></a>
<a id="最新模型结构收益未转为整体审核收益"></a>
<a id="2026-10-24-最新基础结构通过复杂审核仍失败"></a>
<a id="最新核验"></a>
<a id="最新核验-1"></a>
<a id="2026-10-24-领域业务候选与事实收尾"></a>
<a id="2026-10-09-第二版限定原型冻结历史"></a>
