# Tantivy 长流程原生故障诊断 v8

最新结论：真实故障已复现，首个因果文件错误为`.tmp→.managed.json`原子替换的MoveFileExW/Windows5，早于Python主错3.014ms。真实阻塞持有者及底层NT状态仍未知，未选择猜测性行为修复，正式建设不恢复。正式685674，诊断副本875674，模型0。下文保留前置失败及纠正授权过程；最终事实见末节。

接续c21851a与草稿PR #5。正式进度685,674；完整24,620,947输入已准备，不重新分词或准备。原库只读，模型0，8765不重启/切换，PR #4不变。本页不是全量恢复或故障根因关闭回执。

## 已确认的错误传播缺口

固定绑定0.27.0，官方tag提交8ce402400ad7d879d46e69055901e2c9ceafc9e7。`src/index.rs`的add/commit/wait将核心错误转为Python错误；未发现注册Rust日志接收器。单独设置RUST_LOG不能保证得到日志，RUST_BACKTRACE只对实际panic有用，不会把普通Result错误补成回溯。

核心[0.27.0 index_writer.rs](https://raw.githubusercontent.com/quickwit-oss/tantivy/0.27.0/src/indexer/index_writer.rs)：worker中`index_documents(...)?`返回原始错误并使writer状态失效；继续add遇到关闭通道，只留下通用killed。`wait_merging_threads`第329–338行通过忽略原错误的map_err产生通用Worker thread failed；prepare_commit第575–596行则保留线程返回的原始错误。此前隔离失败脚本额外调用一次commit，走后者，所以取得Windows5；正式路径未额外commit，最后只看到通用错误。这是错误可见性差异，尚不是writer失败原因。

本轮不在原失败索引追加诊断commit，不改变提交结果，不禁用merge。新增add层记录；阶段finally保留正在传播的主异常，清理失败单列，不再用RuntimeError遮住原ValueError。只有正常停止伴随清理失败时仍强制失败，不能虚报成功。

## 正式流程与诊断的核对

| 项目 | 第16段/既有简化诊断 | 本轮有界长流程 |
| --- | --- | --- |
| Python/扩展 | 均指定D盘现有venv、固定T0.27.0；旧进程已退出，历史实际加载DLL哈希未记录，不能追溯补造 | 冻结sys.executable、实际process_exe、Python版本、扩展路径/SHA、账户/cwd |
| 生命周期 | 正式：源封印→全spool/映射核验→有界native恢复证明→writer→每5000 commit→一次merge关闭；简化诊断预读5000后直接建writer | 复用正式supervise/full_stages/FullCheckpoint，包括完整输入核验及同一提交/关闭顺序 |
| 路径 | 正式build为junction到tv-checkpoint-probe11；成功诊断另目录/副本 | 只复制派生检查点并逐文件SHA核对，物理独立目录；路径变化是已知复现限制，成功不算修复 |
| 进程/Job | 既有监督记录launcher及子树；Windows venv入口可能是redirector | 先由实际worker写PID+创建时间，再证明为本次launcher/子进程后附加；原Kill-on-close Job不变 |
| 文件占用 | 旧故障时的其他进程句柄无完整记录 | 启动前仅对该索引69文件作Restart Manager只读查询，点观测无持有者；不保证未来无短暂句柄 |
| 异常顺序 | add通用错→wait通用错→finally顶层RuntimeError | 原生文件边界即时日志→add主错→独立wait错误；主错继续向外传播 |

## 原生文件诊断，不替换生产依赖

官方Frida17.25.2只装在忽略的native-diagnostic-v8/deps，不修改venv。当前PATH及标准目录未找到Rust/链接工具链，本轮优先使用用户授权的限定文件访问跟踪，未制作或替换Tantivy二进制。绑定源码留在同一忽略目录作审计。

仅附加本次经PID/创建时间及父子关系核验的实际worker；路径过滤为副本native索引目录。捕获NT/Win32创建、读写、flush、文件信息/rename、关闭，保存阶段、线程、操作、路径、NTSTATUS和Windows码。普通模式不改参数、返回值、系统错误或异常处理。现有panic hook及完整stderr保留。原生文件内容、完整环境、密钥和请求头不采集。

文件事件最多32MiB，失败事件另8MiB；写入只汇总次数/字节，不记录内容。诊断失效或达到日志上限即请求停止，不能无观察继续。正常不存在探测、EOF或锁竞争也可能产生失败系统调用；raw失败记录不是自动根因标签，必须结合阶段、线程、主异常、时间顺序判定。纯Rust业务Result错误若不伴随I/O或panic，文件跟踪仍不能保证恢复其完整Rust错误链，不能据此解除恢复门禁。

短测保留所有调试失败：short首次附加launcher后被身份检查拒绝；修正实际worker握手后，合成.pos目录冲突保存NTSTATUS C00000BA/WinError5，在Python通用主错之前约2ms记录，清理另列。正常短测先发现只挂Win32 WriteFile不能证明真实写入，补齐Rust实际使用的NtWriteFile/NtClose。最终negative与positive短测通过，positive实际记录15个写入文件、正常commit/merge/关闭。合成故障不充作真实故障复现。只读审计专项曾发现SQLite URI接线和异常关闭问题，已在长流程前修正，失败日志保留。日志失败/主错保留/一次清理/全成员重复拒绝及既有监督专项22项通过；不重复1458业务回归。

## 唯一长流程冻结

使用经SHA复制的685,674派生检查点，完整源/输入/映射校验后沿正式路径运行。现成spool用mode=ro打开，不复制50GiB输入、不重新准备。副本最多新增1,000,000至1,685,674；最长7200秒，包括复制、全输入核验、暂停、merge/关闭与观测空窗；还受原96小时绝对期限限制，先到即停。一个writer，128000000 heap、1索引worker，原merge策略/线程默认不变；树内存891244544bytes、现有157GiB计量+既有3GiB外部预留、磁盘≥30GiB，原忙碌/压力安全点沿用。不自动重试。

计划、代码/扩展/跟踪依赖身份、进程、检查点副本哈希及结果在忽略目录native-diagnostic-v8/long。原construction-ledger追加diagnostic_runs，原deadline不变；原checkpoint/输入/失败记录保留。副本新增数不写正式进度。正式建库仍暂停。长流程未到writer，结果见下节；不能把启动或短测成功写成根因已修复。

只有取得真实原因及针对性修复证据、同长流程验证通过、原检查点再审计且预算足够，才可恢复。若未复现，记录覆盖量/生命周期后结束本轮，不能宣布修复或无限正式重试。

## 本次受控运行结果：工程前置失败，真实原生故障仍未知

冻结d5fb5a4的worker阶段实际226.085秒，12:38:48停止。源封印校验后，SQLite attach复用spool使用了诊断副本ROOT.parent下不存在的路径；这是本轮诊断适配遗漏，不是旧原生writer原因。writer尚未创建，跟踪仅source/input verification，native文件操作0，新增提交0。原正式及副本提交均685674，原checkpoint SHA未变；本次没有得到有效的原生长流程复现或未复现结论，也未覆盖馈送、commit、merge。

观察树峰值273629184bytes（约261MiB）；跟踪附加有6.475秒空窗，不能声称连续资源无异常。result.json的exit_code为1，但原协调CLI未传播该值而返回0，已补修；原回执不覆盖。原最早错误在control/events.jsonl及logs/stderr.log，控制层primary为空仅代表协调器自身没抛错，不能当worker无异常；新代码单列worker_primary。

接线修正为显式绝对reuse_spool、mode=ro，并在源扫描/原生writer前校验；原正式入口默认路径不变。新增实际小型诊断副本贯通及缺失路径拒绝专项通过，相关10项通过，失败测试/实际运行均保留。未再启动同配置或自动改deadline；因用户明确只允许一次长流程，已询问是否允许在本次原绝对截止14:34:46内纠正运行，未获答复前不执行。原96小时截止为2026-11-06 11:49:19，北京时间；终止审计时约71.09小时余量，之后继续按绝对时间扣减。

当前真正修复的是诊断链、主错可见性和诊断入口接线；没有修复经证实的原生根因。正式建设不恢复。尚需验证的假设：历史Windows5说明曾有文件创建拒绝，但第16段未知；简单短窗口/目录成功不能排除长流程状态或瞬时文件访问差异；无panic/低RSS也不能排除未观测的原生分配/句柄/提交额度问题；点时69文件无其他持有者不证明历史无并发访问。只能用可靠原生首错与对应上下文缩小，不换目录追成功、不归罪于引擎或安全软件。

证据路径：native-diagnostic-v8/long/{control/plan.json,copied-checkpoint.json,result.json,termination-audit.json,trace/files.jsonl,logs/stderr.log}、path-preflight-checks.txt、offline-checks-qualified.txt。所有实际材料留忽略存储，源库只读、模型0、8765未操作，PR #5保持草稿，不合并PR #4。

## 提交与核验回执

诊断冻结实现d5fb5a4、入口修正39d8b80均已推送PR #5，两版本各四CI检查全部success。39d8b80之后仅同步文档回执，不改变受测代码；不合并、不关闭检查。本机22项先前诊断/监督专项及路径修正后10项专项、学习站20章/88题源码hash/链接检查通过；原始失败日志均保留，没有手动重复全套业务回归。

2026-11-03 13:11北京时间再核验：本次记录的隔离PID均已退出，正式685674、完整输入24620947，原累计绝对预算余70.634小时。无后台待续写、无模型请求、无8765重启/配置切换。有效原生长流程仍未完成，待用户对一次纠正运行回复；不把CI或短测成功视为根因关闭。

## 2026-11-03 已获准一次纠正运行，原期限不变

用户已明确回复“允许一次纠正后的长流程”。只允许原物理副本、原685674前缀，复验全部已复制文件SHA、确认此前未进入native/写入0后准入；已进入馈送、文件变更、已纠正过或原两小时到期均拒绝。保留旧control/logs/trace/result，另记corrected-*；绝对截止仍为2026-11-03 14:34:46，不重新复制输入或重置96h，不自动重试。纠正准入及路径专项11项通过。真实结果待本次运行结束，尚未恢复正式建设。

## 真实长流程最终结果（1c8c9b7）

用户明确允许一次纠正运行；同一物理副本、同一原两小时绝对截止，旧结果不覆盖，corrected-*独立保存。没有再次复制50GiB输入，spool以mode=ro打开，没有重新分词。原正式685674检查点SHA未变。

| 阶段/结果 | 实测 | 范围 |
| --- | --- | --- |
| 实际worker阶段 | 2228.700秒，约37分09秒 | 含跟踪准入和关闭 |
| 源、完整输入与映射校验 | 2179.589秒 | 合并阶段标记间隔，不能拆成精确子项 |
| 原生前缀恢复与writer创建 | 8.193秒 | 含685674有界ID证明及创建，非纯open计时 |
| 首次feed至首个致命文件错误 | 37.695秒 | 含Python校验、38次native commit及映射检查点；不是纯writer内核时间 |
| 诊断副本已提交 | 875674，新增190000 | 第39批[875674,880674)失败；不计正式进度 |
| 新进程只读重开/全部ID审计 | 15.64秒 | 全875674唯一且等于映射，位置/正负ID范围/映射hash与checkpoint一致 |
| 未提交5000条 | 与原spool元数据及terms SHA一致 | 只读，不重投，不补commit |

### 首错与传播

北京时间13:55:13.058，worker PID6740、创建时间1793683083.882902，线程14012，序列4016：MoveFileExW将`.tmpfXccu2`替换为`.managed.json`失败，WinError5。前一次同线程替换在2ms前成功；失败临时文件写入1602bytes，且记录到该写句柄关闭，之后由原tempfile清理删除。日志没有注入故障（inject_pos_failure=false），没有修改API参数/返回值/merge。

13:55:13.061出现add_document的writer killed，晚3.014ms；随后wait_merging_threads报Worker thread failed。新阶段finally保留原ValueError向外传播，join错误在native-errors与stage_closed单列，协调CLI返回1。与旧只剩RuntimeError或join错误相比，诊断链这次确实捕获到了更早操作。

限定PID/索引路径范围内，失败系统调用分类为179次NtReadFile EOF（WinError38，read_to_end的正常末尾）和1次上述MoveFileExW/5。EOF原始记录保留，不当作导致worker终止的错误。实际Move没有对应的低层NT rename返回记录，NTSTATUS未知，不能用合成.pos测试的C00000BA或推测的ACCESS_DENIED状态补填；也未捕获故障瞬间目标读句柄及共享模式。

### 原因缩小与仍未知之处

固定核心tag0.27.0提交67889269cae67063c372bc236b102d632a021568：[ManagedDirectory](https://github.com/quickwit-oss/tantivy/blob/67889269cae67063c372bc236b102d632a021568/src/directory/managed_directory.rs#L285)在open_write前登记片段，[MmapDirectory atomic_write](https://github.com/quickwit-oss/tantivy/blob/67889269cae67063c372bc236b102d632a021568/src/directory/mmap_directory/mod.rs#L362)写/flush/sync临时文件后persist替换.managed。注册中的IO错误同样包装为待建片段的OpenWriteError。因此，历史诊断的.pos filepath不能证明底层就是CreateFile(.pos)失败；旧报告的具体系统调用表述应收窄，旧原始错误不覆盖，本次也不反推历史为同一操作。

本机一次合成文件试验：无读者时MoveFileExW成功；持有读句柄时，无论share mask7（含DELETE）或3，均返回5，释放本测试自有读句柄后成功。没有操作用户程序或真实索引，也没有引入自动重试。这证明旧替换语义可被读句柄触发同类错误，不能证明本次实际有谁持有.managed。

本轮进程仅在初始加载时出现一次.managed读打开；没有记录后续读打开。副本写入前67文件的Restart Manager点查询无持有者；原目录69文件也无持有者，均不是故障瞬间的证据。故障后.managed为普通Archive属性32、无readonly位。13:54:50–13:55:30内未找到关联该PID/索引的Application或Defender指定错误事件；这不排除其他文件过滤或短暂访问。

| 剩余假设 | 直接证据 | 缺口 |
| --- | --- | --- |
| 短时读句柄与legacy替换语义冲突 | 本机合成试验可产生相同5，释放后成功 | 实际故障瞬间持有者、share mask及关闭时序未知 |
| 文件过滤/访问上下文变化 | 实际替换返回5，相邻替换成功 | 没有归因到具体过滤器/程序，不能归罪安全软件或修改ACL |
| 原生资源因素 | 树峰值约601MiB、无资源stop，直接错误是文件替换 | 无故障瞬间系统commit/句柄额度快照；低RSS不作全面排除 |
| 固定输入错误 | 同窗口新索引成功，本次前38批成功 | 不支持稳定输入错误归因，仍不泛化为任何输入均安全 |

没有足够证据选择一个经验证的实际行为修复。本轮未加metadata重试、未切T版本、未关闭merge、未改变分词/schema/评分；相关维护者的Windows替换兼容方案只能作后续源码对照，未直接采用。剩余最小动作是取得该原子替换的句柄/共享模式、底层rename结果和故障时上下文，再选择一次针对性修复；不再自动长流程或转检索研究。

### 完整性、资源与停止决定

只读审计以5000批遍历全部875674原生ID，SQLite磁盘唯一表拒绝重复，集合与映射相等，映射hash490667af6ab38d613a03d805a473b608dcfab6f152fe86768ffc353c99995078。原有负674/正ID范围、位置及checkpoint绑定通过，待提交5000的spool/hash也通过。该proof明确标scope=diagnostic committed prefix、failure_unresolved=true、approved_for_resume_or_service=false，不把可读前缀写成完整/可服务索引。

已观测树峰值630198272bytes（约601.0MiB，低于原850MiB护栏），派生计量峰值57758289158bytes（约53.79GiB，含旧spool/保留现场，非本轮净增），最低采样系统可用内存1204801536bytes。连续心跳最大间隔0.731秒；启动跟踪附加在首次心跳之前，不能称全程无采样空窗。实际日志约1.52MB，失败调用约64KB，未触及32/8MiB日志上限，无stop.json。14:21收尾可用磁盘约742.49GiB。原96h账本截止2026-11-06 11:49:19不变，余约69.46h并继续扣减；原两小时诊断截止14:34:46未重置。

只读前缀可核对，不等于故障修复。首个系统操作已可见，但实际阻塞来源/修复与同长流程通过尚未成立，因此不恢复正式建设、不再复制/搬目录重试。所有本次隔离进程和协调CLI已结束，原库只读，8765未重启/切换，模型调用/项目usage0。PR #4不动，PR #5保持草稿。

运行1c8c9b7四CI检查均success；新增atomic-sharing-probe仅为本机短验证，未变更生产路径。本轮初期22相关专项、路径修正后10项、纠正准入后11项按影响执行；不是新增模型或业务全批次。完整输入、首次前置失败、真实故障、合成测试及证明均留既有忽略存储，不提交原始输入输出。
