"""Server-owned bearer token and an OS process lease; no token logging."""
import os
import secrets

def token_for(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('x',encoding='ascii') as f:f.write(secrets.token_urlsafe(32))
    except FileExistsError:pass
    value=path.read_text(encoding='ascii').strip()
    if len(value)<32 or any(c.isspace() for c in value):raise ValueError('Invalid managed local token file')
    return value

class ProcessLease:
    def __init__(self,path):self.path=path;self.file=None
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.file=self.path.open('a+b')
        if self.file.seek(0,2)==0:self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();self.file=None
            raise RuntimeError('Another local application process owns this run database') from None
    def close(self):
        if self.file:
            self.file.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            self.file.close();self.file=None

