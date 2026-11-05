"""Explicit isolated DLL build; does not install dependencies or alter the venv."""
import json
import os
import subprocess
import sys
from pathlib import Path
from rag.tantivy_manifest import sha


def main():
    root=Path(os.environ['PTAI_ATOMIC_TEST_ROOT'])
    root.mkdir(parents=True,exist_ok=True)
    source=Path('evaluation/tantivy_atomic_compat_v9.c')
    dll=root/'ptai_atomic_compat_v9.dll'
    command=[sys.executable,'-m','ziglang','cc','-target','x86_64-windows-gnu','-O2','-shared',str(source),'-o',str(dll),'-lkernel32']
    subprocess.run(command,check=True)
    (root/'build-identity.json').write_text(json.dumps({'command':command,'source_sha256':sha(source),'dll_sha256':sha(dll),'ziglang':'0.15.2','scope':'unapproved experimental build; not a production dependency'}))


if __name__=='__main__':main()
