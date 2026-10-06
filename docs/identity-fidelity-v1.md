# 英文身份与提取忠实性收尾 v1

接续 a898e34，本地/远端一致，初始工作区干净。本轮仅兼容英文身份和澄清提取忠实性。私有输入、输出、源码冻结、日志和审阅包在 data/runtime_local/identity-fidelity-v1/，历史结果不改。

## 身份与续建

剩余54片逐片读取Parquet schema：51片可读，全部无 _id；3片仍是此前核对发布字节后确认的尾部损坏片，不下载或修造。原中文7,373,300行断点保留。

rag/corpus_build.py 的 source_identity 保留实际非空原ID；缺失时使用命名空间 industrycorpus2:row-v1: 加 SHA-256，身份输入为固定revision、完整分片路径、从0开始的原始绝对行号。跨128行batch、跳过已提交行和重启不改变身份。corpus_identity 另存内部ID、revision、正文SHA、original_id_missing=1及身份协议；重复正文也保留其原行身份，并通过既有corpus_duplicates关联规范正文。未知原始机构、URL、日期不编造。Evidence增加原ID缺失/内部身份警告；既有中文ID、片段ID及去重行为不变。

构建新增操作系统非阻塞写者锁，崩溃自动释放锁，不需删除锁文件。错误时关闭SQLite连接；每批正文、FTS、身份和断点同一事务，失败整批回滚。确认无写者后启动唯一逻辑写者；venv父/子进程属于同一次启动。实际英文原行0/127/128/255/256的身份、正文哈希回查通过。完整库尚未完成，实时提交值见私有build-progress.json/build.log，未新发布完整快照、未切换日常固定kc-5894…部分快照。

当前后台包装入口 data/runtime_local/identity-fidelity-v1/continue-build.py：续建后核对SQLite、全部规范正文哈希、内部身份/重复谱系和全部片段区间/身份，再调用既有不可变发布机制。FTS完整性、封印和原文回查通过后写build-completed-verification.json。计划独立发布 data/retrieval_local/industry-corpus-v1/published-complete-identity-v2.sqlite3，覆盖定义明确排除3个已核验不可读片；文件出现本身不代表最终核验通过。目前无完成记录，不宣称完整交付。遇错误停止并保留日志/断点，不循环重启。

公共恢复入口仍为 python -m rag.corpus_build，使用原 --base、--base-knowledge、--database、--manifest、--shards 参数。当前精确参数留在上述包装脚本。必须先确认没有写者，不清空、不重复下载、不另起并行进程。当前仍在运行，不执行恢复命令。

## 忠实性与事实支持

旧repair运行664d2f…两个uncertain理由涉及“可能过度表述”和“来源归因不同”。已核对原回答、冻结proposition和实际原响应并保存对应关系。忠实性比较回答原锚点与提取命题的立场、否定、条件、数量、因果主体/方向和义务；不是拿命题与Evidence比较。错误回答也可能忠实提取，来源不支持/归因不同属于事实支持。真正提取异议和等价不确定仍保留，程序不猜语义、不强制faithful。

提示独立版本 evidence-verification-v9.12-answer-target-fidelity-boundary；schema13、v9.11输出契约、support-relation-v5及independent-review-projection-v2派生计算不变。未改一次Revision资格和政策；历史响应、提示和失败不回填。

公开synthetic_fixture使用生物、交通、地质三种主题：忠实提取错误答案→contradicted；正确回答的限定被提取丢失→保留disputed/有效not_assessable；忠实正确目标→正常supported。另有稳定身份、跨batch、故障回滚、恢复及唯一写者回归。这是接口验证，不是模型语义准确率。完整678项离线测试通过。

## 唯一真实验收与首版限制

原功率因数问题、122字符旧答案和原引用范围不变，只正常提交一次，新run ab338c35ba86422c80e7be65759b9583。4次请求、50716已记录token、18.089秒，0契约/执行问题，1回答版本、1轮双审、0Revision。

两个因果组件本次均faithful/insufficient_evidence：来源把电压波动、谐波增大归于补偿选择使用不当，不能当成低功率因数本身的直接后果。但模型修复建议均null，未满足原文绑定修复资格；原引用2条件必要性仍uncertain。最终人工复核、风险未知、部分解决。原引用模型仍倾向反向支持，原始supported与程序有效not_assessable分别保存。原引用1必要条件没有在正文明确保留，程序有效insufficient。

未伪造修订后答案或重审，没有额外运行正常/工程题，没有换题重跑。**自动Revision仍为首版未验收能力**。原引用误判与语义限制继续保留，不无限延长本轮。

实际浏览器核对答案、引用、未解决原句、执行与业务分离；同8765自动会话无手输令牌。正常重启后旧repair和本次新run原结果/快照、请求数、NLI记录和Evidence回查一致，0重发/补算。NLI仍可选、默认关闭、原门禁不变。

日常双击 start-powertrustai.cmd，自动连接 http://127.0.0.1:8765/ 。停止用项目Python -m backend --stop --port 8765。交付时服务和唯一语料续建保持运行，停止新增开发，交所有者试用。长期Markdown＋本地学习站手册要求保留，本轮只记录身份/事务、忠实性与事实真值分离及实际未修订原因。
