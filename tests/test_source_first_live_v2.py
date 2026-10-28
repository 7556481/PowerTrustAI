import asyncio,json,os,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from model_adapter.contracts import ModelResponse,ModelUsage,ModelSettings
from model_adapter.runtime import ModelBudget,model_scope
from tests.test_literal_review_v1 import Provider,fixture
from tests.test_source_first_audit_v1 import CandidateProvider
from tests.test_schema14_factory_flow import GOOD
from backend.config import ServiceConfig
from backend.serialization import wire
from services.evidence_scope import make_snapshot
from services.claim_extractor import ModelClaimExtractor
from evaluation.source_first_live_v2 import batch,UsageGate

class Substitute(CandidateProvider):
    async def complete(self,r):
        await asyncio.sleep(.001) # Allow the existing fact/domain pair to overlap.
        from services.local_revision_v2 import VERSION
        if r.prompt_version==VERSION:
            d=json.loads(r.messages[1].content);auth=d['authorizations'][0]
            v=dict(context_id=d['context_id'],edits=[dict(unit_ref=auth['unit_ref'],authorization_refs=[auth['authorization_ref']],text=GOOD,
                support_refs=[auth['source_spans'][0]['source_ref']],dependencies=[])],opinion_actions=[dict(opinion_ref=o['opinion_ref'],action='modified' if o['origin']=='source_bound_fact_defect' else 'retained',edit_indices=[0] if o['origin']=='source_bound_fact_defect' else [],explanation='Synthetic action') for o in d['opinions']])
            out=ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        else:out=await super().complete(r)
        return replace(out,usage=ModelUsage(10,5,15,cache_hit_tokens=0,cache_miss_tokens=10))

class LiveTests(unittest.TestCase):
    def test_same_factory_driver_all_slots_revision_store_and_threshold_stop(self):
        from rag.storage import KnowledgeStore,SourceMetadata
        async def go(root,threshold):
            doc=root/'source.md';doc.write_text(GOOD+' The synthetic setting applies under condition C.',encoding='utf-8')
            with KnowledgeStore(root/'index.sqlite3') as store:
                k=store.ingest(doc,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
                e=store.evidence(store.rows(k)[0]['fragment_id'],k)
            inp=fixture();a=replace(inp.answer,citations=tuple(replace(c,evidence_ids=(e.evidence_id,)) for c in inp.answer.citations))
            req=replace(inp.request,existing_answer=a,provided_evidence=(e,))
            p=Substitute();extractor=ModelClaimExtractor(p,ModelSettings('deepseek-flash',90,8000,96000),typed_components=True,protocol_version=7,daily_guidance=True)
            with model_scope(ModelBudget(2)):extracted=await extractor.extract(a)
            snap=make_snapshot(a,(e,),k)
            m=dict(cases=[dict(request=wire(req),snapshot=wire(snap),extraction=wire(extracted)) for _ in range(4)])
            c=ServiceConfig(index_db=root/'index.sqlite3',knowledge_version=k,run_db=root/'runs.sqlite3')
            gate=UsageGate(root/'batch',threshold=threshold)
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('backend.assembly.ROOT',root):
                s=await batch(c,m,root/'batch',lambda *a,**k:p,gate=gate)
            return s,gate
        for threshold in (1200000,1):
            with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:
                s,g=asyncio.run(go(Path(tmp).resolve(),threshold))
                if threshold==1:
                    self.assertTrue(g.stopped);self.assertLess(len(s['control']),8)
                else:
                    self.assertEqual(len(s['control']),8,{k:v.get('execution_issues') for k,v in s['outputs'].items()});self.assertFalse(s['unexecuted'])
                    candidates=[x for x in s['outputs'].values() if x.get('report',{}).get('literal_protocol')=='source_first_audit_v1']
                    self.assertEqual(len(candidates),4)
                    self.assertTrue(all(x['answer']['version']==2 and len(x['review_rounds'])==2 for x in candidates))
                self.assertLessEqual(g.calls,96);self.assertEqual(g.tokens,15*(g.calls-len(g.pending)))

    def test_missing_usage_stops_and_boundary_caps(self):
        from types import SimpleNamespace as NS
        with tempfile.TemporaryDirectory() as tmp:
            g=UsageGate(Path(tmp));r=NS(model_id='deepseek-flash',max_output_tokens=8000,messages=[])
            g(dict(case=0,variant='baseline'),r,1)
            with self.assertRaises(Exception):g.received(1,ModelResponse('{}','deepseek-flash'))
            self.assertTrue(g.stopped);self.assertEqual(g.pending,{1})
            with self.assertRaises(RuntimeError):g(dict(case=1,variant='baseline'),r,2)

    def test_global_call_cap_and_unknown_send_stop(self):
        from types import SimpleNamespace as NS
        from evaluation.source_first_live_v2 import Accounted
        with tempfile.TemporaryDirectory() as tmp:
            g=UsageGate(Path(tmp),cap=2);r=NS(model_id='deepseek-flash',max_output_tokens=8000,messages=[])
            for i in range(2):g(dict(case=i,variant='baseline'),r,i+1)
            with self.assertRaises(RuntimeError):g(dict(case=3,variant='baseline'),r,3)
            self.assertEqual(g.calls,2)
        async def go(tmp):
            g=UsageGate(Path(tmp));g(dict(case=0,variant='baseline'),r,1)
            class Failed:
                async def complete(self,r):raise TimeoutError()
            with self.assertRaises(TimeoutError):await Accounted(Failed(),g).complete(r)
            self.assertTrue(g.stopped);self.assertEqual(g.pending,{1})
        with tempfile.TemporaryDirectory() as tmp:asyncio.run(go(tmp))
