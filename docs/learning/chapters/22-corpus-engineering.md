# 22 数据发布、事务与稳定原文身份

本专题绑定应用提交 `e4fb27e7c8893a5ad141ebef0ae5f32216648065`，2026-11-24离线核对。配置只看[当前状态](../../current-status.md)。数字分别标记真实实验与教学构造；以下问题不授权现场工程操作。

## 数据究竟来自哪里
[下载器](../../../rag/corpus_download.py)固定数据集 `BAAI/IndustryCorpus2_electric_power_energy`，按manifest revision下载Parquet分片并核验长度与LFS SHA。发布者提供聚合数据，不等于每条正文的原出版机构。记录缺原出处时不能补写“官方”。原文权限、可定位性与权威性分别讨论。
“事务”把一批写入作为整体提交或回滚。以第128条失败为例，不能只把进度推进而漏掉正文；[构建器](../../../rag/corpus_build.py)在同一事务内写正文、身份及下一行断点。`writer_lease`使用OS锁；锁文件存在本身不代表进程还活着。

## 从下载到发布的调用链
下载器的.partial文件先校验再改名；构建器用PyArrow每批128行读取，SQLite WAL、64MiB cache配置和FILE临时存储限制资源。每个批次BEGIN IMMEDIATE，提交后才有可恢复断点。publish显式检查FTS完整性、分片状态与排除记录，再产生备份和内容封印；构建库不直接充当发布库。中断恢复以已提交行号为准，不宣称任何时刻都零重复计算。

::: answer 题22.1：SHA去重之前是否先做空格归一化？
大库add_record直接对原始text.encode()求SHA；未先规范化正文。代码只对空正文做入口拒绝，不把大小写、空白差异合为同文。因此相同字节是精确重复，近重复不自动合并。重复来源写corpus_duplicates并指向canonical记录；缺原ID时构造revision、shard、行号绑定的内部ID，不能把它称原出版ID。实现见[corpus_index.add_record](../../../rag/corpus_index.py)、[source_identity](../../../rag/corpus_build.py)。验证可用两条只差换行的文本，预期不是同一正文hash。继续追问：清洗若改变正文，必须另存变换及映射，不能继续用旧范围。
:::

::: answer 题22.2：损坏分片能不能跳过然后说全库100%？
字节与manifest不符直接失败；字节正确但Parquet不可读记录verified_bytes_unreadable_parquet与排除状态。发布完整性考虑每个声明分片的完成或已核验排除，统计必须另列排除数和实际读入数。完整发布状态不是所有来源内容都可读。代码在[构建和发布](../../../rag/corpus_build.py)，测试见[test_corpus_index](../../../tests/test_corpus_index.py)。继续追问：更换可读副本不能静默沿用旧revision，应重新核验manifest身份。
:::

## 切分不是语义理解
当前大库chunks默认1200字符，后半窗口内尝试句号、换行等边界，无滑动重叠；下一段从上一段end开始。邻接由同一record按start排序得到。公式、表格、跨段例外可能被切开，邻接扩展只能部分补救，不能保证完整意义。PDF/小库有各自切分实现，不能把一个参数推广到所有资料。

::: answer 题22.3：原文范围怎样稳定？启动慢是否意味着每次查询都慢？
Evidence绑定知识版本、来源身份与字符范围，正文要与原始范围逐字一致。seal读取库内manifest并核验旁路清单与整库hash；只读进程已验证身份用文件大小/mtime检测变化。冷启动全文件核验可能很慢，不能记成每次FTS查询成本。发布前完整性检查、启动byte seal、每次命中定位是不同层。参考[seal与邻接](../../../rag/corpus_index.py)、[封印测试](../../../tests/test_published_corpus_seal.py)。继续追问：hash保证相同字节，不保证来源正确、内容真实或检索充分。
:::
