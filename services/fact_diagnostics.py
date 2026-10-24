"""Read-only diagnostics, no policy changes."""
def explain(verification):
 rows=[]
 for r in verification.get('object_reviews',[]):
  causes=[]
  if r.get('origin')=='execution_incomplete':causes.append('execution_failure')
  if r.get('stage_conflict'):causes.append('stage_classification_or_dependency_conflict')
  if r.get('classification_objection'):causes.append('classification_objection')
  if r.get('fidelity') in ('uncertain','disputed'):causes.append('literal_fidelity_issue')
  if r.get('raw_model_status')=='insufficient_evidence':causes.append('insufficient_evidence')
  if r.get('object_kind')=='engineering_relation':causes.append('engineering_capability_boundary')
  rows.append(dict(claim_id=r.get('claim_id'),component_id=r.get('component_id'),raw_support=r.get('raw_model_status'),effective_support=r.get('effective_support_status'),causes=causes,classification_reason=r.get('classification_objection')))
 return rows
