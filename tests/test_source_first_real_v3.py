"""Deterministic replies for real-index wiring; never semantic model scores."""
import json,unittest,asyncio
from dataclasses import replace
from tests.test_source_first_live_v2 import Substitute
from tests.test_literal_review_v1 import response
from model_adapter.contracts import ModelResponse,ModelUsage

class ActualInputSubstitute(Substitute):
    def __init__(self,mode='normal'):super().__init__();self.mode=mode;self.counts={}
    async def complete(self,r):
        from services.source_first_audit_v1 import VERSION
        from services.local_revision_v2 import VERSION as RV
        d=json.loads(r.messages[1].content)
        if r.prompt_version==VERSION:
            answer=d['answer'];key=(answer['answer_id'],answer['version']);n=self.counts.get(key,0);self.counts[key]=n+1
            v=response(d);v['defects']=[]
            for row in v['units']:row['status']='supported'
            # A deterministic evidence-gap response, not a quality label.
            if 'N5' in answer['answer_id']:
                for row in v['units']:row.update(status='insufficient_evidence',quote_ids=[])
                for row in v['citations']:row.update(status='insufficient_evidence',quote_ids=[])
            else:
                pairs=[('需联合确定','可能需要联合研究确定'),('并非用于热额定值考核，而是用于确定稳定性限制','在确定稳定性限制时也予以考虑')]
                for a in d['units']:
                    for target,new in pairs:
                        if target in a['text']:
                            row=next(x for x in v['units'] if x['anchor_id']==a['anchor_id']);row['status']='contradicted'
                            ids=a['allowed_quote_ids'][:1]
                            v['defects'].append(dict(anchor_id=a['anchor_id'],original_text=target,difference='Synthetic source-bound test difference; not a model score.',correction_boundary='Synthetic local replacement; preserve other content.',quote_ids=ids))
            out=ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        elif r.prompt_version==RV:
            edits=[]
            for auth in d['authorizations']:
                unit=next(u for u in d['units'] if u['unit_ref']==auth['unit_ref'])
                text=unit['text'].replace('需联合确定','可能需要联合研究确定').replace('并非用于热额定值考核，而是用于确定稳定性限制','在确定稳定性限制时也予以考虑')
                edits.append(dict(unit_ref=unit['unit_ref'],authorization_refs=[auth['authorization_ref']],text=text,
                    support_refs=list(dict.fromkeys([s['source_ref'] for s in auth['source_spans']]+[s['source_ref'] for s in unit['prior_support']])),dependencies=[]))
            v=dict(context_id='wrong' if self.mode=='revision_failure' else d['context_id'],edits=edits,
                opinion_actions=[dict(opinion_ref=o['opinion_ref'],action='modified' if o['origin']=='source_bound_fact_defect' else 'retained',edit_indices=list(range(len(edits))) if o['origin']=='source_bound_fact_defect' else [],explanation='Synthetic action, not proof of repair') for o in d['opinions']])
            out=ModelResponse(json.dumps(v),r.model_id,finish_reason='stop')
        else:return await super().complete(r)
        return replace(out,usage=ModelUsage(10,5,15,cache_hit_tokens=0,cache_miss_tokens=10))

class BudgetV3Tests(unittest.TestCase):
    def test_actual_nonempty_neighbor_revision_strict_report_and_restart(self):
        from pathlib import Path
        import tempfile,os
        from unittest.mock import patch
        from backend.config import ServiceConfig
        from backend.serialization import wire
        from core.models import ClaimExtractionOutput
        from core.validation import validate_report,ContractError
        from evaluation.archive_replay import restore
        from harness.contracts import HarnessResult
        from model_adapter.runtime import model_scope,ModelBudget
        from model_adapter.contracts import ModelSettings
        from services.claim_extractor import ModelClaimExtractor
        from services.evidence_scope import make_snapshot
        from rag.storage import KnowledgeStore,SourceMetadata
        from tests.test_literal_review_v1 import fixture
        from tests.test_source_first_live_v2 import Substitute
        from tests.test_schema14_factory_flow import GOOD
        from evaluation.source_first_real_v3 import batch,Gate
        async def go(root):
            from tests.pdf_fixtures import make_pdf
            doc=root/'fixture.pdf';doc.write_bytes(make_pdf([GOOD+' The synthetic setting applies under condition C.','Additional synthetic source context.']))
            with KnowledgeStore(root/'index.sqlite3') as k:
                version=k.ingest(doc,'fixture',SourceMetadata(source_type='synthetic_fixture')).knowledge_version
                candidates=[k.evidence(row['fragment_id'],version) for row in k.rows(version)]
                e=next(e for e in candidates if GOOD in e.text)
                self.assertTrue(e.provenance.next_fragment_id or e.provenance.previous_fragment_id)
            inp=fixture();a=replace(inp.answer,citations=tuple(replace(c,evidence_ids=(e.evidence_id,)) for c in inp.answer.citations))
            req=replace(inp.request,existing_answer=a,provided_evidence=(e,));provider=Substitute()
            with model_scope(ModelBudget(2)):
                extraction=await ModelClaimExtractor(provider,ModelSettings('deepseek-flash',90,8000,96000),typed_components=True,protocol_version=7,daily_guidance=True).extract(a)
            m=dict(cases=[dict(request=wire(req),snapshot=wire(make_snapshot(a,(e,),version)),extraction=wire(extraction))])
            c=ServiceConfig(index_db=root/'index.sqlite3',knowledge_version=version,execution_path='langgraph_v1')
            with patch.dict(os.environ,{'DEEPSEEK_MODEL_ID':'deepseek-flash'}),patch('backend.assembly.ROOT',root):
                s=await batch(c,m,root/'batch',lambda *a,**k:provider,Gate(root/'batch'),rows=[dict(id='S1-candidate',input=dict(line='B',case=0,variant='candidate'))])
            raw=next(iter(s['outputs'].values()));out=restore(raw,HarnessResult)
            self.assertFalse(out.execution_issues,out.execution_issues)
            self.assertEqual(out.answer.version,2);self.assertEqual(len(out.review_rounds),2)
            self.assertTrue(any(r.context_evidence_ids for r in out.retrieval_records))
            self.assertTrue(any(b.origin=='index_adjacent_context' and b.core_evidence_ids for b in out.evidence_bindings))
            validate_report(out.report)
            with self.assertRaises(ContractError):validate_report(replace(out.report,literal_reviews=()))
        with tempfile.TemporaryDirectory(dir='data/retrieval_local') as tmp:asyncio.run(go(Path(tmp).resolve()))

    def test_twenty_chain_and_one_sixty_global_boundary(self):
        from evaluation.source_first_real_v3 import Gate
        from types import SimpleNamespace as NS
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            g=Gate(Path(tmp));r=NS(model_id='deepseek-flash',max_output_tokens=8000,messages=[])
            for chain in range(8):
                for i in range(20):g(dict(case=chain,variant='test'),r,1)
            self.assertEqual(g.calls,160)
            with self.assertRaises(RuntimeError):g(dict(case=9,variant='test'),r,1)
