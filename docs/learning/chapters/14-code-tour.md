# 14 核心源码阅读路线：输入、调用、异常与取舍

## 如何读，不被版本文件淹没

先看backend/__main__.py和assembly.py，再读OfflineHarness.run，最后才深入当前Agent协议。目录里旧v4/v6/v9不是多个并行审核器，而是历史契约保留。当前manifest明确schema和prompt；不要凭文件名最大数字猜采用版本。

本章代码摘录由write-excerpts脚本按AST函数/实际行号读取当前源码，记录文件及片段SHA。省略的部分明确是摘录，不当完整函数。你可以从同名函数继续读上下文。正文解释的是责任，代码才是异常和字段的最终依据。

当前新增紧凑协议入口agents/verification_contract_v14.py的ReviewCatalog/run只通过直接组件回归，真实Harness输入包装遗漏导致12题失败；默认日常仍13。读harness/runtime.py中schema9–13构造ReliabilityVerificationInput的分支，便能定位为何新14没有tool_results。这个已知缺口没有在本轮自动补后重跑，见第15章。

## 第一条路线：从提交到冻结答案

ApplicationService.submit验证配置、排队并保存TaskRequest。worker建立Bundle，调用OfflineHarness.run；runtime中invoke统一处理期限、使用量、执行问题和observer。问答先检索、Generation，已有回答直接冻结；提取服务输出claims，validate_extraction检查覆盖和绑定。

阅读任务：找到answer_id/version在哪里生成，找到substantive_answer=False为何绕过提取。若生成未成功，是否可能还有领域模型请求？按状态和usage回答，别只看函数名。

## 第二条路线：Evidence怎样变成typed basis

KnowledgeStore.evidence从固定版本片段构造原文对象；RetrievalSession保存命中与交付，quote_candidates提供字面候选，EvidenceScope为独立审核和每项原引用建立不同命名空间。解析器把合法选择映射到TextExcerpt或metadata/calculation等正式对象；core.typed_evidence负责类型义务。

阅读任务：一个quote属于当前原引用scope但text相同于另一scope，借用是否合法？答案是不合法，作用域是审核对象与交付身份，不仅文字。程序可验证这个关系，不用模型判断“看起来同源”。

## 第三条路线：政策与Revision

ProductAuditPolicy.decide_context读取执行、分类、支持、领域和引用结果。bounded_repair.eligible_repairs只允许存在原文绑定建议的faithful adverse对象。Revision不自行通过；runtime创建新版本后回到提取和双审。观察review_rounds和answer.versions而非只看usage中有没有revision组件。

阅读任务：为什么一个insufficient finding不必自动修订？因为可能是缺资料；没有已交付原文能支撑实质replacement时不能发明修复。反例中即使可修另一个错误，其他缺口也保留。

## 第四条路线：存储和只读恢复

RunStore.tx管理短写事务，index保存版本化对象，result经backend.presentation/serialization安全投影。GET result和NLI读取已存结果，不调用Harness。LocalNLI失败只产生diagnostic对象，主判断已结束，不反向进入Agent输入。

阅读任务：重启恢复时为什么queued/running变interrupted而不是继续worker？没有供应商幂等保证和完整续执行证明，自动重发会重复收费、改变历史。恢复不等于重新执行。

## 对每个函数问五个问题

- 输入来自用户、数据库、模型还是程序派生？信任边界不同。
- 输出是否绑定task、answer和knowledge版本？有没有跨版本缓存？
- 哪些非法字段会抛异常，哪些业务未知会合法返回？
- 函数是否改变状态/数据库，还是纯转换？
- 测试是否走真实生产调用路线，还是只手工构造内部对象？

例如strict_json拒绝重复键，避免模型输出两个status被普通json.loads静默保留后者。它能保证唯一键，不能保证status语义正确。source_identity生成稳定定位，不证明原来源权威。fuse_ranks融合排名，不执行事实核验。

## 面试阅读练习

练习1：注释掉某个validate_review会发生什么？参考：未知/错版本依据可能进入结果，影响政策和存储；不是“更宽容”而是失去边界。练习2：只删除旧协议文件能简化当前模型消息吗？不一定，应检查真正拼装模板与运行profile；清代码目录不等于减少输出字段。

面试说法：“我能从API沿submit/worker/Harness读到审核解析，解释每个边界可证明什么。代码摘录绑定实际版本和哈希，历史协议不冒充当前默认。”

