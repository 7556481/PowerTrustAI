"""Offline substitute rehearsal; synthetic outputs are never semantic evidence."""
import asyncio,json,os,tempfile,unittest,sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend.config import ServiceConfig
from model_adapter.contracts import ModelResponse,ModelConnectionError
from tests.test_literal_review_v1 import Provider
from evaluation import local_revision_v2_flash_check_v1 as t


class Substitute(Provider):
    def __init__(self,mode='edit'):super().__init__();self.mode=mode
    async def complete(self,r):
        if r.prompt_version!='local-revision-source-actions-v2':return await super().complete(r)
        self.requests.append(r);d=json.loads(r.messages[1].content)
        if self.mode=='service':raise ModelConnectionError()
        edits=[];indices={}
        if self.mode=='edit':
            for a in d['authorizations']:
                u=a['unit_ref']
                if u not in indices:
                    indices[u]=len(edits);unit=next(x for x in d['units'] if x['unit_ref']==u)
                    edits.append(dict(unit_ref=u,authorization_refs=[],text=unit['text']+' [Synthetic offline fixture.]',support_refs=[],dependencies=[]))
                e=edits[indices[u]];e['authorization_refs'].append(a['authorization_ref'])
                e['support_refs']=list(dict.fromkeys(e['support_refs']+[x['source_ref'] for x in a['source_spans']]))
        actions=[]
        for o in d['opinions']:
            a=next((x for x in d['authorizations'] if x['authorization_ref']==o.get('authorization_ref')),None)
            ii=[indices[a['unit_ref']]] if a and self.mode=='edit' else []
            actions.append(dict(opinion_ref=o['opinion_ref'],action='modified' if ii else 'retained',edit_indices=ii,explanation='Synthetic wiring fixture; no semantic assessment.'))
        value=dict(context_id=d['context_id'],edits=edits,opinion_actions=actions)
        if self.mode=='invalid':value['illegal_extra']=True
        return ModelResponse(json.dumps(value),r.model_id,finish_reason='stop')


