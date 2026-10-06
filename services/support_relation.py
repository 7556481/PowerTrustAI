"""V1 reviewable source-to-claim warrant; never a program proof of truth."""
from copy import deepcopy
import json
import re
from services.validation_diagnostics import ErrorCollector

VERSION='source-support-relation-v1'
V2_INSTRUCTIONS='''
Source support relation v2: ALSO include whole_claim_supported (boolean),
missing_clauses (list of strings), conditions_preserved (boolean),
authority_scope (explanation,normative_requirement,setting,engineering_guarantee,other)
in support_relation. Classify the ACTUAL proposition, not the topic or source's tone.
Evaluate EVERY proposition, causal link, quantifier and necessary condition in the
complete citation/component, not only its true subset. A supported result requires
whole_claim_supported=true, missing_clauses=[], conditions_preserved=true.
Explain separately the source's asserted premises, its causal link/conclusion, and
the claim's scope. If only one clause is established, use insufficient_evidence,
list the unsupported clauses and retain the supported subset in explanation.
Do not generalize some inductive devices to all loads or equate local component
reactive exchange with a whole-grid voltage-maintenance explanation. Ideal,
sinusoidal steady-state, fixed voltage and appropriate compensation conditions
cannot disappear: lossless ideal elements do not establish zero losses in actual
equipment, nor unchanged branch current when supply voltage changes.
Industry corpus original_source_unverified is permitted for explanatory coverage,
not sole authority for normative requirements, settings or engineering guarantees.
Unknown original publisher/URL/date remain unknown; dataset host is not the author.
These coverage flags are model judgments, not a deterministic semantic proof.
'''
V3_INSTRUCTIONS="""
STRICT TYPES: authority_scope MUST be a STRING exactly one of "explanation",
"normative_requirement", "setting", "engineering_guarantee", "other".
NEVER return an object of all scope categories; "explanatory_body" is source_kind,
NOT an authority_scope value. Use null for absent repair, never {} or a boolean.
Source support relation v3 adds EXACT fields answer_conditions, causal_direction_preserved,
repair. answer_conditions is a list of EXACT {source_quote_id,source_condition,answer_quote}.
List EVERY necessary source condition for the evaluated proposition; source_condition
must be literal text within the selected quote and answer_quote a literal substring
of THIS evaluated answer body, explicitly retaining the condition. Use the SHORTEST literal NECESSARY QUALIFIER,
not a whole definition/claim as source_condition. Its literal words must also occur
inside answer_quote (whitespace/punctuation differences allowed); do not match a
condition to a ratio, conclusion, disclaimer or only the supported part of a claim.
If answer paraphrases a condition beyond this literal check, do not certify supported;
report the unresolved literal qualification and, if possible, a source-bound repair.
An assumption,
missing_information, reviewer applicability_conditions, or your explanation is NOT
answer-body qualification. Do not use an unrelated boilerplate sentence as a condition.
For unsupported conditions return answer_quote="" and conditions_preserved=false.
causal_direction_preserved is boolean: same causal subject, direction and conditions,
not an inverse, converse or common-topic association. A->B does not prove B->A;
incorrect use of a remedy causing harm does not prove the original deficiency causes harm.
SUPPORTED requires actual conditions and causal direction, not your added explanation.
repair is null unless an insufficient/contradicted statement is LOCATED and a substantive
replacement answering the SAME user subquestion is already justified by selected body.
Then return EXACT {replacement,source_quote_id,source_excerpt}; source_excerpt must be
literal within that selected quote. This is a repair proposal, not truth certification.
Do not propose deletion, disclaimer-only repair, invented data or missing engineering study.
An unanswerable requested subquestion must remain missing, not disappear from the answer.
For insufficient results include support_relation when a bounded repair is available,
with missing_clauses/conditions and the repair above; do not invent a repair for empty bases.
Evaluate the repair opportunity for every located missing qualifier/changed causal subject:
if the source provides a correct SAME-question replacement, select that literal quote,
include its basis and proposal; do not merely omit repair without checking it.
Synthetic shape example (substitute actual selected IDs and exact strings):
{"source_kind":"explanatory_body","quote_ids":["actual-quote-id"],
"explanation":"The source asserts A causes B only under condition C.",
"whole_claim_supported":false,"missing_clauses":["Condition C omitted"],
"conditions_preserved":false,"authority_scope":"explanation",
"answer_conditions":[{"source_quote_id":"actual-quote-id","source_condition":"under C","answer_quote":""}],
"causal_direction_preserved":true,
"repair":{"replacement":"Under C, A causes B.","source_quote_id":"actual-quote-id","source_excerpt":"Under C, A causes B."}}
For a definitive claim with no necessary condition, answer_conditions=[] is legal.
This is type/shape guidance only, NEVER use synthetic example words as actual evidence.
"""

