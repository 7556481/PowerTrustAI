# 14 核心源码阅读路线：输入、调用、异常与取舍

## v7只读标注源码路线

先读backend/answer_annotations.py的identity/locate/project：身份与逐字核验先于展示，同句意见只合入口，不合后台记录。backend/presentation.py保留原解释字段并追加inline_review；backend/service.py仅投影已保存审核身份，不重执行、不落库。再读backend/static/inline_review.js的model/render，检查Array.from码点切片、重叠分段、纯文本节点、复制原文和历史版本隔离。app.js保持原epoch/轮询/反馈机制。tests/test_answer_annotations_v7.py与tests/ui_inline_review_probe.js覆盖坏区间、重复句、版本/原文不符、emoji/CRLF、同句两来源、重叠、原文复制及关闭焦点。

下列两个片段从本轮实际AST摘录；只展示定位入口及精确核验，不代表整个函数。源码身份见source-check/source-version，不能把安全定位说成审核语义正确。

### 精确标注入口：identity

backend/answer_annotations.py实际行6–10，完整函数。

```python
def identity(obj, answer):
    return (bool(answer.get('answer_id')) and type(answer.get('version')) is int
            and obj.get('answer_id') == answer['answer_id']
            and type(obj.get('answer_version')) is int
            and obj['answer_version'] == answer['version'])
```


### 精确标注入口：locate

backend/answer_annotations.py实际行13–28，部分函数。

```python
def locate(answer, binding):
    """Explicit invalid offsets never fall back to text search."""
    if not identity(binding, answer):
        return None, '缺少或不符的回答版本绑定'
    text = answer.get('text')
    original = binding.get('text')
    if not isinstance(text, str) or not isinstance(original, str) or not original:
        return None, '缺少逐字原文；不能使用改述主张定位'
    start, end = binding.get('start_offset'), binding.get('end_offset')
    if 'start_offset' in binding or 'end_offset' in binding:
        if (type(start) is int and type(end) is int and 0 <= start < end <= len(text)
                and text[start:end] == original):
            return (start, end, original, 'saved_offset'), None
        return None, '原文区间或逐字核验不符'
    start = text.find(original)
    if start < 0 or text.find(original, start + 1) >= 0:
```

v6界面入口：backend/static/index.html为单列用户问答，diagnostics.html为历史与专业诊断；diagnostic_input.js独占工程背景及已有回答payload。共享app.js用实际DOM职责选择渲染/辅助读取，但认证、请求归属和主轮询只有一套。tests/ui_question_probe.js用真实主页ID创建DOM，不补造诊断节点；旧异步/反馈探针明确针对诊断页继续执行。backend/api.py只把三个确切新静态资源加入白名单，未放宽任意路径、query或运行API鉴权。

## 当前源码身份与读法（2026-10-27维护同步）

历史评测应用基线1a92d03、入口babdfe1保持冻结；2026-10-27工程维护源码身份见source-version，未改历史合同/政策。先读evaluation/natural_draft_audit_v1.py的recover与batch：前者恢复实际8稿及快照，后者接入原Factory/Harness并统一预发送扣额。参考只进离线分析，不进模型。再读rag/chinese_first.py，区分目录范围、语言触发与实际Evidence。候选默认关闭，生产schema13、受管langgraph_v1，源码fallback sequential，8765停服。

后端本轮先读backend/service.py的_worker/_run_one/lifecycle_status及result，区分资源故障、排队终态和无实质回答适用阶段；backend/assembly.py的close_resources会尝试全部资源，不强行越过未确认drain。前端可从backend/static/app.js的reviewDrafts/load/requestAuxiliary看草稿归属、主周期与辅助slot独立、revision和终态收敛，从backend/store.py的require_run/state_row看测量支持的轻量读取（get完整恢复仍保留）；list_runs保留兼容的120字问题摘要；tools/ui_fixture.py仅用于隔离合成8766，不是生产入口。五个死导入的清理不改变摘录函数体。

以下仅摘函数开头最多18行，明确不是完整函数；所有记录按AST限定符定位，保留完整函数终点、实际文件LF身份与片段哈希。长函数的后续分支必须继续读源码，不以开头代替证明。旧摘录已重新从实际文件取文，历史运行身份仍见原提交。


## 2026-10-24历史真实验证边界

