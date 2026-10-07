# 14 核心源码阅读路线：输入、调用、异常与取舍

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

本章代码摘录由write-excerpts脚本按AST函数/实际行号读取当前源码，记录文件及片段SHA。省略的部分明确是摘录，不当完整函数。你可以从同名函数继续读上下文。正文解释的是责任，代码才是异常和字段的最终依据。

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

## 沿一条实际请求完整阅读：谁创建对象，谁保存事实

以下基于当前函数，不是另建示意调度器。先看教学对象，再沿十步追字段；schema14上轮包装遗漏在真实Harness中，直接组件测试绕过该输入构造。日常仍默认13。integration-learning-v2历史阶段统一输入能力并完成Factory回归；该轮唯一烟测634a22…已发Fact请求，但条件/basis ID非法而未完整，当轮未开启新批次。后续schema-choice-v1已完成固定8题13/14对照，并另列正常服务及2ω→ω实质修订全重审；详见[第08章后续对照](08-verification.md)。这里的“唯一烟测”只指历史阶段，不代表至今只有一次验证。

### 一个贯穿对象的synthetic摘要

```json
{
  "example_kind": "synthetic_fixture, 教学对象摘要，不是完整API wire",
  "task": {"task_id": "synthetic-task-01", "mode": "question_answer", "question": "只解释这个教学装置在条件C下的许可电压"},
  "evidence": {"evidence_id": "synthetic-evidence-01", "source_type": "synthetic_fixture", "text": "在条件C下，这个教学装置的许可电压为3kV。", "locator": "教学正文字符[0,n)"},
  "answer": {"answer_id": "synthetic-answer-01", "version": 1, "text": "在条件C下，教学装置的许可电压为3kV。", "citation": "绑定同一正文单元与synthetic-evidence-01"},
  "claim": {"claim_id": "synthetic-claim-01", "component_id": "synthetic-part-01", "proposition": "在条件C下，教学装置的许可电压为3kV。", "basis_target": "technical_content", "verification_obligation": "technical_truth"},
  "finding": {"finding_id": "synthetic-finding-01", "answer_version": 1, "status": "supported", "basis": "当前实际交付正文中程序绑定的quote", "reason": "教学固定响应保留相同装置、数值和条件"},
  "disposition": {"kind": "pass仅在所需检查/原引用完成且无阻断时", "resolution": "完整", "execution_integrity": "complete"}
}
```

这些是教学身份和固定判断，不冒充原始官方资料或真实模型正确率。现实ID/哈希/区间由程序产生。许可值的正文依据与3kV→3000V单位工具是两个对象：工具只验证前缀换算，不能证明装置许可值。若独立/原引用或领域义务没完成，即使这个finding为supported，处置也不能pass。

### 1 API：普通字段变成任务，不把浏览器当路径输入器

backend/api.py的Submit是严格Pydantic模型，未知字段拒绝。Submit.task检查两种mode与existing_answer一致，建立task_id；已有回答也建立answer_id、version1，indexed引用按fragment ID回查转正式Evidence。create_app内submit路由先校验现有引用区间/固定库，调用service.submit后返回202/run_id。浏览器不设置本机模型路径，也不拿DeepSeek密钥。

### 2 接受：先持久化，再让worker取任务

ApplicationService.submit验证TaskRequest/预算、配置preflight及队列；rid=uuid4产生run_id，factory.manifest记录代码/知识/协议，RunStore.create保存request/config。async lock保护队列接收与状态；保存失败不能返回假接受。先生成run_id不是完成审核，UI随后GET状态。任务和运行身份分开，原问题相同也不是同一run。

### 3 worker与Factory：装配真实组件，而非模拟回退

ApplicationService._worker取得队列项，mark running，factory.create(rid, observer)产生Bundle；observer是lambda snapshot: store.checkpoint(rid,snapshot)。ComponentFactory.create建立两个适配器、固定Retriever、四Agent、Extractor、单位工具和Product政策，注入已有OfflineHarness。它不调用evaluation脚本，也不另建业务调度器；构造失败清资源并ConfigurationError。

### 4 Harness输入与冻结：版本对象的起点

OfflineHarness.run收到TaskRequest、RunBudget、knowledge_version和run_id。问答检索/生成，已有回答直接用原AnswerDraft。invoke统一预算、deadline、ModelContext和异常；record产生事件并通知observer。Generation快照须保留实际Evidence与知识版本。无实质回答有明确不适用终态，不能把程序拒答当真实答题继续审核。

