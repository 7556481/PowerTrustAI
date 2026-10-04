# PowerTrustAI 工作规则

- 先读 `docs/handoff.md`、`docs/documentation-index.md` 和 `docs/design-decisions.md`；以实际代码及指定版本归档为准，历史报告不是当前配置。
- 最终中文学习与面试手册要求见 `docs/final-handbook-requirements.md`；每轮结束更新 handoff 和文档索引，保留重要决策、失败及验证证据。README 不替代最终手册。
- 复用现有 `harness.runtime.OfflineHarness`、四 Agent、Retriever/Evidence 与确定性政策，不另建调度器。真实服务事实审核必须显式启用 schema12。
- 保持默认检索、固定知识快照和严格 ID/版本/原文定位约束；改变协议、模型、切分或实验配置须独立版本化，不能覆盖历史结果。
- `power-system-hallucination-risk-assessor/` 是独立历史仓库，不修改或展开跟踪。旧六维评分、阈值、默认参考及关键词规则未经审查不能成为生产依据。
- 不读取、显示或归档密钥文件内容、凭据和请求头。仅在用户授权的真实运行中由已有入口加载项目根 `.env`；环境变量优先。
- 普通测试离线、无付费请求；真实批次须有明确授权、冻结配置、调用上限和失败停止条件。交接不启动新付费批次。
- 官方全文、模型、数据库、实际输入/响应和运行输出留在 Git 忽略的 `data/`；不自动提交或推送。
- 分开报告执行失败、证据不足、工程前提缺失和语义疑点。引用可回查、相关性分数及规则告警不等于模型正确识别；pass 不是工程安全认证。
- AI 辅助、用户监督的反馈保留来源，不改为专家金标准；unknown 保留排名，不当作不相关。
- 项目解释器：`D:\PowerTrustAI\.venv\Scripts\python.exe`。验证：`& .\.venv\Scripts\python.exe -m unittest discover -s tests -v`。沙箱拒绝启动时用工具审批，不重建环境或改权限。
