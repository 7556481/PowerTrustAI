"""Evaluation-only addressedness/claim-target revision; offline, no paid entry point."""
from copy import deepcopy

from evaluation import premise_bound_review_v5 as previous
from evaluation.text_bound_review import canonical
from model_adapter.contracts import ModelMessage
from services.validation_diagnostics import StructuredValidationError

VERSION = 'addressedness-claim-target-eval-v6-dev'
# Schema, ID binding and decomposition stay unchanged. These instructions clarify
# semantic decisions; the parser cannot mechanically certify those decisions.
PROMPT = previous.PROMPT + '''

Addressedness decision order:
1. Find what the answer explicitly says about EACH requested aspect, including
negation, a wrong conclusion or an explicitly wrong relationship/operation.
2. A definite opposite answer still addresses that aspect: use covered when
the requested object, relation and necessary qualifications are explicitly
addressed. Do not downgrade coverage merely because it disagrees with evidence.
3. Use partially_covered only for actual missing required content, scope,
conditions or explanation; identify the missing part in the coverage rationale.
A broader substituted scope does not preserve a required narrower scope. Use
missing when the aspect is absent, uncertain when genuinely unclear. Never
fill in omitted content from the evidence or from your own reasoning.
4. Judge correctness/support separately. Unsupported extras do not erase
addressed requirements. An instruction not to make an assertion is not a demand
to explicitly deny it in every answer.

Determine the assertion's target, not the mere occurrence of technical nouns:
- A general definition, literature rule, or interpretation of supplied text is
literature_statement, even when expressed as ordinary declarative prose. Judge
it against supplied literature and scope_context; no real site observation is
needed to restate a definition. No scenario premise is required for a general
literature statement. Do not invent a real application from a generic statement.
- A stipulated hypothetical restatement is premise_restatement. Applying a
rule to such a case is scenario_application, not verification of an actual site.
- Claims that an actual named device/site currently has a state, measured
value, compliance or safety property are external_claim. Do not turn literature
rules or hypothetical premises into evidence that the actual instance was
inspected. Require relevant actual_record evidence for supported/contradicted
actual-instance claims; without it retain insufficient_evidence/not_assessable.
This preserves site-evidence requirements; it does not waive all verification.
An actual_record must concern the same subject and asserted property; explain
that match. Its record_context identifies a delivered record, not independent
certification that the record is authentic or the installation safe.

Evidence source_role defaults to literature; actual_record is a separate input
role with record_context. Neither the requirement wording, a claim_type label,
nor selecting a basis ID proves semantic support or real-world verification.
Keep label/rationale tensions explicit; do not invent a reason or change an ID
to make the output pass. Return the original exact JSON schema, no new fields.'''


def need(ok,path,rule):
    if not ok:raise StructuredValidationError(VERSION,path,rule)


def basis_catalog(task):
    catalog=previous.basis_catalog(task)
    for i,e in enumerate(task['evidence']):
        path='input.evidence['+str(i)+']'
        role=e.get('source_role','literature')
        need(role in ('literature','actual_record'),path+'.source_role','declared_source_role_required')
        if role=='actual_record':
            context=e.get('record_context')
            need(isinstance(context,dict) and set(context)=={'subject','record_id','locator'},
                 path+'.record_context','traceable_record_context_required')
            for key in ('subject','record_id','locator'):
                need(isinstance(context[key],str) and bool(context[key].strip()),
                     path+'.record_context.'+key,'nonempty_record_identity_required')
            catalog[e['evidence_id']]='actual_record'
    return catalog


def model_input(card,example):
    task=previous.model_input(card,example)
    for source,row in zip(card['evidence'],task['evidence']):
        row['source_role']=source.get('source_role','literature')
        if row['source_role']=='actual_record':
            row['record_context']=deepcopy(source.get('record_context'))
    basis_catalog(task)
    return task


def messages(task):
    basis_catalog(task)
    return (ModelMessage('system',PROMPT),ModelMessage('user',canonical(task)))


def parse(value,task):
    catalog=basis_catalog(task)
    # Delegate all previous shape/IDs/binding and nonempty-rationale checks first.
    # Old projection treats evidence as literature only for syntax validation;
    # typed source-role checks and derived labels below remain v6's authority.
    result=previous.parse(value,task)
    for i,unit in enumerate(result['units']):
        for j,judgment in enumerate(unit['judgments']):
            path='$.units['+str(i)+'].judgments['+str(j)+']'
            roles={catalog[x] for x in judgment['basis_ids']}
            if judgment['support'] in ('supported','contradicted'):
                if judgment['claim_type']=='external_claim':
                    need('actual_record' in roles,path+'.basis_ids','actual_instance_record_required')
                if judgment['claim_type']=='literature_statement':
                    need(roles=={'literature_evidence'},path+'.basis_ids','literature_statement_needs_literature')
                if judgment['claim_type']=='scenario_application':
                    need(roles=={'hypothetical_premise','literature_evidence'},
                         path+'.basis_ids','hypothetical_application_needs_premise_and_rule')
            judgment['program_basis_bindings']=[{'basis_id':ident,'basis_kind':catalog[ident]}
                                                for ident in judgment['basis_ids']]
            if judgment['claim_type']=='external_claim':
                judgment['program_support_scope']=('delivered_actual_record_not_independent_site_certification'
                    if 'actual_record' in roles else 'actual_instance_not_verified_by_delivered_records')
    return result
