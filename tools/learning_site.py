"""Offline Markdown learning site: stdlib only, no application/database imports."""
import argparse,html,json,re,hashlib,webbrowser
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/learning'
DEST=SOURCE/'site'

def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
    def link(m):
        target=m[2]
        if re.match(r'^(?:javascript|data|file):',target,re.I):return m[1]
        if target.endswith('.md'):target=target[:-3]+'.html'
        return '<a href="'+target+'" rel="noreferrer noopener">'+m[1]+'</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)

def highlight(code,language):
    # Lexical display only. No executable HTML or imported highlighting framework.
    if language in ('python','py'):
        import tokenize,io,token,keyword
        parts=[];end=0;lines=code.splitlines(keepends=True);starts=[0]
        for line in lines:starts.append(starts[-1]+len(line))
        try:
            for t in tokenize.generate_tokens(io.StringIO(code).readline):
                a=starts[min(t.start[0]-1,len(starts)-1)]+t.start[1]
                b=starts[min(t.end[0]-1,len(starts)-1)]+t.end[1]
                if a<end or b<=a:continue
                parts.append(html.escape(code[end:a]));kind=''
                if t.type==token.STRING:kind='string'
                elif t.type==token.NUMBER:kind='number'
                elif t.type==tokenize.COMMENT:kind='comment'
                elif t.type==token.NAME and keyword.iskeyword(t.string):kind='keyword'
                parts.append('<span class="'+kind+'">'+html.escape(code[a:b])+'</span>' if kind else html.escape(code[a:b]));end=b
            return ''.join(parts)+html.escape(code[end:])
        except (tokenize.TokenError,IndentationError):pass
    return html.escape(code)

