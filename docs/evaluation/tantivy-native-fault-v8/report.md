# Tantivy 长流程原生故障诊断 v8

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
