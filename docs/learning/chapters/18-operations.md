# 18 环境、启动、Git、迁移与排障

## 三种入口，互不打断

日常双击start-powertrustai.cmd，使用8765并自动连接；问答/已有回答正常提交会调用付费模型。演示用python -m backend --demo，必须独立端口/目录配置，synthetic_fixture不用DeepSeek；不能演示结果冒充真实审核。学习双击start-learning.cmd，8770纯静态，不读模型密钥、不启动任务、不占运行库。

```powershell
cd D:\PowerTrustAI
& .\.venv\Scripts\python.exe -m backend --open --port 8765
& .\.venv\Scripts\python.exe -m backend --stop --port 8765
& .\.venv\Scripts\python.exe -m tools.learning_site build
& .\.venv\Scripts\python.exe -m tools.learning_site serve --open --port 8770
```

学习服务Ctrl+C停止，不影响审核。直接打开docs/learning/site/index.html同样可读，页面搜索通过本地search-data.js，无fetch/CORS要求。正文只改Markdown，HTML不要手工维护第二份。

## 环境与资源

项目解释器D:/PowerTrustAI/.venv/Scripts/python.exe，项目Python3.13；训练依赖独立CPU环境已存在，不为读站重建。Git/Python缺失使用官方渠道，依赖按锁文件，不盲目升级。Intel GPU不按CUDA配置，不为项目修改驱动。

资料、模型、DB和真实输出在data忽略目录。公开克隆不带私有权重/全文库，所以默认离线synthetic能运行，不代表真实语料可完整复现。文档构建器只依赖标准库，不引入复杂平台、远程字体或训练框架。

## 迁移需要证明什么

先定位实际迁移目录，核对restore、manifest、exclusions、failures；大小/SHA相符再复制data，相对结构不变，冲突停止覆盖。数据库检查SQLite integrity，保留迁移目录，不复制旧虚拟环境、旧凭据或旧WAL/SHM。模型revision/配置/快照与索引需匹配。

路径变化只修改新的启动配置和环境，不批量改写历史冻结请求、task哈希或归档。旧训练环境重装依赖不等于重跑实验；恢复验证仅导入/本地加载。凭据由所有者本机填写，报告仅路径和版本，不显示真实值。

## Git与命令级网络

修改前看status、HEAD和远端，实际有更新接续不回退。代码/Markdown/静态站源码提交，data/原始响应/权重/官方全文不提交。普通push，不强推。代理只在明确需要的Git命令使用已核实127.0.0.1:7897，不能把Git代理盲套到模型API，更不关SSL。

```powershell
git status --short
git rev-parse HEAD
git -c http.proxy=http://127.0.0.1:7897 ls-remote origin refs/heads/master
```

本地提交成功不等远端更新，push之后读远端哈希；敏感检查应看实际Git树和blob，不只相信.gitignore。配置说明用空值或名称，不含密钥。

## 按错误层次排障

| 表现 | 应查证据 | 不要做 |
|---|---|---|
| 401/连接丢失 | 本机会话、固定令牌路径、origin、服务重启 | 发令牌到聊天或URL |
| 422输入拒绝 | 必填字段/模式/长度及实际请求 | 编造厂站参数 |
| 429队列满 | 活动run及等待队列 | 连续POST刷提交 |
| 模型连接失败 | 实际异常类型、阶段、服务配置 | 认定不支持中文、关闭SSL |
| OUTPUT_CONTRACT_ERROR | 原响应、纠正、具体字段、实际模板 | 只补题目提示、静默填ID |
| 证据不足 | 原文、范围、交付、完整命题条件 | 把未找到说成全库不存在 |
| KeyError _id | 分片schema与原断点 | 重复下载或清空库 |
| interrupted | 原结果/阶段、重启恢复 | 自动重发付费任务 |

## 最小复现记录

记录源码/配置/知识/模型revision，实际输入、阶段、原响应、校验位置、有效部分、调用量、时间与资源。浏览器检查保存实际截图；HTTP脚本仅是脚本证据。学习内容来源可公开必要脱敏摘要，完整原始证据仍私有。

普通回归：python -m unittest discover -s tests -v，离线不加载.env、不付费。冻结验收批次另有授权和停止条件，事前预期不进入模型消息。环境受限拒绝启动用工具审批，不重建环境或改权限绕过。

## 构建与进度排障

先查实际命令/父子关系、日志尾、next_row、磁盘，再判断退出原因。没有日志证据就写未知，不猜断电/网络。仍有唯一写者时不另起；退出后从有效断点恢复，不能清库。发布有独立完成核验记录后才可考虑切换日常配置，本轮不自动切换。

## 面试与最终练习

练习：日常服务正常、学习站8770打不开，是否要重启审核？参考：不需要，查学习server/静态文件/端口，不干扰8765。练习：模型API成功但Git推不上，是否统一设置全局代理？参考：分别诊断，保持命令级及SSL。

面试可说：“我把可运行代码、私有资料恢复和可复现结论分开，保留哈希/版本与失败。统一入口改善本机使用，但没有把单用户localhost部署宣称多用户生产平台。”

## 文档源码跨平台身份

Git可把Windows工作区CRLF检出为Linux LF；直接比较工作区原字节SHA会误报代码不同。学习站source-check同时保留原始文件SHA和明确source_text_lf_sha256（仅CRLF→LF，空格/代码不变）；CI按后者核查教学源码。真实Evidence、PDF和快照仍严格原字节/原文/版本哈希，不能套这个教学规则修改生产依据。首次远端CI失败保留，Git LF副本重现后修复，再核对CI，而不是取消来源校验。

## 三道自测：先作答，再展开

### 自测1：学习站启动是否要停8765？

::: answer 展开参考答案1
不需要；8770独立静态阅读。
:::

### 自测2：Git网络与模型网络应统一代理吗？

::: answer 展开参考答案2
应分别诊断，不盲套代理或关闭SSL。
:::

### 自测3：唯一写者仍在运行能再启动吗？

::: answer 展开参考答案3
不能；先核对进程/父子关系，保留原断点。
:::