def instructions(version=1):
    if version==1:return INSTRUCTIONS
    if version==4:
        old=instructions(3).replace('Source support relation v3','Source support relation v4').replace('EXACT {source_quote_id,source_condition,answer_quote}','EXACT {source_quote_id,source_condition,answer_quote,relationship,reason}')
        start=old.index('Its literal words must also occur');end=old.index('An assumption,',start)
        old=old[:start]+'''Faithful paraphrases are permitted; do not require copying source words.
relationship is exactly preserved, missing or uncertain; reason explains semantic
equivalence of the ACTUAL body quote and source condition (not shared topic alone).
Preserve negation, quantifiers, necessary/sufficient direction, causal subject,
units and scope. If uncertain, cannot certify supported. source_condition remains
an EXACT source excerpt; answer_quote remains an EXACT answer excerpt. Never use
reviewer explanation as body qualification.\n'''+old[end:]
        return old.replace('"answer_quote":""}', '"answer_quote":"","relationship":"missing","reason":"Condition absent from answer"}')
    if version==3:return instructions(2).replace('source_kind,quote_ids,explanation,whole_claim_supported,missing_clauses,conditions_preserved,authority_scope}', 'source_kind,quote_ids,explanation,whole_claim_supported,missing_clauses,conditions_preserved,authority_scope,answer_conditions,causal_direction_preserved,repair}')+V3_INSTRUCTIONS
    return INSTRUCTIONS.replace('{source_kind,quote_ids,explanation}',
        '{source_kind,quote_ids,explanation,whole_claim_supported,missing_clauses,conditions_preserved,authority_scope}')+V2_INSTRUCTIONS
INSTRUCTIONS='''
Source support relation v1: topic relevance is not support. For each supported or
contradicted body-based component, ALSO return support_relation EXACT
{source_kind,quote_ids,explanation}; every definitive original citation item also requires it.
source_kind explanatory_body,data_table,exercise_question,term_mention,mixed,other.
quote_ids must be EXACTLY the selected text_excerpt IDs for THIS component/item only.
explanation must identify what the selected original text actually asserts or measures
and how that establishes/refutes the WHOLE qualified claim; explain any bounded inference.
An exercise asking 'how does X relate to Y?' DOES NOT state the relationship or causal mechanism.
Table headings merely listing X and Y do not explain causation. Questions, topic mentions,
reading lists, keywords and assignments alone cannot be supported or contradicted: use
insufficient_evidence (or not_assessable for genuinely ambiguous meaning). Never infer answers
from the fact a question was posed, even in an authoritative textbook. Distinguish an answered
exercise's actual derivation from its unanswered question. Don't invent missing explanation.
Data tables CAN support their actual measured/defined values, with units, conditions and
limits; never reject all tables. For mixed fragments point to the actual explanatory statement
or measured data in your explanation; unrelated declarative sentences don't establish causality.
Partial keyword overlap or a true subset cannot support a whole citation. Keep independent
truth review and original reference review separate; no borrowing from another scope.
This relation is a MODEL judgment, not automatic proof. Do not add support_relation to
non-definitive results unless useful; [] bases remain legal for insufficient evidence.
'''

