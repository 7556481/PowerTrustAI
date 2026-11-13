# 按场景安装

- 演示：根目录 `python -m pip install -r requirements.txt`，等同 `demo.txt`（API锁定包＋CI图运行时）。无需密钥、知识库、模型权重。
- 公共回归：`python -m pip install -r requirements/public.txt`，另含语料与PDF夹具依赖。CI实际使用此入口。
- 真实本机服务：已有环境保留；新建环境先装public，再按私有配置提供固定SQLite快照与DeepSeek。
- `api.txt`为最小API直接依赖，`api.lock.txt`为已验证闭包；demo使用后者。
- `corpus.txt`、`pdf.txt`按需；`embedding.txt`及`embedding.lock.txt`只供可选CPU语义实验，不默认安装或下载权重。
- `langgraph.txt`引用`langgraph.lock.txt`；该锁保留Windows amd64/CPython3.13轮子哈希，使用`--require-hashes`，不可直接当跨平台锁。公开CI/demo使用`ci.txt`中原有版本。
- `training-v1.txt`仅隔离CPU训练环境，不装入日常服务环境。

原清单版本/哈希/平台注释保留。冻结报告中的旧根路径不改写，需要重现时检出对应固定提交。
