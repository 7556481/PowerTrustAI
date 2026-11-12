import asyncio,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
from core.models import Evidence,EvidenceProvenance
from rag.contracts import RetrievalRequest,RetrievalPurpose,RetrievalResult,RetrievalHit,ContextOptions,ContextResult
from evaluation.fast_overlap_v27 import select,CandidateRetriever

class FrozenSelectionTests(unittest.TestCase):
    def evidence(self,i,text):return Evidence(i,'source','version','original-range',text,'synthetic_fixture')
    def select(self,q,items,**kw):
        with patch('evaluation.fast_overlap_v27.query_tokens',return_value=set(q.split())),patch('rag.chinese_terms.terms',side_effect=lambda text:tuple(text.split())):
            return select(q,items,**kw)
    def test_full_spans_budget_and_identity_only_dedup(self):
        a=self.evidence('a','alpha');b=self.evidence('b','beta')
        chosen,trace=self.select('alpha beta',[a,a,b],max_results=3,root_chars=9)
        self.assertEqual(chosen,(a,b));self.assertEqual(trace['root_chars'],9)
        self.assertIs(chosen[0],a)
        chosen,_=self.select('alpha',[self.evidence('long','alpha '*20),a],root_chars=5)
        self.assertEqual(chosen,(a,))
    def test_conflicting_identity_rejected_and_equal_text_other_ids_preserved(self):
        a=self.evidence('same','alpha');b=self.evidence('other','alpha')
        chosen,_=self.select('alpha',[a,b]);self.assertEqual(chosen,(a,b))
        with self.assertRaises(ValueError):self.select('alpha',[a,replace(a,text='beta')])
    def test_coverage_selection_does_not_depend_on_evidence_id(self):
        items=[self.evidence('x','alpha alpha alpha'),self.evidence('y','alpha'),self.evidence('z','beta')]
        a,_=self.select('alpha beta',items,max_results=2)
        b,_=self.select('alpha beta',[replace(e,evidence_id='renamed'+str(i)) for i,e in enumerate(items)],max_results=2)
        self.assertEqual([e.text for e in a],[e.text for e in b]);self.assertIn('beta',{e.text for e in a});self.assertTrue(any('alpha' in e.text for e in a))
    def test_candidate_wider_pool_then_original_context_and_certificate(self):
        a=self.evidence('a','alpha');hit=RetrievalHit('a','fragment',1,1.0,'synthetic')
        class Native:
            cache_identity=('fixture',);execution_profile='topic_v4_subject_v1';last_trace={}
            async def retrieve(obj,r):obj.request=r;return RetrievalResult((a,),r.knowledge_version,hits=(hit,))
            async def source_context(obj,items,k,options):obj.context=(items,k,options);return ContextResult((),0,options)
            async def validate_evidence(obj,items,k):obj.validated=(items,k)
            def close(obj):pass
        async def run():
            native=Native();reader=CandidateRetriever(native);request=RetrievalRequest('alpha','fixture',RetrievalPurpose.VERIFICATION,'k',3,ContextOptions())
            with patch('evaluation.fast_overlap_v27.query_tokens',return_value={'alpha'}),patch('rag.chinese_terms.terms',return_value=('alpha',)):
                result=await reader.retrieve(request)
            self.assertEqual(native.request.max_results,6);self.assertIsNone(native.request.context_options);self.assertEqual(native.context[0],(a,))
            await reader.validate_result(request,result)
            with self.assertRaises(ValueError):await reader.validate_result(replace(request,query='other'),result)
        asyncio.run(run())

@unittest.skipUnless(importlib.util.find_spec('tantivy'),'optional native sample dependency unavailable')
class PackedLookupTests(unittest.TestCase):
    def test_old_identity_and_original_payload_need_no_sqlite(self):
        import tantivy,sqlite3
        from evaluation.fast_overlap_pack_v27 import PackedCatalog,sha
        from backend.serialization import wire
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);native=root/'index';native.mkdir();schema=tantivy.SchemaBuilder();schema.add_text_field('fid',stored=True,tokenizer_name='raw');schema.add_text_field('terms',stored=True);schema.add_bytes_field('payload',stored=True)
            index=tantivy.Index(schema.build(),path=str(native));writer=index.writer(heap_size=20000000,num_threads=1)
            text='alpha beta';provenance=EvidenceProvenance('doc','doc-v','f'*64,'legacy-fid','k',0,len(text),1,1)
            e=Evidence('legacy-id','doc','doc-v','chars[0:10)',text,'synthetic_fixture',provenance=provenance)
            payload=json.dumps({'evidence':wire(e),'terms_sha':hashlib.sha256(text.encode()).hexdigest(),'body_sha':hashlib.sha256(text.encode()).hexdigest()}).encode();doc=tantivy.Document();doc.add_text('fid','legacy-fid');doc.add_text('terms',text);doc.add_bytes('payload',payload);writer.add_document(doc);writer.commit();writer.wait_merging_threads();index.reload()
            (root/'asset.json').write_text(json.dumps({'knowledge_version':'k','files':{p.name:sha(p) for p in native.iterdir() if p.is_file() and not p.name.endswith('.lock')}}))
            with patch.object(sqlite3,'connect',side_effect=PermissionError('unavailable')):
                catalog=PackedCatalog(root);self.assertEqual(catalog.evidence('legacy-fid','k'),e);self.assertEqual(catalog.verify_evidence(e),e)
