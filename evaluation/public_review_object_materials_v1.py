"""Offline input binding for the authorized object-boundary batch."""
from dataclasses import asdict
import json
import hashlib
from evaluation.public_review_validation_materials_v1 import ROOT, sha
from core.models import PremiseTaskRequest,PremiseDeclaration,TaskMode,EngineeringContext,Evidence,AnswerDraft,EvidenceBinding
from core.validation import require,validate_types
from agents.contracts import GenerationInput
from agents.generation import messages_for
from services.task_premises_v1 import catalog,parse_extraction
from services.answer_constraints import character_limit,validate_length,planning_target
PUBLIC=ROOT/'docs/evaluation/public-review-object-v2-live-v1'
ORDER=('OB2-01','OB2-02','OB2-03')
def read(name):return json.loads((PUBLIC/name).read_text(encoding='utf8'))
def build_inputs(document):
    out={}
    require(len(document['branches'])==3,'Exactly three')
    for b in document['branches']:
        v=b['request'];e=tuple(Evidence(**{k:tuple(x) if type(x)==list else x for k,x in row.items()}) for row in v['provided_evidence'])
        a=None if v['existing_answer'] is None else AnswerDraft(**{k:tuple(x) if type(x)==list else x for k,x in v['existing_answer'].items()})
        req=PremiseTaskRequest(v['task_id'],TaskMode(v['mode']),v['scenario_id'],v['question'],user_context=v['user_context'],provided_evidence=e,existing_answer=a,engineering_context=EngineeringContext(goal='conceptual'),premise_declarations=tuple(PremiseDeclaration(**x) for x in v['premise_declarations']))
        require(asdict(req)==v or sha(asdict(req))==sha(v),'Exact request reconstruction')
        value=GenerationInput(req,e,(EvidenceBinding(e[0].evidence_id,'user_reference'),),None,tuple(b['answer_requirements']))
        validate_types(value,GenerationInput);out[req.task_id]=value
    require(tuple(out)==ORDER,'Fixed order')
    return out,None

def identities(values,unused=None):
    rows=[]
    for ident,v in values.items():
        messages=None if ident!='OB2-01' else [asdict(m) for m in messages_for(v,3,product_guidance=True)]
        rows.append({'request_id':ident,'case_id':ident,'mode':v.request.mode.value,'request_sha256':sha(asdict(v.request)),
            'generation_input_sha256':sha(asdict(v)),'premise_catalog_sha256':sha([asdict(p) for p in catalog(v.request)]),
            'initial_generation_messages_sha256':None if messages is None else sha(messages)})
    return rows,None

class FrozenObjectExtractor:
    uses_model_adapter=False
    async def extract_for_task(self,answer,request):
        b=read('inputs-r1.json')['branches'][2]
        require(sha(asdict(request))==sha(b['request']),'Injected extraction task identity')
        require(sha(asdict(answer))==sha(b['request']['existing_answer']),'Injected answer identity')
        return parse_extraction(b['injected_extraction_wire'],answer,request)
    async def extract(self,answer):raise ValueError('Actual task required')

def check():
    old=read('inputs-v1.json');new=read('inputs-r1.json')
    changed=json.loads(json.dumps(old));changed['branches'][0]['answer_requirements'][-1]='中文正文不超过220字符。'
    value=build_inputs(changed)[0]['OB2-01']
    changed['branches'][0]['initial_generation_messages']=[asdict(m) for m in messages_for(value,3,product_guidance=True)]
    changed['branches'][0]['identity']['initial_generation_messages_sha256']=sha(changed['branches'][0]['initial_generation_messages'])
    require(changed==new,'Only approved length and derived messages/hash changed')
    plan=read('freeze-plan-v1.json')
    for x in plan['bound_files']:
        require(hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256'],'Approved materials/source unchanged')
    values,_=build_inputs(new);v=values['OB2-01']
    require(character_limit(v.request.question,v.answer_requirements)==220,'Program strict maximum220')
    messages=messages_for(v,3,product_guidance=True)
    p=json.loads(messages[1].content)['answer_length_constraint']
    require(p['maximum_characters']==220 and p['advisory_target_characters']==165,'Prompt max220 target165')
    validate_length(AnswerDraft('length-fixture',1,'x'*220),v.request.question,v.answer_requirements)
    try:validate_length(AnswerDraft('length-fixture',1,'x'*221),v.request.question,v.answer_requirements)
    except ValueError:pass
    else:raise ValueError('221 must fail')
    b=new['branches'][2];parse_extraction(b['injected_extraction_wire'],values['OB2-03'].request.existing_answer,values['OB2-03'].request)
    print('Only length input changed; program/prompt max220 advisory165; 221 rejected; injected identity valid')
if __name__=='__main__':check()
