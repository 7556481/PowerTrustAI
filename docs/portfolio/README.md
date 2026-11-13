# Public Portfolio fixtures

这里展示可公开复现的工程边界，不是电力语义准确率benchmark。所有正文为synthetic_fixture，不包含官方原文、私有运行或训练权重；不需要API密钥或模型下载。

运行 `python -m tools.public_checks`，以及 `python -m harness.demo`。实际Factory贯通见tests/test_schema14_factory_flow.py：问答/已有回答、合法计算、原引用隔离分组、真实分类异议、非法ID保留同级结果、一次Revision与重提取双审、schema13兼容。作用域与条件细项见tests/test_compact_review.py；共享停止见tests/test_batch_control.py。

不能以引用存在代替引用支持。该集合没有完整相关性参考池，不报告Recall；真实语义评价来源为AI辅助用户监督，未声称专家金标准。真实schema13/14对照是私有小型开发案例，预期不进入模型消息。未来30–50项benchmark未在本轮扩展。