### 5 提取：原锚点→规范命题→组件

ModelClaimExtractor.extract(protocol7)由answer_anchors提供原文锚点，模型选anchor_id，程序绑定区间。parse_extraction/claim_obligations检查覆盖、立场和义务，不能悄悄改错答案。这里生成的claim_id/component_id属于当前answer版本；对象与输入原文不同步会成为忠实性异议。

### 6 工具与交付：类型成立才可作为依据

requests_for按受支持数值/单位组织真实工具调用，保存ToolResult/current_tools；这不是通用P/Q求解。retrieve_for分别组织Verification/Domain用途交付，保留每版本的EvidenceBinding与RetrievalRecord。独立审核只收到这一轮允许资料，不把全部库或旧运行池借过来。

### 7 双审输入和并发：上轮遗漏恰在这里

基础EvidenceVerificationInput只有request/answer/claims/evidence/快照；ReliabilityVerificationInput另含tool_results、delivery_summary和fact_retrieval_bindings。上轮runtime只按schema9–13做包装，14在ModelAgent开始前就缺字段。组件测试手工给扩展输入绕过了这一行。

事实与领域输入绑定同一answer/claims，各自允许不同Evidence用途。reviewers通过create_task/gather并发等待；异常不能使有效peer变无效。schema13/14决定解析入口，不应让散落版本条件决定是否携带本该提供的数据。本轮由ModelAgent.review_input_type声明扩展类型，services/review_inputs.build构造输入；历史未声明的注入组件在同处保留兼容映射。已用Factory→Harness→真实parser的synthetic贯通核对，而不是声称一个内部函数成功就接好线。

### 8 政策：读有效发现，不再问模型投票

ProductAuditPolicy.decide_context读取执行问题、typed支持、异议、原引用与领域范围。parent状态由组件聚合；支持、严重度、处置、解决程度分开。缺执行先禁止放行，未解决异议复核；明确已选原文的可修复缺陷可一次Revision，真正缺输入仍保留。raw supported不覆盖保守effective状态。

### 9 Revision：新对象重建，旧版不抹去

RevisionInput包含当前发现和合法依据，check_revision检查实际修改/绑定。成功后answer=revised.answer，version递增，保存revision_outputs和旧ReviewRound；循环回提取，current_tools和审核对象按新版本重建。verification/domain/report临时清空，防v1结论沿用v2。对象索引按run/answer/version保存，旧错误与反馈继续可读。

### 10 observer、事务、结果与UI

record给observer一个阶段快照，包括事件、已完成对象、review_rounds、usage和执行问题。RunStore.checkpoint在短tx中写event、snapshot并index对象，tx的BEGIN IMMEDIATE/commit/rollback不跨网络等待。observer异常转HarnessObserverError，不能称保存完成。

worker最终store.mark保存result，ApplicationService.result经store读取/结果投影，API GET result和trace返回安全视图。backend/static/app.js的renderAnswers/renderTrace及结果装载中的decision区域构建用保存结果展示；GET/刷新不启动Harness、Revision或NLI补算。UI展示改善和旧结论不修改是两种责任。

### 如何亲自验证这条路线

对同一synthetic任务记录Factory实际组件类、Harness收到/转成的输入类、真正parser收的payload、Trace状态、Store对象和API结果。问答与已有回答都走，不模拟替换Harness本身；测试有成功工具basis、多个原引用scope、Revision后两轮提取/双审和不同版本保存。捕获共享装配故障时，提交执行器应先落已发请求/部分结果再停止后续，而非把AttributeError当单题语义差。

## 本轮完整路线的实际代码摘录

每段给出实际行号，短段结束明确标“后续行省略”；省略不改变语义判断，不是可独立运行的全部函数。

### 摘录：Task/Answer身份与引用绑定

backend/api.py / Submit.task，实际行54–67。

