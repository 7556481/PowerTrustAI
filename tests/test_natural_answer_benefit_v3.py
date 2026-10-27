from tests.temp_paths import ignored_temporary_directory
"""20-slot offline substitute: workflow evidence, no semantic model score."""
import asyncio,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from contextlib import closing
from types import SimpleNamespace
from evaluation import natural_answer_benefit_v3 as t
from backend.config import ServiceConfig
from rag.storage import KnowledgeStore,SourceMetadata
from tests.test_literal_review_v1 import Provider
from tests.test_schema14_factory_flow import GOOD,BAD
from tests.test_local_revision_v2_flash_check_v1 import Substitute
from model_adapter.contracts import ModelResponse,ModelConnectionError
from core.validation import ContractError

class FixtureProvider(Substitute):
    async def complete(self,r):
        if self.mode=='service':self.requests.append(r);raise ModelConnectionError()
        if r.prompt_version.startswith('evidence-bound-generation'):
            if self.mode=='generation_fail':
                self.requests.append(r);return ModelResponse('{}',r.model_id,finish_reason='stop')
            out=await super().complete(r);v=json.loads(out.text);v['answer_units'][0]['text']=BAD
            return replace(out,text=json.dumps(v))
        if r.prompt_version=='local-revision-source-actions-v2':
            out=await super().complete(r);v=json.loads(out.text)
            for e in v['edits']:e['text']=e['text'].replace(BAD,GOOD)
            return replace(out,text=json.dumps(v))
        return await super().complete(r)

