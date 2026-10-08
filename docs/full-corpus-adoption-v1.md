# 完整FTS库日常接入 v1（2026-10-08）

本机日常8765已切换完整发布版本 `kc-c25c9521cb746bef8c725edeb8bfa170efbb44fe5bb431c4d394634215a63a5e`，文件为 `data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3`。完整指70个有效分片14,336,177行全部核算，另3个不可读原发布分片经字节核验排除，不代表全部电力知识均覆盖。去重正文8,630,479条、重复谱系5,705,698条、片段24,620,273个，数据库70,847,647,744字节。FTS全文索引不是全量向量库；原出版社/日期/URL未知的记录保持未知，不升级为规范或工程保证依据。

## 配置与身份

加载完整发布manifest与最终成功记录，确认complete、完整knowledge_version和publication相等；新进程校验数据库SHA-256为 `34154950b460b4c96a53e9ebe74b86c863140b0c03a32e63f6c690cdb7938e41`。日常仍schema13、deepseek-flash、product-decision-v1.5、BM25/aggregate、本地NLI默认关闭；原运行DB、固定本机会话及凭据不变。原部分快照 `kc-5894f664251dad1b93bd791e6f27aca648dd5ef19cdcd0685b92d9b48fad36fa`、构建库和下载分片保留。

## 启动与查询实测

原启动同时全库SHA、quick_check和全表计数，独立验证从08:29:13到08:34:41仍未ready，停止的是本轮无模型任务的验证进程；这不是完成的前后性能对照。最小改动：发布清单必须与库内封印逐字段一致，保留每个新进程完整文件SHA；字节一致时复用发布时SQLite/FTS完整性与成员核验，免除重复SQL全库扫描。未发布合成库仍执行直接SQL检查；命中仍严格回查正文、字符区间和身份。文件stamp变化拒绝，没有持久化跳过SHA的缓存。

独立服务首启约52.02秒，独立离线首次seal51.92秒；同进程再次seal0.000260秒，日常正常重启约43.50秒。没有清OS文件缓存，因此不是物理冷机实验或稳定SLA。每次新进程仍会读取约70.85GB做SHA；启动器等待由40秒延长到30分钟，等待期间不提交任务，不减少鉴权或核验。

|查询（取3条）|耗时秒|Evidence回查秒|
|---|---:|---:|
|变压器|4.760|0.000638|
|电动机|0.199|0.000771|
|输电|0.235|0.000679|
|继电保护|0.110|0.000680|

四题EXPLAIN均为FTS `VIRTUAL TABLE INDEX 0:M1` 和排序临时树，MATCH走倒排索引，非扫描全库正文。SQLite计划的SCAN字样不能单独解释成全表正文扫描。12条命中回查相等，不把命中或相关性当答案准确率。独立服务工作集约53.3MB、峰值68.9MB；日常真实任务工作集约123.8MB、峰值126.6MB，Windows进程工作集不包括全部OS文件缓存。

## 一次真实任务与重启

调用前冻结中文电动机基本作用问题、100字要求、配置和源码哈希；仅一次新run，5请求、73,716token、约49.92秒；生成、提取、事实及领域审核完整执行，0Revision，结果保存。业务处置needs_information/风险unknown：当前政策对未提供结构化engineering_context仍列工程输入/输入单位/仿真边界缺口。此为剩余审核/产品限制，不能归为完整库装配失败，本轮不修协议、不刷结果，也未回退正确接入的库。实际答案和所有审核结果保留在忽略目录。

空闲正常停止并重启后，81条运行request/result/status哈希与runs/events/objects/reviews计数不变；新旧3项API结果逐字段相等，旧部分知识版本及新完整版本Evidence均回查一致，新任务请求数5→5，无补算/重发。浏览器实际检查8765刷新自动连接、中文答案/待补充/来源及重启后同引用原文回查，无手输令牌。749项离线回归通过，56.743秒（包括继承的合成fixture回归重复覆盖）；历史失败不改写。

## 日常启动与回退

双击根目录 `start-powertrustai.cmd`，首次启动需等待完整字节校验，不要因暂未打开页面反复提交。或项目解释器 `python -m backend --open --port 8765`。空闲停止 `python -m backend --stop --port 8765`。本轮完成后日常服务仍运行，验证8771停止；旧配置副本见 `data/runtime_local/full-corpus-adoption-v1/daily-knowledge-before.json`。

回退前确认无活动/排队任务，执行：

```powershell
& .\.venv\Scripts\python.exe -m backend --stop --port 8765
Copy-Item -LiteralPath .\data\runtime_local\full-corpus-adoption-v1\daily-knowledge-before.json -Destination .\data\runtime_local\daily-knowledge.json
& .\.venv\Scripts\python.exe -m backend --open --port 8765
```

若停止请求失败（如仍有任务），不得继续覆盖配置。回退只换固定知识配置，不重发、不修改运行库、不删除完整快照；明确重启后health应为原prefix版本。

## 审阅资料

私有归档 `data/runtime_local/full-corpus-adoption-v1/`：发布身份、四主题逐条Evidence/查询计划、启动/资源、冻结输入、唯一新运行、旧回查、全运行重启哈希、浏览器截图、离线日志及统一ZIP。无凭据、数据库、完整PDF或模型权重。本轮没有训练、迁移、排名调参、审核协议或UI修改；未建立全量向量索引。