```python
    def task(self,indexed_evidence=()):
        if not self.question.strip() or self.existing_answer is not None and not self.existing_answer.strip():raise InputError('Nonempty question/answer required')
        if (self.mode=='assess_existing')!=(self.existing_answer is not None):raise InputError('Existing answer required only for assess_existing')
        if self.existing_citations and self.mode!='assess_existing':raise InputError('Citation bindings require existing answer')
        if any(len(s)>4000 for s in self.answer_requirements):raise InputError('Answer requirement too long')
        aid=uuid4().hex
        by_fragment={e.provenance.fragment_id:e.evidence_id for e in indexed_evidence}
        citations=tuple(CitationBinding(c.start_offset,c.end_offset,tuple(by_fragment[f] for f in c.fragment_ids)) for c in self.existing_citations)
        answer=None if self.existing_answer is None else AnswerDraft(aid,1,self.existing_answer,citations=citations)
        refs=tuple(Evidence('user-'+uuid4().hex,'user_supplied','unverified',r.label,r.text,'user_reference') for r in self.references)
        e=self.engineering_context
        engineering=None if e is None else EngineeringContext(e.goal,e.network_model,e.operating_point,e.limits,
            tuple(e.contingencies),tuple(EngineeringQuantity(uuid4().hex,q.kind,q.value,q.unit,q.reference) for q in e.quantities))
        return TaskRequest(uuid4().hex,TaskMode(self.mode),'voltage_stability_reactive_support',self.question,self.user_context,answer,refs+tuple(indexed_evidence),engineering)
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：API接收与异常返回

backend/api.py / create_app.submit，实际行228–247。

```python
    async def submit(body:Submit,request:Request):
        try:
            indexed=()
            if body.existing_citations:
                if config.profile!='real':raise InputError('Indexed references require real knowledge snapshot')
                if body.mode!='assess_existing' or body.existing_answer is None:raise InputError('Existing answer required')
                for c in body.existing_citations:
                    if not 0<=c.start_offset<c.end_offset<=len(body.existing_answer):raise InputError('Citation span outside answer')
                import asyncio
                def resolve():
                    from rag.storage import KnowledgeStore
                    ids=tuple(dict.fromkeys(f for c in body.existing_citations for f in c.fragment_ids))
                    with KnowledgeStore(config.index_db,readonly=True) as index:
                        return tuple(index.evidence(f,config.knowledge_version) for f in ids)
                indexed=await asyncio.to_thread(resolve)
            rid=await svc(request).submit(body.task(indexed),answer_requirements=tuple(body.answer_requirements),
                indexed_reference_ids=tuple(e.evidence_id for e in indexed),nli_enabled=body.local_nli_enabled)
        except InputError as exc:
            if str(exc).startswith('Complete citation scopes exceed configured capacity; citation_indexes='):
                raise HTTPException(422,detail={'code':'REVIEW_MESSAGE_CAPACITY_EXCEEDED',
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：保存接受和队列

backend/service.py / ApplicationService.submit，实际行56–81。

```python
    async def submit(self,request,*,answer_requirements=(),indexed_reference_ids=(),nli_enabled=None):
        validate_request(request,self.config.budget)
        selected=self.config.nli_enabled if nli_enabled is None else nli_enabled
        if type(selected) is not bool:raise ValueError('NLI selection must be boolean')
        if selected and nli_enabled is not None:
            from core.validation import InputError
            if not self.nli_capability()['available']:raise InputError('Local NLI not configured/available; disable the optional selection')
            await self.ensure_nli() # A load failure is diagnostic only; the audit still runs.
        knowledge=self.factory.preflight()
        if self.config.profile=='real' and request.existing_answer and request.existing_answer.citations:
            from services.citation_workload import submission_rejections
            from core.validation import InputError
            rejected=submission_rejections(request,knowledge,self.config.verification_schema,self.config.citation_workload)
            if rejected:raise InputError('Complete citation scopes exceed configured capacity; citation_indexes='+str(list(rejected)))

        async with self.lock:
            if self.closing or self.storage_fault:raise ServiceUnavailable('Service not accepting work')
            if self.queue.full():raise QueueFullError('Waiting queue is full')
            rid=uuid4().hex;manifest=self.factory.manifest(knowledge)
            manifest['answer_requirements']=answer_requirements
            manifest['indexed_reference_ids']=indexed_reference_ids
            manifest['local_nli_diagnostic']={'version':'local-nli-task-selection-v1','enabled':selected,'authority':'diagnostic_only','affects_decision':False}
            manifest['local_nli_diagnostic'].update(load_status='ready' if selected and self.nli and self.nli.identity and not self.nli.failure else 'failed' if selected else 'not_requested',load_error=self.nli.failure if selected and self.nli else None)
            self.store.create(rid,request,manifest)
            self.queue.put_nowait((rid,request,knowledge,answer_requirements,indexed_reference_ids))
        return rid
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：worker装配和最终保存

backend/service.py / ApplicationService._worker，实际行100–126。

```python
    async def _worker(self):
        while not self.closing:
            if self.storage_fault:return
            rid,request,knowledge,requirements,indexed_ids=await self.queue.get()
            bundle=None
            try:
                if self.store.get(rid)['status']!='queued':continue
                self.active=rid;self.store.mark(rid,'running')
                bundle=self.factory.create(rid,lambda snapshot:self.store.checkpoint(rid,snapshot))
                self.active_bundle=bundle
                result=await bundle.harness.run(request,self.config.budget,knowledge_version=knowledge,
                    answer_requirements=tuple(requirements),indexed_reference_ids=tuple(indexed_ids),run_id=rid)
                status='interrupted' if self.closing else 'cancelled' if result.state.value=='cancelled' else 'failed' if result.state.value=='failed' else 'finished'
                self.store.mark(rid,status,error_code='PROCESS_INTERRUPTED' if self.closing else None,result=result)
                if self.nli and not self.closing and self.store.get(rid)['config'].get('local_nli_diagnostic',{}).get('enabled',self.config.nli_enabled):
                    task=asyncio.create_task(self.diagnose_completed(rid,wire(result)),name='local-nli:'+rid)
                    self.nli_tasks.add(task);task.add_done_callback(self.nli_tasks.discard)
            except asyncio.CancelledError:
                try:self.store.mark(rid,'interrupted',error_code='PROCESS_INTERRUPTED')
                except StorageError:self.storage_fault=True;self.volatile_errors[rid]='RUN_STORAGE_FAILED'
                raise
            except (StorageError,HarnessObserverError):
                self.storage_fault=True;self.volatile_errors[rid]='RUN_STORAGE_FAILED'
                try:self.store.mark(rid,'interrupted',error_code='RUN_STORAGE_FAILED')
                except StorageError:pass
            except Exception:
                try:self.store.mark(rid,'failed',error_code='SERVICE_EXECUTION_FAILED')
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：真实装配的资源建立

backend/assembly.py / ComponentFactory.create，实际行143–158。

```python
    def create(self,rid,observer):
        if self.config.profile=='synthetic_fixture':
            from agents.fakes import make_fake_harness
            harness=make_fake_harness();harness.observer=observer
            if self.config.decision_policy=='product-v1':
                from harness.product_policy import ProductAuditPolicy
                harness.policy=ProductAuditPolicy(synthetic_fixture=True)
            return Bundle(harness)
        from agents.generation import EvidenceGenerationAgent
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from agents.power_domain_review import ModelPowerDomainReviewAgent
        from agents.revision import ModelRevisionAgent
        from services.claim_extractor import ModelClaimExtractor
        from tools.unit_conversion import UnitConversionTool
        from model_adapter.contracts import ModelSettings
        from model_adapter.deepseek import create_adapter
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：原锚点输入与实际解析选择

services/claim_extractor.py / ModelClaimExtractor.extract，实际行142–157。

```python
    async def extract(self, answer):
        if self.protocol_version in (5,6,7):
            from services.answer_anchors import anchors,parse,SYSTEM as anchor_system
            if self.protocol_version==6:
                from services.answer_basis_targets import parse,SYSTEM as anchor_system
            if self.protocol_version==7:
                from services.claim_obligations import parse,SYSTEM as anchor_system
                if self.daily_guidance:
                    from services.claim_obligations import DAILY_SYSTEM as anchor_system
            payload={'answer_id':answer.answer_id,'answer_version':answer.version,'ANSWER_ANCHORS':anchors(answer),
                'assumptions':answer.assumptions,'missing_information':answer.missing_information}
            path=None if self.diagnostics is None else self.diagnostics.save_scope(payload)
            output,_=await structured_request(self.client,(ModelMessage('system',anchor_system),ModelMessage('user',json.dumps(payload,ensure_ascii=False))),
                ('atomic-claims-v7-obligations-faithful-assertions-v2' if self.daily_guidance else 'atomic-claims-v7-obligations') if self.protocol_version==7 else 'atomic-claims-v6-basis-target-anchors' if self.protocol_version==6 else 'atomic-claims-v5-program-anchors',lambda v:parse(v,answer),diagnostics=self.diagnostics,
                response_contract_version='atomic-claims-v'+str(self.protocol_version),candidate_catalog_path=path)
            return output
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：政策上下文，不是另一个模型

harness/product_policy.py / ProductAuditPolicy.decide_context，实际行24–40。

```python
    def decide_context(self, verification, domain, budget, revision_round, *, request,
                       answer, claims, extraction, issues, retrieval):
        facts, findings = verification.findings, domain.findings
        ids = tuple(f.finding_id for f in facts if f.status != V.SUPPORTED) + tuple(
            f.finding_id for f in findings if f.check_status in ('warning', 'not_assessable')
            or f.severity == Severity.HIGH)
        context = request.engineering_context
        scope = context.goal if context else 'unknown'
        basis = ('User requested scope: ' + scope,
                 'Claim components and independent analysis_scope check retain technical truth obligations',
                 'Classification is fallible; scope alone never overrides an adverse finding')
        checks = [('fact_support', 'applicable', 'Every extracted claim must have independent verification'),
                  ('original_citations', 'applicable' if answer.citations else 'not_applicable',
                   'Separate original citation judgments' if answer.citations else 'No original citations')]
        for claim in claims:
            basis += (f'{claim.claim_id}: type={claim.claim_type}; assertion_role={claim.assertion_role}; model classification is not proof',)
            for component, target in zip(claim.components, getattr(claim, 'component_basis_targets', ())):
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：阶段与对象短事务

backend/store.py / RunStore.checkpoint，实际行89–100。

```python
    def checkpoint(self,rid,snapshot):
        v=wire(snapshot);event=v['event']
        with self.tx():
            ordinal=self.db.execute('SELECT COUNT(*) FROM events WHERE run_id=?',(rid,)).fetchone()[0]+1
            self.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',(rid,event['event_id'],ordinal,dumps(event),dumps(v.get('stage_output'))))
            self.db.execute('UPDATE runs SET snapshot=?,harness_state=? WHERE id=?',(dumps(v),v['state'],rid))
            # Bind domain finding IDs to this frozen answer; domain findings already have explicit bindings.
            self.index(rid,v)
            if v.get('stage_output') and event['component']=='evidence_verification':
                answer=v['stage_output'];aid=answer['answer_id'];version=answer['answer_version']
                for f in answer['findings']:
                    self.index(rid,dict(f,answer_id=aid,answer_version=version))
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 摘录：保存结果到安全投影

backend/service.py / ApplicationService.result，实际行163–187。

```python
    def result(self,rid):
        row=self.store.get(rid);raw=row['result'] or row['snapshot']
        if raw is None:return {'execution':self.state(rid),'result_available':False,'reason':'No stage result persisted yet'}
        raw=dict(raw)
        if row['result'] is None:
            # Use already persisted valid sibling outputs, not a second execution.
            names={'generation':'generation_output','claim_extraction':'extraction_output',
                   'evidence_verification':'verification_output','power_domain_review':'domain_output'}
            for stage in self.store.events(rid):
                name=names.get(stage['event']['component']);output=stage['stage_output']
                if not name or not isinstance(output,dict):continue
                if output.get('answer_version') is not None and raw.get('answer') and output['answer_version']!=raw['answer']['version']:continue
                if raw.get(name) is None:raw[name]=output
        report=raw.get('report');decision=None if not report else report['decision']
        rounds=raw.get('review_rounds',[])
        issues=list(raw.get('execution_issues',[]))
        for output in (raw.get('verification_output'),raw.get('domain_output')):
            if output:issues+=output.get('execution_issues',[])
        current_version=(raw.get('answer') or {}).get('version')
        no_answer=(raw.get('generation_output') or {}).get('substantive_answer') is False
        if no_answer and not issues:complete=True
        complete=bool(rounds) and rounds[-1]['answer']['version']==current_version and all(not r[k].get('execution_issues') for r in rounds for k in ('verification','domain_review')) and not issues
        verification=raw.get('verification_output') or {};domain=raw.get('domain_output') or {}
        original=row['request'].get('existing_answer')
        if original is None and raw.get('generation_output'):original=raw['generation_output']['answer']
```
只摘录该函数入口/关键部分，省略后续实现；沿当前源码继续阅读。

### 关键连接：实际Harness组件注入

backend/assembly.py实际行176–185，仅连接处摘录，周围初始化/后续逻辑省略。

```python
            harness=OfflineHarness(EvidenceGenerationAgent(model,settings,diagnostic_dir=diag,schema_version=3,product_guidance=self.config.decision_policy=='product-v1'),
                ModelEvidenceVerificationAgent(model,settings,diagnostic_dir=diag,schema_version=self.config.verification_schema,citation_workload=self.config.citation_workload,support_relation_checks=True,support_relation_version=5),
                ModelPowerDomainReviewAgent(domain_model,settings,diagnostic_dir=diag,protocol_version=5,safety_review=True),
                ModelRevisionAgent(model,settings,diagnostic_dir=diag,protocol_version=2,clean_answer_body=True),
                ModelClaimExtractor(model,settings,diagnostic_dir=diag,typed_components=True,protocol_version=7,daily_guidance=self.config.decision_policy=='product-v1'),
                policy=self.product_policy(),retriever=retriever,retrieval_settings=RetrievalSettings(fact_strategy=self.config.fact_strategy),unit_tool=UnitConversionTool(version='scalar-si-conversion-v2'),observer=observer,
                generation_query_converter=GenerationQueryConverter(model,settings,diag) if self.config.retrieval_mode=='bm25' else None,
                generation_corpus_english=corpus_english)
            harness.subject_supplement=True
            return Bundle(harness,resources)
```

### 关键连接：按输入契约包装，而非散落版本条件

harness/runtime.py实际行432–438，仅连接处摘录，周围初始化/后续逻辑省略。

```python
                from services.review_inputs import build as build_review_input
                summary=lambda delivery:__import__('json').dumps(__import__('dataclasses').asdict(delivery.record)) if retrieval else ''
                v_input=build_review_input(self.verification,v_input,tool_results=current_tools,
                    delivery_summary=summary(vd) if retrieval else '',
                    fact_retrieval_bindings=vd.record.fact_bindings if retrieval else ())
                d_input=build_review_input(self.domain_review,d_input,tool_results=current_tools,
                    delivery_summary=summary(dd) if retrieval and not evidence_only else '')
```

### 关键连接：并发双审和异常收尾

harness/runtime.py实际行477–488，仅连接处摘录，周围初始化/后续逻辑省略。

```python
                reviewers = [asyncio.create_task(job) for job in (
                    review("evidence_verification", self.verification, v_input, merge_evidence(v_evidence, original_evidence), True, v_retrieval_issue),
                    review("power_domain_review", self.domain_review, d_input, d_evidence, False, d_retrieval_issue),
                )]
                try:
                    (verification, v_issue), (domain, d_issue) = await asyncio.gather(*reviewers)
                except BaseException:
                    for reviewer in reviewers:
                        reviewer.cancel()
                    await asyncio.gather(*reviewers,return_exceptions=True)
                    raise
                if v_issue:
```

### 关键连接：修订后重建与旧轮次保留

harness/runtime.py实际行600–613，仅连接处摘录，周围初始化/后续逻辑省略。

```python
                answer = revised.answer
                revision_outputs.append(revised)
                active_snapshot = revised.evidence_snapshot
                evidence = merge_evidence(evidence, revised.evidence)
                collect_agent_evidence(revised.evidence)
                record("revision_changes", ExecutionStatus.SUCCEEDED, perf_counter(),
                       "; ".join(change.description for change in revised.changes),
                       outputs=(f"{answer.answer_id}@{answer.version}",))
                rounds += 1
                verification = domain = None
                report = None
        except HarnessObserverError:
            raise
        except RequiredRetrievalFailure as exc:
```

## 三道自测：先作答，再展开

### 自测1：为什么直接组件测试不够？

::: answer 展开参考答案1
它可能手工传扩展输入，遗漏真实Factory/Harness构造分支。
:::

### 自测2：task_id和run_id在哪里产生？

::: answer 展开参考答案2
Submit.task构造任务身份；ApplicationService.submit生成运行身份。
:::

### 自测3：observer失败还能声称结果保存吗？

::: answer 展开参考答案3
不能；抛HarnessObserverError并报告持久化失败。
:::
