"""Versioned grammatical scoring cleanup; subject membership stays unchanged."""
import re
from rag.topic_lanes import plan as subject_plan

VERSION='topic-subject-grammar-bm25-v2'
# No physical units, numbers, negation, direction or load/state qualifiers.
GRAMMAR={'时','会','使','其','所','以','也','而','但','则','应','可','要','把','某','段','受','更','都','才','就','将','被','等','得','地','着','仍','又','已','对','需','于'}

def plan(query):
    mode,expression=subject_plan(query)[0]
    left,separator,right=expression.partition(') AND (')
    if mode!='focus' or not separator:return [(mode,expression)]
    words=re.findall(r'"([^\"]+)"',left)
    subjects=set(re.findall(r'"([^\"]+)"',right))
    kept=[w for w in words if w not in GRAMMAR or w in subjects]
    if not kept:return [(mode,expression)]
    return [('focus','('+' OR '.join('"'+w+'"' for w in kept)+separator+right)]

def rank(connection,query,limit):
    expression=plan(query)[0][1]
    if not expression:return []
    return connection.execute('SELECT rowid,bm25(corpus_fts) AS score FROM corpus_fts WHERE corpus_fts MATCH ? ORDER BY score,rowid LIMIT ?',(expression,limit)).fetchall()
