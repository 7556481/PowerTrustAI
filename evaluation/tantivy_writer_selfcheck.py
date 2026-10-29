"""Actual builder checkpoint/lifecycle regression with synthetic source only."""
import gc,tempfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from evaluation.tantivy_bounded_v1 import build,index

def main():
 with tempfile.TemporaryDirectory() as td:
  folder=Path(td)/'sample';f={'resources':{'writer_heap':16000000},'source':{'max_chunk':2100}}
  def rows(c,**kw):
   for i in range(kw['start'],kw['stop']):yield i+1,'synthetic-'+str(i),'无功 功率','无功 功率'
  with patch('evaluation.tantivy_bounded_v1.source',lambda:nullcontext(None)),patch('evaluation.tantivy_bounded_v1.rows',rows),patch('rag.chinese_terms.terms',lambda s:tuple(s.split())):
   r=build(folder,2100,f,SimpleNamespace(check=lambda **kw:{}))
  assert r['n']==2100 and r['complete'];idx=index(folder/'tantivy');idx.reload();assert idx.searcher().num_docs==2100;del idx;gc.collect()
 print('Actual builder crossed two1000-doc barriers with2100 exact synthetic mappings;0 model')
if __name__=='__main__':main()
