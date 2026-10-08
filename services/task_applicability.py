"""Versioned task applicability; model semantic assessment, program-bound identity."""
import json,hashlib
from dataclasses import replace
from core.validation import require
MARKER=' [task-applicability-v1] '
INSTRUCTION='''\nFor the analysis_scope check ONLY add task_scope: conceptual, engineering, or uncertain.
Judge the actual user question AND the current asserted answer, not merely topic words.
conceptual means only explanation/description without a requested specific device rating,
setting, operation, plant outcome or asserted engineering guarantee. engineering includes
such concrete requests even if the answer only asks for missing inputs. User goal=conceptual
cannot exempt actual engineering assertions. Absence of structured goal is NOT evidence
of either conceptual or engineering. If scope is unclear, task_scope=uncertain and explain.
The existing analysis_scope rationale explains the requested scope, actual answer scope and
any disagreement; do not change technical-truth duties or hide missing evidence.
Other check objects keep their original fields. This is a model scope judgment, not proof.
'''
def read(findings):
 for f in findings:
  if f.category=='analysis_scope' and MARKER in f.rationale:return json.loads(f.rationale.rsplit(MARKER,1)[1])
 return None
def effective(context,assessment):
 if context is not None and context.goal=='plant_assessment':return 'engineering'
 return assessment['scope'] if assessment else None

def bind(inputs,output,scope):
 f=next(f for f in output.findings if f.category=='analysis_scope')
 require(MARKER not in f.rationale,'Reserved task scope marker')
 # A model's own unresolved scope/operational finding cannot certify conceptuality.
 if scope=='conceptual' and any(x.category in ('analysis_scope','operating_prerequisites') and x.check_status in ('warning','not_assessable') for x in output.findings):scope='uncertain'
 from services.bounded_repair import GAP_MARKER
 assessment={'version':'task-applicability-v1','scope':scope,'reason':f.rationale.split(GAP_MARKER,1)[0],
  'answer_id':inputs.answer.answer_id,'answer_version':inputs.answer.version,
  'answer_sha256':hashlib.sha256(inputs.answer.text.encode()).hexdigest(),
  'question_sha256':hashlib.sha256(inputs.request.question.encode()).hexdigest(),
  'structured_goal':inputs.request.engineering_context.goal if inputs.request.engineering_context else None}
 findings=tuple(replace(x,rationale=x.rationale+MARKER+json.dumps(assessment,ensure_ascii=False)) if x.category=='analysis_scope' else x for x in output.findings if x.origin!='program_rule')
 from agents.power_domain_review import program_findings
 program,checks=program_findings(inputs,output.quote_candidates,assessment=assessment)
 return replace(output,findings=program+findings,consistency_checks=checks)
