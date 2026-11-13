# 公开仓库维护主线（v31）

日常维护路径：从最新origin/master新建codex工作分支 → 普通push → PR → Public offline checks的offline检查成功 → 合并 → 本地master快进。禁止直接强推或删除master；不要求人工批准（0），模型/私有数据不上传。主干保护的实际设置及来源检查以本轮回执为准，不能把计划写成已生效。

## 依赖与目录审查

10份有效根清单集中到requirements/，版本、哈希和Windows平台说明保留；langgraph.txt内部-r改为同目录langgraph.lock.txt。根requirements.txt原为0字节，旧acceptance_preparation仅把它作为可选指纹来源，不是有效安装依赖；现明确默认演示安装。demo为api.lock+ci（图运行时），public另含corpus/pdf。嵌入/训练按需隔离。

消费者：公共CI改用requirements/public.txt；README安装走根默认入口；backend装配/harness运行时及测试缺依赖提示同步新路径；学习站04/14章同步安装指引。所有冻结报告和历史评测脚本不批量替换旧路径，重现须检出固定提交。portfolio公开案例迁到docs/portfolio，文档索引和README链接同步。output/pdf保留两份固定旧版交付：docs/handbook-r1-changes.md等历史链接和两个独立PDF构建器仍是消费者，不能当无用目录删；本轮不生成PDF。

## 代码审查和实际重构

正式start-powertrustai.cmd→tools.managed_overlap→backend.api/ManagedFactory→Harness，演示--demo→tools.ui_fixture→SyntheticUIFactory，历史GET→RunService.result/RunStore与evidence端点；公开评测入口tools.public_checks/harness.demo/acceptance_preparation已逐路径核对。

健康探测曾两处实现策略：backend.launcher只接URLError，tools.managed_overlap再套一层接RemoteDisconnected。现在统一到backend.launcher.health_at，普通open_local/受管启动/回退均直接调用同一实现，删除受管层重复包装；连接关闭竞态测试改为替换中央urlopen，覆盖同一行为。这消除了普通入口与受管入口错误处理容易漂移的维护负担。

保留backend.__main__独立命令行兼容入口、Store旧快照投影和services旧协议解析：它们仍被已有历史读取、schema13生产和冻结评测动态选择。保留evaluation旧脚本的固定版本/原路径假设，不并入日常入口；退役Tantivy未在普通Factory注册。services中相似的审核模板/解析器代表不同合同和旧Store兼容，未证明无消费者就不合并。没有按文件名批量删除。

本轮0真实模型请求，不重启8765，不改私有知识库/正式Store。两个工作树原有材料在本机data/runtime_local/repo-mainline-v31逐文件备份和哈希；本地master同步时仅暂存三份已修改文档，快进后恢复全部历史补记，未跟踪材料逐项保留。分支处置、归档标签、保护实际值与验证日志见该本机回执，公开归档位置会在收尾补齐。
