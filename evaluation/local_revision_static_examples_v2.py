"""Export NEW self-authored synthetic examples only. No historical file or real source input."""
import json
from dataclasses import replace
from backend.config import ROOT
from backend.serialization import wire
from core.models import CitationBinding
from core.validation import ContractError
from services.answer_anchors import anchors
from services.local_revision_v2 import plan,parse
from tests.test_local_revision_v2 import inputs,proposal


def examples():
    mixed=inputs();text='Under C, the permitted setting is 9 kV.\n\nThe relay has two terminals.'
    simple_a=replace(mixed.answer,text=text,citations=(CitationBinding(0,text.index('\n\n'),('limit',)),CitationBinding(text.index('\n\n')+2,len(text),('relay',))))
    aa=anchors(simple_a);start=text.index('9 kV')
    d=replace(mixed.verification.literal_defects[0],anchor_id=aa[0]['anchor_id'],start_offset=start,end_offset=start+4)
    reviews=tuple(replace(r,anchor_id=a['anchor_id'],text=a['text'],start_offset=a['start_offset'],end_offset=a['end_offset']) for r,a in zip(mixed.verification.literal_reviews,aa))
    simple=replace(mixed,answer=simple_a,request=replace(mixed.request,existing_answer=simple_a),verification=replace(mixed.verification,literal_defects=(d,),literal_reviews=reviews))
    result=[]
    for name,inp,dependent in (('single-error',simple,False),('mixed-and-domain',mixed,False),('own-error-and-premise',inputs(True),True)):
        # This exporter cannot publish real archived source or response content.
        assert inp.answer.answer_id=='new-handwritten-fixture'
        assert {e.evidence_id for e in inp.allowed_evidence}=={'limit','relay'}
        assert all(e.source_type=='synthetic_fixture' and e.source_id.startswith('synthetic') for e in inp.allowed_evidence)
        assert all(len(e.text)<100 for e in inp.allowed_evidence)
        p=plan(inp);v=proposal(p,dependent)
        if name=='single-error':
            v['edits'][0]['text']='Under C, the permitted setting is 3 kV.'
            v['edits'][0]['support_refs']=[k for k,s in p.sources.items() if s.evidence_id=='limit']
        out=parse(v,p)
        result.append(dict(id=name,origin='HANDWRITTEN SYNTHETIC NEW OBJECT: not cleaned historical output or real delivery',
            actual_message_input=p.payload,proposed_output=v,
            program_derived=dict(answer=out.answer,edit_links=out.edit_links,preservation=out.preservation,finding_actions=out.finding_actions),
            subsequent_checks=['unchanged Harness/graph re-extraction','full original literal fact review','full original domain review','normal Store readback; IDs and byte preservation do not prove semantics']))
    p=plan(mixed);bad=proposal(p);bad['edits'][0]['authorization_refs']=[next(k for k,o in p.opinions.items() if o['authority_ref'] is None)]
    try:parse(bad,p)
    except ContractError as exc:diagnostic=exc.diagnostic
    else:raise AssertionError('Domain opinion incorrectly authorized an edit')
    result.append(dict(id='domain-opinion-cannot-authorize',origin='HANDWRITTEN SYNTHETIC INVALID COUNTEREXAMPLE',actual_message_input=p.payload,proposed_output=bad,program_derived=dict(applied=False,diagnostic=diagnostic)))
    return wire(result)


if __name__=='__main__':
    path=ROOT/'docs/evaluation/local-revision-offline-redesign-v1/static-examples.json'
    path.write_text(json.dumps(examples(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('3 new synthetic static examples and 1 invalid counterexample; zero project model requests.')
