# 本机手动查看与单次续建

仅适用于当前机器和既有检查点。入口复用原监督、身份/后验和原96h账本，不调用模型或启动8765。依赖忽略存储的既有一次性入口模板及实际审计，不是可在新克隆中独立建库的工具。

在PowerShell执行：

```powershell
Set-Location 'C:\Users\37307\.codex\worktrees\stable-release-integration\PowerTrustAI'
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -X utf8 -m tools.tantivy_manual_once --status
```

查看正式已提交数、最后一段账本状态、实际worker身份及剩余原预算。只有已提交数增加才算建库进展。账本running与进程存活分列，不把旧回执当作当前运行证据。

你决定额外运行一次时执行：

```powershell
& 'D:\PowerTrustAI\.venv\Scripts\python.exe' -X utf8 -m tools.tantivy_manual_once --run-once
```

该操作本身就是本次额外一次执行指令。工具检查前次结束、已识别.managed替换故障、完整后验、原进程退出及当前提交边界；随后原一次性入口再确认相关文件SHA与审计一致。生成唯一编号的执行脚本/记录，保留原3/3和历次额外授权，原96h期限不重置；已有脚本、未知错误、审计不符、过期、仍在跑均拒绝。每次只运行一次，结束后不会自动继续下一次。不要删除拒绝标记或旧记录以强行重用入口。

保持运行终端开启，另开一个PowerShell用--status查看。现有入口可能先花约37分钟做源/完整spool校验，期间终端少有输出，这是尚未改进的成本。机器休眠期间停止工作，恢复后仍按原绝对期限判断；休眠/观测空窗不能当有效工作时间。

如需请求安全停止，在另一窗口先进入同一工作目录，再执行：

```powershell
$root = 'D:\PowerTrustAI\data\retrieval_local\tantivy-full-fast-v1'
$ledger = Get-Content -LiteralPath "$root\construction-ledger.json" -Raw | ConvertFrom-Json
$segment = $ledger.segments[-1]
if ($segment.status -eq 'running') {
    '{"reason":"operator_requested_stop"}' | Set-Content -LiteralPath (Join-Path $segment.control 'stop.json') -Encoding ascii
}
```

这是现有监督的停止请求：等待当前安全点/关闭及必要后验完成，不直接杀未知PID或关闭终端。若停止后结果不满足已识别故障与完整后验，通用入口会拒绝再次启动，需检查具体记录；不得仅删除stop.json继续。Ctrl+C/关闭窗口不代替这一正常停止流程。

2026-11-04准备入口时，第5次运行1065674→1090674，新增25000，随后替换5并完成后验；全部旧进程已结束。此次只验证--help、--status、内存中准备及拒绝条件，没有启动第6次。当前绝对期限仍为2026-11-06 11:49:19（北京时间），到期后需另行决定新预算，工具不会自动延长。

## 连续续跑（2026-11-04用户授权）

用户已授权在现有预算内持续运行，不再逐次确认。执行`python -m tools.tantivy_manual_once --continue`，使用同一项目解释器和工作目录。每次仍调用原单次监督/后验，无固定重启次数上限；原96小时截止、磁盘/内存、单writer、来源/检查点审计、未知故障及故障零提交增长停止保持。正常PauseCheckpoint退出0、清理为空、无stop请求且完整后验通过时允许继续；不再错误地要求它必须有Windows5失败字段。

此命令与--run-once/--status互斥；不要并行启动第二个连续入口。需要停止时按上面的stop.json流程，连续入口遇到该停止结果也会退出，不会自动清除用户stop请求。当前正式目录核验1985674/24620947，约8.1%；完整spool准备不等于索引建库完成。第12次是正常资源/服务暂停，零新增并非原生writer再次失败。已启动第13次，未调整系统审批/防护或原生引擎。
