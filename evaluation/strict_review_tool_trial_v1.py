"""One fixed strict-carrier validation. No new controller, reviewer or semantic fields."""
from dataclasses import replace
import hashlib,json
from backend.config import ROOT
from evaluation import production_review_v2 as base
from evaluation import review_simple_trial_v1 as simple
from evaluation.public_review_validation_trial_v1 import read
from services.review_simple_tool_v1 import ToolCatalog,PROMPT,SYSTEM
from model_adapter.strict_review_tool import specification,VERSION
from model_adapter.contracts import ModelRequest,ModelMessage,ModelSettings
from model_adapter.deepseek import DeepSeekAdapter

PUBLIC=ROOT/'docs/evaluation/strict-review-tool-v1'
LOCAL=ROOT/'data/retrieval_local/strict-review-tool-v1'
request=base.request
fixed_input=base.fixed_input
task_runner=base.task_runner


def materials():return read(simple.LOCAL/'materials.json')


def order():
    old= simple.order();byid={x['id']:x for x in old};names=['A1-simple_v1','A3-simple_v1','A1-production']
    for i in range(2,9):
        if i!=3:names.append(f'A{i}-simple_v1')
        names.append(f'A{i}-production')
    rows=[byid[n] for n in names]+[x for x in old if x['input']['line']!='A']
    return [dict(id=x['id'].replace('simple_v1','strict_tool_v1'),input={**x['input'],'variant':x['input']['variant'].replace('simple_v1','strict_tool_v1')}) for x in rows]


def variants(c,v):return replace(c,fact_review_contract='simple_v1' if v=='strict_tool_v1' else 'production',review_result_transport='strict_tool_v1' if v=='strict_tool_v1' else 'json')


class Gate(simple.ContractRecurrence):
    def __init__(self):super().__init__(variant='strict_tool_v1',prompt=PROMPT,stages=(simple.CONTRACT,VERSION,'json_parse'))
    def __call__(self,spec,raw):
        recurrence=super().__call__(spec,raw)
        if recurrence:return recurrence
        if spec['line']=='A' and spec['variant']=='strict_tool_v1' and spec['case'] in (0,2) and (raw.get('execution_issues') or raw['state']!='completed'):
            return dict(component='service',code='SERVICE_EXECUTION_FAILED',message='Strict carrier admission A1/A3 did not complete; remaining fixed batch stopped, no alternate parameters or resend.',admission_case=spec['case']+1)
        return None


async def batch(*args,**kwargs):return await simple.shared_batch(*args,**kwargs,result_guard=Gate())


def freeze():
    m=materials();adapter=DeepSeekAdapter(ModelSettings('deepseek-flash'))
    try:
        for i in range(8):
            cat=ToolCatalog(fixed_input(request(m,i,draft=True)))
            for group in ([t for t,x in cat.targets.items() if x['kind']=='fact'],[t for t,x in cat.targets.items() if x['kind']=='citation']):
                msg=(ModelMessage('system',SYSTEM),ModelMessage('user',json.dumps(cat.payload(group),ensure_ascii=False)))
                adapter.validate_request(ModelRequest('deepseek-flash',msg,8000,PROMPT,result_tool=specification()))
    finally:adapter.close()
    return base.freeze(public=PUBLIC,local=LOCAL,materials_factory=materials,order_factory=order,version='strict-review-tool-v1',additional_identity=dict(transport=VERSION,schema=specification(),prompt=PROMPT,system_sha256=hashlib.sha256(SYSTEM.encode()).hexdigest(),projection='simple-condition-projection-v1.1',admission='A1/A3 strict candidate first; legal complete outputs required, no semantic agreement gate.',baseline_a1='New production A1 executed once because Factory/config transport code identity changed; old A1 not counted as same-batch pair.'))


def execute():return base.execute(public=PUBLIC,local=LOCAL,order_factory=order,variants_factory=variants,result_guard=Gate())
