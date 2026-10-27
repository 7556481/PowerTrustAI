"""Isolated persisted marking examples; no real adapters, .env or user records."""
import argparse
from dataclasses import replace
import tempfile
from uuid import uuid4

from agents.contracts import EvidenceVerificationOutput
from agents.fakes import FakeConfig, fake_evidence
from core.models import (AnswerDraft, AnswerSpan, CitationBinding, CitationAssessment, Claim,
    ClaimExtractionOutput, TaskMode, TaskRequest, VerificationFinding, VerificationStatus, Severity)
from tools.ui_fixture import SyntheticUIFactory, fixture_app, terminal

TARGET='本段为P-V母线的合成说明，具体适用条件仍需资料核实。'
TEXT='合成材料，仅供交互验收。\r\n😀 '+TARGET+'\r\n这句话没有定位意见；未标注不代表核实正确。'


class LiteralExtractor:
    def __init__(self,legacy=False):self.legacy=legacy
    async def extract(self, answer):
        start=answer.text.index(TARGET)
        c=Claim(answer.answer_id+'-v'+str(answer.version)+'-c',answer.answer_id,answer.version,TARGET,start,start+len(TARGET),'technical')
        if self.legacy:return (c,)
        spans=tuple(AnswerSpan(answer.text[a:b],a,b,'合成界面说明文字，不作为技术主张') for a,b in ((0,start),(start+len(TARGET),len(answer.text))) if a<b)
        return ClaimExtractionOutput(answer.answer_id,answer.version,(c,),spans,())


class TwoOpinionVerifier:
    def __init__(self,status):self.status=status
    async def run(self,inputs):
        claim=inputs.claims[0]
        reason='已存合成事实意见：当前资料不足以支持这句话的适用条件。' if self.status==VerificationStatus.INSUFFICIENT_EVIDENCE else '已存合成冲突意见：审核判断该句与所用依据冲突；仅作交互样本。'
        finding=VerificationFinding('synthetic-fact-'+str(inputs.answer.version),claim.claim_id,self.status,('offline-e1',),reason,'synthetic-inline-v7')
        citations=tuple(CitationAssessment(i,self.status,('offline-e1',),(),
            '已存合成引用意见：引用资料没有提供该句所需的限定。',(),'synthetic-inline-v7') for i,_ in enumerate(inputs.answer.citations))
        return EvidenceVerificationOutput(inputs.answer.answer_id,inputs.answer.version,inputs.claims,(finding,),(fake_evidence(),),citation_reviews=citations)


class InlineFactory(SyntheticUIFactory):
    case=None
    def create(self,rid,observer):
        bundle=super().create(rid,observer)
        if self.case:
            bundle.harness.extractor=LiteralExtractor(legacy=self.case=='冲突与版本')
            bundle.harness.verification=TwoOpinionVerifier(VerificationStatus.CONTRADICTED if self.case=='冲突与版本' else VerificationStatus.INSUFFICIENT_EVIDENCE)
            if self.case=='未定位前提':
                original=bundle.harness.domain_review
                class TaskDomain:
                    async def run(self,inputs):
                        out=await original.run(inputs)
                        return replace(out,findings=(replace(out.findings[0],claim_ids=(),severity=Severity.LOW,missing_prerequisites=('合成工况资料',),rationale='已存合成任务意见：缺少工况资料，没有可绑定的正文句子。'),))
                bundle.harness.domain_review=TaskDomain()
        return bundle


async def seed_inline(service,factory):
    cases={}
    for name in ('同句双意见','冲突与版本','未定位前提'):
        factory.case=name;factory.fake_config=FakeConfig()
        tid=uuid4().hex;start=TEXT.index(TARGET)
        request=TaskRequest(tid,TaskMode.ASSESS_EXISTING,'voltage_stability_reactive_support','synthetic_fixture · 正文标注 · '+name,
            existing_answer=AnswerDraft(tid+'-answer',1,TEXT,citations=(CitationBinding(start,start+len(TARGET),('offline-e1',)),)),provided_evidence=(fake_evidence(),))
        rid=await service.submit(request);await terminal(service,rid);cases['正文标注 · '+name]=rid
        result=service.result(rid)
        if name=='同句双意见':
            p=result['presentation']['inline_review']
            assert p['located_region_count']==1 and len(p['opinions'])==2,(p,result['execution'])
            assert result['answer']['final']['text']==TEXT
    factory.case=None
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8766);args=parser.parse_args()
    if not 1024<=args.port<=65535 or args.port in (8765,8770):parser.error('Use an isolated nonproduction port')
    import uvicorn
    with tempfile.TemporaryDirectory(prefix='powertrust-inline-v7-') as directory:
        app=fixture_app(directory,factory_type=InlineFactory,seed_extra=seed_inline)
        print(f'Inline synthetic preview: http://127.0.0.1:{args.port}/fixture/connect ; model calls=0',flush=True)
        uvicorn.run(app,host='127.0.0.1',port=args.port,workers=1,access_log=False,log_level='warning')


if __name__=='__main__':main()
