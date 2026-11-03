"""One fixed C-temp disk-location diagnostic, same5000/schema/engine/writer."""
import tempfile,sqlite3,json,time,shutil,os
from pathlib import Path
import tantivy
from evaluation.tantivy_full_build_v1 import ROOT
from rag.tantivy_build import create_index,atomic
os.environ['RUST_BACKTRACE']='full'
assert not (ROOT/'disk-location-probe-Dshort11.json').exists()
assert shutil.disk_usage(tempfile.gettempdir()).free>31*1024**3
folder=ROOT.parent/'tv-path-probe11';folder.mkdir(exist_ok=False);c=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);rows=c.execute('select rowid,terms from input where position>=680674 and position<685674 order by position').fetchall();c.close();assert len(rows)==5000
index=create_index(folder/'tantivy');w=index.writer(heap_size=128000000,num_threads=1);result={'window':[680674,685674],'folder':str(folder),'factor':'disk location only; same5000 input/schema/pretokenization/128MB/1worker','models':0};start=time.monotonic()
try:
 for rid,text in rows:w.add_document(tantivy.Document(rowid=rid,terms=text))
 w.commit();result['passed']=True
except Exception as e:
 result.update(passed=False,primary=repr(e))
 try:w.commit()
 except Exception as e:result['commit_diagnostic']=repr(e)
finally:
 try:w.wait_merging_threads()
 except Exception as e:result['cleanup']=repr(e)
 index.reload();result.update(n=index.searcher().num_docs,seconds=time.monotonic()-start,bytes=sum(x.stat().st_size for x in folder.rglob('*') if x.is_file()));atomic(ROOT/'disk-location-probe-Dshort11.json',result);print(json.dumps(result))
