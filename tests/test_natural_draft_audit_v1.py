from tests.temp_paths import ignored_temporary_directory
import asyncio,os,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from evaluation import natural_draft_audit_v1 as t
from backend.config import ServiceConfig
from model_adapter.contracts import ModelConnectionError
from tests.test_literal_review_v1 import Provider


@unittest.skipUnless((t.OLD/'batch/summary.json').exists(),'Private archive absent')
class NaturalAuditTests(unittest.TestCase):
    def exercise(self,network=False,tamper=False):
        generated,origins=t.recover();m=t.load(t.LOCAL/'materials.json');m['origins']=origins
        if tamper:m['origins'][0]=dict(origins[0],snapshot_sha256='wrong')
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve()
            class Fake(Provider):
                async def complete(self,r):
                    if network:self.requests.append(r);raise ModelConnectionError()
                    return await super().complete(r)
            fake=Fake();c=ServiceConfig(index_db=root/'MUST-NOT-OPEN.sqlite3',knowledge_version=origins[0]['knowledge_version'],execution_path='langgraph_v1',fact_review_contract='literal_v1',local_revision_interface='source_actions_v2')
            c=replace(c,budget=replace(c.budget,max_revision_rounds=1,max_model_calls=24,max_duration_seconds=800,max_transient_retries=0))
            with (patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('rag.storage.KnowledgeStore',side_effect=AssertionError('No index')),
                patch('rag.corpus_index.seal',side_effect=AssertionError('No seal')),patch('harness.deepseek_trial.load_project_env',side_effect=AssertionError('No offline env'))):
                s=asyncio.run(t.batch(c,m,generated,root/'batch',lambda *a,**kw:fake))
            if network or tamper:
                self.assertEqual(len(s['control']),1);self.assertTrue(s['control'][0]['stop'])
                self.assertEqual(len(fake.requests),1 if network else 0)
            else:
                self.assertEqual(len(s['control']),8);self.assertFalse(s['unexecuted'])
                self.assertFalse(any(row['stop'] for row in s['control']))
                for ctrl in s['control']:
                    i=ctrl['accepted']['spec']['case'];r=s['outputs'][ctrl['accepted']['run_id']]
                    self.assertEqual(r['answer'],t.wire(generated[i].answer));self.assertEqual(r['evidence'],t.wire(generated[i].evidence))
                    self.assertFalse(r['retrieval_records']);self.assertIsNone(r['generation_output'])
                    self.assertEqual({x['component'] for x in r['model_records']},{'claim_extraction','evidence_verification','power_domain_review'})
                    self.assertEqual(len(r['model_records']),3);self.assertEqual(len(r['review_rounds']),1)
                    inp=t.load(root/'batch'/r['run_id']/'input.json');self.assertEqual(t.sha(inp['generation_snapshot']),origins[i]['snapshot_sha256'])
                    self.assertEqual(t.shared.saved_result(root/'batch/runs.sqlite3',r['run_id']),r)
                    self.assertTrue(all(b['origin']=='user_reference' for b in r['evidence_bindings']))
                    self.assertEqual(inp['generation_snapshot']['evidence_bindings'],t.wire(generated[i].generation_output.evidence_snapshot.evidence_bindings))
            self.assertFalse(c.index_db.exists())
    def test_all_eight_inputs_fresh_initial_audits_no_history_charges(self):self.exercise()
    def test_shared_network_stops_first_chain(self):self.exercise(network=True)
    def test_snapshot_identity_stops_before_send(self):self.exercise(tamper=True)


if __name__=='__main__':unittest.main()