@unittest.skipUnless((t.OLD/'batch/summary.json').exists(),'Private historical archive unavailable')
class NaturalBenefitTests(unittest.TestCase):
    def exercise(self,mode='edit',*,cap=304,quota=24,full_entry=False):
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve();doc=root/'fixture.md'
            doc.write_text(GOOD+'\n'+'\n'.join(q['question'] for q in t.N),encoding='utf-8')
            with KnowledgeStore(root/'index.sqlite3') as store:k=store.ingest(doc,'synthetic',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
            c=ServiceConfig(index_db=root/'index.sqlite3',knowledge_version=k,execution_path='langgraph_v1',run_db=root/'private/batch/runs.sqlite3')
            c=replace(c,budget=replace(c.budget,max_model_calls=quota,max_duration_seconds=800,max_revision_rounds=1,max_transient_retries=0))
            m=t.materials();p=FixtureProvider(mode);limit=t.SendLimit(root/'private/batch',cap=cap)
            with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('backend.assembly.ROOT',root),patch.object(t,'LOCAL',root/'private'),patch.object(t,'PUBLIC',root/'public'),patch('model_adapter.deepseek.create_adapter',return_value=p),patch('harness.deepseek_trial.load_project_env',side_effect=AssertionError('Offline env load')):
                if full_entry:
                    t.save(t.PUBLIC/'materials-reference.json',t.public_materials(m))
                    with patch.object(t,'require_sources'),patch.object(ServiceConfig,'from_environment',return_value=c):s=asyncio.run(t.run())
                    self.assertTrue((root/'private/attempt.json').exists())
                    self.assertEqual(t.load(root/'private/freeze.json'),t.load(root/'public/freeze.json'))
                    with self.assertRaisesRegex(ContractError,'Unique'):asyncio.run(t.run())
                else:s=asyncio.run(t.batch(c,m,root/'private/batch',lambda *a,**kw:p,limit=limit))
            self.assertEqual([r['sequence'] for r in s['send_log']],list(range(1,len(s['send_log'])+1)))
            for control in s['control']:
                rid=control.get('accepted',{}).get('run_id');r=s['outputs'].get(rid)
                if r is None:continue
                self.assertEqual(t.shared.saved_result(root/'private/batch/runs.sqlite3',rid),r)
                if r['state']=='unexecuted':continue
                spec=control['accepted']['spec'];inp=t.load(root/'private/batch'/rid/'input.json')
                if spec['line']=='B':
                    self.assertEqual(inp['budget']['max_model_calls'],24 if full_entry else quota)
                    self.assertEqual(inp['budget']['max_duration_seconds'],800)
                    if r['review_rounds']:self.assertEqual(r['review_rounds'][0]['answer'],inp['request']['existing_answer'])
                    self.assertEqual(r['evidence'][:len(inp['request']['provided_evidence'])],inp['request']['provided_evidence'])
                    self.assertFalse(r['retrieval_records']);self.assertIsNone(r['generation_output'])
                    self.assertTrue(all(x['component'] in ('revision','claim_extraction','evidence_verification','power_domain_review') for x in r['model_records']))
                    self.assertTrue((root/'private/batch'/rid/'audit-origin.json').exists())
                    if spec['group']=='H':self.assertEqual(inp['generation_snapshot'],t.wire(t.history()[0][spec['case']].generation_output.evidence_snapshot))
            for message in (root/'private/batch/messages').glob('*.json'):
                msg=t.load(message)
                for q in m['N']:
                    for rule in q['critical']:self.assertNotIn(rule,json.dumps(msg['messages'],ensure_ascii=False))
            (root/'private/batch/runs.sqlite3').rename(root/'private/batch/released.sqlite3')
            return s,p

    def test_exact_20_slots_normal_rag_fresh_initial_and_modified_full_reaudit(self):
        s,p=self.exercise(full_entry=True);self.assertEqual(len(s['control']),20);self.assertFalse(s['unexecuted'])
        self.assertFalse(any(x['stop'] for x in s['control']))
        audits=[r for r in s['outputs'].values() if r.get('review_rounds')]
        self.assertEqual(len(audits),12)
        for r in audits:self.assertTrue({'claim_extraction','evidence_verification','power_domain_review'}<={x['component'] for x in r['model_records'] if x['answer_version']==1})
        self.assertEqual(sum(len(r['review_rounds'])==2 for r in audits),8)
        for r in audits:
            if len(r['review_rounds'])==2:self.assertTrue({'claim_extraction','evidence_verification','power_domain_review'}<={x['component'] for x in r['model_records'] if x['answer_version']==2})

    def test_no_change_and_final_illegal_are_local(self):
        for mode in ('retain','invalid'):
            s,p=self.exercise(mode);self.assertEqual(len(s['control']),20)
            audits=[r for r in s['outputs'].values() if r.get('review_rounds')]
            self.assertEqual(len(audits),12);self.assertTrue(all(len(r['review_rounds'])==1 for r in audits))
            if mode=='invalid':self.assertEqual(sum(x.prompt_version=='local-revision-source-actions-v2' for x in p.requests),16)

    def test_generation_failure_skips_audit_still_retains_8_denominator(self):
        s,p=self.exercise('generation_fail');self.assertEqual(len(s['control']),20)
        self.assertEqual(sum(r['state']=='unexecuted' for r in s['outputs'].values()),8)
        self.assertEqual(sum(x.prompt_version=='literal-review-v1' for x in p.requests),4)

    def test_shared_failure_and_global_cap_stop(self):
        s,p=self.exercise('service');self.assertEqual(len(p.requests),1);self.assertEqual(len(s['control']),1);self.assertTrue(s['control'][0]['stop'])
        s,p=self.exercise(cap=1);self.assertEqual(len(p.requests),1);self.assertTrue(s['control'][-1]['stop']);self.assertEqual(len(s['unexecuted']),18)

    def test_clear_local_quota_continues_independent_slots(self):
        s,p=self.exercise(quota=3);self.assertEqual(len(s['control']),20);self.assertFalse(s['unexecuted'])

    def test_global_deadline_and_chain_counters_do_not_reset(self):
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            now=[0];g=t.SendLimit(Path(tmp),clock=lambda:now[0],seconds=1);r=SimpleNamespace(model_id='deepseek-flash',max_output_tokens=8000)
            g(dict(id='N1',line='G'),r,1);g(dict(id='N1',line='B'),r,2);self.assertEqual(g.used,2)
            now[0]=1
            with self.assertRaises(RuntimeError):g(dict(id='N2',line='G'),r,3)
            self.assertEqual(g.used,2)

if __name__=='__main__':unittest.main()
