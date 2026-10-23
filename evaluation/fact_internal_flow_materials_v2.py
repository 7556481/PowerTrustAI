"""Offline-only v2 revalidation preparation. No execute action or provider creation."""
import asyncio,hashlib,json
from dataclasses import asdict
from pathlib import Path
from agents.fact_flow_v1 import FactFlowAgent
from services.fact_flow_protocol_v2 import create_agent
from evaluation.fact_internal_flow_materials_v1 import CASES,fixed_input
from model_adapter.contracts import ModelSettings
from model_adapter.runtime import ModelBudget,model_scope

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'docs/evaluation/fact-internal-flow-v2'
PRIVATE=ROOT/'data/retrieval_local/fact-internal-flow-v2-preparation'
CASE_IDS=('F01','F02','F03','F04','F05','F08')
SETTINGS=ModelSettings('deepseek-flash',90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

async def prepare():
    rows=[]
    class Captured(BaseException):pass
    for i,cid in enumerate(CASE_IDS):
        case=next(c for c in CASES if c['id']==cid)
        for variant in (('v1','v2') if i%2==0 else ('v2','v1')):
            captured=[]
            class Adapter:
                async def complete(self,r):
                    captured.append(r)
                    raise Captured()
            agent=(FactFlowAgent if variant=='v1' else create_agent)(Adapter(),SETTINGS)
            try:
                with model_scope(ModelBudget(40)):
                    await agent.run(fixed_input(case))
            except Captured:pass
            assert len(captured)==1
            request=captured[0];messages=[asdict(m) for m in request.messages]
            # Capture exactly what the existing model boundary receives, before send.
            identity=hashlib.sha256(json.dumps(messages,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            write(PRIVATE/(cid+'-'+variant+'-messages.json'),{'preparation_only_not_sent':True,'messages':messages})
            rows.append({'case':cid,'variant':variant,'prompt_version':request.prompt_version,
                         'initial_calls':1,'message_sha256':identity})
    write(PUBLIC/'inputs-and-reference-v1.json',{
        'provenance':'Accepted synthetic development cases reused unchanged; not independent held-out tests.',
        'cases':[c for c in CASES if c['id'] in CASE_IDS],
        'F05_layers':{'content':'supported','effective':'not_assessable/review_required','fidelity':'faithful','classification_objection':'explicit nonempty objection required; injected diagnosis, not natural classification accuracy'},
        'reference_never_sent_to_model':True})
    write(PUBLIC/'preparation-v1.json',{'state':'PREPARATION_ONLY_NOT_AUTHORIZED_OR_SENT','model':asdict(SETTINGS),
        'order':rows,'planned_initial_calls':12,'shared_corrections_per_branch':1,'max_total_calls':24,
        'budget_per_branch':40,'request_timeout_seconds':90,'branch_timeout_seconds':110,
        'no_retry_resume_or_supplement':True,'first_unexpected_final_failure_stops_later_branches':True})
    old=json.loads((ROOT/'docs/evaluation/fact-internal-flow-v1/live-freeze-v1.json').read_text(encoding='utf8'))
    paths={x['path'] for x in old['files']}
    paths.update(('services/fact_flow_protocol_v2.py','evaluation/fact_internal_flow_materials_v2.py','tests/test_fact_flow_v2.py'))
    write(PUBLIC/'source-manifest-v1.json',{'state':'PREPARATION_SOURCE_IDENTITIES_NOT_LIVE_FREEZE',
        'files':[{'path':p,'sha256':sha(ROOT/p)} for p in sorted(paths)]})
    print('Prepared 6 unchanged development cases / 12 captured initial messages / 0 provider sends.')

if __name__=='__main__':asyncio.run(prepare())
