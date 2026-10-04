import unittest
from backend.serialization import safe,public_https
from backend.presentation import explain

class ProjectionTests(unittest.TestCase):
    def test_json_field_path_is_not_a_local_file_path(self):
        self.assertEqual(safe({'field_path':'$.findings[2].bases'})['field_path'],'$.findings[2].bases')
        self.assertEqual(safe({'field_path':'D:/private/a.json'})['field_path'],'[local-path-hidden]')
    def test_official_https_preserved(self):
        uri='https://www.nerc.com/pa/RAPA/ra/Reliability%20Assessments%20DL/report.pdf'
        self.assertEqual(safe({'source_uri':uri})['source_uri'],uri)
    def test_invalid_or_private_uri_absent(self):
        for uri in ('javascript:alert(1)','file:///D:/data/a.pdf','D:/data/a.pdf','/private/a.pdf','https://localhost/a','https://127.0.0.1/a','https://u:p@example.org/a','https://example.org/?access_token=x','https://example.org/a#secret','https://example.org\\private'):
            with self.subTest(uri=uri):self.assertIsNone(public_https(uri))
        self.assertIsNone(safe({'source_uri':None})['source_uri'])
    def test_sensitive_fields_and_diagnostics(self):
        p=safe({'API_KEY':'fictional','nested':{'password':'fictional','access_token':'fictional'},'message':'Failure D:/private/a.db','source_uri':'https://www.nerc.com/a.pdf','text':'literal body'})
        self.assertNotIn('fictional',str(p));self.assertNotIn('D:/',str(p));self.assertEqual(p['text'],'literal body')

class ExplanationTests(unittest.TestCase):
    def test_workload_failure_is_execution_not_fact_contradiction(self):
        r=self.result(execution_issues=[{'code':'REVIEW_MESSAGE_CAPACITY_EXCEEDED'},{'code':'REVIEW_WORKLOAD_BUDGET_SHORTFALL'}])
        text=''.join(explain(r)['reasons'])
        self.assertIn('完整消息',text);self.assertIn('剩余调用额度',text);self.assertIn('不能据此判断事实矛盾',text)
    def result(self,**execution):
        return {'execution':dict(status='finished',required_stages_complete=True,all_required_checks_assessed=False,**execution),'findings':{},'answer':{'versions':[{'version':1}]},'evidence':[],'decision':{'kind':'review_required'}}
    def test_complete_but_unassessed_and_missing_prerequisites(self):
        r=self.result();r['findings']['domain']=[{'check_status':'not_assessable','missing_prerequisites':['operating point']}]
        p=explain(r);self.assertTrue(p['run_ended']);self.assertIn('两者可以同时成立',''.join(p['reasons']));self.assertIn('工程前提',''.join(p['reasons']));self.assertNotIn('缺少足够证据',''.join(p['reasons']))
    def test_evidence_contradiction_execution_separate(self):
        r=self.result(execution_issues=[{'code':'TIMEOUT'}]);r['findings']['model_fact']=[{'status':'insufficient_evidence'},{'status':'contradicted'}]
        text=''.join(explain(r)['reasons']);self.assertIn('执行',text);self.assertIn('缺少足够证据',text);self.assertIn('矛盾',text)
    def test_unknown_next_step_and_null_decision(self):
        r=self.result();r['decision']=None;p=explain(r);self.assertIn('待人工检查',p['next_steps'][0]);self.assertIn('1 个回答版本',p['saved'])
