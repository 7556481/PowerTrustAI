# 正式发布、学习站同步与依赖感知清理 v26

2026-11-12，用户明确授权提交、等CI、合并默认分支并直接删除可证无用文件。本轮在既有干净发布工作树、PR #7上继续；起点远端master=3cb0535，本机受管源码eac94b7、文档ee31fc2。原本机8765进程9904保持，0重启、0模型请求；正式数据/凭据/索引不进Git，D:/PowerTrustAI原有3份未提交文档及26项未跟踪材料逐项保留。

## 发布范围和学习站

PR #7只整合v23已验收的事实审核/领域检索重叠、受管显式Factory、日常启动、同Store回退及文档，不合入PR #6/Tantivy实验代码。通用默认component，本机data/runtime_local/managed-service.json明确overlap；SQLite/topic_v4_subject_v1、schema13、Flash、serial_v1、baseline及原预算/审核政策不变。实际进程载入eac94b7，后续提交只改变学习站/文档，不为清理重启。

README保持项目概览，补日常/演示/回退入口及两项成果。学习站首页、16性能、17口述、18运维注明：7个完整的同初稿真实Flash对照中审核终态中位33.48→23.71秒，约早9.8秒（29.2%），发生于初稿之后；Tantivy全库90片/24620947成员已建成，v18四个冻结宽查询速度比中位1.868946、普通Q5—Q8为0.583055，检索候选未替代日常SQLite。历史失败、共同缺陷与首稿生成边界保留。[固定v23报告](https://github.com/7556481/PowerTrustAI/blob/75cbbdd/docs/evaluation/fact-domain-overlap-v23/report.md) · [固定v18报告](https://github.com/7556481/PowerTrustAI/blob/75cbbdd/docs/evaluation/tantivy-shards-v16/query-repair-v18.md)。

源码身份/20章88解析/构建/本地链接通过。实际浏览器打开首页、运维页、N1/A3/N4目标，截图learning-home.png留私有data。发现旧构建器把外部GitHub report.md误改为report.html，已修复为仅转换本地章节链接，7项学习站测试通过；修复后浏览器核对报告href保持.md。学习入口http://127.0.0.1:8770/，根目录start-learning.cmd可复用，静态站与8765分离。一次Playwright点击未可靠导航，改为打开已观测链接目标核对；不冒称该点击成功。

## 必须保留的真实路径

- 正式原文知识库：D:/PowerTrustAI/data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3及同名.manifest.json。
- 正式Store/历史/反馈/每任务预算usage：D:/PowerTrustAI/data/runtime_local/runs.sqlite3及运行中的-wal/-shm；D:/PowerTrustAI/data/retrieval_local/service_private保留诊断。无独立全局批次账本，不套用v24烟测账本。受管managed-service、daily-knowledge、orchestration、认证和回退配置原位保留，不读取/展示凭据内容。
- 90片：D:/PowerTrustAI/data/retrieval_local/tantivy-shards-v16/accepted-shard-group.json、full-reader-manifest-000…089.json及proof，逐片index_path和父目录mapping.sqlite3。精确90项在私有protected-shards.json，实际1661个清单原生文件、90个mapping存在。
- 首片正本：D:/PowerTrustAI/data/retrieval_local/tv-checkpoint-probe11/tantivy及父目录mapping.sqlite3；tantivy-full-fast-v1/build目录联接指向该父目录，不能沿联接递归删除。另一个tantivy-supervision-v3/input联接指向tantivy-stability-v2/input，扫描不重复计数。
- v18必要输入：D:/PowerTrustAI/data/retrieval_local/tantivy-full-fast-v1/spool.sqlite3，53678977024字节。GlobalIDFRetriever._rank每次从input读取候选terms、TF并核验terms_sha/rowid；不是可删构建缓存。本次真实零模型读取已经过该路径。
- 历史报告/日志/输入身份/唯一复现场景、模型及原训练材料保留。外部构建位置C:/Users/37307/AppData/Local/Temp/powertrust-tantivy-probe11-ucqlh51f现为空；项目相关14个外部临时目录扫描文件总字节0，未对外部目录递归删除。

## 已执行删除与空间口径

扫描data目录不跟随联接，清理前83829个文件、169230508349逻辑字节；项目相关外部目录无文件，无扫描错误。私有inventory-before.json及external-inventory-before.json按文件体积排序，不能把两个联接目标再算一遍。

|类别|删除文件数|逻辑字节|
|---|---:|---:|
|旧原生/索引现场中与保留正本SHA-256完全相同的大副本|118|4343862432|
|有对应.py源文件的可再生__pycache__字节码|201|2994888|
|合计|319|4346857320|

逐文件删除前重新核对SHA-256、正本仍存在且不在删除清单、绝对路径位于项目data、所有父目录无联接/符号链接且不属于90片/映射保留目录。全部是叶文件unlink，没有递归删除目标；真实NTFS硬链接数和inode记录在deletions.json。失败现场保留日志/身份及独有文件，大重复块通过“原路径+SHA+保留正本路径”可重建，不保留第二份大副本。

删除窗口D盘free从773163417600增至777510727680，实测净增加4347310080字节（约4.347GB，约4.049GiB）；文件逻辑量4346857320不同于磁盘free增量，后者还受分配簇及同期写入影响，不宣称二者相等。C盘同窗口free减少86016字节，本轮C盘未删文件，不能计作清理释放。跨整轮起止净变化另存final-closeout.json，包含清单、Git/日志等新写入，不拿它冒充精确文件分配释放量。无全库备份或大型ZIP。

## 最大五项（按data下两级、不重叠目录逻辑量排序）

|剩余路径（相对data）|字节|保留理由|
|---|---:|---|
|retrieval_local/industry-corpus-v1|73465514710|正式70.85GB SQLite及原始来源/历史prefix；旧prefix约2.62GB尚未证明身份/内容可完全由正式库替代，保守保留|
|retrieval_local/tantivy-full-fast-v1|56960946517|53.68GB spool是v18实际TF/hash读取依赖；其余保留唯一输入/日志/失败现场|
|retrieval_local/tantivy-shards-v16|16931779578|90片封存索引、映射和验收清单，候选仍可运行|
|runtime_local/cleanup-20261008|3940883853|约3.86GB历史训练环境/旧材料尚未证明可精确再生，不当缓存删除；最大单文件dnnl.lib约2.33GB|
|retrieval_local/tantivy-stability-v2|3309231457|旧冻结spool/不同规模实验唯一输入及复现库，未完成与full spool的逐行等价证明|

上述后三项的历史环境、旧prefix/旧spool是确实未证明可替代的大项，单列保留，不把“当前不走它”当可删除依据。首片tv-checkpoint-probe11约2.88GB虽排在五项之后，仍属于强制保留路径。

## 清理后验收

原8765 ready/Factory overlap/进程9904不变，日常入口只复用现有服务；110条历史、2454 events、3286 objects、8 reviews及预算usage逐表hash不变。正式API读取既有答案和两条引用，经同一SQLite corpus_evidence原文/区间/hash回查完全一致。未发新题、未重放POST。

从75cbbdd提取小型rag源码快照到忽略data，未把实验模块合入默认配置。实际GlobalIDFRetriever零模型检索一次，6根原文、3段邻接/2004字符，证书校验通过，90片/1661文件/90 mapping齐备；检索6.078秒，初始化含来源封印393.051秒单列。初次验证脚本误传isolated参数，在构造前/发查询前失败，按原签名修正后唯一查询成功，失败回执保留。v18原生worker正常关闭，正式服务不受影响。

逐文件清理清单、剩余排序、磁盘时间窗、引用与v18回执、未提交材料保护清单均留data/runtime_local/closeout-v26。最终默认分支合并SHA与独立远端核验、CI、整轮磁盘净变化写final-closeout.json，不提前把PR已提交当合并完成。
