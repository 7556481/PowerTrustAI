"""Required public regression; no credentials or private replay prerequisites."""
import importlib.util,unittest,sys
from pathlib import Path

def main():
    for name in ('fastapi','httpx','pyarrow','jieba','pypdf'):
        if importlib.util.find_spec(name) is None:raise RuntimeError('Required public test dependency missing: '+name)
    for name in ('test_schema14_factory_flow.py','test_compact_review.py','test_batch_control.py','test_learning_site.py'):
        if not (Path('tests')/name).is_file():raise RuntimeError('Required public regression missing: '+name)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
    # Only unavailable private archives and explicitly optional runtime checks may skip.
    forbidden=[(str(t),why) for t,why in result.skipped if not any(s in why.lower() for s in ('private','historical','archive','optional node'))]
    for test,why in forbidden:print('Unexpected required check skipped:',test,why,file=sys.stderr)
    if not result.wasSuccessful() or forbidden:raise SystemExit(1)
    print('Public regressions passed; optional skips:',len(result.skipped))
if __name__=='__main__':main()
