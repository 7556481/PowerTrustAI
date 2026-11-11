"""Explicit opt-in factory; normal production default stays serial preparation."""
from backend.assembly import ComponentFactory
class OverlapFactory(ComponentFactory):
 def create(self,*a,**kw):
  b=super().create(*a,**kw)
  if self.config.tantivy_manifest is not None or self.config.fact_review_execution!='serial_v1' or self.config.audit_strategy!='baseline':raise ValueError('SQLite production fact order required')
  b.harness.fact_domain_retrieval_overlap=True
  return b
