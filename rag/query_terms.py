"""Development-designed controlled query terms; never modifies source/Evidence.

Opt-in experimental BM25 query adapter. These are lexical aids, not factual
rules. English/Chinese siblings are the same evaluation family.
"""
VERSION = 'power-zh-en-query-terms-v1'
TERMS = (
    ('电压稳定', 'voltage stability'),
    ('电压失稳', 'voltage instability'),
    ('母线电压', 'bus voltage'),
    ('正常', 'normal'),
    ('发电机', 'generator generators'),
    ('无功', 'reactive power'),
    ('支撑', 'support'),
    ('运行', 'operating operation'),
    ('限制', 'limit limits'),
    ('监测', 'monitor monitoring'),
    ('裕度', 'margin margins'),
    ('储备', 'reserve reserves'),
    ('短时过载', 'short overload'),
    ('遗漏', 'miss'),
    ('大范围', 'wide area'),
)

def expand_query(query):
    matched=[{'trigger':zh,'terms':en} for zh,en in TERMS if zh in query]
    return query + ((' ' + ' '.join(m['terms'] for m in matched)) if matched else ''), tuple(matched)