## 实际代码摘录

以下段落由程序读取源码生成，并由source-check.json核对；不是手写伪代码。

### 重复键、非有限值与严格JSON

路径 services/structured_model.py，函数 strict_json，行18–21。

```python
def strict_json(text):
    return json.loads(text, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          StructuredValidationError("json_parse", "$", "nonfinite_numbers_not_allowed")))
```

输入是模型响应字符串，输出JSON对象；异常仍进入有限纠正，绝不把解析失败变业务通过。

### 名次融合不验证事实

路径 rag/semantic.py，函数 fuse_ranks，行149–154。

```python
def fuse_ranks(bm25, dense, *, constant=60):
    scores = {}
    for ranking in (bm25, dense):
        for rank, (index, _) in enumerate(ranking, 1):
            scores[index] = scores.get(index, 0.0) + 1.0 / (constant + rank)
    return scores
```

输入是两路固定排名，输出各片段RRF分；未出现的路不贡献，名次从1。

### 原ID和内部ID分离

路径 rag/corpus_build.py，函数 source_identity，行10–14。

```python
def source_identity(row,revision,shard,row_number):
    original=row.get('_id')
    missing=original is None or original==''
    if not missing:return str(original),False
    return 'industrycorpus2:row-v1:'+digest(canonical([revision,shard,row_number]).encode()),True
```

输入含可缺失_id的记录、revision、分片和绝对行号；输出身份和missing标志，不猜出版机构。

### 短事务的commit与rollback

路径 backend/store.py，函数 RunStore.tx，行50–56。

```python
    def tx(self):
        try:
            self.db.execute('BEGIN IMMEDIATE');yield;self.db.commit()
        except BaseException as exc:
            self.db.rollback()
            if isinstance(exc,sqlite3.Error):raise StorageError('Run transaction failed') from None
            raise
```

写入中异常回滚，SQLite错误转StorageError；网络调用在事务外。

### 一次修订资格不是修订成功

路径 services/bounded_repair.py，函数 eligible_repairs，行21–31。

```python
def eligible_repairs(finding):
    """At least one faithful adverse component; other gaps remain untouched."""
    from dataclasses import replace
    rows=getattr(finding,'component_reviews',())
    if not rows:return repair_proposals(finding)
    proposals=[]
    for row in rows:
        if row.status.value not in ('insufficient_evidence','contradicted'):continue
        if row.classification_issue or row.fidelity_status!='faithful':continue
        proposals.extend(repair_proposals(replace(finding,status=row.status,component_reviews=(row,))))
    return tuple(proposals)
```

输入是当前finding，输出可用原文绑定建议；faithful并且adverse才考虑，repair=null不会自动造建议。

### 确定性标量计算的边界

路径 tools/unit_conversion.py，函数 compute，行14–24。

```python
def compute(payload):
    if set(payload)!={'value','from_unit','to_unit','claim_id'}:raise ValueError('unit_conversion.input: exact declared fields required')
    value=payload['value'];a,b=payload['from_unit'],payload['to_unit']
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('unit_conversion.value: finite scalar required')
    if a not in PAIRS or b not in PAIRS or PAIRS[a][0]!=PAIRS[b][0]:raise ValueError('unit_conversion.units: known same-dimension units required')
    if type(payload['claim_id']) is not str:raise ValueError('unit_conversion.claim_id: program claim binding required')
    converted=value*PAIRS[a][1]/PAIRS[b][1]
    if not math.isfinite(converted):raise ValueError('unit_conversion.output: finite result required')
    return {'input':dict(payload),'output_value':converted,'output_unit':b,'quantity_kind':PAIRS[a][0],
        'scope':'scalar SI conversion only; user data unverified; no stability, equipment suitability or simulation result',
        'rule_source':'SI prefix scale whitelist in tools/unit_conversion.py; program rule, not an electrical operating standard'}
```

完整函数可看有限单位表和类别校验；不做潮流或厂站性能分析。

### 恢复状态但不重发

路径 backend/store.py，函数 RunStore.recover，行58–60。

```python
    def recover(self):
        with self.tx():
            self.db.execute("UPDATE runs SET status='interrupted',ended=?,error_code='PROCESS_INTERRUPTED' WHERE status IN ('queued','running')",(now(),))
```

SQL只将未完成标interrupted，没有模型调用；已有结果保持原版本。
