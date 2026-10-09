"""Versioned subject-constrained BM25 recall; full statements stay in audit inputs."""
import re
from functools import lru_cache
from rag.chinese_terms import segmenter,query_expression,TOPIC_VERSION,ALIASES
VERSION='topic-subject-and-bm25-v1'
GENERIC={'系统','电力','情况','条件','范围','适用范围','主要优点','优点','主要','关系','中文','普通','说明','回答','意义','原因','方法','过程','问题','同等','用量','相比','任何','不是','常用','以内','字'}

@lru_cache(maxsize=1)
def tagger():
    from jieba.posseg import POSTokenizer
    return POSTokenizer(segmenter())

def plan(query):
    # Only user output constraints/routing metadata are stripped; never delete
    # an asserted universal claim from the actual answer or model review.
    text=re.sub(r'\nvoltage_stability_reactive_support\nengineering prerequisites constraints operating limits applicability\s*$','',query).replace('功率因素','功率因数')
    text=re.sub(r'(?:不要|请勿|避免)(?:说|声称|宣称|断言|作出|做出|认为)[^。；;!?！？]*','',text)
    text=re.sub(r'\d+\s*字(?:以内|以下)|请用[^。；;!?！？]{0,60}?(?:回答|说明)','',text)
    anchors=[]
    # Each independent clause retains a subject lane. Do not select a topic
    # from answer-format metadata; full positive qualifier terms still score.
    for sentence in re.split(r'[。；;!?！？\n]',text):
        for t in tagger().cut(sentence,HMM=False):
            w=t.word.casefold()
            if (t.flag.startswith('n') or t.flag in ('eng','l')) and len(w)>=2 and w not in GENERIC and re.fullmatch(r'[a-z0-9\u3400-\u4dbf\u4e00-\u9fff]+',w):
                if w not in anchors:anchors.append(w)
                break
    if not anchors or len(anchors)>24:return [('fallback',query_expression(query,TOPIC_VERSION))]
    anchors=sorted(anchors)
    groups=['('+' OR '.join('"'+t+'"' for t in sorted({w,*ALIASES.get(w,())}))+')' for w in anchors]
    expression=query_expression(text,TOPIC_VERSION)
    return [('focus','('+expression+') AND ('+' OR '.join(groups)+')')]

def rank(connection,query,limit):
    expression=plan(query)[0][1]
    if not expression:return []
    return connection.execute('SELECT rowid,bm25(corpus_fts) AS score FROM corpus_fts WHERE corpus_fts MATCH ? ORDER BY score,rowid LIMIT ?',(expression,limit)).fetchall()