def pure_question(text):
    # A conservative literal signal only: mixed prose/tables are not classified here.
    text=re.sub(r'^\s*(?:思考题|练习题|Question)\s*[:：]?\s*','',text.strip(),flags=re.I)
    return bool(re.fullmatch(r'[^\n|。.!！?？]+[?？]',text))

def normalize(value,group,scopes,version=1,answer=None,claims=()):
    v=deepcopy(value);ec=ErrorCollector('source-support-relation-v'+str(version))
    for n,item in enumerate(v.get(group,[]) if isinstance(v,dict) else []):
        if not isinstance(item,dict):continue
        rows=item.get('component_reviews',[]) if group=='findings' else [item]
        scope=scopes[0] if group=='findings' else scopes[item.get('citation_index',-1)+1] if type(item.get('citation_index')) is int and 0<=item['citation_index']<len(scopes)-1 else None
        for j,row in enumerate(rows if isinstance(rows,list) else []):
            if not isinstance(row,dict):continue
            path=f'$.{group}[{n}]'+(f'.component_reviews[{j}]' if group=='findings' else '')
            bases=item.get('bases',[]) if group=='findings' else row.get('bases',[])
            if group=='findings':bases=[bases[k] for k in row.get('basis_indexes',[]) if type(k) is int and isinstance(bases,list) and 0<=k<len(bases)] if isinstance(row.get('basis_indexes'),list) else []
            ids=[b.get('quote_id') for b in bases if isinstance(b,dict) and b.get('type')=='text_excerpt'] if isinstance(bases,list) else []
            definitive=row.get('status') in ('supported','contradicted')
            relation=row.pop('support_relation',None)
            if not ids and group=='findings' and relation is None:continue
            if not definitive and relation is None:continue
            p=path+'.support_relation'
            required={'source_kind','quote_ids','explanation'}
            if version>=2:required|={'whole_claim_supported','missing_clauses','conditions_preserved','authority_scope'}
            if version>=3:required|={'answer_conditions','causal_direction_preserved','repair'}
            if not ec.fields(relation,required,set(),p):continue
            if version>=2:
                ec.check(type(relation['whole_claim_supported']) is bool,p+'.whole_claim_supported','boolean_required')
                ec.check(type(relation['conditions_preserved']) is bool,p+'.conditions_preserved','boolean_required')
                authority=relation['authority_scope']
                ec.check(authority in ('explanation','normative_requirement','setting','engineering_guarantee','other'),p+'.authority_scope','known_authority_scope_required')
                missing=relation['missing_clauses']
                ec.check(type(missing) is list and all(type(x) is str and x.strip() for x in missing),p+'.missing_clauses','string_array_required')
                if row.get('status')=='supported':
                    ec.check(relation['whole_claim_supported'] is True and missing==[] and relation['conditions_preserved'] is True,p,'partial_or_condition_lost_claim_cannot_be_supported')
                    if authority in ('normative_requirement','setting','engineering_guarantee') and scope is not None:
                        selected={getattr(scope.by_wire[q],'evidence_id',None) for q in ids if isinstance(q,str) and q in scope.by_wire}
                        metadata=[m for m in getattr(scope,'metadata',[]) if m.get('evidence_id') in selected]
                        ec.check(not metadata or not all(m.get('source_type')=='industry_corpus_unverified' for m in metadata),p,'unverified_corpus_not_sole_normative_or_engineering_authority')
            if version>=3:
                body=''
                if answer is not None:
                    if group=='citation_reviews':
                        ci=item.get('citation_index')
                        if type(ci) is int and 0<=ci<len(answer.citations):
                            cit=answer.citations[ci];body=answer.text[cit.start_offset:cit.end_offset]
                    else:
                        claim=next((c for c in claims if c.claim_id==item.get('claim_id')),None)
                        if claim is not None:body=answer.text[claim.start_offset:claim.end_offset]
                pairs=relation['answer_conditions'];ec.check(type(pairs) is list,p+'.answer_conditions','condition_pairs_required')
                ec.check(type(relation['causal_direction_preserved']) is bool,p,'causal_boolean_required')
                for ci,pair in enumerate(pairs if isinstance(pairs,list) else []):
                    cp=p+'.answer_conditions['+str(ci)+']'
                    pair_fields={'source_quote_id','source_condition','answer_quote'}
                    if version==4:pair_fields|={'relationship','reason'}
                    if not ec.fields(pair,pair_fields,set(),cp):continue
                    q=pair['source_quote_id'];src=pair['source_condition'];dst=pair['answer_quote']
                    ec.check(type(q) is str and q in ids and scope is not None and q in scope.by_wire,cp,'bound_source_condition_required')
                    ec.check(type(src) is str and bool(src.strip()) and scope is not None and type(q) is str and q in scope.by_wire and src in scope.by_wire[q].text,cp,'literal_source_condition_required')
                    ec.check(type(dst) is str and (dst=='' or dst in body),cp,'condition_must_be_in_evaluated_answer_body')
                    if row.get('status')=='supported':
                        ec.check(type(dst) is str and bool(dst.strip()),cp,'supported_answer_condition_missing')
                        if version==3:
                            literal=lambda x:re.sub(r'[\W_]+','',x).casefold()
                            ec.check(type(src) is str and type(dst) is str and bool(literal(src)) and literal(src) in literal(dst),cp,'source_qualifier_words_must_be_in_answer_condition')
                        else:ec.check(pair['relationship']=='preserved',cp,'uncertain_or_missing_condition_cannot_be_supported')
                    if version==4:
                        ec.check(pair['relationship'] in ('preserved','missing','uncertain'),cp,'known_condition_relationship_required')
                        ec.check(type(pair['reason']) is str and bool(pair['reason'].strip()),cp,'condition_equivalence_reason_required')
                if row.get('status')=='supported':ec.check(relation['causal_direction_preserved'] is True,p,'causal_subject_or_direction_changed')
                repair=relation['repair']
                if repair is not None and ec.fields(repair,{'replacement','source_quote_id','source_excerpt'},set(),p+'.repair'):
                    q=repair['source_quote_id'];excerpt=repair['source_excerpt']
                    ec.check(row.get('status') in ('insufficient_evidence','contradicted'),p,'repair_only_adverse_judgment')
                    ec.check(type(repair['replacement']) is str and bool(repair['replacement'].strip()),p,'substantive_replacement_required')
                    ec.check(type(q) is str and q in ids and scope is not None and q in scope.by_wire,p,'repair_selected_body_required')
                    ec.check(type(excerpt) is str and bool(excerpt.strip()) and scope is not None and type(q) is str and q in scope.by_wire and excerpt in scope.by_wire[q].text,p,'literal_repair_basis_required')
            ec.check(type(row.get('rationale')) is str and bool(row['rationale'].strip()),path+'.rationale','original_nonempty_rationale_required')
            kind=relation['source_kind'];ec.check(kind in ('explanatory_body','data_table','exercise_question','term_mention','mixed','other'),p+'.source_kind','known_source_kind_required')
            ec.check(type(relation['quote_ids']) is list and relation['quote_ids']==list(dict.fromkeys(ids)),p+'.quote_ids','exact_local_selected_body_basis_ids_required')
            ec.check(type(relation['explanation']) is str and bool(relation['explanation'].strip()),p+'.explanation','explicit_source_assertion_to_qualified_claim_reason_required')
            if definitive:
                ec.check(kind not in ('exercise_question','term_mention'),p,'questions_or_term_mentions_do_not_establish_or_refute_claim')
                candidates=[scope.by_wire[q].text for q in ids if scope is not None and isinstance(q,str) and q in scope.by_wire]
                ec.check(not candidates or not all(pure_question(t) for t in candidates),p,'selected_only_unanswered_question_is_not_support')
            if type(row.get('rationale')) is str:
                row['rationale']=row['rationale']+' ['+('source-support-relation-v'+str(version) if version>=2 else VERSION)+'] '+json.dumps(relation,ensure_ascii=False,separators=(',',':'))
    ec.finish();return v
