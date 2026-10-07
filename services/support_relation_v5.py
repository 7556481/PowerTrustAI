"""ID-selected source conditions and program-owned effective support status."""
from copy import deepcopy
import json
from services.condition_candidates import catalog
from services.validation_diagnostics import ErrorCollector
from services.support_relation import pure_question

MARKER=' [source-support-relation-v5] '
INSTRUCTIONS='''
Source support relation v5 REQUIRED for supported/contradicted body judgments; also
provide it for a located repair or condition uncertainty. EXACT source_kind,quote_ids,
explanation,whole_claim_supported,missing_clauses,conditions_preserved,authority_scope,
answer_conditions,causal_direction_preserved,repair. source_kind explanatory_body,
data_table,exercise_question,term_mention,mixed,other. authority_scope STRING exactly
explanation,normative_requirement,setting,engineering_guarantee,other.
quote_ids EXACT selected text_excerpt basis IDs for this component/citation ONLY.
Answer conditions EXACT {condition_id,necessity,answer_quote,relationship,reason}.
Select condition_id from SOURCE_CONDITION_CANDIDATES whose quote_id belongs to YOUR
selected basis subset. Program binds exact source text/range/version; NEVER emit
source_condition,source_excerpt,offsets or a copied source quotation. Candidates are
WHOLE quote carriers, NOT mechanically proven necessary conditions: identify their
actual relevant qualifier in reason. No suitable carrier -> explain missing coverage
in missing_clauses; uncertainty remains uncertainty. No fuzzy selection/other scope.
necessity required,not_required,uncertain. relationship preserved,missing,uncertain.
answer_quote must be literal from the evaluated ANSWER body, or "" if absent.
Faithful synonyms are permitted: explain preservation of negation, quantity, units,
necessary/sufficient direction and scope. Reviewer notes/assumptions are NOT body limits.
Evaluate EVERY clause, necessary condition and causal subject/direction. A->B does
not establish B->A. whole_claim_supported,conditions_preserved,causal_direction_preserved
are booleans; missing_clauses list of strings. Preserve actual judgments independently;
program derives effective support, so do not duplicate a classification-derived status.
Source relevance/questions/term mentions alone cannot support or refute a proposition;
tables may support bounded measured values. Unknown corpus origin is allowed for
explanations, not sole authority for settings/normative requirements/engineering guarantees.
repair null or EXACT {replacement,condition_id}: choose an actual selected source
carrier supporting a substantive SAME-question correction. Do not copy source_excerpt.
NULL CONTRACT: use "repair": null when no directly supported replacement is available.
A repair object requires BOTH fields: replacement is a nonempty string; condition_id
is a NON-NULL string identifying a SOURCE_CONDITION_CANDIDATE whose quote_id occurs
in this relation's selected quote_ids. {"replacement":"...","condition_id":null}
is INVALID. Never invent/select an unrelated ID just to complete a repair. Either
select a genuinely supporting carrier from this scope or keep the whole repair null.
Propose a repair for a located qualifier loss or changed causal subject IF the already
selected body justifies the correction. Do not delete requested topics or invent inputs.
This proposal is not verification; all remaining gaps and full re-review remain required.
'''

def body_for(group,item,answer,claims):
    if group=='citation_reviews':
        i=item.get('citation_index')
        if type(i) is int and 0<=i<len(answer.citations):
            c=answer.citations[i];return answer.text[c.start_offset:c.end_offset]
    else:
        c=next((c for c in claims if c.claim_id==item.get('claim_id')),None)
        if c:return answer.text[c.start_offset:c.end_offset]
    return ''

