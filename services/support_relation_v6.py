"""V6 selects body once through bases/indexes; no model duplicate quote list."""
from copy import deepcopy
import json
from services.support_relation_v5 import INSTRUCTIONS as OLD,normalize as normalize_v5,MARKER as OLD_MARKER
from services.validation_diagnostics import ErrorCollector
MARKER=' [source-support-relation-v6] '
INSTRUCTIONS=OLD.replace('relation v5','relation v6').replace('EXACT source_kind,quote_ids,','EXACT source_kind,').replace('quote_ids EXACT selected text_excerpt basis IDs for this component/citation ONLY.','quote_ids is PROGRAM-OWNED. DO NOT output that field. Select body once using bases plus component basis_indexes (citation bases directly). Conditions/repair must refer only to carriers of these selected body bases.').replace("this relation's selected quote_ids",'THIS component/citation selected text_excerpt bases')
INSTRUCTIONS+='\nDo not repeat a selected quote list in support_relation. The program binds it strictly from this component basis_indexes; it does not repair illegal IDs or infer support. Exact quote IDs in bases and condition IDs remain scope-bound.\n'
def normalize(value,group,scopes,answer,claims):
 v=deepcopy(value);ec=ErrorCollector('source-support-relation-v6')
 for i,item in enumerate(v.get(group,[]) if isinstance(v,dict) else []):
  if not isinstance(item,dict):continue
  ci=item.get('citation_index');scope=scopes[0] if group=='findings' else scopes[ci+1] if type(ci) is int and 0<=ci<len(scopes)-1 else None
  rows=item.get('component_reviews',[]) if group=='findings' else [item]
  for j,row in enumerate(rows if isinstance(rows,list) else []):
   if not isinstance(row,dict):continue
   rel=row.get('support_relation');p=f'$.{group}[{i}].component[{j}]'
   ec.check(MARKER not in row.get('rationale','') if isinstance(row.get('rationale'),str) else False,p,'reserved_program_marker_not_model_output')
   if rel is None:continue
   if not ec.check(type(rel) is dict,p,'relation_object_required'):continue
   ec.check('quote_ids' not in rel,p,'duplicate_quote_ids_not_in_v6_model_contract')
   bases=item.get('bases',[]) if group=='findings' else row.get('bases',[])
   if not ec.check(type(bases) is list,p,'bases_array_required'):continue
   if group=='findings':
    ix=row.get('basis_indexes')
    if not ec.check(type(ix) is list and all(type(x) is int and 0<=x<len(bases) for x in ix),p,'exact_local_basis_indexes_required'):continue
    bases=[bases[x] for x in ix]
   ids=[]
   for b in bases:
    if type(b) is dict and b.get('type')=='text_excerpt':
     q=b.get('quote_id');ec.check(type(q) is str and scope is not None and q in scope.by_wire,p,'exact_scoped_body_quote_required')
     if type(q) is str and q not in ids:ids.append(q)
   rel['quote_ids']=ids # explicit derived field, never replacement of model IDs
 ec.finish();out=normalize_v5(v,group,scopes,answer,claims)
 for item in out.get(group,[]):
  for row in item.get('component_reviews',[]) if group=='findings' else [item]:
   text=row.get('rationale','')
   if OLD_MARKER in text:
    reason,body=text.rsplit(OLD_MARKER,1);bound=json.loads(body);bound['source_selection_version']='program-local-selected-bases-v6';row['rationale']=reason+MARKER+json.dumps(bound,ensure_ascii=False,separators=(',',':'))
 return out

def selection_guidance(scopes,response,citation_indexes=None):
 """Explain the model's declared selection; do not replace any illegal ID."""
 from services.condition_candidates import catalog
 try:value=json.loads(response)
 except (ValueError,TypeError):return {'version':'local-selection-guidance-v6','reason':'Response is not a JSON object; original scope IDs still required'}
 result=[];group='findings' if citation_indexes is None else 'citation_reviews'
 for item in value.get(group,[]) if isinstance(value,dict) else []:
  if not isinstance(item,dict):continue
  ci=item.get('citation_index');scope=scopes[0] if group=='findings' else scopes[ci+1] if type(ci) is int and 0<=ci<len(scopes)-1 else None
  for row in item.get('component_reviews',[]) if group=='findings' else [item]:
   if not isinstance(row,dict) or scope is None:continue
   bases=item.get('bases',[]) if group=='findings' else row.get('bases',[])
   indexes=row.get('basis_indexes',[]) if group=='findings' else list(range(len(bases))) if isinstance(bases,list) else []
   valid=isinstance(bases,list) and isinstance(indexes,list) and all(type(i) is int and 0<=i<len(bases) for i in indexes)
   ids=[bases[i].get('quote_id') for i in indexes if isinstance(bases[i],dict) and bases[i].get('type')=='text_excerpt'] if valid else []
   valid=valid and all(isinstance(q,str) and q in scope.by_wire for q in ids)
   result.append({'claim_id':item.get('claim_id'),'component_index':row.get('component_index'),'citation_index':ci,'scope_id':scope.scope_id,'declared_selection_valid':valid,'selected_quote_ids':ids,
    'allowed_condition_ids_for_declared_selection':[{'condition_id':c['condition_id'],'quote_id':c['quote_id']} for c in catalog(scope).values() if valid and c['quote_id'] in ids]})
 return {'version':'local-selection-guidance-v6','note':'Model support_relation has NO quote_ids. Program derives them from your legal local bases/indexes. Conditions/repair select only these carriers; no justified repair means repair=null. This diagnostic does not change illegal IDs or certify support.','components':result}
