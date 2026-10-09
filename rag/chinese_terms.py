"""Versioned deterministic dictionary segmentation, shared by FTS build/query."""
import re
from functools import lru_cache
VERSION = 'jieba-0.42.1-electric-terms-v1'
QUERY_VERSION='electric-topic-query-v2'
TOPIC_VERSION='electric-topic-query-v3-format-metadata'
ALIASES={'功率因素':('功率因数',),'无功':('无功功率',),'电网':('电力系统',)}
TERMS = ('无功功率','有功功率','功率因数','无功补偿','电压稳定','母线电压','感性负载','并联电容','静止无功补偿器','静止同步补偿器','电力变压器','短路电流','继电保护','电能质量')
@lru_cache(maxsize=1)
def segmenter():
    import jieba
    t=jieba.Tokenizer()
    t.initialize()
    for word in TERMS:t.add_word(word,100000)
    return t
def terms(text):
    return tuple(w.casefold() for w in segmenter().cut(text,HMM=False)
                 if re.fullmatch(r'[a-zA-Z0-9\u3400-\u4dbf\u4e00-\u9fff]+',w))
def query_expression(text,version=QUERY_VERSION):
    if version==TOPIC_VERSION:
        # Generated task-routing metadata is not a body-search topic. Strip only
        # the exact program-owned suffix, not free user engineering language.
        text=re.sub(r'\nvoltage_stability_reactive_support\nengineering prerequisites constraints operating limits applicability\s*$','',text)
        text=re.sub(r'(?:请)?用\s*\d+\s*字(?:以内(?:回答|说明)?|回答|说明)','',text)
        version=QUERY_VERSION
        topic=True
    else:topic=False
    if version=='electric-topic-query-v1':
        return ' OR '.join('"'+w+'"' for w in sorted(set(terms(text))))
    if version!=QUERY_VERSION:raise ValueError('Unknown query processing version')
    text=text.replace('功率因素','功率因数')
    # Generic answer-format requests aren't search topics. Keep the original query
    # in RetrievalRequest/archives; no factual conclusion or source is added.
    text=re.sub(r'请用[^。；;!?！？]{0,60}?(?:回答|说明)[，,。]?','',text)
    text=re.sub(r'(?:控制在|不超过|最多)\s*\d+\s*字(?:以内)?','',text)
    text=re.sub(r'不讨论[^。；;!?！？]*','',text)
    selected=[w for w in terms(text) if w not in {'什么','为什么','怎么','如何','需要','请','回答','说明','以内','不','讨论','具体','普通','中文','用','能','理解','控制','的','了','是','和','与','在','及','或','为','到','有'}]
    if topic:selected=[w for w in selected if w not in {'条件','下','它','关系'}]
    expanded=set(selected)
    for w in selected:expanded.update(ALIASES.get(w,()))
    return ' OR '.join('"'+w+'"' for w in sorted(expanded))