def diagram(source):
    """Small explicit diagram format embedded in Markdown; no remote renderer."""
    spec=json.loads(source);nodes={n['id']:n for n in spec['nodes']}
    colors={'control':'#176f63','data':'#275a97','persist':'#a85a13'}
    uid=hashlib.sha256(source.encode()).hexdigest()[:10]
    out=[f'<div class="diagram"><svg role="img" aria-label="{html.escape(spec["title"])}" viewBox="0 0 {int(spec["width"])} {int(spec["height"])}" xmlns="http://www.w3.org/2000/svg"><title>{html.escape(spec["title"])}</title><defs>']
    for kind,color in colors.items():out.append(f'<marker id="{uid}-{kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>')
    out.append('</defs>')
    for edge in spec['edges']:
        a,b=nodes[edge['from']],nodes[edge['to']];kind=edge['kind'];color=colors[kind]
        if 'points' in edge:points=edge['points']
        elif a['x']==b['x']:points=[[a['x']+a['w']/2,a['y']+a['h']],[b['x']+b['w']/2,b['y']]]
        else:points=[[a['x']+a['w'],a['y']+a['h']/2],[b['x'],b['y']+b['h']/2]]
        path='M '+' L '.join(f'{float(x)} {float(y)}' for x,y in points)
        dash='' if kind=='control' else ' stroke-dasharray="7 4"' if kind=='data' else ' stroke-dasharray="2 4"'
        out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"{dash} marker-end="url(#{uid}-{kind})"/>')
        if edge.get('label'):
            x,y=edge.get('label_at',points[len(points)//2]);out.append(f'<text x="{x}" y="{y}" class="edge-label" fill="{color}">{html.escape(edge["label"])}</text>')
    for n in nodes.values():
        out.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="8" fill="#edf3ee" stroke="#64858b"/>')
        for i,line in enumerate(n['label'].split('\n')):out.append(f'<text x="{n["x"]+n["w"]/2}" y="{n["y"]+22+i*19}" text-anchor="middle" fill="#182c34" class="node-label">{html.escape(line)}</text>')
    out.append('</svg></div><p class="diagram-legend">实线绿：控制调用；虚线蓝：数据交付；点线橙：持久化。箭头不表示投票或事实证明。</p>')
    return ''.join(out)

def render(markdown):
    out=[];toc=[];lines=markdown.splitlines();i=0;paragraph=[];listing=False
    def flush():
        if paragraph:out.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    def close_list():
        nonlocal listing
        if listing:out.append('</ul>');listing=False
    while i<len(lines):
        line=lines[i]
        if line.startswith('```'):
            flush();close_list();language=line[3:].strip();code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
            out.append(diagram('\n'.join(code)) if language=='diagram' else '<pre><code class="language-'+html.escape(language)+'">'+highlight('\n'.join(code),language)+'</code></pre>')
        elif line.startswith('::: answer'):
            flush();close_list();title=line[len('::: answer'):].strip() or '展开参考答案';inner=[];i+=1
            while i<len(lines) and lines[i].strip()!=':::':inner.append(lines[i]);i+=1
            if i==len(lines):raise ValueError('Unclosed answer block')
            content,_=render('\n'.join(inner));out.append('<details class="self-answer"><summary>'+html.escape(title)+'</summary>'+content+'</details>')
        elif re.match(r'^#{1,6} ',line):
            flush();close_list();level=len(line)-len(line.lstrip('#'));title=line[level:].strip();anchor='section-'+str(len(toc)+1);toc.append((level,title,anchor));out.append(f'<h{level} id="{anchor}">'+inline(title)+f'</h{level}>')
        elif line.startswith('|') and i+1<len(lines) and re.match(r'^\|[ :|\-]+\|?$',lines[i+1]):
            flush();close_list();cells=lambda s:s.strip().strip('|').split('|');head=cells(line);i+=2;rows=[]
            while i<len(lines) and lines[i].startswith('|'):rows.append(cells(lines[i]));i+=1
            i-=1;out.append('<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+inline(x.strip())+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(x.strip())+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>')
        elif line.startswith('- ') or re.match(r'^\d+\. ',line):
            flush()
            if not listing:out.append('<ul>');listing=True
            out.append('<li>'+inline(re.sub(r'^(?:- |\d+\. )','',line))+'</li>')
        elif line.startswith('> '):flush();close_list();out.append('<blockquote>'+inline(line[2:])+'</blockquote>')
        elif not line.strip():flush();close_list()
        elif line.startswith('<!--'):flush();close_list()
        else:paragraph.append(line)
        i+=1
    flush();close_list();return '\n'.join(out),toc

def build():
    DEST.mkdir(parents=True,exist_ok=True)
    chapters=sorted((SOURCE/'chapters').glob('*.md'))
    pages=[SOURCE/'index.md',*chapters,SOURCE/'questions-for-chatgpt.md']
    version=json.loads((SOURCE/'source-version.json').read_text(encoding='utf-8'))
    names={p.stem:next(x[2:] for x in p.read_text(encoding='utf-8').splitlines() if x.startswith('# ')) for p in pages}
    nav=''.join('<a href="'+p.stem+'.html">'+html.escape(names[p.stem])+'</a>' for p in pages)
    search=[];stats=[]
    for n,p in enumerate(pages):
        text=p.read_text(encoding='utf-8');body,toc=render(text)
        page_toc=''.join('<a href="#'+a+'">'+html.escape(t)+'</a>' for level,t,a in toc if level in (2,3))
        adjacent=('<a href="'+pages[n-1].stem+'.html">← '+html.escape(names[pages[n-1].stem])+'</a>' if n else '')+('<a href="'+pages[n+1].stem+'.html">'+html.escape(names[pages[n+1].stem])+' →</a>' if n+1<len(pages) else '')
        content='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(names[p.stem])+' · PowerTrustAI学习站</title><link rel="stylesheet" href="style.css"><body><header><a href="index.html">PowerTrustAI / 项目学习与面试</a><button id="menu" aria-expanded="false">目录</button><label>全文搜索<input id="search" type="search" placeholder="条件、RRF、Revision…"></label></header><div id="search-results" aria-live="polite" hidden></div><div class="layout"><nav id="chapters" aria-label="章节目录">'+nav+'</nav><main><div class="version">源码基线 '+html.escape(version['application_commit'][:12])+' · '+html.escape(version['document_version'])+' · 教学示例与真实结果分别标记</div><article>'+body+'</article><footer>'+adjacent+'</footer></main><aside aria-label="本章目录">'+page_toc+'</aside></div><script src="search-data.js"></script><script src="site.js"></script></body></html>'
        (DEST/(p.stem+'.html')).write_text(content,encoding='utf-8');search.append({'title':names[p.stem],'url':p.stem+'.html','text':text});stats.append({'source':p.relative_to(ROOT).as_posix(),'characters':len(text),'sha256':hashlib.sha256(text.encode()).hexdigest()})
    for name in ('style.css','site.js'): (DEST/name).write_bytes((SOURCE/'assets'/name).read_bytes())
    (DEST/'search-data.js').write_text('window.learningSearch='+json.dumps(search,ensure_ascii=False).replace('<','\\u003c')+';',encoding='utf-8')
    (DEST/'build-manifest.json').write_text(json.dumps({'version':version,'chapters':stats,'markdown_characters':sum(s['characters'] for s in stats),'network_dependencies':False},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built',len(chapters),'chapters;',sum(s['characters'] for s in stats),'Markdown characters')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('build','serve'),nargs='?',default='serve');parser.add_argument('--port',type=int,default=8770);parser.add_argument('--open',action='store_true');a=parser.parse_args()
    if a.action=='build':build();return
    if not (DEST/'index.html').exists():build()
    url=f'http://127.0.0.1:{a.port}/'
    from urllib.request import build_opener,ProxyHandler
    # Probe before bind: Windows SO_REUSEADDR can permit a second listener.
    try:
        with build_opener(ProxyHandler({})).open(url,timeout=2) as response:body=response.read(131072).decode('utf-8')
    except OSError:body=None
    if body is not None:
        if 'PowerTrustAI学习站' not in body:raise RuntimeError('Port occupied by another service; choose a different --port')
        if a.open:webbrowser.open(url)
        print('Existing learning site reused: '+url);return
    class ReaderServer(ThreadingHTTPServer):allow_reuse_address=False
    server=ReaderServer(('127.0.0.1',a.port),partial(SimpleHTTPRequestHandler,directory=str(DEST)))
    if a.open:webbrowser.open(url)
    print(f'Learning only: {url} ; Ctrl+C to stop. No paid API.')
    server.serve_forever()

if __name__=='__main__':main()
