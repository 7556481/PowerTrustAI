"""Read-only source -> bounded independent scalar/document-length statistics.
No scorer release: arbitrary exact phrase DF fails candidate-bounded admission.
"""
import json,sqlite3,time
from pathlib import Path
from evaluation.tantivy_score_attribution_v1 import varints
ROOT=Path('D:/PowerTrustAI/data/retrieval_local/tantivy-light-score-v1')
SCOPES={'quality674':Path('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2/quality/fts.sqlite3'),'million':Path('D:/PowerTrustAI/data/retrieval_local/tantivy-supervision-v3/million/fts.sqlite3')}
def build():
 results=[]
 for name,source in SCOPES.items():
  target=ROOT/(name+'-stats.sqlite3')
  if target.exists():raise RuntimeError('Independent statistics already exist; no overwrite')
  start=time.perf_counter();src=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(target)
  try:
   n,total=varints(src.execute('select block from corpus_fts_data where id=1').fetchone()[0]);assert 0<n<=1000000
   dst.executescript('create table metadata(n integer,total_terms integer,avgdl real);create table lengths(rowid integer primary key,length integer not null);');dst.execute('insert into metadata values(?,?,?)',(n,total,total/n));count=0;length_sum=0
   for rid,blob in src.execute('select id,sz from corpus_fts_docsize order by id'):
    if time.perf_counter()-start>120:raise TimeoutError('Statistics build admission expired')
    values=varints(blob);assert len(values)==1;dl=values[0];dst.execute('insert into lengths values(?,?)',(rid,dl));count+=1;length_sum+=dl
   assert count==n and length_sum==total;dst.commit()
  finally:src.close();dst.close()
  results.append({'scope':name,'n':n,'total_terms':total,'avgdl':total/n,'seconds':time.perf_counter()-start,'bytes':target.stat().st_size,'all_lengths_sum_verified':True,'tf_or_phrase_index_built':False})
 (ROOT/'statistics-build.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(json.dumps(results))
if __name__=='__main__':build()
