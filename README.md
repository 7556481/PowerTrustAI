# PowerTrustAI

A trustworthy AI framework for power system large language models.

离线 Harness 运行说明：[docs/offline-harness.md](docs/offline-harness.md)。
Markdown、SQLite、BM25 与 Evidence 入库/查询说明：[docs/markdown-retrieval.md](docs/markdown-retrieval.md)。
文本型 PDF 入库、质量诊断与官方资料试运行：[docs/pdf-retrieval.md](docs/pdf-retrieval.md)。
PDF 页内切分、相邻上下文与三份资料对比：[docs/pdf-retrieval-quality.md](docs/pdf-retrieval-quality.md)。
真实 Retriever 接入 Harness、固定版本与预算验证：[docs/harness-retrieval.md](docs/harness-retrieval.md)。
结构化 Generation Agent、模型适配接口及仅生成 CLI：[docs/generation-agent.md](docs/generation-agent.md)。
DeepSeek 官方连接、本机安全配置与一次连接测试后五问：[docs/deepseek-generation.md](docs/deepseek-generation.md)。
精确引用、主张提取与局部 Evidence Verification：[docs/evidence-verification.md](docs/evidence-verification.md)。
本机单用户辅助审核服务、运行存储、HTTP API 与人工复核：[docs/local-review-service-v1.md](docs/local-review-service-v1.md)。

## Core Features

- Retrieval Augmented Generation (RAG)
- Multi-Agent Verification
- Agent Harness
- Power System Knowledge Tools

## Architecture

Question
↓
Generation Agent
↓
Verification Agent
↓
Evidence Retrieval
↓
Final Response
