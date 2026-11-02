import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend.config import ServiceConfig
class ManagedFastChecks(unittest.TestCase):
 def root(self,t,missing=False):
  root=Path(t);d=root/'data/runtime_local';d.mkdir(parents=True);manifest=root/'data/accepted/manifest.json';manifest.parent.mkdir()
  if not missing:manifest.write_text('{}')
  (d/'fast-retrieval.json').write_text(json.dumps({'version':'fast-retrieval-service-v1','manifest':'data/accepted/manifest.json','knowledge_version':'synthetic_fixture'}));return root
 def test_explicit_managed_fast_and_demo_ignores(self):
  with tempfile.TemporaryDirectory() as t:
   root=self.root(t)
   with patch('backend.config.ROOT',root),patch('harness.deepseek_trial.load_project_env'),patch.dict('os.environ',{'POWERTRUST_KNOWLEDGE_VERSION':'synthetic_fixture'}):
    c=ServiceConfig.from_environment();self.assertEqual(c.tantivy_worker_mode,'fast_v1');self.assertEqual(c.verification_schema,13);self.assertIsNone(ServiceConfig.from_environment(demo=True).tantivy_manifest)
 def test_missing_index_explicit_failure(self):
  with tempfile.TemporaryDirectory() as t:
   root=self.root(t,True)
   with patch('backend.config.ROOT',root),patch('harness.deepseek_trial.load_project_env'),patch.dict('os.environ',{'POWERTRUST_KNOWLEDGE_VERSION':'synthetic_fixture'}):
    with self.assertRaises(ValueError):ServiceConfig.from_environment()
 def test_legacy_audit_candidate_cannot_mix(self):
  with self.assertRaises(ValueError):ServiceConfig(tantivy_manifest=Path('unused'),tantivy_worker_mode='fast_v1',fact_review_execution='citation_pair_v1')
 def test_smoke_is_one_frozen_question_and_owner_removal_restores_daily_admission(self):
  import hashlib
  from types import SimpleNamespace as N
  from backend.assembly import ComponentFactory,ConfigurationError
  with tempfile.TemporaryDirectory() as t:
   root=self.root(t);d=root/'data/runtime_local';b=d/'accounting';b.mkdir();(b/'state.json').write_text('{}');owner=d/'publication-smoke.json';question='synthetic_fixture'
   owner.write_text(json.dumps({'version':'publication-smoke-budget-v1','budget_dir':'data/runtime_local/accounting','question_sha256':hashlib.sha256(question.encode()).hexdigest()}))
   with patch('backend.config.ROOT',root),patch('harness.deepseek_trial.load_project_env'),patch.dict('os.environ',{'POWERTRUST_KNOWLEDGE_VERSION':'synthetic_fixture'}):c=ServiceConfig.from_environment();self.assertIsNone(ServiceConfig.from_environment(demo=True).model_budget_dir)
   f=ComponentFactory(c);request=N(question=question,mode=N(value='question_answer'));f.bind_budget_task('one',request)
   with self.assertRaises(ConfigurationError):f.bind_budget_task('two',request)
   owner.unlink();f.bind_budget_task('daily',N(question='ordinary',mode=N(value='question_answer')));self.assertNotIn('daily',f._budget_runs)
if __name__=='__main__':unittest.main()
