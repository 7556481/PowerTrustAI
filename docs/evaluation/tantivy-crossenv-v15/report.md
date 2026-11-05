# Windows→Linux续写→Windows产品读取：首次小样本验证

结论：**本轮未验证通过，尚不能确认能够跨环境续写并由Windows产品读取；也没有证据认定索引格式不兼容。** 首次Windows准备阶段因本轮验证脚本的SQLite连接释放错误失败，Linux续写及返回读取均未执行。依用户“任一步失败即记录边界”要求不修后重跑。

## 环境与冻结方案

本机wsl --list --verbose返回1、--status返回50，正确UTF-16解码均为“未安装适用于Linux的Windows子系统”；docker/podman命令不可用。未安装WSL、修改系统或探测无关SSH配置。可用独立环境为仓库已有GitHub Actions渠道（现有public-offline即ubuntu-latest），因此选择公开托管Windows→ubuntu-latest→Windows串行作业，不传输私有数据库/输入/正式检查点/凭据。此渠道存在不代表它已获准承担全量数据建设。

冻结代码3e9e1eaa05324ddb16a62291c79d2217e237b24e，evaluation/tantivy_crossenv_v15.py及tantivy-crossenv.yml。样本完全是public synthetic_fixture，完整成员5个，预期ID[-1,1,2,3,4]；Windows先提交前三个，Linux按原FullCheckpoint/StreamingCheckpoint的prepared journal→native commit→mapping→checkpoint协议续写最后两个，正常wait_merging_threads和关闭。返回新进程全ID/映射/正文与terms hash核验，再由ComponentFactory的fast_v1产品Retriever验证5条固定查询（旧native/并联电容/继电保护、新变压器油温/频率偏差），复用worker并检查资源释放。没有模型、问答批次或生产发布。

两侧拟固定tantivy Python绑定0.27.0、jieba0.42.1、whitespace existing_terms、原schema与position/fieldnorm、writer128000000 heap/1线程/默认merge，未改评分/查询转换。脚本记录实际平台、Python、绑定文件SHA、词典与查询代码hash、native schema；运输使用相对路径文件清单SHA，产品manifest绝对路径只能在接收侧经新验收绑定，不能把旧绝对路径当可加载凭证。

## 实际执行与首个失败

[唯一运行41942205637](https://github.com/7556481/PowerTrustAI/actions/runs/41942205637)，Windows job126965550321；Linux及返回Windows两个job均skipped，未自动重试。实际Windows为Server2025 10.0.26100、runner image windows-2025-vs2026/20261030.294.1、Python3.13.17 x64，pip成功安装tantivy0.27.0的cp311-abi3-win_amd64 wheel、jieba0.42.1、psutil7.0.0。Linux实际版本/绑定SHA/核心格式仍未知，因为尚未运行，不用计划版本代替实际身份。

Windows seed命令08:33:52.772开始，08:33:55.087开始输出清理异常，08:33:55.251以exit1结束（北京时间2026-11-05）。异常路径为fixture临时db.sqlite3，系统错误为WinError32“文件正由另一进程使用”；不是.managed.json替换错误5。

**可确认的本轮程序问题：** seed使用`with sqlite3.connect(fixture.p) as src, sqlite3.connect(root / 'source.sqlite3') as dst: src.backup(dst)`。SQLite Connection上下文负责事务提交/回滚，不负责close；局部src/dst在finally调用fixture.tearDown时仍存活，源库未释放，导致临时目录清理失败。audit中的只读mapping连接也采用相同事务上下文用法，未来验证前同样需明确close；它尚未造成此次已记录清理路径，不混为实际首错。修复边界应是本验证夹具显式关闭各连接、单列主错和清理错，不是更改Tantivy生命周期、ACL或生产依赖。本轮未实施修复/第二次运行。

失败作业仍上传20个文件、15085字节ZIP；artifact13376617914，SHA256 302c85b39103329b7877aafdac08c09ef8f66abdb0b4d3aa794be667e83e9b37，名称crossenv-windows-seed。保留该首次失败现场，不能把有artifact或内部检查完成视作该阶段成功，也不把它传给Linux绕过失败门禁。原始CI日志及公开样本在该运行artifact；无需归档完整CI环境或认证相关日志。

## 阶段判定

| 阶段 | 结果 |
| --- | --- |
| 可用独立CI渠道 | 已确认，仓库既有Actions Linux渠道 |
| Windows小检查点阶段正常结束 | 失败：本轮夹具连接未关闭造成清理Win32/32 |
| Linux打开并按协议续写 | 未执行 |
| Linux正常merge/关闭、返回文件身份 | 未执行 |
| Windows实际Factory/产品Retriever读取返回索引 | 未执行 |
| 跨环境续写兼容性 | 未验证，不是已证明不兼容 |

## 下一次决策所需资料

当前不能建议迁移正式检查点；本轮没有跨环境续写吞吐、传输吞吐或返回产品查询耗时。正式迁移的磁盘、传输量与时间预算不以15085字节小artifact线性外推，不把GitHub托管runner临时空间当作满足160GiB建设上限。先经下一次授权处理公开夹具连接关闭并完成同一小样本链，再根据正式检查点/剩余spool的实际范围、源库可用性、接收端空间与输入身份、传输校验、完整验收成本、保密性和runner时限做单独规划。本轮没有迁移任何正式数据。

正式索引2575674、输入24620947保持，原deadline/账本未改，无第18次，8765不操作，模型调用0；未合并PR #4/#5。只有本验证脚本及隔离workflow、报告和学习站更新。Python编译及文档检查与此次失败CI分别报告，不宣称CI全通过。
