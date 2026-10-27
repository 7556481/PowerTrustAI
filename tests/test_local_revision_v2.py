from tests.temp_paths import ignored_temporary_directory
"""Hand-authored engineering checks, never repaired historical model predictions."""
import asyncio,json,os,tempfile,unittest
from dataclasses import replace
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from agents.contracts import (RevisionInput, LiteralVerificationOutput, PowerDomainReviewOutput)
from core.models import (AnswerDraft,Evidence,EvidenceExcerpt,CitationBinding,TaskRequest,TaskMode,EngineeringContext,DomainFinding,Severity)
from core.literal_review import LiteralDefect,LiteralUnitReview
from core.validation import ContractError,validate_revision
from services.answer_anchors import anchors
from services.local_revision_v2 import plan,parse,system,example,VERSION,ScopedLocalRevisionAgent
from model_adapter.contracts import ModelResponse,ModelSettings,ModelOutputError
from model_adapter.runtime import ModelBudget,model_scope


def inputs(dependent=False):
    e=Evidence('limit','synthetic','v1','fixture limit','Under C, the permitted setting is 3 kV. It does not exceed 5 kV.','synthetic_fixture')
    other=Evidence('relay','synthetic-relay','v1','fixture relay','The relay has two terminals.','synthetic_fixture')
    paragraphs=['Under C, the permitted setting is 9 kV. The relay has two terminals.']
    if dependent:paragraphs.append('The permitted setting exceeds 5 kV.')
    paragraphs.append('The relay has two terminals.')
    text='\n\n'.join(paragraphs);a=AnswerDraft('new-handwritten-fixture',1,text,citations=(CitationBinding(0,len(paragraphs[0]),('limit','relay')),CitationBinding(len(text)-len(paragraphs[-1]),len(text),('relay',))))
    aa=anchors(a);q=EvidenceExcerpt(e.evidence_id,e.text,0,len(e.text));r=EvidenceExcerpt(other.evidence_id,other.text,0,len(other.text))
    ds=[LiteralDefect('defect-setting',aa[0]['anchor_id'],'9 kV',aa[0]['text'].index('9 kV'),aa[0]['text'].index('9 kV')+4,'Source states 3 not9 under C.','Correct setting only; retain relay fact.',(q,))]
    if dependent:ds.append(LiteralDefect('defect-conclusion',aa[1]['anchor_id'],aa[1]['text'],aa[1]['start_offset'],aa[1]['end_offset'],'Source states it does not exceed5.','Correct conclusion consistently with premise.',(q,)))
    reviews=tuple(LiteralUnitReview(x['anchor_id'],x['text'],x['start_offset'],x['end_offset'],'contradicted' if i<len(aa)-1 else 'supported','Synthetic complete unit judgment.','adequate',(q,) if i<len(aa)-1 else (r,)) for i,x in enumerate(aa))
    v=LiteralVerificationOutput(a.answer_id,a.version,(),(),(e,other),literal_reviews=reviews,literal_defects=tuple(ds))
    f=DomainFinding('domain-scope',a.answer_id,a.version,(),Severity.LOW,'analysis_scope','Correct the same overly broad setting assertion.',check_status='warning')
    domain=PowerDomainReviewOutput(a.answer_id,a.version,(f,),(e,other))
    req=TaskRequest('handwritten',TaskMode.ASSESS_EXISTING,'concept','Explain the given setting and retain the relay fact.',existing_answer=a,provided_evidence=(e,other),engineering_context=EngineeringContext(goal='conceptual'))
    return RevisionInput(req,a,v,domain,(e,other),())