def normalize(value,group,scopes,answer,claims):
    v=deepcopy(value);ec=ErrorCollector('source-support-relation-v5')
    for i,item in enumerate(v.get(group,[]) if isinstance(v,dict) else []):
        if type(item) is not dict:continue
        ci=item.get('citation_index');scope=scopes[0] if group=='findings' else scopes[ci+1] if type(ci) is int and 0<=ci<len(scopes)-1 else None
        candidates=catalog(scope) if scope else {};body=body_for(group,item,answer,claims)
        rows=item.get('component_reviews',[]) if group=='findings' else [item]
        for j,row in enumerate(rows if isinstance(rows,list) else []):
            if type(row) is not dict:continue
            p=f'$.{group}[{i}].support_relation[{j}]';rel=row.pop('support_relation',None)
            ec.check(type(row.get('rationale')) is str and all(m not in row.get('rationale','') for m in (' [source-support-relation-v3] ',' [source-support-relation-v4] ',MARKER)),p,'nonempty_rationale_without_reserved_program_marker_required')
            bases=item.get('bases',[]) if group=='findings' else row.get('bases',[])
            if group=='findings':bases=[bases[k] for k in row.get('basis_indexes',[]) if type(k) is int and type(bases) is list and 0<=k<len(bases)] if type(row.get('basis_indexes')) is list else []
            ids=[b.get('quote_id') for b in bases if type(b) is dict and b.get('type')=='text_excerpt'] if type(bases) is list else []
            raw=row.get('status');definitive=raw in ('supported','contradicted')
            if not ids and group=='findings' and rel is None:continue
            if not definitive and rel is None:continue
            fields={'source_kind','quote_ids','explanation','whole_claim_supported','missing_clauses','conditions_preserved','authority_scope','answer_conditions','causal_direction_preserved','repair'}
            if not ec.fields(rel,fields,set(),p):continue
            ec.check(all(type(q) is str for q in ids) and type(rel['quote_ids']) is list and rel['quote_ids']==list(dict.fromkeys(q for q in ids if type(q) is str)),p,'exact_local_selected_body_basis_ids_required')
            ec.check(rel['source_kind'] in ('explanatory_body','data_table','exercise_question','term_mention','mixed','other'),p,'known_source_kind_required')
            ec.check(rel['authority_scope'] in ('explanation','normative_requirement','setting','engineering_guarantee','other'),p,'known_authority_scope_required')
            ec.check(type(rel['explanation']) is str and bool(rel['explanation'].strip()),p,'explicit_support_explanation_required')
            for key in ('whole_claim_supported','conditions_preserved','causal_direction_preserved'):ec.check(type(rel[key]) is bool,p+'.'+key,'boolean_required')
            ec.check(type(rel['missing_clauses']) is list and all(type(x) is str and x.strip() for x in rel['missing_clauses']),p,'missing_clauses_array_required')
            pairs=rel['answer_conditions'];ec.check(type(pairs) is list,p,'condition_array_required');bindings=[];uncertain=False;lost=False
            for k,pair in enumerate(pairs if type(pairs) is list else []):
                cp=p+f'.answer_conditions[{k}]'
                if not ec.fields(pair,{'condition_id','necessity','answer_quote','relationship','reason'},set(),cp):continue
                cid=pair['condition_id'];valid=type(cid) is str and cid in candidates and candidates[cid]['quote_id'] in ids
                ec.check(valid,cp,'condition_id_must_be_selected_in_this_scope')
                ec.check(pair['necessity'] in ('required','not_required','uncertain') and pair['relationship'] in ('preserved','missing','uncertain'),cp,'condition_semantic_enums_required')
                quote=pair['answer_quote'];ec.check(type(quote) is str and (quote=='' or quote in body),cp,'condition_must_be_in_evaluated_answer_body')
                ec.check(type(pair['reason']) is str and bool(pair['reason'].strip()),cp,'condition_reason_required')
                uncertain |= pair['necessity']=='uncertain' or pair['necessity']=='required' and pair['relationship']=='uncertain'
                lost |= pair['necessity']=='required' and (pair['relationship']=='missing' or quote=='')
                if valid:bindings.append(candidates[cid])
            unsupported=rel['source_kind'] in ('exercise_question','term_mention') or bool(ids) and all(scope and q in scope.by_wire and pure_question(scope.by_wire[q].text) for q in ids if type(q) is str)
            authority_missing=False
            if rel['authority_scope'] in ('normative_requirement','setting','engineering_guarantee') and scope:
                selected={scope.by_wire[q].evidence_id for q in ids if type(q) is str and q in scope.by_wire};meta=[m for m in scope.metadata if m['evidence_id'] in selected]
                authority_missing=bool(meta) and all(m.get('source_type')=='industry_corpus_unverified' for m in meta)
            effective=raw
            if uncertain:effective='not_assessable'
            elif raw in ('supported','contradicted') and unsupported:effective='insufficient_evidence'
            elif raw=='supported' and (lost or authority_missing or not rel['whole_claim_supported'] or rel['missing_clauses'] or not rel['conditions_preserved'] or not rel['causal_direction_preserved']):effective='insufficient_evidence'
            repair=rel['repair'];bound_repair=None
            if repair is not None and ec.fields(repair,{'replacement','condition_id'},set(),p+'.repair'):
                cid=repair['condition_id'];valid=type(cid) is str and cid in candidates and candidates[cid]['quote_id'] in ids
                ec.check(valid,p+'.repair','repair_condition_id_must_be_selected_in_this_scope')
                ec.check(type(repair['replacement']) is str and bool(repair['replacement'].strip()),p+'.repair','substantive_replacement_required')
                if valid and effective in ('insufficient_evidence','contradicted') and not unsupported:
                    c=candidates[cid];bound_repair={**repair,'source_quote_id':c['quote_id'],'source_excerpt':c['text'],'program_binding':c}
            saved={**rel,'raw_model_status':raw,'effective_support_status':effective,'condition_bindings':bindings,'condition_candidates_version':'source-condition-carriers-v1','repair':bound_repair,'raw_repair':repair,'semantic_uncertain':uncertain,'authority_missing':authority_missing}
            if type(row.get('rationale')) is str:row['rationale']+=MARKER+json.dumps(saved,ensure_ascii=False,separators=(',',':'))
    ec.finish();return v

def relation(rationale):
    markers=(MARKER,' [compact-support-assessment-v1] ')
    marker=next((m for m in markers if m in rationale),None)
    if marker is None:return None
    return json.loads(rationale.rsplit(marker,1)[1])