【真实失败】计划28槽，候选请求因工程兼容缺陷被拒绝，停止后26槽未执行；没有候选模型正文，自然线完全未发送。已知token仅原版15868，拒绝用量未知。补回JSON提示、拒绝即停及条件/实例独立性后1224离线通过，不能称真实收益。schema13生产默认不变，不采用。[完整响应、依据与版本边界](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/review-contract-simple-v1/report.md#)。

## 2026-10-24 简化合同与投影的源码入口

从services/review_simple_v1.py的SimpleCatalog看起：沿既有ReviewCatalog生成SRC来源目录及ANS答案锚点，decode_wire仅程序绑定顺序身份；parse_one校验ID并明确投影三维声明。旧typed依据/authority/objection/repair继续复用，旧condition空引用投影不再复用。Factory仍注入原事实Agent，配置simple_v1显式启用，production回退，不改领域/修订资格/product政策。

【待真实验证的实现检查】离线替身能通过none/not_applicable/not_claimed用例，是否证明真实模型会识别所有无条件陈述？

::: answer 展开新增练习解析
不能。它只证明程序收到该合法声明时不会走旧遗漏路径；真实模型能否作出正确声明、能否识别条件归属，需要固定真实输入逐项核验。不能将新字段或替身标签当语义成绩。
:::

## 2026-10-24 审核链v2实证更新

本轮入口services/review_scope_v2.py，经backend/config.py与ComponentFactory显式fact_review_contract=scope_v2接入services/scoped_fact_execution.py。默认production保留旧消息/解析；fact_internal_flow须仍为production且schema13。候选使用九语义字段的顺序数组，身份由程序绑定；条件关系映射至原判断再完整重审。真实验证发现逐字字段与空条件投影缺陷，代码保留作失败证据，不建议生产验收。 [完整预测、理由和成本](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/production-review-net-benefit-v2/report.md#)。

2026-10-24：当前Factory显式revision_answer_delivery接入原ModelRevisionAgent，默认production；新prompt身份写入manifest和快照，contract与政策不改。下方两处assembly摘录已按当前AST/连接行重新绑定，旧历史说明以日期阅读。本轮结果与服务实际停服见[报告](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/answer-review-net-benefit-v1/report.md#)。

2026-10-23当前补记：剩余五项固定服务验收完成，本机受管默认已为langgraph_v1，正常服务ready；无配置源码fallback仍sequential。新批32调用、413018token、0失败/未执行；两项诊断实际一次修订和完整重审，但图最终待补充保留，不冒称全部答案认可。四Agent、schema13、七共享阶段及预算/政策不变，A/B未采用。历史104运行/2278事件/2999版本证据对象/8反馈及SHA启动前后相同；原编排可正常停服改受管配置回退。工具浏览器入口已验、登录后视图待一次用户清单，不绕本地文件限制。详见[后续验收](https://github.com/7556481/PowerTrustAI/blob/1a92d03da49ae25f311e950373003d6ab32d09f5/docs/evaluation/langgraph-service-continuation-v1/results-v1.md#)。这是2026-10-23历史服务记录；当前8765停服，以本章开头状态为准。

## 一页请求对象流：先认对象，再读源码

|阶段|对象及身份|数据进入和离开|失败/保存边界|
|---|---|---|---|
|API接收|Submit→TaskRequest；服务产生task_id/run_id|用户问题、可选原回答；客户端不能提交模型路径|先类型校验；无效输入未受理，不算模型失败|
|队列/worker|RunStore保存请求/配置；ComponentFactory产生Bundle|固定知识版本/政策/schema；不把预期标签交模型|共享装配错误停止后续；接受后不能盲重发|
|Generation|AnswerDraft(answer_id,version,text,citations)|实际交付Evidence；答案引用与事实独立检索分开|无实质答案后续不适用；连接/生成失败单列|
|提取|ObligationClaim＋组件ID/原文锚点|立场、数量、必要限定、核验义务|忠实性不同于来源支持，不强制faithful|
|双审|实际EvidenceVerificationInput扩展；领域输入|身份/版本/候选由程序绑定；模型评估支持/条件/异议|Fact与Domain并发；有效同级结果保留；非法ID不补造|
|政策|执行完整性＋业务处置＋问题解决程度|不是多数投票；来源及支持要求仍阻断|可定位局部错误才修订；缺输入不靠删除问题解决|
|Revision|新回答版本，重新产生主张对象|一次实质纠错，重新交付并完整双审|原版错误不抹去；不得修订后直接通过|
|持久化/UI|observer→checkpoint/结果；版本独立|回答、处置、依据先展示，技术详情折叠|刷新/查询/重启只读既有结果，不补算或远程重发|

教学构造：task=T、answer=A/v1、claim=C/组件C0、Evidence=E/知识K；Fact仅可在C0的候选范围选依据，原引用R0仅可用原交付。候选ID不是跨目标通行证。详细synthetic对象与实际函数摘录见下节。

主要契约对照冻结同回答/主张/完整交付，只改13/14；这能减生成/检索混杂，但不能证明完整产品。完整服务与Revision另测，阶段、结构、语义和业务分母分开。采集故障也必须停止并记录，已发请求只离线恢复；否则统计会把报告工程缺陷误算模型失败。


## 如何读，不被版本文件淹没

先看backend/__main__.py和assembly.py，再读OfflineHarness.run，最后才深入当前Agent协议。目录里旧v4/v6/v9不是多个并行审核器，而是历史契约保留。当前manifest明确schema和prompt；不要凭文件名最大数字猜采用版本。

本章代码摘录按AST函数/实际行号读取当前源码，记录文件及片段SHA。省略的部分明确是摘录，不当完整函数。你可以从同名函数继续读上下文。正文解释的是责任，代码才是异常和字段的最终依据。

在learning-audit-v1历史版本中，新增紧凑协议入口agents/verification_contract_v14.py的ReviewCatalog/run只通过直接组件回归，真实Harness输入包装遗漏导致12题失败；默认日常仍13。查看learning-audit-v1冻结源码中harness/runtime.py的历史schema9–13包装分支，可以定位当时14缺tool_results；当前已改用显式输入能力和services/review_inputs.build，不把历史分支当现行源码。那个批次没有在当轮自动补后重跑，见第15章。

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


## 实际代码摘录（本轮重新核对）

### 严格JSON只验证结构

路径 services/structured_model.py，函数 strict_json，行18–21；完整函数至21行，完整定义。

```python
def strict_json(text):
    return json.loads(text, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          StructuredValidationError("json_parse", "$", "nonfinite_numbers_not_allowed")))
```

片段SHA256：76dd2f489da70c1558dd13cb5f101317b869c9ca56842a563dac6970ebe94200。

### RRF融合不保证支持

路径 rag/semantic.py，函数 fuse_ranks，行149–154；完整函数至154行，完整定义。

```python
def fuse_ranks(bm25, dense, *, constant=60):
    scores = {}
    for ranking in (bm25, dense):
        for rank, (index, _) in enumerate(ranking, 1):
            scores[index] = scores.get(index, 0.0) + 1.0 / (constant + rank)
    return scores
```

片段SHA256：9f646b4b29742ebf72bb5eb3db8128c250360dbb855b5e6c9896640dd7ad4f18。

### 来源身份不等于权威

路径 rag/corpus_build.py，函数 source_identity，行10–14；完整函数至14行，完整定义。

```python
def source_identity(row,revision,shard,row_number):
    original=row.get('_id')
    missing=original is None or original==''
    if not missing:return str(original),False
    return 'industrycorpus2:row-v1:'+digest(canonical([revision,shard,row_number]).encode()),True
```

片段SHA256：58f3c8dd93e5a6c23b7b5edbe2112c3ae1bfc686917a07a38e2f684b2c5e35d7。

### 短事务边界

路径 backend/store.py，函数 RunStore.tx，行50–56；完整函数至56行，完整定义。

```python
    def tx(self):
        try:
            self.db.execute('BEGIN IMMEDIATE');yield;self.db.commit()
        except BaseException as exc:
            self.db.rollback()
            if isinstance(exc,sqlite3.Error):raise StorageError('Run transaction failed') from None
            raise
```

片段SHA256：dad37aa75bf1c5e6c3552cf4ebe57685a07f4328d5ff92f9b2452f058782739f。

### 恢复不自动续跑

路径 backend/store.py，函数 RunStore.recover，行58–60；完整函数至60行，完整定义。

```python
    def recover(self):
        with self.tx():
            self.db.execute("UPDATE runs SET status='interrupted',ended=?,error_code='PROCESS_INTERRUPTED' WHERE status IN ('queued','running')",(now(),))
```

片段SHA256：e053039f0449359a72a0d0f7685aaaba2289e17e2832a5b51c22b11a54271334。

### 复用装配与固定Evidence入口

路径 backend/assembly.py，函数 ComponentFactory.create，行275–292；完整函数至357行，局部摘录。

```python
    def create(self,rid,observer,*,fixed_evidence_only=False):
        """Fixed Evidence evaluation may skip index resources; defaults unchanged."""
        if type(fixed_evidence_only) is not bool:raise ConfigurationError('Boolean fixed evidence mode required')
        if self.config.profile=='synthetic_fixture':
            from agents.fakes import make_fake_harness
            harness=make_fake_harness();harness.observer=observer;harness.execution_path=self.config.execution_path
            if self.config.decision_policy=='product-v1':
                from harness.product_policy import ProductAuditPolicy
                harness.policy=ProductAuditPolicy(synthetic_fixture=True)
            return Bundle(harness)
        from agents.generation import EvidenceGenerationAgent
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        if self.config.fact_internal_flow!='production':
            from agents.fact_flow_v1 import FactFlowAgent as FactAgent
            if self.config.fact_internal_flow=='joint_v2':
                from services.fact_flow_protocol_v2 import create_agent as FactAgent
            elif self.config.fact_internal_flow=='two_stage_v1':
                from services.fact_two_stage_v1 import create_agent as FactAgent
```

片段SHA256：90c30e41b968135fa24d44bf40d33f767e4ac80d3a4bd4f0848188937aac21bb。

### 受预算约束的完整闭环

路径 harness/runtime.py，函数 OfflineHarness.run，行47–64；完整函数至66行，局部摘录。

```python
    async def run(self, request, budget, *, knowledge_version=None, generation_only=False, answer_requirements=(),
                  evidence_only=False, indexed_reference_ids=(), generation_snapshot=None, run_id=None):
        if self.execution_path not in ("sequential", "langgraph_v1"):
            raise InputError("Unknown Harness execution path")
        driver = None
        if self.execution_path == "langgraph_v1":
            # Optional dependencies are never imported by the default path.
            try:
                from harness.graph_runtime_v1 import run_graph, validate_versions
            except ImportError as exc:
                raise InputError("Optional LangGraph dependencies unavailable; install requirements-langgraph.lock.txt") from exc
            validate_versions()
            driver = run_graph
        execution = RunExecution(
            self, request, budget, knowledge_version=knowledge_version,
            generation_only=generation_only, answer_requirements=answer_requirements,
            evidence_only=evidence_only, indexed_reference_ids=indexed_reference_ids,
            generation_snapshot=generation_snapshot, run_id=run_id,
```

片段SHA256：e63611d2194634a77c92814d4afdc25f3659c5fbbc0d33e07db0c083239ca525。

### 确定性政策与执行完整性

路径 harness/product_policy.py，函数 ProductAuditPolicy.decide_context，行24–41；完整函数至177行，局部摘录。

```python
    def decide_context(self, verification, domain, budget, revision_round, *, request,
                       answer, claims, extraction, issues, retrieval):
        from agents.contracts import LiteralVerificationOutput
        if isinstance(verification,LiteralVerificationOutput):
            from services.literal_policy_v1 import decide
            return decide(self,verification,domain,budget,revision_round,request=request,answer=answer,claims=claims,extraction=extraction,issues=issues,retrieval=retrieval)
        facts, findings = verification.findings, domain.findings
        ids = tuple(f.finding_id for f in facts if f.status != V.SUPPORTED) + tuple(
            f.finding_id for f in findings if f.check_status in ('warning', 'not_assessable')
            or f.severity == Severity.HIGH)
        context = request.engineering_context
        from services.task_applicability import read,effective
        assessment=read(findings)
        scope=effective(context,assessment) if assessment else context.goal if context else 'unknown'
        basis = (('Model-reviewed requested/asserted scope: ' + scope + '; ' + assessment['reason']) if assessment else 'User requested scope: ' + scope,
                 'Claim components and independent analysis_scope check retain technical truth obligations',
                 'Classification is fallible; scope alone never overrides an adverse finding')
        checks = [('fact_support', 'applicable', 'Every extracted claim must have independent verification'),
```

片段SHA256：723110fc5ff83741dba7a3c4727ba3085b2db5f456fcd9d069ccbec474c6daf3。

### D/O/S/U修订上下文

路径 services/local_revision_v2.py，函数 plan，行79–96；完整函数至144行，局部摘录。

```python
def plan(inputs):
    """Program-owned projection; no credential loading, retrieval or semantic inference."""
    validate_types(inputs,RevisionInput)
    v=inputs.verification;answer=inputs.answer
    require(isinstance(v,LiteralVerificationOutput),'V2 revision requires literal review output')
    require((v.answer_id,v.answer_version)==(answer.answer_id,answer.version),'Revision input version conflict')
    require(not v.execution_issues and not inputs.domain_review.execution_issues,'Incomplete review cannot authorize revision')
    require((inputs.domain_review.answer_id,inputs.domain_review.answer_version)==(answer.answer_id,answer.version),'Domain version conflict')
    require(len({e.evidence_id for e in inputs.allowed_evidence})==len(inputs.allowed_evidence),'Duplicate allowed evidence identity')
    validate_answer(answer,inputs.allowed_evidence)
    av={e.evidence_id:e for e in inputs.allowed_evidence};aa=anchors(answer)
    units={f'U{i}':a for i,a in enumerate(aa)};unit_by_anchor={a['anchor_id']:k for k,a in units.items()}
    require(len(unit_by_anchor)==len(aa),'Duplicate answer anchor')
    authorities={f'D{i}':d for i,d in enumerate(sorted(v.literal_defects,key=lambda d:d.finding_id))}
    require(len({d.finding_id for d in authorities.values()})==len(authorities),'Duplicate authority')
    vr={r.anchor_id:r for r in v.literal_reviews}
    require(len(vr)==len(v.literal_reviews) and set(vr)==set(unit_by_anchor),'Prior literal review coverage/identity conflict')
    prior={u:[] for u in units};used=set()
```

片段SHA256：c28fdfa8e6ad60f7adbe6a53ceb78054de90f99e78cd7b8c39438de699148910。

### 修改授权与意见记账

路径 services/local_revision_v2.py，函数 parse，行171–188；完整函数至241行，局部摘录。

```python
def parse(value,p):
    ec=Errors()
    if not ec.fields(value,'root','$'):ec.finish()
    ec.check(value.get('context_id')==p.payload['context_id'],'$.context_id','answer_version_context_mismatch')
    edits=value.get('edits');actions=value.get('opinion_actions');good_edits=[];targets={};used_d=set();action_rows=[];seen_o=set()
    if ec.check(type(edits) is list,'$.edits','array_required'):
        for i,e in enumerate(edits):
            path=f'$.edits[{i}]'
            if not ec.fields(e,'edit',path):continue
            u=e.get('unit_ref');valid_u=type(u) is str and u in p.units
            ec.check(valid_u,path+'.unit_ref','current_unit_ref_required')
            if valid_u:
                ec.check(u not in targets,path+'.unit_ref','conflicting_unit_replacement');targets[u]=i
            ds=ec.refs(e.get('authorization_refs'),p.authorities,path+'.authorization_refs','authorization_ref',nonempty=True)
            used_d.update(ds)
            legal={k for k,s in p.sources.items() if valid_u and any(s.evidence_id==x['evidence_id'] for x in p.prior[u]) or any(s.evidence_id==q.evidence_id for d in ds for q in p.authorities[d].sources)}
            ss=ec.refs(e.get('support_refs'),legal,path+'.support_refs','support_source_ref',nonempty=True)
            for d in ds:
```

片段SHA256：fde156157edada85f95c68411719d42b920d829d7d0989fbc93ae99a7f6c55b6。

### 跨语言词项入口

路径 rag/chinese_first.py，函数 lexical，行26–27；完整函数至27行，完整定义。

```python
def lexical(text):
    return tokenize(text) + tuple(w.casefold() for w in re.findall(r'[\u0370-\u03ff]+|[=+*/^<>≤≥−]', text))
```

片段SHA256：34eac82ab0a0f0c47de7edafd71fc66321aa0f691bc60f11ef4d0eb50650fffd。

### 恢复实际输入与知识身份

路径 evaluation/natural_draft_audit_v1.py，函数 recover，行27–44；完整函数至45行，局部摘录。

```python
def recover():
    summary=load(OLD/'batch/summary.json');generated={};origins=[]
    with closing(sqlite3.connect((OLD/'batch/runs.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        for i in range(8):
            ident=f'N{i+1}-C';control=next(r for r in summary['control'] if r['case_id']==ident);rid=control['accepted']['run_id']
            raw=summary['outputs'][rid];path=OLD/'batch'/rid/'result.json';inp=load(OLD/'batch'/rid/'input.json')
            require(load(path)==raw and json.loads(db.execute('SELECT result FROM runs WHERE id=?',(rid,)).fetchone()[0])==raw,'Historical result/Store mismatch')
            req=restore(inp['request'],TaskRequest);gen=restore(raw['generation_output'],GenerationOutput)
            validate_snapshot(gen.evidence_snapshot,gen.answer)
            require(wire(gen.answer)==raw['answer'] and wire(gen.evidence_snapshot.evidence)==raw['evidence'],'Historical natural draft/snapshot mismatch')
            require(wire(gen.evidence_snapshot.evidence_bindings)==raw['evidence_bindings'],'Historical role/binding mismatch')
            require(gen.evidence_snapshot.question==req.question and gen.evidence_snapshot.user_context==req.user_context and gen.evidence_snapshot.engineering_context==req.engineering_context,'Historical question/context mismatch')
            generated[i]=SimpleNamespace(answer=gen.answer,evidence=gen.evidence_snapshot.evidence,generation_output=replace(gen,model_records=()),model_records=(),duration_ms=0,retrieval_records=())
            origins.append(dict(id=f'N{i+1}',old_run_id=rid,request=wire(req),answer_sha256=sha(raw['answer']),evidence_sha256=sha(raw['evidence']),
                bindings_sha256=sha(raw['evidence_bindings']),snapshot_sha256=sha(raw['generation_output']['evidence_snapshot']),
                knowledge_version=gen.evidence_snapshot.knowledge_version,old_generation_records=raw['model_records'],historical_cost_recounted=False,
                origin='archived_natural_generation_only; all initial extraction/fact/domain audits must be fresh',
                files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in (path,OLD/'batch'/rid/'input.json')]))
```

片段SHA256：0aafb6e57a7f5b5ed99e5510729a7a8cb2bf889033eaacd3c596d693f241ba54。

### 一次有界审核批次

路径 evaluation/natural_draft_audit_v1.py，函数 batch，行88–105；完整函数至108行，局部摘录。

```python
async def batch(c,m,generated,root,provider,*,limit=None):
    limit=limit or SendLimit(root)
    async def runner(h,req,budget,**kw):
        i=next(i for i,row in enumerate(m['origins']) if row['request']['question']==req.question);origin=m['origins'][i]
        require(req.existing_answer==generated[i].answer and req.provided_evidence==generated[i].evidence,'Fixed natural input differs')
        require(sha(kw['generation_snapshot'])==origin['snapshot_sha256'],'Real generation snapshot differs')
        require(h.retriever is None and not h.subject_supplement and kw['knowledge_version']==origin['knowledge_version'],'Unexpected retrieval/snapshot scope')
        save(root/kw['run_id']/'audit-origin.json',dict(origin=origin,new_run_id=kw['run_id'],initial_audits='all_fresh',
            archived_generation_bindings_preserved_in_snapshot=True,current_provided_evidence_roles='normal fixed-evidence Harness user_reference; distinct from archived generation core/adjacent roles',
            no_historical_audit_replay=True,historical_cost_recounted=False))
        return await h.run(req,budget,**kw)
    def guard(spec,raw):
        if any(x['code'] in ('MODEL_TIMEOUT','TIMEOUT','MODEL_CANCELLED','CANCELLED') for x in raw.get('execution_issues',[])):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Shared timeout/unknown acceptance; stop new sends')
        if raw.get('generation_output') or raw.get('retrieval_records'):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Unexpected generation/retrieval')
    rows=[dict(id=f'N{i+1}',input=dict(id=f'N{i+1}',line='B',case=i,variant='candidate')) for i in range(8)]
    return await shared.batch(c,m,root,provider,factory_type=Factory,rows=rows,request_builder=request,variant_config=lambda cfg,v:cfg,
```

片段SHA256：02992c4f6c2777c98590b491f3c7ea98ed33bdaed94359d697e52cb2696429ae。

### 固定证据生成诊断入口

路径 evaluation/retrieval_evidence_answer_check_v1.py，函数 run，行186–203；完整函数至216行，局部摘录。

```python
async def run():
    require(not (LOCAL/'attempt.json').exists(),'Unique new attempt only; no resume')
    require(not subprocess.check_output(['git','status','--porcelain','--','agents','backend','core','harness','model_adapter','rag','services','evaluation','tests','tools'],cwd=ROOT,text=True).strip(),'Commit sources first')
    require(not subprocess.check_output(['git','diff',BASE,'--','agents','backend','core','harness','model_adapter','rag','services','tools'],cwd=ROOT),'Business semantics changed')
    m=load(LOCAL/'materials.json');recovered,origins=recover();require(origins==load(LOCAL/'origins.json'),'Prepared origins changed')
    original_materials=load(OLD/'materials.json')
    for key in ('N','rules','reference_sources'):
        require(m[key]==original_materials[key],'Frozen original reference changed: '+key)
    c=ServiceConfig.from_environment()  # sole real-run root .env loader
    require(os.environ.get('DEEPSEEK_MODEL_ID')=='deepseek-flash','Flash only')
    previous=load(OLD/'freeze.json')
    for key in ('profile','decision_policy','execution_path','verification_schema','retrieval_mode','retrieval_execution_profile',
        'fact_strategy','fact_review_contract','local_revision_interface','revision_answer_delivery','review_result_transport',
        'fact_internal_flow','domain_internal_flow','extraction_message_profile','review_message_profile','knowledge_version'):
        require(getattr(c,key)==previous['configuration'][key],'Original configuration differs: '+key)
    c=replace(c,run_db=LOCAL/'batch/runs.sqlite3',budget=replace(c.budget,max_model_calls=2,max_duration_seconds=800,max_transient_retries=0))
    manifest=ComponentFactory(c).manifest(c.knowledge_version,fixed_evidence_only=True)
    require(manifest['prompts']['generation']==previous['manifest']['prompts']['generation'],'Generation prompt differs')
```

片段SHA256：25f9bd3f284cb5574787e52d9d8d53f5df3d0aa86422c901ef757e5529a4c6f0。

::: answer 新源码核对练习：测试14项通过能证明N2被识别吗？
不能。专项证明恢复身份、真初审路径、预算与Store等接缝；自然语义判断必须看实际预测和原文。N2的审核supported恰好表明程序接线正确也可能语义漏检。检查文件哈希能证明教材读的是这份源码，不能证明模型结论正确。
:::

## 既有源码练习（历史题保留）

::: answer 展开新增练习解析
不能。它只证明程序收到该合法声明时不会走旧遗漏路径；真实模型能否作出正确声明、能否识别条件归属，需要固定真实输入逐项核验。不能将新字段或替身标签当语义成绩。
:::

::: answer 展开参考答案1
它可能手工传扩展输入，遗漏真实Factory/Harness构造分支。
:::

::: answer 展开参考答案2
Submit.task构造任务身份；ApplicationService.submit生成运行身份。
:::

::: answer 展开参考答案3
不能；抛HarnessObserverError并报告持久化失败。
:::

## schema13双通道候选的源码边界

候选仍走原Factory和Harness，不另设运行编排。事实先行、引用两项一波；晚索引非法先返回也不能抢先纠正，结果按原次序合并后做覆盖检查。实际HTTP容量由两个原单线程适配器保证，取消await不等于线程已停止。默认serial_v1及v7只读标注不改，真实收益未验证。

### waves

路径 agents/schema13_concurrency_v1.py，实际行33–50，局部摘录，完整函数至63行；取消后的租约归还需继续阅读函数finally。

```python
async def waves(work, check, order):
    """First independent review is serial; later citation waves contain <=2 tasks."""
    async def perform(index):
        try:
            return await check(work[index], index)
        finally:
            order.done[index].set()
    first = await perform(0)
    yield [(work[0], first)]
    if first[2] or current_budget().fatal_error is not None:
        return
    start = 1
    while start < len(work):
        remaining = current_budget().limit - current_budget().used
        # With insufficient slack preserve canonical serial correction priority.
        width = 2 if remaining >= len(work) - start + (not order.used) else 1
        indexes = list(range(start, min(start + width, len(work))))
        tasks = [asyncio.create_task(perform(i)) for i in indexes]
```

### BoundedPairAdapter.complete

路径 model_adapter/bounded_pair_v1.py，实际行17–34，局部摘录，完整函数至43行；取消后的租约归还需继续阅读函数finally。

```python
    async def complete(self, request):
        from model_adapter.contracts import ModelConnectionError
        if self._closed:
            raise ModelConnectionError()
        if self.available is None:
            self.available = asyncio.Queue()
            for child in self.children:
                self.available.put_nowait(child)
        child = await self.available.get()
        loop = asyncio.get_running_loop()
        def release():
            if not self._closed:
                self.available.put_nowait(child)
        try:
            if self._closed:
                raise ModelConnectionError()
            return await child.complete(request)
        finally:
```

## 2026-10-28 来源优先代码入口（默认关闭）

沿backend/config.py的audit_strategy显式选择source_first_audit_v1，并配对literal_v1/source_actions_v2及串行BM25。backend/assembly.py仍装配原四职责和OfflineHarness；harness/source_first_audit_v1.py只提供共享阶段的供给与缺口函数。rag/retriever.py的source_context复用唯一工作线程和KnowledgeStore严格回查；services/source_first_audit_v1.py单独版本化提示，复用原文输出/修订合同。归档还原明确识别候选LiteralAuditReport，不改旧报告。

evaluation/source_first_materials_v1.py先冻结资料；evaluation/source_first_audit_redesign_v1.py只做离线wire预算准入和原子预留测试，本轮未形成获准发送的真实批次。preflight结果是budget_not_admitted，不能当真实配对入口已跑通。实现绑定de16d5efdd2685a81877f92f1d9dd2b27fdac10a，验证工具绑定64e3ca5；生产仍schema13，不切schema14或引用并发。

## 2026-10-28 v3真实入口与归档重读

实现及入口绑定f69a4124f0193708ff5421734a0206efe60a703a。evaluation/source_first_real_v3.py复用原shared.batch/run_fixed、Factory、OfflineHarness、RunStore及四职责，在真实Retriever/KnowledgeStore上先做归档响应回放与确定性模型贯通，再冻结唯一四对；不是新调度器。每链20、全批160硬上限、usage累计300万停发，未知发送/usage停整批，原子发送边界与已在途越过分开记账。

实际29请求/669718token、未决0/越过0，未追加批次。8条真实归档经普通ApplicationService结果读取验证原对象和完整执行；临时小Store副本只恢复正常manifest/真实TaskRequest，不改原归档或复制大库。隔离8766页面用真实库离线固定响应投影验证不足标注与范围，synthetic_fixture不冒充真实模型推理；用户8765未动。

## 2026-10-28 v4版本与入口身份

业务及UI实现绑定2e99786b7940c4b023cfbe4dde5120e6cd04d86e；services/source_first_audit_v2.py只扩展单元比较并复用literal内部对象/校验及原有修订授权，策略/提示/报告标识v2。evaluation/source_first_quality_v4.py复用v3原子记账和shared.batch，非新调度器。类默认仍baseline，显式候选配置才使用v2。

唯一真实批次停止后仅只读工具补充失败档案“不假报完整”的断言，未改业务或恢复；3条普通结果重读保持原对象，S2仍不完整。实际输入响应、来源、ledger及截图留忽略data；公开报告/摘要仅必要脱敏统计。历史v2/v3失败与原分支成绩不改。

## 2026-10-28 v5：隔离入口与冻结源码

实验实现c2ecddfdb7f7ac364c673d25f27f246e5c5d2b62，公开归档adc122754926510a28f4155f85977694d58ac1db。evaluation/source_first_completion_v5.py复用v4材料、v3批次和现有Factory，evaluation/failure_isolation_v5.py只在显式入口启用，旧调用者默认故障政策不变。业务源码与45c39c8相同，source_first_audit_v2及source_actions_v2语义合同未改。

真实批次后普通结果接口重读12条，末稿对象一致，S3基线未完整如实保留；只复制小运行Store做读取，不复制大库或重放POST。原始响应/来源和私有初末稿留忽略data，公开仅必要统计与复核结论。源码身份和构建同步不表示候选启用。

## 2026-10-28 v6：独立版本与源码冻结

实现98de2084e16e3b96a49a973fb634db8b8a946e81，报告归档c7895777ed85c0bc202280752f7cf17996cc6fba。services/source_first_audit_v3.py复用v2一致性解析和literal源目录，backend配置/Factory、Harness来源开关、严格报告白名单及普通范围投影显式认v3；未改v1/v2提示或历史标签。evaluation/source_first_modality_v6.py复用共享批次和v5故障策略，无新调度器。

编码前10材料冻结，旧八份对象不变；真实库10条合成/归档离线路径、1433全套及14实际归档普通读取通过。付费后源码身份未变，原文/响应/实际初末稿与截图只留忽略data，公开仅必要统计。预览夹具简记缺正常request/manifest导致404，补齐规范小Store副本后通过，不能当业务代码被修改或真实批次重跑。

## 2026-10-29 v7：A/B独立身份与默认关闭

A诊断fccd159、边界测试b8782ae，未改运行时SQL；B实现18d4f671e7f073b014ca18e4fdbc32b94e91cb92、报告归档ec9c7df72b3ab628ae5293efbba6039470d9f42c。services/source_first_audit_v4.py复用现有quote/locator与literal解析，reference_ref绑定协议、答案/版本、anchor、知识身份与quote；选择表只指向已有正文，不额外复制池。services/audit_reference_v7.py仅为该候选澄清领域字段，原解析器严格性不变。

LiteralReviewAgent默认payload钩子不改旧wire，Factory/配置/Harness/报告及普通范围投影显式识别v4，旧版本和schema13/baseline默认保留。B真实批次强制原topic_v4_subject_v1 SQL，不混用A潜在收益；付费后源码未改。十条实际普通结果重读原对象一致、全部未完整如实保留，原文和响应只留忽略data。
