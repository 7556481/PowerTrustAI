"""Persisted-identity projection, exact offsets and non-mutating compatibility."""
from copy import deepcopy
import unittest
from backend.answer_annotations import project, locate
from backend.presentation import explain
from pathlib import Path
import shutil
import subprocess


def sample(text='😀前缀\r\n同一句意见。\n另一句。'):
    original='同一句意见。';start=text.find(original)
    a=dict(answer_id='a',version=2,text=text,citations=[dict(start_offset=start,end_offset=start+len(original),evidence_ids=['e'])])
    c=dict(answer_id='a',answer_version=2,claim_id='c',text=original,start_offset=start,end_offset=start+len(original),proposition='改述不能用于定位')
    return dict(execution=dict(status='finished',required_stages_complete=True),answer=dict(final=a,versions=[a]),
                snapshots=dict(extraction=dict(answer_id='a',answer_version=2,claims=[c])),
                review_bindings=dict(verification=dict(answer_id='a',answer_version=2)),
                findings=dict(model_fact=[dict(finding_id='f',claim_id='c',status='insufficient_evidence',rationale='事实意见理由',evidence_ids=['e'])],
                              original_citations=[dict(citation_index=0,status='insufficient_evidence',rationale='引用意见理由',evidence_ids=['e'])]),
                decision=dict(kind='needs_information'),evidence=[])


class InlineProjectionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Optional Node runtime unavailable')
    def test_actual_main_client_marking_copy_and_keyboard(self):
        r=subprocess.run(['node','tests/ui_inline_review_probe.js'],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_same_span_preserves_two_reasons_one_region_and_raw_data(self):
        r=sample();before=deepcopy(r);p=explain(r)['inline_review']
        self.assertEqual(r,before);self.assertEqual(p['located_region_count'],1)
        self.assertEqual([o['reason'] for o in p['opinions']],['事实意见理由','引用意见理由'])
        self.assertEqual([o['origin'] for o in p['opinions']],['fact','citation'])
        for o in p['opinions']:
            self.assertEqual(r['answer']['final']['text'][o['start']:o['end']],o['original_text'])
            self.assertEqual(o['answer_version'],2)

    def test_unique_literal_fallback_never_first_duplicate_or_proposition(self):
        r=sample();c=r['snapshots']['extraction']['claims'][0];c.pop('start_offset');c.pop('end_offset')
        self.assertEqual(project(r)['opinions'][0]['location_method'],'unique_literal')
        for text in ('同一句意见。同一句意见。','只有改述'):
            r['answer']['final']['text']=text
            self.assertFalse(project(r)['opinions'][0]['located'])
        c.pop('text');self.assertFalse(project(r)['opinions'][0]['located'])

    def test_invalid_offsets_have_no_search_fallback(self):
        for start,end in ((-1,2),(True,5),(999,1000),(0,6),(7,None)):
            r=sample();c=r['snapshots']['extraction']['claims'][0];c.update(start_offset=start,end_offset=end)
            self.assertFalse(project(r)['opinions'][0]['located'])

    def test_missing_mismatched_claim_extraction_review_and_citation_identity(self):
        for target,field,value in [('claim','answer_id','wrong'),('claim','answer_version',1),('claim','answer_id',None),('extraction','answer_version',1),('review','answer_version',1)]:
            r=sample();obj={'claim':r['snapshots']['extraction']['claims'][0],'extraction':r['snapshots']['extraction'],'review':r['review_bindings']['verification']}[target];obj[field]=value
            self.assertFalse(project(r)['opinions'][0]['located'])
        r=sample();r['review_bindings']={};self.assertFalse(project(r)['opinions'][1]['located'])
        r=sample();r['findings']['original_citations'][0]['answer_version']=1
        self.assertFalse(project(r)['opinions'][1]['located'])

    def test_old_full_round_can_supply_exact_verification_identity(self):
        r=sample();r['review_bindings']={};r['review_rounds']=[dict(answer=deepcopy(r['answer']['final']),verification=dict(answer_id='a',answer_version=2))]
        self.assertTrue(project(r)['opinions'][1]['located'])
        r['review_rounds'][0]['answer']['text']='different';self.assertFalse(project(r)['opinions'][1]['located'])

    def test_overlapping_regions_merge_adjacent_regions_do_not_expand(self):
        r=sample('同一句意见。另一句。');a=r['answer']['final'];cs=r['snapshots']['extraction']['claims']
        cs.extend([dict(cs[0],claim_id='overlap',text=a['text'][3:8],start_offset=3,end_offset=8),dict(cs[0],claim_id='adjacent',text=a['text'][8:],start_offset=8,end_offset=len(a['text']))])
        r['findings']['model_fact'].extend([dict(finding_id='g',claim_id=c,status='contradicted',rationale='冲突') for c in ('overlap','adjacent')])
        p=project(r);self.assertEqual([(x['start'],x['end']) for x in p['regions']],[(0,8),(8,len(a['text']))])

    def test_running_interrupted_no_answer_and_unanchored_task_opinions(self):
        for status,complete,noanswer in [('running',False,False),('interrupted',False,False),('failed',False,False),('finished',True,True)]:
            r=sample();r['execution'].update(status=status,required_stages_complete=complete);r['no_substantive_answer']=noanswer
            p=project(r);self.assertFalse(p['ready']);self.assertEqual(p['regions'],[])
        r=sample();r['findings']['domain']=[dict(finding_id='task',answer_id='a',answer_version=2,missing_prerequisites=['工况'],rationale='工程前提缺失')]
        self.assertEqual(project(r)['unlocated_count'],1)
        self.assertEqual(project(r)['opinions'][-1]['reason'],'工程前提缺失')

    def test_unicode_crlf_literal_html_and_empty_answer_are_unchanged(self):
        for text in ['😀同一句意见。\r\n<图>','𠮷\n同一句意见。<script>bad()</script>']:
            r=sample(text);before=deepcopy(r);p=project(r)
            self.assertEqual(p['opinions'][0]['start'],text.index('同一句意见。'));self.assertEqual(r,before)
        r=sample();r['answer']['final']['text']='';self.assertEqual(project(r)['located_region_count'],0)

    def test_projection_does_not_relabel_insufficient_evidence_as_error(self):
        p=project(sample());self.assertEqual({o['status'] for o in p['opinions']},{'insufficient_evidence'})


class InlineAPITests(unittest.TestCase):
    def test_actual_saved_result_read_adds_binding_without_mutation_or_reexecution(self):
        from tests.test_local_api import APITests
        from agents.fakes import FakeConfig
        from core.models import VerificationStatus
        fixture=APITests();fixture.setUp()
        try:
            fixture.factory.fake_config=FakeConfig(verification_statuses=(VerificationStatus.INSUFFICIENT_EVIDENCE,))
            rid=fixture.run_task()
            store=fixture.client.app.state.service.store
            before=fixture.client.portal.call(lambda:store.get(rid))
            created=len(fixture.factory.created)
            for _ in range(2):
                response=fixture.client.get('/runs/'+rid+'/result',headers=fixture.headers)
                self.assertEqual(response.status_code,200);r=response.json();p=r['presentation']['inline_review']
                self.assertEqual(p['located_region_count'],1)
                self.assertEqual(p['answer_id'],r['answer']['final']['answer_id'])
                self.assertEqual(p['answer_version'],r['answer']['final']['version'])
                self.assertEqual(r['review_bindings']['verification']['answer_id'],p['answer_id'])
            self.assertEqual(before,fixture.client.portal.call(lambda:store.get(rid)))
            self.assertEqual(created,len(fixture.factory.created))
            self.assertEqual(fixture.client.get('/runs/'+rid+'/result').status_code,401)
            self.assertEqual(fixture.client.get('/ui/inline_review.js').status_code,200)
        finally:fixture.tearDown()

