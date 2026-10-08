# 迁回旧电脑：只读准备清单（2026-10-08）

本轮没有复制、备份、删除、下载、重建索引或训练。旧电脑目标路径/空闲空间尚未实测；实际迁回另行授权。私有路径与逐文件大小盘点在忽略目录data/runtime_local/release-freeze-v1/migration-inventory.json；本清单不包含凭据内容。

## 已盘点与旧迁移包差异

实际旧包位于项目根PowerTrustAI-migration-20261005-091606，其manifest对应27ec89858480cd92c00e48ffa3bdc5f315936894。当前已排除环境与明显凭据路径的data盘点9,720文件/189,526,975,279字节；其中4,762路径不在旧manifest、1个旧成员大小改变。同大小不表示同哈希或未改变；复制时须对选定成员重新SHA-256比对，不只用时间判断。四个synthetic_fixture临时目录ACL不可读，本轮明确留盘点缺口，不改权限、不当必需历史材料。

旧包之后新增的重点不是重新迁移旧数据：中文原件/抽取与basic-coverage、完整industry-corpus及旧prefix；support-nli-review-v2确认事件/监督69、新划分及support-nli-expanded-v3训练和SSIAG留出；本地NLI模型profile/诊断、schema13/14对照、日常运行/反馈与service_private原请求响应、完整库接入及性能验收。原pending/旧标签、旧实验失败与旧模型保留，不能只复制最新审阅ZIP。迁移对象清单必须在正式停机时再刷新，日常新运行会使本次清单过时。

## 对象、是否必需及处理方式

| 类别 | 对象 | 恢复要求 |
|---|---|---|
| Git源码与学习站 | origin/master最终冻结提交、全部tracked源码/锁文件/Markdown/站点/启动脚本 | 克隆或Git bundle，核对origin/提交；不要带旧.venv或历史独立仓库混入 |
| 当前完整发布FTS | data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3及同名manifest.json；build-completed-verification.json | 发布库70,847,647,744字节，精确SHA 34154950b460b4c96a53e9ebe74b86c863140b0c03a32e63f6c690cdb7938e41；完整知识版本kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e |
| 历史知识版本与来源 | published-prefix-v1/v2（合计约2.62GB）、official-pdf/basic-coverage/zh-daily/semantic等SQLite；knowledge_local及相应原件/manifest/版本配置 | 历史Evidence需要历史库；不能仅保留当前完整库。历史vector只作为匹配历史版本的可选资源 |
| 运行与反馈 | data/runtime_local/runs.sqlite3；其他私有实验运行SQLite；data/retrieval_local/service_private及实际请求/响应/归档 | SQLite备份保存runs/events/objects/reviews；反馈、版本及请求数比较；原始响应含私有文字，非公开发布 |
| 监督与实验 | support-dataset/review/finetune/nli各版本、家族/分配/confirmation事件、预测/指标/训练日志；semantic/reranker及失败审阅记录 | 保留原pending和确认版本，不再补标、重预测或训练；仅环境锁文件，不带虚拟环境 |
| 轻量模型与配置 | MiniLM官方固定revision模型约328.5MB、expanded-v3 epoch1约328.5MB、Tiny各起点/检查点约17.5–17.7MB；tokenizer/config/label映射/model哈希及服务端profile | 核对权重SHA和实际revision；CPU，独立训练环境按锁重建。NLI默认关闭，不把模型路径交给浏览器 |
| 配置 | daily-knowledge.json、新旧快照回退配置、NLI model-profile及锁文件 | 新路径只改新配置/环境变量；不批量改历史请求、task或实验哈希 |
| 可选保留 | 原始下载分片40,643,467,106字节、构建库70,847,647,744字节、RoBERTa候选约1.426GB、重复导出ZIP/初始检查点 | 新机原件继续保留；迁回日常不必再下载/重建，也不必复制整个构建库。是否迁回这些存档由用户决定 |
| 排除 | .env、访问令牌、会话/票据/进程状态、请求头、.venv/training-env、缓存、WAL/SHM | 密钥旧机本人填写；旧令牌不复用，由服务新生成。不复制WAL/SHM代替SQLite一致性备份 |

## 空间预算（GB为十进制，非压缩后估算）

已盘点全部可选存档约189.53GB（176.51GiB），未计虚拟环境/源码/4个不可读临时目录。排除构建库、下载分片、RoBERTa候选、WAL/SHM后，保守保留其余当前数据约76.59GB（71.34GiB），含历史prefix、轻量模型和实验。运行库主文件约140.32MB，未把活跃WAL大小当作备份后大小保证。

建议旧机目的盘至少100GB可用用于日常+历史材料；如果备份暂存与目的库同盘同时存在，建议至少160GB再加环境与余量。若包括所有可选原分片/构建库，建议至少210GB；同盘再完整暂存一份需约400GB。正式迁移前按实际备份后大小重算，不能保证ZIP能有效压缩SQLite/Parquet/权重。当前新机D盘约273.62GB可用，旧机空间未知。

## SQLite一致性与身份

正式执行时先确认没有活动/排队任务，正常停日常服务及需要迁移的写者，避免复制半事务。运行/反馈和可写实验库采用sqlite3.Connection.backup()，或在确认所有写者退出且已完成checkpoint后复制主库；不要分别拼接运行中的主库和WAL。备份后quick_check/integrity检查、行数/版本/反馈与关键Evidence回查；计算备份文件SHA并写新迁移manifest。

不可变发布库要求精确字节SHA与既有manifest一致。可先SQLite一致性备份作保全，但backup输出可能改变页布局，**不能给不同字节文件沿用旧发布manifest**。正式停服且确认发布库无写事务/WAL待提交后，精确复制发布主库和同名manifest，核对已有SHA；若backup输出字节改变，保留为备份而不是直接用旧manifest启动。旧历史库同样核对知识版本。绝不忽略校验、关闭SSL或重造身份。

## 恢复顺序与验收

1. 确认旧机目标路径、空间与CPU，Git恢复最终提交；核对配置与依赖锁，重建Python3.13项目环境及需要的独立CPU模型环境。
2. 精确恢复当前发布库/manifest/成功核验记录、历史知识库及原文定位资源；校验文件SHA、数据库身份、K和FTS索引，不建全量向量。
3. SQLite一致性恢复运行/反馈和实验库，恢复监督/模型/原始响应记录；恢复新配置路径。凭据由本人填写，不从迁移包复制。
4. 通过普通启动入口加载完整库，等待现有全SHA打开校验；只读ready、不同主题检索与历史Evidence回查，检查新旧运行/回答版本/反馈和请求数。此准备清单不授权模型付费验收。
5. 检查新自动连接/手动故障入口，重启无重发；保留回退配置与新机原资料直到用户确认。回退只能选已核验旧快照并明确覆盖缩小，不能悄悄改历史K。

## 用户待决定

旧机路径/磁盘与是否迁回全部原分片、构建库、RoBERTa和重复ZIP；迁回前何时停服做一致性备份；是否接受限定学习/演示首版的已知误放行和耗时限制。长期Markdown学习站及个人面试表达后续共同补充，冻结不自动开启新开发。
