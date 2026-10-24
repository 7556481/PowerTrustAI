"""Patched simple_v1 admission and fixed batch; reuses the existing sole controller."""
import hashlib,json
from evaluation import production_review_v2 as base
from evaluation import review_simple_trial_v1 as old
from evaluation.public_review_validation_trial_v1 import read,sha
from backend.config import ROOT
from services.review_simple_v1 import SimpleCatalog,SYSTEM,PROMPT,CONTRACT
from model_adapter.deepseek import json_mode_preflight
from model_adapter.contracts import ModelRequest,ModelMessage

PUBLIC=ROOT/'docs/evaluation/review-simple-patch-v1'
LOCAL=ROOT/'data/retrieval_local/review-simple-patch-v1'
request=base.request
fixed_input=base.fixed_input
task_runner=base.task_runner
variants=old.variants


def materials():
    # Frozen questions/references/source bytes from the stopped batch, not regenerated.
    return read(old.LOCAL/'materials.json')


def order():
    rows=old.order();byid={x['id']:x for x in rows}
    names=['A1-simple_v1','A2-simple_v1','A2-production']
    for i in range(3,9):names.extend((f'A{i}-simple_v1',f'A{i}-production'))
    return [byid[n] for n in names]+[x for x in rows if x['input']['line']!='A']


def history_identity():
    summary=read(old.LOCAL/'batch/summary.json');control=next(x for x in summary['control'] if x['case_id']=='A1-production');rid=control['accepted']['run_id']
    inp=read(old.LOCAL/'batch'/rid/'input.json');current=base.wire(request(materials(),0,draft=True))
    if sha(inp['request'])!=sha(current):raise ValueError('Historical A1 input differs')
    frozen=read(old.PUBLIC/'freeze.json');identity=[]
    # Support semantics are unchanged; public transport safety intentionally differs.
    files=('agents/verification_contract_v10_batched.py','agents/verification_contract_v9.py','agents/verification_contract_v9_scoped.py','services/support_relation_v6.py','services/quote_candidates.py','services/scoped_candidates.py','services/answer_anchors.py','services/claim_obligations.py','core/validation.py','backend/config.py','backend/assembly.py')
    prior={x['path']:x['sha256'] for x in frozen['files']}
    for name in files:
        h=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        if h!=prior[name]:raise ValueError('Historical A1 business identity differs: '+name)
        identity.append(dict(path=name,sha256=h))
    sends=[x for x in summary['send_log'] if x['run_id']==rid]
    if any(x['parameters']!=dict(model_id='deepseek-flash',max_output_tokens=8000) for x in sends):raise ValueError('Historical A1 model parameters differ')
    return dict(id='A1-production',historical_reference=True,not_same_batch_pair=True,run_id=rid,input_sha256=sha(inp),matching_request_sha256=sha(current),model_parameters=sends[0]['parameters'],business_files=identity,summary_sha256=hashlib.sha256((old.LOCAL/'batch/summary.json').read_bytes()).hexdigest(),old_result_sha256=hashlib.sha256((old.LOCAL/'batch'/rid/'result.json').read_bytes()).hexdigest(),no_new_cost=True)


class Gate(old.ContractRecurrence):
    def __call__(self,spec,raw):
        recurrence=super().__call__(spec,raw)
        if recurrence:return recurrence
        if spec['line']=='A' and spec['variant']=='simple_v1' and spec['case'] in (0,1) and (raw.get('execution_issues') or raw['state']!='completed'):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Admission A1/A2 did not obtain a legal final result; remaining fixed batch stopped. No repeat.',admission_case=spec['case']+1)
        return None


async def batch(*args,**kwargs):return await old.shared_batch(*args,**kwargs,result_guard=Gate())


def freeze():
    m=materials()
    for i in range(8):
        cat=SimpleCatalog(fixed_input(request(m,i,draft=True)))
        for group in ([t for t,x in cat.targets.items() if x['kind']=='fact'],[t for t,x in cat.targets.items() if x['kind']=='citation']):
            messages=(ModelMessage('system',SYSTEM),ModelMessage('user',json.dumps(cat.payload(group),ensure_ascii=False)))
            json_mode_preflight(ModelRequest('deepseek-flash',messages,8000,PROMPT))
    return base.freeze(public=PUBLIC,local=LOCAL,materials_factory=materials,order_factory=order,version='review-simple-patch-v1',additional_identity=dict(historical_reference=history_identity(),candidate=dict(prompt=PROMPT,contract=CONTRACT,projection='simple-condition-projection-v1.1',system_sha256=hashlib.sha256(SYSTEM.encode()).hexdigest()),admission='A1/A2 candidate are first and included; any incomplete admission stops remaining sends; no paid probe.'))


def execute():
    f=read(PUBLIC/'freeze.json')
    if f['additional_identity']['historical_reference']!=history_identity():raise ValueError('Historical reference identity changed')
    return base.execute(public=PUBLIC,local=LOCAL,order_factory=order,variants_factory=variants,result_guard=Gate())
