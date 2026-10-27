from tests.temp_paths import ignored_temporary_directory
import asyncio,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from evaluation import review_delivery_unblock_v1 as t
from evaluation import answer_review_net_benefit_v1 as shared
from tests.test_schema14_factory_flow import SyntheticProvider,GOOD
from tests.test_review_simple_v1 import response
from model_adapter.contracts import ModelResponse,ModelConnectionError
from model_adapter.strict_review_tool import map_null,VERSION,NAME
from backend.config import ServiceConfig
from rag.storage import KnowledgeStore,SourceMetadata


class DeliveryTests(unittest.TestCase):
    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/production-review-net-benefit-v2/materials.json').is_file(), 'Private historical archive unavailable')
    def test_guard_protected_semantic_error_stops_dependent_delivery(self):
        g=t.Gate(t.materials());issue=g(dict(line='A',case=2,variant='bound'),dict(execution_issues=[],verification_output=dict(findings=[dict(status='supported'),dict(status='supported')],citation_reviews=[])))
        self.assertEqual(issue['protected']['unit'],1)
        self.assertEqual(len(t.order()),17);self.assertEqual(sum(x['input']['line']=='G' for x in t.order()),3)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/production-review-net-benefit-v2/materials.json').is_file(), 'Private historical archive unavailable')
    def test_full_rehearsal_factory_same_draft_budget_and_response_storage_stop(self):
        for failure in (None,'shared','response_storage'):
            with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
                root=Path(tmp).resolve();p=root/'fixture.md';p.write_text(GOOD,encoding='utf-8')
                with KnowledgeStore(root/'knowledge.sqlite3') as k:version=k.ingest(p,'synthetic-fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
                c=ServiceConfig(index_db=root/'knowledge.sqlite3',knowledge_version=version,execution_path='langgraph_v1');m=t.materials();refs={text:ref for a in m['A'] for (_,text),ref in zip(a['units'],a['reference'])}
                original=SyntheticProvider.complete
                async def complete(provider,r):
                    if failure=='shared':raise ModelConnectionError()
                    if r.result_tool is None:return await original(provider,r)
                    d=json.loads(r.messages[1].content);v=response(d)
                    for row,target in zip(v['judgments'],d['targets']):
                        row['status']=refs.get(target['proposition'],'supported')
                        if 'answer_ids' not in r.result_tool['function']['parameters']['properties']['judgments']['items']['properties']['conditions']['properties']:row['conditions'].pop('answer_ids')
                    args=json.dumps(map_null(v,encode=True));return ModelResponse(args,r.model_id,finish_reason='tool_calls',result_transport=dict(version=VERSION,content='',tool_calls=[dict(id='fixture',type='function',function=dict(name=NAME,arguments=args))]))
                write=shared.write
                def storage(path,value):
                    if failure=='response_storage' and path.parent.name=='responses':raise OSError('offline fixture storage fault')
                    return write(path,value)
                with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'synthetic-fixture','DEEPSEEK_API_KEY':'fixture'}),patch('backend.assembly.ROOT',root),patch.object(SyntheticProvider,'complete',complete),patch.object(shared,'write',storage):
                    s=asyncio.run(shared.batch(c,m,root/'batch',lambda settings,**kw:SyntheticProvider(),rows=t.order(),request_builder=t.base.request,variant_config=t.variants,task_runner=t.base.task_runner,result_guard=t.Gate(m),fixed_audit_delivery=False))
                if failure:self.assertEqual(len(s['control']),1)
                else:
                    self.assertEqual(len(s['control']),17);self.assertFalse(s['unexecuted'])
                    for i in range(3):
                        controls=[x for x in s['control'] if x['case_id'].startswith(f'B{i+1}-')];values=[s['outputs'][x['accepted']['run_id']] for x in controls]
                        self.assertEqual(values[0]['review_rounds'][0]['answer'],values[1]['review_rounds'][0]['answer'])
                        frozen=[json.loads((root/'batch'/x['accepted']['run_id']/'input.json').read_text(encoding='utf-8')) for x in controls]
                        self.assertEqual(frozen[0]['generation_snapshot'],frozen[1]['generation_snapshot']);self.assertEqual(frozen[0]['budget'],frozen[1]['budget'])
                        generation=next(s['outputs'][x['accepted']['run_id']] for x in s['control'] if x['case_id']==f'G{i+1}')
                        charged=generation['retrieval_records'][-1] if generation['retrieval_records'] else {}
                        self.assertEqual(frozen[0]['budget']['max_retrieval_calls'],c.budget.max_retrieval_calls-charged.get('calls_used',0))
                        self.assertEqual(frozen[0]['budget']['max_retrieval_chars_total'],c.budget.max_retrieval_chars_total-charged.get('cumulative_chars',0))
                (root/'batch/runs.sqlite3').rename(root/'closed.sqlite3')


if __name__=='__main__':unittest.main()
