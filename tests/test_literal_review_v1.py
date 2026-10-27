from tests.temp_paths import ignored_temporary_directory
"""Candidate engineering/contract tests; synthetic judgments are not semantic scores."""
import asyncio,json,os,tempfile,unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from agents.contracts import ReliabilityVerificationInput, RevisionInput
from core.models import AnswerDraft,Evidence,CitationBinding,TaskRequest,TaskMode,EngineeringContext
from core.validation import validate_review,validate_revision,ContractError
from services.answer_anchors import anchors
from services.literal_review_v1 import parse,catalog,parse_revision,LiteralReviewAgent,LocalRevisionAgent
from model_adapter.contracts import ModelResponse,ModelSettings,ModelConnectionError
from tests.test_schema14_factory_flow import SyntheticProvider,GOOD,BAD


def fixture():
    text=BAD+'\n\nThe synthetic setting applies under condition C.'
    a=AnswerDraft('literal-fixture',1,text,citations=(CitationBinding(0,len(BAD),('e',)),CitationBinding(len(BAD)+2,len(text),('e',))))
    e=Evidence('e','synthetic','v1','fixture',GOOD+' The synthetic setting applies under condition C.','synthetic_fixture')
    r=TaskRequest('fixture',TaskMode.ASSESS_EXISTING,'concept','Explain voltage and condition.',existing_answer=a,provided_evidence=(e,),engineering_context=EngineeringContext(goal='conceptual'))
    return ReliabilityVerificationInput(r,a,(),(e,),original_evidence=(e,))


def response(d):
    rows=[];defects=[]
    for a in d['units']:
        bad=BAD in a['text'];ids=a.get('allowed_quote_ids',d['INDEPENDENT_QUOTE_IDS'])[:1]
        rows.append(dict(anchor_id=a['anchor_id'],status='contradicted' if bad else 'supported',reason='Synthetic complete original unit meaning.',source_reliability='adequate',quote_ids=ids))
        if bad:defects.append(dict(anchor_id=a['anchor_id'],original_text=BAD,difference='Synthetic source says 3, original says9 under the same condition.',correction_boundary='Correct voltage to3, retain condition and second unit.',quote_ids=ids))
    return dict(units=rows,defects=defects,citations=[dict(citation_index=c['citation_index'],status='supported',reason='Synthetic citation meaning.',quote_ids=c['allowed_quote_ids'][:1]) for c in d['original_citations']])


class Provider(SyntheticProvider):
    def __init__(self,**kw):super().__init__();self.options=kw
    async def complete(self,r):
        if r.prompt_version=='literal-review-v1':
            self.requests.append(r);d=json.loads(r.messages[1].content);self.payloads.append(d);v=response(d)
            if self.options.get('malformed'):v['units']=[]
            return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        if r.prompt_version=='literal-local-revision-v1':
            self.requests.append(r);d=json.loads(r.messages[1].content);self.payloads.append(d)
            no=self.options.get('no_change');defects=d['verification']['literal_defects'];ids={x['finding_id'] for x in defects}
            v=dict(replacements=[] if no else [dict(anchor_id=d['units'][0]['anchor_id'],text=GOOD,evidence_ids=[d['sources'][0]['evidence_id']],finding_ids=list(ids),relation='direct',explanation='Synthetic direct quantity correction.')],
                finding_actions=[dict(finding_id=i,action='modified' if i in ids and not no else 'unresolved' if i in ids else 'retained',explanation='Synthetic bounded action.') for i in d['FINDING_IDS']])
            return ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        return await super().complete(r)


