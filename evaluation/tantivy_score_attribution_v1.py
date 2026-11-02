"""Bounded, read-only score attribution for previously diagnosed Q10/Q4/Q12."""
import collections,json,math,re,sqlite3,time
from pathlib import Path
from rag.chinese_terms import terms
from evaluation.tantivy_ranking_v1 import ROOT,SCOPES,SOURCE,readonly

def varints(blob):
 out=[];v=0
 for b in blob:
  v=(v<<7)|(b&127)
  if b<128:out.append(v);v=0
 return out

def leaves(x):
 if 'TermQuery' in x.get('description',''):yield x
 else:
  for y in x.get('details',[]):yield from leaves(y)
def flattened(x):
 yield x
 for y in x.get('details',[]):yield from flattened(y)
def main():
 started=time.monotonic();diag=json.loads((ROOT/'diagnosis.json').read_text(encoding='utf8'));freeze=json.loads((ROOT/'freeze.json').read_text(encoding='utf8'));output=[]
 for r in diag:
  q=next(q for q in freeze['queries'] if q['id']==r['query']);folder=SCOPES[r['scope']]
  with readonly(folder/'fts.sqlite3') as c,readonly(SOURCE) as source:
   c.execute('create virtual table temp.vocab using fts5vocab(main,corpus_fts,row)')
   global_stats=varints(c.execute('select block from corpus_fts_data where id=1').fetchone()[0]);n,total=global_stats;avg=total/n
   words=re.findall(r'"([^" ]+)"',q['fts_expression']);assert len(set(words))<=100
   t=time.monotonic();df={w:(c.execute('select doc,cnt from temp.vocab where term=?',(w,)).fetchone() or (0,0)) for w in set(words)};df_seconds=time.monotonic()-t
   docs=[]
   for detail in r['details']:
    rid=detail['rowid'];expected_t=dict(r['tantivy'])[rid];expected_f=dict(r['fts']).get(rid);dl=varints(c.execute('select sz from corpus_fts_docsize where id=?',(rid,)).fetchone()[0])[0]
    if rid<0:
     fid=c.execute('select fragment_id from mapping where rowid=?',(rid,)).fetchone()[0];text=source.execute('select search_text from fragments where fragment_id=?',(fid,)).fetchone()[0];tokens=terms(text)
    else:
     with readonly('D:/PowerTrustAI/data/retrieval_local/tantivy-stability-v2/input/spool.sqlite3') as spool:tokens=spool.execute('select terms from rows where rowid=?',(rid,)).fetchone()[0].split()
    tf=collections.Counter(tokens);assert len(tokens)==dl
    all_leaves=list(leaves(detail['explanation']));lengths={z['value'] for leaf in all_leaves for z in flattened(leaf) if z.get('description')=='dl, length of field'};assert len(lengths)==1;tdl=next(iter(lengths));table=[]
    for w in sorted(set(words)):
     if not tf[w]:continue
     freq=df[w][0];idf=math.log((n-freq+.5)/(freq+.5));fi=idf if idf>0 else 1e-6;ti=math.log1p((n-freq+.5)/(freq+.5));table.append({'term':w,'query_multiplicity':words.count(w),'frequency':tf[w],'df':freq,'total_occurrences':df[w][1],'fts_idf':fi,'tantivy_idf':ti})
    def score(t_idf,t_length):
     length=tdl if t_length else dl
     return sum(x['query_multiplicity']*x['frequency']*2.2*(x['tantivy_idf'] if t_idf else x['fts_idf'])/(x['frequency']+1.2*(.25+.75*length/avg)) for x in table)
    actual=score(False,False);assert expected_f is not None and abs(actual-expected_f)<1e-8,(rid,actual,expected_f)
    predicted_t=score(True,True);assert abs(predicted_t-expected_t)<.0002,(rid,predicted_t,expected_t)
    docs.append({'rowid':rid,'fts_rank':next(i+1 for i,x in enumerate(r['fts']) if x[0]==rid),'tantivy_rank':next(i+1 for i,x in enumerate(r['tantivy']) if x[0]==rid),'fts_score':expected_f,'tantivy_score':expected_t,'length_exact':dl,'length_tantivy':tdl,'matched_terms':table,'counterfactual_scores':{'fts_formula':actual,'only_idf_swapped':score(True,False),'only_length_swapped':score(False,True),'both_swapped':predicted_t}})
   # Exact counts are separate diagnostic work, never part of normal Top-K timing.
   t=time.monotonic();matched=c.execute('select count(*) from corpus_fts where corpus_fts match ?',(q['fts_expression'],)).fetchone()[0]
   output.append({'scope':r['scope'],'query':r['query'],'documents':n,'total_terms':total,'avgdl':avg,'df_terms':len(df),'df_seconds':df_seconds,'exact_count':matched,'count_seconds':time.monotonic()-t,'docs':docs})
 (ROOT/'score-attribution.json').write_text(json.dumps({'elapsed':time.monotonic()-started,'results':output},ensure_ascii=False,indent=2),encoding='utf8')
 for r in output:
  print(r['scope'],r['query'],'df_s',r['df_seconds'],'docs',[(d['rowid'],d['length_exact'],d['length_tantivy'],d['counterfactual_scores']) for d in r['docs']],flush=True)
if __name__=='__main__':main()
