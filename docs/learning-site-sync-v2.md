# 新电脑独立学习站同步清单（第二版）

GitHub仓库：https://github.com/7556481/PowerTrustAI 。冻结引用 `release-v2-20261009`；最终完整提交哈希由本轮交付明确提供，并以 `git rev-parse release-v2-20261009` 核对。源码修复身份 `04ec59b59313500ea97bffe5b1421a0def0407cb`；文档与站点的最终交付哈希应按冻结引用核对，不能把修复提交误称全部交付。

## 只阅读（最小）

必需路径：**docs/learning/site/** 整个目录，包含index.html、20章页面、60自测折叠答案、CSS/JS、search-data.js及build-manifest.json。双击index.html即可离线阅读，不需要Python、业务项目环境、.env、data、模型、数据库或令牌。直接沿用GitHub文件，不提供ZIP，也不用恢复业务项目。

Git稀疏同步示例（冻结引用发布后）：

```powershell
git clone --filter=blob:none --no-checkout https://github.com/7556481/PowerTrustAI.git PowerTrustAI-learning
cd PowerTrustAI-learning
git sparse-checkout init --no-cone
git sparse-checkout set /docs/learning/site/
git checkout release-v2-20261009
git rev-parse HEAD
```

## 本地服务或重建

额外路径：`docs/learning/`（Markdown、assets、版本与引用记录）、`tools/__init__.py`、`tools/learning_site.py`、`start-learning.cmd`。依赖仅Python **3.10+标准库**，不安装业务requirements、不建立新虚拟环境，不读取私有data。现有学习启动器有.venv就复用；独立电脑没有时用py -3/python。

```powershell
git sparse-checkout set /docs/learning/ /tools/__init__.py /tools/learning_site.py /start-learning.cmd
python -m tools.learning_site build
python -m tools.learning_site serve --open --port 8770
```

若Windows安装的是py启动器，可改为 `py -3 -m tools.learning_site ...`。8770纯静态站，与业务8765无关；没有自动付费任务、模型调用或训练。

## 可选源码引用校验

增加 `tools/learning_checks.py` 和下面公开只读文件。这些文件仅供教学摘录哈希与定位校验，**不导入或启动业务代码**；无私有data仍可构建静态站。运行 `python -m tools.learning_checks`，应核对20章/60自测、链接与LF规范化源码SHA。

- `backend/api.py`
- `backend/assembly.py`
- `backend/service.py`
- `backend/store.py`
- `harness/product_policy.py`
- `harness/runtime.py`
- `rag/corpus_build.py`
- `rag/semantic.py`
- `services/bounded_repair.py`
- `services/claim_extractor.py`
- `services/structured_model.py`
- `tools/unit_conversion.py`

追加稀疏路径时保留上述学习路径和这份列表。source-version.json标记应用源码身份，source-check.json绑定实际函数/摘录/行号；Git LF/CRLF仅按文档规范化核验，不改变生产Evidence身份规则。

## 验收边界

站点布局、自测与20章保留，第二版定位为限定范围性能改进原型。最终默认v4+lossless/schema13/flash/product1.5/BM25 aggregate/NLI关闭仅说明业务配置；**独立学习站不需要这些运行依赖**。覆盖不足、语义不稳定、历史长度失败和耗时波动仍需学习，不承诺所有10秒，不宣称费用或纠正率下降。

最终交付以release-v2-20261009冻结引用对应的完整哈希为准；两题程序pass而内容/浏览器项目未全部通过，站点如实保存这些限制。完成发布后无需恢复业务项目即可阅读/启动本独立学习站。