class LiteralTests(unittest.TestCase):
    def test_original_not_distorted_extraction_mixed_and_missing_coverage(self):
        inp=fixture();qs,ind,orig=catalog(inp)
        d=dict(units=anchors(inp.answer),INDEPENDENT_QUOTE_IDS=list(ind),original_citations=[dict(citation_index=i,allowed_quote_ids=list(q)) for i,q in orig.items()])
        raw=response(d);out=parse(raw,inp);validate_review(out,inp.answer,(),inp.seed_evidence,True)
        self.assertFalse(out.findings);self.assertEqual(out.literal_reviews[0].text,BAD)
        self.assertEqual(out.literal_defects[0].original_text,BAD)
        for mutate in (lambda x:x['units'].pop(),lambda x:x['units'].append(x['units'][0]),lambda x:x['defects'][0].update(original_text='not in answer'),lambda x:x['citations'][0].update(quote_ids=['other-source'])):
            x=deepcopy(raw);mutate(x)
            with self.assertRaises(ContractError):parse(x,inp)

    def test_local_assembly_citation_rebind_preservation_conflict_and_no_change(self):
        inp=fixture();_,ind,orig=catalog(inp)
        raw=response(dict(units=anchors(inp.answer),INDEPENDENT_QUOTE_IDS=list(ind),original_citations=[dict(citation_index=i,allowed_quote_ids=list(q)) for i,q in orig.items()]))
        v=parse(raw,inp)
        from agents.contracts import PowerDomainReviewOutput
        domain=PowerDomainReviewOutput(inp.answer.answer_id,1,(),())
        ri=RevisionInput(inp.request,inp.answer,v,domain,inp.seed_evidence,())
        fid=v.literal_defects[0].finding_id
        value=dict(replacements=[dict(anchor_id=anchors(inp.answer)[0]['anchor_id'],text=GOOD,evidence_ids=['e'],finding_ids=[fid],relation='direct',explanation='Synthetic direct source correction.')],finding_actions=[dict(finding_id=fid,action='modified',explanation='Synthetic corrects quantity with condition preserved.')])
        out=parse_revision(value,ri);validate_revision(out,inp.answer,inp.seed_evidence,())
        self.assertEqual(out.answer.text,GOOD+'\n\n'+anchors(inp.answer)[1]['text'])
        self.assertEqual(out.answer.citations[1].start_offset,len(GOOD)+2)
        self.assertTrue(out.preservation)
        value['replacements'].append(value['replacements'][0])
        with self.assertRaises(ContractError):parse_revision(value,ri)
        no=parse_revision(dict(replacements=[],finding_actions=[dict(finding_id=fid,action='retained',explanation='Disputed, do not force edit.')]),ri)
        validate_revision(no,inp.answer,inp.seed_evidence,());self.assertEqual(no.answer,inp.answer)

    def exercise(self,**options):
        from backend.config import ServiceConfig
        from backend.assembly import ComponentFactory
        from backend.store import RunStore
        from backend.serialization import wire
        from rag.storage import KnowledgeStore,SourceMetadata
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve();p=root/'fixture.md';p.write_text(GOOD,encoding='utf-8')
            with KnowledgeStore(root/'knowledge.sqlite3') as k:version=k.ingest(p,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
            c=ServiceConfig(index_db=root/'knowledge.sqlite3',knowledge_version=version,run_db=root/'runs.sqlite3',fact_review_contract='literal_v1',execution_path='langgraph_v1')
            provider=Provider(**options);store=RunStore(c.run_db);inp=fixture();store.create('fixture',inp.request,{})
            async def go():
                factory=ComponentFactory(c);bundle=None
                try:
                    bundle=factory.create('fixture',lambda v:store.checkpoint('fixture',v));bundle.harness.retriever=None
                    return await bundle.harness.run(inp.request,c.budget,run_id='fixture')
                finally:
                    if bundle:await bundle.drain();bundle.close()
                    await factory.close()
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'synthetic-fixture','DEEPSEEK_API_KEY':'fixture'}),patch('model_adapter.deepseek.create_adapter',return_value=provider),patch('backend.assembly.ROOT',root):
                result=asyncio.run(go())
            raw=wire(result);store.mark('fixture','finished',result=raw);self.assertEqual(store.get('fixture')['result'],raw);store.close()
            from evaluation.archive_replay import restore
            from harness.contracts import HarnessResult
            self.assertEqual(wire(restore(raw,HarnessResult)),raw)
            c.run_db.rename(root/'released.sqlite3')
            return result,provider

    def test_factory_graph_store_modified_full_reextract_and_both_reviews(self):
        r,p=self.exercise()
        self.assertFalse(r.execution_issues,r.execution_issues);self.assertEqual(r.answer.version,2)
        self.assertEqual(len(r.review_rounds),2);self.assertEqual(len(r.revision_outputs),1)
        self.assertEqual(sum(x.prompt_version.startswith('atomic-claims') for x in p.requests),2)
        self.assertEqual(sum(x.prompt_version.startswith('power-domain') for x in p.requests),2)
        self.assertEqual(r.answer.text.split('\n\n')[1],fixture().answer.text.split('\n\n')[1])

    def test_factory_graph_no_change_attempt_terminates_original_version(self):
        r,p=self.exercise(no_change=True)
        self.assertFalse(r.execution_issues,r.execution_issues);self.assertEqual(r.answer.version,1)
        self.assertEqual(len(r.revision_outputs),1);self.assertEqual(len(r.review_rounds),1)
        self.assertEqual(r.report.decision.reason_codes,('LOCAL_REVISION_NO_CHANGE',))

    def test_factory_malformed_one_correction_retains_domain_no_revision(self):
        r,p=self.exercise(malformed=True)
        self.assertTrue(r.execution_issues);self.assertIsNotNone(r.domain_output);self.assertFalse(r.revision_outputs)
        self.assertEqual(sum(x.prompt_version=='literal-review-v1' for x in p.requests),2)

    def test_explicit_length_and_dependent_binding_and_crossunit_citation(self):
        inp=fixture();_,ind,orig=catalog(inp)
        raw=response(dict(units=anchors(inp.answer),INDEPENDENT_QUOTE_IDS=list(ind),original_citations=[dict(citation_index=i,allowed_quote_ids=list(q)) for i,q in orig.items()]))
        from agents.contracts import PowerDomainReviewOutput
        ri=RevisionInput(inp.request,inp.answer,parse(raw,inp),PowerDomainReviewOutput(inp.answer.answer_id,1,(),()),inp.seed_evidence,())
        fid=ri.verification.literal_defects[0].finding_id
        v=dict(replacements=[dict(anchor_id=anchors(inp.answer)[0]['anchor_id'],text=GOOD,evidence_ids=['e'],finding_ids=[fid],relation='direct',explanation='Synthetic source correction.')],finding_actions=[dict(finding_id=fid,action='modified',explanation='Synthetic direct correction.')])
        with self.assertRaises(ContractError):parse_revision(v,replace(ri,request=replace(ri.request,question='最多10字')))
        cross=replace(inp.answer,citations=(CitationBinding(0,len(inp.answer.text),('e',)),))
        out=parse_revision(v,replace(ri,answer=cross))
        self.assertEqual(out.answer.text[out.answer.citations[-1].start_offset:out.answer.citations[-1].end_offset].strip(),anchors(inp.answer)[1]['text'])
        bad=deepcopy(v);bad['replacements'][0]['finding_ids']=['unknown']
        with self.assertRaises(ContractError):parse_revision(bad,ri)
        dep=deepcopy(v);dep['replacements'].append(dict(anchor_id=anchors(inp.answer)[1]['anchor_id'],text='Correct dependent explanation under C.',evidence_ids=['e'],finding_ids=[fid],relation='dependent',explanation='Synthetic dependency; model meaning still needs review.'))
        self.assertEqual(len(parse_revision(dep,ri).replacements),2)

    def test_parser_bug_is_not_format_correction(self):
        from services.literal_review_v1 import parser_boundary
        with self.assertRaises(RuntimeError):parser_boundary(lambda v:1+None,{})

    def test_timeout_cancel_and_zero_budget_do_not_become_semantic_judgments(self):
        from model_adapter.runtime import model_scope,ModelBudget
        from model_adapter.contracts import ModelTimeoutError,ModelBudgetError
        class Waiting:
            async def complete(self,r):await asyncio.sleep(1)
        async def go(cancel=False,zero=False):
            agent=LiteralReviewAgent(Waiting(),ModelSettings('synthetic',timeout_seconds=.005))
            with model_scope(ModelBudget(0 if zero else 2)):
                if cancel:
                    task=asyncio.create_task(agent.run(fixture()));await asyncio.sleep(.001);task.cancel();return await task
                return await agent.run(fixture())
        with self.assertRaises(ModelTimeoutError):asyncio.run(go())
        with self.assertRaises(ModelBudgetError):asyncio.run(go(zero=True))
        with self.assertRaises(asyncio.CancelledError):asyncio.run(go(cancel=True))

    @unittest.skipUnless(Path('data/retrieval_local/review-delivery-unblock-v1/batch/summary.json').exists(),'Private historical archive unavailable')
    def test_actual_complex_natural_inputs_retain_original_review_units(self):
        from evaluation.natural_review_seam_v1 import generations
        for g in generations().values():
            inp=fixture()
            r=replace(inp.request,existing_answer=g.answer,provided_evidence=g.evidence)
            vi=replace(inp,request=r,answer=g.answer,seed_evidence=g.evidence,original_evidence=g.evidence)
            provider=Provider()
            out=asyncio.run(LiteralReviewAgent(provider,ModelSettings('synthetic')).run(vi))
            self.assertEqual([x.text for x in out.literal_reviews],[a['text'] for a in anchors(g.answer)])
            self.assertEqual(provider.payloads[0]['answer']['text'],g.answer.text)
            self.assertFalse(out.findings) # Local substitute is engineering evidence only.

    def test_send_limit_global_generation_and_deadline_persist_before_send(self):
        from evaluation.literal_review_stage1_v1 import SendLimit
        from types import SimpleNamespace
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            now=[0];guard=SendLimit(Path(tmp)/'ledger.json',clock=lambda:now[0]);spec=dict(line='G',case=0,variant='production');r=SimpleNamespace(model_id='deepseek-flash',max_output_tokens=8000)
            guard(spec,r,1);guard(spec,r,2)
            with self.assertRaises(RuntimeError):guard(spec,r,3)
            now[0]=21600
            with self.assertRaises(RuntimeError):guard(dict(line='A',case=1,variant='production'),r,3)
            self.assertEqual(guard.remaining_seconds(),.001)
            self.assertEqual(json.loads((Path(tmp)/'ledger/0002.json').read_text(encoding='utf-8'))['used'],2)

    @unittest.skipUnless((Path(__file__).resolve().parents[1]/'data/retrieval_local/deepseek/revision-normal-voltage-v2.json').is_file(), 'Private historical archive unavailable')
    def test_exact_entry_28_slot_offline_rehearsal_freeze_store_and_shared_stop(self):
        from evaluation import literal_review_stage1_v1 as t
        from backend.config import ServiceConfig
        from rag.storage import KnowledgeStore,SourceMetadata
        self.assertEqual(len(t.order()),28)
        for failure in (False,True):
            with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
                root=Path(tmp).resolve();doc=root/'fixture.md';doc.write_text(GOOD,encoding='utf-8')
                with KnowledgeStore(root/'knowledge.sqlite3') as k:version=k.ingest(doc,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
                c=ServiceConfig(index_db=root/'knowledge.sqlite3',knowledge_version=version,execution_path='langgraph_v1')
                class RehearsalProvider(Provider):
                    async def complete(self,r):
                        if failure:raise ModelConnectionError()
                        return await super().complete(r)
                with patch.object(t,'LOCAL',root/'private'),patch.object(t,'PUBLIC',root/'public'),patch('backend.assembly.ROOT',root),patch('harness.deepseek_trial.load_project_env'),patch.object(ServiceConfig,'from_environment',return_value=c),patch('model_adapter.deepseek.create_adapter',side_effect=lambda *a,**kw:RehearsalProvider()),patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash','DEEPSEEK_API_KEY':'fixture'}):
                    result=asyncio.run(t.run())
                if failure:self.assertEqual(len(result['control']),1)
                else:
                    self.assertEqual(len(result['control']),28);self.assertFalse(result['unexecuted'])
                    for i in range(4):
                        pair=[r for r in result['control'] if r['case_id'].startswith(f'B{i+1}-')]
                        inputs=[json.loads((root/'private/batch'/r['accepted']['run_id']/'input.json').read_text(encoding='utf-8')) for r in pair]
                        self.assertEqual(inputs[0],inputs[1])
                freeze=json.loads((root/'private/freeze.json').read_text(encoding='utf-8'));self.assertEqual(freeze,json.loads((root/'public/freeze.json').read_text(encoding='utf-8')))
                self.assertEqual(freeze['plan']['logical_slots'],28)
                (root/'private/batch/runs.sqlite3').rename(root/'released.sqlite3')


if __name__=='__main__':unittest.main()
