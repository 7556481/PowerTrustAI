# 显式Factory有限发布方案（待浏览器烟测完成与结果审阅）

当前状态：不能建议有限启用，先解决report.md所列浏览器认证阻断，完成唯一自然题和故障/取消页面验收。v23的29.20%/9.775秒沿用为既有同稿配对观察；本次单题不能重新计算提速幅度。

## 受管入口

在已包含75cbbdd及本次入口代码的受管checkout、项目解释器下运行，沿原ServiceConfig.from_environment/根.env加载器、环境变量优先和原localhost会话启动，不手工读取认证文件。当前无生产环境变量开关；--factory是显式组合选择，默认component。

有限隔离启用命令（示例，不在本轮自动执行）：

```powershell
& D:\PowerTrustAI\.venv\Scripts\python.exe -m tools.managed_overlap --factory overlap --port 8779 --store D:\PowerTrustAI\data\runtime_local\overlap-limited-v1\runs.sqlite3 --budget-dir D:\PowerTrustAI\data\runtime_local\overlap-limited-v1\accounting --model-cap 16 --token-cap 300000 --open
```

必须保留这个Store/token路径和账本，不以换目录重置付费余量。unknown usage保留原预留，出现未决或共享故障时停止有限批次、等待物理执行释放，核对账本后再审阅，不自动重发。该命令不修改现有start-powertrustai.cmd或8765配置。

## 识别生效

正常结果configuration.managed_factory显示requested selection。仅看该字段不够：同Store旁managed-overlap-events.jsonl记录factory_created.enabled、领域retrieval_start/return和fact_http_worker_begin。确认实际事实HTTP工作线程在领域读取返回前开始，不能仅以create_task或配置标志宣布生效。记录器不归档headers、凭据或请求正文。物理socket发送仍不是该时点，不混同。

## 一键回退

```powershell
.\rollback-overlap.cmd --port 8779 --store D:\PowerTrustAI\data\runtime_local\overlap-limited-v1\runs.sqlite3 --budget-dir D:\PowerTrustAI\data\runtime_local\overlap-limited-v1\accounting
```

脚本先通过原session/stop优雅停止，忙碌时返回错误并退出，不能强杀在途工作；然后同Store/账本选择component并--open。工厂开关置于参数末尾，普通Factory不会被前置参数覆盖。正常历史保留，无数据迁移、不重建知识库、不覆盖旧响应。应确认新结果managed_factory.selection=component、factory_created.enabled=False，事实请求回到领域读取之后的原准备顺序。

## 8765发布审阅

只有浏览器烟测通过并经用户审阅决定，才考虑把同一显式入口的端口改为8765并使用已备份的现行受管Store/账本配置；不能把隔离Store当生产历史，不照抄示例路径覆盖现有数据。先记录原启动命令/Factory/源码及配置身份、正常优雅停止，再选择overlap；回退同一--port/--store到component。当前本轮未授权执行此切换，保持8765不动。