def proposal(p,dependent=False,no_change=False):
    if no_change:return dict(context_id=p.payload['context_id'],edits=[],opinion_actions=[dict(opinion_ref=o,action='unresolved',edit_indices=[],explanation='Handwritten disputed action, no edit.') for o in p.opinions])
    owners={u:[d for d,x in p.authorities.items() if x.anchor_id==a['anchor_id']] for u,a in p.units.items()}
    refs={e.evidence_id:k for k,e in p.sources.items()}
    edits=[dict(unit_ref='U0',authorization_refs=owners['U0'],text='Under C, the permitted setting is 3 kV. The relay has two terminals.',support_refs=[refs['limit'],refs['relay']],dependencies=[])]
    if dependent:edits.append(dict(unit_ref='U1',authorization_refs=owners['U1']+owners['U0'],text='The permitted setting does not exceed 5 kV.',support_refs=[refs['limit']],dependencies=[dict(unit_ref='U0',reason='The conclusion depends on the corrected setting in U0 as well as having its own sourced defect.')]))
    actions=[]
    for o,data in p.opinions.items():
        idx=[i for i,e in enumerate(edits) if data['authority_ref'] in e['authorization_refs']] if data['authority_ref'] else [0]
        actions.append(dict(opinion_ref=o,action='modified',edit_indices=idx,explanation='Handwritten proposed edit addresses this opinion, not proof of resolution.'))
    return dict(context_id=p.payload['context_id'],edits=edits,opinion_actions=actions)


