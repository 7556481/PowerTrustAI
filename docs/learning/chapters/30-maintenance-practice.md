# 30 依赖、CI与安全删除的工程依据

本专题绑定应用提交 `e4fb27e7c8893a5ad141ebef0ae5f32216648065`，2026-11-24离线核对。配置只看[当前状态](../../current-status.md)。数字分别标记真实实验与教学构造；以下问题不授权现场工程操作。

## 库必须对应消费者
FastAPI提供API路由与校验边界，Uvicorn运行ASGI服务；LangGraph装配阶段图；jieba负责中文预分词；PyArrow在构建工具流式读Parquet；sqlite3、http.client、asyncio、hashlib属于Python标准库，无需额外pip安装。PDF、embedding、CPU训练是按需环境，不能把实验包都装进演示入口。消费者见[依赖场景说明](../../../requirements/README.md)、[正式装配](../../../backend/assembly.py)、[语料构建](../../../rag/corpus_build.py)。

::: answer 题30.1：约束、锁与哈希分别解决什么？
版本范围允许解析器选满足条件的版本；锁固定已验证闭包；hash约束安装字节身份，不保证包无漏洞。项目langgraph锁有Windows/CPython平台约束，不能称万能跨平台锁。根requirements.txt给演示默认入口，public.txt用于公开回归，training-v1只在隔离训练环境。继续追问：CI成功只证明那套依赖和公开夹具，未装私有资料时不能证明全库生产查询可用。
:::

## 分支、提交与报告
提交SHA固定内容，分支是可移动指针，tag用于保留结束研究头。工作分支→PR→实际offline检查→合并，master禁止强推/删除并要求PR。保护是否生效要查远端规则及当前检查来源，不能从文档一句话推断。冻结报告链接到固定提交，删除工作分支不删这些提交的可达归档。

::: answer 题30.2：已合并与没有独有提交相同吗？
不相同。squash后旧分支提交可能不是master祖先，但内容已整合；需结合关联PR、merge-base、diff和独有工作检查。删研究分支前以tag保住需要的头并从远端核验可达，删除使用预期旧SHA防止覆盖后来提交。继续追问：删分支只移指针；删索引移除本机检索能力；删历史Store会破坏用户记录，三者风险不同。
:::

::: answer 题30.3：一段旧代码没被静态import能否删除？
不能。Factory注册、命令行python -m入口、动态import、冻结评测脚本、旧Store反序列化都可能消费它。先建立调用图，再搜索配置/脚本/测试/历史重现约定；保留模块应指出具体消费者。格式化与lint是否强制看[公共检查入口](../../../tools/public_checks.py)和[工作流](../../../.github/workflows)，不能由简历措辞推断。本项目自动检查不等于任何团队经历。继续追问：将模块移出默认路径仍可保留重现用途，但需要验证动态选择与兼容回读。
:::

## 本机版本核对练习
同时核对启动命令、进程命令行、源码SHA、受管Factory、manifest、Store与账本路径和health。端口ready不是配置身份，磁盘master更新不代表旧进程加载新代码。演示与生产必须隔离端口/Store；本轮不重启8765、不读密钥、不发模型请求。
