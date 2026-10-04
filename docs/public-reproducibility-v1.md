# 公开仓库可复现性验证 v1

记录日期：2026-10-04；初始master/e1042cdb，代码父提交fb235746。不是基于旧526bdee推断。独立本地克隆使用 `git clone --no-local --no-hardlinks`，仅获取Git内容；新建Python 3.13.2虚拟环境，不继承项目site-packages，不复制项目真实`.env`、原有data或模型。候选检出仅覆盖明确公开改动，最终提交与清单另核对。

## 复现问题与修复

基线纯标准库：442项，8错误，55跳过；错误为公开baseline读取缺失私有归档、citation API测试强制导入可选FastAPI、四个测试的诊断临时父目录不存在，以及protocol/revision未保护的私有读取。新并发探针另得到实际2请求/轨迹3条。错误日志原样保留，不将其改为成功。

- 公开 `baseline()` 默认不读取私有历史；`include_private_history=True` 是显式选项，缺失文件可跳过。该模块仍是历史验收工具，不作为当前服务配置。
- `test_acceptance_preparation`已有私有重放保护，保留断言；增加新可选模型元数据None的旧归档兼容比较。
- protocol与revision补齐缺档跳过，旧历史原失败断言保留。新增公开synthetic_fixture证明旧引用原文缺失仍失败。
- 六个诊断测试文件使用 `tests/fixture_paths.py` 显式自建允许作用域父目录，再创建独立临时子目录；保持路径约束和原有效同级发现断言。
- API测试仅在缺可选依赖时跳过；补锁httpx/httpcore/certifi，使HTTP TestClient可复现。没有把关键普通回归全部设skip。
- 并行ModelClient记录与structured_request返回均使用稳定归属，见[轨迹说明](model-trace-attribution-v1.md)。

## 环境与已完成检查

实际修复提交97e35235e1e30b5cd81a6dd8b1ac6d01e31b568b再次独立克隆：标准库455项/60跳过/55.227秒；锁定API/PDF455项/27私有历史跳过/68.130秒；原Harness七场景与两模式实际HTTP演示通过，付费0。最终克隆不复制原data/.env，演示服务已停止。对应final-*日志与提交、依赖、跳过清单保存本机verification.json。

Git全部可达历史及暂存路径/blob审核通过（240路径、286唯一blob），排除秘密/data/模型/数据库/全文；公开安全测试的example.org虚构拒绝URL经审核记录例外。用户最新授权推送，但一次普通push因github.com:443不可连接失败；最终只读回查也连接重置。本轮未上传，不强推、不改代理或SSL、不反复重试；待推送含此前fb235746/e1042cdb和本轮代码/说明提交。长期授权与确切网络观察见handoff。

最初修复候选：标准库453项/60跳过，36.779秒；API/PDF锁定环境453项/27跳过，72.528秒。后续新增纠正耗尽与SQLite重启绑定回归，两个环境11项新增回归均通过；最终锁定环境完整455项/27跳过，68.266秒。最终提交复查见本机verification.json。

锁定安装：`requirements-api.lock.txt`（FastAPI0.115.12、uvicorn0.34.2、httpx0.28.1及列出的传递依赖），PDF检查使用 `requirements-pdf.txt`（pypdf6.10.0）。完整精确安装清单在本机verification.json；其他Python/平台未声称已验证。安装依赖访问公开PyPI，但普通测试/演示均无付费模型请求。

27个锁定环境跳过项均为私有历史材料重放，缺档原因逐项保留；标准库另外跳过33个可选API/PDF依赖检查。公开错误ID、引用作用域、部分失败、容量、纠正预算、并发/取消/超时、API持久化和路径安全检查正常执行。真实私有历史不复制、不上传，本轮不重复真实schema13付费回归。

原 `python -m harness.demo` 七个确定性场景完成，包括两种模式、Revision、证据不足、超时、修订上限和非法ID；模拟pass只验证机械路径。

实际启动候选克隆 `python -m backend --demo --port 8769`，`/health`确认synthetic_fixture、网页返回200；`backend.http_demo`完成两种HTTP提交、Evidence回查、人工反馈保存、错误版本409、无令牌401，0付费调用。未加载真实知识库/真实`.env`；只使用该克隆自行生成的演示令牌，不输出或归档请求头。测试服务已停止。**本轮是HTTP和页面资源检查，未做新的浏览器交互验收。**

## 可运行命令与证据

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m harness.demo
& .\.venv\Scripts\python.exe -m pip install -r requirements-api.lock.txt -r requirements-pdf.txt
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m backend --demo --port 8765
# 另开终端
& .\.venv\Scripts\python.exe -m backend.http_demo --port 8765
```

本机忽略目录 `data/runtime_local/public-repro-v1/` 保存baseline-offline.txt、baseline-demo.txt、baseline-trace-probe.txt，candidate-stdlib-final.txt、candidate-locked-tests.txt、candidate-new-regressions-*、candidate-locked-final.txt、candidate-http-demo.txt、dependency-install.txt、reading-notes.md、verification.json与Git路径/blob审核记录。准备阶段相对路径失误及未完整覆盖候选的早期运行也保留，未计为通过。本报告不宣称语义准确率、专家金标准或工程认证。
