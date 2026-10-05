"""Loopback launch ticket -> HttpOnly session; bearer remains an advanced fallback.

Only the authenticated local launcher can issue a short, single-use ticket.
Ticket is POSTed from a local bootstrap file, never put in a URL or log.
Persistent registry contains session digests and expiry only, never credentials.
"""
import hashlib
import html
import json
import os
from pathlib import Path
import secrets
import time


class LocalSessions:
    version = 'localhost-launch-session-v1'
    lifetime = 7 * 86400

    def __init__(self, run_db):
        self.path = Path(run_db).with_suffix('.sessions.json')
        self.cookie = 'powertrust_' + hashlib.sha256(str(Path(run_db).resolve()).encode()).hexdigest()[:12]
        self.tickets = {}
        self.sessions = {}
        if self.path.exists():
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if value.get('version') != self.version:raise ValueError('Unknown local session version')
            self.sessions = value['sessions']

    @staticmethod
    def digest(value):return hashlib.sha256(value.encode('ascii')).hexdigest()

    def valid(self, value):
        if not isinstance(value, str) or len(value) > 100 or not value.isascii():return False
        return self.sessions.get(self.digest(value), 0) > time.time()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions = {k:v for k,v in self.sessions.items() if v > time.time()}
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version':self.version, 'sessions':self.sessions}), encoding='utf-8')
        os.replace(temporary, self.path)

    def issue(self, origin):
        ticket = secrets.token_urlsafe(32)
        self.tickets = {k:v for k,v in self.tickets.items() if v > time.time()}
        self.tickets[self.digest(ticket)] = time.time() + 60
        # No external scripts/resources; an explicit button also works without JS.
        return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="referrer" content="no-referrer"><title>打开PowerTrustAI</title>'
            '<form method="post" action="'+html.escape(origin+'/session/bootstrap',quote=True)+'">'
            '<input type="hidden" name="ticket" value="'+ticket+'">'
            '<button>打开PowerTrustAI</button></form>'
            '<script>document.forms[0].submit();</script></html>')

    def redeem(self, ticket):
        if not isinstance(ticket,str) or len(ticket)>100 or not ticket.isascii():return None
        if self.tickets.pop(self.digest(ticket), 0) <= time.time():return None
        session = secrets.token_urlsafe(32)
        self.sessions[self.digest(session)] = time.time() + self.lifetime
        self.save()
        return session

    def forget(self, value):
        if isinstance(value,str) and value.isascii():self.sessions.pop(self.digest(value),None)
        self.save()
