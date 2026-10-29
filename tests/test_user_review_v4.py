import json,unittest,hashlib
from backend.user_review import reason,TASK,GAP,FALLBACK,project,scope_only

class UserReviewTests(unittest.TestCase):
    def test_product_policy_early_return_keeps_scope_note_out_of_missing_tasks(self):
        from tests.test_answer_annotations_v7 import sample
        from backend.presentation import explain
        r=sample();r['decision']=dict(kind='pass',policy_version='product-decision-v1',reasons=[])
        r['findings']['domain']=[dict(category='analysis_scope',check_status='no_issue',rationale='概念'+GAP+json.dumps([dict(index=0,applicability='scope_note',reason='非本题所需。')]))]
        p=explain(r);self.assertEqual(p['scope_note_indexes'],[0])

    def test_exact_known_payload_once_and_unknown_bad_fallback(self):
        natural='用户只请求概念解释；未声称厂站通过研究。'
        payload=dict(version='task-applicability-v1',scope='conceptual',reason=natural,answer_id='private-id',answer_sha256='private-hash')
        self.assertEqual(reason(natural+GAP+'[]'+TASK+json.dumps(payload)),natural)
        self.assertEqual(reason(natural+TASK+'{broken'),FALLBACK)
        self.assertEqual(reason(natural+' [task-applicability-v99] {}'),FALLBACK)
        self.assertEqual(reason('合法公式 f(x)={x², x>0}；区间[1,2]。'),'合法公式 f(x)={x², x>0}；区间[1,2]。')
        self.assertEqual(reason(natural+TASK+json.dumps(dict(payload,version='other'))),FALLBACK)

    def test_dedup_preserves_ids_and_different_roles_conflicts_sources(self):
        row=dict(opinion_id='a',finding_id='f1',origin='fact',status='insufficient_evidence',reason='证据不足。',evidence_ids=['e'],answer_id='a',answer_version=1,start=0,end=2)
        rows=project([row,dict(row,opinion_id='b',finding_id='f2'),dict(row,opinion_id='c',origin='domain'),dict(row,opinion_id='d',status='contradicted'),dict(row,opinion_id='e',evidence_ids=['other'])])
        self.assertEqual(len(rows),4);self.assertEqual(rows[0]['finding_ids'],['f1','f2']);self.assertEqual(rows[0]['opinion_ids'],['a','b'])

    def test_only_bound_general_program_notes_move_not_substantive_gaps(self):
        a=dict(answer_id='a',version=1,text='概念解释。');q='解释概念。'
        assessment=dict(version='task-applicability-v1',scope='conceptual',reason='概念',answer_id='a',answer_version=1,answer_sha256=hashlib.sha256(a['text'].encode()).hexdigest(),question_sha256=hashlib.sha256(q.encode()).hexdigest())
        f=dict(category='engineering_inputs',origin='program_rule',rationale='Input presence checked only; data are user-provided and quality/adequacy are not certified.')
        scope=dict(category='analysis_scope',rationale='概念'+TASK+json.dumps(assessment))
        r=dict(answer=dict(final=a),task_context=dict(question=q,structured_goal='conceptual'),findings=dict(domain=[scope]))
        self.assertTrue(scope_only(f,r));self.assertFalse(scope_only(dict(f,origin='model_judgment'),r))
        self.assertFalse(scope_only(dict(f,rationale='缺少当前任务必需的设备参数。'),r))
        scope['rationale']='工程'+TASK+json.dumps(dict(assessment,scope='engineering'))
        self.assertFalse(scope_only(f,r))
        scope['rationale']='旧版'+TASK+json.dumps(dict(assessment,answer_version=2))
        self.assertFalse(scope_only(f,r))
