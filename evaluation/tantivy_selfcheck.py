"""Synthetic exhaustive membership checks, before any corpus performance timing."""
import tempfile,sqlite3,json
from pathlib import Path
from evaluation.tantivy_bounded_v1 import index,ast,query,save,LOCAL

def main():
 import tantivy
 with tempfile.TemporaryDirectory() as td:
  idx=index(Path(td)/'t');w=idx.writer(heap_size=16000000,num_threads=1);c=sqlite3.connect(':memory:');c.execute("create virtual table corpus_fts using fts5(terms,content='')")
  texts=['电压 稳定 无功','电压 无功 稳定','电压稳定 abc','nerc power factor','power factor nerc','gop top 30','a'*80,'电压 无功']
  for i,text in enumerate(texts,1):c.execute('insert into corpus_fts(rowid,terms) values(?,?)',(i,text));w.add_document(tantivy.Document(terms=text,rowid=i))
  w.commit();w.wait_merging_threads();idx.reload();searcher=idx.searcher();rows=[]
  for expression in ['"电压" OR "无功"','"电压" AND "稳定"','"电压 稳定"','("电压" OR "nerc") AND "无功"','"电压" NOT "稳定"','terms:"nerc" AND "power factor"','"'+('a'*80)+'"','"missing"']:
   b=sorted(r[0] for r in c.execute('select rowid from corpus_fts where corpus_fts match ?',(expression,)));a=sorted(searcher.doc(addr)['rowid'][0] for _,addr in searcher.search(query(idx,ast(expression)),limit=20,count=True).hits);assert a==b,(expression,a,b);rows.append(dict(expression=expression,matching_ids=a))
  for invalid in ['"a" NEAR "b"','title:"nerc"','"a" AND','"a-b"']:
   try:ast(invalid)
   except ValueError:pass
   else:raise AssertionError('Unsupported syntax accepted')
  save(LOCAL/'synthetic-semantics.json',dict(passed=True,rows=rows,unsupported_rejected=4));print('8 exhaustive membership checks and4 rejection checks passed;0 model')
if __name__=='__main__':main()
