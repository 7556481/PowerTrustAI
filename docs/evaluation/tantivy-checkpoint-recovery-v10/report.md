# 原版Tantivy有界检查点恢复 v10

接续8b7035a。用户终止签名补丁路线；本轮不加载隔离DLL，不改变系统防护、信任或原版Tantivy0.27.0扩展，不改变分词/schema/评分/merge/成员及模型合同。原生故障未被修复；本轮验证的是失败后可证明安全的检查点恢复。

## 规则冻结

- 正式最多3次故障恢复，计数持久化；连续恢复之间原生已提交数未增加即停止，不重置原96小时绝对期限2026-11-06 11:49:19（北京时间）。
- 后续仅接受限定本轮PID/创建时间、实际索引目录直接捕获的`.tmp*`→`.managed.json` MoveFileExW/5，且无其他未解释的关键原生错误；通用writer killed不足以分类。资源/期限/诊断停止不能改称文件替换故障。
- 用户另外明确授权：原正式685674的第16段旧错仍未知，但在副本受控恢复及正式完整审计通过后，允许其作为一次初始准入，**计入3次上限**。不事后将其标成与v8同因。
- 每次新writer前确认旧writer/Rust合并线程所在进程及监督/观察子树已退出，完成新进程只读审计；失败现场的派生索引、映射、journal/元数据归档，保存原因、前后checkpoint、审计及实际增量。原物理建设目录不搬迁，不把诊断875674并入正式685674。
- 只允许已有精确边界：无journal时native=mapping=checkpoint；未提交journal则native=mapping=start；native=end且mapping=start时仅滚进映射；native=mapping=end时仅完成journal收尾。其他组合立即停止。已原生提交的成员不再馈送。

## 审计覆盖

有界5000批遍历全部原生ID，磁盘SQLite唯一表核对映射及允许的journal集合。逐行核对输入位置、正负ID范围、fragment/body绑定、terms SHA、checkpoint前缀hash和journal完整payload hash；正ID还与原库corpus_chunks只读绑定核对。映射quick_check通过，meta schema、删除状态、opstamp与原子提交边界一致。

依据固定核心directory/footer.rs，检查meta中**每个已提交segment所需的六类文件**（idx/pos/term/store/fast/fieldnorm）：必须在.managed登记、实际存在，逐文件验证JSON footer的版本0.27.0/format7、长度、magic1337及流式完整body CRC32，并保存SHA256。meta/.managed在审计前后必须相同。失败登记的额外未提交文件单列保留，不把它们缺失或半写误当已提交文件损坏，也不自行删除它们。

原schema的terms未stored，不能直接重建每个原生文档的全部词位；本证明覆盖全部输入terms hash/来源绑定、提交ID集合与全部必要文件CRC，不宣称逐项重建了倒排内容。最终全量身份、24题查询质量/性能及既有产品门槛仍须通过。

## 受控恢复计划

唯一一次受控恢复从**已直接捕获替换故障的v8副本875674前缀**复制派生文件，逐文件SHA一致，不复制/重建完整spool。新目录checkpoint-recovery-v10/controlled，只读原输入、原库，先审计再用原FullCheckpoint恢复；仅新增10000（两次5000提交）至885674，最多2小时且受原96h截止。结束后新进程再审计全部已提交ID/映射/输入hash及必要文件CRC。若失败，不自动再做一次受控验证。

沿用原监督Job、deadline、服务繁忙/资源暂停与退出宽限。原850MiB进程树预算内为轻量控制器预留64MiB，段监督的剩余上限扣除该预留，不额外加预算；原派生157GiB计量加3GiB预留、磁盘至少30GiB。观察仅保留失败系统调用与阶段，过滤正常EOF，日志有界；原生行为不拦截、不改写。监督分段进程退出后才进入下一审计，避免观察helper或merge生命周期重叠。

## 当前验证

真实小索引验证native-before-mapping中断后只补映射、全部ID/源输入一致，CRC故意破坏会拒绝；边界、3次/零进度/期限和未知错误拒绝专项通过。新增审计初测发现磁盘seen库未开启URI导致只读attach失败，已在实际受控运行前修正；初失败保留，不作为数据损坏。相关15项通过，不重跑无关完整业务测试。

实际受控结果及正式建设状态待运行后追加。完整输入24620947和正式685674不变，原96h不重置，模型0、8765不操作、PR4不动，PR5保持草稿。所有实际材料在Git忽略的checkpoint-recovery-v10，不覆盖v8/v9现场。
