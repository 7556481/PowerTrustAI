"""Bounded failed-window diagnostic: logical junction versus physical path."""
import json,sqlite3,time,os,sys
from pathlib import Path
from rag.tantivy_build import create_index,atomic
from evaluation.tantivy_full_build_v1 import ROOT
import tantivy

def main():
 os.environ['RUST_BACKTRACE']='full'
 suffix=sys.argv[1] if len(sys.argv)>1 else '';assert suffix in ('','-sandbox');out=ROOT/('diagnostic16-paths'+suffix);out.mkdir(exist_ok=False)
 con=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
 rows=con.execute('select rowid,terms from input where position>=685674 and position<690674 order by position').fetchall();con.close();assert len(rows)==5000
 results=[]
 for name,path in [('junction',ROOT/('build/diagnostic16-junction'+suffix)),('physical',(ROOT/'build').resolve()/('diagnostic16-physical'+suffix))]:
  assert not path.exists();idx=create_index(path);w=idx.writer(heap_size=128000000,num_threads=1);r={'path':str(path),'factor':name,'window':[685674,690674]};start=time.monotonic()
  try:
   for rid,t in rows:w.add_document(tantivy.Document(rowid=rid,terms=t))
   w.commit();r['passed']=True
  except BaseException as e:
   r['primary']=repr(e)
   # Isolated failed probe only: expose native originating error; never touch failed production checkpoint.
   try:w.commit()
   except BaseException as e:r['diagnostic_commit']=repr(e)
  finally:
   try:w.wait_merging_threads()
   except BaseException as e:r['cleanup']=repr(e)
  idx.reload();r.update(seconds=time.monotonic()-start,n=idx.searcher().num_docs);results.append(r);atomic(out/'result.json',results)
 print(json.dumps(results))
if __name__=='__main__':main()