@unittest.skipUnless((t.OLD/'batch/summary.json').exists(),'Private historical inputs unavailable')
class FlashEntryTests(unittest.TestCase):
    def exercise(self,mode='edit',*,cap=48,storage=False,quota=12):
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve();p=Substitute(mode);history=t.recover()
            c=replace(t.config(ServiceConfig(execution_path='langgraph_v1')),index_db=root/'MUST-NOT-OPEN.sqlite3',run_db=root/'runs.sqlite3')
            c=replace(c,budget=replace(c.budget,max_model_calls=quota))
            limit=t.SendLimit(root,max_calls=cap)
            original=t.shared.write
            def write(path,value):
                if storage and path.parent.name=='responses':raise OSError('Synthetic persistence failure')
                return original(path,value)
            with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('rag.storage.KnowledgeStore',side_effect=AssertionError('Index opened')),patch('rag.retriever.AsyncSQLiteBM25Retriever',side_effect=AssertionError('Retriever opened')),patch('backend.assembly.ROOT',root),patch.object(t.shared,'write',side_effect=write):
                t.verify_policy(c,history)
                manifest=t.FixedFactory(c).manifest(None,fixed_evidence_only=True)
                self.assertEqual(manifest['local_revision_interface'],'source_actions_v2')
                result=asyncio.run(t.batch(c,history,root,lambda *a,**k:p,limit=limit))
            self.assertFalse(c.index_db.exists());self.assertEqual(len(result['send_log']),len(list((root/'messages').glob('*.json'))))
            self.assertEqual([x['sequence'] for x in result['send_log']],list(range(1,len(result['send_log'])+1)))
            for rid,raw in result['outputs'].items():
                self.assertEqual(t.shared.saved_result(root/'runs.sqlite3',rid),raw)
                self.assertTrue((root/rid/'historical-replay.json').exists())
                with closing(sqlite3.connect('file:'+(root/'runs.sqlite3').as_posix()+'?mode=ro',uri=True)) as db:
                    request,snapshot=db.execute('SELECT request,snapshot FROM runs WHERE id=?',(rid,)).fetchone()
                    self.assertEqual(json.loads(request)['historical_source']['origin'],'historical_replay')
                    self.assertEqual(json.loads(snapshot)['first_round_provenance']['origin'],'historical_replay')
                    events=db.execute('SELECT payload,stage_output FROM events WHERE run_id=?',(rid,)).fetchall()
                    first=[json.loads(e) for e,o in events if o and json.loads(e)['answer_version']==1]
                    self.assertTrue({'claim_extraction','evidence_verification','power_domain_review'}<={x['component'] for x in first})
                self.assertTrue(all(x['prompt_version']!='literal-review-v1' or x['answer_version']==2 for x in raw['model_records']))
                self.assertFalse(raw['retrieval_records'])
            (root/'runs.sqlite3').rename(root/'released.sqlite3')
            return result,p

    def test_four_slot_edit_reextract_double_review_store_no_history_charge(self):
        s,p=self.exercise()
        self.assertEqual(len(s['control']),4);self.assertFalse(s['unexecuted'])
        for r in s['outputs'].values():
            self.assertFalse(r['execution_issues'],r['execution_issues']);self.assertEqual(r['answer']['version'],2)
            self.assertEqual(len(r['review_rounds']),2);self.assertEqual(len(r['revision_outputs']),1)
            self.assertEqual(len(r['model_records']),4)
            self.assertTrue(all(x['answer_version']==2 or x['component']=='revision' for x in r['model_records']))
        self.assertEqual(len(p.requests),16)
        self.assertEqual(sum(x.prompt_version.startswith('atomic-claims') for x in p.requests),4)
        self.assertEqual(sum(x.prompt_version=='literal-review-v1' for x in p.requests),4)
        self.assertEqual(sum(x.prompt_version.startswith('power-domain') for x in p.requests),4)

    def test_all_retained_consumes_attempt_no_reaudit(self):
        s,p=self.exercise('retain');self.assertEqual(len(p.requests),4)
        self.assertEqual(len(s['control']),4)
        for r in s['outputs'].values():
            self.assertFalse(r['execution_issues']);self.assertEqual(r['answer']['version'],1)
            self.assertEqual(len(r['review_rounds']),1);self.assertEqual(r['report']['decision']['reason_codes'],['LOCAL_REVISION_NO_CHANGE'])

    def test_invalid_final_not_cleaned_one_correction_local_continue(self):
        s,p=self.exercise('invalid');self.assertEqual(len(s['control']),4);self.assertEqual(len(p.requests),8)
        for r in s['outputs'].values():
            self.assertTrue(r['execution_issues']);self.assertFalse(r['revision_outputs']);self.assertEqual(r['answer']['version'],1)
        self.assertEqual(sum(x.correction for x in p.requests),4)

    def test_service_and_response_storage_stop_remaining(self):
        for mode,storage in [('service',False),('retain',True)]:
            s,p=self.exercise(mode,storage=storage)
            self.assertEqual(len(s['control']),1);self.assertTrue(s['control'][0]['stop']);self.assertEqual(s['unexecuted'],['A2','A3','A4'])
            self.assertEqual(len(p.requests),1)

    def test_global_cap_stops_without_resubmit(self):
        s,p=self.exercise('retain',cap=1);self.assertEqual(len(p.requests),1)
        self.assertEqual(s['unexecuted'],['A3','A4']);self.assertTrue(s['control'][-1]['stop'])

    def test_clear_chain_quota_is_local_and_continues(self):
        s,p=self.exercise(quota=1);self.assertEqual(len(p.requests),4)
        self.assertEqual(len(s['control']),4);self.assertFalse(s['unexecuted'])
        self.assertTrue(all(r['execution_issues'] for r in s['outputs'].values()))

    def test_exact_run_entry_freezes_four_inputs_and_one_attempt(self):
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve();p=Substitute('retain');c=ServiceConfig(index_db=root/'MUST-NOT-OPEN.sqlite3',execution_path='langgraph_v1')
            with patch.object(t,'LOCAL',root/'private'),patch.object(t,'PUBLIC',root/'public'),patch.object(t,'require_committed_sources'),patch('harness.deepseek_trial.load_project_env') as env,patch.object(ServiceConfig,'from_environment',return_value=c),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline-fixture','DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('model_adapter.deepseek.create_adapter',return_value=p),patch('rag.storage.KnowledgeStore',side_effect=AssertionError('Index opened')),patch('rag.retriever.AsyncSQLiteBM25Retriever',side_effect=AssertionError('Retriever opened')),patch('backend.assembly.ROOT',root):
                asyncio.run(t.run());env.assert_called_once()
                f=json.loads((root/'public/freeze.json').read_text(encoding='utf-8'))
                self.assertEqual(f['order'],t.order(t.recover()));self.assertEqual(f['budget']['total_new'],48)
                self.assertEqual(json.loads((root/'private/freeze.json').read_text(encoding='utf-8')),f)
                self.assertTrue((root/'private/attempt.json').exists());self.assertEqual(len(p.requests),4)
                with self.assertRaisesRegex(ValueError,'Unique'):asyncio.run(t.run())
            self.assertFalse(c.index_db.exists())

    def test_budget_and_clock_before_send(self):
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:
            now=[0];g=t.SendLimit(Path(tmp),clock=lambda:now[0],max_calls=2,max_seconds=3)
            r=SimpleNamespace(model_id='deepseek-flash',max_output_tokens=8000)
            g({'case':0},r,1);now[0]=3
            with self.assertRaisesRegex(RuntimeError,'global_time_limit'):g({'case':0},r,2)
            self.assertEqual(g.used,1);self.assertEqual(g.remaining_seconds(),.001)
            self.assertEqual(json.loads((Path(tmp)/'global-stop.json').read_text())['reason'],'global_time_limit')

    def test_unique_attempt_refuses_before_environment_loading(self):
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:
            root=Path(tmp);(root/'attempt.json').write_text('{}')
            with patch.object(t,'LOCAL',root),patch('harness.deepseek_trial.load_project_env',side_effect=AssertionError('env loaded')):
                with self.assertRaisesRegex(ValueError,'Unique'):asyncio.run(t.run())


if __name__=='__main__':unittest.main()
