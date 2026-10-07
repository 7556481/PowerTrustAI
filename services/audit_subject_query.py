"""One syntactic subject query after assessed technical evidence insufficiency.

No truth correction, device dictionary, ranking change or silent evidence filtering.
The original assertion query and all deliveries are retained. Ambiguous syntax skips.
"""
import re
VERSION='audit-subject-supplement-v1'

PRE_REVIEW_VERSION='literal-subject-pre-review-v2'

def literal_subject(text):
 text=text.strip()
 m=re.search(r'可以|能够|不能|会|能|是|\b(?:can|cannot|may|is|are|does|will)\b',text,re.I)
 if not m:return ''
 subject=text[:m.start()].strip(' \"“”\'')
 if not 2<=len(subject)<=60 or re.search(r'[,，;；。:：]|(?:^|\s)(?:if|when|under)\b|条件|时',subject,re.I):return ''
 return subject

def question_subject(question):
 # Only explicit concept-question subjects, not inferred answers or source terms.
 first=re.split(r'[？?。；;]',question.strip(),maxsplit=1)[0]
 first=re.sub(r'^(?:请)?(?:简要)?(?:解释|说明|介绍)\s*','',first)
 patterns=(r'^(?:什么是|什么叫)([^，,:：]{2,60})$',
           r'^([^，,:：]{2,60}?)的(?:主要作用|作用|定义|含义|原理)(?:是什么|是怎样的)?$',
           r'^([^，,:：]{2,60}?)是什么$',r'^what is (.{2,60})$',r'^what does (.{2,60}) do$')
 for pattern in patterns:
  m=re.fullmatch(pattern,first,re.I)
  if m:return m[1].strip()
 return ''

def before_review(claims):
 subjects=[]
 for c in claims:
  if not c.components or any(t not in ('technical_content','document_body') for t in getattr(c,'component_basis_targets',())):continue
  subject=literal_subject(c.text)
  if subject and subject not in subjects:subjects.append(subject)
 return '\n'.join(subjects[:3])
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
