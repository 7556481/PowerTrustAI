"""Public synthetic fixtures, no archive, official text or API requirement."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from evaluation import support_dataset as d

def sample(prop='The value is 230 kV under rated conditions.',family='question-one',version=1):
    text='synthetic_fixture: The value is 230 kV under rated conditions.'
    task={'task_type':'factual_support','claim':{'text':prop,'proposition':prop,'assertion_role':'asserted',
        'qualifiers':['rated conditions'],'category':'technical','basis_target':'technical_content','scope':['rated conditions']},
        'answer_excerpt':prop,'evidence':[{'basis_id':'q1','evidence_id':'e1','text':text,'text_sha256':d.digest(text),
            'start_offset':10,'end_offset':10+len(text),'warnings':[],'metadata':{'source_uri':'https://example.org/fixture','file_page':2}}],
        'other_basis':[],'knowledge_version':'synthetic_fixture-k','delivery_state':'hits','required_evidence_delivery':'delivered'}
    origin={'run_id':'synthetic_fixture-run','answer_id':'answer','answer_version':version,'question_family':family,
        'lineage_root_sha256':'synthetic_fixture-lineage','request_sha256':'request','response_sha256':'response'}
    return d.make_sample(task,origin,{'structure_valid':True,'model_status':'supported','human_feedback':[]})

def archive(root,*,wrong_scope=None,error=None,model='synthetic_fixture',target='technical_content'):
    s=sample();e=s['task']['evidence'][0];quote={k:e[k] for k in ('text','evidence_id','start_offset','end_offset')};quote['quote_id']='q1'
    mapping={'claim_id':'c1','component_id':'co1','answer_id':'answer','answer_version':1,
        'knowledge_version':'synthetic_fixture-k','allowed_quote_ids':['q1'],'outcome':'hits'}
    if wrong_scope:mapping.update(wrong_scope)
    data={'answer':{'answer_id':'answer','version':1,'text':'synthetic_fixture answer'},'question':'synthetic_fixture question',
        'knowledge_version':'synthetic_fixture-k','claims':[{'claim_id':'c1','text':s['task']['claim']['text'],'qualifiers':['input condition'],
            'components':[{'component_id':'co1','proposition':s['task']['claim']['proposition'],'category':'technical'}],
            'component_basis_targets':[target]}],
        'QUOTE_CANDIDATES':[quote,dict(quote,quote_id='q2',evidence_id='e2',text='x',start_offset=0,end_offset=1)],
        'EVIDENCE_METADATA':[{'evidence_id':'e1','source_uri':'https://example.org/fixture'}],
        'FACT_EVIDENCE_DELIVERY':{'components':[mapping]},
        'TOOL_RESULTS':[{'result_id':'t1','status':'succeeded','payload':{'value':230}}],
        'GENERATION_INPUT_SNAPSHOT':{'question':'synthetic_fixture','answer_requirements':'not a label','prior_review_memory':'must not leak'}}
    response={'findings':[{'claim_id':'c1','applicability_conditions':['MODEL OUTPUT MUST NOT ENTER INPUT'],
        'component_reviews':[{'component_index':0,'status':'supported','rationale':'synthetic_fixture model proposal'}]}]}
    mp=root/'messages.json';d.write(mp,{'messages':[{'role':'system','content':'fixture'},{'role':'user','content':d.canonical(data)}]})
    text=d.canonical(response);path=root/'response-fixture.json'
    d.write(path,{'scope':'PRIVATE_MODEL_RESPONSE_DIAGNOSTIC','model_id':model,'request_messages_path':str(mp),
        'response_text':text,'response_sha256':d.digest(text),'validation_error':error,'prompt_version':'synthetic_fixture','call_number':1})
    return path

class SupportDatasetTests(unittest.TestCase):
    def test_extraction_scoped_evidence_and_input_not_output(self):
        with tempfile.TemporaryDirectory() as directory:
            archive(Path(directory));values,skips=d.extract(directory,model_ids={'synthetic_fixture'})
        self.assertFalse(skips);self.assertEqual(len(values),1);s=values[0]
        self.assertEqual([e['basis_id'] for e in s['task']['evidence']],['q1'])
        self.assertEqual(s['task']['claim']['scope'],['input condition'])
        self.assertEqual(s['task']['other_basis'][0]['type'],'tool_result')
        self.assertEqual(s['supervision']['status'],'pending');self.assertIsNone(s['supervision']['label'])

    def test_wrong_quote_version_and_knowledge_are_rejected(self):
        for wrong in ({'allowed_quote_ids':['q-other']},{'answer_version':2},{'knowledge_version':'other-k'}):
            with self.subTest(wrong=wrong),tempfile.TemporaryDirectory() as directory:
                archive(Path(directory),wrong_scope=wrong);values,skips=d.extract(directory)
                self.assertFalse(values);self.assertEqual(len(skips),1)

    def test_archive_model_selection_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            archive(Path(directory));values,skips=d.extract(directory,model_ids={'another-model'})
        self.assertFalse(values);self.assertEqual(skips[0]['reason'],'model_not_selected')

    def test_response_hash_and_outside_request_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=archive(Path(directory));r=d.read(path);r['response_sha256']='wrong';path.write_text(d.canonical(r),encoding='utf8')
            self.assertFalse(d.extract(directory)[0])
            r['request_messages_path']=str(Path(directory).parent/'outside.json');path.write_text(d.canonical(r),encoding='utf8')
            self.assertEqual(d.extract(directory)[1][0]['reason'],'request outside explicit archive root')

    def test_structure_failure_preserved_not_semantic_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            archive(Path(directory),error={'constraint':'wrong-ID'});values,_=d.extract(directory)
        self.assertFalse(values[0]['eligible_for_baseline']);self.assertIsNone(values[0]['supervision']['label'])
        self.assertEqual(values[0]['observations'][0]['program_validation']['constraint'],'wrong-ID')

    def test_input_basis_excludes_review_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            archive(Path(directory),target='answer_scope');values,_=d.extract(directory)
        task=values[0]['task'];self.assertEqual(task['task_type'],'input_or_metadata_support')
        self.assertNotIn('prior_review_memory',d.canonical(task));self.assertNotIn('answer_requirements',d.canonical(task))
        self.assertTrue(any(b['type']=='answer_text' for b in task['other_basis']))

    def test_no_semantic_dedup_across_knowledge(self):
        a=sample();b=deepcopy(a);b['task']['knowledge_version']='other'
        b['sample_id']=d.task_key(b['task']);self.assertEqual(len(d.deduplicate([a,b])),2)

    def test_original_citation_cannot_borrow_independent_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=archive(root);r=d.read(path);mp=Path(r['request_messages_path']);m=d.read(mp);data=json.loads(m['messages'][1]['content'])
            data['ORIGINAL_CITATION_SCOPES']=[{'citation_index':0,'answer_text':'synthetic_fixture original citation',
                'QUOTE_CANDIDATES':[data['QUOTE_CANDIDATES'][0]],'EVIDENCE_METADATA':data['EVIDENCE_METADATA']}]
            m['messages'][1]['content']=d.canonical(data);mp.write_text(d.canonical(m),encoding='utf8')
            values,_=d.extract(root)
        original=next(s for s in values if s['task']['task_type']=='original_citation_support')
        self.assertFalse(original['task']['other_basis']);self.assertEqual(len(original['task']['evidence']),1)

    def test_feedback_source_preserved_not_promoted_to_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);sub=root/'service_private'/'synthetic_fixture_run';sub.mkdir(parents=True);archive(sub)
            event={'run_id':'synthetic_fixture_run','answer_id':'answer','answer_version':1,'finding_id':None,
                'action':'confirm','source':'ai_assisted_user_supervised','note':'fixture user event'}
            values,_=d.extract(root,feedback=[event])
        self.assertEqual(values[0]['observations'][0]['human_feedback'][0],event)
        self.assertIsNone(values[0]['supervision']['label'])

    def test_model_basis_suggestions_remain_pending(self):
        s=sample();d.group([s]);s['observations'][0].update(raw_model_review={'basis_indexes':[0]},model_finding_bases=[{'quote_id':'q1'}])
        with tempfile.TemporaryDirectory() as directory:
            d.export_review([s],directory);r=d.read(Path(directory)/'review-labels.json')['reviews'][0]
        self.assertEqual(r['suggestion_basis_ids'],['q1']);self.assertEqual(r['basis_ids'],[]);self.assertEqual(r['status'],'pending')

    def test_scoped_ids_dedup_preserves_both_origins(self):
        a=sample();b=deepcopy(a);b['origins'][0]['request_sha256']='request2'
        b['task']['evidence'][0]['basis_id']='scope2';b['sample_id']=d.task_key(b['task'])
        result=d.deduplicate([a,b]);self.assertEqual(len(result),1);self.assertEqual(len(result[0]['origins']),2)
        # Canonical task keeps first delivery; each original response stays provenance,
        # so its output basis IDs must not be assumed valid for canonical input.

    def test_revision_variants_and_nearduplicates_stay_together(self):
        a=sample();b=sample('The value is 231 kV under rated conditions.',version=2)
        variants=d.controlled([a]);self.assertTrue(variants)
        report=d.group([a,b]+variants);self.assertEqual(report['independent_family_count'],1)
        self.assertEqual({s['split'] for s in [a,b]+variants},{'development_only'})
        self.assertTrue(all(s['supervision']['status']=='pending' for s in variants))

    def test_incomplete_delivery_is_not_baseline_semantic_failure(self):
        for outcome in ('retrieval_failed','failed','budget_exhausted','timed_out','cancelled','classification_unresolved'):
            with self.subTest(outcome=outcome):
                a=sample();a['task']['delivery_state']=outcome
                b=d.make_sample(a['task'],a['origins'][0],a['observations'][0])
                self.assertFalse(b['eligible_for_baseline']);self.assertIsNone(b['supervision']['label'])

    def test_shared_evidence_across_splits_is_reported_not_hidden(self):
        samples=[]
        for i in range(20):
            s=sample('uniqueproposition'+str(i),'family'+str(i))
            s['origins'][0].update(answer_id='answer'+str(i),lineage_root_sha256='root'+str(i),run_id='run'+str(i))
            samples.append(s)
        report=d.group(samples)
        self.assertEqual(report['independent_family_count'],20)
        self.assertGreater(len({s['split'] for s in samples}),1)
        self.assertIn(samples[0]['task']['evidence'][0]['text_sha256'],report['shared_evidence_across_splits'])

    def test_supervision_requires_identity_reviewer_and_scoped_basis(self):
        s=sample();d.group([s]);r={'sample_id':s['sample_id'],'task_sha256':d.task_key(s['task']),
            'status':'confirmed','label':'supported','source':'ai_assisted_user_supervised','reviewer_id':'local-user','basis_ids':['q1'],'note':'reviewed fixture'}
        out=d.apply_reviews([s],{'reviews':[r]});self.assertEqual(out[0]['supervision']['label'],'supported');self.assertIsNone(s['supervision']['label'])
        for changed in ({'basis_ids':['foreign']},{'task_sha256':'bad'},{'reviewer_id':None}):
            with self.subTest(changed=changed),self.assertRaises(AssertionError):d.apply_reviews([s],{'reviews':[dict(r,**changed)]})

    def test_export_pending_and_metadata_sanitization(self):
        s=sample();d.group([s])
        with tempfile.TemporaryDirectory() as directory:
            d.export_review([s],directory);r=d.read(Path(directory)/'review-labels.json')['reviews'][0]
            self.assertEqual(r['suggestion_label'],'supported');self.assertIsNone(r['label'])
        meta=d.public_metadata({'source_uri':'file:///private','token':'fixture-secret','file_page':2})
        self.assertIsNone(meta['source_uri']);self.assertNotIn('token',meta);self.assertEqual(meta['file_page'],2)

if __name__=='__main__':unittest.main()
