"""Public synthetic fixtures; no API or private prerequisites."""
import json,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from rag.corpus_build import source_identity,writer_lease,build,sha
from tests import test_corpus_index
from contextlib import closing

class IdentityTests(unittest.TestCase):
 def test_stable_namespaced_identity_and_original_preservation(self):
  self.assertEqual(source_identity({'_id':123},'rev','a',0),('123',False))
  a=source_identity({},'rev','a',128)
  self.assertTrue(a[1]);self.assertTrue(a[0].startswith('industrycorpus2:row-v1:'))
  self.assertEqual(a,source_identity({},'rev','a',128))
  self.assertNotEqual(a,source_identity({},'rev','a',129));self.assertNotEqual(a,source_identity({},'other','a',128))
  self.assertNotEqual(a,source_identity({},'rev','b',128))
 def test_unique_writer(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'db'
   with writer_lease(p):
    with self.assertRaises(OSError):
     with writer_lease(p):pass
   with writer_lease(p):pass
 def test_cross_batch_rollback_resume_and_duplicate_identity(self):
  import pyarrow as pa,pyarrow.parquet as pq
  fixture=test_corpus_index.CorpusTests();fixture.setUp()
  try:
   folder=Path(fixture.tmp.name);shards=folder/'rows';shards.mkdir();p=shards/'english.parquet'
   texts=['Synthetic_fixture body '+str(i) for i in range(259)]+['Synthetic_fixture body 0']
   pq.write_table(pa.table({'text':texts}),p)
   m=folder/'manifest.json';m.write_text(json.dumps({'revision':'r'*40,'files':[{'path':p.name,'size':p.stat().st_size,'lfs':{'oid':sha(p)}}]}))
   a=SimpleNamespace(base=str(fixture.p),database=str(folder/'build.sqlite3'),base_knowledge=fixture.base,manifest=str(m),shards=str(shards),wait=False)
   from rag.corpus_index import add_record
   def fail(con,**kw):
    if kw['row_number']==130:raise RuntimeError('synthetic transaction failure')
    return add_record(con,**kw)
   with patch('rag.corpus_build.add_record',side_effect=fail):
    with self.assertRaises(RuntimeError):build(a)
   with closing(sqlite3.connect(a.database)) as c:
    self.assertEqual(c.execute('SELECT next_row FROM corpus_progress').fetchone()[0],128)
    self.assertEqual(c.execute('SELECT count(*) FROM corpus_identity').fetchone()[0],128)
   build(a);build(a)
   with closing(sqlite3.connect(a.database)) as c:
    self.assertEqual(c.execute('SELECT next_row,complete FROM corpus_progress').fetchone(),(260,1))
    rows=c.execute('SELECT row_number,internal_id,body_sha256,original_id_missing FROM corpus_identity ORDER BY row_number').fetchall()
    self.assertEqual(len(rows),260);self.assertEqual(len({r[1] for r in rows}),260)
    self.assertEqual(rows[128][1],source_identity({},'r'*40,p.name,128)[0]);self.assertEqual(rows[0][2],rows[-1][2])
    self.assertEqual(rows[-1][3],1)
  finally:fixture.tearDown()

class FidelityBoundaryTests(unittest.TestCase):
 def test_independent_truth_and_fidelity_different_topics(self):
  from tests.test_audit_interface_v2 import InterfaceTests
  from core.models import VerificationStatus
  cases=[('contradicted','faithful','All bacteria produce oxygen.','All bacteria produce oxygen.','Not all bacteria produce oxygen.'),('supported','disputed','Only on dry roads, braking distance stays short.','Braking distance stays short.','Only on dry roads, braking distance stays short.'),('supported','faithful','Granite is an igneous rock.','Granite is an igneous rock.','Granite is an igneous rock.')]
  for status,fidelity,answer_text,target_text,source_text in cases:
   reason="Synthetic_fixture answer-target comparison: "+answer_text+" -> "+target_text
   with self.subTest(reason=reason):
    def mutate(v,d):
     for f in v['findings']:
      for r in f['component_reviews']:
       r['status']=status;r['semantic_review']['fidelity']=fidelity;r['semantic_review']['rationale']=reason
       r['support_relation']['whole_claim_supported']=status=='supported'
    from tests.test_fact_rereview_v3 import inputs
    from core.models import AnswerDraft,Evidence
    from dataclasses import replace
    from services.answer_anchors import anchors
    from services.claim_obligations import parse
    from services.evidence_scope import make_snapshot
    inp=inputs(False);answer=AnswerDraft('synthetic-answer',2,answer_text)
    item={'anchor_id':anchors(answer)[0]['anchor_id'],'proposition':target_text,'claim_type':'technical_fact','assertion_role':'asserted','semantic_qualifiers':[],'components':[{'category':'technical_fact','proposition':target_text,'basis_target':'technical_content','verification_obligation':'technical_truth'}]}
    claims=parse({'claims':[item],'non_claims':[]},answer).claims
    seed=Evidence('independent','s1','v1','Synthetic_fixture',source_text,'synthetic_fixture')
    request=replace(inp.request,existing_answer=answer)
    inp=replace(inp,request=request,answer=answer,claims=claims,seed_evidence=(seed,),generation_snapshot=make_snapshot(answer,(seed,),None,request=request,prompt_version='synthetic_fixture'))
    with patch('tests.test_audit_interface_v2.inputs',return_value=inp):out,_=InterfaceTests().exercise(mutate)
    self.assertFalse(out.execution_issues);r=out.findings[0].component_reviews[0]
    self.assertEqual(r.raw_support_status,status);self.assertEqual(r.fidelity_status,fidelity)
    self.assertEqual(r.status,VerificationStatus.NOT_ASSESSABLE if fidelity=='disputed' else VerificationStatus(status))
