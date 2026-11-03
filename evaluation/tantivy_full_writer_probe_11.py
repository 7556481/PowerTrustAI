"""One frozen failed-input window, new derived index, preserve original error chain."""
import os,json,sqlite3,time,traceback
from pathlib import Path
from rag.tantivy_build import create_index,atomic
from evaluation.tantivy_full_build_v1 import ROOT

def error(e):return {'type':type(e).__name__,'repr':repr(e),'cause':repr(e.__cause__),'context':repr(e.__context__)}
def main():
 os.environ['RUST_BACKTRACE']='full';out=ROOT/'diagnostic-window-11';out.mkdir(exist_ok=False);c=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);rows=c.execute('select rowid,terms from input where position>=680674 and position<685674 order by position').fetchall();c.close();assert len(rows)==5000
 import tantivy
 index=create_index(out/'tantivy');w=index.writer(heap_size=128000000,num_threads=1);started=time.monotonic();primary=None;result={'window':[680674,685674],'rows':len(rows),'changes':'fresh index, same128MB/1worker, already prepared strings; no source reads/tokenization interleaved'}
 try:
  for rid,pre in rows:w.add_document(tantivy.Document(rowid=rid,terms=pre))
  w.commit();result['completed']=True
 except BaseException as e:
  primary=e;result['primary']=error(e)
  try:w.commit()
  except BaseException as original:result['commit_root_error']=error(original)
 finally:
  try:w.wait_merging_threads()
  except BaseException as e:result['close_error']=error(e)
  result['seconds']=time.monotonic()-started;index.reload();result['native_n']=index.searcher().num_docs;atomic(out/'result.json',result)
 if primary:raise primary
if __name__=='__main__':main()
