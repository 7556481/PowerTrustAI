"""Public synthetic fixed fact-only comparison materials; never calls a model."""
from dataclasses import replace
import json
from pathlib import Path
from core.models import AnswerDraft,Evidence,PremiseTaskRequest,PremiseDeclaration,TaskMode
from agents.contracts import ReliabilityVerificationInput
from services.answer_anchors import anchors
from services.claim_obligations import parse

CASES=[
 {'id':'F01','topic':'library','question':'复述规则并判断本次借阅。','premises':['读者年龄为19岁。','卡片为蓝色。'],
  'body':'合成图书馆规则：年龄至少18岁可借阅档案，但并非必须借阅。',
  'answer':'年龄至少18岁可借阅档案，但并非必须借阅。本次读者19岁，因此可借阅档案。',
  'components':[('年龄至少18岁可借阅档案，但并非必须借阅。','literature_rule','supported',[]),('本次读者19岁，因此可借阅档案。','rule_application','supported',[0])]},
 {'id':'F02','topic':'freezer','question':'按规则判断样本能否入库。','premises':['样本温度为8度。'],
  'body':'合成样本规则：只有温度不高于4度的样本才允许入库。',
  'answer':'样本温度为8度，故符合不高于4度的条件，可以入库。',
  'components':[('样本温度为8度，故符合不高于4度的条件，可以入库。','rule_application','contradicted',[0])]},
 {'id':'F03','topic':'course','question':'判断本次课程报名资格。','premises':['学分为24。','背包为绿色。','学生编号为88。'],
  'body':'合成课程规则：学分至少20即可报名。', 'answer':'学分为24，因此满足至少20学分的报名条件。',
  'components':[('学分为24，因此满足至少20学分的报名条件。','rule_application','supported',[0])]},
 {'id':'F04','topic':'score','question':'比较题设分数与正文阈值，只判断数值关系。','premises':['分数为71。','姓名为甲。'],
  'body':'合成资料：本表比较基准为64分。','answer':'题设分数71大于正文基准64。',
  'components':[('题设分数71大于正文基准64。','numeric_comparison','supported',[0])],
  'comparison':{'left':{'value':'71','quote':'71'},'right':{'value':'64','quote':'64'},'operator':'>'}},
 {'id':'F05','topic':'archive','question':'只复述档案规则。','premises':['本次记录有3页。'],
  'body':'合成档案规则：记录至少2页时可以编号。','answer':'规则允许至少2页的记录编号。',
  'components':[('规则允许至少2页的记录编号。','literature_rule','supported',[])],
  'injected_category':'input_evidence_coverage','diagnostic':'预置提取分类故障，单列诊断，不是自然分类正确率'},
 {'id':'F06','topic':'device','question':'判断设备额定承载能力。','premises':['标签颜色为白色。'],
  'body':'合成设备说明：本段只介绍外壳颜色，没有额定承载数据。','answer':'设备额定承载能力为900千克。',
  'components':[('设备额定承载能力为900千克。','external_fact','insufficient_evidence',[])]},
 {'id':'F07','topic':'reporting','question':'复述题设记录。','premises':['记录数量为12。'],
  'body':'合成背景：记录按日归档。','answer':'题设记录数量为12。题设记录数量为21。',
  'components':[('题设记录数量为12。','premise_restatement','supported',[0]),('题设记录数量为21。','premise_restatement','contradicted',[0])]},
 {'id':'F08','topic':'engineering','question':'给定电流能否算出设备寿命？','premises':['电流为5安。'],
  'body':'合成设备资料：未给出寿命模型、温度或试验数据。','answer':'电流为5安，因此设备寿命为50年。',
  'components':[('电流为5安，因此设备寿命为50年。','engineering_relation','insufficient_evidence',[])]},
]

