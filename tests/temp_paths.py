"""Small synthetic output directories inside the existing diagnostics boundary."""
from pathlib import Path
import tempfile


def ignored_temporary_directory(*, dir, **kwargs):
    parent = Path(dir).resolve()
    root = Path(__file__).resolve().parents[1] / 'data'
    if parent not in (root / 'retrieval_local', root / 'evaluation_local'):
        raise ValueError('Unexpected test output parent')
    parent.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=parent, **kwargs)
