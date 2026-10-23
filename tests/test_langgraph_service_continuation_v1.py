"""Offline five-item collection, stop and Windows resource-release gates."""
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from evaluation import langgraph_service_trial_v1 as trial
from evaluation import langgraph_service_continuation_v1 as continuation
from tests.test_langgraph_service_trial_v1 import Gates

@unittest.skipUnless(importlib.util.find_spec('langgraph'),'Optional locked graph runtime not installed')
class ContinuationGates(unittest.TestCase):
    def collect(self,fail_second=False):
        collect=trial.saved_result;seen=[];database=[]
        def reader(db,rid):
            database.append(Path(db));result=collect(db,rid)
            seen.append((rid,result))
            if fail_second and len(seen)==2:raise OSError('Synthetic collector fault after persistence')
            return result
        with patch.object(trial,'ORDER',continuation.ORDER),patch.object(trial,'saved_result',side_effect=reader):
            summary,provider=Gates().exercise()
        # TemporaryDirectory cleanup above must succeed on Windows: no live handles.
        self.assertFalse(database[0].exists())
        return summary,provider,seen

    def test_five_complete_once_and_saved_accounting_matches_sent(self):
        s,p,seen=self.collect()
        self.assertEqual([b['id'] for b in s['branches']],[i for i,_,_ in continuation.ORDER])
        self.assertEqual([b['status'] for b in s['branches']],['complete']*5)
        self.assertEqual(len({rid for rid,_ in seen}),5)
        self.assertEqual(sum(len(b['sent']) for b in s['branches']),len(p.requests))
        for b in s['branches']:
            self.assertEqual(len(b['sent']),len(b['result']['model_records']))
            self.assertFalse(b['result']['execution_issues'])

    def test_middle_collection_failure_preserves_two_accepted_rows_stops_three(self):
        s,p,seen=self.collect(True)
        self.assertEqual([b['status'] for b in s['branches']],['complete','execution_failed']+['unexecuted']*3)
        self.assertEqual(len(seen),2)
        self.assertEqual(s['branches'][1]['run_id'],seen[1][0])
        self.assertIsNotNone(seen[1][1])
        self.assertEqual(sum(len(b.get('sent',[])) for b in s['branches']),len(p.requests))

    def test_readonly_connection_releases_database_for_rename_delete(self):
        with tempfile.TemporaryDirectory(dir=trial.ROOT/'data/retrieval_local') as t:
            p=Path(t)/'runs.sqlite3'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE runs(id TEXT,result TEXT)')
                db.execute("INSERT INTO runs VALUES('x','{}')")
            db.close()
            self.assertEqual(trial.saved_result(p,'x'),{})
            with self.assertRaises(ValueError):trial.saved_result(p,'absent')
            q=p.with_suffix('.released');p.rename(q);q.unlink()

    def test_original_first_item_is_excluded(self):
        self.assertEqual(continuation.ORDER,trial.ORDER[1:])
        self.assertNotIn('LSI-01-S',[i for i,_,_ in continuation.ORDER])

    def test_manifest_allows_only_declared_engineering_hash_changes(self):
        old=trial.read(continuation.OLD_FREEZE)
        manifest=trial.read(continuation.OLD_FREEZE)['manifest']
        key=next(k for k in manifest['source_sha256'] if k.replace('\\','/')=='backend/static/app.js')
        manifest['source_sha256'][key]='engineering-change'
        # Archived live source identities must reject today's evolved source tree.
        # Exercise the old delta rule against its frozen inventory, never rewrite it.
        frozen={str((continuation.ROOT/f['path']).resolve()):f['sha256'] for f in old['bound_files']}
        def frozen_digest(path):
            name=Path(path).relative_to(continuation.ROOT).as_posix()
            return 'engineering-change' if name=='backend/static/app.js' else frozen[str(Path(path).resolve())]
        with patch.object(trial,'config_identity',return_value=old['configuration']),patch.dict('os.environ',{'DEEPSEEK_MODEL_ID':old['model_id']}),patch.object(continuation,'digest',side_effect=frozen_digest):
            changes=continuation.compatibility(old,None,manifest)
            self.assertIn('backend/static/app.js',[r['path'] for r in changes])
            manifest['prompts']['generation']='forbidden-business-change'
            with self.assertRaises(ValueError):continuation.compatibility(old,None,manifest)

if __name__=='__main__':unittest.main()
