import json,sqlite3,unittest
from contextlib import closing
from services.review_transport import pack,expand
from services.json_nesting import diagnostic
from services.structured_model import strict_json
from rag.topic_lanes import plan as baseline
from rag.topic_scoring import plan

class TransportTests(unittest.TestCase):
    def test_manifest_does_not_claim_inactive_schema_transport(self):
        from backend.config import ServiceConfig
        from backend.assembly import ComponentFactory
        compact=ComponentFactory(ServiceConfig(profile='synthetic_fixture',verification_schema=13,review_message_profile='lossless_v1',fact_strategy='per_claim_v1')).manifest(None)
        other=ComponentFactory(ServiceConfig(profile='synthetic_fixture',verification_schema=14,review_message_profile='lossless_v1')).manifest(None)
        self.assertIn('v9.20',compact['prompts']['verification'])
        self.assertTrue(compact['prompts']['verification'].endswith('-fact-delivery-v1'))
        self.assertEqual(other['review_message_profile'],'baseline_v1')
        self.assertNotIn('review_transport',other)

    def test_lossless_full_bodies_and_scope_binding(self):
        body='温度范围、频率条件和限定原文。'*50
        metadata={'source_version':'frozen','provenance':{'knowledge_version':'frozen-k','source_uri':'unverified','warnings':['unknown origin']*20}}
        payload={'QUOTE_CANDIDATES':[{'quote_id':'scope-a-0','evidence_id':'e1','text':body,'metadata':metadata}],
                 'GENERATION_INPUT_SNAPSHOT':{'evidence':[{'evidence_id':'e1','text':body,'metadata':metadata}]},
                 'SOURCE_CONDITION_CANDIDATES':[{'condition_id':'condition-a','quote_id':'scope-a-0'}],
                 'ORIGINAL_CITATION_SCOPES':[{'scope_id':'scope-b','QUOTE_CANDIDATES':[{'quote_id':'scope-b-0','evidence_id':'e1','text':body,'metadata':metadata}]}]}
        packed=pack(payload)
        self.assertEqual(expand(packed),payload)
        self.assertLess(len(json.dumps(packed)),len(json.dumps(payload)))
        self.assertEqual(packed['SOURCE_CONDITION_CANDIDATES'],payload['SOURCE_CONDITION_CANDIDATES'])
        self.assertEqual(packed['ORIGINAL_CITATION_SCOPES'][0]['scope_id'],'scope-b')

    def test_actual_failure_nesting_strictly_rejected_without_repair(self):
        text='{"findings":[{"component_reviews":[{"support_relation":{"repair":null}]}]}'
        self.assertEqual(diagnostic(text)['expected_closer'],'}')
        with self.assertRaises(json.JSONDecodeError):strict_json(text)
        valid='{"findings":[{"component_reviews":[{"support_relation":{"repair":null}}]}]}'
        # Validly nested form closes relation AND component before the array.
        self.assertEqual(strict_json(valid)['findings'][0]['component_reviews'][0]['support_relation'],{'repair':None})
        self.assertEqual(diagnostic('{"x":"braces } ] and escaped \\" quote"}').get('unclosed_containers'),0)

class QueryTests(unittest.TestCase):
    def test_units_negation_direction_and_load_qualifiers_retained(self):
        q='电动机轻载与满载时，频率降低，电压为220V，非正弦情况下不能作全范围保证。'
        expression=plan(q)[0][1]
        for term in ('轻载','满载','频率','降低','220v','正弦'):
            self.assertIn('"'+term+'"',expression)
        self.assertNotIn('"时"',expression)

    def test_subject_membership_and_tie_order_on_synthetic_corpus(self):
        with closing(sqlite3.connect(':memory:')) as c:
            c.execute('create virtual table corpus_fts using fts5(terms)')
            c.executemany('insert into corpus_fts(terms) values (?)',[(s,) for s in ('变压器 频率 会 时 降低 正弦 稳态','变压器 频率 正弦 稳态','电机 时 会 提高','频率 电池')])
            for q in ('变压器频率降低时会如何变化？','电池温度和效率之间的关系。','220V'):
                a=baseline(q)[0][1];b=plan(q)[0][1]
                self.assertEqual(c.execute('select rowid from corpus_fts where corpus_fts match ? order by rowid',(a,)).fetchall(),c.execute('select rowid from corpus_fts where corpus_fts match ? order by rowid',(b,)).fetchall())

    def test_packed_real_contract_path_keeps_strict_scope(self):
        import asyncio
        from tests import test_fact_rereview_v3 as fixture
        from tests.test_audit_interface_v2 import warrant
        from agents.evidence_verification import ModelEvidenceVerificationAgent
        from model_adapter.contracts import ModelSettings,ModelResponse
        from model_adapter.runtime import ModelBudget,model_scope
        from services.request_metrics import measure
        inp=fixture.inputs(False,two=True);seen=[]
        class Adapter:
            async def complete(self,req):
                sent=json.loads(req.messages[1].content)
                d=expand(sent) if 'TRANSPORT_VERSION' in sent else sent
                seen.append(d);v=fixture.response(d)
                for f in v['findings']:
                    for row in f['component_reviews']:
                        ids=[f['bases'][i]['quote_id'] for i in row['basis_indexes']]
                        row['support_relation']=warrant(d,ids)
                metrics=measure(req.messages)
                self_metrics.append(metrics)
                return ModelResponse(json.dumps(v),req.model_id,finish_reason='stop')
        self_metrics=[]
        async def run():
            with model_scope(ModelBudget(2)):
                return await ModelEvidenceVerificationAgent(Adapter(),ModelSettings('synthetic_fixture'),schema_version=13,support_relation_checks=True,support_relation_version=6,review_message_profile='lossless_v1').run(inp)
        result=asyncio.run(run())
        self.assertFalse(result.execution_issues)
        self.assertIn('v9.20',result.prompt_version)
        self.assertTrue(all(m['evidence_chars_unique']>0 for m in self_metrics))

if __name__=='__main__':unittest.main()
