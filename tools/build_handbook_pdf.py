"""Build the project's own handbook; no model calls, credentials or data ingestion.

Requires reportlab (document tooling runtime, separate from project execution).
Markdown and Mermaid sources remain editable. PDF diagrams use vector graphics.
"""
from pathlib import Path
import argparse
import html
import re
import json
import hashlib

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, Flowable, CondPageBreak,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT = Path(__file__).resolve().parents[1]
NAVY = colors.HexColor('#19324B')
TEAL = colors.HexColor('#27676B')
GRAY = colors.HexColor('#56616D')
LIGHT = colors.HexColor('#EDF2F6')


def inline(text):
    text = html.escape(text)
    text = re.sub(r'https?://[A-Za-z0-9./:_-]+', lambda m: '<link href="'+m.group()+'" color="#27676B">'+m.group()+'</link>', text)
    text = re.sub(r'`([^`]+)`', r'<font color="#27676B">\1</font>', text)
    return re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)


class Doc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == 'Chapter':
            label = flowable.getPlainText()
            key = 'chapter-' + hashlib.sha256(label.encode()).hexdigest()[:16]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(label, key, 0, False)
            self.notify('TOCEntry', (0, label, self.page, key))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#CCD5DE'))
    canvas.line(48, 42, A4[0] - 48, 42)
    canvas.setFont('CJK', 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(48, 28, 'PowerTrustAI  /  本机辅助审核原型 v0.1  /  2026-10-04')
    canvas.drawRightString(A4[0] - 48, 28, str(doc.page))
    if doc.page > 1:
        canvas.drawString(48, A4[1] - 30, '项目学习与面试手册  ·  辅助审核不是工程安全认证')
    canvas.restoreState()


def diagram(kind):
    width = A4[0] - 96
    d = Drawing(width, 326 if kind == 'architecture' else 330)
    def box(x, y, w, h, lines, fill=LIGHT):
        d.add(Rect(x, y, w, h, fillColor=fill, strokeColor=colors.HexColor('#BAC8D5'), rx=5, ry=5))
        for i, text in enumerate(lines):
            d.add(String(x+w/2, y+h/2+(len(lines)-1)*7-i*14-3, text,
                         fontName='CJK', fontSize=9.5, textAnchor='middle', fillColor=NAVY))
    def arrow(x1,y1,x2,y2):
        d.add(Line(x1,y1,x2,y2,strokeColor=TEAL,strokeWidth=1))
        if y1 != y2:
            d.add(Polygon([x2,y2,x2-3,y2+6,x2+3,y2+6],fillColor=TEAL,strokeColor=TEAL))
        else:
            d.add(Polygon([x2,y2,x2-6,y2-3,x2-6,y2+3],fillColor=TEAL,strokeColor=TEAL))
    cx=width/2
    if kind=='architecture':
        for y, lines in [(278,['同源中文 Web 页面']), (224,['API：鉴权 / 校验 / 作用域']),
                         (170,['ApplicationService + ComponentFactory']),
                         (116,['OfflineHarness：流程 / 预算 / 确定性政策'])]:
            box(cx-152,y,304,38,lines)
        for y in [278,224,170]: arrow(cx,y,cx,y-16)
        box(0,49,153,43,['四 Agent + 提取服务','受控模型适配器'])
        box(173,49,153,43,['Retriever / Evidence','有限工具 / 程序规则'])
        box(346,49,153,43,['SQLite 运行存储','事件 / 结果 / 反馈'])
        arrow(cx-99,116,76,92);arrow(cx,116,249,92);arrow(cx+99,116,422,92)
        d.add(String(cx,17,'模型判断、程序规则、工具和人工意见保留各自来源',fontName='CJK',fontSize=9,textAnchor='middle',fillColor=GRAY))
    else:
        box(cx-150,282,300,34,['API 提交：保存 run_id'])
        box(12,224,213,36,['问答：Generation'])
        box(width-225,224,213,36,['已有回答：直接建初稿'])
        arrow(cx,282,118,260);arrow(cx,282,width-118,260)
        box(cx-150,164,300,40,['冻结 v1 → ClaimExtractor'])
        arrow(118,224,cx-50,204);arrow(width-118,224,cx+50,204)
        box(cx-150,105,300,40,['事实审核 + 领域审核','程序检查 → 确定性政策'])
        arrow(cx,164,cx,145)
        box(10,40,234,44,['需要修订且未超限：Revision v2','重新提取 + 双重审（最多一次）'])
        box(width-239,40,229,44,['结束或达到限制','保存有效结果 / 人工复核'])
        arrow(cx-65,105,127,84);arrow(cx+65,105,width-124,84)
        arrow(244,62,width-239,62)
        d.add(String(cx,14,'异常、取消、预算耗尽可以提前停止；每阶段保留有效部分',fontName='CJK',fontSize=8.8,textAnchor='middle',fillColor=GRAY))
    d.scale(.85, .85)
    d.height *= .85
    return d


def build(source, output):
    pdfmetrics.registerFont(TTFont('CJK', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
    pdfmetrics.registerFont(TTFont('CJK-Bold', 'C:/Windows/Fonts/msyhbd.ttc', subfontIndex=0))
    pdfmetrics.registerFontFamily('CJK',normal='CJK',bold='CJK-Bold',italic='CJK',boldItalic='CJK-Bold')
    styles=getSampleStyleSheet()
    body=ParagraphStyle('BodyCJK',fontName='CJK',fontSize=10.5,leading=17.5,spaceAfter=8,wordWrap='CJK',textColor=NAVY)
    chapter=ParagraphStyle('Chapter',parent=body,fontName='CJK-Bold',fontSize=20,leading=28,spaceAfter=20)
    section=ParagraphStyle('Section',parent=body,fontName='CJK-Bold',fontSize=13,leading=21,spaceBefore=12,spaceAfter=8,keepWithNext=True)
    small=ParagraphStyle('SmallCJK',parent=body,fontSize=8.8,leading=13.2,spaceAfter=3)
    code=ParagraphStyle('CodeCJK',parent=body,fontSize=8.5,leading=13,spaceAfter=5,backColor=LIGHT,borderPadding=6)
    tocstyle=ParagraphStyle('TOCCJK',parent=body,fontSize=11,leading=21,leftIndent=0,firstLineIndent=0,spaceBefore=5)
    lines=source.read_text(encoding='utf-8').splitlines()
    story=[]
    story.extend([Spacer(1,110),Paragraph('PowerTrustAI',ParagraphStyle('Cover',parent=chapter,fontSize=37,leading=48)),
        Paragraph('项目学习与面试手册',ParagraphStyle('CoverTitle',parent=chapter,fontSize=25,leading=36)),
        Spacer(1,25),Paragraph('从概念、代码与真实失败理解本机辅助审核',body),
        Paragraph('v0.1  ·  2026-10-04',body),Spacer(1,52),
        Paragraph('可回查依据 / 有限修订 / 持久化 / 人工监督',body),
        Paragraph('不是工程安全认证；不以测试数量代替语义正确。',small),PageBreak()])
    i=1
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1;continue
        if line=='## 目录':
            story.append(PageBreak());story.append(Paragraph('目录',section))
            toc=TableOfContents();toc.levelStyles=[tocstyle];story.append(toc)
            i+=1
            while i<len(lines) and lines[i].strip()!='<!-- chapter -->': i+=1
            continue
        if line=='<!-- chapter -->':
            story.append(CondPageBreak(480));i+=1;continue
        if line.startswith('<!-- diagram:'):
            story.append(diagram(line.split(':')[1].split()[0]));story.append(Spacer(1,10));i+=1;continue
        if line.startswith('# '):story.append(Paragraph(inline(line[2:]),chapter));i+=1;continue
        if line.startswith('## '):story.append(Paragraph(inline(line[3:]),section));i+=1;continue
        if line.startswith('```'):
            chunk=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                # Render code as safe text; wrap long paths, never truncate.
                raw=lines[i]
                chunk.extend([raw[j:j+72] for j in range(0,max(1,len(raw)),72)])
                i+=1
            story.append(Paragraph('<br/>'.join(html.escape(x).replace(' ','&#160;') for x in chunk),code));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',x) for x in cells): rows.append([Paragraph(inline(x),small) for x in cells])
                i+=1
            n=len(rows[0]);width=A4[0]-96
            ratios={3:[.22,.39,.39],4:[.17,.28,.28,.27]}.get(n,[1/n]*n)
            table=Table(rows,colWidths=[width*x for x in ratios],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LINEBELOW',(0,0),(-1,0),.8,TEAL),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D8E0E7')),
                ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([KeepTogether([table]),Spacer(1,10)]);continue
        if line.startswith('- '):story.append(Paragraph('• '+inline(line[2:]),body));i+=1;continue
        para=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','<!--','- ')):
            para.append(lines[i].strip());i+=1
        text=' '.join(para)
        citation=text.startswith(('本章依据：','阅读依据：','阅读入口：','代码入口：','依据：','本章依据：','证据路径：'))
        story.append(Paragraph(inline(text),small if citation else body))
    output.parent.mkdir(parents=True,exist_ok=True)
    grouped=[]
    j=0
    while j<len(story):
        if (isinstance(story[j],Paragraph) and story[j].style.name=='Section'
                and j+1<len(story) and isinstance(story[j+1],KeepTogether)):
            grouped.append(KeepTogether([story[j]]+story[j+1]._content))
            j+=2
        else:
            grouped.append(story[j]);j+=1
    doc=Doc(str(output),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=54,bottomMargin=56,
            title='PowerTrustAI 项目学习与面试手册',author='PowerTrustAI 项目文档',allowSplitting=True)
    doc.addPageTemplates(PageTemplate(id='Main',frames=Frame(48,56,A4[0]-96,A4[1]-110,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),onPage=footer))
    doc.multiBuild(grouped)
    record={'source':str(source.relative_to(ROOT)),'output':str(output.relative_to(ROOT)),
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'pdf_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'pages':doc.page,
            'model_calls':0,'credentials_read':False,'historical_pdf_body_read':False}
    log=ROOT/'data/runtime_local/final-handbook/build.json';log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=ROOT/'docs/PowerTrustAI-project-study-interview-handbook.md')
    parser.add_argument('--output',type=Path,default=ROOT/'output/pdf/PowerTrustAI_Project_Study_Interview_Handbook_v0.1.pdf')
    args=parser.parse_args();build(args.source,args.output)
