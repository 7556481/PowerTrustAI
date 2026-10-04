"""Public synthetic diagnostic directories; no pre-existing data tree required."""
import tempfile
from services.response_diagnostics import LOCAL_ROOT

def synthetic_diagnostics():
    LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix='synthetic_fixture-', dir=LOCAL_ROOT)