class V2Tests(unittest.TestCase):
    def exercise_factory(self,*,no_change=False,storage_fault=False):
        from backend.config import ServiceConfig
        from backend.assembly import ComponentFactory
        from backend.store import RunStore
        from backend.serialization import wire
        from evaluation.archive_replay import restore
        from harness.contracts import HarnessResult
        from tests.test_literal_review_v1 import Provider,fixture
        from tests.test_schema14_factory_flow import GOOD
        from rag.storage import KnowledgeStore,SourceMetadata
        class ProviderV2(Provider):
            async def complete(self,r):
                if r.prompt_version!=VERSION:return await super().complete(r)
                self.requests.append(r);d=json.loads(r.messages[1].content);self.payloads.append(d)
                auth=d['authorizations'][0];edits=[] if no_change else [dict(unit_ref=auth['unit_ref'],authorization_refs=[auth['authorization_ref']],text=GOOD,support_refs=[auth['source_spans'][0]['source_ref']],dependencies=[])]
                value=dict(context_id=d['context_id'],edits=edits,opinion_actions=[dict(opinion_ref=o['opinion_ref'],action='unresolved' if no_change else 'modified' if o['origin']=='source_bound_fact_defect' else 'retained',edit_indices=[] if no_change or o['origin']!='source_bound_fact_defect' else [0],explanation='Handwritten Factory fixture action; not semantic score.') for o in d['opinions']])
                return ModelResponse(json.dumps(value),r.model_id,finish_reason='stop')
        with ignored_temporary_directory(dir='data/retrieval_local') as tmp:
            root=Path(tmp).resolve();doc=root/'fixture.md';doc.write_text(GOOD,encoding='utf-8')
            with KnowledgeStore(root/'knowledge.sqlite3') as k:version=k.ingest(doc,'fixture').knowledge_version
            c=ServiceConfig(index_db=root/'knowledge.sqlite3',knowledge_version=version,run_db=root/'runs.sqlite3',fact_review_contract='literal_v1',local_revision_interface='source_actions_v2',execution_path='langgraph_v1')
            provider=ProviderV2();store=RunStore(c.run_db);req=fixture().request;store.create('fixture',req,{})
            def observe(v):
                if storage_fault and v['event'].component=='revision':raise OSError('Handwritten storage failure')
                store.checkpoint('fixture',v)
            async def go():
                f=ComponentFactory(c);b=None
                try:
                    b=f.create('fixture',observe);b.harness.retriever=None
                    return await b.harness.run(req,c.budget,run_id='fixture')
                finally:
                    if b:await b.drain();b.close()
                    await f.close()
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'synthetic','DEEPSEEK_API_KEY':'fixture'}),patch('model_adapter.deepseek.create_adapter',return_value=provider),patch('backend.assembly.ROOT',root):
                if storage_fault:
                    from harness.execution import HarnessObserverError
                    with self.assertRaises(HarnessObserverError):asyncio.run(go())
                    self.assertEqual(sum(r.prompt_version==VERSION for r in provider.requests),1)
                    store.close();return None,provider
                result=asyncio.run(go());manifest=ComponentFactory(c).manifest(version)
                self.assertEqual(manifest['contracts']['revision'],VERSION)
                self.assertEqual(ComponentFactory(replace(c,local_revision_interface='production')).manifest(version)['contracts']['revision'],'literal-local-revision-v1')
            raw=wire(result);store.mark('fixture','finished',result=raw);self.assertEqual(store.get('fixture')['result'],raw)
            self.assertEqual(wire(restore(raw,HarnessResult)),raw);store.close();c.run_db.rename(root/'released.sqlite3')
            return result,provider

    def test_factory_graph_full_reaudit_store_and_old_reading(self):
        r,p=self.exercise_factory();self.assertFalse(r.execution_issues,r.execution_issues)
        self.assertEqual(r.answer.version,2);self.assertEqual(len(r.review_rounds),2)
        self.assertEqual(sum(x.prompt_version.startswith('atomic-claims') for x in p.requests),2)
        self.assertEqual(sum(x.prompt_version.startswith('power-domain') for x in p.requests),2)

    def test_factory_no_change_and_shared_storage_stop(self):
        r,p=self.exercise_factory(no_change=True);self.assertFalse(r.execution_issues)
        self.assertEqual(r.answer.version,1);self.assertEqual(len(r.revision_outputs),1)
        self.assertEqual(r.report.decision.reason_codes,('LOCAL_REVISION_NO_CHANGE',))
        self.assertEqual(sum(x.prompt_version==VERSION for x in p.requests),1)
        self.exercise_factory(storage_fault=True)

    def test_mixed_source_authority_separate_from_opinion_accounting(self):
        inp=inputs();p=plan(inp);v=proposal(p);out=parse(v,p)
        validate_revision(out,inp.answer,inp.allowed_evidence,inp.domain_review.findings,revision_context=inp)
        self.assertEqual(out.answer.text.split('\n\n')[0],v['edits'][0]['text'])
        self.assertEqual(out.answer.text.split('\n\n')[-1],anchors(inp.answer)[-1]['text'])
        self.assertEqual(out.answer.citations[0].evidence_ids,('limit','relay'))
        self.assertEqual(len(out.finding_actions),2);self.assertTrue(out.preservation)
        x=deepcopy(v);x['edits'][0]['authorization_refs']=[next(k for k,o in p.opinions.items() if o['authority_ref'] is None)]
        with self.assertRaises(ContractError) as cm:parse(x,p)
        self.assertIn('legal_authorization_ref_required',[e['constraint'] for e in cm.exception.diagnostic['errors']])
        x=deepcopy(v);x['edits'][0]['support_refs']=[k for k,e in p.sources.items() if e.evidence_id=='relay']
        with self.assertRaises(ContractError) as cm:parse(x,p)
        self.assertIn('authorization_source_must_be_selected',[e['constraint'] for e in cm.exception.diagnostic['errors']])

    def test_own_error_and_premise_dependency_not_exclusive(self):
        p=plan(inputs(True));v=proposal(p,True);out=parse(v,p)
        link=next(l for l in out.edit_links if l['edit_index']==1)
        self.assertEqual(len(link['same_location']),1);self.assertEqual(len(link['other_location']),1)
        self.assertEqual(len(link['dependencies']),1)
        x=deepcopy(v);x['edits'][1]['dependencies']=[]
        with self.assertRaises(ContractError):parse(x,p)

    def test_unauthorized_cross_unit_edit_and_unrelated_source_rejected(self):
        inp=inputs();extra=Evidence('unrelated','other','v1','other','Unrelated body.','synthetic_fixture')
        p=plan(replace(inp,allowed_evidence=inp.allowed_evidence+(extra,)))
        self.assertNotIn('unrelated',[s.evidence_id for s in p.sources.values()])
        v=proposal(p);v['edits'].append(dict(v['edits'][0],unit_ref='U1',text='An unrelated claim.',dependencies=[]))
        with self.assertRaises(ContractError):parse(v,p)

    def test_diagnostics_collect_independent_errors_with_roles_and_safe_parent_types(self):
        p=plan(inputs());v=proposal(p);v['type']='json_object';v['context_id']='old-context'
        v['edits'][0]['authorization_refs']=['O1'];v['edits'][0]['support_refs']=[];v['opinion_actions'][0]['opinion_ref']='D0'
        with self.assertRaises(ContractError) as cm:parse(v,p)
        es=cm.exception.diagnostic['errors'];rules={e['constraint'] for e in es}
        self.assertTrue({'unexpected_fields_not_allowed','answer_version_context_mismatch','legal_authorization_ref_required','nonempty_support_source_ref_required','legal_opinion_ref_required'}<=rules)
        self.assertTrue(any(e['field_path']=='$.edits[0].authorization_refs[0]' and e['allowed_ids']==list(p.authorities) for e in es))
        for bad in (None,[],{'edits':[None,{'dependencies':[[],{}]}],'opinion_actions':[[],{'opinion_ref':[]}]}):
            with self.assertRaises(ContractError):parse(bad,p)
        name='bad"\n'+('x'*300);v[name]=True
        with self.assertRaises(ContractError) as cm:parse(v,p)
        encoded=cm.exception.diagnostic['errors'][0]['unknown_field_names']
        self.assertTrue(all(len(x)<200 for x in encoded));self.assertNotIn('\n',encoded[-1])

    def test_duplicates_version_no_change_and_reconstruction(self):
        inp=inputs();p=plan(inp);out=parse(proposal(p,no_change=True),p)
        self.assertEqual(out.answer,inp.answer);self.assertFalse(out.replacements)
        unsorted=replace(inp,answer=replace(inp.answer,citations=tuple(reversed(inp.answer.citations))))
        np=plan(unsorted)
        self.assertEqual(parse(proposal(np,no_change=True),np).answer,unsorted.answer)
        for mutate in (lambda v:v['edits'].append(v['edits'][0]),lambda v:v['opinion_actions'].pop(),lambda v:v['opinion_actions'].append(v['opinion_actions'][0]),lambda v:v['edits'][0].update(text=p.units['U0']['text'])):
            v=proposal(p);mutate(v)
            with self.assertRaises(ContractError):parse(v,p)
        changed=replace(inp,answer=replace(inp.answer,version=2),verification=replace(inp.verification,answer_version=2),domain_review=replace(inp.domain_review,answer_version=2))
        # Old anchors cannot bind a new version, even if the text is identical.
        with self.assertRaises(ContractError):plan(changed)
        applied=parse(proposal(p),p)
        with self.assertRaises(ContractError):validate_revision(replace(applied,answer=replace(applied.answer,text='forged')),inp.answer,inp.allowed_evidence,inp.domain_review.findings,revision_context=inp)
        short=replace(inp,request=replace(inp.request,question='最多10字'))
        with self.assertRaises(ContractError):parse(proposal(plan(short)),plan(short))
        for invalid in (replace(inp,allowed_evidence=inp.allowed_evidence+(inp.allowed_evidence[0],)),replace(inp,verification=replace(inp.verification,literal_reviews=inp.verification.literal_reviews+(inp.verification.literal_reviews[0],)))):
            with self.assertRaises(ContractError):plan(invalid)

    @unittest.skipUnless(Path('data/retrieval_local/literal-review-stage1-v1/batch/summary.json').exists(),'Private historical archive unavailable')
    def test_all_eight_unchanged_old_refusals_and_four_real_projections(self):
        from evaluation.local_revision_offline_v1 import old_input,SEQUENCES,independent_old_errors
        from services.literal_review_v1 import parse_revision as old_parse
        from services.structured_model import strict_json
        count=0
        for n in SEQUENCES:
            inp,msg,data,text=old_input(n);raw=strict_json(text)
            with self.assertRaises(ContractError):old_parse(raw,inp)
            p=plan(inp)
            with self.assertRaises(ContractError):parse(raw,p) # No cleaning/ID or label transformation.
            audit=independent_old_errors(raw,inp);self.assertTrue(audit['opinion_accounting_complete'])
            self.assertTrue(audit['independently_observable'])
            if not msg['correction']:
                count+=1
                self.assertNotIn('verification',p.payload);self.assertNotIn('domain_review',p.payload)
                self.assertEqual(len({s['evidence_id'] for s in p.payload['sources']}),len(p.payload['sources']))
                for s in p.payload['sources']:self.assertEqual(s['text'],next(e.text for e in inp.allowed_evidence if e.evidence_id==s['evidence_id']))
                expected={e for c in inp.answer.citations for e in c.evidence_ids}|{q.evidence_id for d in inp.verification.literal_defects for q in d.sources}
                self.assertTrue(expected<={s['evidence_id'] for s in p.payload['sources']})
        self.assertEqual(count,4)

    def test_new_static_examples_are_synthetic_and_apply_or_refuse_as_declared(self):
        from evaluation.local_revision_static_examples_v2 import examples
        rows=examples();self.assertEqual(len(rows),4)
        for row in rows[:3]:
            self.assertEqual(row['program_derived']['answer']['version'],2)
            self.assertTrue(all(s['source_type']=='synthetic_fixture' for s in row['actual_message_input']['sources']))
        self.assertFalse(rows[-1]['program_derived']['applied'])

    def test_actual_message_white_projection_and_one_correction_all_errors(self):
        inp=inputs();p=plan(inp);valid=proposal(p);bad=deepcopy(valid);bad['type']='json_object';bad['edits'][0]['authorization_refs']=['O1']
        seen=[]
        class Adapter:
            async def complete(self,r):
                seen.append(r);return ModelResponse(json.dumps(bad if len(seen)==1 else valid),r.model_id,finish_reason='stop')
        async def go():
            budget=ModelBudget(2)
            with model_scope(budget):return await ScopedLocalRevisionAgent(Adapter(),ModelSettings('synthetic')).run(inp)
        out=asyncio.run(go());self.assertEqual(out.answer.version,2);self.assertEqual(len(seen),2)
        data=json.loads(seen[0].messages[1].content)
        self.assertNotIn('verification',data);self.assertNotIn('domain_review',data)
        self.assertEqual([s['text'] for s in data['sources']],[s.text for s in p.sources.values()])
        correction=json.loads(seen[1].messages[-1].content)
        self.assertEqual(correction['invalid_output'],json.dumps(bad))
        self.assertGreaterEqual(len(correction['validation_errors']),2)
        self.assertEqual(correction['program_scope_guidance']['authorization_refs'],list(p.authorities))
        self.assertIn('action EXACT opinion_ref,action,edit_indices,explanation',system());self.assertEqual(set(example()),{'context_id','edits','opinion_actions'})

    def test_parser_bug_not_corrected_and_budget_timeout_cancel(self):
        class Adapter:
            def __init__(self):self.calls=0
            async def complete(self,r):self.calls+=1;return ModelResponse('{}',r.model_id,finish_reason='stop')
        adapter=Adapter()
        with patch('services.local_revision_v2.parse',side_effect=TypeError('private implementation detail')):
            with self.assertRaises(RuntimeError):asyncio.run(ScopedLocalRevisionAgent(adapter,ModelSettings('synthetic')).run(inputs()))
        self.assertEqual(adapter.calls,1)
        from model_adapter.contracts import ModelBudgetError,ModelTimeoutError
        class Wait:
            async def complete(self,r):await asyncio.sleep(1)
        async def go(zero=False,cancel=False):
            with model_scope(ModelBudget(0 if zero else 2)):
                task=asyncio.create_task(ScopedLocalRevisionAgent(Wait(),ModelSettings('synthetic',timeout_seconds=.01)).run(inputs()))
                if cancel:await asyncio.sleep(.001);task.cancel()
                return await task
        with self.assertRaises(ModelBudgetError):asyncio.run(go(zero=True))
        with self.assertRaises(ModelTimeoutError):asyncio.run(go())
        with self.assertRaises(asyncio.CancelledError):asyncio.run(go(cancel=True))


if __name__=='__main__':unittest.main()
