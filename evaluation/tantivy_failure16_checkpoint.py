"""Single cloned-checkpoint failure16 diagnostic; original checkpoint remains read-only."""
import json,shutil,sqlite3,time
from pathlib import Path
from rag.tantivy_build import atomic
from rag.tantivy_manifest import sha
from evaluation.tantivy_full_build_v1 import ROOT
from evaluation.tantivy_full_identity_v1 import FullCheckpoint

def main():
 out=ROOT/'diagnostic16-checkpoint';out.mkdir(exist_ok=False);dest=out/'tantivy';dest.mkdir();started=time.time();files={}
 for p in (ROOT/'build/tantivy').iterdir():
  if p.is_file() and not p.name.endswith('.lock'):
   before=sha(p);shutil.copyfile(p,dest/p.name);assert before==sha(dest/p.name)==sha(p);files[p.name]=before
 for name in ('mapping.sqlite3','checkpoint.json','prepared.json'):
  src=ROOT/'build'/name;shutil.copyfile(src,out/name);assert sha(src)==sha(out/name)
 identity=json.loads((ROOT/'build-identity.json').read_text());con=sqlite3.connect((ROOT/'spool.sqlite3').resolve().as_uri()+'?mode=ro',uri=True);rows=con.execute('select * from input where position>=685674 and position<690674 order by position').fetchall();con.close();assert len(rows)==5000
 owner=None;r={'source_committed':685674,'window':[685674,690674],'copied_files':files,'original_readonly':True}
 try:
  owner=FullCheckpoint(out,identity,authorized_full=True,total_seconds=180,segment_seconds=180)
  owner.append(rows);r['passed']=True
 except BaseException as e:
  r['primary']=repr(e)
  if owner:
   try:owner.writer.commit()
   except BaseException as e:r['isolated_commit_diagnostic']=repr(e)
 finally:
  if owner:
   try:r['cleanup']=owner.close(primary=RuntimeError('diagnostic') if 'primary' in r else None)
   except BaseException as e:r['cleanup']=repr(e)
  r['seconds']=time.time()-started;atomic(out/'result.json',r)
 print(json.dumps({k:v for k,v in r.items() if k!='copied_files'}))
if __name__=='__main__':main()
