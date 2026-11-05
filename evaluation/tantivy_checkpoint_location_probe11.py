"""One copied-derived-checkpoint location test; original checkpoint read-only."""
import json,time,sqlite3,shutil
from pathlib import Path
import tantivy
from evaluation.tantivy_full_build_v1 import ROOT
from rag.tantivy_build import create_index,atomic
from rag.tantivy_manifest import sha
out=ROOT.parent/'tv-checkpoint-probe11';out.mkdir(exist_ok=False);dest=out/'tantivy';dest.mkdir();source=ROOT/'build/tantivy';proof=json.loads((ROOT/'recovery-audit-11.json').read_text());assert proof['passed'] and proof['committed']==680674
for f in source.iterdir():
 if f.is_file() and not f.name.endswith('.lock'):
  assert sha(f)==proof['native_files'][f.name];shutil.copyfile(f,dest/f.name);assert sha(dest/f.name)==proof['native_files'][f.name]
idx=create_index(dest);assert idx.searcher().num_docs==680674
c=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);rows=c.execute('select rowid,terms from input where position>=680674 and position<685674 order by position').fetchall();c.close();assert len(rows)==5000
w=idx.writer(heap_size=128000000,num_threads=1);result={'copied_verified_prefix':680674,'source_unchanged':True,'destination':str(dest),'factor':'derived checkpoint directory only','models':0};start=time.monotonic()
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
 idx.reload();result.update(n=idx.searcher().num_docs,seconds=time.monotonic()-start);atomic(ROOT/'checkpoint-location-probe11.json',result);print(json.dumps(result))
