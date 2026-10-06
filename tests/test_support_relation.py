"""Public synthetic source warrant fixtures, not expert semantic benchmarks."""
import asyncio,json,hashlib
from types import SimpleNamespace
import unittest
from core.validation import ContractError
from services.support_relation import normalize
from tests.test_fact_rereview_v3 import inputs,response
from agents.evidence_verification import ModelEvidenceVerificationAgent
from model_adapter.contracts import ModelResponse,ModelSettings
from model_adapter.runtime import ModelBudget,model_scope

def scope(text):return SimpleNamespace(by_wire={'q':SimpleNamespace(text=text)})
def wire(kind='explanatory_body',reason='The source explicitly states the qualified relationship.'):
 return {'citation_reviews':[{'citation_index':0,'status':'supported','rationale':'synthetic_fixture','applicability_conditions':[],
   'bases':[{'type':'text_excerpt','quote_id':'q'}],'support_relation':{'source_kind':kind,'quote_ids':['q'],'explanation':reason}}]}

class WarrantTests(unittest.TestCase):
 def test_exercise_asking_relation_not_supported_even_if_labeled_body(self):
  for kind in ('exercise_question','explanatory_body','mixed'):
   with self.assertRaises(ContractError):normalize(wire(kind),'citation_reviews',[scope('irrelevant'),scope('思考题：无功功率为什么影响电压？')])
 def test_terms_only_do_not_support_mechanism_and_table_data_can_support_values(self):
  with self.assertRaises(ContractError):normalize(wire('term_mention'),'citation_reviews',[scope('irrelevant'),scope('表头：电压 无功功率')])
  v=normalize(wire('data_table','The row reports Q=2 var at U=10 V; it supports only those measured values.'),'citation_reviews',[scope('irrelevant'),scope('U/V | Q/var\n10 | 2')])
  self.assertEqual(v['citation_reviews'][0]['status'],'supported');self.assertIn('source-support-relation-v1',v['citation_reviews'][0]['rationale'])
 def test_explicit_body_statement_survives_but_cross_scope_ids_do_not(self):
  v=wire();normalize(v,'citation_reviews',[scope('irrelevant'),scope('Synthetic: under condition C, Q changes voltage by mechanism M.')])
  v['citation_reviews'][0]['support_relation']['quote_ids']=['other-scope']
  with self.assertRaises(ContractError):normalize(v,'citation_reviews',[scope('irrelevant'),scope('Explicit statement.')])
 def test_empty_explanation_rejected_and_insufficient_remains_legal(self):
  with self.assertRaises(ContractError):normalize(wire(reason=''),'citation_reviews',[scope('irrelevant'),scope('Explicit statement.')])
  v=wire('exercise_question');v['citation_reviews'][0]['status']='insufficient_evidence'
  self.assertEqual(normalize(v,'citation_reviews',[scope('irrelevant'),scope('思考题：为何？')])['citation_reviews'][0]['status'],'insufficient_evidence')
 def test_support_explanation_does_not_fill_missing_original_rationale(self):
  for value in (None,123,''):
   v=wire();v['citation_reviews'][0]['rationale']=value
   with self.assertRaises(ContractError):normalize(v,'citation_reviews',[scope('irrelevant'),scope('Explicit source statement.')])
  v=wire();del v['citation_reviews'][0]['rationale']
  with self.assertRaises(ContractError):normalize(v,'citation_reviews',[scope('irrelevant'),scope('Explicit source statement.')])
 def test_mixed_measurement_table_and_exercise_does_not_invalidate_actual_measurement(self):
  text='U/V | Q/var\n10 | 2\n思考题：为什么电压变化？'
  v=wire('data_table','The measurement row establishes only U=10 V and Q=2 var; the question provides no causal explanation.')
  self.assertEqual(normalize(v,'citation_reviews',[scope('irrelevant'),scope(text)])['citation_reviews'][0]['status'],'supported')
 def test_actual_schema13_profile_retains_atomic_correction_and_records_warrant(self):
  inp=inputs(False);seen=[]
  class Adapter:
   async def complete(self,r):
    seen.append(r);d=json.loads(r.messages[1].content);v=response(d)
    for f in v['findings']:
     for c in f['component_reviews']:
      c['support_relation']={'source_kind':'term_mention' if len(seen)==1 else 'explanatory_body','quote_ids':[f['bases'][k]['quote_id'] for k in c['basis_indexes']],
       'explanation':'Synthetic text explicitly names the three rating categories with their actual conditions.','whole_claim_supported':True,'missing_clauses':[],'conditions_preserved':True,'authority_scope':'explanation','answer_conditions':[],'causal_direction_preserved':True,'repair':None}
    return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
  async def run():
   with model_scope(ModelBudget(2)):
    return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=13,support_relation_checks=True,support_relation_version=3).run(inp)
  out=asyncio.run(run());self.assertFalse(out.execution_issues);self.assertEqual(len(seen),2);self.assertIn('source-support-relation-v3',out.findings[0].component_reviews[0].rationale)
  from backend.assembly import ComponentFactory
  from backend.config import ServiceConfig
  manifest=ComponentFactory(ServiceConfig(profile='synthetic_fixture')).manifest(None)
  self.assertEqual(manifest['template_sha256']['independent'],hashlib.sha256(seen[0].messages[0].content.encode()).hexdigest())

if __name__=='__main__':unittest.main()
