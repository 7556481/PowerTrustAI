"""Markdown is authoritative; validate locally rendered pages without a browser claim."""
from pathlib import Path
import json,re,hashlib
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
from tools.learning_site import build

def source_text_digest(data):
    # Documentation-only identity: Git text checkout may use CRLF or LF.
    # No spaces/content changes; original Evidence/file hashes are untouched.
    return hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()

class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.add(attrs['id'])
        if tag=='a' and 'href' in attrs:self.links.append(attrs['href'])
        if tag=='link' and 'href' in attrs:self.links.append(attrs['href'])
        if tag=='script' and 'src' in attrs:self.links.append(attrs['src'])


def validate_local_links(directory):
    pages={}
    for page in directory.glob('*.html'):
        parser=PageLinks();parser.feed(page.read_text(encoding='utf-8'));pages[page.resolve()]=parser
    for page,parser in pages.items():
        for link in parser.links:
            url=urlsplit(link)
            if url.scheme or url.netloc:continue
            target=(page.parent/unquote(url.path)).resolve() if url.path else page
            if not target.exists():raise ValueError('Broken local link: '+link)
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError('Broken local anchor in '+page.name+': '+link)


def main():
    build();root=Path('docs/learning');chapters=sorted((root/'chapters').glob('*.md'))
    if not chapters:raise ValueError('Learning chapters absent')
    answer_count=0
    for p in chapters:
        text=p.read_text(encoding='utf-8')
        expected=text.count('::: answer ')
        if not expected:raise ValueError('Explained self checks missing: '+str(p))
        answer_count+=expected
        page=root/'site'/(p.stem+'.html');rendered=page.read_text(encoding='utf-8')
        if rendered.count('<details class="self-answer">')!=expected:raise ValueError('Folded answer rendering failed')
    v=json.loads((root/'source-check.json').read_text(encoding='utf-8'))
    for key in ('excerpts','request_route_excerpts','connection_excerpts','graph_excerpts','learning_runtime'):
        for record in v.get(key,[]):
            if source_text_digest(Path(record['file']).read_bytes())!=record['source_text_lf_sha256']:raise ValueError('Stale source reference: '+record['file'])
    validate_local_links(root/'site')
    print(f'{len(chapters)} chapters / {answer_count} folded answers / source hashes / local links verified; browser is separate.')
if __name__=='__main__':main()
