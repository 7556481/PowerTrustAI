# GitHub基线上传：本轮诊断与恢复

2026-10-04。仅操作 `D:/PowerTrustAI`，不操作旧项目。当前分支 `master`，本地基线提交 `3d5e0cd842a1039731aafb209fb5444bd1905622`，origin 为用户指定的 `https://github.com/7556481/PowerTrustAI.git`。218个明确文件已核对暂存和全部历史blob，凭据、data、模型、官方全文、数据库及旧仓库未进入提交。

## 实际诊断

- 未发现普通Git HTTP/HTTPS代理、该仓库URL专属代理或当前任务进程中的相关代理环境变量。
- 系统Git使用schannel；未关闭SSL验证，未修改全局代理。
- TCP443探测曾成功，但无认证HTTPS curl仍返回连接重置和HTTP000；这不证明TLS握手完成。
- Git默认、HTTP/1.1、仅本命令清空代理的只读ls-remote均连接重置；schannel查询还出现连接超时。
- 尚未到凭据登录步骤；不能据此判断密码错误、仓库为空、仓库私有或不存在。
- 0次推送，尚未设置upstream，不强推、不改远端、不打标签。

可以确认失败发生于访问GitHub的网络连接阶段。具体是本机防火墙、网络路由、代理客户端或上游连接问题，现有证据不能唯一确定。代理值若存在只记录协议/主机/端口及“凭据已隐藏”，不输出实际用户名、密码或Token。

## 用户在本机恢复

1. 用浏览器检查GitHub是否可访问，确认现有可信网络或代理客户端状态；必要时切换能访问GitHub的网络。浏览器可达不保证Git走同一路径。
2. 本机PowerShell运行以下无凭据只读检查，不加详细请求头日志：

```powershell
Test-NetConnection github.com -Port 443
curl.exe --silent --show-error --connect-timeout 10 --max-time 20 --output NUL --write-out "HTTP=%{http_code} TLS_verify=%{ssl_verify_result}" https://github.com
git -c safe.directory=D:/PowerTrustAI ls-remote origin
```

3. 若已有本机代理客户端，核实它实际提供的HTTP或SOCKS端口和协议，不猜端口。可使用仅当前命令的代理覆盖验证；以下占位符必须替换为客户端实际端口，不输入凭据URL：

```powershell
git -c safe.directory=D:/PowerTrustAI -c http.proxy=http://127.0.0.1:实际HTTP端口 ls-remote origin
```

SOCKS入口需用客户端对应协议，不能将SOCKS端口当HTTP使用。不要关闭SSL验证、不要未经检查修改全局代理，也不要将代理密码或GitHubToken发到聊天。

4. 网络恢复后由现有Git凭据管理器或官方交互登录在本机完成认证。确认远端引用；非空时先fetch、比较共同历史和差异，不直接覆盖。
5. 确认与远端兼容的当前基线后，推送实际 `master` 分支并设置upstream。已有用户授权，恢复后可接续，不需重新索取推送许可；当前不能跳过远端检查。

本轮私有审计与诊断路径：`data/runtime_local/github-baseline/`。上传中断不影响本地基线和学习手册；此说明不启动自动监测或反复重试推送。
