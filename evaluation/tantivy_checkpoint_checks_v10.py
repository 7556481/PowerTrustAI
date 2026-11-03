import json
import tempfile
import time
import unittest
from pathlib import Path
from evaluation.tantivy_checkpoint_recovery_v10 import boundary,component,classify,admit_recovery,audit
from rag.tantivy_manifest import IndexIdentityError


class RecoveryChecks(unittest.TestCase):
    def test_exact_boundaries(self):
        p={'start':3,'end':5,'rows':[1,2]}
        self.assertIn('offer-journal',boundary(3,3,{'count':3},p)[0])
        self.assertIn('mapping-only',boundary(3,5,{'count':3},p)[0])
        self.assertIn('no-native-replay',boundary(5,5,{'count':3},p)[0])
        for m,n,c in [(3,4,3),(4,5,3),(3,3,2),(5,3,3)]:
            with self.assertRaises(IndexIdentityError):boundary(m,n,{'count':c},p)

    def test_cap_no_progress_and_deadline(self):
        s={'entries':[]}
        admit_recovery(s,5,time.time()+10,{'initial':True})
        with self.assertRaises(RuntimeError):admit_recovery(s,5,time.time()+10,{})
        admit_recovery(s,6,time.time()+10,{})
        admit_recovery(s,7,time.time()+10,{})
        with self.assertRaises(RuntimeError):admit_recovery(s,8,time.time()+10,{})
        with self.assertRaises(TimeoutError):admit_recovery({'entries':[]},5,time.time()-1,{})

    def test_generic_failure_not_classified(self):
        with self.assertRaises(RuntimeError):classify([],"ValueError('worker killed')",Path.cwd())
        root=Path.cwd();p=str(root).replace('/','\\')
        e={'operation':'MoveFileExW','path':p+'\\.tmp-test','to':p+'\\.managed.json','failed':True,'winerror':5,'wall_ms':100}
        self.assertEqual(classify([e],"ValueError('worker killed')",root)['kind'],'identified-managed-atomic-replace-win5')
        with self.assertRaises(RuntimeError):classify([e,dict(e,operation='NtWriteFile',winerror=112)],"ValueError('worker killed')",root)

    def test_real_file_crc_and_journal_native_before_mapping(self):
        import hashlib
        from rag.tantivy_build import CheckpointBuild,InputSpool
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);identity={'expected':4,'version':'synthetic'};sp=InputSpool(root/'input.sqlite3',identity)
            rows=[[i,-(i+1),'fragment-'+str(i),hashlib.sha256(str(i).encode()).hexdigest(),hashlib.sha256(b'original terms').hexdigest(),'original terms'] for i in range(4)]
            sp.append(rows);sp.close();b=CheckpointBuild(root/'build',identity,total_seconds=60,segment_seconds=30)
            b.append(rows[:2]);b.close()
            b=CheckpointBuild(root/'build',identity,total_seconds=60,segment_seconds=30)
            with self.assertRaisesRegex(RuntimeError,'native-before-mapping'):b.append(rows[2:],fail_after_native=True)
            b.close()
            proof=audit(root/'build',identity,root/'input.sqlite3',root/'proof.json')
            self.assertEqual(proof['native_committed'],4)
            self.assertEqual(proof['mapped'],2)
            self.assertIn('mapping-only',proof['action'])
            b=CheckpointBuild(root/'build',identity,total_seconds=60,segment_seconds=30)
            self.assertEqual(b.con.execute('select count(*) from rows').fetchone()[0],4)
            b.close()
            audit(root/'build',identity,root/'input.sqlite3',root/'after.json')
            file=next((root/'build/tantivy').glob('*.store'))
            self.assertTrue(component(file)['bytes'])
            with file.open('r+b') as f:
                old=f.read(1);f.seek(0);f.write(bytes([old[0]^1]))
            with self.assertRaisesRegex(IndexIdentityError,'CRC'):component(file)


if __name__=='__main__':unittest.main()
