# 控制器固定不可变输入身份：实现与验证

2026-11-04用户批准实施。这里的epoch-v14仅是输入验证版本，不改变生产审核schema13，也不修改Tantivy0.27.0、分词/schema/评分或merge。

## 实现

连续入口启动一个长期存活的输入控制器：先以Windows原生只读句柄打开源库、源sidecar、完整spool、build-identity与input-complete，仅允许其他读者，拒绝写入和删除/路径替换。**不对Tantivy索引、.managed或merge文件施加这种锁**。随后完整验证源库字节seal、全成员范围和24620947条spool的位置/ID/terms SHA及完整元数据摘要一次，保存分段时间与过程状态。

每个原受监管worker按PID及创建时间验证活跃控制器，通过DuplicateHandle复制实际持有的句柄，核对卷/文件ID、大小/写时间等身份及receipt SHA。不是仅凭落盘成功标志或mtime跳过完整验证。每0.5秒检查控制器活跃身份、固定句柄身份及绝对deadline；控制器退出/PID变化、句柄关闭、文件身份不符、receipt改变或停止请求，均拒绝继续。

连续入口持有单独所有权锁，仍由原单次入口持有建库ROOT锁，不允许并行writer。控制器本身受既有64MiB预留、原96h、30GiB磁盘余量和服务忙/内存压力暂停约束；worker监督预算已经扣除控制器预留，未额外增加总内存。关闭控制器后句柄释放；重开控制器必须再次完整验证，旧receipt不能独立获准。

## 每次恢复保留什么

writer仍采用原FullCheckpoint、有限journal、原append/commit/merge等待和一次关闭。恢复前仍使用新进程完整ID/映射/journal/来源绑定和必要组件CRC/SHA审计。worker确认审计文件、当前meta/managed/mapping/journal及必要组件SHA未变，核对恢复后的映射摘要等于审计中的输入前缀，才馈送下一批。

变化在于：改用显式mode=ro读取固定spool，移除该worker路径中的源库整文件SHA及完整未提交spool反复遍历；不再执行StreamingSpool建表DDL。动态检查、原生全部ID恢复证明、来源回查及最终全量身份/查询质量验收保留。无epoch的旧入口仍兼容原完整校验。

## 验证与实际准入

真实Windows合成测试通过：写入/删除/重命名被固定句柄拒绝；子进程能复制父进程句柄；控制器正常退出后即使子进程仍持有文件句柄也拒绝继续；控制器身份或receipt改变拒绝；句柄关闭拒绝。合成完整输入只验证一次，两个原版writer重开均成功，完整ID/CRC后验通过，未调用模型。首轮夹具缺settings表的失败保留，补齐真实KnowledgeStore结构后验证通过；没有修改生产源库迎合测试。相关24专项通过，未手动重跑全业务回归。

正式切换前经现有stop请求正常结束旧段29，正式仍1985674，全部旧worker退出、必要后验通过，旧记录保留。原单次脚本在手动停止后试图读取不存在的原生错误日志导致终态附加FileNotFoundError，也保留；本轮维护停止按精确原因、Expired且清理为空、已有完整后验作专门准入，不重分类为原生故障。

首个真实输入控制器PID8600/创建1793805805.2889643已启动，验证阶段树外控制器峰值约52.5MiB（实测快照），低于64MiB预留。尚在首次完整验证时，不宣称实际恢复时间已缩短或有新增提交。完整输入与当前检查点保留，原96h截止不变，模型0，8765不切换。原子替换故障尚未修复；后续仍按已授权已识别故障/零提交增量/未知故障停止规则继续。

## 操作

仍使用`python -m tools.tantivy_manual_once --continue`。默认status另外显示活跃输入控制器最近阶段及spool校验行数，明确不作为正式提交数。验证进度在忽略存储input-epochs/<epoch>/state.json；有效receipt仅在控制器活跃且句柄可核验时使用。

如需在首次验证阶段停止，在`data/retrieval_local/tantivy-full-fast-v1/input-epochs/stop.json`写停止请求；该标记不会自动清除。已有worker时仍可使用该段stop.json安全停止。停止后先检查记录，不通过删除标记跳过身份检查。

实际源seal、全spool一次验证、后续恢复准入与新增提交耗时待运行记录，不能提前承诺省下37分钟。最终全量验收仍是独立门槛。