def fixed_input(case):
    answer=AnswerDraft('fixed-'+case['id'],1,case['answer'])
    evidence=Evidence('body-'+case['id'],'synthetic-'+case['topic'],'v1','whole synthetic paragraph',case['body'],'synthetic_fixture')
    request=PremiseTaskRequest('task-'+case['id'],TaskMode.ASSESS_EXISTING,'conceptual',case['question'],
        user_context='\n'.join(case['premises']),existing_answer=answer,provided_evidence=(evidence,),
        premise_declarations=tuple(PremiseDeclaration('user_context',p) for p in case['premises']))
    category=case.get('injected_category','input_evidence_coverage' if all(c[1]=='premise_restatement' for c in case['components']) else 'technical_fact')
    components=[{'category':category,'proposition':c[0],
        'basis_target':'input_snapshot' if category=='input_evidence_coverage' else 'technical_content',
        'verification_obligation':'input_provided' if category=='input_evidence_coverage' else 'technical_truth'} for c in case['components']]
    claims=parse({'claims':[{'anchor_id':anchors(answer)[0]['anchor_id'],'proposition':case['answer'],
        'claim_type':category,'components':components,'assertion_role':'asserted','semantic_qualifiers':[]}],'non_claims':[]},answer).claims
    return ReliabilityVerificationInput(request,answer,claims,(evidence,))

if __name__=='__main__':
    Path('docs/evaluation/fact-internal-flow-v1/inputs-and-reference-v1.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

async def prepare_messages():
    """Capture the actual first adapter request, abort before any network call."""
    import hashlib
    from dataclasses import asdict
    from agents.evidence_verification import ModelEvidenceVerificationAgent
    from agents.fact_flow_v1 import FactFlowAgent
    from model_adapter.contracts import ModelSettings
    from model_adapter.runtime import ModelBudget,model_scope
    class Captured(BaseException):pass
    root=Path('data/evaluation_local/fact-internal-flow-v1/preparation-v1');root.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case in CASES:
        inp=fixed_input(case)
        for variant in ('original','candidate') if int(case['id'][1:])%2 else ('candidate','original'):
            seen=[]
            class Adapter:
                async def complete(self,request):
                    seen.append(request)
                    raise Captured()
            settings=ModelSettings('deepseek-flash',90,8000,96000,'https://api.deepseek.com','DEEPSEEK_API_KEY')
            agent=(FactFlowAgent(Adapter(),settings) if variant=='candidate' else
                   ModelEvidenceVerificationAgent(Adapter(),settings,schema_version=13,support_relation_checks=True,support_relation_version=6,review_message_profile='lossless_v1'))
            try:
                with model_scope(ModelBudget(40)):await agent.run(inp)
            except Captured:pass
            if not seen and all(c.category=='input_evidence_coverage' for claim in inp.claims for c in claim.components) and variant=='original':
                rows.append({'case':case['id'],'variant':variant,'status':'PROGRAM_PRECONDITION_NO_INPUT_SNAPSHOT','initial_calls':0,'maximum_corrections':0,'not_a_success':True})
                continue
            if len(seen)!=1:raise AssertionError('Exactly one captured initial request required: '+case['id']+' '+variant)
            messages=[asdict(m) for m in seen[0].messages]
            payload=json.dumps(messages,ensure_ascii=False,sort_keys=True).encode('utf-8')
            (root/(case['id']+'-'+variant+'.json')).write_bytes(payload)
            rows.append({'case':case['id'],'variant':variant,'prompt_version':seen[0].prompt_version,
                'message_sha256':hashlib.sha256(payload).hexdigest(),'message_chars':len(payload.decode('utf-8')),
                'status':'PREPARATION_ONLY_NOT_SENT','initial_calls':1,'maximum_corrections':1})
    manifest={'version':'fact-internal-flow-comparison-preparation-v1','paid_execution_authorized':False,
        'synthetic_development_material':True,'tool_inputs':[],'retrieval':'fixed delivered evidence; no new retrieval',
        'model':'deepseek-flash','timeout_seconds':90,'max_output_tokens':8000,'max_response_chars':96000,
        'per_branch_existing_budget':40,'planned_initial_calls':sum(r['initial_calls'] for r in rows),'conditional_corrections_max':sum(r['maximum_corrections'] for r in rows),
        'planned_call_upper_bound':sum(r['initial_calls']+r['maximum_corrections'] for r in rows),'order':rows,
        'input_sha256':hashlib.sha256(json.dumps(CASES,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest(),
        'reference_sent_to_model':False}
    Path('docs/evaluation/fact-internal-flow-v1/preparation-v1.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return manifest
