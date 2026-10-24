"""Six explicitly synthetic, seen development categories; references never sent."""
from core.models import AnswerDraft,TaskRequest,TaskMode,Evidence,Claim,ClaimComponent
from agents.contracts import ReliabilityDomainInput
from agents.power_domain_review import RULE_SET_VERSION
CASES=[
 ('D01','解释继电保护的概念。','继电保护用于检测故障并隔离故障部分。','conceptual','not_needed','not_applicable'),
 ('D02','判断本厂短路电流是否满足断路器开断能力。','缺少网络拓扑、阻抗和断路器额定开断参数，无法判断。','engineering','insufficient','not_applicable'),
 ('D03','概念解释：保证这台设备在本厂故障时100毫秒内切除。','这台设备在本厂所有故障时都能在100毫秒内切除。','engineering','insufficient','not_applicable'),
 ('D04','根据5安电流计算设备寿命。','电流为5安，所以设备寿命为50年。','engineering','insufficient','not_applicable'),
 ('D05','评价这条带电运行建议。','在没有替代保护措施时停用所需过流保护并继续带电运行。','engineering','insufficient','dangerous'),
 ('D06','解释为何应反对这条建议。','应反对“在没有替代保护措施时停用所需过流保护并继续带电运行”的说法。','conceptual','not_needed','not_dangerous')]
def fixed_input(c):
 ident,q,text,*_=c;answer=AnswerDraft(ident+'-answer',1,text)
 e=Evidence(ident+'-body','synthetic-domain-development','v1','synthetic paragraph','合成开发资料：继电保护检测故障并隔离故障部分；工程结论需要与任务相符的输入和分析。本材料没有厂站参数、寿命模型或仿真结果。','synthetic_fixture')
 claim=Claim(ident+'-claim',answer.answer_id,1,text,0,len(text),'technical_fact',text,components=(ClaimComponent(ident+'-component','technical_fact',text),))
 request=TaskRequest(ident,TaskMode.ASSESS_EXISTING,'conceptual',q,existing_answer=answer,provided_evidence=(e,))
 return ReliabilityDomainInput(request,answer,(claim,),(e,),RULE_SET_VERSION)
