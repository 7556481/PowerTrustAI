import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import retrieval_evidence_answer_check_v1 as t
from backend.config import ServiceConfig
from model_adapter.contracts import ModelResponse, ModelConnectionError, ModelMessage, ModelRequest
from core.validation import ContractError
from tests.test_schema14_factory_flow import SyntheticProvider


@unittest.skipUnless((t.OLD/'batch/retrieval.sqlite3').exists(),'Archived private input unavailable')
class ArchivedAnswerTests(unittest.TestCase):
    def exercise(self,mode='ok'):
        recovered,origins=t.recover();m=dict(N=t.old.N)
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve();p=SyntheticProvider();requests=[]
            class Provider:
                def close(self):pass
                async def complete(self,r):
                    requests.append(r)
                    if mode=='network':raise ModelConnectionError()
                    if mode=='first_slot_invalid' and len(requests)<=2:return ModelResponse('{}',r.model_id,finish_reason='stop')
                    return await p.complete(r)
            c=ServiceConfig(index_db=root/'MUST-NOT-OPEN.sqlite3',knowledge_version=origins[0]['knowledge_version'],execution_path='langgraph_v1')
            if mode=='tamper':origins[0]=dict(origins[0],delivery_sha256='wrong')
            with (patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('rag.storage.KnowledgeStore',side_effect=AssertionError('No index access')),
                patch('rag.corpus_index.seal',side_effect=AssertionError('No seal')),patch('services.generation_query.GenerationQueryConverter.run',side_effect=AssertionError('No conversion')),
                patch('harness.deepseek_trial.load_project_env',side_effect=AssertionError('No offline env load'))):
                summary=asyncio.run(t.batch(c,m,recovered,origins,root/'batch',lambda *a,**k:Provider()))
            if mode in ('network','tamper'):
                self.assertEqual(len(summary['control']),1);self.assertTrue(summary['control'][0]['stop'])
                self.assertEqual(len(requests),1 if mode=='network' else 0)
            else:
                self.assertEqual(len(summary['control']),16);self.assertFalse(summary['unexecuted'])
                self.assertFalse(any(row['stop'] for row in summary['control']))
                self.assertEqual(len(requests),17 if mode=='first_slot_invalid' else 16)
            for control in summary['control']:
                rid=control.get('accepted',{}).get('run_id');raw=summary['outputs'].get(rid)
                if raw is None:continue
                spec=control['accepted']['spec'];d=recovered[(spec['case'],spec['variant'])]
                self.assertEqual(raw['evidence'],t.wire(d.evidence));self.assertEqual(raw['evidence_bindings'],t.wire(d.bindings))
                self.assertEqual(raw['retrieval_records'][0]['query_method'],'archived_retrieval')
                self.assertEqual(raw['retrieval_records'][0]['calls_used'],0)
                self.assertIsNone(raw['extraction_output']);self.assertIsNone(raw['verification_output']);self.assertIsNone(raw['domain_output'])
                if raw['generation_output']:
                    snap=raw['generation_output']['evidence_snapshot']
                    self.assertEqual(snap['knowledge_version'],d.record.knowledge_version)
                    self.assertEqual(snap['evidence_bindings'],t.wire(d.bindings))
                    self.assertEqual(snap['question'],m['N'][spec['case']]['question'])
                self.assertEqual(t.shared.saved_result(root/'batch/runs.sqlite3',rid),raw)
            bad_query=t.load(t.OLD/'batch/retrieval/N6-C.json')['plan']['english_query']
            self.assertTrue(all(bad_query not in msg.content for req in requests for msg in req.messages))
            self.assertFalse(c.index_db.exists())
            return summary

    def test_exact_16_archived_deliveries_normal_generation_and_store(self):self.exercise()
    def test_invalid_first_branch_retained_and_independent_partner_continues(self):self.exercise('first_slot_invalid')
    def test_network_failure_stops_after_first_send(self):self.exercise('network')
    def test_input_identity_failure_stops_before_send(self):self.exercise('tamper')

    def test_messages_are_equal_except_evidence_and_actual_origins(self):
        recovered,_=t.recover();m=dict(N=t.old.N)
        for i in range(8):
            messages=[t.messages_for(t.GenerationInput(t.request(m,i),recovered[(i,v)].evidence,recovered[(i,v)].bindings,recovered[(i,v)].record.knowledge_version),3,product_guidance=True) for v in ('A','C')]
            self.assertEqual(messages[0][:2],messages[1][:2]);self.assertEqual(len(messages[0]),3)
            for v,wire in zip(('A','C'),messages):
                d=json.loads(wire[-1].content)
                self.assertEqual(set(d),{'section','evidence','origins'})
                self.assertEqual(d['evidence'],t.wire(recovered[(i,v)].evidence))
                self.assertEqual(d['origins'],t.wire(recovered[(i,v)].bindings))

    def test_send_limit_is_global_and_per_branch(self):
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:
            limit=t.SendLimit(Path(tmp));r=ModelRequest('deepseek-flash',(ModelMessage('user','{}'),),8000,'evidence-bound-generation-fixture')
            spec=dict(case=0,variant='A');limit(spec,r,1);limit(spec,replace(r,correction=True),2)
            with self.assertRaises(ContractError):limit(spec,r,3)
            limit(dict(case=0,variant='C'),r,3);self.assertEqual(limit.used,3)
            limit.used=32
            with self.assertRaises(ContractError):limit(dict(case=1,variant='C'),r,33)

    def test_session_refuses_changed_original_question(self):
        recovered,_=t.recover();d=recovered[(0,'A')]
        req=replace(t.request(dict(N=t.old.N),0),question='Changed question')
        session=t.ArchivedSession(d,req.question)
        with self.assertRaises(ContractError):asyncio.run(session.retrieve(t.RetrievalPurpose.GENERATION,req,None,()))


if __name__=='__main__':unittest.main()
