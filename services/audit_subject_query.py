"""One syntactic subject query after assessed technical evidence insufficiency.

No truth correction, device dictionary, ranking change or silent evidence filtering.
The original assertion query and all deliveries are retained. Ambiguous syntax skips.
"""
import re
VERSION='audit-subject-supplement-v1'
def query(claims,findings):
 byid={f.claim_id:f for f in findings};subjects=[]
 for c in claims:
  f=byid.get(c.claim_id)
  if f is None or f.status.value!='insufficient_evidence':continue
  if not c.components or any(t not in ('technical_content','document_body') for t in getattr(c,'component_basis_targets',())):continue
  if any(getattr(r,'fidelity_status','')!='faithful' for r in f.component_reviews):continue
  text=c.text.strip() # Literal answer anchor, never translated proposition for subject identity.
  m=re.search(r'可以|能够|不能|会|能|是|\b(?:can|cannot|may|is|are|does|will)\b',text,re.I)
  if not m:continue
  subject=text[:m.start()].strip(' \"“”\'')
  if not 2<=len(subject)<=60 or re.search(r'[,，;；。:：]|(?:^|\s)(?:if|when|under)\b|条件|时',subject,re.I):continue
  if subject not in subjects:subjects.append(subject)
 return '\n'.join(subjects[:3])
