"""Markdown is authoritative; validate locally rendered pages without a browser claim."""
from pathlib import Path
import json,re,hashlib
from tools.learning_site import build

def source_text_digest(data):
    # Documentation-only identity: Git text checkout may use CRLF or LF.
    # No spaces/content changes; original Evidence/file hashes are untouched.
    return hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()

def main():
    build();root=Path('docs/learning');chapters=sorted((root/'chapters').glob('*.md'))
    if len(chapters)!=20:raise ValueError('Required twenty chapters absent')
    for p in chapters:
        text=p.read_text(encoding='utf-8')
        if text.count('::: answer ')!=3:raise ValueError('Required self checks missing: '+str(p))
        page=root/'site'/(p.stem+'.html');rendered=page.read_text(encoding='utf-8')
        if rendered.count('<details class="self-answer">')!=3:raise ValueError('Folded answer rendering failed')
    v=json.loads((root/'source-check.json').read_text(encoding='utf-8'))
    for key in ('excerpts','request_route_excerpts','connection_excerpts'):
        for record in v.get(key,[]):
            if source_text_digest(Path(record['file']).read_bytes())!=record['source_text_lf_sha256']:raise ValueError('Stale source reference: '+record['file'])
    for p in (root/'site').glob('*.html'):
        for link in re.findall(r'href="([^"]+)"',p.read_text(encoding='utf-8')):
            target=link.split('#')[0]
            if target and ':' not in target and not (p.parent/target).exists():raise ValueError('Broken local link: '+link)
    print('20 chapters / 60 folded answers / source hashes / local links verified; browser is separate.')
if __name__=='__main__':main()
