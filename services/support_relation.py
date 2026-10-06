"""V1 reviewable source-to-claim warrant; never a program proof of truth."""
from copy import deepcopy
import json
import re
from services.validation_diagnostics import ErrorCollector

VERSION='source-support-relation-v1'
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

def normalize(value,group,scopes):
    v=deepcopy(value);ec=ErrorCollector(VERSION)
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
            if not ec.fields(relation,{'source_kind','quote_ids','explanation'},set(),p):continue
            ec.check(type(row.get('rationale')) is str and bool(row['rationale'].strip()),path+'.rationale','original_nonempty_rationale_required')
            kind=relation['source_kind'];ec.check(kind in ('explanatory_body','data_table','exercise_question','term_mention','mixed','other'),p+'.source_kind','known_source_kind_required')
            ec.check(type(relation['quote_ids']) is list and relation['quote_ids']==list(dict.fromkeys(ids)),p+'.quote_ids','exact_local_selected_body_basis_ids_required')
            ec.check(type(relation['explanation']) is str and bool(relation['explanation'].strip()),p+'.explanation','explicit_source_assertion_to_qualified_claim_reason_required')
            if definitive:
                ec.check(kind not in ('exercise_question','term_mention'),p,'questions_or_term_mentions_do_not_establish_or_refute_claim')
                candidates=[scope.by_wire[q].text for q in ids if scope is not None and isinstance(q,str) and q in scope.by_wire]
                ec.check(not candidates or not all(pure_question(t) for t in candidates),p,'selected_only_unanswered_question_is_not_support')
            if type(row.get('rationale')) is str:
                row['rationale']=row['rationale']+' ['+VERSION+'] '+json.dumps(relation,ensure_ascii=False,separators=(',',':'))
    ec.finish();return v
